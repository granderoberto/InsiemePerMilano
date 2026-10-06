import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from datetime import timedelta
from django.test import Client
from django.utils import timezone
from core.models import *
PW="DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def cl(u): c = Client(); c.login(email=u.email, password=PW); return c
adm = Utente.objects.get(ruolo="amministratore"); mod = Utente.objects.filter(ruolo="moderatore").first()
norm = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$").order_by("id")[10]
A, M, N = cl(adm), cl(mod), cl(norm)
for url in ["/amministrazione/", "/amministrazione/utenti/", "/amministrazione/utenti/?q=a&ruolo=utente&stato=attivo&metodo=spid", f"/amministrazione/utenti/{norm.id}/", "/amministrazione/registro/",
            "/amministrazione/registro/?operazione=sostegno&attore=utente", "/amministrazione/statistiche/", "/amministrazione/statistiche/?periodo=7", "/amministrazione/statistiche/?periodo=tutto", "/amministrazione/categorie/", "/amministrazione/normative/", "/normative/"]:
    r = A.get(url); esito(f"admin GET {url}", r.status_code == 200, r.status_code if r.status_code != 200 else "")
for c, nome in ((M, "moderatore"), (N, "utente"), (Client(), "visitatore")):
    esito(f"{nome} non entra in /amministrazione/", c.get("/amministrazione/utenti/").status_code in (404, 302))
r = A.get("/amministrazione/statistiche/utenti_piu_attivi.csv?periodo=30"); t = r.content.decode("utf-8-sig")
esito("CSV scaricabile con intestazioni", r.status_code == 200 and "attachment" in r["Content-Disposition"] and t.splitlines()[0] == "Utente;Azioni" and len(t.splitlines()) > 2, t.splitlines()[1][:40] if len(t.splitlines())>1 else "")
esito("CSV inesistente -> 404", A.get("/amministrazione/statistiche/boh.csv").status_code == 404)
# modifica dati
v0 = (norm.nome, norm.cognome, norm.email, norm.data_nascita, norm.quartiere_id)
base = {"nome": norm.nome, "cognome": norm.cognome, "email": norm.email, "data_nascita": norm.data_nascita.isoformat(), "quartiere": norm.quartiere_id or ""}
A.post(f"/amministrazione/utenti/{norm.id}/modifica/", {**base, "nome": "Nomecorretto"}); norm.refresh_from_db(); esito("modifica senza motivo rifiutata", norm.nome == v0[0])
A.post(f"/amministrazione/utenti/{norm.id}/modifica/", {**base, "nome": "Nomecorretto", "motivo": "Errore di battitura"}); norm.refresh_from_db(); esito("modifica con motivo", norm.nome == "Nomecorretto")
l = LogAttivita.objects.filter(tabella="utenti", id_oggetto=norm.id, operazione="modifica").order_by("-id").first(); esito("modifica nel log con motivo e valori", l and l.dati_nuovi["motivo"] == "Errore di battitura" and l.dati_precedenti["nome"] == v0[0])
r = A.post(f"/amministrazione/utenti/{norm.id}/modifica/", {**base, "data_nascita": (timezone.now().date() - timedelta(days=365*10)).isoformat(), "motivo": "prova"}, follow=True)
norm.refresh_from_db(); esito("under 14 bloccato dal trigger", norm.data_nascita == v0[3], " | ".join(str(m) for m in (r.context["messages"] if r.context else []))[:60])
A.post(f"/amministrazione/utenti/{norm.id}/modifica/", {**base, "motivo": "ripristino"})
# ruoli
A.post(f"/amministrazione/utenti/{norm.id}/ruolo/", {"ruolo": "moderatore"}); norm.refresh_from_db(); esito("promosso a moderatore", norm.ruolo == "moderatore")
esito("ora vede la moderazione", cl(norm).get("/moderazione/").status_code == 200)
A.post(f"/amministrazione/utenti/{norm.id}/ruolo/", {"ruolo": "utente"}); norm.refresh_from_db(); esito("riportato a utente", norm.ruolo == "utente")
A.post(f"/amministrazione/utenti/{adm.id}/ruolo/", {"ruolo": "utente"}); adm.refresh_from_db(); esito("nessuno cambia il proprio ruolo", adm.ruolo == "amministratore")
esito("cambio ruolo nel log", LogAttivita.objects.filter(operazione="cambio_ruolo", id_oggetto=norm.id).count() >= 2)
# sospensioni
M.post(f"/moderazione/utenti/{norm.id}/sospendi/", {"motivo": "Comportamento scorretto", "giorni": "3"}); norm.refresh_from_db(); s = norm.sospensioni.first()
esito("moderatore sospende (3 giorni)", norm.stato_account == "sospeso" and s and s.fine and s.moderatore_id == mod.id)
Nn = cl(norm); r = Nn.post(f"/segnalazioni/{Segnalazione.objects.filter(stato_id=3, nascosta=False).exclude(autore=norm).first().id}/sostieni/"); esito("sospeso non può interagire", r.status_code == 302 and Sostegno.objects.filter(utente=norm).count() == Sostegno.objects.filter(utente=norm).count())
esito("notifica di sospensione", Notifica.objects.filter(utente=norm, tipo="stato_account", messaggio__contains="sospeso").exists())
A.post(f"/amministrazione/utenti/{norm.id}/riattiva/"); norm.refresh_from_db(); s.refresh_from_db(); esito("amministratore riattiva", norm.stato_account == "attivo" and s.revocata_il and s.revocante_id == adm.id)
A.post(f"/amministrazione/utenti/{adm.id}/sospendi/", {"motivo": "x"}); adm.refresh_from_db(); esito("non ci si sospende da soli", adm.stato_account == "attivo")
# scadenza automatica
M.post(f"/moderazione/utenti/{norm.id}/sospendi/", {"motivo": "Prova scadenza", "giorni": "1"}); s2 = Sospensione.objects.filter(utente=norm, revocata_il__isnull=True).first()
Sospensione.objects.filter(pk=s2.pk).update(inizio=timezone.now()-timedelta(days=3), fine=timezone.now()-timedelta(days=1))
Client().login(email=norm.email, password=PW); c = Client(); c.login(email=norm.email, password=PW); c.get("/profilo/"); norm.refresh_from_db()
esito("la sospensione scaduta finisce da sola", norm.stato_account == "attivo" and Sospensione.objects.get(pk=s2.pk).revocata_il is not None)
# categorie
A.post("/amministrazione/categorie/", {"azione": "aggiungi", "nome": "Categoria di prova", "descrizione": "x"}); c1 = Categoria.objects.filter(nome="Categoria di prova").first(); esito("categoria aggiunta", c1 is not None)
A.post("/amministrazione/categorie/", {"azione": "aggiungi", "nome": "categoria di PROVA"}); esito("categoria duplicata rifiutata", Categoria.objects.filter(nome__iexact="categoria di prova").count() == 1)
A.post("/amministrazione/categorie/", {"azione": "attiva", "id": c1.id}); c1.refresh_from_db(); esito("categoria disattivata", not c1.attiva)
esito("categoria disattivata non nel modulo", "Categoria di prova" not in cl(norm).get("/segnalazioni/nuova/").content.decode())
Categoria.objects.filter(pk=c1.pk).delete()
# normative
n_prima = DocumentoNormativo.objects.count()
A.post("/amministrazione/normative/", {"tipo": "privacy", "versione": "2", "testo": "Nuovo testo segnaposto."}); esito("nuova versione pubblicata", DocumentoNormativo.objects.count() == n_prima + 1)
esito("notifica 'normativa_aggiornata' agli utenti", Notifica.objects.filter(utente=norm, tipo="normativa_aggiornata").exists())
pub = Segnalazione.objects.filter(stato_id=3, nascosta=False).exclude(autore=norm).first()
r = cl(norm).post(f"/segnalazioni/{pub.id}/sostieni/"); esito("senza nuova accettazione non si interagisce -> pagina di accettazione", r.status_code == 302 and "normative/accetta" in r["Location"])
c = cl(norm); r = c.post("/normative/accetta/", {}); esito("accettazione incompleta rifiutata", r.status_code == 200)
nuovi = [d.id for d in __import__("core.services.normative", fromlist=["x"]).da_accettare(norm)]; r = c.post("/normative/accetta/", {"documento": nuovi}); esito("accettazione registrata", r.status_code == 302 and not __import__("core.services.normative", fromlist=["x"]).da_accettare(norm))
Sostegno.objects.filter(utente=norm, segnalazione=pub).delete(); r = c.post(f"/segnalazioni/{pub.id}/sostieni/"); esito("poi può di nuovo sostenere", Sostegno.objects.filter(utente=norm, segnalazione=pub).exists())

# pulizia: la versione 2 di prova non deve restare nel database
for d in DocumentoNormativo.objects.filter(versione="2"):
    Consenso.objects.filter(documento=d).delete(); d.delete()
Notifica.objects.filter(tipo="normativa_aggiornata", messaggio__contains="(2)").delete()
esito("pulizia: versione di prova rimossa", not DocumentoNormativo.objects.filter(versione="2").exists())
