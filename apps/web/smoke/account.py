import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from django.core import mail
from django.test import Client
from core.models import *
from core.services import token
PW="DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
u = Utente.objects.filter(ruolo="utente", stato_account="attivo", metodo_registrazione="credenziali", password__startswith="$2b$").order_by("id")[20]
c = Client(); c.login(email=u.email, password=PW)
# recupero password
r = Client().post("/password-dimenticata/", {"email": u.email}); esito("recupero: risposta neutra", r.status_code == 200 and "Se l'indirizzo" in r.content.decode())
r = Client().post("/password-dimenticata/", {"email": "non.esiste@example.org"}); esito("recupero: stessa risposta se l'email non esiste", "Se l'indirizzo" in r.content.decode())
t = token.crea("reset", u); r = Client().get(f"/reset-password/{t}/"); esito("link di reset valido", r.status_code == 200 and "Scegli una nuova password" in r.content.decode())
cl = Client(); r = cl.post(f"/reset-password/{t}/", {"password": "debole", "password2": "debole"}); esito("password debole rifiutata", "almeno 8" in r.content.decode())
r = cl.post(f"/reset-password/{t}/", {"password": "Nuova!Pass9", "password2": "Nuova!Pass9"}); u.refresh_from_db(); esito("password reimpostata", r.status_code == 302 and u.check_password("Nuova!Pass9"))
r = Client().get(f"/reset-password/{t}/"); esito("il link non è riutilizzabile", "non è valido" in r.content.decode())
esito("accesso con la nuova password", Client().login(email=u.email, password="Nuova!Pass9"))
esito("token scaduto/alterato rifiutato", token.leggi(t + "x", "reset") is None and token.leggi(t, "conferma") is None)
u.set_password(PW); u.save(update_fields=["password"])  # ripristino
# cambio email
c = Client(); c.login(email=u.email, password=PW); vecchia = u.email
c.post("/profilo/email/", {"email": vecchia}); u.refresh_from_db(); esito("stessa email di un altro account rifiutata", u.email == vecchia)
c.post("/profilo/email/", {"email": "nuova.mail.prova@example.org"}); u.refresh_from_db(); esito("l'email non cambia prima della conferma", u.email == vecchia)
c.get(f"/profilo/email/conferma/{token.crea('email', u, 'nuova.mail.prova@example.org')}/"); u.refresh_from_db(); esito("dopo la conferma l'email cambia", u.email == "nuova.mail.prova@example.org")
altro = Utente.objects.exclude(pk=u.pk).filter(stato_account="attivo").first(); c2 = Client(); c2.login(email=altro.email, password=PW)
c2.get(f"/profilo/email/conferma/{token.crea('email', u, 'rubata@example.org')}/"); altro.refresh_from_db(); esito("un link altrui non vale per un altro account", altro.email != "rubata@example.org")
Utente.objects.filter(pk=u.pk).update(email=vecchia); u.refresh_from_db()
# preferenze
c = Client(); c.login(email=u.email, password=PW); r = c.get("/profilo/notifiche/"); esito("pagina preferenze", r.status_code == 200 and PreferenzaNotifica.objects.filter(utente=u).count() == 8)
c.post("/profilo/notifiche/", {"app_stato_segnalazione": "on"}); p = {x.tipo: x for x in PreferenzaNotifica.objects.filter(utente=u)}
esito("obbligatorie sempre attive, le altre come scelto", p["verifica_account"].in_app and p["stato_account"].in_app and p["stato_segnalazione"].in_app and not p["nuovo_commento"].in_app)
from portale.views import notifica
n0 = Notifica.objects.filter(utente=u).count(); notifica(u, "nuovo_commento", "x"); esito("notifica disattivata non creata", Notifica.objects.filter(utente=u).count() == n0)
notifica(u, "stato_segnalazione", "y"); esito("notifica attiva creata", Notifica.objects.filter(utente=u).count() == n0 + 1)
notifica(u, "stato_account", "z"); esito("notifica obbligatoria sempre creata", Notifica.objects.filter(utente=u).count() == n0 + 2)
# nuova segnalazione approvata -> notifica al quartiere
mod = Utente.objects.filter(ruolo="moderatore").first(); M = Client(); M.login(email=mod.email, password=PW)
s = Segnalazione.objects.filter(stato_id=2, eliminata_il__isnull=True).exclude(esito_moderazione="bloccato").first()
vicino = Utente.objects.filter(quartiere_id=s.quartiere_id, stato_account="attivo").exclude(pk=s.autore_id).first()
if vicino:
    n1 = Notifica.objects.filter(utente=vicino, tipo="nuova_segnalazione_quartiere").count(); M.post(f"/moderazione/segnalazioni/{s.id}/approva/")
    esito("approvazione avvisa chi abita nel quartiere", Notifica.objects.filter(utente=vicino, tipo="nuova_segnalazione_quartiere").count() >= n1 + (1 if PreferenzaNotifica.objects.filter(utente=vicino, tipo="nuova_segnalazione_quartiere", in_app=False).count() == 0 else 0))
else: print("(nessun residente nello stesso quartiere nei dati demo)")
# verifica: moderatore approva ma email non confermata -> resta in attesa
x = Utente.objects.filter(stato_account="in_attesa_verifica", email_verificata_il__isnull=True, verifiche__esito_ia="da_rivedere", verifiche__revisore__isnull=True).distinct().first()
if x:
    v = x.verifiche.filter(esito_ia="da_rivedere", revisore__isnull=True).first(); M.post(f"/moderazione/verifiche/{v.id}/decidi/", {"esito": "approvata", "motivo": "Documento ok"}); x.refresh_from_db()
    esito("verifica approvata ma email non confermata: resta in attesa", x.stato_account == "in_attesa_verifica")
    c = Client(); c.login(email=x.email, password=PW); c.get(f"/conferma-email/{token.crea('conferma', x)}/"); x.refresh_from_db(); esito("poi la conferma email lo attiva", x.stato_account == "attivo")
else: print("(nessun utente in attesa con email non confermata e verifica da rivedere)")
