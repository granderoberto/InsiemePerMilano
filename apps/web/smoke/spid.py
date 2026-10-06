"""Sicurezza del ritorno SPID/CIE sul sito (token del ponte) e dei reindirizzamenti. Non serve il servizio SPID acceso."""
import os, sys, hashlib, time, uuid, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from unittest import mock
from django.conf import settings
from django.core import signing
from django.test import Client
from core.models import *
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
SALT, CHIAVE = "lnc-ponte-spid", settings.SPID_BRIDGE_SECRET
def token(cf="RSSMRA80A01F205X", metodo="spid", nascita="1980-01-01", email="mario.rossi.spid@example.org", chiave=CHIAVE, **kw):
    d = {"metodo": metodo, "cf": cf, "nome": "Mario", "cognome": "Rossi", "email": email, "nascita": nascita, "emittente": "http://idp.test", "nonce": uuid.uuid4().hex, **kw}
    return signing.dumps(d, key=chiave, salt=SALT)
def avviato(metodo="spid", next=""):
    c = Client(); r = c.get(f"/accedi/spid/avvia/{metodo}/" + (f"?next={next}" if next else ""))
    return c, r
def msg(r):
    return " | ".join(str(m) for m in (r.context["messages"] if r.context else []))
esito("la configurazione è attiva (servizio e segreto)", settings.SPID_CIE_ATTIVO)
c, r = avviato(); esito("avvio: rimanda al servizio SPID", r.status_code == 302 and r["Location"].startswith(settings.SPID_SERVIZIO_URL.rstrip("/") + "/ponte/avvia/?profilo=spid"), r["Location"][:70])
esito("metodo sconosciuto -> 404", Client().get("/accedi/spid/avvia/google/").status_code == 404)
r = Client().get("/accedi/spid/ritorno/?t=" + token()); esito("ritorno senza aver avviato l'accesso: rifiutato", r.status_code == 302 and "/accedi/spid/" in r["Location"] and not Utente.objects.filter(email="mario.rossi.spid@example.org").exists())
c, _ = avviato(); r = c.get("/accedi/spid/ritorno/?t=" + token(chiave="altro-segreto"), follow=True); esito("firma con un altro segreto: rifiutata", "non è valida" in r.content.decode() and "spid_nuovo" not in c.session)
c, _ = avviato(); r = c.get("/accedi/spid/ritorno/?t=abc.def.ghi", follow=True); esito("token inventato: rifiutato", "spid_nuovo" not in c.session)
c, _ = avviato()
with mock.patch("time.time", return_value=time.time() - 400): vecchio = token()
r = c.get("/accedi/spid/ritorno/?t=" + vecchio, follow=True); esito("token scaduto (oltre 120 s): rifiutato", "spid_nuovo" not in c.session)
c, _ = avviato(); t = token(); r = c.get("/accedi/spid/ritorno/?t=" + t); esito("token valido: porta al completamento", r.status_code == 302 and r["Location"].endswith("/accedi/spid/completa/"))
c2, _ = avviato(); r = c2.get("/accedi/spid/ritorno/?t=" + t, follow=True); esito("lo stesso token non si riusa (anche da un altro accesso)", "già stata usata" in r.content.decode() and "spid_nuovo" not in c2.session)
c, _ = avviato("cie"); r = c.get("/accedi/spid/ritorno/?t=" + token(metodo="spid"), follow=True); esito("metodo diverso da quello avviato: rifiutato", "spid_nuovo" not in c.session)
c, _ = avviato(); r = c.get("/accedi/spid/ritorno/?t=" + token(cf="<script>"), follow=True); esito("codice fiscale non valido: rifiutato", "spid_nuovo" not in c.session)
c, _ = avviato(); c.get("/accedi/spid/ritorno/?t=" + token()); r = c.get("/accedi/spid/ritorno/?t=" + token(), follow=True); esito("il ritorno vale una volta per avvio", "non è valida" in r.content.decode() or "scaduta" in r.content.decode())
r = Client().get("/accedi/spid/ritorno/?errore=cf", follow=True); esito("identità senza codice fiscale: messaggio chiaro", "codice fiscale" in r.content.decode())
r = Client().get("/accedi/spid/completa/", follow=True); esito("completamento senza identità in sospeso: rifiutato", "scaduta" in r.content.decode())
# completamento
CONS = {k: "on" for k in ["privacy", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"]}
def nuovo(cf, nascita="1980-01-01", **kw):
    c, _ = avviato(); c.get("/accedi/spid/ritorno/?t=" + token(cf=cf, nascita=nascita, email=kw.pop("email", f"{cf.lower()}@example.org"))); return c
c = nuovo("MNRGLI99A01F205X", nascita="2020-01-01"); r = c.post("/accedi/spid/completa/", {"email": "minorenne.spid@example.org", **CONS}); esito("under 14: account non creato", not Utente.objects.filter(email="minorenne.spid@example.org").exists() and "14 anni" in r.content.decode())
c = nuovo("SENSCN80A01F205X", nascita=""); r = c.post("/accedi/spid/completa/", {"email": "senza.data@example.org", **CONS}); esito("senza data di nascita dal gestore: viene chiesta", "Inserisci la data di nascita" in r.content.decode())
r = c.post("/accedi/spid/completa/", {"email": "senza.data@example.org", "data_nascita": "1985-06-15", **CONS}); esito("data inserita a mano: account creato", Utente.objects.filter(email="senza.data@example.org", data_nascita="1985-06-15").exists())
esiste = Utente.objects.filter(metodo_registrazione="credenziali").first()
c = nuovo("DPLCNF80A01F205X"); r = c.post("/accedi/spid/completa/", {"email": esiste.email, **CONS}); esito("email già di un altro account: rifiutata con indicazione", "Esiste già un account" in r.content.decode() and not Utente.objects.filter(codice_fiscale_hash=hashlib.sha256(b"DPLCNF80A01F205X").hexdigest()).exists())
r = c.post("/accedi/spid/completa/", {"email": "dpl.cnf@example.org", "privacy": "on"}); esito("senza tutti i consensi: account non creato", not Utente.objects.filter(email="dpl.cnf@example.org").exists())
r = c.post("/accedi/spid/completa/", {"email": "dpl.cnf@example.org", **CONS}); u = Utente.objects.filter(email="dpl.cnf@example.org").first()
esito("account creato: attivo, solo hash del codice fiscale, 5 consensi", u and u.stato_account == "attivo" and u.password is None and u.codice_fiscale_hash == hashlib.sha256(b"DPLCNF80A01F205X").hexdigest() and u.consensi.count() == 5)
esito("l'utente risulta autenticato", "_auth_user_id" in c.session)
esito("il codice fiscale in chiaro non è da nessuna parte nel registro", not LogAttivita.objects.filter(dati_nuovi__icontains="DPLCNF80A01F205X").exists())
c, _ = avviato(); r = c.get("/accedi/spid/ritorno/?t=" + token(cf="DPLCNF80A01F205X"), follow=True); esito("secondo accesso: entra senza ripetere il completamento", "_auth_user_id" in c.session and "completa" not in r.redirect_chain[-1][0] if r.redirect_chain else False)
Utente.objects.filter(pk=u.pk).update(stato_account="eliminato", eliminato_il="2026-01-01 00:00:00"); c, _ = avviato(); r = c.get("/accedi/spid/ritorno/?t=" + token(cf="DPLCNF80A01F205X"), follow=True)
esito("account eliminato: accesso negato", "_auth_user_id" not in c.session and "eliminato" in r.content.decode())
# reindirizzamenti aperti
for dest in ("//evil.example/x", "https://evil.example/", "/\\evil.example"):
    c, _ = avviato(next=dest); c.get("/accedi/spid/ritorno/?t=" + token(cf="OPNRDR80A01F205X", email="open.redirect@example.org"))
    r = c.post("/accedi/spid/completa/", {"email": "open.redirect@example.org", **CONS}); esito(f"SPID: next={dest!r} non porta fuori dal sito", r.status_code == 302 and r["Location"] in ("/", "") or r["Location"].startswith("/") and not r["Location"].startswith("//"), r["Location"])
    Utente.objects.filter(email="open.redirect@example.org").update(codice_fiscale_hash=None, metodo_registrazione="credenziali", password_hash="x") if False else None
u = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$", mfa_attiva=False).order_by("id")[5]
for dest in ("//evil.example/x", "https://evil.example/"):
    r = Client().post("/accedi/", {"email": u.email, "password": "DemoMilano2026!", "next": dest}); esito(f"login: next={dest!r} non porta fuori dal sito", r.status_code == 302 and r["Location"] == "/", r["Location"])
r = Client().post("/accedi/", {"email": u.email, "password": "DemoMilano2026!", "next": "/profilo/"}); esito("login: un next interno funziona", r["Location"] == "/profilo/")
