"""Quota giornaliera di ogni fornitore (docs/piano_ia_openrouter.md, «Multi-fornitore»).

Ogni fornitore ha limiti e contatore propri (`fornitori.limiti`). Il conteggio viene dal registro (`log_attivita`, una riga per
richiesta, con `tabella` = nome del fornitore: le righe di OpenRouter già presenti hanno tabella «openrouter») e, dove esiste, dal
contatore ufficiale (OpenRouter: `GET /key`). Vale il maggiore dei due. Le richieste senza risposta (404, 403, 429) non contano.
Ripartizione di ogni fornitore: segnalazioni 72%, commenti 16%, riserva 12%; oltre l'88% i commenti aspettano.
Il giorno di tutti i fornitori finisce a mezzanotte UTC (Cloudflare lo dichiara; per gli altri è un'ipotesi, perciò un 429 del
fornitore lo mette da parte per 30 minuti invece che fino a mezzanotte)."""
import logging
import time
from datetime import datetime, timedelta, timezone

from core.models import LogAttivita
from core.services import log as registro

from . import fornitori, trasporto

log = logging.getLogger(__name__)
TABELLA = "openrouter"   # compatibilità: nome del fornitore storico
MOTIVO_ESAURITA = "quota IA giornaliera esaurita"
_cache = {}      # nome -> {"scade": monotonic, "usate": int|None}
_esauriti = {}   # nome -> monotonic fino a cui il fornitore è messo da parte dopo un suo 429


def inizio_giorno_utc():
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def registra_richiesta(tipo, fornitore, modello, codice, secondi, contata, errore=""):
    """Una riga di registro per ogni richiesta fatta a un fornitore (tabella = nome del fornitore)."""
    nome = fornitore if isinstance(fornitore, str) else fornitore.nome
    registro.registra(None, "decisione_ia", nome, 0, None, {"tipo": tipo, "fornitore": nome, "modello": modello, "http": codice,
                                                            "secondi": round(secondi, 1), "contata": bool(contata), "errore": errore[:120]})
    c = _cache.get(nome)
    if contata and c and c["usate"] is not None:
        c["usate"] += 1


def _righe(f, tipo=None):
    qs = LogAttivita.objects.filter(tabella=f.nome, operazione="decisione_ia", avvenuto_il__gte=inizio_giorno_utc(), dati_nuovi__contata=True)
    return qs.filter(dati_nuovi__tipo=tipo) if tipo else qs


def usate_locali(f=None, tipo=None):
    """Richieste contate oggi per un fornitore (predefinito: OpenRouter, come prima)."""
    return _righe(f or fornitori.FORNITORI["openrouter"], tipo).count()


def usate_ufficiali(f=None, forza=False):
    """Richieste usate oggi secondo il fornitore, o None se non c'è un contatore o non è raggiungibile. Valore tenuto 60 secondi."""
    f = f or fornitori.FORNITORI["openrouter"]
    if not f.contatore_ufficiale or not fornitori.chiave(f):
        return None
    c = _cache.get(f.nome)
    if not forza and c and time.monotonic() < c["scade"]:
        return c["usate"]
    try:
        codice, d = trasporto.http("GET", fornitori.url_base(f) + "/key", fornitori.chiave(f), timeout=10)
        u = d["data"]["free_model_daily_requests"]["used"] if codice == 200 else None
    except Exception:  # noqa: BLE001
        log.warning("Quota IA: contatore ufficiale di %s non raggiungibile, uso il registro locale", f.nome)
        u = None
    _cache[f.nome] = {"scade": time.monotonic() + 60, "usate": u}
    return u


def stato(f=None, forza=False):
    """{fornitore, etichetta, usate, limite, rimaste, ufficiale, segnalazioni, commenti, limiti} per il pannello e per le decisioni."""
    f = f or fornitori.FORNITORI["openrouter"]
    lim = fornitori.limiti(f)
    ufficiale = usate_ufficiali(f, forza)
    usate = max(usate_locali(f), ufficiale or 0)
    return {"fornitore": f.nome, "etichetta": f.etichetta, "usate": usate, "limite": lim["rpd"], "rimaste": max(lim["rpd"] - usate, 0),
            "ufficiale": ufficiale, "segnalazioni": usate_locali(f, "segnalazione"), "commenti": usate_locali(f, "commento"), "limiti": lim,
            "configurato": fornitori.configurato(f), "motivo": fornitori.motivo_non_configurato(f), "nota_dati": f.nota_dati,
            "messo_da_parte": _esauriti.get(f.nome, 0) > time.monotonic()}


def stato_tutti(forza=False):
    return [stato(f, forza) for f in fornitori.FORNITORI.values()]


def segna_esaurito(f, minuti=30):
    """Il fornitore ha risposto con un suo 429: si prova col successivo e si riprova con questo tra `minuti`."""
    _esauriti[f.nome] = time.monotonic() + minuti * 60


def ammesso_da(f, tipo):
    """-> (si/no, motivo): il fornitore ha ancora quota per questo tipo di lavoro? `tipo`: «segnalazione» o «commento»."""
    if _esauriti.get(f.nome, 0) > time.monotonic():
        return False, f"{f.etichetta}: messo da parte dopo un suo limite"
    s = stato(f)
    lim = s["limiti"]
    if s["usate"] >= lim["rpd"]:
        return False, MOTIVO_ESAURITA
    if tipo == "segnalazione":
        if s["segnalazioni"] >= lim["segnalazioni"]:
            return False, "quota IA segnalazioni esaurita"
        return True, ""
    if tipo == "commento":
        if s["usate"] >= lim["soglia"] or s["commenti"] >= lim["commenti"]:
            return False, "quota IA commenti esaurita"
        return True, ""
    raise ValueError(tipo)


def ammesso(tipo):
    """-> (si/no, motivo): almeno un fornitore della catena può fare questo lavoro. Le segnalazioni hanno foto: serve la visione."""
    cat = fornitori.catena(visione=(tipo == "segnalazione"))
    if not cat:
        return False, "nessun fornitore configurato"
    motivo = MOTIVO_ESAURITA
    for f in dict.fromkeys(f for f, _ in cat):
        ok, m = ammesso_da(f, tipo)
        if ok:
            return True, ""
        motivo = m
    return False, motivo


def azzera_cache():
    _cache.clear()
    _esauriti.clear()
