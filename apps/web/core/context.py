from django.conf import settings


def sito(request):
    non_lette = 0
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated:
        non_lette = u.notifiche.filter(letta=False).count()
    return {
        "notifiche_non_lette": non_lette,
        "SIMULAZIONE_SPID_CIE": settings.SIMULAZIONE_SPID_CIE,
        "SIMULAZIONE_VERIFICA_DOCUMENTO": settings.SIMULAZIONE_VERIFICA_DOCUMENTO,
    }
