"""Client di OpenRouter per i modelli gratuiti (docs/piano_ia_openrouter.md, fase 1).

Una sola funzione, `chiedi`, che manda una richiesta e restituisce un JSON già controllato. Regole:
  - la catena di modelli passa al successivo solo per errori che NON consumano quota (404 privacy, 403, 429 «a monte»);
  - un 429 della nostra quota ferma tutto (`QuotaEsaurita`), nessun nuovo tentativo;
  - su errore del server o scadenza si riprova UNA volta lo stesso modello, poi si passa al successivo;
  - una risposta vuota o con JSON sbagliato ha consumato quota: nessun altro modello (`RispostaNonValida`);
  - le richieste sono distanziate (IA_INTERVALLO_MIN) e ognuna finisce nel registro;
  - la privacy è sempre `data_collection = "deny"`: nessun addestramento sui dati.
Il testo dell'utente va sempre nel messaggio `user`, mai nelle istruzioni."""
import json
import logging
import re
import threading
import time
from dataclasses import dataclass

from django.conf import settings

from . import quota, trasporto

log = logging.getLogger(__name__)


class ErroreIA(Exception):
    """Base: il controllo non è riuscito; chi chiama deve ricadere su `dubbio`."""


class QuotaEsaurita(ErroreIA):
    pass


class NessunModello(ErroreIA):
    pass


class RispostaNonValida(ErroreIA):
    pass


@dataclass
class Risposta:
    dati: dict
    modello: str
    secondi: float
    token: int | None
    fornitore: str | None


_blocco = threading.Lock()
_ultima = [0.0]
_dormi = time.sleep      # sostituibili nelle prove
_orologio = time.monotonic


def _ritmo():
    """Attende il tempo minimo dall'ultima richiesta (in tutto il processo)."""
    with _blocco:
        manca = _ultima[0] + settings.IA_INTERVALLO_MIN - _orologio()
        if manca > 0:
            _dormi(manca)
        _ultima[0] = _orologio()


# ---------------------------------------------------------------- controllo del JSON
def valida(dato, schema, percorso="$"):
    """Sottoinsieme di JSON Schema che ci serve: object, array, integer, boolean, string, required, additionalProperties, maxLength, enum.
    -> None se valido, altrimenti il testo del primo errore."""
    t = schema.get("type")
    if t == "object":
        if not isinstance(dato, dict):
            return f"{percorso}: atteso un oggetto"
        for k in schema.get("required", []):
            if k not in dato:
                return f"{percorso}: manca «{k}»"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(dato) - set(props):
            return f"{percorso}: campi non previsti {sorted(set(dato) - set(props))}"
        for k, sub in props.items():
            if k in dato and (e := valida(dato[k], sub, f"{percorso}.{k}")):
                return e
    elif t == "array":
        if not isinstance(dato, list):
            return f"{percorso}: atteso un elenco"
        for i, x in enumerate(dato):
            if e := valida(x, schema.get("items", {}), f"{percorso}[{i}]"):
                return e
    elif t == "integer":
        if isinstance(dato, bool) or not isinstance(dato, int):
            return f"{percorso}: atteso un intero"
    elif t == "number":
        if isinstance(dato, bool) or not isinstance(dato, (int, float)):
            return f"{percorso}: atteso un numero"
    elif t == "boolean":
        if not isinstance(dato, bool):
            return f"{percorso}: atteso true o false"
    elif t == "string":
        if not isinstance(dato, str):
            return f"{percorso}: atteso un testo"
        if len(dato) > schema.get("maxLength", 10 ** 9):
            return f"{percorso}: testo troppo lungo"
    if "enum" in schema and dato not in schema["enum"]:
        return f"{percorso}: valore non ammesso"
    return None


def _estrai(risposta):
    try:
        t = risposta["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return None
    m = re.search(r"\{.*\}", t, re.S)  # il modello a volte avvolge il JSON in testo o in ```
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


# ---------------------------------------------------------------- richiesta
def _corpo(modello, sistema, utente, schema, max_token):
    istruzioni = sistema + " Rispondi solo con un oggetto JSON conforme a questo schema: " + json.dumps(schema, ensure_ascii=False)
    return {"model": modello, "temperature": 0, "max_tokens": max_token,
            "messages": [{"role": "system", "content": istruzioni}, {"role": "user", "content": utente}],
            "response_format": {"type": "json_object"}, "provider": {"data_collection": "deny"}}


def _messaggio_errore(d):
    e = d.get("error") if isinstance(d, dict) else None
    return json.dumps(e, ensure_ascii=False) if e else ""


def chiedi(tipo, sistema, utente, schema, *, modelli, max_token):
    """Manda la richiesta al primo modello utilizzabile della catena.

    tipo: «segnalazione» o «commento» (serve al registro e alla quota). utente: testo, oppure l'elenco di parti del messaggio
    (testo e immagini) nel formato di OpenRouter. -> Risposta. Solleva QuotaEsaurita, NessunModello, RispostaNonValida."""
    if not settings.OPENROUTER_API_KEY:
        raise NessunModello("chiave OpenRouter non impostata")
    if not modelli:
        raise NessunModello("nessun modello configurato")
    ultimo = "nessun tentativo"
    for modello in modelli:
        for tentativo in (1, 2):
            _ritmo()
            t0 = time.monotonic()
            try:
                codice, d = trasporto.http("POST", "/chat/completions", _corpo(modello, sistema, utente, schema, max_token),
                                           timeout=settings.IA_TIMEOUT_RICHIESTA)
            except OSError as e:  # include TimeoutError e gli errori di rete
                quota.registra_richiesta(tipo, modello, 0, time.monotonic() - t0, False, type(e).__name__)
                ultimo = f"{modello}: {type(e).__name__}"
                continue  # un solo nuovo tentativo, poi il modello successivo
            sec = time.monotonic() - t0
            errore = _messaggio_errore(d)
            if codice == 200 and errore:  # alcuni fornitori rispondono 200 con l'errore nel corpo
                codice = (d.get("error") or {}).get("code") or 502
                codice = codice if isinstance(codice, int) else 502
            if codice == 200:
                quota.registra_richiesta(tipo, modello, 200, sec, True)
                dati = _estrai(d)
                if dati is None or (err := valida(dati, schema)):
                    log.warning("IA: risposta di %s non valida (%s)", modello, "JSON assente" if dati is None else err)
                    raise RispostaNonValida(f"{modello}: " + ("JSON assente o vuoto" if dati is None else err))
                return Risposta(dati, modello, sec, (d.get("usage") or {}).get("total_tokens"), d.get("provider"))
            quota.registra_richiesta(tipo, modello, codice, sec, False, errore)
            ultimo = f"{modello}: HTTP {codice}"
            if codice == 429 and "upstream" not in errore:
                raise QuotaEsaurita(MOTIVO_429)
            if codice in (401, 402):
                raise NessunModello(f"chiave OpenRouter non accettata (HTTP {codice})")
            if codice in (403, 404, 429):
                break  # non consuma quota: subito il modello successivo
            if codice < 500:
                break
            # errore del server: un nuovo tentativo, poi il modello successivo
    raise NessunModello("nessun modello ha risposto (" + ultimo + ")")


MOTIVO_429 = "limite di richieste di OpenRouter raggiunto"
