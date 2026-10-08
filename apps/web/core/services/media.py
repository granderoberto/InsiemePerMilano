import json
import subprocess
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

try:  # foto HEIC/HEIF (formato predefinito dell'iPhone): si convertono in JPEG
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # senza la libreria i file HEIC vengono rifiutati come immagine non valida
    pass

MAX_FOTO = 10 * 1024 * 1024
MAX_VIDEO = 50 * 1024 * 1024
FOTO = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".heic": "image/jpeg", ".heif": "image/jpeg"}  # HEIC/HEIF diventano JPEG
VIDEO = {".mp4": "video/mp4", ".mov": "video/quicktime"}


class MediaNonValido(Exception):
    pass


def _cartella():
    d = Path(settings.MEDIA_ROOT) / "media" / date.today().strftime("%Y/%m")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _durata_video(path: Path) -> int:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                             capture_output=True, text=True, timeout=30, check=True).stdout
        return int(round(float(json.loads(out)["format"]["duration"])))
    except Exception as e:  # ffprobe assente o file illeggibile
        raise MediaNonValido("Non riesco a leggere la durata del video.") from e


def salva(file):
    """Valida e salva un file caricato. Rimuove i metadati (EXIF) dalle foto prima di pubblicarle.
    Restituisce un dict con i campi della tabella `media`."""
    ext = Path(file.name).suffix.lower()
    if ext in FOTO:
        if file.size > MAX_FOTO:
            raise MediaNonValido(f"«{file.name}»: la foto supera 10 MB.")
        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)
            img = ImageOps.exif_transpose(Image.open(file))  # applica la rotazione dell'EXIF prima di toglierlo
            pulita = Image.new(img.mode, img.size)  # copia i soli pixel: via ogni metadato
            pulita.putdata(list(img.getdata()))
        except Exception as e:
            raise MediaNonValido(f"«{file.name}»: immagine non valida.") from e
        nome = f"{uuid.uuid4().hex}{'.png' if ext == '.png' else '.jpg'}"
        dest = _cartella() / nome
        if ext == ".png":
            pulita.save(dest, "PNG")
        else:
            pulita.convert("RGB").save(dest, "JPEG", quality=88)
        return dict(tipo="foto", mime=FOTO[ext], dimensione=dest.stat().st_size, durata=None,
                    percorso=str(dest.relative_to(settings.MEDIA_ROOT)))
    if ext in VIDEO:
        if file.size > MAX_VIDEO:
            raise MediaNonValido(f"«{file.name}»: il video supera 50 MB.")
        grezzo = _cartella() / f"{uuid.uuid4().hex}{ext}"
        with open(grezzo, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        try:
            durata = _durata_video(grezzo)
            if not 1 <= durata <= 60:
                raise MediaNonValido(f"«{file.name}»: il video deve durare al massimo 60 secondi.")
        except MediaNonValido:
            grezzo.unlink(missing_ok=True)
            raise
        pulito = grezzo.with_name(grezzo.stem + "_p" + ext)  # niente metadati: ffmpeg se disponibile, altrimenti file originale
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(grezzo), "-map_metadata", "-1", "-c", "copy", str(pulito)],
                           check=True, timeout=120)
            grezzo.unlink(missing_ok=True)
            grezzo = pulito
        except Exception:
            pulito.unlink(missing_ok=True)
        return dict(tipo="video", mime=VIDEO[ext], dimensione=grezzo.stat().st_size, durata=durata,
                    percorso=str(grezzo.relative_to(settings.MEDIA_ROOT)))
    raise MediaNonValido(f"«{file.name}»: formato non ammesso (foto JPG/PNG, video MP4/MOV).")
