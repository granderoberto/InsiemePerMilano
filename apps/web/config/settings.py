"""Impostazioni del progetto web (sviluppo locale).

Il database è quello di Aiven: credenziali da `.env` nella radice del repository, database da DJANGO_DB_NAME
(default: la_nostra_citta_test). Lo schema del dominio è gestito dalle migrazioni SQL (db/migrations/),
non da Django: vedi la regola di convivenza in CLAUDE.md.
"""
import os
import tempfile
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
ALLOWED_HOSTS = [h.strip() for h in _e("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _e("DJANGO_CSRF_ORIGINS").split(",") if o.strip()]  # es. https://lanostracitta.example

if not DEBUG:
    # dietro il proxy dell'hosting: HTTPS già terminato, lo dichiara l'intestazione X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _e("DJANGO_SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(_e("DJANGO_HSTS_SECONDS", "3600"))  # alzare a 31536000 quando tutto funziona
    SECURE_REDIRECT_EXEMPT = [r"^salute/$"]  # il controllo di stato dell'hosting arriva in HTTP
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
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
SIMULAZIONE_VERIFICA_DOCUMENTO = IA_BACKEND.endswith(".simulato")

# Email: con EMAIL_HOST in .env si usa un server SMTP vero; senza, escono sulla console del server (solo sviluppo)
EMAIL_HOST = _e("EMAIL_HOST")
EMAIL_BACKEND = ("django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend")
EMAIL_PORT = int(_e("EMAIL_PORT", "587"))
EMAIL_HOST_USER = _e("EMAIL_USER")
EMAIL_HOST_PASSWORD = _e("EMAIL_PASSWORD")
EMAIL_USE_SSL = _e("EMAIL_SSL", "0") == "1"                 # porta 465
EMAIL_USE_TLS = not EMAIL_USE_SSL and _e("EMAIL_TLS", "1") == "1"  # porta 587 (STARTTLS)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = _e("EMAIL_FROM", "La Nostra Città <noreply@insiemepermilano.example>")
SITE_URL = _e("SITE_URL")  # es. https://lanostracitta.example : usato nei link delle email (obbligatorio in produzione)
