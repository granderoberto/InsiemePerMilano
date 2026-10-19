"""Verifica VERA del documento d'identità, eseguita sul nostro server (nessun servizio esterno, nessuna immagine esce).

Cinque controlli (par. 3.3 della specifica):
- lettura (OCR): Tesseract legge il testo del documento; si controlla anche la nitidezza della foto;
- corrispondenza dei dati: nome, cognome e data di nascita del modulo devono comparire nel documento (confronto «sfocato»);
- validità: scadenza non superata e, se c'è la zona a lettura ottica (MRZ), codici di controllo corretti;
- autenticità: controlli di coerenza (foto del volto sul documento, MRZ coerente con il testo, selfie diverso dalla foto);
  NON è una perizia: l'autenticità vera richiede lettura dei sistemi di sicurezza del documento, quindi i casi dubbi vanno a un moderatore;
- volto: confronto tra la foto del documento e il selfie con il modello SFace di OpenCV (YuNet trova i volti).

Il punteggio 0-100 pesa i controlli; le soglie (85 e 50) sono quelle della specifica."""
import datetime
import difflib
import logging
import re
import shutil
import unicodedata
from pathlib import Path

from django.conf import settings

log = logging.getLogger(__name__)

MODELLI = Path(settings.BASE_DIR) / "modelli"
YUNET, SFACE = MODELLI / "face_detection_yunet_2023mar.onnx", MODELLI / "face_recognition_sface_2021dec.onnx"
PESI = {"ok_lettura_ocr": 20, "ok_corrispondenza_dati": 25, "ok_validita": 15, "ok_autenticita": 15, "ok_confronto_volto": 25}
SOGLIA_VOLTO, SOGLIA_VOLTO_DUBBIO = 0.40, 0.30     # coseno SFace: ≥0,363 è la soglia «stessa persona» del modello; qui si è un po' più severi
NITIDEZZA_MIN = 45.0                                # varianza del laplaciano
MOTIVI = {
    "ok_lettura_ocr": "Documento non leggibile: foto troppo piccola, sfocata o storta",
    "ok_corrispondenza_dati": "I dati del documento non corrispondono a quelli inseriti",
    "ok_validita": "Documento scaduto o scadenza e codici di controllo non verificabili",
    "ok_autenticita": "Non si riconoscono gli elementi attesi di un documento (foto del volto, codici coerenti)",
    "ok_confronto_volto": "Il volto nel selfie non corrisponde alla foto del documento",
}


def disponibile() -> bool:
    try:
        import cv2, numpy, pytesseract  # noqa: F401, E401
    except ImportError:
        return False
    return bool(shutil.which("tesseract")) and YUNET.is_file() and SFACE.is_file() and (MODELLI / "tessdata" / "ita.traineddata").is_file()


# ----------------------------------------------------------------- immagini e OCR
def _decodifica(blocco):
    import cv2, numpy as np
    dati, tipo, _ = blocco
    if tipo == "pdf":
        return None
    return cv2.imdecode(np.frombuffer(dati, np.uint8), cv2.IMREAD_COLOR)


def _nitidezza(img) -> float:
    import cv2
    grigio = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ridotto = cv2.resize(grigio, (1000, int(1000 * grigio.shape[0] / grigio.shape[1])))
    return float(cv2.Laplacian(ridotto, cv2.CV_64F).var())


def _ocr(img, larghezza=1800, psm=6, lang="ita+eng", extra="") -> str:
    import cv2, pytesseract
    h, w = img.shape[:2]
    if w != larghezza:
        img = cv2.resize(img, (larghezza, int(h * larghezza / w)), interpolation=cv2.INTER_CUBIC if w < larghezza else cv2.INTER_AREA)
    grigio = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    cfg = f'--tessdata-dir "{MODELLI / "tessdata"}" --psm {psm} {extra}'
    try:
        return pytesseract.image_to_string(grigio, lang=lang, config=cfg, timeout=40)
    except Exception:  # noqa: BLE001 - OCR non riuscito o troppo lento: testo vuoto, il controllo di lettura fallirà
        log.exception("OCR non riuscito")
        return ""


def _ocr_mrz(img) -> str:
    """La MRZ sta in basso: si rilegge solo quella fascia con l'alfabeto ristretto."""
    h = img.shape[0]
    fascia = img[int(h * 0.55):, :]
    return _ocr(fascia, larghezza=2000, psm=6, lang="eng", extra="-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")


# ----------------------------------------------------------------- testo
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def _token_presenti(attesi: str, testo_norm: str) -> float:
    """Frazione dei pezzi di `attesi` (nome o cognome) trovati nel testo, anche con piccoli errori dell'OCR."""
    parole = set(testo_norm.split())
    pezzi = [p for p in _norm(attesi).split() if len(p) >= 2]
    if not pezzi:
        return 0.0
    trovati = 0
    for p in pezzi:
        if p in parole or (len(p) >= 4 and difflib.get_close_matches(p, parole, n=1, cutoff=0.82)):
            trovati += 1
    return trovati / len(pezzi)


def _date_nel_testo(testo: str) -> set:
    date_trovate = set()
    for g, m, a in re.findall(r"(?<!\d)(\d{1,2})[\s./\-](\d{1,2})[\s./\-](\d{4}|\d{2})(?!\d)", testo):
        try:
            a = int(a)
            if a < 100:
                continue
            date_trovate.add(datetime.date(a, int(m), int(g)))
        except ValueError:
            pass
    return date_trovate


def _scadenza_dal_testo(testo: str, escluse: set):
    oggi = datetime.date.today()
    candidate = sorted(d for d in _date_nel_testo(testo) if d not in escluse and d.year >= oggi.year - 15)
    return candidate[-1] if candidate else None


# ----------------------------------------------------------------- volti
def _volti(img):
    import cv2
    h, w = img.shape[:2]
    if max(h, w) < 900:
        s = 900 / max(h, w); img = cv2.resize(img, (int(w * s), int(h * s)))
        h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (w, h), 0.6, 0.3, 5000)
    _, volti = det.detect(img)
    if volti is None:
        return img, []
    return img, sorted(volti, key=lambda f: -(f[2] * f[3] * f[14]))   # il più grande e sicuro per primo


def _somiglianza(doc_img, doc_volto, selfie_img, selfie_volto) -> float:
    import cv2
    rec = cv2.FaceRecognizerSF.create(str(SFACE), "")
    a = rec.feature(rec.alignCrop(doc_img, doc_volto))
    b = rec.feature(rec.alignCrop(selfie_img, selfie_volto))
    return float(rec.match(a, b, cv2.FaceRecognizerSF_FR_COSINE))


# ----------------------------------------------------------------- verifica
def verifica_documento(fronte, retro, selfie, dati=None):
    """fronte/retro/selfie: (bytes, tipo, dimensioni) come da file_documento.leggi (retro può essere None).
    dati: {nome, cognome, data_nascita (date), tipo_documento}. -> {flag, punteggio, esito, motivo}"""
    from . import mrz as modulo_mrz
    dati = dati or {}
    flag = {k: False for k in PESI}
    parziale = 0.0
    note = []
    img_f, img_r, img_s = _decodifica(fronte), (_decodifica(retro) if retro else None), _decodifica(selfie)
    if img_f is None or (retro and img_r is None) or img_s is None:
        return _esito(flag, 0, ["Per la verifica automatica servono foto JPG o PNG (non PDF)"], forza_rifiuto=True)

    # 1) lettura
    nitida = _nitidezza(img_f) >= NITIDEZZA_MIN
    testo_f = _ocr(img_f)
    testo_r = _ocr(img_r) if img_r is not None else ""
    testo = testo_f + "\n" + testo_r
    t_norm = _norm(testo)
    flag["ok_lettura_ocr"] = nitida and len(t_norm.split()) >= 12 and min(img_f.shape[:2]) >= 500

    # 2) MRZ (carta d'identità elettronica e passaporto)
    mrz = None
    if dati.get("tipo_documento") in ("carta_identita", "passaporto", None):
        mrz = modulo_mrz.leggi(testo_r + "\n" + testo_f) or modulo_mrz.leggi(_ocr_mrz(img_r if img_r is not None else img_f))
    mrz_ok = bool(mrz) and mrz["controlli_ok"] >= mrz["controlli_tot"] - 1   # un errore dell'OCR si tollera

    # 3) corrispondenza dei dati
    nascita = dati.get("data_nascita")
    nome_ok = _token_presenti(dati.get("nome", ""), t_norm)
    cognome_ok = _token_presenti(dati.get("cognome", ""), t_norm)
    date_doc = _date_nel_testo(testo) | ({mrz["nascita"]} if mrz and mrz["nascita"] else set())
    nascita_ok = bool(nascita) and nascita in date_doc
    flag["ok_corrispondenza_dati"] = nome_ok >= 0.99 and cognome_ok >= 0.99 and nascita_ok
    if not flag["ok_corrispondenza_dati"]:
        parziale += PESI["ok_corrispondenza_dati"] * (0.35 * (nome_ok >= 0.99) + 0.35 * (cognome_ok >= 0.99) + 0.30 * nascita_ok) * 0.5

    # 4) validità
    oggi = datetime.date.today()
    scadenza = mrz["scadenza"] if mrz_ok and mrz["scadenza"] else _scadenza_dal_testo(testo, {nascita} if nascita else set())
    if scadenza is None:
        note.append("scadenza non leggibile")
    elif scadenza < oggi:
        note.append("documento scaduto")
    flag["ok_validita"] = scadenza is not None and scadenza >= oggi and (mrz_ok or not mrz)

    # 5) volto e autenticità
    img_f2, volti_doc = _volti(img_f)
    img_s2, volti_selfie = _volti(img_s)
    rifiuto_selfie = False
    similitudine = None
    if not volti_selfie:
        rifiuto_selfie = True
        note.append("nel selfie non si vede un volto")
    else:
        x, y, w, h = volti_selfie[0][:4]
        if w * h < 0.03 * img_s2.shape[0] * img_s2.shape[1]:
            note.append("nel selfie il volto è troppo piccolo")
    if volti_doc and volti_selfie:
        similitudine = _somiglianza(img_f2, volti_doc[0], img_s2, volti_selfie[0])
        flag["ok_confronto_volto"] = similitudine >= SOGLIA_VOLTO
        if not flag["ok_confronto_volto"] and similitudine >= SOGLIA_VOLTO_DUBBIO:
            parziale += PESI["ok_confronto_volto"] * 0.5
    elif not volti_doc:
        note.append("sul documento non si trova la foto del volto")
    stesso_file = fronte[0] == selfie[0]
    flag["ok_autenticita"] = bool(volti_doc) and nitida and not stesso_file and (not mrz or mrz_ok)
    if stesso_file:
        note.append("il selfie è lo stesso file del documento")

    punteggio = sum(PESI[k] for k, v in flag.items() if v) + parziale
    log.info("Verifica documento: %s similitudine=%s mrz=%s", {k: v for k, v in flag.items()}, None if similitudine is None else round(similitudine, 3), bool(mrz))
    return _esito(flag, punteggio, note, forza_rifiuto=rifiuto_selfie, scaduto=scadenza is not None and scadenza < oggi)


def _esito(flag, punteggio, note, forza_rifiuto=False, scaduto=False):
    punteggio = int(round(punteggio))
    if not all(flag.values()):
        punteggio = min(punteggio, 84)   # approvata solo se TUTTI i controlli sono superati: un dubbio va sempre a una persona
    if scaduto:
        punteggio = min(punteggio, 45)   # documento scaduto: rifiutata, l'utente può caricarne uno valido
    if forza_rifiuto:
        punteggio = min(punteggio, 36)
    esito = "approvata" if punteggio >= 85 else "da_rivedere" if punteggio >= 50 else "rifiutata"
    motivi = [MOTIVI[k] for k, v in flag.items() if not v] + [n[:1].upper() + n[1:] for n in note]
    return {"flag": flag, "punteggio": punteggio, "esito": esito, "motivo": "; ".join(dict.fromkeys(motivi)) or None}
