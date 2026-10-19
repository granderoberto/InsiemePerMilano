import re
from datetime import date

from django import forms

from core.models import Categoria, Quartiere, Utente
import time

from django.core import signing
from django.utils.safestring import mark_safe

from core.services import file_documento, password

class QuartiereMilano(forms.ModelChoiceField):
    """Scelta del quartiere (NIL del Comune di Milano) dall'elenco o dalla mappa (static/js/quartiere.js)."""

    def __init__(self, **kw):
        kw.setdefault("queryset", Quartiere.objects.order_by("nome"))
        kw.setdefault("required", False)
        kw.setdefault("empty_label", "— nessuno —")
        kw.setdefault("widget", forms.Select(attrs={"data-mappa-quartiere": "1"}))
        super().__init__(**kw)

    def label_from_instance(self, q):
        return q.nome_leggibile


def _l(tipo, testo):
    """Testo del documento come collegamento alla pagina delle normative (si apre in un'altra scheda: il modulo resta com'è)."""
    return f'<a href="/normative/#{tipo}" target="_blank" rel="noopener">{testo}</a>'


MESSAGGI_CONSENSI = {
    "privacy": mark_safe(f"Ho letto l'{_l('privacy', 'informativa sulla privacy')} (GDPR, art. 13)"),
    "biometrici": mark_safe(f"Acconsento al {_l('biometrici', 'trattamento dei dati biometrici')} per il confronto del selfie (GDPR, art. 9)"),
    "intelligenza_artificiale": mark_safe(f"Ho letto l'{_l('intelligenza_artificiale', 'informativa sull&#x27;uso dell&#x27;intelligenza artificiale')} e so di poter chiedere la revisione di una persona (art. 22)"),
    "termini_uso": mark_safe(f"Accetto i {_l('termini_uso', 'termini d&#x27;uso')} e il regolamento della community"),
    "cookie": mark_safe(f"Ho letto la {_l('cookie', 'cookie policy')}"),
    "eta_minima": mark_safe(f"Dichiaro di avere almeno 14 anni ({_l('eta_minima', 'perché')})"),
}


def eta_anni(nascita: date) -> int:
    oggi = date.today()
    return oggi.year - nascita.year - ((oggi.month, oggi.day) < (nascita.month, nascita.day))


class SegnalazioneForm(forms.Form):
    tipo = forms.ChoiceField(label="Tipo", choices=[("problema", "Segnalo un problema"), ("proposta", "Faccio una proposta")],
                             widget=forms.RadioSelect, initial="problema")
    titolo = forms.CharField(label="Titolo", max_length=100, help_text="Massimo 100 caratteri.")
    descrizione = forms.CharField(label="Descrizione", min_length=30, max_length=2000, widget=forms.Textarea(attrs={"rows": 6}),
                                  help_text="Tra 30 e 2000 caratteri: cosa succede, da quanto, a chi crea disagio.")
    categorie = forms.ModelMultipleChoiceField(label="Categorie", queryset=Categoria.objects.filter(attiva=True),
                                               widget=forms.CheckboxSelectMultiple, error_messages={"required": "Scegli almeno una categoria."},
                                               help_text="Te le suggeriamo noi in base al testo: puoi confermarle o cambiarle.")
    latitudine = forms.FloatField(widget=forms.HiddenInput, error_messages={"required": "Indica il luogo sulla mappa."})
    longitudine = forms.FloatField(widget=forms.HiddenInput, error_messages={"required": "Indica il luogo sulla mappa."})
    indirizzo = forms.CharField(label="Indirizzo (facoltativo)", max_length=255, required=False)

    def clean(self):
        d = super().clean()
        lat, lon = d.get("latitudine"), d.get("longitudine")
        if lat is not None and lon is not None and not (45.38 <= lat <= 45.54 and 9.04 <= lon <= 9.28):
            self.add_error(None, "Il luogo scelto è fuori dal Comune di Milano.")
        return d


_NUOVA = {"data-password": "nuova", "autocomplete": "new-password"}


SALT_SFIDA = "lnc-sfida-selfie"


def nuova_sfida() -> str:
    """Il selfie deve arrivare dalla fotocamera della nostra pagina: la pagina riceve una sfida firmata e a scadenza e la rimanda."""
    return signing.dumps({"t": time.time()}, salt=SALT_SFIDA)


class DocumentiForm(forms.Form):
    """Documento d'identità (fronte e retro) e selfie dal vivo: par. 3.2. Si usa in registrazione e nei nuovi tentativi."""
    tipo_documento = forms.ChoiceField(label="Tipo di documento", choices=[("carta_identita", "Carta d'identità"), ("patente", "Patente"), ("passaporto", "Passaporto")],
                                       initial="carta_identita")
    fronte = forms.FileField(label="Documento: fronte", help_text="JPG, PNG o PDF, al massimo 5 MB.",
                             widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,application/pdf"}))
    retro = forms.FileField(label="Documento: retro", required=False, help_text="JPG, PNG o PDF, al massimo 5 MB. Per il passaporto non serve.",
                            widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,application/pdf"}))
    selfie = forms.FileField(label="Selfie", widget=forms.FileInput(attrs={"hidden": True, "accept": "image/jpeg"}),
                             error_messages={"required": "Scatta il selfie con la fotocamera."})
    sfida = forms.CharField(widget=forms.HiddenInput, required=False)

    def clean_sfida(self):
        try:
            signing.loads(self.cleaned_data.get("sfida", ""), salt=SALT_SFIDA, max_age=20 * 60)
        except signing.BadSignature:
            raise forms.ValidationError("Il selfie va scattato con la fotocamera dalla pagina (non si può caricare dalla galleria) ed entro 20 minuti: scattalo di nuovo.")
        return self.cleaned_data["sfida"]

    def clean(self):
        d = super().clean()
        try:
            if d.get("fronte"):
                d["_fronte"] = file_documento.leggi(d["fronte"], "Fronte del documento")
            if d.get("retro"):
                d["_retro"] = file_documento.leggi(d["retro"], "Retro del documento")
            elif d.get("tipo_documento") and d["tipo_documento"] != "passaporto":
                self.add_error("retro", "Carica anche il retro del documento.")
            if d.get("selfie"):
                d["_selfie"] = file_documento.leggi(d["selfie"], "Selfie", ammetti_pdf=False)
        except file_documento.FileNonValido as e:
            self.add_error(None, str(e))
        return d


class RegistrazioneForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=50)
    cognome = forms.CharField(label="Cognome", max_length=50)
    email = forms.EmailField(label="Email", max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs=_NUOVA))
    password2 = forms.CharField(label="Ripeti la password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "data-conferma": "password"}))
    data_nascita = forms.DateField(label="Data di nascita", widget=forms.DateInput(attrs={"type": "date"}),
                                   help_text="Età minima: 14 anni.")
    quartiere = QuartiereMilano(label="Quartiere di residenza (facoltativo)")
    privacy = forms.BooleanField(label=MESSAGGI_CONSENSI["privacy"])
    intelligenza_artificiale = forms.BooleanField(label=MESSAGGI_CONSENSI["intelligenza_artificiale"])
    termini_uso = forms.BooleanField(label=MESSAGGI_CONSENSI["termini_uso"])
    cookie = forms.BooleanField(label=MESSAGGI_CONSENSI["cookie"])
    eta_minima = forms.BooleanField(label=MESSAGGI_CONSENSI["eta_minima"])

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if Utente.objects.filter(email=e).exists():
            raise forms.ValidationError("Esiste già un account con questa email.")
        return e

    def clean_data_nascita(self):
        n = self.cleaned_data["data_nascita"]
        if n > date.today() or eta_anni(n) < 14:
            raise forms.ValidationError("Per registrarti devi avere almeno 14 anni.")
        return n

    def clean(self):
        d = super().clean()
        if d.get("password"):
            err = password.valida(d["password"], d.get("nome", ""), d.get("cognome", ""), d.get("email", ""))
            if err:
                self.add_error("password", err)
        if d.get("password") and d.get("password2") and d["password"] != d["password2"]:
            self.add_error("password2", "Le due password non coincidono.")
        return d


class VerificaForm(DocumentiForm):
    """Verifica facoltativa dell'identità, necessaria per pubblicare: documento, selfie e, la prima volta, il consenso biometrico (art. 9)."""
    biometrici = forms.BooleanField(label=MESSAGGI_CONSENSI["biometrici"])

    def __init__(self, *a, consenso_gia_dato=False, **kw):
        super().__init__(*a, **kw)
        if consenso_gia_dato:
            del self.fields["biometrici"]


class SpidCompletaForm(forms.Form):
    """Primo accesso con SPID/CIE: nome, cognome e codice fiscale arrivano dal gestore di identità e non si modificano."""
    email = forms.EmailField(label="Email", max_length=254)
    data_nascita = forms.DateField(label="Data di nascita", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    quartiere = QuartiereMilano(label="Quartiere di residenza (facoltativo)")
    privacy = forms.BooleanField(label=MESSAGGI_CONSENSI["privacy"])
    intelligenza_artificiale = forms.BooleanField(label=MESSAGGI_CONSENSI["intelligenza_artificiale"])
    termini_uso = forms.BooleanField(label=MESSAGGI_CONSENSI["termini_uso"])
    cookie = forms.BooleanField(label=MESSAGGI_CONSENSI["cookie"])
    eta_minima = forms.BooleanField(label=MESSAGGI_CONSENSI["eta_minima"])

    def __init__(self, *a, nascita_idp=None, **kw):
        super().__init__(*a, **kw)
        self.nascita_idp = nascita_idp  # se il gestore la fornisce, non si chiede e non si può cambiare
        if nascita_idp:
            del self.fields["data_nascita"]

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if Utente.objects.filter(email=e).exists():
            raise forms.ValidationError("Esiste già un account con questa email: accedi con le credenziali o recupera la password.")
        return e

    def clean(self):
        d = super().clean()
        n = self.nascita_idp or d.get("data_nascita")
        if not n:
            self.add_error("data_nascita", "Inserisci la data di nascita.")
        elif n > date.today() or eta_anni(n) < 14:
            self.add_error(None if self.nascita_idp else "data_nascita", "Per usare la piattaforma devi avere almeno 14 anni.")
        d["nascita"] = n
        return d


_NUOVA = {"data-password": "nuova", "autocomplete": "new-password"}


class PasswordForm(forms.Form):
    password = forms.CharField(label="Nuova password", widget=forms.PasswordInput(attrs=_NUOVA))
    password2 = forms.CharField(label="Ripeti la password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "data-conferma": "password"}))

    def __init__(self, *a, utente=None, **kw):
        super().__init__(*a, **kw)
        self.utente = utente  # per non accettare password basate sui propri dati

    def clean_password(self):
        u = self.utente
        err = password.valida(self.cleaned_data["password"], getattr(u, "nome", ""), getattr(u, "cognome", ""), getattr(u, "email", ""))
        if err:
            raise forms.ValidationError(err)
        return self.cleaned_data["password"]

    def clean(self):
        d = super().clean()
        if d.get("password") and d.get("password2") and d["password"] != d["password2"]:
            self.add_error("password2", "Le due password non coincidono.")
        return d


class CambioPasswordForm(PasswordForm):
    attuale = forms.CharField(label="Password attuale", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    field_order = ["attuale", "password", "password2"]

    def clean_attuale(self):
        if not (self.utente and self.utente.check_password(self.cleaned_data["attuale"])):
            raise forms.ValidationError("La password attuale non è corretta.")
        return self.cleaned_data["attuale"]
