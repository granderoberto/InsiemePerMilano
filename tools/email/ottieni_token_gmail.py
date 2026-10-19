"""Ottiene (una volta) il token per inviare email con l'API di Gmail e lo scrive nel .env come GMAIL_REFRESH_TOKEN.
Prima: in .env metti GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET (vedi docs/produzione.md, «Gmail API»).
Uso: tools/.venv/bin/python tools/email/ottieni_token_gmail.py   (si apre il browser: accedi con l'account Gmail e consenti l'invio)"""
import http.server, json, pathlib, re, secrets, sys, threading, urllib.parse, urllib.request, webbrowser

RADICE = pathlib.Path(__file__).resolve().parents[2]
ENV = RADICE / ".env"
PORTA = 8765
SCOPE = "https://www.googleapis.com/auth/gmail.send"


def leggi(chiave):
    m = re.search(rf"^{chiave}=(.*)$", ENV.read_text(), re.M)
    return m.group(1).strip() if m else ""


cid, segreto = leggi("GMAIL_CLIENT_ID"), leggi("GMAIL_CLIENT_SECRET")
if not cid or not segreto:
    sys.exit("Metti GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET nel file .env, poi rilancia.")
redirect = f"http://127.0.0.1:{PORTA}/"
stato = secrets.token_urlsafe(16)
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": stato})
risultato = {}


class Gestore(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get("state", [""])[0] == stato and "code" in q:
            risultato["code"] = q["code"][0]
            msg = "Fatto: puoi chiudere questa scheda e tornare al terminale."
        else:
            risultato["errore"] = q.get("error", ["risposta non valida"])[0]
            msg = "Qualcosa non è andato bene: torna al terminale."
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        self.wfile.write(f"<p style='font:18px sans-serif;margin:40px'>{msg}</p>".encode())

    def log_message(self, *a):  # niente log: nell'indirizzo c'è il codice
        pass


server = http.server.HTTPServer(("127.0.0.1", PORTA), Gestore)
threading.Thread(target=server.handle_request, daemon=True).start()
print("Apro il browser per l'autorizzazione. Se non si apre, copia questo indirizzo:\n" + url + "\n")
webbrowser.open(url)
while not risultato:
    threading.Event().wait(0.3)
if "code" not in risultato:
    sys.exit("Autorizzazione non riuscita: " + risultato.get("errore", "?"))
dati = urllib.parse.urlencode({"code": risultato["code"], "client_id": cid, "client_secret": segreto, "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
try:
    r = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=dati), timeout=20))
except Exception as e:  # noqa: BLE001
    sys.exit(f"Scambio del codice non riuscito: {e}")
if "refresh_token" not in r:
    sys.exit("Google non ha restituito il refresh token. Riprova (il permesso va concesso di nuovo) o controlla l'app OAuth.")
testo = ENV.read_text()
riga = f"GMAIL_REFRESH_TOKEN={r['refresh_token']}"
testo = re.sub(r"^GMAIL_REFRESH_TOKEN=.*$", riga, testo, flags=re.M) if re.search(r"^GMAIL_REFRESH_TOKEN=", testo, re.M) else testo.rstrip("\n") + "\n" + riga + "\n"
ENV.write_text(testo)
print("Fatto: GMAIL_REFRESH_TOKEN scritto nel .env (non viene mostrato). Prova: cd apps/web && .venv/bin/python manage.py prova_email tuoindirizzo@gmail.com")
