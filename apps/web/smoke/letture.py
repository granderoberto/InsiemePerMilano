import os, django, json
import sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from django.test import Client
from core.models import Segnalazione, Utente
c = Client()
pub = Segnalazione.objects.filter(stato_id=3, nascosta=False).first()
nonpub = Segnalazione.objects.filter(stato_id=2, eliminata_il__isnull=True).first()
cred = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$").first()
mod = Utente.objects.filter(ruolo="moderatore").first()
def get(url, cli=c, atteso=200):
    r = cli.get(url); ok = "OK " if r.status_code == atteso else "!! "
    print(f"{ok}{r.status_code} {url}" + ("" if ok == "OK " else f"  (atteso {atteso})")); return r
get("/"); get("/?vista=mappa"); get("/?q=semaforo&ordine=sostegni"); get("/?quartiere=1&categoria=1&stato=5&tipo=problema")
r = get("/api/segnalazioni.geojson"); print("   feature:", len(json.loads(r.content)["features"]))
get(f"/segnalazioni/{pub.id}/"); get(f"/segnalazioni/{nonpub.id}/", atteso=404)
get("/statistiche/"); get("/statistiche/?periodo=30&quartiere=1")
get("/accedi/"); get("/registrati/"); get("/accedi/spid/")
get("/segnalazioni/nuova/", atteso=302); get("/profilo/", atteso=302); get("/moderazione/", atteso=302)
get("/media/demo/12.jpg"); get("/api/suggerisci-categorie/?titolo=Semaforo&descrizione=il semaforo pedonale dura poco"); get("/api/quartiere/?lat=45.4642&lon=9.19")
# utente normale loggato
u = Client(); ok = u.login(email=cred.email, password="DemoMilano2026!"); print("login utente:", ok)
for url in ["/", "/profilo/", "/notifiche/", "/segnalazioni/nuova/"]: get(url, u)
get(f"/segnalazioni/{nonpub.id}/", u, atteso=200 if nonpub.autore_id == cred.id else 404)
get("/moderazione/", u, atteso=404)
# moderatore (hash bcrypt come gli altri utenti con credenziali)
m = Client(); print("login moderatore:", m.login(email=mod.email, password="DemoMilano2026!"))
get("/moderazione/", m); get(f"/moderazione/segnalazioni/{nonpub.id}/", m); get(f"/segnalazioni/{nonpub.id}/", m)
# amministratore creato all'installazione (senza verifica del documento): può interagire senza consenso biometrico
adm = Utente.objects.get(ruolo="amministratore"); a = Client(); a.login(email=adm.email, password="DemoMilano2026!"); get("/segnalazioni/nuova/", a)
