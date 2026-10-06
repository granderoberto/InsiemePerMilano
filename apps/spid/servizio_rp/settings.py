"""Servizio SPID/CIE: Relying Party OpenID Connect (SDK spid-cie-oidc-django) con un «ponte» verso il sito.

Configurazione da variabili d'ambiente o dal file `.env` della radice del repository. Valori per l'ambiente di prova
ufficiale (federazione di test dell'SDK): vedi demo/ e README. Per la produzione servono l'adesione di un ente a SPID e
CIE, le chiavi e la configurazione di federazione dell'RP (README, «Passare alla produzione»)."""
import os
from pathlib import Path

import aiohttp

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent.parent


def _leggi_env():
    env, f = {}, REPO_ROOT / ".env"
    if f.exists():
        for riga in f.read_text().splitlines():
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                env[k.strip()] = v.strip()
    return env


_env = _leggi_env()
e = lambda k, d="": os.environ.get(k) or _env.get(k, d)

DEBUG = e("SPID_DEBUG", "1") == "1"
SECRET_KEY = e("SPID_SECRET_KEY", "solo-sviluppo-servizio-spid")
ALLOWED_HOSTS = e("SPID_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
ADMIN_PATH = e("SPID_ADMIN_PATH", "admin-spid/")
APPEND_SLASH = False

# --- ponte verso il sito -------------------------------------------------------------------------
SITO_URL = e("SPID_SITO_URL", "http://127.0.0.1:8000").rstrip("/")   # dove rimandare l'utente con l'identità
PONTE_SEGRETO = e("SPID_BRIDGE_SECRET")                                 # condiviso con il sito: firma il token
PONTE_SCADENZA_SECONDI = 120

# --- federazione OpenID Connect (SPID e CIE) -----------------------------------------------------
OIDCFED_DEFAULT_TRUST_ANCHOR = e("SPID_TRUST_ANCHOR", "http://127.0.0.1:8010")
OIDCFED_TRUST_ANCHORS = [OIDCFED_DEFAULT_TRUST_ANCHOR]
OIDCFED_REQUIRED_TRUST_MARKS = []
# identity provider raggiungibili. In produzione: l'elenco degli IdP SPID e l'IdP CIE (entity id) dalla federazione.
PROVIDER_SPID = e("SPID_PROVIDER_SPID", "http://127.0.0.1:8012/oidc/op")
PROVIDER_CIE = e("SPID_PROVIDER_CIE", "http://127.0.0.1:8012/oidc/op")
OIDCFED_IDENTITY_PROVIDERS = {
    "spid": {PROVIDER_SPID: OIDCFED_DEFAULT_TRUST_ANCHOR},
    "cie": {PROVIDER_CIE: OIDCFED_DEFAULT_TRUST_ANCHOR},
}
HTTPC_PARAMS = {
    "connection": {"ssl": e("SPID_VERIFICA_SSL", "0") == "1"},   # in produzione: 1
    "session": {"timeout": aiohttp.ClientTimeout(total=8)},
}

# Dati richiesti all'IdP (oltre a quelli essenziali dell'SDK): la data di nascita serve per l'età minima di 14 anni
RP_REQUIRED_CLAIMS = {
    "id_token": {"given_name": {"essential": True}, "email": {"essential": True}},
    "userinfo": {"given_name": None, "family_name": None, "email": None, "birthdate": None,
                 "https://attributes.eid.gov.it/fiscal_number": None},
}
RP_ATTR_MAP = {
    "sub": ("sub",),
    "username": ({"func": "spid_cie_oidc.relying_party.processors.issuer_prefixed_sub", "kwargs": {"sep": "__"}},),
    "first_name": ("given_name", "given_name"),
    "last_name": ("family_name", "last_name"),
    "email": ("email", "email"),
    "birthdate": ("birthdate", "birthdate"),
    "fiscal_number": ("https://attributes.eid.gov.it/fiscal_number", "fiscal_number"),
}

SPID_SCELTA_IDP = e("SPID_SCELTA_IDP", "0") == "1"   # produzione: l'utente sceglie il proprio gestore SPID da un elenco
LOGIN_REDIRECT_URL = "/ponte/consegna/"      # dopo il login: l'SDK manda qui, il ponte consegna l'identità al sito
LOGOUT_REDIRECT_URL = "/oidc/rp/landing"
LOGIN_URL = "/oidc/rp/landing"

AUTH_USER_MODEL = "spid_cie_oidc_accounts.User"   # utenti «ombra» dell'SDK: nessun dato resta oltre la consegna
INSTALLED_APPS = [
    "spid_cie_oidc.accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bootstrap_italia_template",
    "spid_cie_oidc.entity",
    "spid_cie_oidc.authority",
    "spid_cie_oidc.relying_party",
    "djagger",
    "ponte",
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
# Tutti i servizi girano su 127.0.0.1 e i cookie non distinguono le porte: nomi diversi per non sovrascriversi
SESSION_COOKIE_NAME = "spid_rp_sessione"
CSRF_COOKIE_NAME = "spid_rp_csrf"
SESSION_COOKIE_SAMESITE = "Lax"   # il ritorno dall'IdP è una navigazione di primo livello: Lax basta e protegge

ROOT_URLCONF = "servizio_rp.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "servizio_rp.wsgi.application"

# Database PROPRIO del servizio (regola 5 di CLAUDE.md: un progetto Django per database). In sviluppo: SQLite.
if e("SPID_DB_ENGINE", "sqlite") == "mysql":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql", "NAME": e("SPID_DB_NAME", "la_nostra_citta_spid"),
        "HOST": e("DB_HOST"), "PORT": e("DB_PORT"), "USER": e("DB_USER"), "PASSWORD": e("DB_PASSWORD"),
        "OPTIONS": {"charset": "utf8mb4", "ssl": {"ca": str(REPO_ROOT / "certs" / "ca.pem")}, "ssl_mode": "VERIFY_IDENTITY"}}}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static_raccolti"

(BASE_DIR / "logs").mkdir(exist_ok=True)
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"default": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"},
                 "file": {"class": "logging.handlers.TimedRotatingFileHandler", "filename": str(BASE_DIR / "logs" / "servizio.log"),
                          "when": "midnight", "backupCount": 30, "formatter": "default"}},
    "loggers": {"spid_cie_oidc": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
                "ponte": {"handlers": ["console", "file"], "level": "INFO", "propagate": False}},
}
