"""Documenti normativi: ultima versione per tipo e consensi ancora da dare."""
from core.models import Consenso, DocumentoNormativo


def ultime_versioni():
    ultimi = {}
    for d in DocumentoNormativo.objects.all().order_by("id"):  # id crescente = pubblicazione crescente
        ultimi[d.tipo] = d
    return ultimi


def da_accettare(utente):
    """Documenti (ultima versione di ogni tipo) che l'utente non ha ancora accettato.
    Il consenso biometrico riguarda solo chi ha fatto il confronto del selfie: chi si è registrato con le credenziali
    e ha una verifica d'identità (non SPID/CIE, non l'amministratore creato all'installazione)."""
    accettati = set(Consenso.objects.filter(utente=utente).values_list("documento_id", flat=True))
    out = []
    for tipo, d in ultime_versioni().items():
        if d.id in accettati:
            continue
        if tipo == "biometrici" and (utente.metodo_registrazione != "credenziali" or not utente.verifiche.exists()):
            continue
        out.append(d)
    return out
