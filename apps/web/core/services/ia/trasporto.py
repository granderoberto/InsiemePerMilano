"""Chiamate HTTP verso i fornitori (solo libreria standard + certificati aggiornati). Separato per poterlo sostituire nelle prove."""
import json
import ssl
import urllib.error
import urllib.request

try:
    import certifi
    _CONTESTO = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    _CONTESTO = ssl.create_default_context()


def http(metodo, url, chiave, corpo=None, timeout=30, intestazioni=None):
    """-> (codice, dati). Non solleva per gli errori HTTP; per rete e scadenze solleva OSError/TimeoutError.
    La chiave va solo nell'intestazione di autorizzazione: mai nei log, mai nell'indirizzo."""
    dati = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dati, method=metodo)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + chiave)
    req.add_header("User-Agent", "LaNostraCitta/1.0")   # alcuni fornitori (Cloudflare) rifiutano l'agente predefinito di Python
    req.add_header("X-Title", "La Nostra Citta")
    for k, v in (intestazioni or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CONTESTO) as r:
            codice, testo = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        codice, testo = e.code, e.read().decode("utf-8", "replace")
    try:
        return codice, json.loads(testo)
    except ValueError:
        return codice, {"error": {"message": testo[:300]}}
