import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
import pyotp
from django.db import DatabaseError, transaction
from django.test import Client
from django.utils import timezone
from core.models import *
from core.services import mfa
PW="DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
u = Utente.objects.filter(ruolo="utente", stato_account="attivo", metodo_registrazione="credenziali", mfa_attiva=False, password__startswith="$2b$").order_by("id")[30]
adm = Utente.objects.get(ruolo="amministratore")
c = Client(); c.login(email=u.email, password=PW)
r = c.get("/profilo/2fa/"); segreto = c.session.get("mfa_pendente")
esito("pagina di attivazione con QR e chiave", r.status_code == 200 and "<svg" in r.content.decode() and segreto and segreto in r.content.decode())
r = c.post("/profilo/2fa/", {"codice": "000000"}); u.refresh_from_db(); esito("codice errato: non si attiva", not u.mfa_attiva and u.mfa_segreto is None)
r = c.post("/profilo/2fa/", {"codice": pyotp.TOTP(segreto).now()}); u.refresh_from_db()
esito("codice giusto: 2FA attiva, segreto cifrato nel DB", u.mfa_attiva and u.mfa_segreto and segreto not in u.mfa_segreto and mfa.decifra(u.mfa_segreto) == segreto)
esito("attivazione nel log", LogAttivita.objects.filter(utente=u, tabella="utenti", operazione="modifica", dati_nuovi__mfa_attiva=True).exists())
# accesso in due passaggi
d = Client(); r = d.post("/accedi/", {"email": u.email, "password": PW}); esito("password giusta -> secondo passo (non ancora autenticato)", r.status_code == 302 and "accedi/2fa" in r["Location"] and "_auth_user_id" not in d.session)
esito("il sito non si apre senza il codice", d.get("/segnalazioni/nuova/").status_code == 302 and "_auth_user_id" not in d.session)
r = d.post("/accedi/2fa/", {"codice": "123456"}); esito("codice errato rifiutato", "non corretto" in r.content.decode() and "_auth_user_id" not in d.session)
r = d.post("/accedi/2fa/", {"codice": pyotp.TOTP(segreto).now()}); esito("codice giusto -> accesso", r.status_code == 302 and "_auth_user_id" in d.session)
esito("accesso con secondo fattore nel log", LogAttivita.objects.filter(utente=u, operazione="accesso", dati_nuovi__secondo_fattore=True).exists())
e = Client(); r = e.get("/accedi/2fa/"); esito("secondo passo senza password: rimandato all'accesso", r.status_code == 302 and "accedi" in r["Location"])
f = Client(); f.post("/accedi/", {"email": u.email, "password": "sbagliata"}); esito("password errata: niente secondo passo", "mfa_utente" not in f.session)
# scadenza e blocco
g = Client(); g.post("/accedi/", {"email": u.email, "password": PW}); s = g.session; s["mfa_scade"] = timezone.now().timestamp() - 1; s.save()
r = g.get("/accedi/2fa/"); esito("passaggio scaduto dopo 5 minuti", r.status_code == 302 and "accedi" in r["Location"])
h = Client(); h.post("/accedi/", {"email": u.email, "password": PW})
for i in range(5): h.post("/accedi/2fa/", {"codice": "111111"})
u.refresh_from_db(); esito("5 codici errati bloccano l'account per 15 minuti", u.bloccato_fino and u.bloccato_fino > timezone.now())
i2 = Client(); r = i2.post("/accedi/", {"email": u.email, "password": PW}); esito("bloccato: nemmeno la password basta", "bloccato" in r.content.decode())
Utente.objects.filter(pk=u.pk).update(bloccato_fino=None, tentativi_falliti=0); u.refresh_from_db()
# disattivazione
c2 = Client(); c2.login(email=u.email, password=PW)
c2.post("/profilo/2fa/disattiva/", {"password": PW, "codice": "000000"}); u.refresh_from_db(); esito("disattivare con codice errato: no", u.mfa_attiva)
c2.post("/profilo/2fa/disattiva/", {"password": "sbagliata", "codice": pyotp.TOTP(segreto).now()}); u.refresh_from_db(); esito("disattivare con password errata: no", u.mfa_attiva)
c2.post("/profilo/2fa/disattiva/", {"password": PW, "codice": pyotp.TOTP(segreto).now()}); u.refresh_from_db(); esito("password + codice: disattivata, segreto cancellato", not u.mfa_attiva and u.mfa_segreto is None)
# azzeramento da amministratore
c3 = Client(); c3.login(email=u.email, password=PW); sec = mfa.nuovo_segreto(); c3.get("/profilo/2fa/"); sec = c3.session["mfa_pendente"]; c3.post("/profilo/2fa/", {"codice": pyotp.TOTP(sec).now()}); u.refresh_from_db()
A = Client(); A.login(email=adm.email, password=PW)
A.post(f"/amministrazione/utenti/{u.id}/mfa_reset/", {}); u.refresh_from_db(); esito("azzeramento senza motivo rifiutato", u.mfa_attiva)
A.post(f"/amministrazione/utenti/{u.id}/mfa_reset/", {"motivo": "Telefono perso, identità verificata"}); u.refresh_from_db()
esito("l'amministratore azzera la 2FA con motivo", not u.mfa_attiva and u.mfa_segreto is None and Notifica.objects.filter(utente=u, messaggio__contains="azzerata").exists())
esito("utente semplice non può azzerare", Client().post(f"/amministrazione/utenti/{u.id}/mfa_reset/", {"motivo": "x"}).status_code in (302, 404))
# SPID/CIE: non previsto
sp = Utente.objects.filter(metodo_registrazione="spid", stato_account="attivo").first(); cs = Client(); cs.force_login(sp, backend="core.backends.UtenteBackend")
r = cs.get("/profilo/2fa/"); esito("SPID/CIE: la 2FA dell'app non si propone", r.status_code == 302)
# vincolo nel database: flag acceso senza segreto non esiste
try:
    with transaction.atomic(): Utente.objects.filter(pk=u.pk).update(mfa_attiva=True, mfa_segreto=None)
    esito("il database rifiuta mfa_attiva senza segreto", False)
except DatabaseError as ex:
    esito("il database rifiuta mfa_attiva senza segreto", ex.args[0] == 3819, f"errno {ex.args[0]}")
