"""Router dei fornitori di modelli per i controlli IA (docs/piano_ia_openrouter.md, «Multi-fornitore»).

Una sola funzione, `chiedi`, che manda una richiesta al primo fornitore utilizzabile della catena e restituisce un JSON già controllato.
La catena è un elenco di coppie (fornitore, modello) in ordine di preferenza, separato per il testo e per la visione: le richieste
con foto vanno solo ai fornitori con un modello con visione. Regole:
  - si passa alla coppia successiva solo per errori che NON consumano quota (404 privacy, 403, 429 «a monte» di OpenRouter, rete);
  - un 429 del fornitore stesso lo mette da parte (30 minuti) e si prova col fornitore successivo, senza nuovi tentativi;
    se tutti i fornitori sono senza quota si solleva `QuotaEsaurita`;
  - su errore del server o scadenza si riprova UNA volta lo stesso modello, poi si passa al successivo;
  - una risposta vuota o con JSON sbagliato ha consumato quota: nessun altro modello (`RispostaNonValida`);
  - le richieste sono distanziate secondo il limite al minuto di ogni fornitore e ognuna finisce nel registro;
  - un fornitore senza chiave è «non configurato»: si salta, non è un errore. Se non resta nessuno: `NessunModello`.
La privacy (OpenRouter: `data_collection = "deny"`) è nel corpo della richiesta. Il testo dell'utente va sempre nel messaggio `user`."""
import json
import logging
import re
import threading
import time
from dataclasses import dataclass

from django.conf import settings

from . import fornitori, quota, trasporto

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
    istradato_da: str | None   # il sottofornitore che ha risposto, se il fornitore lo dice (OpenRouter)
    fornitore: str = ""        # nome del fornitore della nostra catena (openrouter, groq, …)


_blocco = threading.Lock()
_ultima = {}             # nome fornitore -> istante dell'ultima richiesta
_dormi = time.sleep      # sostituibili nelle prove
_orologio = time.monotonic


def _ritmo(f):
    """Attende il tempo minimo dall'ultima richiesta a questo fornitore (in tutto il processo): 60 / richieste al minuto."""
    if not settings.IA_INTERVALLO_MIN:   # nelle prove si azzera
        return
    intervallo = 60 / max(fornitori.limiti(f)["rpm"], 1)
    with _blocco:
        manca = _ultima.get(f.nome, -1e9) + intervallo - _orologio()
        if manca > 0:
            _dormi(manca)
        _ultima[f.nome] = _orologio()


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
def _adatta_immagini(utente, massimo):
    """Se il messaggio ha più immagini di quante ne accetta il fornitore, tiene le prime (con l'etichetta che le precede)."""
    if not isinstance(utente, list):
        return utente
    n, out, trattenute = 0, [], 0
    for i, p in enumerate(utente):
        if p.get("type") == "image_url":
            if trattenute >= massimo:
                if out and out[-1].get("type") == "text" and out[-1].get("text", "").startswith("<foto"):
                    out.pop()   # l'etichetta della foto scartata
                continue
            trattenute += 1
        out.append(p)
    return out


def _corpo(f, modello, sistema, utente, schema, max_token):
    istruzioni = sistema + " Rispondi solo con un oggetto JSON conforme a questo schema: " + json.dumps(schema, ensure_ascii=False)
    corpo = {"model": modello, "temperature": 0, f.campo_token: max_token,
             "messages": [{"role": "system", "content": istruzioni}, {"role": "user", "content": _adatta_immagini(utente, f.max_immagini)}]}
    if f.json_object:
        corpo["response_format"] = {"type": "json_object"}
    corpo.update(dict(f.privacy))
    return corpo


def _messaggio_errore(d):
    e = d.get("error") if isinstance(d, dict) else None
    if isinstance(d, dict) and not e and isinstance(d.get("errors"), list) and d["errors"]:   # Cloudflare
        e = d["errors"][0]
    return json.dumps(e, ensure_ascii=False) if e else ""


MOTIVO_429 = "limite di richieste raggiunto presso i fornitori"


def chiedi(tipo, sistema, utente, schema, *, max_token, visione=False, timeout=None, catena=None):
    """Manda la richiesta al primo fornitore utilizzabile della catena.

    tipo: «segnalazione» o «commento» (serve al registro e alla quota). utente: testo, oppure l'elenco di parti del messaggio
    (testo e immagini) nel formato OpenAI. visione=True usa la catena con visione. `catena` (prove e confronti): elenco di
    (fornitore o nome, modello) al posto di quella configurata.
    -> Risposta. Solleva QuotaEsaurita, NessunModello, RispostaNonValida."""
    esplicito = bool(catena)
    cat = [((fornitori.FORNITORI[f] if isinstance(f, str) else f), m) for f, m in catena] if catena else fornitori.catena(visione)
    if not cat:
        raise NessunModello("nessun fornitore configurato")
    ultimo, senza_quota, altri_errori, scartati = "nessun tentativo", [], False, set()
    for f, modello in cat:
        if not fornitori.configurato(f, esplicito):
            ultimo = f"{f.nome}: {fornitori.motivo_non_configurato(f, esplicito)}"
            continue
        if f.nome in senza_quota or f.nome in scartati:
            continue
        ammesso, motivo = quota.ammesso_da(f, tipo)
        if not ammesso:
            senza_quota.append(f.nome)
            ultimo = f"{f.nome}: {motivo}"
            continue
        for tentativo in (1, 2):
            _ritmo(f)
            t0 = time.monotonic()
            try:
                codice, d = trasporto.http("POST", fornitori.url_base(f) + "/chat/completions", fornitori.chiave(f),
                                           _corpo(f, modello, sistema, utente, schema, max_token),
                                           timeout=timeout or settings.IA_TIMEOUT_RICHIESTA)
            except OSError as e:  # include TimeoutError e gli errori di rete
                quota.registra_richiesta(tipo, f, modello, 0, time.monotonic() - t0, False, type(e).__name__)
                ultimo, altri_errori = f"{f.nome} {modello}: {type(e).__name__}", True
                continue  # un solo nuovo tentativo, poi il modello successivo
            sec = time.monotonic() - t0
            errore = _messaggio_errore(d)
            if codice == 200 and errore:  # alcuni fornitori rispondono 200 con l'errore nel corpo
                codice = (d.get("error") or {}).get("code") or 502
                codice = codice if isinstance(codice, int) else 502
            if codice == 200:
                quota.registra_richiesta(tipo, f, modello, 200, sec, True)
                dati = _estrai(d)
                if dati is None or (err := valida(dati, schema)):
                    fine = ((d.get("choices") or [{}])[0].get("finish_reason") if isinstance(d, dict) else None) or "?"
                    log.warning("IA: risposta di %s/%s non valida (%s, finish=%s)", f.nome, modello, "JSON assente" if dati is None else err, fine)
                    raise RispostaNonValida(f"{f.nome} {modello}: " + (f"JSON assente o vuoto (finish={fine})" if dati is None else err))
                return Risposta(dati, modello, sec, (d.get("usage") or {}).get("total_tokens"), d.get("provider"), f.nome)
            quota.registra_richiesta(tipo, f, modello, codice, sec, False, errore)
            ultimo = f"{f.nome} {modello}: HTTP {codice}"
            if codice == 429 and (f.nome != "openrouter" or "upstream" not in errore):
                quota.segna_esaurito(f)   # il limite è il nostro con questo fornitore: si passa al successivo
                senza_quota.append(f.nome)
                break
            if codice in (401, 402):
                ultimo, altri_errori = f"{f.nome}: chiave non accettata (HTTP {codice})", True
                scartati.add(f.nome)   # inutile riprovare con altri modelli dello stesso fornitore
                break
            altri_errori = True
            if codice in (403, 404, 429) or codice < 500:
                break  # non consuma quota: subito il modello successivo
            # errore del server: un nuovo tentativo, poi il modello successivo
    if senza_quota and not altri_errori:   # nessuno ha risposto e il motivo è solo la quota
        raise QuotaEsaurita(MOTIVO_429)
    raise NessunModello("nessun modello ha risposto (" + ultimo + ")")
