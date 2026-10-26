"""Prefiltro, coda e lavoratore dei controlli IA (fase 2). Finto OpenRouter locale: nessuna richiesta vera.
Tutto in una transazione annullata alla fine."""
import os, sys, json, re, threading, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from datetime import timedelta
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from django.db import transaction
from django.test import Client, override_settings
from django.utils import timezone
import shutil, subprocess, base64, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from core.models import *
from core.services.ia import coda, controllo, lavoratore, openrouter as orr, prefiltro as pf, quota
from portale.views import crea_segnalazione
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))

# ------------------------------------------------------------------ prefiltro
def P(t, **k): return pf.analizza(t, **k)
esito("minaccia: bloccato senza modello", P("Ti ammazzo domani", tipo="commento").esito == "bloccato")
esito("insulto scritto «i d i o t a»: da inviare", P("sei un i d i o t a", tipo="commento").esito == "da_inviare")
esito("insulto con sostituzioni «1d10ta»", "insulto" in P("sei un 1d10ta", tipo="commento").segnali)
esito("variante scritta male «strunzo»", "insulto" in P("sei uno strunzo", tipo="commento").segnali)
esito("«ritardo» non è un insulto", P("il tram è in ritardo", tipo="commento").esito == "pulito")
esito("telefono, email, targa", all(s in P(t, tipo="commento").segnali for s, t in (("telefono", "chiama 333 1234567"), ("email", "scrivi a mario@x.it"), ("targa", "la targa AB123CD"))))
esito("codice fiscale valido sì, a caso no", "codice_fiscale" in P("RSSMRA85T10A562S", tipo="commento").segnali and "codice_fiscale" not in P("RSSMRA85T10A562X", tipo="commento").segnali)
esito("IBAN valido sì, errato no", "iban" in P("IT60X0542811101000000123456", tipo="commento").segnali and "iban" not in P("IT61X0542811101000000123456", tipo="commento").segnali)
esito("spam: due indirizzi web o web + parola", "spam" in P("vai su a.com e b.com", tipo="commento").segnali and "spam" in P("COMPRA su www.x.com", tipo="commento").segnali)
esito("commento pulito: nessuna richiesta", P("Concordo, il marciapiede è in pessime condizioni.", tipo="commento").esito == "pulito" and P("ok", tipo="commento").esito == "pulito")
esito("con foto: sempre da inviare", P("Marciapiede rotto in via Padova, servono lavori", ha_media=True).esito == "da_inviare")
esito("segnalazione senza foto e con categoria sicura: pulita", P("Il marciapiede è rotto, la panchina è sporca e c'è un graffito sull'aiuola").esito == "pulito")
esito("segnalazione senza categoria riconoscibile: da inviare", P("Vorrei segnalare una cosa che non va nel mio quartiere").esito == "da_inviare")
e1 = P("Bella idea", tipo="commento"); esito("doppione dello stesso testo", P("bella idea!!", tipo="commento", recenti=[e1.impronta]).esito == "doppione")
esito("priorità: l'insulto pesa più dell'email", P("idiota", tipo="commento").rischio > P("mario@x.it", tipo="commento").rischio)
esito("esito locale e punteggio", P("Ti ammazzo", tipo="commento").esito_locale == "bloccato" and P("ciao", tipo="commento").esito_locale == "ok" and P("idiota", tipo="commento").esito_locale is None)

# ------------------------------------------------------------------ finto OpenRouter
stato = {"fn": None, "richieste": [], "usate": 0}
class Finto(BaseHTTPRequestHandler):
    def _r(self, codice, dati):
        self.send_response(codice); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(dati).encode())
    def do_GET(self): self._r(200, {"data": {"free_model_daily_requests": {"used": stato["usate"], "limit": 50, "remaining": 50 - stato["usate"]}}})
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); stato["richieste"].append(corpo)
        self._r(*stato["fn"](corpo))
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), Finto); threading.Thread(target=srv.serve_forever, daemon=True).start()
def contenuto(d): return 200, {"choices": [{"message": {"content": json.dumps(d)}}], "usage": {"total_tokens": 900}, "provider": "Finto"}
def giudica(corpo):
    """Approva tutto tranne i testi che contengono «idiota» o «spam»; per i commenti risponde per ogni id; con le foto risponde anche per foto."""
    u = corpo["messages"][1]["content"]
    if isinstance(u, list):   # segnalazione con foto
        testo = " ".join(p["text"] for p in u if p["type"] == "text")
        cattivo = bool(re.search(r"idiota|spam", testo))
        ids = [int(i) for i in re.findall(r'<foto id="(\d+)"', testo)]
        return contenuto({"approvato": not cattivo, "motivazione": "insulto" if cattivo else "", "coerente": stato.get("coerente", True),
                          "foto": [{"id": i, "problema": stato.get("problema", {}).get(i, "nessuno")} for i in ids]})
    if "<commento" in u:
        ris = [{"id": int(i), "approvato": not re.search(r"idiota|spam", t), "motivazione": "" if not re.search(r"idiota|spam", t) else "insulto a un utente"}
               for i, t in re.findall(r'<commento id="(\d+)">(.*?)</commento>', u, re.S)]
        return contenuto({"risultati": ris})
    cattivo = bool(re.search(r"idiota|spam", u))
    return contenuto({"approvato": not cattivo, "motivazione": "insulto" if cattivo else ""})
orr._dormi = lambda s: None
IMP = dict(OPENROUTER_URL=f"http://127.0.0.1:{srv.server_address[1]}", OPENROUTER_API_KEY="chiave-di-prova", IA_INTERVALLO_MIN=0, IA_TIMEOUT_RICHIESTA=5, IA_MODALITA="coda")

class Rollback(Exception): pass
cat = list(Categoria.objects.filter(attiva=True)[:2]); qid = Quartiere.objects.first().id
utente = Utente.objects.filter(ruolo="utente", stato_account="attivo", metodo_registrazione="spid").first()
adm = Utente.objects.filter(ruolo="amministratore", stato_account="attivo").first()
CART = Path(settings.MEDIA_ROOT) / "media" / "prova_ia"; CART.mkdir(parents=True, exist_ok=True)
def foto(nome, testo=None, volto=False):
    if volto and Path("prova_documento/selfie_da_inquadrare.jpg").exists(): im = Image.open("prova_documento/selfie_da_inquadrare.jpg").convert("RGB")
    else: im = Image.new("RGB", (900, 600), (200, 210, 190))
    if testo:
        d = ImageDraw.Draw(im); d.text((30, 200), testo, fill=(0, 0, 0), font=ImageFont.load_default(size=70))
    im.save(CART / nome, "JPEG"); return {"tipo": "foto", "percorso": f"media/prova_ia/{nome}", "mime": "image/jpeg", "dimensione": 1000, "durata": None}
FILE = [foto("base.jpg")]
def nuova(titolo, descrizione, file=None):
    d = {"tipo": "problema", "titolo": titolo, "descrizione": descrizione, "latitudine": 45.46, "longitudine": 9.19, "indirizzo": None}
    return crea_segnalazione(utente, d, qid, file or FILE, cat)
def commenta(s, testo, c=None):
    c = c or Client(); c.force_login(utente, backend="core.backends.UtenteBackend")
    c.post(f"/segnalazioni/{s.id}/commenta/", {"testo": testo}); return Commento.objects.filter(segnalazione=s, autore=utente).order_by("-id").first()
def riga(**f): return CodaIA.objects.filter(**f).order_by("-id").first()

try:
    with override_settings(**IMP), transaction.atomic():
        quota.azzera_cache(); stato["fn"] = giudica
        # ---- segnalazione con foto: salvata subito, in attesa, senza esito; poi il lavoratore
        s = nuova("Marciapiede rotto in via Padova", "Il marciapiede davanti al civico 10 è rotto da mesi e pericoloso per gli anziani.")
        s.refresh_from_db()
        esito("segnalazione salvata «In attesa» senza esito", s.stato_id == 2 and s.esito_moderazione is None and s.controllo_in_corso)
        r = riga(segnalazione=s); esito("una riga in coda con priorità e impronta", r and r.stato == "in_coda" and r.priorita == 10 and len(r.impronta) == 64 and r.segnali == ["foto"])
        cm = Client(); cm.force_login(adm, backend="core.backends.UtenteBackend")
        cm.post(f"/moderazione/segnalazioni/{s.id}/approva/"); s.refresh_from_db()
        esito("il moderatore non può approvare finché il controllo è in corso", s.stato_id == 2)
        esito("passo: la segnalazione è controllata", lavoratore.passo() == "fatto")
        s.refresh_from_db(); r.refresh_from_db()
        esito("esito ok scritto, punteggio e riga «fatto»", s.esito_moderazione == "ok" and s.punteggio_moderazione == Decimal("0.050") and r.stato == "fatto" and not s.controllo_in_corso)
        l = LogAttivita.objects.filter(tabella="segnalazioni", id_oggetto=s.id, operazione="decisione_ia").order_by("-id").first()
        esito("registro: modello, fornitore, versione del prompt", l and l.dati_nuovi["fornitore"] == "openrouter" and l.dati_nuovi["modello"] and l.dati_nuovi["versione_prompt"] == "2026-10-26.2", l and l.dati_nuovi)
        corpo = stato["richieste"][-1]
        esito("il testo dell'autore sta nel messaggio user, non nelle istruzioni", "marciapiede" in json.dumps(corpo["messages"][1]["content"]) and "marciapiede" not in corpo["messages"][0]["content"])
        cm.post(f"/moderazione/segnalazioni/{s.id}/approva/"); s.refresh_from_db()
        esito("dopo l'esito il moderatore approva", s.stato_id == 3)
        # ---- il modello dice no: dubbio
        s2 = nuova("Problema con idiota", "Il vicino è un idiota e parcheggia sul marciapiede davanti al passo carraio ogni giorno.")
        lavoratore.passo(); s2.refresh_from_db()
        esito("il modello respinge: esito dubbio (mai bloccato)", s2.esito_moderazione == "dubbio" and s2.punteggio_moderazione == Decimal("0.650"))
        # ---- minaccia: bloccato dal prefiltro, nessuna coda
        s3 = nuova("Basta", "Vi ammazzo tutti se non sistemate la strada, ve lo giuro davvero.")
        s3.refresh_from_db(); esito("minaccia: bloccata subito, nessuna riga in coda", s3.esito_moderazione == "bloccato" and riga(segnalazione=s3) is None and s3.stato_id == 2)
        esito("l'autore è avvisato del blocco", Notifica.objects.filter(utente=utente, tipo="contenuto_bloccato").exists())
        # ---- modifica: la riga vecchia è sostituita
        s4 = nuova("Buca in strada", "Una buca profonda in via Torino all'altezza del civico 5 che danneggia le auto.")
        vecchia = riga(segnalazione=s4); s4.descrizione = "Testo cambiato dopo l'invio, buca profonda in via Torino."; s4.save(update_fields=["descrizione"])
        lavoratore.passo(); vecchia.refresh_from_db(); esito("contenuto modificato dopo l'accodamento: riga «saltato», nessuna richiesta", vecchia.stato == "saltato")
        # ---- commenti: pulito resta locale, dubbio va in coda e si rilegge a blocchi
        n0 = len(stato["richieste"])
        c1 = commenta(s, "Concordo, grazie per la segnalazione."); esito("commento pulito: pubblicato con esito ok, nessuna coda", c1.esito_moderazione == "ok" and riga(commento=c1) is None)
        c2 = commenta(s, "Sei un idiota se pensi questo"); esito("commento con insulto: pubblicato, esito in attesa, in coda", c2 and c2.esito_moderazione is None and riga(commento=c2).stato == "in_coda")
        c3 = commenta(s, "Ti ammazzo"); esito("commento con minaccia: non pubblicato", not Commento.objects.filter(testo="Ti ammazzo").exists())
        c4 = commenta(s, "Contattami al 333 1234567 per chiarire"); esito("commento con telefono: in coda", riga(commento=c4) is not None)
        c5 = commenta(s, "Sei un idiota se pensi questo"); esito("commento identico: esito dubbio locale, non accodato", c5.esito_moderazione == "dubbio" and riga(commento=c5) is None)
        esito("fin qui nessuna richiesta al modello per i commenti", len(stato["richieste"]) == n0)
        esito("meno di 10 commenti e recenti: il blocco non parte", lavoratore.passo() == "vuoto")
        with override_settings(IA_COMMENTI_MINIMO=2):
            esito("con 2 commenti in coda (soglia 2) parte il blocco", lavoratore.passo() == "fatto")
        c2.refresh_from_db(); c4.refresh_from_db()
        esito("una sola richiesta per tutto il blocco", len(stato["richieste"]) == n0 + 1)
        esito("esiti per commento: insulto dubbio, telefono ok", c2.esito_moderazione == "dubbio" and c4.esito_moderazione == "ok")
        esito("commenti rimasti in coda: nessuno", not CodaIA.objects.filter(stato="in_coda", commento__isnull=False).exists())
        # ---- un commento vecchio parte anche da solo
        c6 = commenta(s, "Un altro idiota nel quartiere"); CodaIA.objects.filter(commento=c6).update(creata_il=timezone.now() - timedelta(hours=7))
        esito("commento in coda da più di 6 ore: parte da solo", lavoratore.passo() == "fatto")
        # ---- il modello salta un id / risponde male
        s5 = nuova("Lampione spento", "Il lampione all'angolo di via Settala è spento da giorni e la strada è buia di sera.")
        stato["fn"] = lambda corpo: contenuto({"approvato": "forse", "motivazione": ""})
        esito("risposta non valida: «errore», la riga resta in coda per riprovare", lavoratore.passo() == "errore" and riga(segnalazione=s5).stato == "in_coda" and riga(segnalazione=s5).tentativi == 1)
        CodaIA.objects.filter(segnalazione=s5).update(non_prima_di=timezone.now() - timedelta(minutes=1))
        esito("secondo errore", lavoratore.passo() == "errore")
        CodaIA.objects.filter(segnalazione=s5).update(non_prima_di=timezone.now() - timedelta(minutes=1))
        esito("terzo errore: riga «fallito» e esito dubbio per il moderatore", lavoratore.passo() == "errore" and riga(segnalazione=s5).stato == "fallito")
        s5.refresh_from_db(); esito("dopo 3 tentativi la segnalazione è «dubbio» (decide una persona)", s5.esito_moderazione == "dubbio" and not s5.controllo_in_corso)
        # ---- nessun modello (privacy) e quota
        stato["fn"] = lambda corpo: (404, {"error": {"code": 404, "message": "No endpoints found matching your data policy"}})
        s6 = nuova("Semaforo guasto", "Il semaforo all'incrocio di viale Monza lampeggia da una settimana senza funzionare bene.")
        esito("nessun modello disponibile: «errore» e riprova più tardi", lavoratore.passo() == "errore" and riga(segnalazione=s6).stato == "in_coda" and riga(segnalazione=s6).non_prima_di > timezone.now())
        stato["fn"] = giudica; CodaIA.objects.filter(segnalazione=s6).update(non_prima_di=timezone.now() - timedelta(minutes=1))
        stato["usate"] = 50; quota.azzera_cache()
        esito("quota esaurita: il lavoro aspetta, nessuna richiesta", lavoratore.passo() == "quota" and riga(segnalazione=s6).stato == "in_coda")
        stato["usate"] = 0; quota.azzera_cache()
        esito("quota di nuovo libera: il lavoro riparte", lavoratore.passo() == "fatto" and riga(segnalazione=s6).stato == "fatto")
        # ---- oltre 24 ore
        s7 = nuova("Fontanella rotta", "La fontanella del parco di via Padova perde acqua da giorni e sta allagando il sentiero.")
        CodaIA.objects.filter(segnalazione=s7).update(creata_il=timezone.now() - timedelta(hours=25))
        Segnalazione.objects.filter(pk=s7.pk).update(creata_il=timezone.now() - timedelta(hours=25))
        lavoratore.passo(); s7.refresh_from_db()
        esito("oltre 24 ore in coda: dubbio per il moderatore, riga «fallito»", s7.esito_moderazione == "dubbio" and riga(segnalazione=s7).stato == "fallito")
        # ---- righe bloccate in corso
        s8 = nuova("Aiuola secca", "L'aiuola davanti alla scuola è secca da settimane, serve un intervento di giardinaggio.")
        r8 = riga(segnalazione=s8); CodaIA.objects.filter(pk=r8.pk).update(stato="in_corso", presa_il=timezone.now() - timedelta(minutes=30))
        esito("riga rimasta «in_corso» dopo un riavvio: torna in coda", coda.riprendi_bloccate() >= 1 and riga(segnalazione=s8).stato == "in_coda")
        # ---- priorità
        CodaIA.objects.filter(stato="in_coda").update(stato="saltato")
        a = nuova("Rifiuti per strada", "Cumulo di rifiuti accanto ai cassonetti di via Padova, da giorni nessuno li ritira."); ra = riga(segnalazione=a)
        b = nuova("Strada pericolosa", "Il vicino è un idiota che sfreccia in via Padova a velocità folle davanti alla scuola."); rb = riga(segnalazione=b)
        CodaIA.objects.filter(pk__in=[ra.pk, rb.pk]).update(stato="in_coda")
        tipo, righe = coda.scegli(); esito("priorità: prima il rischio più alto", righe[0].pk == rb.pk, (ra.priorita, rb.priorita))
        # ---- FASE 3: foto, volti, testo nelle foto, video
        CodaIA.objects.filter(stato="in_coda").update(stato="saltato"); stato["fn"] = giudica; stato["problema"] = {}; stato["coerente"] = True
        n0 = len(stato["richieste"])
        sf = nuova("Albero caduto in via Torino", "Un albero è caduto sul marciapiede dopo il temporale e blocca il passaggio.", [foto("v.jpg", volto=True)])
        mv = sf.media.get()
        lavoratore.passo(); corpo = stato["richieste"][-1]; parti = corpo["messages"][1]["content"]
        imgs = [p for p in parti if p["type"] == "image_url"]
        esito("segnalazione con foto: una sola richiesta con testo e immagine", len(stato["richieste"]) == n0 + 1 and len(imgs) == 1 and imgs[0]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        esito("la foto è ridotta a 768 px al massimo", max(Image.open(io.BytesIO(base64.b64decode(imgs[0]["image_url"]["url"].split(",")[1]))).size) <= 768)
        esito("il prompt con le foto non contiene il testo dell'utente", "Albero caduto" not in corpo["messages"][0]["content"] and "Albero caduto" in parti[0]["text"])
        if Path("prova_documento/selfie_da_inquadrare.jpg").exists():
            inviata = Image.open(io.BytesIO(base64.b64decode(imgs[0]["image_url"]["url"].split(",")[1]))).convert("L"); orig = Image.open("prova_documento/selfie_da_inquadrare.jpg").convert("L").resize(inviata.size)
            import numpy as np
            def nitidezza(im, box): a = np.array(im.crop(box), float); return np.abs(np.diff(a, axis=1)).mean()
            w, h = inviata.size; box = (int(w * .3), int(h * .15), int(w * .55), int(h * .35))
            esito("il volto è sfocato prima dell'invio", nitidezza(inviata, box) < 0.6 * nitidezza(orig, box), (nitidezza(inviata, box), nitidezza(orig, box)))
        sf.refresh_from_db(); mv.refresh_from_db()
        esito("esito ok, coerenza alta, media «ok»", sf.esito_moderazione == "ok" and sf.punteggio_coerenza == Decimal("0.900") and mv.esito_visione == "ok")
        l = LogAttivita.objects.filter(tabella="segnalazioni", id_oggetto=sf.id, operazione="decisione_ia").order_by("-id").first()
        esito("registro: volti sfocati e modello", l and any(str(x).startswith("volti_sfocati") for x in l.dati_nuovi["segnali"]) == (Path("prova_documento/selfie_da_inquadrare.jpg").exists()), l and l.dati_nuovi)
        # contenuto non adatto e foto non coerente
        s9 = nuova("Pista ciclabile interrotta", "La pista ciclabile di via Settala si interrompe all'incrocio ed è molto pericolosa.", [foto("a.jpg")])
        stato["problema"] = {1: "sessuale"}; lavoratore.passo(); s9.refresh_from_db(); m9 = s9.media.get()
        esito("foto con contenuto sessuale: dubbio, media «dubbio» con punteggio alto", s9.esito_moderazione == "dubbio" and m9.esito_visione == "dubbio" and m9.punteggio_sessuale == Decimal("0.900") and m9.punteggio_violenza == Decimal("0.020"))
        s10 = nuova("Strisce pedonali sbiadite", "Le strisce pedonali davanti alla scuola sono quasi invisibili e le auto non si fermano.", [foto("b.jpg")])
        stato["problema"] = {}; stato["coerente"] = False; lavoratore.passo(); s10.refresh_from_db()
        esito("foto non coerente col testo: dubbio e coerenza bassa", s10.esito_moderazione == "dubbio" and s10.punteggio_coerenza == Decimal("0.200"))
        stato["coerente"] = True
        # testo scritto nelle foto
        s11 = nuova("Cantiere abbandonato", "Il cantiere in via Padova è fermo da mesi e il recinto è aperto verso il marciapiede.", [foto("c.jpg", "VIA PADOVA 12 CHIUSA")])
        lavoratore.passo(); m11 = s11.media.get(); parti = stato["richieste"][-1]["messages"][1]["content"]
        esito("testo letto nella foto: salvato e passato al modello", "padova" in (m11.testo_ocr or "").lower() and any("<testo_letto>" in p.get("text", "") for p in parti), m11.testo_ocr)
        n1 = len(stato["richieste"]); s12 = nuova("Muro con scritte", "Sul muro della scuola c'è una scritta minacciosa che spaventa i bambini ogni mattina.", [foto("d.jpg", "TI AMMAZZO")])
        lavoratore.passo(); s12.refresh_from_db()
        esito("minaccia scritta in una foto: bloccata senza chiedere al modello", s12.esito_moderazione == "bloccato" and len(stato["richieste"]) == n1 and s12.media.get().esito_testo_ocr == "bloccato", s12.media.get().testo_ocr)
        # file mancanti
        s13 = nuova("Panchina rotta", "La panchina nel giardino di via Vitruvio è rotta e ha le assi spezzate da giorni.", [{**FILE[0], "percorso": "media/prova_ia/non_esiste.jpg"}])
        n2 = len(stato["richieste"]); lavoratore.passo(); s13.refresh_from_db()
        esito("foto non leggibili: solo testo al modello, esito dubbio «foto non verificabili»", s13.esito_moderazione == "dubbio" and len(stato["richieste"]) == n2 + 1 and not isinstance(stato["richieste"][-1]["messages"][1]["content"], list))
        # più di 5 foto e video
        sette = [foto(f"m{i}.jpg") for i in range(7)]; s14 = nuova("Rifiuti ovunque", "Rifiuti abbandonati lungo tutta la via davanti ai cassonetti, da giorni nessuno ritira nulla.", sette)
        lavoratore.passo(); imgs = [p for p in stato["richieste"][-1]["messages"][1]["content"] if p["type"] == "image_url"]
        esito("al massimo 5 immagini per richiesta", len(imgs) == 5, len(imgs))
        mp4 = CART / "clip.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=10", "-pix_fmt", "yuv420p", str(mp4)], check=True)
        s15 = nuova("Incrocio pericoloso", "Al semaforo di viale Monza le auto passano col rosso e rischiano di investire i pedoni.", [{"tipo": "video", "percorso": "media/prova_ia/clip.mp4", "mime": "video/mp4", "dimensione": 5000, "durata": 4}])
        lavoratore.passo(); imgs = [p for p in stato["richieste"][-1]["messages"][1]["content"] if p["type"] == "image_url"]
        esito("video: due fotogrammi", len(imgs) == 2, len(imgs))
        # ---- blocco del lavoratore
        esito("blocco su database per un solo lavoratore", lavoratore._blocco_acquisito())
        # ---- modalità sincrona: comportamento di prima
        with override_settings(IA_MODALITA="sincrona"):
            z = nuova("Marciapiede dissestato", "Il marciapiede in via Vitruvio è dissestato e le radici dell'albero lo sollevano."); z.refresh_from_db()
            esito("modalità sincrona: esito subito e nessuna coda", z.esito_moderazione == "ok" and z.punteggio_coerenza is not None and riga(segnalazione=z) is None and not z.controllo_in_corso)
        raise Rollback()
except Rollback:
    pass
shutil.rmtree(CART, ignore_errors=True)
srv.shutdown()
esito("nessuna riga lasciata (coda e registro)", not CodaIA.objects.filter(segnalazione__titolo="Marciapiede rotto in via Padova").exists())
