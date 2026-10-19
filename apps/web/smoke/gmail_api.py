"""Invio con l'API di Gmail: prova contro un finto server locale (nessuna email vera)."""
import os, sys, json, base64, email, threading, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from django.core.mail import EmailMultiAlternatives, get_connection
from django.test import override_settings
from core import email_backend
from core.email_backend import ErroreGmailApi
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
ricevuti = {"token": [], "invii": [], "stato": 200}
class Finto(BaseHTTPRequestHandler):
    def do_POST(self):
        corpo = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path == "/token":
            ricevuti["token"].append(parse_qs(corpo.decode())); self.rispondi(200, {"access_token": "AT-%d" % len(ricevuti["token"]), "expires_in": 3600})
        else:
            ricevuti["invii"].append((self.headers.get("Authorization"), json.loads(corpo))); self.rispondi(ricevuti["stato"], {"id": "x"} if ricevuti["stato"] == 200 else {"error": "non autorizzato"})
    def rispondi(self, codice, dati):
        self.send_response(codice); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(dati).encode())
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), Finto); porta = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{porta}"
with override_settings(GMAIL_CLIENT_ID="cid", GMAIL_CLIENT_SECRET="seg", GMAIL_REFRESH_TOKEN="rt", GMAIL_TOKEN_URL=base + "/token", GMAIL_SEND_URL=base + "/send"):
    email_backend._token.update(valore=None, scade=0)
    conn = get_connection("core.email_backend.GmailApiBackend")
    m = EmailMultiAlternatives("Conferma il tuo indirizzo · Città", "Ciao, conferma qui: https://esempio/x", "La Nostra Città <mittente@gmail.com>", ["destinatario@example.org"], connection=conn)
    m.attach_alternative("<p>Ciao, <b>conferma</b></p>", "text/html")
    esito("un messaggio viene inviato", m.send() == 1)
    t = ricevuti["token"][0]
    esito("il token si chiede con il refresh token e il client", t["grant_type"] == ["refresh_token"] and t["refresh_token"] == ["rt"] and t["client_id"] == ["cid"] and t["client_secret"] == ["seg"])
    auth, corpo = ricevuti["invii"][0]
    esito("l'invio usa il token di accesso come Bearer", auth == "Bearer AT-1")
    msg = email.message_from_bytes(base64.urlsafe_b64decode(corpo["raw"]))
    esito("il messaggio contiene destinatario, mittente e oggetto (anche con le lettere accentate)", msg["To"] == "destinatario@example.org" and "mittente@gmail.com" in msg["From"] and str(email.header.make_header(email.header.decode_header(msg["Subject"]))) == "Conferma il tuo indirizzo · Città")
    tipi = [p.get_content_type() for p in msg.walk()]
    esito("ci sono la parte testo e la parte HTML", "text/plain" in tipi and "text/html" in tipi)
    m2 = EmailMultiAlternatives("Seconda", "testo", "a@gmail.com", ["b@example.org"], connection=conn); m2.send()
    esito("il token di accesso si riusa (una sola richiesta di token)", len(ricevuti["token"]) == 1 and ricevuti["invii"][1][0] == "Bearer AT-1")
    ricevuti["stato"] = 401
    try:
        EmailMultiAlternatives("Errore", "testo", "a@gmail.com", ["b@example.org"], connection=conn).send(); ok = False
    except ErroreGmailApi as e: ok = "401" in str(e)
    esito("se Gmail rifiuta (401) l'errore è chiaro e viene sollevato", ok)
    esito("con fail_silently l'errore non interrompe e non conta come inviato", EmailMultiAlternatives("Errore", "testo", "a@gmail.com", ["b@example.org"], connection=get_connection("core.email_backend.GmailApiBackend", fail_silently=True)).send() == 0)
    ricevuti["stato"] = 200
    EmailMultiAlternatives("Dopo l'errore", "testo", "a@gmail.com", ["b@example.org"], connection=conn).send()
    esito("dopo un errore si chiede un token nuovo", len(ricevuti["token"]) >= 2)
with override_settings(GMAIL_CLIENT_ID="", GMAIL_CLIENT_SECRET="", GMAIL_REFRESH_TOKEN="", EMAIL_HOST=""):
    pass
srv.shutdown()
