"""Impostazioni del progetto web (sviluppo locale).

Il database è quello di Aiven: credenziali da `.env` nella radice del repository, database da DJANGO_DB_NAME
(default: la_nostra_citta_test). Lo schema del dominio è gestito dalle migrazioni SQL (db/migrations/),
non da Django: vedi la regola di convivenza in CLAUDE.md.
"""
import os
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

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-sviluppo-non-usare-in-produzione")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")

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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DJANGO_DB_NAME", "la_nostra_citta_test"),
        "HOST": _env.get("DB_HOST", "localhost"),
        "PORT": _env.get("DB_PORT", "3306"),
        "USER": _env.get("DB_USER", "root"),
        "PASSWORD": _env.get("DB_PASSWORD", ""),
        "OPTIONS": {
            "charset": "utf8mb4",
            "ssl": {"ca": str(REPO_ROOT / "certs" / "ca.pem")},
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
MEDIA_ROOT = BASE_DIR / "media"

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Simulazioni in attesa dell'SDK SPID/CIE e dei servizi IA (mostrate nel sito)
SIMULAZIONE_SPID_CIE = True
SIMULAZIONE_VERIFICA_DOCUMENTO = True
