"""Client OpenRouter e quota (fase 1): prove contro un finto server locale. Nessuna chiamata vera, nessuna richiesta consumata.
Tutto dentro una transazione annullata alla fine (il registro è append-only: così non resta nulla)."""
import os, sys, json, time, threading, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from http.server import BaseHTTPRequestHandler, HTTPServer
from django.db import transaction
from django.test import override_settings
from core.models import LogAttivita
from core.services.ia import openrouter as orr, quota
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["risultati"], "properties": {"risultati": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["id", "approvato", "motivazione"],
    "properties": {"id": {"type": "integer"}, "approvato": {"type": "boolean"}, "motivazione": {"type": "string", "maxLength": 60}}}}}}
BUONO = {"risultati": [{"id": 1, "approvato": True, "motivazione": ""}, {"id": 2, "approvato": False, "motivazione": "insulto a un utente"}]}
def ok(testo=None, provider="Recursive"): return 200, {"choices": [{"message": {"content": testo if testo is not None else json.dumps(BUONO)}, "finish_reason": "stop"}], "usage": {"total_tokens": 1500}, "provider": provider}
PRIVACY = (404, {"error": {"code": 404, "message": "No endpoints found matching your data policy (Free model training)"}})
A_MONTE = (429, {"error": {"code": 429, "message": "temporarily rate-limited upstream", "metadata": {"limit_source": "upstream_provider_shared_pool"}}})
NOSTRA = (429, {"error": {"code": 429, "message": "Rate limit exceeded: free-models-per-day"}})

stato = {"coda": [], "richieste": [], "key": (200, {"data": {"free_model_daily_requests": {"used": 3, "limit": 50, "remaining": 47}}}), "ritardo": 0}
class Finto(BaseHTTPRequestHandler):
    def _r(self, codice, dati):
        self.send_response(codice); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(dati).encode())
    def do_GET(self):
        stato["richieste"].append(("GET", self.path, self.headers.get("Authorization"), None)); self._r(*stato["key"])
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        stato["richieste"].append(("POST", self.path, self.headers.get("Authorization"), corpo))
        if stato["ritardo"]: time.sleep(stato["ritardo"])
        try: self._r(*stato["coda"].pop(0))
        except (BrokenPipeError, ConnectionResetError): pass
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), Finto); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"

class Rollback(Exception): pass
PRIMA = LogAttivita.objects.filter(tabella="openrouter").count()   # righe vere già presenti (richieste reali fatte a mano)
def prova(coda, modelli=("m1:free", "m2:free"), tipo="segnalazione", utente="Commento di prova"):
    stato["coda"][:] = coda; stato["richieste"].clear()
    try:
        return orr.chiedi(tipo, "Sei un filtro.", utente, SCHEMA, modelli=list(modelli), max_token=2000), None
    except orr.ErroreIA as e:
        return None, e
def post_fatte(): return [r for r in stato["richieste"] if r[0] == "POST"]

impostazioni = dict(OPENROUTER_URL=BASE, OPENROUTER_API_KEY="chiave-di-prova-segreta", IA_INTERVALLO_MIN=0, IA_TIMEOUT_RICHIESTA=5)
try:
    with override_settings(**impostazioni), transaction.atomic():
        orr._dormi = lambda s: None
        quota.azzera_cache()
        # ---- risposta valida e contenuto della richiesta
        r, e = prova([ok()])
        esito("risposta valida: dati, modello, token, fornitore", r and r.dati == BUONO and r.modello == "m1:free" and r.token == 1500 and r.fornitore == "Recursive", e)
        _, _, auth, corpo = post_fatte()[0]
        esito("intestazione di autorizzazione presente", auth == "Bearer chiave-di-prova-segreta")
        esito("privacy: data_collection = deny", corpo["provider"] == {"data_collection": "deny"})
        esito("lo schema è nelle istruzioni, il testo dell'utente nel messaggio user", "risultati" in corpo["messages"][0]["content"] and corpo["messages"][1] == {"role": "user", "content": "Commento di prova"})
        esito("max_tokens e temperatura 0", corpo["max_tokens"] == 2000 and corpo["temperature"] == 0)
        # ---- registro e chiave
        riga = LogAttivita.objects.filter(tabella="openrouter").order_by("-id").first()
        esito("la richiesta è nel registro, contata", riga and riga.dati_nuovi["contata"] is True and riga.dati_nuovi["modello"] == "m1:free" and riga.dati_nuovi["tipo"] == "segnalazione")
        esito("la chiave non compare mai nel registro", not any("chiave-di-prova" in json.dumps(l.dati_nuovi) for l in LogAttivita.objects.filter(tabella="openrouter")))
        # ---- JSON avvolto in testo o in ```
        r, e = prova([ok("Ecco:\n```json\n" + json.dumps(BUONO) + "\n```")]); esito("JSON dentro ``` letto", r and r.dati == BUONO, e)
        # ---- catena di modelli
        r, e = prova([PRIVACY, ok()]); esito("404 privacy: passa al modello successivo", r and r.modello == "m2:free" and len(post_fatte()) == 2, e)
        riga404 = LogAttivita.objects.filter(tabella="openrouter", dati_nuovi__http=404).first()
        esito("il 404 è registrato ma non contato", riga404 is not None and riga404.dati_nuovi["contata"] is False)
        r, e = prova([A_MONTE, ok()]); esito("429 «a monte»: modello successivo", r and r.modello == "m2:free", e)
        r, e = prova([(403, {"error": {"message": "only agentic harnesses"}}), ok()]); esito("403: modello successivo", r and r.modello == "m2:free", e)
        r, e = prova([PRIVACY, A_MONTE]); esito("tutti i modelli non disponibili: NessunModello", isinstance(e, orr.NessunModello), e)
        # ---- quota nostra
        r, e = prova([NOSTRA, ok()]); esito("429 della nostra quota: QuotaEsaurita e nessun altro tentativo", isinstance(e, orr.QuotaEsaurita) and len(post_fatte()) == 1, e)
        # ---- errori del server
        r, e = prova([(500, {"error": {"message": "interno"}}), ok()], modelli=("m1:free",)); esito("500 poi 200: un nuovo tentativo sullo stesso modello", r and r.modello == "m1:free" and len(post_fatte()) == 2, e)
        r, e = prova([(500, {}), (502, {}), ok()]); esito("due errori del server: passa al modello successivo", r and r.modello == "m2:free" and len(post_fatte()) == 3, e)
        r, e = prova([(500, {})] * 4, modelli=("m1:free", "m2:free")); esito("errori ripetuti: NessunModello dopo 2+2 richieste", isinstance(e, orr.NessunModello) and len(post_fatte()) == 4, e)
        # ---- scadenza
        stato["ritardo"] = 2
        with override_settings(IA_TIMEOUT_RICHIESTA=1):
            r, e = prova([ok(), ok()], modelli=("m1:free",)); esito("scadenza del tempo: NessunModello (un nuovo tentativo)", isinstance(e, orr.NessunModello) and len(post_fatte()) == 2, e)
        stato["ritardo"] = 0; time.sleep(2.5)
        # ---- risposte non valide: hanno consumato quota, nessun altro modello
        r, e = prova([ok(""), ok()]); esito("risposta vuota: RispostaNonValida, nessun altro modello", isinstance(e, orr.RispostaNonValida) and len(post_fatte()) == 1, e)
        riga = LogAttivita.objects.filter(tabella="openrouter", dati_nuovi__http=200).order_by("-id").first()
        esito("la risposta vuota è contata (ha consumato quota)", riga and riga.dati_nuovi["contata"] is True)
        r, e = prova([ok("non è json")]); esito("testo non JSON: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([ok(json.dumps({"risultati": [{"id": 1, "approvato": "sì", "motivazione": ""}]}))]); esito("tipo sbagliato: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([ok(json.dumps({"risultati": [{"id": 1, "approvato": True, "motivazione": "x" * 61}]}))]); esito("motivazione troppo lunga: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([ok(json.dumps({"risultati": [], "extra": 1}))]); esito("campo non previsto: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        # ---- 200 con errore nel corpo
        r, e = prova([(200, {"error": {"code": 404, "message": "No endpoints"}}), ok()]); esito("200 con errore nel corpo trattato come l'errore", r and r.modello == "m2:free", e)
        # ---- chiave
        r, e = prova([(401, {"error": {"message": "No auth"}}), ok()]); esito("401: NessunModello subito", isinstance(e, orr.NessunModello) and len(post_fatte()) == 1, e)
        with override_settings(OPENROUTER_API_KEY=""):
            r, e = prova([ok()]); esito("senza chiave: NessunModello, nessuna richiesta", isinstance(e, orr.NessunModello) and not post_fatte(), e)
        r, e = prova([ok()], modelli=()); esito("senza modelli: NessunModello", isinstance(e, orr.NessunModello), e)
        # ---- ritmo tra le richieste
        attese, t = [], [100.0]
        orr._dormi = lambda s: (attese.append(s), t.__setitem__(0, t[0] + s)); orr._orologio = lambda: t[0]; orr._ultima[0] = 0.0
        with override_settings(IA_INTERVALLO_MIN=4):
            prova([ok(), ok()]); t[0] += 1; prova([ok()])
        esito("ritmo: la seconda richiesta attende il resto dei 4 secondi", len(attese) == 1 and abs(attese[0] - 3) < 0.01, attese)
        orr._dormi, orr._orologio = (lambda s: None), time.monotonic
        # ---- quota
        quota.azzera_cache(); stato["key"] = (200, {"data": {"free_model_daily_requests": {"used": 3, "limit": 50, "remaining": 47}}})
        esito("contatore ufficiale letto da /key", quota.usate_ufficiali(forza=True) == 3)
        ALTA = dict(IA_QUOTA_GIORNALIERA=10**6, IA_QUOTA_SEGNALAZIONI=10**6, IA_QUOTA_COMMENTI=10**6, IA_QUOTA_SOGLIA_COMMENTI=10**6)   # il registro di oggi contiene richieste vere
        with override_settings(**ALTA):
            s = quota.stato(); esito("stato: usate = il maggiore tra ufficiale e registro, rimaste", s["usate"] >= 3 and s["usate"] == max(3, quota.usate_locali()) and s["rimaste"] == 10**6 - s["usate"], s)
        esito("la lettura di /key porta la chiave", any(r[0] == "GET" and r[1] == "/key" and r[2] == "Bearer chiave-di-prova-segreta" for r in stato["richieste"]))
        n = len([r for r in stato["richieste"] if r[0] == "GET"]); quota.usate_ufficiali(); esito("il valore è tenuto in memoria 60 secondi", len([r for r in stato["richieste"] if r[0] == "GET"]) == n)
        def con_ufficiali(n): quota.azzera_cache(); stato["key"] = (200, {"data": {"free_model_daily_requests": {"used": n, "limit": 50, "remaining": 50 - n}}})
        with override_settings(**ALTA):
            con_ufficiali(0); esito("ammesso: segnalazione e commento a quota libera", quota.ammesso("segnalazione")[0] and quota.ammesso("commento")[0])
        with override_settings(**{**ALTA, "IA_QUOTA_SOGLIA_COMMENTI": 44}):
            con_ufficiali(44); esito("da 44 in su: commenti no, segnalazioni sì", not quota.ammesso("commento")[0] and quota.ammesso("segnalazione")[0])
        with override_settings(IA_QUOTA_GIORNALIERA=50):
            con_ufficiali(50); a = quota.ammesso("segnalazione"); esito("a 50: nessuno, con il motivo", not a[0] and a[1] == quota.MOTIVO_ESAURITA and not quota.ammesso("commento")[0], a)
        stato["key"] = (500, {}); quota.azzera_cache(); locali = quota.usate_locali()
        esito("/key non disponibile: si usa il registro locale", quota.usate_ufficiali(forza=True) is None and quota.stato()["usate"] == locali)
        with override_settings(OPENROUTER_URL="http://127.0.0.1:1"):
            quota.azzera_cache(); esito("rete assente: nessun errore, si usa il registro", quota.usate_ufficiali(forza=True) is None)
        stato["key"] = (200, {"data": {"free_model_daily_requests": {"used": 0, "limit": 50, "remaining": 50}}}); quota.azzera_cache()
        with override_settings(**{**ALTA, "IA_QUOTA_SEGNALAZIONI": quota.usate_locali("segnalazione") + 1}):
            quota.azzera_cache(); esito("sotto il tetto delle segnalazioni: ammessa", quota.ammesso("segnalazione")[0])
            quota.registra_richiesta("segnalazione", "m1:free", 200, 1.0, True); esito("tetto delle segnalazioni (impostazione) raggiunto", not quota.ammesso("segnalazione")[0])
        with override_settings(**{**ALTA, "IA_QUOTA_COMMENTI": quota.usate_locali("commento") + 1}):
            quota.azzera_cache(); esito("sotto il tetto dei commenti: ammesso", quota.ammesso("commento")[0])
            quota.registra_richiesta("commento", "m1:free", 200, 1.0, True); esito("tetto dei commenti raggiunto", not quota.ammesso("commento")[0])
        quota.registra_richiesta("segnalazione", "m1:free", 404, 0.1, False)
        c = quota.usate_locali(); quota.registra_richiesta("segnalazione", "m1:free", 429, 0.1, False); esito("le richieste non contate non aumentano il totale", quota.usate_locali() == c)
        raise Rollback()
except Rollback:
    pass
srv.shutdown()
esito("nessuna riga lasciata nel registro dalla prova", LogAttivita.objects.filter(tabella="openrouter").count() == PRIMA)
