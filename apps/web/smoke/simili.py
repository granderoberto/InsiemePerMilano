import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from django.test import Client
from core.models import *
from core.services import simili
PW="DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
base = Segnalazione.objects.filter(stato_id=3, nascosta=False, eliminata_il__isnull=True, autore_id__lte=154).order_by("-id").first()
lat, lon = float(base.latitudine), float(base.longitudine)
r = simili.trova_simili(lat, lon, base.titolo, base.descrizione)
esito("la stessa segnalazione, nella stessa posizione, è la prima", r and r[0]["id"] == base.id and r[0]["distanza_m"] <= 10, f"{len(r)} risultati")
r2 = simili.trova_simili(lat, lon, base.titolo, base.descrizione, escludi=base.id); esito("escludi la propria (in modifica)", all(x["id"] != base.id for x in r2))
r3 = simili.trova_simili(lat + 0.03, lon + 0.03, base.titolo, base.descrizione); esito("a 4 km non è 'la stessa zona'", all(x["id"] != base.id for x in r3))
r4 = simili.trova_simili(lat, lon, "Concerto di musica jazz serale", "Una serata di strumenti e sassofoni", categorie=[]); esito("testo senza parole in comune e senza categoria: nessuna proposta", base.id not in [x["id"] for x in r4])
cat = base.classificazioni.first().categoria_id
r5 = simili.trova_simili(lat, lon, "Altro tema del tutto", "xyz qwe", categorie=[cat]); esito("stessa categoria a due passi: proposta anche con testo diverso", base.id in [x["id"] for x in r5])
esito("risultati ordinati per somiglianza e al massimo 5", len(r) <= 5 and [x["somiglianza"] for x in r] == sorted([x["somiglianza"] for x in r], reverse=True))
esito("solo segnalazioni pubbliche", all(Segnalazione.objects.get(pk=x["id"]).e_pubblica for x in r))
# API
c = Client(); j = c.get("/api/simili/", {"lat": lat, "lon": lon, "titolo": base.titolo, "descrizione": base.descrizione}).json()
esito("API: visitatore vede le simili ma non può sostenere", j["simili"] and j["puo_sostenere"] is False)
esito("API: coordinate mancanti -> elenco vuoto", c.get("/api/simili/").json() == {"simili": []})
altro = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$").exclude(pk=base.autore_id).order_by("id")[40]
B = Client(); B.login(email=altro.email, password=PW)
Sostegno.objects.filter(utente=altro, segnalazione=base).delete()
j = B.get("/api/simili/", {"lat": lat, "lon": lon, "titolo": base.titolo, "descrizione": base.descrizione}).json(); x = next(i for i in j["simili"] if i["id"] == base.id)
esito("API: utente attivo può sostenere, non l'ha ancora fatto", j["puo_sostenere"] and not x["sostenuta"] and not x["propria"])
r = B.post(f"/api/segnalazioni/{base.id}/sostieni/"); esito("sostegno diretto dalla pagina (JSON)", r.status_code == 200 and r.json()["sostenuta"] is True, str(r.json()))
r = B.post(f"/api/segnalazioni/{base.id}/sostieni/"); esito("secondo clic: ritira il sostegno", r.json()["sostenuta"] is False)
A = Client(); A.login(email=base.autore.email, password=PW); r = A.post(f"/api/segnalazioni/{base.id}/sostieni/")
esito("l'autore non può sostenere la propria (trigger) -> errore chiaro", r.status_code == 400 and "autore" in r.json()["errore"], r.json().get("errore", "")[:50])
j = A.get("/api/simili/", {"lat": lat, "lon": lon, "titolo": base.titolo, "descrizione": base.descrizione}).json(); esito("l'autore la vede come 'propria'", next(i for i in j["simili"] if i["id"] == base.id)["propria"])
esito("sostegno JSON da visitatore -> accesso richiesto", Client().post(f"/api/segnalazioni/{base.id}/sostieni/").status_code == 302)
r = B.get("/segnalazioni/nuova/"); esito("la pagina del modulo contiene il pannello", r.status_code == 200 and 'id="simili"' in r.content.decode() and "URL_SIMILI" in r.content.decode())
