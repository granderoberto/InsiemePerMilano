"""Aiuti comuni ai controlli: file di prova per documento e selfie."""
import io

from PIL import Image


def immagine(lato=900, formato="JPEG", nome="x.jpg", tipo="image/jpeg"):
    from django.core.files.uploadedfile import SimpleUploadedFile
    b = io.BytesIO()
    Image.new("RGB", (lato, lato), (120, 140, 200)).save(b, formato)
    return SimpleUploadedFile(nome, b.getvalue(), content_type=tipo)


def campi_documento(fronte=900, retro=900, selfie=400, tipo="carta_identita"):
    """Campi del modulo per documento e selfie (file nuovi a ogni chiamata: un file si legge una volta sola)."""
    from portale.forms import nuova_sfida
    c = {"tipo_documento": tipo, "fronte": immagine(fronte, nome="fronte.jpg"), "selfie": immagine(selfie, nome="selfie.jpg"), "sfida": nuova_sfida()}
    if retro:
        c["retro"] = immagine(retro, nome="retro.jpg")
    return c


import uuid
SFX = uuid.uuid4().hex[:6]   # distingue le email create in questa esecuzione da quelle delle precedenti
UTENTI_DEMO_MAX_ID = 154       # gli utenti dei dati demo hanno id fino a 154: le prove ne scelgono solo tra questi
