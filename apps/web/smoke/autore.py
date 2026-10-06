import os, io, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from core.models import *
PW="DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def foto(nome="f.jpg"):
    b=io.BytesIO(); Image.new("RGB",(60,40),(30,120,60)).save(b,"JPEG"); return SimpleUploadedFile(nome,b.getvalue(),content_type="image/jpeg")
au = Utente.objects.filter(ruolo="utente", stato_account="attivo", password__startswith="$2b$").order_by("id")[3]
mod = Utente.objects.filter(ruolo="moderatore").first(); A, M = Client(), Client()
A.login(email=au.email, password=PW); M.login(email=mod.email, password=PW)
cat = Categoria.objects.get(nome="Decoro urbano").id
dati = {"tipo":"problema","titolo":"Panchine rotte nel giardino","descrizione":"Le panchine del giardino pubblico hanno assi mancanti e sono pericolose per i bambini.","categorie":[cat],"latitudine":"45.4642","longitudine":"9.19"}
A.post("/segnalazioni/nuova/", {**dati, "media": [foto()]}); s = Segnalazione.objects.filter(autore=au, titolo="Panchine rotte nel giardino").order_by("-id").first(); esito("creata", s and s.stato_id == 2)
r = A.get(f"/segnalazioni/{s.id}/modifica/"); esito("pagina di modifica", r.status_code == 200 and "Modifica la segnalazione" in r.content.decode())
r = A.post(f"/segnalazioni/{s.id}/modifica/", {**dati, "titolo":"Panchine rotte e giochi rovinati","descrizione":dati["descrizione"]+" Anche i giochi sono rovinati.","latitudine":"45.4868","longitudine":"9.188","media":[foto("n.jpg")]}, follow=True)
s.refresh_from_db(); esito("modifica salvata (titolo, posizione -> Isola, 2 media, 1 copertina)", s.titolo.startswith("Panchine rotte e giochi") and s.quartiere_id == 11 and s.media.count() == 2 and s.media.filter(copertina=True).count() == 1, f"quartiere={s.quartiere_id} media={s.media.count()}")
l = LogAttivita.objects.filter(operazione="modifica", tabella="segnalazioni", id_oggetto=s.id).first(); esito("versione precedente nel log", l and l.dati_precedenti["titolo"] == "Panchine rotte nel giardino" and l.dati_nuovi["n_media"] == 2)
m0 = list(s.media.order_by("ordine").values_list("id", flat=True))
r = A.post(f"/segnalazioni/{s.id}/modifica/", {**dati, "rimuovi_media": [m0[0], m0[1]]}); esito("senza media rifiutata", Media.objects.filter(segnalazione=s).count() == 2)
r = A.post(f"/segnalazioni/{s.id}/modifica/", {**dati, "rimuovi_media": [m0[0]]}, follow=True); esito("rimozione di un file", Media.objects.filter(segnalazione=s).count() == 1)
# blocco IA + richiesta di revisione
A.post(f"/segnalazioni/{s.id}/modifica/", {**dati, "titolo":"Avviso", "descrizione":"Se non intervenite ti ammazzo, le panchine sono rotte da mesi e nessuno fa nulla."}, follow=True)
s.refresh_from_db(); esito("testo con minaccia -> esito bloccato", s.esito_moderazione == "bloccato")
r = A.post(f"/segnalazioni/{s.id}/revisione/", {"motivo": "Era una frase scritta male, mi scuso."}, follow=True); rr = RichiestaRevisione.objects.filter(segnalazione=s).first(); esito("richiesta di revisione creata", rr is not None and rr.stato == "aperta")
r = A.post(f"/segnalazioni/{s.id}/revisione/", {"motivo": "di nuovo"}); esito("seconda richiesta non duplicata", RichiestaRevisione.objects.filter(segnalazione=s).count() == 1)
r = M.get("/moderazione/"); esito("richiesta visibile in moderazione", f"/moderazione/richieste/{rr.id}/decidi/" in r.content.decode())
r = A.post(f"/moderazione/richieste/{rr.id}/decidi/", {"esito":"accolta","risposta":"ok"}); esito("utente semplice non decide", r.status_code == 404)
r = M.post(f"/moderazione/richieste/{rr.id}/decidi/", {"esito":"accolta","risposta":"Frase ritenuta accettabile dopo la revisione."}, follow=True)
s.refresh_from_db(); rr.refresh_from_db(); esito("richiesta accolta -> segnalazione approvata", rr.stato == "accolta" and rr.moderatore_id == mod.id and rr.chiusa_il and s.stato_id == 3 and s.esito_moderazione == "bloccato", f"stato={s.stato_id}")
r = A.post(f"/segnalazioni/{s.id}/elimina/"); s.refresh_from_db(); esito("non si elimina una segnalazione già approvata", s.eliminata_il is None)
dati2 = {**dati, "titolo": "Da eliminare subito"}; A.post("/segnalazioni/nuova/", {**dati2, "media": [foto()]}); s2 = Segnalazione.objects.filter(autore=au, titolo="Da eliminare subito").order_by("-id").first()
A.post(f"/segnalazioni/{s2.id}/elimina/"); s2.refresh_from_db(); esito("eliminazione logica in stato 2", s2.eliminata_il is not None)
r = Client().get(f"/segnalazioni/{s2.id}/"); esito("eliminata: non visibile al pubblico", r.status_code == 404)
# verifica rifiutata -> richiesta -> moderatore
ut = Utente.objects.filter(stato_account="in_attesa_verifica", metodo_registrazione="credenziali", verifiche__esito_ia="rifiutata", verifiche__revisore__isnull=True).distinct().first()
if ut:
    v = ut.verifiche.filter(esito_ia="rifiutata", revisore__isnull=True).order_by("-creata_il").first(); U = Client(); U.login(email=ut.email, password=PW)
    esito("profilo mostra la verifica rifiutata", "Verifica dell'identità non superata" in U.get("/profilo/").content.decode())
    U.post(f"/profilo/verifiche/{v.id}/revisione/", {"motivo": "Il documento è valido."}); rv = RichiestaRevisione.objects.filter(verifica=v, stato="aperta").first(); esito("richiesta di revisione verifica", rv is not None)
    if rv: M.post(f"/moderazione/richieste/{rv.id}/decidi/", {"esito":"accolta","risposta":"Documento valido."}); ut.refresh_from_db(); v.refresh_from_db(); esito("accolta -> account attivo", ut.stato_account == "attivo" and v.esito_finale == "approvata")
else: print("(nessun utente con verifica rifiutata nei dati demo)")
