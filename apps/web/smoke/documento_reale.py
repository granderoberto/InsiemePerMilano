"""Verifica vera del documento: OCR, MRZ, confronto dei dati, validità, volti. Usa documenti sintetici (smoke/_documenti.py)."""
import os, sys, datetime, time, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from smoke import _documenti as D
from core.services.ia import documento_reale as R, mrz
from PIL import ImageFilter
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
esito("Tesseract, OpenCV e i modelli sono disponibili", R.disponibile())
dati = {"nome": "Mario", "cognome": "Rossi", "data_nascita": datetime.date(1990, 3, 15), "tipo_documento": "carta_identita"}
def prova(nome, fr, re_, se, d=None, atteso=None, cond=None):
    t = time.time(); r = R.verifica_documento(D.blocco(D.jpeg(fr)), D.blocco(D.jpeg(re_)) if re_ is not None else None, D.blocco(D.jpeg(se)), d or dati)
    ok = (atteso is None or r["esito"] == atteso) and (cond is None or cond(r))
    esito(nome, ok, f"{r['esito']} {r['punteggio']} {int(time.time() - t)}s | " + ", ".join(k[3:] for k, v in r["flag"].items() if not v) + (" | " + r["motivo"] if r["motivo"] and not ok else ""))
    return r
r = prova("documento in regola e selfie della stessa persona: approvata", D.fronte(), D.retro(), D.selfie(), atteso="approvata")
esito("tutti e cinque i controlli superati, punteggio 100", all(r["flag"].values()) and r["punteggio"] == 100)
prova("cognome diverso da quello del modulo: da rivedere, dati non corrispondono", D.fronte(cognome="BIANCHI"), D.retro(cognome="BIANCHI"), D.selfie(), cond=lambda r: not r["flag"]["ok_corrispondenza_dati"] and r["esito"] != "approvata")
prova("data di nascita diversa: i dati non corrispondono", D.fronte(nascita="16.03.1990"), D.retro(nascita="900316"), D.selfie(), cond=lambda r: not r["flag"]["ok_corrispondenza_dati"] and r["esito"] != "approvata")
prova("documento scaduto: validità non superata, mai approvata", D.fronte(scadenza="14.02.2019"), D.retro(scadenza="190214"), D.selfie(), cond=lambda r: not r["flag"]["ok_validita"] and r["esito"] != "approvata")
prova("codici di controllo della MRZ sbagliati: autenticità non superata", D.fronte(), D.retro(rovina=True), D.selfie(), cond=lambda r: not r["flag"]["ok_autenticita"] and r["esito"] != "approvata")
prova("foto del documento sfocata: lettura non riuscita", D.fronte().filter(ImageFilter.GaussianBlur(9)), D.retro().filter(ImageFilter.GaussianBlur(9)), D.selfie(), cond=lambda r: not r["flag"]["ok_lettura_ocr"] and r["esito"] != "approvata")
prova("selfie senza volto: rifiutata", D.fronte(), D.retro(), D.senza_volto(), atteso="rifiutata")
r = R.verifica_documento((b"%PDF-1.4 x", "pdf", None), None, D.blocco(D.jpeg(D.selfie())), dati); esito("un PDF non si può leggere: rifiutata con messaggio chiaro", r["esito"] == "rifiutata" and "JPG o PNG" in (r["motivo"] or ""))
# volto diverso: si simula una somiglianza bassa (non ci sono due volti diversi tra i dati di prova)
orig = R._somiglianza
R._somiglianza = lambda *a: 0.10; prova("volto che non somiglia: confronto non superato, mai approvata", D.fronte(), D.retro(), D.selfie(), cond=lambda r: not r["flag"]["ok_confronto_volto"] and r["esito"] != "approvata")
R._somiglianza = lambda *a: 0.34; prova("somiglianza dubbia: va a un moderatore, non è rifiutata", D.fronte(), D.retro(), D.selfie(), cond=lambda r: r["esito"] == "da_rivedere" or r["punteggio"] >= 50)
R._somiglianza = orig
# MRZ in sé
t = mrz.costruisci_td1("CA12345AB", "900315", "350214", "MARIO", "ROSSI"); m = mrz.leggi(t)
esito("MRZ TD1 valida: 4 codici su 4, date lette", m["controlli_ok"] == 4 and m["nascita"] == datetime.date(1990, 3, 15) and m["scadenza"] == datetime.date(2035, 2, 14))
m2 = mrz.leggi(mrz.costruisci_td3("YA1234567", "900315", "330214", "MARIA", "BIANCHI")); esito("MRZ TD3 (passaporto) valida: 5 codici su 5", m2["controlli_ok"] == 5)
esito("MRZ con una cifra sbagliata: i codici lo segnalano", mrz.leggi(t.replace("900315", "900316"))["controlli_ok"] < 4)
