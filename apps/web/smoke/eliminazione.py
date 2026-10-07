"""Eliminazione dell'account: dati personali rimossi, contenuti conservati in forma anonima."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
import pyotp
from django.test import Client
from core.models import *
from core.services import mfa
PW = "DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def con_contenuti(metodo):
    for u in Utente.objects.filter(ruolo="utente", stato_account="attivo", metodo_registrazione=metodo, id__lte=154).order_by("id"):
        if u.segnalazioni.exists() and u.commenti.exists() and u.sostegni.exists():
            return u
u = con_contenuti("credenziali"); email0, nome0 = u.email, u.nome
n_segn, n_comm, n_sost = u.segnalazioni.count(), u.commenti.count(), u.sostegni.count()
Notifica.objects.create(utente=u, tipo="stato_account", messaggio="prova")
c = Client(); c.login(email=u.email, password=PW)
esito("la pagina di conferma si apre", c.get("/profilo/elimina/").status_code == 200)
c.post("/profilo/elimina/", {"conferma": "ELIMINA", "password": "sbagliata"}); u.refresh_from_db(); esito("password errata: non elimina", u.stato_account == "attivo")
c.post("/profilo/elimina/", {"password": PW}); u.refresh_from_db(); esito("senza scrivere ELIMINA: non elimina", u.stato_account == "attivo")
c2 = Client(); c2.login(email=u.email, password=PW)
# con la 2FA serve anche il codice
seg = mfa.nuovo_segreto(); u.mfa_attiva, u.mfa_segreto = True, mfa.cifra(seg); u.save(update_fields=["mfa_attiva", "mfa_segreto"])
c3 = Client(); c3.force_login(u, backend="core.backends.UtenteBackend")
c3.post("/profilo/elimina/", {"conferma": "ELIMINA", "password": PW, "codice": "000000"}); u.refresh_from_db(); esito("con 2FA attiva serve anche il codice giusto", u.stato_account == "attivo")
u.mfa_attiva, u.mfa_segreto = False, None; u.save(update_fields=["mfa_attiva", "mfa_segreto"])
r = c2.post("/profilo/elimina/", {"conferma": "ELIMINA", "password": PW}, follow=True); u.refresh_from_db()
esito("account eliminato", u.stato_account == "eliminato" and u.eliminato_il)
esito("dati personali rimossi", u.nome == "Utente" and u.cognome == "eliminato" and u.email.endswith("@anonimo.invalid") and u.quartiere_id is None and not u.profilo_pubblico and u.data_nascita.month == 1 and u.data_nascita.day == 1 and u.mfa_segreto is None)
esito("password non più utilizzabile", not u.check_password(PW) and not u.check_password("!"))
esito("le notifiche personali sono cancellate", not Notifica.objects.filter(utente=u).exists() and not PreferenzaNotifica.objects.filter(utente=u).exists())
esito("segnalazioni, commenti e sostegni restano", u.segnalazioni.count() == n_segn and u.commenti.count() == n_comm and u.sostegni.count() == n_sost)
s = u.segnalazioni.filter(stato_id__in=[3, 5], nascosta=False).first()
if s: esito("sulle pagine pubbliche compare «Utente eliminato»", "Utente eliminato" in Client().get(f"/segnalazioni/{s.id}/").content.decode() and nome0 + " " not in Client().get(f"/segnalazioni/{s.id}/").content.decode().split("<main")[1].split("</main>")[0])
esito("nel registro resta la traccia, senza dati personali", LogAttivita.objects.filter(utente=u, operazione="eliminazione", tabella="utenti").exists() and not LogAttivita.objects.filter(utente=u, operazione="eliminazione", dati_nuovi__icontains=nome0).exists())
esito("la sessione è chiusa", Client().get("/profilo/").status_code == 302 and c2.get("/profilo/").status_code == 302)
esito("non si può più accedere (né con l'email vecchia né con quella anonima)", not Client().login(email=email0, password=PW) and not Client().login(email=u.email, password="!") and Client().post("/accedi/", {"email": u.email, "password": "!"}).status_code == 200)
esito("la stessa email si può riusare per un nuovo account", not Utente.objects.filter(email=email0).exists())
# SPID/CIE
sp = con_contenuti("spid") or Utente.objects.filter(metodo_registrazione="spid", stato_account="attivo", id__lte=154).first(); cf0 = sp.codice_fiscale_hash
cs = Client(); cs.force_login(sp, backend="core.backends.UtenteBackend")
cs.post("/profilo/elimina/", {"conferma": "ELIMINA"}); sp.refresh_from_db()
esito("SPID/CIE: basta confermare; impronta del codice fiscale sostituita (si potrà riregistrare)", sp.stato_account == "eliminato" and sp.codice_fiscale_hash != cf0 and sp.password is None and not Utente.objects.filter(codice_fiscale_hash=cf0).exists())
# ultimo amministratore
adm = Utente.objects.get(ruolo="amministratore"); ca = Client(); ca.login(email=adm.email, password=PW)
ca.post("/profilo/elimina/", {"conferma": "ELIMINA", "password": PW}); adm.refresh_from_db(); esito("l'ultimo amministratore non può eliminarsi", adm.stato_account == "attivo")
# in admin l'utente eliminato non si modifica
A = ca; r = A.post(f"/amministrazione/utenti/{u.id}/modifica/", {"nome": "Mario", "cognome": "R", "email": "x@example.org", "data_nascita": "1990-01-01", "motivo": "x"}, follow=True); u.refresh_from_db(); esito("l'amministratore non può modificare un account eliminato", u.nome == "Utente")
