"""Pannello amministratore dei controlli IA e motivazioni nella coda del moderatore (fase 4). Nessuna richiesta di rete.
Tutto in una transazione annullata alla fine."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from django.db import transaction
from django.test import Client, override_settings
from core.models import *
from core.services import log
from core.services.ia import coda, esiti, quota
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
class Rollback(Exception): pass
adm = Utente.objects.filter(ruolo="amministratore", stato_account="attivo").first()
mod = Utente.objects.filter(ruolo="moderatore", stato_account="attivo").first()
norm = Utente.objects.filter(ruolo="utente", stato_account="attivo").first()
def client(u): c = Client(); c.force_login(u, backend="core.backends.UtenteBackend"); return c
try:
    with override_settings(OPENROUTER_URL="http://127.0.0.1:1", OPENROUTER_API_KEY="x", IA_MODALITA="coda"), transaction.atomic():
        quota.azzera_cache()
        r = client(adm).get("/amministrazione/ia/")
        esito("pannello: pagina aperta dall'amministratore", r.status_code == 200 and b"Quota di oggi" in r.content and b"Ultime richieste a OpenRouter" in r.content)
        esito("pannello: stato, modalità e chiave mostrati (mai il valore)", b"coda in background" in r.content and b"presente" in r.content and b"x</" not in r.content)
        esito("pannello: il moderatore e l'utente non lo aprono", client(mod).get("/amministrazione/ia/").status_code == 404 and client(norm).get("/amministrazione/ia/").status_code == 404)
        esito("menu: voce «Controlli IA»", b"Controlli IA" in client(adm).get("/amministrazione/").content)
        # ---- coda nel pannello
        s = Segnalazione.objects.filter(stato_id=2, eliminata_il__isnull=True).first()
        from core.services.ia import prefiltro
        riga = coda.accoda(prefiltro.analizza("Marciapiede rotto", ha_media=True), segnalazione=s)
        coda.chiudi([riga], "fallito", "nessun modello ha risposto")
        r = client(adm).get("/amministrazione/ia/")
        esito("coda: la riga fallita compare con il suo errore", s.titolo[:20].encode() in r.content and b"nessun modello ha risposto" in r.content)
        client(adm).post("/amministrazione/ia/riprova_falliti/"); riga.refresh_from_db()
        esito("«Rimetti in coda i falliti»: riga di nuovo in coda, tentativi azzerati", riga.stato == "in_coda" and riga.tentativi == 0 and riga.errore is None)
        esito("l'azione dell'amministratore è nel registro", LogAttivita.objects.filter(tabella="coda_ia", operazione="modifica", utente=adm).exists())
        esito("azioni vietate a chi non è amministratore", client(mod).post("/amministrazione/ia/riprova_falliti/").status_code == 404)
        # ---- «esegui un controllo ora»
        coda.chiudi([riga], "saltato")
        r = client(adm).post("/amministrazione/ia/esegui/", follow=True); esito("esegui con coda vuota: messaggio chiaro", "Niente da controllare".encode() in r.content)
        with override_settings(IA_MODALITA="sincrona"):
            r = client(adm).post("/amministrazione/ia/esegui/", follow=True); esito("esegui con modalità sincrona: non attiva", b"non sono attivi" in r.content)
        esito("azione sconosciuta: 404", client(adm).post("/amministrazione/ia/boh/").status_code == 404)
        # ---- motivazione al moderatore
        c2 = Commento.objects.filter(eliminato_il__isnull=True).order_by("-creato_il").first()
        s.esito_moderazione = "dubbio"; s.save(update_fields=["esito_moderazione"])
        log.registra(None, "decisione_ia", "segnalazioni", s.id, None, {"esito_moderazione": "dubbio", "motivazione": "insulto a un utente", "segnali": ["insulto", "volti_sfocati:2"], "fornitore": "openrouter", "modello": "m1:free"})
        Commento.objects.filter(pk=c2.pk).update(esito_moderazione="dubbio")
        log.registra(None, "decisione_ia", "commenti", c2.id, None, {"esito_moderazione": "dubbio", "motivazione": "numero di telefono", "segnali": ["telefono"], "fornitore": "openrouter"})
        cm = client(mod); dash = cm.get("/moderazione/").content.decode()
        esito("coda del moderatore: motivo e segnali della segnalazione", "insulto a un utente" in dash and "insulto, volti sfocati: 2" in dash and "controllo con modello" in dash)
        esito("coda del moderatore: motivo del commento", "numero di telefono" in dash)
        det = cm.get(f"/moderazione/segnalazioni/{s.id}/").content.decode()
        esito("scheda della segnalazione: motivo mostrato", "insulto a un utente" in det and "Controlli automatici" in det)
        d = esiti.ultime_decisioni("segnalazioni", [s.id, 999999999]); esito("ultime_decisioni: l'ultima vale, gli ignoti sono assenti", d[s.id]["motivazione"] == "insulto a un utente" and 999999999 not in d)
        log.registra(None, "decisione_ia", "segnalazioni", s.id, None, {"esito_moderazione": "ok", "motivazione": "", "fornitore": "locale"})
        esito("ultime_decisioni: dopo una nuova decisione vale la più recente", esiti.ultime_decisioni("segnalazioni", [s.id])[s.id]["esito"] == "ok")
        # ---- presa atomica della coda
        a = coda.accoda(prefiltro.analizza("Buca", ha_media=True), segnalazione=Segnalazione.objects.filter(eliminata_il__isnull=True)[1])
        b = coda.accoda(prefiltro.analizza("Buca profonda", ha_media=True), segnalazione=Segnalazione.objects.filter(eliminata_il__isnull=True)[2])
        CodaIA.objects.filter(pk=b.pk).update(stato="in_corso")   # preso da un altro lavoratore
        esito("prendi: se un'altra riga è già presa non ne prende nessuna", coda.prendi([a, b]) is False)
        a.refresh_from_db(); esito("prendi: la riga già presa da noi torna in coda con i tentativi a posto", a.stato == "in_coda" and a.tentativi == 0)
        CodaIA.objects.filter(pk=b.pk).update(stato="in_coda"); esito("prendi: tutte libere, le prende", coda.prendi([a, b]) is True and CodaIA.objects.get(pk=a.pk).stato == "in_corso")
        raise Rollback()
except Rollback:
    pass
