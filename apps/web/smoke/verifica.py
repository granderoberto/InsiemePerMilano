"""Verifica dell'identità con documento e selfie (facoltativa alla registrazione, necessaria per pubblicare):
file, archivio temporaneo, esiti, tentativi, consenso biometrico, blocco della pubblicazione."""
import os, sys, glob, django
os.environ["IA_DOCUMENTO"] = "simulato"   # questa prova controlla il flusso con il controllo simulato (punteggi fissi); la prova vera è verifica_reale.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from core.models import *
from core.services import temporaneo, token
from smoke._aiuti import SFX, campi_documento
PW = "Tr4ghetto-Blu!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def residui(): return glob.glob(str(settings.TMP_VERIFICHE_DIR / "*" / "*")) + glob.glob(str(settings.TMP_VERIFICHE_DIR / "*"))
CONSENSI = {k: "on" for k in ["privacy", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"]}
def registra(n):
    """Registra un utente SENZA documenti, conferma l'email e lo fa accedere. -> (client, utente)"""
    c = Client(); email = f"verifica.prova{n}{SFX}@example.org"
    r = c.post("/registrati/", {"nome": "Verifica", "cognome": f"Prova{n}", "email": email, "data_nascita": "1996-03-10", "password": PW, "password2": PW, **CONSENSI}, follow=True)
    u = Utente.objects.filter(email=email).first()
    return c, u
def attiva(c, u):
    c.get(f"/conferma-email/{token.crea('conferma', u)}/"); u.refresh_from_db()
def verifica(c, docs=None, primo=True):
    d = docs if docs is not None else campi_documento()
    if primo: d = {**d, "biometrici": "on"}
    return c.post("/profilo/verifica/", d, follow=True)

# --- registrazione senza documenti
c, u = registra(1)
esito("la registrazione non chiede documento né selfie", u is not None and u.verifiche.count() == 0)
esito("alla registrazione non si dà il consenso biometrico", not Consenso.objects.filter(utente=u, documento__tipo="biometrici").exists())
esito("fino alla conferma email l'account è in attesa", u.stato_account == "in_attesa_verifica")
attiva(c, u)
esito("dopo la conferma email l'account è attivo (senza verifica)", u.stato_account == "attivo" and not u.identita_verificata)
esito("il profilo propone di verificare l'identità", "Verifica la mia identità" in c.get("/profilo/").content.decode())

# --- pubblicare richiede la verifica; sostenere e commentare no
r = c.get("/segnalazioni/nuova/"); esito("senza verifica «nuova segnalazione» porta alla verifica", r.status_code == 302 and "/profilo/verifica/" in r["Location"])
r = c.post("/segnalazioni/nuova/", {"titolo": "x"}); esito("e non si può pubblicare nemmeno con un invio diretto", r.status_code == 302 and Segnalazione.objects.filter(autore=u).count() == 0)
pubb = Segnalazione.objects.filter(stato_id=3, eliminata_il__isnull=True).exclude(autore=u).first()
r = c.post(f"/segnalazioni/{pubb.id}/sostieni/"); esito("senza verifica si può sostenere", Sostegno.objects.filter(utente=u, segnalazione=pubb).exists())
r = c.post(f"/segnalazioni/{pubb.id}/commenta/", {"testo": "Concordo con questa proposta, grazie."}); esito("e commentare", Commento.objects.filter(autore=u, segnalazione=pubb).exists())

# --- file non validi: nessun tentativo registrato
def tentativi(u): return u.verifiche.count()
r = verifica(c, {**campi_documento(), "fronte": SimpleUploadedFile("fronte.jpg", b"MZ\x90\x00 non sono un'immagine", content_type="image/jpeg")}); esito("un eseguibile travestito da .jpg è rifiutato", tentativi(u) == 0 and "formato non ammesso" in r.content.decode())
r = verifica(c, {**campi_documento(), "fronte": SimpleUploadedFile("f.jpg", b"\xff\xd8\xff" + b"0" * 100, content_type="image/jpeg")}); esito("immagine danneggiata rifiutata", tentativi(u) == 0 and "danneggiata" in r.content.decode())
grande = SimpleUploadedFile("g.jpg", b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10), content_type="image/jpeg")
r = verifica(c, {**campi_documento(), "fronte": grande}); esito("oltre 5 MB rifiutato", tentativi(u) == 0 and "5 MB" in r.content.decode())
r = verifica(c, campi_documento(retro=None)); esito("carta d'identità senza retro rifiutata", tentativi(u) == 0 and "retro" in r.content.decode().lower())
docs = campi_documento(); docs.pop("selfie"); r = verifica(c, docs); esito("senza selfie: rifiutata", tentativi(u) == 0 and "Scatta il selfie" in r.content.decode())
docs = campi_documento(); docs["sfida"] = "inventata"; r = verifica(c, docs); esito("selfie senza sfida valida (non scattato dalla pagina): rifiutato", tentativi(u) == 0 and "fotocamera" in r.content.decode())
docs = campi_documento(); docs["selfie"] = SimpleUploadedFile("s.pdf", b"%PDF-1.4 finto", content_type="application/pdf"); r = verifica(c, docs); esito("il selfie non può essere un PDF", tentativi(u) == 0)
r = verifica(c, campi_documento(), primo=False); esito("senza il consenso biometrico non si procede", tentativi(u) == 0 and not Consenso.objects.filter(utente=u, documento__tipo="biometrici").exists())
esito("dopo errori e rifiuti nessun file resta sul disco", not residui(), str(residui()[:2]))

# --- esiti
r = verifica(c, campi_documento(retro=None, tipo="passaporto")); v = u.verifiche.get(); u.refresh_from_db()
esito("il passaporto non richiede il retro; nitido: approvata (96)", v.esito_ia == "approvata" and v.punteggio == 96 and v.tentativo == 1)
esito("il consenso biometrico viene registrato solo ora", Consenso.objects.filter(utente=u, documento__tipo="biometrici").count() == 1)
esito("a verifica finita non resta nessun file", not residui())
esito("registro: verifica e decisione IA (sistema)", LogAttivita.objects.filter(tabella="verifiche_identita", id_oggetto=v.id).count() == 2)
esito("identità verificata: ora si può aprire «nuova segnalazione»", u.identita_verificata and c.get("/segnalazioni/nuova/").status_code == 200)
esito("la pagina di verifica non serve più", c.get("/profilo/verifica/").status_code == 302)

c2, u2 = registra(2); attiva(c2, u2)
verifica(c2, campi_documento(fronte=400)); v2 = u2.verifiche.get(); esito("documento a bassa risoluzione: da rivedere (66)", v2.esito_ia == "da_rivedere" and v2.punteggio == 66 and not v2.ok_lettura_ocr, v2.motivo)
esito("in revisione non si può ripetere né pubblicare", c2.get("/profilo/verifica/").status_code == 302 and c2.get("/segnalazioni/nuova/").status_code == 302 and not u2.identita_verificata)
mod = Utente.objects.filter(ruolo="moderatore").first(); M = Client(); M.login(email=mod.email, password="DemoMilano2026!")
esito("compare nella coda del moderatore", f"/moderazione/verifiche/{v2.id}/decidi/" in M.get("/moderazione/").content.decode())
M.post(f"/moderazione/verifiche/{v2.id}/decidi/", {"esito": "approvata", "motivo": "Documento verificato a mano"}); u2 = Utente.objects.get(pk=u2.pk)
esito("il moderatore approva: l'identità risulta verificata", u2.identita_verificata and c2.get("/segnalazioni/nuova/").status_code == 200)

c3, u3 = registra(3); attiva(c3, u3)
verifica(c3, campi_documento(selfie=100)); v3 = u3.verifiche.get(); esito("selfie minuscolo: rifiutata (36) con motivo", v3.esito_ia == "rifiutata" and v3.punteggio == 36 and "volto" in v3.motivo)
esito("l'utente è avvisato con il motivo", Notifica.objects.filter(utente=u3, messaggio__contains="non è stata superata").exists())
esito("il profilo propone di riprovare", "Riprova con nuove foto" in c3.get("/profilo/").content.decode())
verifica(c3, campi_documento(selfie=100), primo=False); esito("2º tentativo ancora rifiutato", u3.verifiche.count() == 2 and u3.verifiche.get(tentativo=2).esito_ia == "rifiutata")
verifica(c3, campi_documento(), primo=False); esito("3º tentativo approvato", u3.verifiche.get(tentativo=3).esito_ia == "approvata" and Utente.objects.get(pk=u3.pk).identita_verificata)
r = verifica(c3, campi_documento(), primo=False); esito("non c'è un 4º tentativo", u3.verifiche.count() == 3)
c4, u4 = registra(4); attiva(c4, u4)
for i in range(3): verifica(c4, campi_documento(selfie=100), primo=(i == 0))
esito("tre rifiuti: nessun altro tentativo, resta la revisione umana", u4.verifiche.count() == 3 and c4.get("/profilo/verifica/").status_code == 302 and "revisione" in c4.get("/profilo/").content.decode().lower())

# --- chi non ha confermato l'email non può verificare; SPID/CIE e comitato sono già verificati
c5, u5 = registra(5); r = c5.get("/profilo/verifica/"); esito("senza email confermata la verifica non si apre", r.status_code == 302)
sp = Utente.objects.filter(metodo_registrazione__in=["spid", "cie"], stato_account="attivo").first()
esito("SPID/CIE: identità verificata senza documenti", sp is None or sp.identita_verificata)
esito("moderatore e amministratore possono pubblicare", Utente.objects.filter(ruolo="moderatore").first().identita_verificata and Utente.objects.filter(ruolo="amministratore").first().identita_verificata)
esito("un utente non loggato non vede la pagina", Client().get("/profilo/verifica/").status_code == 302)

# --- archivio cifrato
with temporaneo.archivio() as a:
    nome = a.salva(b"contenuto riservato del documento"); grezzo = open(a.percorso() / nome, "rb").read()
    esito("l'archivio temporaneo è cifrato su disco", b"riservato" not in grezzo and a.leggi(nome) == b"contenuto riservato del documento")
    cartella = a.percorso()
esito("e sparisce all'uscita", not cartella.exists())
try:
    with temporaneo.archivio() as a: pp = a.percorso(); a.salva(b"x"); raise RuntimeError("errore a metà verifica")
except RuntimeError: pass
esito("anche se la verifica va in errore, i file vengono cancellati", not pp.exists() and not residui())
