import re
from datetime import date

from django import forms

from core.models import Categoria, Quartiere, Utente

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


class RegistrazioneForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=50)
    cognome = forms.CharField(label="Cognome", max_length=50)
    email = forms.EmailField(label="Email", max_length=254)
    password = forms.CharField(label="Password", widget=forms.PasswordInput,
                               help_text="Almeno 8 caratteri, con una maiuscola, un numero e un simbolo.")
    password2 = forms.CharField(label="Ripeti la password", widget=forms.PasswordInput)
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

    def clean_password(self):
        p = self.cleaned_data["password"]
        if not (len(p) >= 8 and re.search(r"[A-Z]", p) and re.search(r"\d", p) and re.search(r"[^\w\s]", p)):
            raise forms.ValidationError("La password deve avere almeno 8 caratteri, una maiuscola, un numero e un simbolo.")
        return p

    def clean_data_nascita(self):
        n = self.cleaned_data["data_nascita"]
        if n > date.today() or eta_anni(n) < 14:
            raise forms.ValidationError("Per registrarti devi avere almeno 14 anni.")
        return n

    def clean(self):
        d = super().clean()
        if d.get("password") and d.get("password2") and d["password"] != d["password2"]:
            self.add_error("password2", "Le due password non coincidono.")
        return d


class SpidSimulatoForm(forms.Form):
    metodo = forms.ChoiceField(label="Identità digitale", choices=[("spid", "SPID"), ("cie", "CIE")], widget=forms.RadioSelect, initial="spid")
    nome = forms.CharField(max_length=50, label="Nome")
    cognome = forms.CharField(max_length=50, label="Cognome")
    data_nascita = forms.DateField(label="Data di nascita", widget=forms.DateInput(attrs={"type": "date"}))
    codice_fiscale = forms.CharField(label="Codice fiscale (fittizio)", min_length=16, max_length=16,
                                     help_text="Sedici caratteri. Viene salvato solo come impronta (hash).")
    email = forms.EmailField(label="Email")
    privacy = forms.BooleanField(label=MESSAGGI_CONSENSI["privacy"])
    intelligenza_artificiale = forms.BooleanField(label=MESSAGGI_CONSENSI["intelligenza_artificiale"])
    termini_uso = forms.BooleanField(label=MESSAGGI_CONSENSI["termini_uso"])
    cookie = forms.BooleanField(label=MESSAGGI_CONSENSI["cookie"])
    eta_minima = forms.BooleanField(label=MESSAGGI_CONSENSI["eta_minima"])

    def clean_data_nascita(self):
        n = self.cleaned_data["data_nascita"]
        if n > date.today() or eta_anni(n) < 14:
            raise forms.ValidationError("Per accedere devi avere almeno 14 anni.")
        return n

    def clean_codice_fiscale(self):
        cf = self.cleaned_data["codice_fiscale"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{16}", cf):
            raise forms.ValidationError("Il codice fiscale deve avere 16 caratteri alfanumerici.")
        return cf

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
