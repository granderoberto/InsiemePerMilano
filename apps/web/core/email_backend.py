"""Invio delle email con l'API di Gmail (HTTPS, porta 443).

Serve dove l'SMTP in uscita è bloccato (per esempio i servizi gratuiti di Render, che bloccano le porte 25, 465 e 587).
Usa un token OAuth «di aggiornamento» (refresh token) creato una volta con `tools/email/ottieni_token_gmail.py`:
niente password dell'account, solo il permesso di inviare messaggi (scope gmail.send). Impostazioni: GMAIL_CLIENT_ID,
GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN."""
import base64
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)
_token = {"valore": None, "scade": 0.0}


class ErroreGmailApi(Exception):
    pass


def _richiesta(url, dati=None, intestazioni=None, timeout=15):
    corpo = None if dati is None else (dati if isinstance(dati, bytes) else json.dumps(dati).encode())
    req = urllib.request.Request(url, data=corpo, headers=intestazioni or {}, method="POST" if corpo is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        dettaglio = e.read()[:300].decode("utf-8", "replace")
        raise ErroreGmailApi(f"{url.split('/')[2]} ha risposto {e.code}: {dettaglio}") from e
    except urllib.error.URLError as e:
        raise ErroreGmailApi(f"connessione a {url.split('/')[2]} non riuscita: {e.reason}") from e


def access_token():
    """Token di accesso valido (si rinnova da solo con il refresh token)."""
    if _token["valore"] and time.time() < _token["scade"] - 60:
        return _token["valore"]
    r = _richiesta(getattr(settings, "GMAIL_TOKEN_URL", "https://oauth2.googleapis.com/token"),
                   urllib.parse.urlencode({"client_id": settings.GMAIL_CLIENT_ID, "client_secret": settings.GMAIL_CLIENT_SECRET,
                                           "refresh_token": settings.GMAIL_REFRESH_TOKEN, "grant_type": "refresh_token"}).encode(),
                   {"Content-Type": "application/x-www-form-urlencoded"})
    if "access_token" not in r:
        raise ErroreGmailApi("risposta senza access_token: il refresh token potrebbe essere scaduto o revocato")
    _token["valore"], _token["scade"] = r["access_token"], time.time() + int(r.get("expires_in", 3600))
    return _token["valore"]


class GmailApiBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        inviati = 0
        for m in email_messages:
            try:
                grezzo = base64.urlsafe_b64encode(m.message().as_bytes()).decode()
                _richiesta(getattr(settings, "GMAIL_SEND_URL", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"),
                           {"raw": grezzo}, {"Authorization": "Bearer " + access_token(), "Content-Type": "application/json"})
                inviati += 1
            except ErroreGmailApi:
                _token["valore"] = None   # al prossimo tentativo si chiede un token nuovo
                log.exception("Invio con l'API di Gmail non riuscito")
                if not self.fail_silently:
                    raise
        return inviati
