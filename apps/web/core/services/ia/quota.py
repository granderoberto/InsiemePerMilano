"""Quota giornaliera di OpenRouter (piano gratuito: 50 richieste, azzerate a mezzanotte UTC).

Due fonti: il contatore ufficiale (`GET /key` → `free_model_daily_requests`, non consuma richieste) e il registro locale
(`log_attivita`, tabella «openrouter»). Vale il maggiore dei due: il registro non vede le richieste fatte a mano (la sonda).
Le richieste che non hanno prodotto una risposta (404, 403, 429 a monte) non consumano quota e non si contano.
Ripartizione (docs/piano_ia_openrouter.md, §2): segnalazioni 36, commenti 8, riserva 6."""
import logging
import time
from datetime import datetime, timezone

from django.conf import settings

from core.models import LogAttivita
from core.services import log as registro

from . import trasporto

log = logging.getLogger(__name__)
TABELLA = "openrouter"
MOTIVO_ESAURITA = "quota IA giornaliera esaurita"
_cache = {"scade": 0.0, "usate": None}


def inizio_giorno_utc():
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def registra_richiesta(tipo, modello, codice, secondi, contata, errore=""):
    """Una riga di registro per ogni richiesta fatta a OpenRouter."""
    registro.registra(None, "decisione_ia", TABELLA, 0, None, {"tipo": tipo, "modello": modello, "http": codice,
                                                               "secondi": round(secondi, 1), "contata": bool(contata), "errore": errore[:120]})
    if contata and _cache["usate"] is not None:
        _cache["usate"] += 1


def _righe(tipo=None):
    qs = LogAttivita.objects.filter(tabella=TABELLA, operazione="decisione_ia", avvenuto_il__gte=inizio_giorno_utc(), dati_nuovi__contata=True)
    return qs.filter(dati_nuovi__tipo=tipo) if tipo else qs


def usate_locali(tipo=None):
    return _righe(tipo).count()


def usate_ufficiali(forza=False):
    """Richieste usate oggi secondo OpenRouter, o None se non raggiungibile. Valore tenuto 60 secondi."""
    if not forza and time.monotonic() < _cache["scade"]:
        return _cache["usate"]
    try:
        codice, d = trasporto.http("GET", "/key", timeout=10)
        u = d["data"]["free_model_daily_requests"]["used"] if codice == 200 else None
    except Exception:  # noqa: BLE001
        log.warning("Quota IA: contatore ufficiale non raggiungibile, uso il registro locale")
        u = None
    _cache.update(scade=time.monotonic() + 60, usate=u)
    return u


def stato(forza=False):
    """{usate, limite, rimaste, segnalazioni, commenti, ufficiale} per il pannello amministratore e per le decisioni."""
    ufficiale = usate_ufficiali(forza)
    locali = usate_locali()
    usate = max(locali, ufficiale or 0)
    limite = settings.IA_QUOTA_GIORNALIERA
    return {"usate": usate, "limite": limite, "rimaste": max(limite - usate, 0), "ufficiale": ufficiale,
            "segnalazioni": usate_locali("segnalazione"), "commenti": usate_locali("commento")}


def ammesso(tipo):
    """-> (si/no, motivo). `tipo`: «segnalazione» o «commento»."""
    s = stato()
    if s["usate"] >= s["limite"]:
        return False, MOTIVO_ESAURITA
    if tipo == "segnalazione":
        if s["segnalazioni"] >= settings.IA_QUOTA_SEGNALAZIONI:
            return False, "quota IA segnalazioni esaurita"
        return True, ""
    if tipo == "commento":
        if s["usate"] >= settings.IA_QUOTA_SOGLIA_COMMENTI or s["commenti"] >= settings.IA_QUOTA_COMMENTI:
            return False, "quota IA commenti esaurita"
        return True, ""
    raise ValueError(tipo)


def azzera_cache():
    _cache.update(scade=0.0, usate=None)
