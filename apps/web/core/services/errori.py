from django.db import DatabaseError


class RegolaViolata(Exception):
    """Una regola imposta dal database (trigger/CHECK) ha rifiutato l'operazione."""


def traduci(e: DatabaseError) -> RegolaViolata:
    """Trigger (SQLSTATE 45000) = errno 1644 con messaggio italiano; CHECK = 3819; UNIQUE = 1062."""
    codice = e.args[0] if e.args else None
    testo = str(e.args[1]) if len(e.args) > 1 else str(e)
    if codice == 1644:
        return RegolaViolata(testo)
    if codice == 3819:
        return RegolaViolata("I dati non rispettano un vincolo del sistema.")
    if codice == 1062:
        return RegolaViolata("Esiste già un elemento uguale.")
    return RegolaViolata("Operazione non riuscita.")
