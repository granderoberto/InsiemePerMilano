"""Interfaccia unica verso i controlli di intelligenza artificiale (docs/architettura_ia.md, «Gateway IA»).

Il resto del sito chiama solo queste funzioni; non sa quale fornitore c'è dietro. Il fornitore si sceglie con
`IA_BACKEND` nelle impostazioni (modulo che espone le stesse quattro funzioni). Oggi c'è solo quello simulato.

Contratto:
  controlla_testo(testo)                              -> (esito, punteggio_rischio 0-1)      esito: ok | dubbio | bloccato
  suggerisci_categorie(titolo, descrizione)           -> [(nome_categoria, confidenza 0-1)]
  coerenza_immagine_testo(titolo, descrizione, n)     -> punteggio 0-1 (1 = coerente)
  verifica_documento(fronte, selfie)                  -> {flag, punteggio 0-100, esito, motivo}   esito: approvata | da_rivedere | rifiutata

Se il fornitore non risponde, l'esito è `dubbio` («controllo non disponibile»): nel dubbio decide una persona, mai il silenzio.
"""
import logging
from importlib import import_module

from django.conf import settings

log = logging.getLogger(__name__)

MOTIVO_NON_DISPONIBILE = "Controllo automatico non disponibile"


def _backend():
    return import_module(getattr(settings, "IA_BACKEND", "core.services.ia.simulato"))


def controlla_testo(testo: str):
    try:
        return _backend().controlla_testo(testo)
    except Exception:
        log.exception("IA: controlla_testo non riuscito")
        return "dubbio", 0.5


def suggerisci_categorie(titolo: str, descrizione: str):
    try:
        return _backend().suggerisci_categorie(titolo, descrizione)
    except Exception:
        log.exception("IA: suggerisci_categorie non riuscito")
        return []  # nessun suggerimento: l'utente sceglie a mano


def coerenza_immagine_testo(titolo: str, descrizione: str, n_media: int):
    try:
        return _backend().coerenza_immagine_testo(titolo, descrizione, n_media)
    except Exception:
        log.exception("IA: coerenza_immagine_testo non riuscito")
        return 0.5


def verifica_documento(fronte, selfie):
    try:
        return _backend().verifica_documento(fronte, selfie)
    except Exception:
        log.exception("IA: verifica_documento non riuscito")
        flag = {k: False for k in ("ok_lettura_ocr", "ok_corrispondenza_dati", "ok_validita", "ok_autenticita", "ok_confronto_volto")}
        return {"flag": flag, "punteggio": 50, "esito": "da_rivedere", "motivo": MOTIVO_NON_DISPONIBILE}
