import os, io, django, hashlib
import sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from datetime import date
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from core.models import *
from smoke._aiuti import SFX, UTENTI_DEMO_MAX_ID, campi_documento
PW="DemoMilano2026!"
def esito(nome, cond, extra=""): print(("OK  " if cond else "!!  ")+nome+(f"  [{extra}]" if extra else ""))
def msgs(r): return [str(m) for m in r.context["messages"]] if r.context else []
def foto(exif=True, nome="f.jpg"):
    im = Image.new("RGB", (80, 60), (200, 40, 40)); b = io.BytesIO()
    if exif:
        e = Image.Exif(); e[0x010F] = "FotocameraDiProva"; e[0x8825] = {1: "N", 2: (45.0, 27.0, 0.0), 3: "E", 4: (9.0, 11.0, 0.0)}
        im.save(b, "JPEG", exif=e)
    else: im.save(b, "JPEG")
    return SimpleUploadedFile(nome, b.getvalue(), content_type="image/jpeg")

mod = Utente.objects.filter(ruolo="moderatore").first()
autore = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$", id__lte=UTENTI_DEMO_MAX_ID).order_by("id").first()
altro = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$", id__lte=UTENTI_DEMO_MAX_ID).exclude(pk=autore.pk).order_by("-id").first()
pub = Segnalazione.objects.filter(stato_id=3, nascosta=False).exclude(autore=altro).exclude(autore=autore).first()
A, B, M = Client(), Client(), Client()
A.login(email=autore.email, password=PW); B.login(email=altro.email, password=PW); M.login(email=mod.email, password=PW)

# --- sostegno
n0 = pub.sostegni.count(); Sostegno.objects.filter(utente=altro, segnalazione=pub).delete(); n0 = pub.sostegni.count()
r = B.post(f"/segnalazioni/{pub.id}/sostieni/", follow=True); esito("sostegno aggiunto", pub.sostegni.count() == n0+1, msgs(r)[-1:][0] if msgs(r) else "")
r = B.post(f"/segnalazioni/{pub.id}/sostieni/", follow=True); esito("sostegno ritirato (toggle)", pub.sostegni.count() == n0)
own = Segnalazione.objects.filter(autore=altro, stato_id=3, nascosta=False).first()
if own: r = B.post(f"/segnalazioni/{own.id}/sostieni/", follow=True); esito("sostegno alla propria bloccato dal trigger", Sostegno.objects.filter(utente=altro, segnalazione=own).count()==0, " | ".join(msgs(r)))
r = Client().post(f"/segnalazioni/{pub.id}/sostieni/"); esito("sostegno da visitatore -> login", r.status_code == 302 and "accedi" in r["Location"])
# --- commenti
r = B.post(f"/segnalazioni/{pub.id}/commenta/", {"testo": "Commento di prova, concordo."}, follow=True)
c = Commento.objects.filter(segnalazione=pub, autore=altro).order_by("-id").first(); esito("commento pubblicato", c is not None and c.esito_moderazione == "ok")
r = A.post(f"/segnalazioni/{pub.id}/commenta/", {"testo": "Risposta di prova.", "padre": c.id}, follow=True)
rr = Commento.objects.filter(padre=c).first(); esito("risposta annidata", rr is not None and rr.segnalazione_id == pub.id)
r = B.post(f"/segnalazioni/{pub.id}/commenta/", {"testo": "Sei un idiota."}, follow=True); cd = Commento.objects.filter(autore=altro, testo__icontains="idiota").first()
esito("commento con insulto: pubblicato ma in 'dubbio'", cd is not None and cd.esito_moderazione == "dubbio")
r = B.post(f"/segnalazioni/{pub.id}/commenta/", {"testo": "Ti ammazzo se..."}, follow=True); esito("commento con minaccia bloccato", not Commento.objects.filter(testo__startswith="Ti ammazzo").exists(), " | ".join(msgs(r))[:70])
r = B.post(f"/segnalazioni/{pub.id}/commenti/{c.id}/elimina/", follow=True); c.refresh_from_db(); esito("commento eliminato (logico)", c.eliminato_il is not None)
# --- nuova segnalazione
dati = {"tipo": "problema", "titolo": "Semaforo pedonale troppo breve in via di prova", "descrizione": "Il semaforo pedonale all'incrocio dura pochi secondi e gli anziani non fanno in tempo ad attraversare la strada.",
        "categorie": [Categoria.objects.get(nome="Mobilità urbana").id], "latitudine": "45.4642", "longitudine": "9.1900", "indirizzo": "Piazza del Duomo"}
r = A.post("/segnalazioni/nuova/", {**dati, "media": [foto(), foto(False, "g.jpg")]}, follow=True)
s = Segnalazione.objects.filter(autore=autore, titolo__startswith="Semaforo pedonale troppo breve in via di prova").order_by("-id").first()
esito("nuova segnalazione creata", s is not None, f"id={s.id if s else None}")
if s:
    esito("quartiere ricavato dalla posizione (Duomo=1)", s.quartiere_id == 1)
    esito("stato avanzato 1->2 via cambi_stato (sistema)", s.stato_id == 2 and s.cambi_stato.count() == 1 and s.cambi_stato.first().operatore_id is None)
    ms_ = list(s.media.all()); esito("2 media, una sola copertina", len(ms_) == 2 and sum(m.copertina for m in ms_) == 1)
    f = ms_[0]; im = Image.open(os.path.join("media", f.percorso[len("media/"):]) if False else os.path.join("media", f.percorso)); ex = im.getexif()
    esito("metadati EXIF rimossi dal file salvato", len(ex) == 0 and not im.info.get("exif"), f"tag residui={len(ex)}")
    cl = list(Classificazione.objects.filter(segnalazione=s)); esito("categoria classificata (origine ia)", len(cl) == 1 and cl[0].origine == "ia", f"{cl[0].origine} {cl[0].confidenza}" if cl else "")
    esito("log di creazione e decisione IA", LogAttivita.objects.filter(tabella="segnalazioni", id_oggetto=s.id).count() >= 3)
    # --- moderazione
    r = A.post(f"/moderazione/segnalazioni/{s.id}/approva/"); esito("utente semplice non può approvare", r.status_code == 404)
    r = M.post(f"/moderazione/segnalazioni/{s.id}/approva/", follow=True); s.refresh_from_db(); esito("moderatore approva (2->3)", s.stato_id == 3, " | ".join(msgs(r))[:60])
    r = M.post(f"/moderazione/segnalazioni/{s.id}/presenta/", {"candidati": [1, 2]}, follow=True); s.refresh_from_db()
    esito("presentata ai candidati (3->5) con 2 invii", s.stato_id == 5 and s.invii.count() == 2)
    r = M.post(f"/moderazione/segnalazioni/{s.id}/rifiuta/", {"motivo": "x"}, follow=True); esito("transizione 5->4 rifiutata dal trigger", Segnalazione.objects.get(pk=s.id).stato_id == 5, " | ".join(msgs(r))[:70])
    esito("notifica all'autore sui cambi di stato", Notifica.objects.filter(utente=autore, tipo="stato_segnalazione", messaggio__contains="Semaforo pedonale").count() >= 2)
# --- limiti e controlli
r = A.post("/segnalazioni/nuova/", {**dati, "latitudine": "45.50", "longitudine": "9.28", "titolo": "Fuori Milano", "media": [foto(False)]}); esito("punto fuori dal Comune rifiutato", not Segnalazione.objects.filter(titolo="Fuori Milano").exists())
r = A.post("/segnalazioni/nuova/", {**dati, "titolo": "Senza media"}); esito("senza media rifiutata", not Segnalazione.objects.filter(titolo="Senza media").exists())
r = A.post("/segnalazioni/nuova/", {**dati, "titolo": "Pdf finto", "media": [SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf")]}); esito("formato non ammesso rifiutato", not Segnalazione.objects.filter(titolo="Pdf finto").exists())
for i in range(6): A.post("/segnalazioni/nuova/", {**dati, "titolo": f"Limite giornaliero {i}", "media": [foto(False)]})
oggi_n = Segnalazione.objects.filter(autore=autore, titolo__startswith="Limite giornaliero").count(); esito("limite di 5 segnalazioni al giorno", Segnalazione.objects.filter(autore=autore, creata_il__date=date.today()).count() <= 5, f"create nel test={oggi_n}")
# --- registrazione
Utente.objects.filter(email=f"nuovo.prova{SFX}@example.org").delete() if False else None
C = Client(); form = {"nome": "Prova", "cognome": "Registrato", "email": f"nuovo.prova{SFX}@example.org", "password": "Ombrello-Verde7!", "password2": "Ombrello-Verde7!", "data_nascita": "1995-05-05",
      **{k: "on" for k in ["privacy", "biometrici", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"]}}
if not Utente.objects.filter(email=form["email"]).exists():
    r = C.post("/registrati/", {**form, **campi_documento(), "data_nascita": "2020-01-01", "email": f"minorenne{SFX}@example.org"}); esito("under 14 rifiutato", not Utente.objects.filter(email=f"minorenne{SFX}@example.org").exists())
    r = C.post("/registrati/", {**form, **campi_documento(), "password": "debole", "password2": "debole", "email": f"debole{SFX}@example.org"}); esito("password debole rifiutata", not Utente.objects.filter(email=f"debole{SFX}@example.org").exists())
    r = C.post("/registrati/", {**form, **campi_documento()}, follow=True); u = Utente.objects.filter(email=form["email"]).first()
    esito("registrazione: verifica simulata ok ma account in attesa della conferma email", u is not None and u.stato_account == "in_attesa_verifica" and u.verifiche.count() == 1 and u.consensi.count() == 6, f"consensi={u.consensi.count() if u else 0}")
    from core.services import token
    r = C.get("/conferma-email/token-sbagliato/", follow=True); esito("link di conferma non valido rifiutato", u.stato_account == "in_attesa_verifica" and Utente.objects.get(pk=u.pk).email_verificata_il is None)
    C.get(f"/conferma-email/{token.crea('conferma', u)}/", follow=True); u.refresh_from_db(); esito("conferma email -> account attivo", u.stato_account == "attivo" and u.email_verificata_il is not None)
    esito("utente già autenticato dopo registrazione", "_auth_user_id" in C.session)
D = Client(); r = D.post("/accedi/", {"email": form["email"], "password": "sbagliata"}); esito("password errata: messaggio", "non corretti" in r.content.decode())
r = D.post("/accedi/", {"email": form["email"], "password": form["password"]}); esito("login con le credenziali registrate", r.status_code == 302)
