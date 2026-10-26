"""Chiamate HTTP verso OpenRouter (solo libreria standard + certificati aggiornati). Separato per poterlo sostituire nelle prove."""
import json
import ssl
import urllib.error
import urllib.request

from django.conf import settings

try:
    import certifi
    _CONTESTO = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    _CONTESTO = ssl.create_default_context()


def http(metodo, percorso, corpo=None, timeout=30):
    """-> (codice, dati). Non solleva per gli errori HTTP; per rete e scadenze solleva OSError/TimeoutError."""
    dati = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(settings.OPENROUTER_URL + percorso, data=dati, method=metodo)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + settings.OPENROUTER_API_KEY)  # mai nei log
    req.add_header("X-Title", "La Nostra Citta")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CONTESTO) as r:
            codice, testo = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        codice, testo = e.code, e.read().decode("utf-8", "replace")
    try:
        return codice, json.loads(testo)
    except ValueError:
        return codice, {"error": {"message": testo[:300]}}
