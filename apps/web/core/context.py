import os

from django.conf import settings


def _versione_css():
    """Cambia a ogni modifica del file: il browser non usa uno stile vecchio dalla cache."""
    try:
        return int(os.path.getmtime(settings.BASE_DIR / "static" / "css" / "site.css"))
    except OSError:
        return 0


def sito(request):
    non_lette = 0
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated:
        non_lette = u.notifiche.filter(letta=False).count()
    return {
        "versione_css": _versione_css(),
        "notifiche_non_lette": non_lette,
        "SIMULAZIONE_SPID_CIE": settings.SIMULAZIONE_SPID_CIE,
        "SIMULAZIONE_VERIFICA_DOCUMENTO": settings.SIMULAZIONE_VERIFICA_DOCUMENTO,
    }
