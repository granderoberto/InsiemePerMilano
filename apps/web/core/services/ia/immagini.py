"""Prepara le foto e i video di una segnalazione per il modello con visione (docs/piano_ia_openrouter.md, fase 3).

Per ogni segnalazione al massimo 5 immagini da 768 px: le foto in ordine, dei video 2 fotogrammi (a 25% e 70%).
Prima dell'invio:
  - i volti si sfocano in locale (YuNet di OpenCV, lo stesso modello della verifica del documento);
  - il testo scritto nelle foto si legge in locale (Tesseract) e si restituisce a parte: passa dal prefiltro e dal modello.
Se mancano OpenCV, i modelli o Tesseract le foto partono lo stesso (l'autore ha accettato l'invio a un fornitore esterno)
e la mancanza finisce nel registro («volti_non_sfocati»). Nessun file esce dal sito: il modello riceve solo le immagini ridotte."""
import base64
import io
import logging
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

from core.services import archivio_media

from . import documento_reale

log = logging.getLogger(__name__)
LATO = 768
MAX_IMMAGINI = 5
MAX_OCR = 300          # caratteri di testo letto da tenere per foto
MIN_CONFIDENZA_OCR = 75  # Tesseract: sotto questa sicurezza (0-100) la parola si scarta
FRAMMENTI_VIDEO = (0.25, 0.70)


def _file(percorso):
    """Il file sul disco; se manca lo si ripristina dall'archivio nel database."""
    f = (Path(settings.MEDIA_ROOT) / percorso).resolve()
    if not f.is_file() and archivio_media.ripristina(percorso):
        f = (Path(settings.MEDIA_ROOT) / percorso).resolve()
    return f if f.is_file() and Path(settings.MEDIA_ROOT).resolve() in f.parents else None


def volti_disponibili():
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return documento_reale.YUNET.is_file()


def sfoca_volti(img):
    """img: array BGR di OpenCV. -> (img, numero di volti sfocati)."""
    import cv2
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(documento_reale.YUNET), "", (w, h), 0.6, 0.3, 5000)
    _, volti = det.detect(img)
    if volti is None:
        return img, 0
    for x, y, fw, fh, *_ in volti:
        x0, y0 = max(int(x - fw * 0.15), 0), max(int(y - fh * 0.25), 0)
        x1, y1 = min(int(x + fw * 1.15), w), min(int(y + fh * 1.15), h)
        if x1 > x0 and y1 > y0:
            zona = img[y0:y1, x0:x1]
            k = max(int(min(x1 - x0, y1 - y0) / 3) | 1, 5)
            img[y0:y1, x0:x1] = cv2.GaussianBlur(zona, (k, k), 0)
    return img, len(volti)


def _leggi_testo(img):
    """Testo ben leggibile nella foto (cartelli, scritte), o "". Si tengono solo le parole che Tesseract legge con sicurezza:
    una foto qualsiasi produce molto rumore («Sr ANS SNS Bre») che non deve arrivare né al prefiltro né al modello."""
    import cv2, pytesseract
    h, w = img.shape[:2]
    grigio = cv2.cvtColor(cv2.resize(img, (1200, int(h * 1200 / w))), cv2.COLOR_BGR2GRAY)
    cfg = f'--tessdata-dir "{documento_reale.MODELLI / "tessdata"}" --psm 11'
    try:
        d = pytesseract.image_to_data(grigio, lang="ita+eng", config=cfg, output_type=pytesseract.Output.DICT, timeout=40)
    except Exception:  # noqa: BLE001
        log.exception("IA: OCR della foto non riuscito")
        return ""
    parole = [t for t, c in zip(d["text"], d["conf"]) if len(t) >= 2 and sum(x.isalnum() for x in t) >= 2 and float(c) >= MIN_CONFIDENZA_OCR]
    return " ".join(parole)[:MAX_OCR] if any(len(t) >= 4 for t in parole) else ""


def _a_data_url(img_bgr):
    import cv2
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def _carica(path):
    """File immagine → array BGR ridotto a LATO px, con la rotazione EXIF applicata."""
    import numpy as np
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((LATO, LATO))
    return np.array(im)[:, :, ::-1].copy()


def _fotogramma(path, frazione, durata):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "f.jpg"
        t = max((durata or 2) * frazione, 0)
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                        "-vf", f"scale='min({LATO},iw)':-2", str(out)], capture_output=True, timeout=60, check=True)
        return _carica(out)


def prepara(media):
    """media: elenco di `Media` della segnalazione. -> dict:
       immagini   [(id del media, ordine, data URL)]            quelle da inviare
       ocr        {id del media: testo letto}                   solo foto con testo
       volti      numero di volti sfocati
       senza_file [id dei media non leggibili]
       note       [segnali tecnici per il registro]"""
    r = {"immagini": [], "ocr": {}, "volti": 0, "senza_file": [], "note": []}
    sfoca = volti_disponibili()
    ocr = documento_reale.disponibile()
    if not sfoca:
        r["note"].append("volti_non_sfocati")
    for m in media:
        if len(r["immagini"]) >= MAX_IMMAGINI:
            break
        f = _file(m.percorso)
        if f is None:
            r["senza_file"].append(m.id)
            continue
        try:
            if m.tipo == "video":
                quadri = [_fotogramma(f, fr, m.durata_sec) for fr in FRAMMENTI_VIDEO[:MAX_IMMAGINI - len(r["immagini"])]]
            else:
                quadri = [_carica(f)]
        except Exception:  # noqa: BLE001 - file illeggibile: si segnala e si va avanti
            log.exception("IA: media %s non leggibile", m.id)
            r["senza_file"].append(m.id)
            continue
        for q in quadri:
            if m.tipo != "video" and ocr:
                testo = _leggi_testo(q)
                if testo:
                    r["ocr"][m.id] = testo
            if sfoca:
                try:
                    q, n = sfoca_volti(q)
                    r["volti"] += n
                except Exception:  # noqa: BLE001
                    log.exception("IA: sfocatura dei volti non riuscita")
                    r["note"].append("volti_non_sfocati")
            r["immagini"].append((m.id, m.ordine, _a_data_url(q)))
    return r
