"""Autenticazione a due fattori con app di autenticazione (TOTP, RFC 6238).

Il segreto non si salva mai in chiaro: si cifra con una chiave derivata da SECRET_KEY (Fernet).
Se SECRET_KEY cambia, i segreti esistenti non si leggono più: l'amministratore deve azzerare la 2FA degli utenti."""
import base64
import hashlib
import io

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

EMITTENTE = "La Nostra Città"


def _fernet():
    chiave = base64.urlsafe_b64encode(hashlib.sha256(("mfa|" + settings.SECRET_KEY).encode()).digest())
    return Fernet(chiave)


def nuovo_segreto() -> str:
    return pyotp.random_base32()


def cifra(segreto: str) -> str:
    return _fernet().encrypt(segreto.encode()).decode()


def decifra(cifrato: str):
    try:
        return _fernet().decrypt(cifrato.encode()).decode()
    except InvalidToken:
        return None


def uri_provisioning(utente, segreto: str) -> str:
    return pyotp.TOTP(segreto).provisioning_uri(name=utente.email, issuer_name=EMITTENTE)


def qr_svg(uri: str) -> str:
    """Il codice QR come SVG da inserire nella pagina (nessun servizio esterno: il segreto non esce dal server)."""
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


def codice_valido(segreto: str, codice: str) -> bool:
    codice = (codice or "").replace(" ", "").strip()
    return codice.isdigit() and len(codice) == 6 and pyotp.TOTP(segreto).verify(codice, valid_window=1)  # ±30 s di tolleranza


def verifica_utente(utente, codice: str) -> bool:
    if not utente.mfa_attiva or not utente.mfa_segreto:
        return False
    segreto = decifra(utente.mfa_segreto)
    return bool(segreto) and codice_valido(segreto, codice)
