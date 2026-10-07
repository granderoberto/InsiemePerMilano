import os

from django.conf import settings


def _versione_css():
    """Cambia a ogni modifica di un file di stile o di script: il browser non usa versioni vecchie dalla cache."""
    try:
        radice = settings.BASE_DIR / "static"
        return int(max(os.path.getmtime(f) for sotto in ("css", "js") for f in (radice / sotto).glob("*.*")))
    except (OSError, ValueError):
        return 0


def sito(request):
    non_lette = 0
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated:
        non_lette = u.notifiche.filter(letta=False).count()
    return {
        "versione_css": _versione_css(),
        "notifiche_non_lette": non_lette,
        "SPID_CIE_ATTIVO": settings.SPID_CIE_ATTIVO,
        "SPID_AMBIENTE_PROVA": settings.SPID_AMBIENTE_PROVA,
        "SIMULAZIONE_VERIFICA_DOCUMENTO": settings.SIMULAZIONE_VERIFICA_DOCUMENTO,
    }
