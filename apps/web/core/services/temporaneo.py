"""Area temporanea CIFRATA per documento e selfie (par. 3.3: «al termine della verifica il sistema cancella le immagini»).
I file si cifrano (Fernet) prima di toccare il disco e si eliminano appena finita la verifica, anche in caso di errore."""
import base64
import hashlib
import os
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings


def _cartella() -> Path:
    d = Path(settings.TMP_VERIFICHE_DIR)
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return d


def _fernet():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("tmp|" + settings.SECRET_KEY).encode()).digest()))


@contextmanager
def archivio():
    """with archivio() as a: a.salva(b'..') -> id; a.leggi(id). All'uscita (anche con errori) tutto viene cancellato."""
    cartella = _cartella() / uuid.uuid4().hex
    cartella.mkdir(mode=0o700)
    f = _fernet()

    class _A:
        def salva(self, dati: bytes) -> str:
            nome = uuid.uuid4().hex
            (cartella / nome).write_bytes(f.encrypt(dati))
            os.chmod(cartella / nome, 0o600)
            return nome

        def leggi(self, nome: str) -> bytes:
            return f.decrypt((cartella / nome).read_bytes())

        def percorso(self):
            return cartella

    try:
        yield _A()
    finally:
        for p in cartella.glob("*"):
            p.unlink(missing_ok=True)
        cartella.rmdir()
