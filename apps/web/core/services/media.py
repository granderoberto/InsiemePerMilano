import io
import json
import subprocess
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

from . import archivio_media

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


MAX_PIXEL = 60_000_000      # oltre, l'immagine è troppo grande da elaborare (una foto da 48 MP ne ha 48 milioni)
MAX_LATO = 2400             # le foto si riducono: bastano per lo schermo e pesano molto meno
Image.MAX_IMAGE_PIXELS = MAX_PIXEL


def rimuovi(percorso: str) -> None:
    """Toglie un file dal disco e dall'archivio nel database."""
    (Path(settings.MEDIA_ROOT) / percorso).unlink(missing_ok=True)
    archivio_media.elimina(percorso)


def _pulisci_foto(file, nome):
    """Apre la foto, applica la rotazione dell'EXIF, la porta in sRGB, la riduce e scarta ogni metadato (GPS compreso)."""
    img = Image.open(file)
    img.verify()
    file.seek(0)
    img = Image.open(file)
    if img.width * img.height > MAX_PIXEL:
        raise MediaNonValido(f"«{nome}»: l'immagine è troppo grande (massimo 60 megapixel).")
    profilo = img.info.get("icc_profile")
    img = ImageOps.exif_transpose(img)
    if profilo:
        try:
            from PIL import ImageCms
            img = ImageCms.profileToProfile(img.convert("RGB"), ImageCms.ImageCmsProfile(io.BytesIO(profilo)), ImageCms.createProfile("sRGB"))
        except Exception:  # noqa: BLE001 - profilo illeggibile: si tengono i colori com'erano
            pass
    img.thumbnail((MAX_LATO, MAX_LATO))
    return img     # un'immagine nuova, salvata più sotto senza EXIF né profilo


def _ha_video(path: Path) -> bool:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=30, check=True).stdout
        return "video" in out
    except Exception:  # noqa: BLE001
        return False


def salva(file):
    """Valida e salva un file caricato. Rimuove i metadati (EXIF) dalle foto prima di pubblicarle.
    Restituisce un dict con i campi della tabella `media`."""
    ext = Path(file.name).suffix.lower()
    if ext in FOTO:
        if file.size > MAX_FOTO:
            raise MediaNonValido(f"«{file.name}»: la foto supera 10 MB.")
        try:
            img = _pulisci_foto(file, file.name)
        except MediaNonValido:
            raise
        except Exception as e:  # noqa: BLE001
            raise MediaNonValido(f"«{file.name}»: immagine non valida.") from e
        nome = f"{uuid.uuid4().hex}{'.png' if ext == '.png' else '.jpg'}"
        dest = _cartella() / nome
        try:
            if ext == ".png":
                img.save(dest, "PNG", optimize=True)
            else:
                img.convert("RGB").save(dest, "JPEG", quality=86, optimize=True, progressive=True)
        except Exception as e:  # noqa: BLE001
            dest.unlink(missing_ok=True)
            raise MediaNonValido(f"«{file.name}»: non riesco a salvare l'immagine.") from e
        percorso = str(dest.relative_to(settings.MEDIA_ROOT))
        archivio_media.salva(percorso, dest)
        return dict(tipo="foto", mime="image/png" if ext == ".png" else "image/jpeg", dimensione=dest.stat().st_size, durata=None, percorso=percorso)
    if ext in VIDEO:
        if file.size > MAX_VIDEO:
            raise MediaNonValido(f"«{file.name}»: il video supera 50 MB.")
        grezzo = _cartella() / f"{uuid.uuid4().hex}{ext}"
        with open(grezzo, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        try:
            if not _ha_video(grezzo):
                raise MediaNonValido(f"«{file.name}»: non è un video valido.")
            durata = _durata_video(grezzo)
            if not 1 <= durata <= 60:
                raise MediaNonValido(f"«{file.name}»: il video deve durare al massimo 60 secondi.")
        except MediaNonValido:
            grezzo.unlink(missing_ok=True)
            raise
        pulito = grezzo.with_name(grezzo.stem + "_p" + ext)  # niente metadati (posizione, dispositivo): ffmpeg se disponibile
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(grezzo), "-map_metadata", "-1", "-c", "copy", "-movflags", "+faststart", str(pulito)],
                           check=True, timeout=120)
            grezzo.unlink(missing_ok=True)
            grezzo = pulito
        except Exception:  # noqa: BLE001
            pulito.unlink(missing_ok=True)
        percorso = str(grezzo.relative_to(settings.MEDIA_ROOT))
        archivio_media.salva(percorso, grezzo)
        return dict(tipo="video", mime=VIDEO[ext], dimensione=grezzo.stat().st_size, durata=durata, percorso=percorso)
    raise MediaNonValido(f"«{file.name}»: formato non ammesso (foto JPG, PNG o HEIC; video MP4 o MOV).")
