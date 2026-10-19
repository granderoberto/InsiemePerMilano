"""Crea un FAC-SIMILE di carta d'identità (dati inventati, foto della NASA di pubblico dominio) per provare la verifica del documento.
Non è un documento valido: porta la scritta «FAC-SIMILE». Uso: apps/web/.venv/bin/python tools/demo/documento_prova.py
Uscita (non versionata): apps/web/prova_documento/{fronte.jpg, retro.jpg, selfie_da_inquadrare.jpg, LEGGIMI.txt}"""
import pathlib, sys
RADICE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "apps" / "web"))
from PIL import ImageDraw
from smoke import _documenti as D

uscita = RADICE / "apps" / "web" / "prova_documento"
uscita.mkdir(exist_ok=True)


def filigrana(im, testo="FAC-SIMILE · DOCUMENTO DI PROVA · NON VALIDO"):
    d = ImageDraw.Draw(im)
    d.text((60, 950), testo, font=D.font("sans", 36), fill=(200, 40, 40))
    return im


filigrana(D.fronte()).save(uscita / "fronte.jpg", quality=93)
filigrana(D.retro()).save(uscita / "retro.jpg", quality=93)
# primo piano del volto (il selfie deve mostrare un volto grande), da inquadrare con la fotocamera
D.volto().crop((110, 10, 410, 410)).resize((900, 1200)).save(uscita / "selfie_da_inquadrare.jpg", quality=93)
(uscita / "LEGGIMI.txt").write_text("""Documento di PROVA (inventato, non valido) per la verifica dell'identità

Dati da usare nella registrazione:
  Nome:            Mario
  Cognome:         Rossi
  Data di nascita: 15/03/1990

Come provare:
  1. Registrati con questi dati (email tua, per esempio un alias Gmail: tuonome+prova@gmail.com) e conferma l'email.
  2. Profilo → «Verifica la mia identità».
  3. Fronte e retro: carica fronte.jpg e retro.jpg di questa cartella (tipo: carta d'identità).
  4. Selfie: si scatta SOLO con la fotocamera della pagina. Apri selfie_da_inquadrare.jpg su un secondo schermo (telefono o altro
     computer) e inquadralo con la fotocamera, tenendo il volto grande e ben illuminato; poi premi «Scatta».
  5. Con tutto in regola deve risultare «Identità verificata».

Prove di fallimento: cambia il cognome o la data nella registrazione (deve andare in revisione), oppure inquadra
un altro volto o niente (selfie rifiutato).
""", encoding="utf-8")
print("creato in", uscita)
