"""Lettura sicura di documento e selfie caricati in registrazione.
Non ci si fida di estensione né tipo dichiarato dal browser: si guardano i primi byte e, per le immagini, si decodifica davvero."""
import io

from PIL import Image

MAX_BYTE = 5 * 1024 * 1024          # 5 MB per lato (par. 3.2)
MAX_PIXEL = 40_000_000              # contro le immagini «bomba» che esauriscono la memoria
FIRME = {b"\xff\xd8\xff": "jpeg", b"\x89PNG\r\n\x1a\n": "png", b"%PDF-": "pdf"}


class FileNonValido(Exception):
    pass


def leggi(file, nome: str, ammetti_pdf=True):
    """-> (bytes, tipo 'jpeg'|'png'|'pdf', (larghezza, altezza) o None). Solleva FileNonValido con un messaggio per l'utente."""
    if file.size > MAX_BYTE:
        raise FileNonValido(f"{nome}: il file supera 5 MB.")
    dati = file.read()
    tipo = next((t for firma, t in FIRME.items() if dati.startswith(firma)), None)
    if tipo is None or (tipo == "pdf" and not ammetti_pdf):
        raise FileNonValido(f"{nome}: formato non ammesso (" + ("JPG, PNG o PDF" if ammetti_pdf else "JPG o PNG") + ").")
    if tipo == "pdf":
        return dati, tipo, None
    try:
        img = Image.open(io.BytesIO(dati))
        larghezza, altezza = img.size
        if larghezza * altezza > MAX_PIXEL:
            raise FileNonValido(f"{nome}: l'immagine è troppo grande.")
        img.load()
    except FileNonValido:
        raise
    except Exception:
        raise FileNonValido(f"{nome}: l'immagine è danneggiata o non valida.")
    return dati, tipo, (larghezza, altezza)
