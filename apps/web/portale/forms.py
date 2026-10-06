import re
from datetime import date

from django import forms

from core.models import Categoria, Quartiere, Utente
from core.services import password

MESSAGGI_CONSENSI = {
    "privacy": "Ho letto l'informativa sulla privacy (GDPR, art. 13)",
    "biometrici": "Acconsento al trattamento dei dati biometrici per il confronto del selfie (GDPR, art. 9)",
    "intelligenza_artificiale": "Ho letto l'informativa sull'uso dell'intelligenza artificiale e so di poter chiedere la revisione di una persona (art. 22)",
    "termini_uso": "Accetto i termini d'uso e il regolamento della community",
    "cookie": "Ho letto la cookie policy",
    "eta_minima": "Dichiaro di avere almeno 14 anni",
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


class RegistrazioneForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=50)
    cognome = forms.CharField(label="Cognome", max_length=50)
    email = forms.EmailField(label="Email", max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs=_NUOVA),
                               help_text="Almeno 8 caratteri, con una maiuscola, un numero e un simbolo.")
    password2 = forms.CharField(label="Ripeti la password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "data-conferma": "password"}))
    data_nascita = forms.DateField(label="Data di nascita", widget=forms.DateInput(attrs={"type": "date"}),
                                   help_text="Età minima: 14 anni.")
    quartiere = forms.ModelChoiceField(label="Quartiere di residenza (facoltativo)", queryset=Quartiere.objects.all(),
                                       required=False, empty_label="— nessuno —")
    privacy = forms.BooleanField(label=MESSAGGI_CONSENSI["privacy"])
    biometrici = forms.BooleanField(label=MESSAGGI_CONSENSI["biometrici"])
    intelligenza_artificiale = forms.BooleanField(label=MESSAGGI_CONSENSI["intelligenza_artificiale"])
    termini_uso = forms.BooleanField(label=MESSAGGI_CONSENSI["termini_uso"])
    cookie = forms.BooleanField(label=MESSAGGI_CONSENSI["cookie"])
    eta_minima = forms.BooleanField(label=MESSAGGI_CONSENSI["eta_minima"])

    CAMPI_CONSENSO = list(MESSAGGI_CONSENSI)

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


class SpidCompletaForm(forms.Form):
    """Primo accesso con SPID/CIE: nome, cognome e codice fiscale arrivano dal gestore di identità e non si modificano."""
    email = forms.EmailField(label="Email", max_length=254)
    data_nascita = forms.DateField(label="Data di nascita", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    quartiere = forms.ModelChoiceField(label="Quartiere di residenza (facoltativo)", queryset=Quartiere.objects.all(), required=False, empty_label="— nessuno —")
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
    password = forms.CharField(label="Nuova password", widget=forms.PasswordInput(attrs=_NUOVA),
                               help_text="Almeno 8 caratteri, con una maiuscola, un numero e un simbolo.")
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
