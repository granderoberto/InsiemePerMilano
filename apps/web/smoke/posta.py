"""Email e password con un server SMTP VERO (locale): conferma, recupero, avvisi, limiti, errori."""
import os, sys, re, email, socket, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0])
from aiosmtpd.controller import Controller
class Raccolta:
    def __init__(self): self.msg = []
    async def handle_DATA(self, server, session, envelope):
        self.msg.append((envelope.rcpt_tos, email.message_from_bytes(envelope.content))); return "250 OK"
raccolta = Raccolta()
s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
srv = Controller(raccolta, hostname="127.0.0.1", port=porta); srv.start()
os.environ.update(EMAIL_HOST="127.0.0.1", EMAIL_PORT=str(porta), EMAIL_TLS="0", EMAIL_FROM="La Nostra Città <noreply@test.example>", SITE_URL="https://lanostracitta.test")
os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"
import django; django.setup()
from django.conf import settings
from django.test import Client
from core.models import *
from smoke._aiuti import SFX, campi_documento
from core.services import token
PW = "DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def testo(m):
    for p in m.walk():
        if p.get_content_type() == "text/plain": return p.get_payload(decode=True).decode()
def html(m):
    for p in m.walk():
        if p.get_content_type() == "text/html": return p.get_payload(decode=True).decode()
def link_in(m): return re.search(r"https://lanostracitta\.test(/[^\s\"<]+)", testo(m)).group(1)
def nuovi(da): return raccolta.msg[da:]
esito("backend SMTP attivo (non la console)", "smtp" in settings.EMAIL_BACKEND and settings.SITE_URL == "https://lanostracitta.test")
base = {"nome": "Giada", "cognome": "Ferretti", "email": f"giada.ferretti.prova{SFX}@example.org", "data_nascita": "1998-04-12", **{k: "on" for k in ["privacy","biometrici","intelligenza_artificiale","termini_uso","cookie","eta_minima"]}}
c = Client()
# --- criteri password in registrazione
for pw, nota in [("corta1!", "troppo corta"), ("senzanumeroA!", "senza numero"), ("Password1!", "troppo comune"), ("Giada-Ferretti9!", "contiene il nome"), ("Zq7!"*30, "troppo lunga")]:
    r = c.post("/registrati/", {**base, **campi_documento(), "password": pw, "password2": pw}); esito(f"password rifiutata: {nota}", r.status_code == 200 and not Utente.objects.filter(email=base["email"]).exists())
r = c.post("/registrati/", {**base, **campi_documento(), "password": "Tr4ghetto-Blu!", "password2": "Diversa-Blu!9"}); esito("le due password devono coincidere", not Utente.objects.filter(email=base["email"]).exists())
# --- registrazione e conferma
n0 = len(raccolta.msg); r = c.post("/registrati/", {**base, **campi_documento(), "password": "Tr4ghetto-Blu!", "password2": "Tr4ghetto-Blu!"}, follow=True)
m = nuovi(n0); u = Utente.objects.get(email=base["email"])
esito("registrazione: UN'email di conferma, al destinatario giusto", len(m) == 1 and m[0][0] == [base["email"]] and "Conferma" in m[0][1]["Subject"])
esito("l'email ha parte testo e parte HTML, mittente configurato", m and testo(m[0][1]) and html(m[0][1]) and "noreply@test.example" in m[0][1]["From"])
esito("il link usa SITE_URL e NON compare a schermo", m and "/conferma-email/" in testo(m[0][1]) and "Link:" not in r.content.decode())
esito("account ancora in attesa", u.stato_account == "in_attesa_verifica")
Client().get(link_in(m[0][1])); u.refresh_from_db(); esito("il link ricevuto attiva l'account", u.stato_account == "attivo" and u.email_verificata_il)
# --- reinvio con limite
n0 = len(raccolta.msg); u2 = Utente.objects.filter(stato_account="in_attesa_verifica", metodo_registrazione="credenziali", email_verificata_il__isnull=True).first()
if u2:
    d = Client(); d.login(email=u2.email, password=PW)
    for i in range(5): d.post("/profilo/conferma/")
    esito("reinvio conferma: al massimo 3 all'ora", len(nuovi(n0)) == 3, f"{len(nuovi(n0))} email")
# --- recupero password
n0 = len(raccolta.msg); Client().post("/password-dimenticata/", {"email": "non.esiste@example.org"}); esito("recupero: email sconosciuta -> nessuna email, risposta neutra", len(nuovi(n0)) == 0)
r = Client().post("/password-dimenticata/", {"email": base["email"].upper()}); m = nuovi(n0)
esito("recupero: l'email arriva (anche se scritta in maiuscolo)", len(m) == 1 and "Reimposta" in m[0][1]["Subject"] and "/reset-password/" in testo(m[0][1]), f"{len(m)}")
l = link_in(m[0][1]); d = Client()
r = d.post(l, {"password": "Password1!", "password2": "Password1!"}); esito("reset: password comune rifiutata", r.status_code == 200 and Utente.objects.get(pk=u.pk).check_password("Tr4ghetto-Blu!"))
r = d.post(l, {"password": "Giada-Nuova7!", "password2": "Giada-Nuova7!"}); esito("reset: password con il proprio nome rifiutata", Utente.objects.get(pk=u.pk).check_password("Tr4ghetto-Blu!"))
n1 = len(raccolta.msg); r = d.post(l, {"password": "Ombrello-Verde4?", "password2": "Ombrello-Verde4?"}); u.refresh_from_db()
esito("reset: nuova password valida accettata", r.status_code == 302 and u.check_password("Ombrello-Verde4?"))
esito("avviso di sicurezza dopo il reset", len(nuovi(n1)) == 1 and "cambiata" in nuovi(n1)[0][1]["Subject"])
esito("il link di reset non si riusa", "non è valido" in Client().get(l).content.decode())
esito("la vecchia password non vale più, la nuova sì", not Client().login(email=u.email, password="Tr4ghetto-Blu!") and Client().login(email=u.email, password="Ombrello-Verde4?"))
n0 = len(raccolta.msg)
for i in range(5): Client().post("/password-dimenticata/", {"email": base["email"]})
esito("recupero: al massimo 3 email all'ora per indirizzo", len(nuovi(n0)) <= 3, f"{len(nuovi(n0))} email")
# --- cambia password
a = Client(); a.login(email=u.email, password="Ombrello-Verde4?"); altra = Client(); altra.login(email=u.email, password="Ombrello-Verde4?")
esito("pagina cambia password", a.get("/profilo/password/").status_code == 200)
a.post("/profilo/password/", {"attuale": "sbagliata", "password": "Nuova-Chiave8!", "password2": "Nuova-Chiave8!"}); esito("cambio: password attuale errata rifiutata", Utente.objects.get(pk=u.pk).check_password("Ombrello-Verde4?"))
a.post("/profilo/password/", {"attuale": "Ombrello-Verde4?", "password": "debole", "password2": "debole"}); esito("cambio: password debole rifiutata", Utente.objects.get(pk=u.pk).check_password("Ombrello-Verde4?"))
n1 = len(raccolta.msg); a.post("/profilo/password/", {"attuale": "Ombrello-Verde4?", "password": "Nuova-Chiave8!", "password2": "Nuova-Chiave8!"}); u.refresh_from_db()
esito("cambio: password nuova salvata e avviso via email", u.check_password("Nuova-Chiave8!") and len(nuovi(n1)) == 1)
esito("la sessione corrente resta attiva", a.get("/profilo/").status_code == 200)
esito("le altre sessioni si chiudono", altra.get("/profilo/").status_code == 302)
# --- cambio email
n1 = len(raccolta.msg); a.post("/profilo/email/", {"email": f"giada.nuova.prova{SFX}@example.org"}); m = nuovi(n1)
esito("cambio email: il link va al NUOVO indirizzo", len(m) == 1 and m[0][0] == [f"giada.nuova.prova{SFX}@example.org"])
a.get(link_in(m[0][1])); u.refresh_from_db(); esito("dopo la conferma l'email cambia", u.email == f"giada.nuova.prova{SFX}@example.org")
# --- password lunghissima al login: nessun errore del server
r = Client().post("/accedi/", {"email": u.email, "password": "x" * 200}); esito("login con password di 200 caratteri: nessun errore 500", r.status_code == 200 and "non corretti" in r.content.decode())
# --- server di posta che non risponde
srv.stop(); n_errori = 0
r = Client().post("/registrati/", {**base, **campi_documento(), "email": f"giada.errore.prova{SFX}@example.org", "password": "Tr4ghetto-Blu!", "password2": "Tr4ghetto-Blu!"}, follow=True)
esito("posta non raggiungibile: la registrazione riesce e avvisa di rinviare il link", Utente.objects.filter(email=f"giada.errore.prova{SFX}@example.org").exists() and "non siamo riusciti" in r.content.decode().lower())
r = Client().post("/password-dimenticata/", {"email": u.email}); esito("posta non raggiungibile: il recupero non rivela nulla", r.status_code == 200 and "Se l'indirizzo" in r.content.decode())
