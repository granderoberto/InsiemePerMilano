"""Token firmati e a scadenza per link nelle email (conferma, recupero password, cambio email).
Non servono tabelle: la firma usa SECRET_KEY e il contenuto del token."""
import hashlib

from django.core import signing

ORE = {"conferma": 72, "reset": 2, "email": 48}


def impronta_password(utente) -> str:
    """Il token di reset si invalida da solo appena la password cambia."""
    return hashlib.sha256((utente.password or "").encode()).hexdigest()[:16]


def crea(scopo, utente, extra=None):
    dati = {"s": scopo, "u": utente.id, "x": extra}
    if scopo == "reset":
        dati["p"] = impronta_password(utente)
    return signing.dumps(dati, salt=f"lnc-{scopo}")


def leggi(token, scopo):
    """-> dict con 'u' ed 'x' se valido, altrimenti None."""
    try:
        d = signing.loads(token, salt=f"lnc-{scopo}", max_age=ORE[scopo] * 3600)
    except signing.BadSignature:
        return None
    return d if d.get("s") == scopo else None
