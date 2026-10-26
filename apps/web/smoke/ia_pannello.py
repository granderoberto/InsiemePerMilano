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
    with override_settings(IA_URL={"openrouter": "http://127.0.0.1:1", "groq": "http://127.0.0.1:1"}, OPENROUTER_API_KEY="x", GROQ_API_KEY="", IA_FORNITORI=["openrouter", "groq"], IA_MODALITA="coda"), transaction.atomic():
        quota.azzera_cache()
        r = client(adm).get("/amministrazione/ia/")
        esito("pannello: pagina aperta dall'amministratore", r.status_code == 200 and b"Fornitori e quota di oggi" in r.content and b"Ultime richieste ai fornitori" in r.content)
        esito("pannello: stato, modalità e chiave mostrati (mai il valore)", b"coda in background" in r.content and b"pronto" in r.content and b"x</" not in r.content)
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
        # ---- registro dei controlli eseguiti (esito + motivazione)
        r0 = client(adm).get("/amministrazione/ia/controlli/"); esito("controlli eseguiti: pagina aperta dall'amministratore", r0.status_code == 200 and b"Ultimo" not in b"" and "Controlli IA".encode() in r0.content)
        log.registra(None, "decisione_ia", "segnalazioni", s.id, None, {"esito_moderazione": "dubbio", "motivazione": "foto non coerenti", "segnali": ["foto", "volti_sfocati:1"], "fornitore": "openrouter", "modello": "m1:free", "secondi": 3.2})
        log.registra(None, "decisione_ia", "commenti", c2.id, None, {"esito_moderazione": "dubbio", "motivazione": "insulto a un utente", "segnali": ["insulto"], "fornitore": "openrouter", "modello": "m1:free"})
        log.registra(None, "decisione_ia", "commenti", 0, None, {"esito_moderazione": "bloccato", "fornitore": "locale", "non_pubblicato": True, "segnali": ["minaccia"]})
        pag = client(adm).get("/amministrazione/ia/controlli/").content.decode()
        esito("controlli eseguiti: motivazione, segnali, modello e esito della segnalazione", "foto non coerenti" in pag and "con foto" in pag and "volti sfocati: 1" in pag and "m1:free" in pag and s.titolo[:25] in pag)
        esito("controlli eseguiti: commento con motivazione e link", "insulto a un utente" in pag and f"#commento-{c2.id}" in pag)
        esito("controlli eseguiti: commento bloccato e non pubblicato visibile", "(commento non pubblicato)" in pag and "minaccia" in pag and "controllo locale" in pag)
        esito("filtro per esito", "foto non coerenti" not in client(adm).get("/amministrazione/ia/controlli/?esito=bloccato").content.decode() and "(commento non pubblicato)" in client(adm).get("/amministrazione/ia/controlli/?esito=bloccato").content.decode())
        t1 = client(adm).get("/amministrazione/ia/controlli/?tipo=segnalazioni&q=non+coerenti").content.decode(); t2 = client(adm).get("/amministrazione/ia/controlli/?tipo=commenti").content.decode()
        esito("filtro per tipo e per motivazione", "foto non coerenti" in t1 and "insulto a un utente" not in t1 and "foto non coerenti" not in t2 and "insulto a un utente" in t2)
        esito("filtro per chi ha deciso (modello / controllo locale)", "(commento non pubblicato)" not in client(adm).get("/amministrazione/ia/controlli/?fonte=modello").content.decode() and "(commento non pubblicato)" in client(adm).get("/amministrazione/ia/controlli/?fonte=locale").content.decode())
        esito("panoramica: ultimi controlli con motivazione", "foto non coerenti" in client(adm).get("/amministrazione/ia/").content.decode())
        esito("controlli e richieste: vietati ai non amministratori", client(mod).get("/amministrazione/ia/controlli/").status_code == 404 and client(norm).get("/amministrazione/ia/richieste/").status_code == 404)
        from core.services.ia import quota as q_
        q_.registra_richiesta("segnalazione", "openrouter", "m1:free", 200, 12.0, True); q_.registra_richiesta("segnalazione", "openrouter", "m1:free", 404, 0.1, False, "privacy")
        q_.registra_richiesta("commento", "groq", "llama-x", 200, 1.5, True)
        ric = client(adm).get("/amministrazione/ia/richieste/").content.decode()
        esito("richieste al fornitore: tutte, anche le fallite, con 404 e consumo", "m1:free" in ric and "404" in ric and "privacy" in ric)
        esito("richieste: colonna fornitore e filtro per fornitore", "groq · llama-x" in ric and "llama-x" not in client(adm).get("/amministrazione/ia/richieste/?fornitore=openrouter").content.decode() and "llama-x" in client(adm).get("/amministrazione/ia/richieste/?fornitore=groq").content.decode())
        pan = client(adm).get("/amministrazione/ia/").content.decode()
        esito("pannello: una riga di quota per ogni fornitore, con lo stato", "Fornitori e quota di oggi" in pan and "OpenRouter" in pan and "Groq" in pan and "manca GROQ_API_KEY" in pan and "non configurato" in pan)
        with override_settings(GROQ_API_KEY="chiave-g"):
            pan = client(adm).get("/amministrazione/ia/").content.decode()
            esito("pannello: con la chiave Groq risulta pronto e mostra la sua quota e la catena", "pronto" in pan and "groq: openai/gpt-oss-20b" in pan and "chiave-g" not in pan)
        from django.core.management import call_command
        import io
        buf = io.StringIO(); call_command("ia_lavora", "--stato", stdout=buf); out = buf.getvalue()
        esito("ia_lavora --stato: quota di ogni fornitore e catene", "OpenRouter:" in out and "Groq: non configurato" in out and "Catena testo:" in out and "Coda:" in out, out[:200])
        esito("controlli eseguiti: filtro per fornitore", "foto non coerenti" in client(adm).get("/amministrazione/ia/controlli/?fornitore=openrouter").content.decode() and "foto non coerenti" not in client(adm).get("/amministrazione/ia/controlli/?fornitore=groq").content.decode())
        esito("richieste: filtro «non consumata»", "privacy" in client(adm).get("/amministrazione/ia/richieste/?consumata=no").content.decode())
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
