"""Registrazione con documento e selfie: file, archivio temporaneo, esiti, tentativi."""
import os, sys, io, glob, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from core.models import *
from core.services import temporaneo
from smoke._aiuti import SFX, campi_documento, immagine
PW = "Tr4ghetto-Blu!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def residui(): return glob.glob(str(settings.BASE_DIR / "tmp_verifiche" / "*" / "*")) + glob.glob(str(settings.BASE_DIR / "tmp_verifiche" / "*"))
def dati(n, **kw):
    base = {"nome": "Verifica", "cognome": f"Prova{n}", "email": f"verifica.prova{n}{SFX}@example.org", "data_nascita": "1996-03-10", "password": PW, "password2": PW,
            **{k: "on" for k in ["privacy","biometrici","intelligenza_artificiale","termini_uso","cookie","eta_minima"]}}
    return {**base, **kw}
def registra(n, docs=None, **kw):
    c = Client(); r = c.post("/registrati/", {**dati(n, **kw), **(docs if docs is not None else campi_documento())}, follow=True)
    return c, r, Utente.objects.filter(email=f"verifica.prova{n}{SFX}@example.org").first()
def senza_cartelle(): return [p for p in glob.glob(str(settings.BASE_DIR / "tmp_verifiche" / "*")) if os.path.isdir(p)]
# --- file non validi: l'account non si crea
c, r, u = registra(1, docs={**campi_documento(), "fronte": SimpleUploadedFile("fronte.jpg", b"MZ\x90\x00 non sono un'immagine", content_type="image/jpeg")}); esito("un eseguibile travestito da .jpg è rifiutato", u is None and "formato non ammesso" in r.content.decode())
c, r, u = registra(2, docs={**campi_documento(), "fronte": SimpleUploadedFile("f.jpg", b"\xff\xd8\xff" + b"0" * 100, content_type="image/jpeg")}); esito("immagine danneggiata rifiutata", u is None and "danneggiata" in r.content.decode())
grande = SimpleUploadedFile("g.jpg", b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10), content_type="image/jpeg")
c, r, u = registra(3, docs={**campi_documento(), "fronte": grande}); esito("oltre 5 MB rifiutato", u is None and "5 MB" in r.content.decode())
c, r, u = registra(4, docs={**campi_documento(retro=None)}); esito("carta d'identità senza retro rifiutata", u is None and "retro" in r.content.decode().lower())
c, r, u = registra(5, docs={**campi_documento(retro=None, tipo="passaporto")}); esito("il passaporto non richiede il retro", u is not None)
docs = campi_documento(); docs.pop("selfie"); c, r, u = registra(6, docs=docs); esito("senza selfie: rifiutata", u is None and "Scatta il selfie" in r.content.decode())
docs = campi_documento(); docs["sfida"] = "inventata"; c, r, u = registra(7, docs=docs); esito("selfie senza sfida valida (non scattato dalla pagina): rifiutato", u is None and "fotocamera" in r.content.decode())
docs = campi_documento(); docs["selfie"] = SimpleUploadedFile("s.pdf", b"%PDF-1.4 finto", content_type="application/pdf"); c, r, u = registra(8, docs=docs); esito("il selfie non può essere un PDF", u is None)
esito("dopo errori e rifiuti nessun file resta sul disco", not residui(), str(residui()[:2]))
# --- esiti
c, r, u = registra(10); v = u.verifiche.get() if u else None
esito("documento nitido: approvata (96), account in attesa dell'email", v and v.esito_ia == "approvata" and v.punteggio == 96 and u.stato_account == "in_attesa_verifica" and v.tentativo == 1)
esito("a verifica finita non resta nessun file", not residui())
esito("registro: verifica e decisione IA (sistema)", LogAttivita.objects.filter(tabella="verifiche_identita", id_oggetto=v.id).count() == 2)
c, r, u2 = registra(11, docs=campi_documento(fronte=400)); v2 = u2.verifiche.get(); esito("documento a bassa risoluzione: da rivedere (66)", v2.esito_ia == "da_rivedere" and v2.punteggio == 66 and not v2.ok_lettura_ocr, v2.motivo)
mod = Utente.objects.filter(ruolo="moderatore").first(); M = Client(); M.login(email=mod.email, password="DemoMilano2026!")
esito("compare nella coda del moderatore", f"/moderazione/verifiche/{v2.id}/decidi/" in M.get("/moderazione/").content.decode())
c, r, u3 = registra(12, docs=campi_documento(selfie=100)); v3 = u3.verifiche.get(); esito("selfie minuscolo: rifiutata (36) con motivo", v3.esito_ia == "rifiutata" and v3.punteggio == 36 and "volto" in v3.motivo)
esito("l'utente è avvisato con il motivo", Notifica.objects.filter(utente=u3, messaggio__contains="non è stata superata").exists())
# --- nuovi tentativi
u3.refresh_from_db(); c3 = Client(); c3.login(email=u3.email, password=PW)
esito("il profilo propone di riprovare (1 tentativo su 3)", "Riprova con nuove foto" in c3.get("/profilo/").content.decode())
r = c3.post("/profilo/verifica/", campi_documento(selfie=100)); esito("2º tentativo ancora rifiutato", u3.verifiche.count() == 2 and u3.verifiche.get(tentativo=2).esito_ia == "rifiutata")
r = c3.post("/profilo/verifica/", campi_documento()); v3b = u3.verifiche.get(tentativo=3); esito("3º tentativo approvato", v3b.esito_ia == "approvata")
r = c3.post("/profilo/verifica/", campi_documento()); esito("non c'è un 4º tentativo", u3.verifiche.count() == 3 and r.status_code == 302)
c4, r, u4 = registra(13, docs=campi_documento(selfie=100)); k = Client(); k.login(email=u4.email, password=PW)
for i in range(2): k.post("/profilo/verifica/", campi_documento(selfie=100))
esito("tre rifiuti: nessun altro tentativo, resta la revisione umana", u4.verifiche.count() == 3 and k.get("/profilo/verifica/").status_code == 302 and "chiedere la revisione" in k.get("/profilo/").content.decode().lower() or "Hai usato tutti" in k.get("/profilo/").content.decode())
esito("un utente già attivo non vede la pagina", Client().get("/profilo/verifica/").status_code == 302)
# --- attivazione: verifica approvata + email confermata
from core.services import token
c5 = Client(); c5.get(f"/conferma-email/{token.crea('conferma', u)}/"); u.refresh_from_db(); esito("verifica approvata + email confermata = account attivo", u.stato_account == "attivo")
c6 = Client(); c6.get(f"/conferma-email/{token.crea('conferma', u2)}/"); u2.refresh_from_db(); esito("email confermata ma verifica ancora in revisione: resta in attesa", u2.stato_account == "in_attesa_verifica")
M.post(f"/moderazione/verifiche/{v2.id}/decidi/", {"esito": "approvata", "motivo": "Documento verificato a mano"}); u2.refresh_from_db(); esito("il moderatore approva: ora è attivo", u2.stato_account == "attivo")
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
