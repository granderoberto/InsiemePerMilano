"""Impostazioni del progetto web (sviluppo locale).

Il database è quello di Aiven: credenziali da `.env` nella radice del repository, database da DJANGO_DB_NAME
(default: la_nostra_citta_test). Lo schema del dominio è gestito dalle migrazioni SQL (db/migrations/),
non da Django: vedi la regola di convivenza in CLAUDE.md.
"""
import os
import tempfile
from email.utils import parseaddr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent.parent


def _leggi_env():
    env = {}
    f = REPO_ROOT / ".env"
    if f.exists():
        for riga in f.read_text().splitlines():
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                env[k.strip()] = v.strip()
    return env


_env = _leggi_env()
_e = lambda k, d="": os.environ.get(k) or _env.get(k, d)  # variabile d'ambiente (hosting) oppure .env (sviluppo)

DEBUG = _e("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = _e("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY è obbligatoria in produzione (DJANGO_DEBUG=0). Se cambia, i segreti 2FA non si leggono più.")
    SECRET_KEY = "solo-sviluppo-non-usare-in-produzione"
# Gli altri siti ricevono solo il nome del nostro sito (non l'indirizzo completo): serve ai tile di OpenStreetMap, che rispondono 403 se manca il Referer
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
ALLOWED_HOSTS = [h.strip() for h in _e("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _e("DJANGO_CSRF_ORIGINS").split(",") if o.strip()]  # es. https://lanostracitta.example
_host_render = _e("RENDER_EXTERNAL_HOSTNAME")  # su Render è l'indirizzo pubblico del servizio, già noto: niente da configurare a mano
if _host_render:
    ALLOWED_HOSTS.append(_host_render)
    CSRF_TRUSTED_ORIGINS.append("https://" + _host_render)

if not DEBUG:
    # dietro il proxy dell'hosting: HTTPS già terminato, lo dichiara l'intestazione X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _e("DJANGO_SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(_e("DJANGO_HSTS_SECONDS", "3600"))  # alzare a 31536000 quando tutto funziona
    SECURE_REDIRECT_EXEMPT = [r"^salute/$"]  # il controllo di stato dell'hosting arriva in HTTP
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "portale",
    "moderazione",
    "amministrazione",
]

MIDDLEWARE = [
    "core.middleware.ControlloDiStato",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # file statici in produzione (in sviluppo li serve runserver)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context.sito",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

def _certificato_db():
    """Certificato CA del database: file certs/ca.pem (sviluppo) oppure testo PEM in DB_CA_PEM (hosting, senza file nel repository)."""
    pem = os.environ.get("DB_CA_PEM", "").replace("\\n", "\n")
    if pem.strip():
        f = Path(tempfile.gettempdir()) / "lnc_db_ca.pem"
        f.write_text(pem)
        return str(f)
    return str(REPO_ROOT / "certs" / "ca.pem")


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": _e("DJANGO_DB_NAME", "la_nostra_citta_test"),
        "HOST": _e("DB_HOST", "localhost"),
        "PORT": _e("DB_PORT", "3306"),
        "USER": _e("DB_USER", "root"),
        "PASSWORD": _e("DB_PASSWORD", ""),
        "OPTIONS": {
            "charset": "utf8mb4",
            "ssl": {"ca": _certificato_db()},
            "ssl_mode": "VERIFY_IDENTITY",
        },
        "CONN_MAX_AGE": 60,
    }
}

# Una FK BIGINT verso utenti.id (INT) fallirebbe: vedi regola 7 in CLAUDE.md
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

AUTH_USER_MODEL = "core.Utente"
AUTHENTICATION_BACKENDS = ["core.backends.UtenteBackend"]
LOGIN_URL = "accedi"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True  # nel DB tutto in UTC

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "static_raccolti"  # destinazione di `collectstatic` in produzione
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
# Foto e video caricati e archivio temporaneo della verifica: in produzione vanno su un disco persistente (DATA_DIR)
DATA_DIR = Path(_e("DATA_DIR") or BASE_DIR)
MEDIA_ROOT = DATA_DIR / "media"
TMP_VERIFICHE_DIR = DATA_DIR / "tmp_verifiche"

# Sessioni su database con una cache davanti: le letture non costano un giro verso il database remoto
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
# Tutti i servizi locali stanno su 127.0.0.1 e i cookie non distinguono le porte: nomi propri per non sovrascriversi
SESSION_COOKIE_NAME = "lnc_sessione"
CSRF_COOKIE_NAME = "lnc_csrf"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Accesso SPID/CIE: il sito parla con il servizio apps/spid (SDK OpenID Connect) tramite un token firmato
SPID_SERVIZIO_URL = os.environ.get("SPID_SERVIZIO_URL") or _env.get("SPID_SERVIZIO_URL", "")
SPID_BRIDGE_SECRET = os.environ.get("SPID_BRIDGE_SECRET") or _env.get("SPID_BRIDGE_SECRET", "")
SPID_CIE_ATTIVO = bool(SPID_SERVIZIO_URL and SPID_BRIDGE_SECRET)
SPID_AMBIENTE_PROVA = (os.environ.get("SPID_AMBIENTE_PROVA") or _env.get("SPID_AMBIENTE_PROVA", "1")) == "1"  # 0 solo con l'adesione reale

# Fornitore dei controlli IA (modulo con il contratto di core/services/ia/__init__.py). Oggi solo il simulato.
IA_BACKEND = os.environ.get("IA_BACKEND") or _env.get("IA_BACKEND", "core.services.ia.simulato")
# Verifica del documento: «auto» usa i controlli veri (Tesseract + OpenCV, core/services/ia/documento_reale.py) se disponibili, altrimenti il simulato
IA_DOCUMENTO = _e("IA_DOCUMENTO", "auto")   # auto | reale | simulato

# IA con OpenRouter (piano gratuito: docs/piano_ia_openrouter.md). I modelli sono in ordine di preferenza (identificativi separati da virgola)
OPENROUTER_API_KEY = _e("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1"
IA_MODELLI_TESTO = [m.strip() for m in _e("IA_MODELLI_TESTO", "recursive/flint-v1.0:free").split(",") if m.strip()]
IA_MODELLI_VISIONE = [m.strip() for m in _e("IA_MODELLI_VISIONE", "dots-studio/dots-3-note-preview:free").split(",") if m.strip()]
IA_MAX_TOKEN_TESTO, IA_MAX_TOKEN_VISIONE = 2000, 6000   # i modelli «ragionano»: con pochi token la risposta resta vuota
IA_TIMEOUT_RICHIESTA = 90          # secondi (12-40 s tipici)
IA_TIMEOUT_VISIONE = 150           # con le foto il modello ci mette fino a 40-60 s
IA_INTERVALLO_MIN = 4              # secondi tra due richieste: 20 al minuto è il limite, qui ne facciamo al massimo 15
IA_QUOTA_GIORNALIERA = 50          # richieste al giorno del piano gratuito (si azzera a mezzanotte UTC)
IA_QUOTA_SEGNALAZIONI, IA_QUOTA_COMMENTI = 36, 8   # il resto (6) è la riserva
IA_QUOTA_SOGLIA_COMMENTI = 44      # oltre questo totale l'IA lavora solo sulle segnalazioni
# Come si eseguono i controlli: «sincrona» = come prima (simulato, subito); «coda» = prefiltro locale e poi coda in background con il modello
IA_MODALITA = _e("IA_MODALITA", "sincrona")
IA_LAVORATORE = _e("IA_LAVORATORE", "0") == "1" and not os.environ.get("LNC_PROVE")   # avvia il lavoratore dentro il processo del sito
IA_COMMENTI_BLOCCO = 25            # commenti in una sola richiesta
IA_COMMENTI_MINIMO, IA_COMMENTI_ATTESA_ORE = 10, 6   # un blocco parte con almeno 10 commenti o quando il più vecchio ha più di 6 ore
IA_ATTESA_MASSIMA_ORE = 24         # oltre questo tempo senza esito la segnalazione passa a «dubbio»

# Email: con EMAIL_HOST in .env si usa un server SMTP vero; senza, escono sulla console del server (solo sviluppo)
EMAIL_HOST = _e("EMAIL_HOST")
# API di Gmail (HTTPS): per gli hosting che bloccano l'SMTP in uscita (Render gratuito). Ha la precedenza sull'SMTP.
GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN = _e("GMAIL_CLIENT_ID"), _e("GMAIL_CLIENT_SECRET"), _e("GMAIL_REFRESH_TOKEN")
GMAIL_API_ATTIVA = bool(GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN) and not os.environ.get("LNC_PROVE")
EMAIL_BACKEND = ("core.email_backend.GmailApiBackend" if GMAIL_API_ATTIVA
                 else "core.email_smtp.SmtpSicuro" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend")
if os.environ.get("LNC_PROVE") == "1":   # prove automatiche (smoke/): mai email vere, anche se nel .env ci sono le credenziali
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_SALTA_INDIRIZZI_RISERVATI = not os.environ.get("LNC_PROVE")   # niente email verso example.org e simili (indirizzi inventati: rimbalzano)
EMAIL_PORT = int(_e("EMAIL_PORT", "587"))
EMAIL_HOST_USER = _e("EMAIL_USER")
EMAIL_HOST_PASSWORD = _e("EMAIL_PASSWORD")
if os.environ.get("LNC_PROVE"):   # le prove parlano solo con il finto server locale: niente credenziali vere
    EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = ""
EMAIL_USE_SSL = _e("EMAIL_SSL", "0") == "1"                 # porta 465
EMAIL_USE_TLS = not EMAIL_USE_SSL and _e("EMAIL_TLS", "1") == "1"  # porta 587 (STARTTLS)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = _e("EMAIL_FROM", "La Nostra Città <noreply@insiemepermilano.example>")
# Il mittente deve essere «Nome <indirizzo>»: se in EMAIL_FROM manca l'indirizzo (errore di configurazione frequente) si usa quello dell'account
if "@" not in parseaddr(DEFAULT_FROM_EMAIL)[1]:
    DEFAULT_FROM_EMAIL = f"La Nostra Città <{EMAIL_HOST_USER or 'noreply@insiemepermilano.example'}>"
SITE_URL = _e("SITE_URL")  # es. https://lanostracitta.example : usato nei link delle email (obbligatorio in produzione)
