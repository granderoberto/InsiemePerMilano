"""Documenti d'identità SINTETICI per le prove (nessun documento vero): carta d'identità con foto, dati e MRZ valida."""
import io, sys, datetime, importlib.util, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_spec = importlib.util.spec_from_file_location("mrz", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "services", "ia", "mrz.py"))
mrz = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(mrz)

def font(nome, dim):
    for p in ({"sans": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
               "mono": ["/System/Library/Fonts/Supplemental/Courier New Bold.ttf", "/System/Library/Fonts/Supplemental/Courier New.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]}[nome]):
        if os.path.exists(p): return ImageFont.truetype(p, dim)
    return ImageFont.load_default(dim)

def volto():
    from skimage import data
    return Image.fromarray(data.astronaut())

def jpeg(im, q=92):
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=q); return b.getvalue()

def blocco(dati, tipo="jpeg", dim=None):
    im = Image.open(io.BytesIO(dati)); return (dati, tipo, im.size)

def fronte(cognome="ROSSI", nome="MARIO", nascita="15.03.1990", scadenza="14.02.2035"):
    im = Image.new("RGB", (1600, 1010), (232, 238, 244)); d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 1580, 990], outline=(30, 60, 110), width=6)
    d.text((60, 50), "REPUBBLICA ITALIANA  -  CARTA DI IDENTITA", font=font("sans", 54), fill=(20, 40, 90))
    im.paste(volto().resize((460, 460)), (80, 200))
    y = 200
    for etichetta, valore in (("COGNOME / SURNAME", cognome), ("NOME / NAME", nome), ("NATO IL / DATE OF BIRTH", nascita), ("SCADENZA / EXPIRY", scadenza)):
        d.text((600, y), etichetta, font=font("sans", 34), fill=(90, 90, 90)); d.text((600, y + 40), valore, font=font("sans", 66), fill=(0, 0, 0)); y += 170
    return im

def retro(cognome="ROSSI", nome="MARIO", nascita="900315", scadenza="350214", numero="CA12345AB", rovina=False):
    im = Image.new("RGB", (1600, 1010), (240, 238, 230)); d = ImageDraw.Draw(im)
    d.text((60, 60), "COMUNE DI MILANO  -  CODICE FISCALE RSSMRA90C15F205X", font=font("sans", 42), fill=(40, 40, 40))
    testo = mrz.costruisci_td1(numero, nascita, scadenza, nome, cognome)
    if rovina: testo = testo.replace(nascita, nascita[:-1] + ("0" if nascita[-1] != "0" else "1"), 1)
    for i, r in enumerate(testo.splitlines()):
        d.text((60, 640 + i * 110), r, font=font("mono", 74), fill=(0, 0, 0))
    return im

def selfie(rotazione=6, scala=0.85):
    v = volto(); w, h = v.size; base = Image.new("RGB", (900, 1200), (150, 160, 170))
    v2 = v.resize((int(w * scala * 1.5), int(h * scala * 1.5))).rotate(rotazione, expand=True, fillcolor=(150, 160, 170))
    base.paste(v2, ((900 - v2.size[0]) // 2, (1200 - v2.size[1]) // 2)); return base

def senza_volto():
    im = Image.new("RGB", (900, 1200), (120, 150, 120)); ImageDraw.Draw(im).rectangle([200, 300, 700, 900], fill=(200, 200, 90)); return im
