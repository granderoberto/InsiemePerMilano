"""Router dei fornitori e quota (fase 1 + «Multi-fornitore»): prove contro un finto server locale. Nessuna chiamata vera, nessuna richiesta
consumata. Tutto dentro una transazione annullata alla fine (il registro è append-only: così non resta nulla)."""
import os, sys, json, time, threading, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from http.server import BaseHTTPRequestHandler, HTTPServer
from django.db import transaction
from django.test import override_settings
from core.models import LogAttivita
from core.services.ia import fornitori as forn, quota, router as orr
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["risultati"], "properties": {"risultati": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["id", "approvato", "motivazione"],
    "properties": {"id": {"type": "integer"}, "approvato": {"type": "boolean"}, "motivazione": {"type": "string", "maxLength": 60}}}}}}
BUONO = {"risultati": [{"id": 1, "approvato": True, "motivazione": ""}, {"id": 2, "approvato": False, "motivazione": "insulto a un utente"}]}
def ok(testo=None, provider="Recursive"): return 200, {"choices": [{"message": {"content": testo if testo is not None else json.dumps(BUONO)}, "finish_reason": "stop"}], "usage": {"total_tokens": 1500}, "provider": provider}
PRIVACY = (404, {"error": {"code": 404, "message": "No endpoints found matching your data policy (Free model training)"}})
A_MONTE = (429, {"error": {"code": 429, "message": "temporarily rate-limited upstream", "metadata": {"limit_source": "upstream_provider_shared_pool"}}})
NOSTRA = (429, {"error": {"code": 429, "message": "Rate limit exceeded: free-models-per-day"}})

# un finto server per tutti i fornitori: il primo pezzo dell'indirizzo dice chi è (/or, /groq, /cf, /cer)
stato = {"code": {"or": [], "groq": [], "cf": [], "cer": []}, "richieste": [], "key": (200, {"data": {"free_model_daily_requests": {"used": 3, "limit": 50, "remaining": 47}}}), "ritardo": 0}
class Finto(BaseHTTPRequestHandler):
    def _r(self, codice, dati):
        self.send_response(codice); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(dati).encode())
    def do_GET(self):
        stato["richieste"].append(("GET", self.path, self.headers.get("Authorization"), None)); self._r(*stato["key"])
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        chi = self.path.split("/")[1]
        stato["richieste"].append(("POST", self.path, self.headers.get("Authorization"), corpo, chi))
        if stato["ritardo"]: time.sleep(stato["ritardo"])
        try: self._r(*stato["code"][chi].pop(0))
        except (BrokenPipeError, ConnectionResetError): pass
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), Finto); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"

class Rollback(Exception): pass
PRIMA = {n: LogAttivita.objects.filter(tabella=n).count() for n in forn.FORNITORI}   # righe vere già presenti (richieste reali fatte a mano)
OR1, OR2 = ("openrouter", "m1:free"), ("openrouter", "m2:free")
def prova(coda_or, catena=None, tipo="segnalazione", utente="Commento di prova", visione=False, **code):
    stato["code"]["or"][:] = coda_or
    for k, v in code.items(): stato["code"][k][:] = v
    stato["richieste"].clear()
    try:
        return orr.chiedi(tipo, "Sei un filtro.", utente, SCHEMA, catena=([OR1, OR2] if catena is None else None if catena == "config" else catena), max_token=2000, visione=visione), None
    except orr.ErroreIA as e:
        return None, e
def post_fatte(chi=None): return [r for r in stato["richieste"] if r[0] == "POST" and (chi is None or r[4] == chi)]

impostazioni = dict(OPENROUTER_API_KEY="chiave-di-prova-segreta", GROQ_API_KEY="", CLOUDFLARE_API_TOKEN="", CLOUDFLARE_ACCOUNT_ID="", CEREBRAS_API_KEY="", MISTRAL_API_KEY="",
                    IA_FORNITORI=["openrouter"], IA_CATENA_TESTO="", IA_CATENA_VISIONE="", IA_INTERVALLO_MIN=0, IA_TIMEOUT_RICHIESTA=5,
                    IA_URL={"openrouter": BASE + "/or", "groq": BASE + "/groq", "cloudflare": BASE + "/cf", "cerebras": BASE + "/cer", "mistral": BASE + "/mis"})
ALTA = dict(IA_QUOTA_GIORNALIERA=10**6, IA_QUOTA_SEGNALAZIONI=10**6, IA_QUOTA_COMMENTI=10**6, IA_QUOTA_SOGLIA_COMMENTI=10**6)   # il registro di oggi contiene richieste vere
def con_env(**v): return {**forn.settings.IA_ENV, **v}
try:
    with override_settings(**impostazioni, **ALTA), transaction.atomic():
        orr._dormi = lambda s: None
        quota.azzera_cache()
        # ---- risposta valida e contenuto della richiesta
        r, e = prova([ok()])
        esito("risposta valida: dati, modello, token, sottofornitore e fornitore", r and r.dati == BUONO and r.modello == "m1:free" and r.token == 1500 and r.istradato_da == "Recursive" and r.fornitore == "openrouter", e)
        _, _, auth, corpo, _ = post_fatte()[0]
        esito("intestazione di autorizzazione presente", auth == "Bearer chiave-di-prova-segreta")
        esito("privacy OpenRouter: data_collection = deny", corpo["provider"] == {"data_collection": "deny"})
        esito("lo schema è nelle istruzioni, il testo dell'utente nel messaggio user", "risultati" in corpo["messages"][0]["content"] and corpo["messages"][1] == {"role": "user", "content": "Commento di prova"})
        esito("max_tokens, temperatura 0 e json_object", corpo["max_tokens"] == 2000 and corpo["temperature"] == 0 and corpo["response_format"] == {"type": "json_object"})
        # ---- registro e chiave
        riga = LogAttivita.objects.filter(tabella="openrouter").order_by("-id").first()
        esito("la richiesta è nel registro (tabella = fornitore), contata", riga and riga.dati_nuovi["contata"] is True and riga.dati_nuovi["modello"] == "m1:free" and riga.dati_nuovi["tipo"] == "segnalazione" and riga.dati_nuovi["fornitore"] == "openrouter")
        esito("la chiave non compare mai nel registro", not any("chiave-di-prova" in json.dumps(l.dati_nuovi) for n in forn.FORNITORI for l in LogAttivita.objects.filter(tabella=n)))
        # ---- JSON avvolto in testo o in ```
        r, e = prova([ok("Ecco:\n```json\n" + json.dumps(BUONO) + "\n```")]); esito("JSON dentro ``` letto", r and r.dati == BUONO, e)
        # ---- catena di modelli dello stesso fornitore
        r, e = prova([PRIVACY, ok()]); esito("404 privacy: passa al modello successivo", r and r.modello == "m2:free" and len(post_fatte()) == 2, e)
        riga404 = LogAttivita.objects.filter(tabella="openrouter", dati_nuovi__http=404).first()
        esito("il 404 è registrato ma non contato", riga404 is not None and riga404.dati_nuovi["contata"] is False)
        r, e = prova([A_MONTE, ok()]); esito("429 «a monte» di OpenRouter: modello successivo", r and r.modello == "m2:free", e)
        r, e = prova([(403, {"error": {"message": "only agentic harnesses"}}), ok()]); esito("403: modello successivo", r and r.modello == "m2:free", e)
        r, e = prova([PRIVACY, A_MONTE]); esito("tutti i modelli non disponibili: NessunModello", isinstance(e, orr.NessunModello), e)
        # ---- quota nostra con un solo fornitore
        r, e = prova([NOSTRA, ok()]); esito("429 del fornitore con un solo fornitore: QuotaEsaurita e nessun altro tentativo", isinstance(e, orr.QuotaEsaurita) and len(post_fatte()) == 1, e)
        quota.azzera_cache()
        # ---- errori del server
        r, e = prova([(500, {"error": {"message": "interno"}}), ok()], catena=[OR1]); esito("500 poi 200: un nuovo tentativo sullo stesso modello", r and r.modello == "m1:free" and len(post_fatte()) == 2, e)
        r, e = prova([(500, {}), (502, {}), ok()]); esito("due errori del server: passa al modello successivo", r and r.modello == "m2:free" and len(post_fatte()) == 3, e)
        r, e = prova([(500, {})] * 4); esito("errori ripetuti: NessunModello dopo 2+2 richieste", isinstance(e, orr.NessunModello) and len(post_fatte()) == 4, e)
        # ---- scadenza
        stato["ritardo"] = 2
        with override_settings(IA_TIMEOUT_RICHIESTA=1):
            r, e = prova([ok(), ok()], catena=[OR1]); esito("scadenza del tempo: NessunModello (un nuovo tentativo)", isinstance(e, orr.NessunModello) and len(post_fatte()) == 2, e)
        stato["ritardo"] = 0; time.sleep(2.5)
        # ---- risposte non valide: hanno consumato quota, nessun altro modello
        r, e = prova([ok(""), ok()]); esito("risposta vuota: RispostaNonValida, nessun altro modello", isinstance(e, orr.RispostaNonValida) and len(post_fatte()) == 1, e)
        riga = LogAttivita.objects.filter(tabella="openrouter", dati_nuovi__http=200).order_by("-id").first()
        esito("la risposta vuota è contata (ha consumato quota)", riga and riga.dati_nuovi["contata"] is True)
        r, e = prova([ok("non è json")]); esito("testo non JSON: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([ok(json.dumps({"risultati": [{"id": 1, "approvato": "sì", "motivazione": ""}]}))]); esito("tipo sbagliato: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([ok(json.dumps({"risultati": [{"id": 1, "approvato": True, "motivazione": "x" * 61}]}))]); esito("motivazione troppo lunga: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([ok(json.dumps({"risultati": [], "extra": 1}))]); esito("campo non previsto: RispostaNonValida", isinstance(e, orr.RispostaNonValida), e)
        r, e = prova([(200, {"error": {"code": 404, "message": "No endpoints"}}), ok()]); esito("200 con errore nel corpo trattato come l'errore", r and r.modello == "m2:free", e)
        # ---- chiavi e fornitori non configurati
        r, e = prova([(401, {"error": {"message": "No auth"}}), ok()]); esito("401: nessun altro modello dello stesso fornitore", isinstance(e, orr.NessunModello) and len(post_fatte()) == 1, e)
        with override_settings(OPENROUTER_API_KEY=""):
            r, e = prova([ok()]); esito("senza chiave: fornitore non configurato, nessuna richiesta, NessunModello", isinstance(e, orr.NessunModello) and not post_fatte(), e)
        with override_settings(IA_FORNITORI=[]):
            r, e = prova([ok()], catena="config"); esito("nessun fornitore attivo e nessuna catena: NessunModello senza richieste", isinstance(e, orr.NessunModello) and "nessun fornitore configurato" in str(e) and not post_fatte(), e)
        # ---- ritmo tra le richieste (per fornitore: 60 / richieste al minuto)
        attese, t = [], [100.0]
        orr._dormi = lambda s: (attese.append(s), t.__setitem__(0, t[0] + s)); orr._orologio = lambda: t[0]; orr._ultima.clear()
        with override_settings(IA_INTERVALLO_MIN=4):
            prova([ok(), ok()]); t[0] += 1; prova([ok()])
        esito("ritmo: la seconda richiesta attende il resto dell'intervallo (OpenRouter: 15 al minuto = 4 s)", len(attese) == 1 and abs(attese[0] - 3) < 0.01, attese)
        orr._dormi, orr._orologio = (lambda s: None), time.monotonic
        # ================= PIÙ FORNITORI =================
        multi = dict(GROQ_API_KEY="chiave-groq", CLOUDFLARE_API_TOKEN="chiave-cf", CLOUDFLARE_ACCOUNT_ID="acc42", IA_FORNITORI=["openrouter", "groq", "cloudflare"])
        with override_settings(**multi):
            groq, cf = forn.FORNITORI["groq"], forn.FORNITORI["cloudflare"]
            esito("catena predefinita: prima OpenRouter, poi Groq e Cloudflare", [f.nome for f, _ in forn.catena(False)] == ["openrouter", "groq", "groq", "cloudflare"], [f.nome for f, _ in forn.catena(False)])
            esito("catena delle foto: solo fornitori con un modello con visione, in ordine", [f.nome for f, _ in forn.catena(True)] == ["openrouter", "groq", "cloudflare"])
            # il primo fornitore non disponibile: si passa al secondo
            quota.azzera_cache()
            r, e = prova([PRIVACY, A_MONTE], catena=[OR1, OR2, ("groq", "llama-3.3-70b-versatile")], groq=[ok()])
            esito("OpenRouter senza modelli utilizzabili: risponde Groq", r and r.fornitore == "groq" and r.modello == "llama-3.3-70b-versatile" and len(post_fatte("or")) == 2 and len(post_fatte("groq")) == 1, e)
            _, _, auth, corpo, _ = post_fatte("groq")[0]
            esito("Groq: chiave propria, nessun parametro di privacy di OpenRouter, max_completion_tokens", auth == "Bearer chiave-groq" and "provider" not in corpo and corpo["max_completion_tokens"] == 2000 and "max_tokens" not in corpo)
            esito("la chiave di OpenRouter non va a Groq e viceversa", all(r_[2] == "Bearer chiave-di-prova-segreta" for r_ in post_fatte("or")))
            riga = LogAttivita.objects.filter(tabella="groq").order_by("-id").first()
            esito("il registro ha una riga per fornitore (tabella = nome)", riga and riga.dati_nuovi["fornitore"] == "groq" and riga.dati_nuovi["contata"] is True)
            # 429 del fornitore: si passa al successivo senza nuovi tentativi, e il fornitore resta da parte
            quota.azzera_cache()
            r, e = prova([NOSTRA], catena=[OR1, ("groq", "llama-3.3-70b-versatile")], groq=[ok()])
            esito("429 di OpenRouter: si passa a Groq, nessun nuovo tentativo", r and r.fornitore == "groq" and len(post_fatte("or")) == 1, e)
            esito("OpenRouter messo da parte dopo il suo limite", not quota.ammesso_da(forn.FORNITORI["openrouter"], "segnalazione")[0] and quota.stato(forn.FORNITORI["openrouter"])["messo_da_parte"])
            r, e = prova([ok()], catena=[OR1, ("groq", "llama-3.3-70b-versatile")], groq=[ok()])
            esito("il fornitore messo da parte viene saltato senza richieste", r and r.fornitore == "groq" and not post_fatte("or"), e)
            # tutti senza quota
            r, e = prova([ok()], catena=[OR1, ("groq", "llama-3.3-70b-versatile")], groq=[(429, {"error": {"message": "rate limit"}})])
            esito("tutti i fornitori senza quota: QuotaEsaurita", isinstance(e, orr.QuotaEsaurita), e)
            quota.azzera_cache()
            # errore non di quota su uno e quota sull'altro → NessunModello (non è solo quota)
            r, e = prova([PRIVACY], catena=[OR1, ("groq", "llama-3.3-70b-versatile")], groq=[(429, {"error": {"message": "rate limit"}})])
            esito("un fornitore senza modelli e uno senza quota: NessunModello", isinstance(e, orr.NessunModello) and not isinstance(e, orr.QuotaEsaurita), e)
            quota.azzera_cache()
            # fornitore non configurato
            with override_settings(GROQ_API_KEY=""):
                r, e = prova([PRIVACY], catena=[OR1, ("groq", "llama-3.3-70b-versatile")])
                esito("Groq senza chiave: non configurato, saltato senza errori né richieste", isinstance(e, orr.NessunModello) and not post_fatte("groq") and not forn.configurato(groq) and "GROQ_API_KEY" in forn.motivo_non_configurato(groq), e)
                esito("la catena predefinita senza la chiave di Groq non lo contiene", all(f.nome != "groq" for f, _ in forn.catena(False)))
            quota.azzera_cache()
            # visione: solo ai fornitori con visione
            foto = [{"type": "text", "text": "<segnalazione>x</segnalazione>"}, {"type": "text", "text": '<foto id="1">'}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}},
                    {"type": "text", "text": '<foto id="2">'}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,BBBB"}},
                    {"type": "text", "text": '<foto id="3">'}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,CCCC"}}]
            cat_v = forn.catena(True)
            r, e = prova([PRIVACY], catena="config", utente=foto, visione=True, groq=[ok()], cf=[ok()])
            esito("visione: la catena è quella dei modelli con visione (Groq, poi Cloudflare)", r and r.fornitore == "groq" and r.modello == "qwen/qwen3.8-27b", (r.fornitore, r.modello) if r else e)
            imgs = [p for p in post_fatte("groq")[0][3]["messages"][1]["content"] if p["type"] == "image_url"]
            esito("Groq: al massimo 3 immagini, con la loro etichetta", len(imgs) == 3)
            quota.azzera_cache()
            r, e = prova([PRIVACY], catena="config", utente=foto, visione=True, groq=[PRIVACY], cf=[ok()])
            cont = post_fatte("cf")[0][3]["messages"][1]["content"] if post_fatte("cf") else []
            esito("Cloudflare: una sola immagine; l'etichetta delle altre è tolta", r and r.fornitore == "cloudflare" and len([p for p in cont if p["type"] == "image_url"]) == 1 and len([p for p in cont if p.get("text", "").startswith("<foto")]) == 1, e)
            esito("Cloudflare: indirizzo con l'identificativo dell'account, nessun response_format, chiave propria", post_fatte("cf")[0][1].startswith("/cf/") and "response_format" not in post_fatte("cf")[0][3] and post_fatte("cf")[0][2] == "Bearer chiave-cf")
            esito("solo testo: i modelli senza visione non ricevono foto, e il testo va a tutti", [f.nome for f, _ in forn.catena(False)].count("groq") == 2)
            with override_settings(IA_URL={}):
                esito("indirizzo di Cloudflare: l'account entra nell'URL", forn.url_base(cf) == "https://api.cloudflare.com/client/v4/accounts/acc42/ai/v1")
            with override_settings(CLOUDFLARE_ACCOUNT_ID=""):
                esito("Cloudflare senza identificativo dell'account: non configurato", not forn.configurato(cf) and "CLOUDFLARE_ACCOUNT_ID" in forn.motivo_non_configurato(cf))
            # catena scelta a mano e precedenza delle impostazioni
            with override_settings(IA_CATENA_TESTO="groq:modello-x,openrouter:a:free"):
                esito("IA_CATENA_TESTO ha la precedenza e il modello può contenere «:»", [(f.nome, m) for f, m in forn.catena(False)] == [("groq", "modello-x"), ("openrouter", "a:free")])
            with override_settings(IA_ENV=con_env(GROQ_MODELLI_TESTO="m-a, m-b")):
                esito("modelli di un fornitore da variabile d'ambiente", [m for f, m in forn.catena(False) if f.nome == "groq"] == ["m-a", "m-b"])
            quota.azzera_cache()
        # ---- fornitori predisposti ma spenti
        with override_settings(CEREBRAS_API_KEY="chiave-cer", MISTRAL_API_KEY="chiave-mis", IA_FORNITORI=["openrouter", "cerebras", "mistral"]):
            mis, cer = forn.FORNITORI["mistral"], forn.FORNITORI["cerebras"]
            esito("Mistral: serve la conferma sul trattamento dei dati (può addestrare nel piano gratuito)", not forn.configurato(mis) and "MISTRAL_NIENTE_ADDESTRAMENTO" in forn.motivo_non_configurato(mis))
            with override_settings(IA_ENV=con_env(MISTRAL_NIENTE_ADDESTRAMENTO="1")):
                esito("Mistral con la conferma: configurato", forn.configurato(mis))
            esito("Cerebras con la chiave: configurato (modello di testo e di visione predefiniti)", forn.configurato(cer) and forn.modelli(cer) == ["gpt-oss-120b"] and forn.modelli(cer, True) == ["qwen-3.8-27b"])
            esito("fornitore non attivo: non è nella catena, ma si può scegliere a mano (prove)", "mistral" not in [f.nome for f, _ in forn.catena(False)] and not forn.configurato(mis) and forn.configurato(cer, True))
        with override_settings(IA_FORNITORI=["openrouter", "google"]):
            esito("«google» non è un fornitore previsto (escluso: usa i dati e i termini lo vietano nello SEE): ignorato", "google" not in forn.FORNITORI and [f.nome for f in forn.attivi()] == ["openrouter"])
        # ---- quota
        quota.azzera_cache(); stato["key"] = (200, {"data": {"free_model_daily_requests": {"used": 3, "limit": 50, "remaining": 47}}})
        orr_ = forn.FORNITORI["openrouter"]
        esito("contatore ufficiale letto da /key (OpenRouter) e solo da lui", quota.usate_ufficiali(orr_, forza=True) == 3 and quota.usate_ufficiali(forn.FORNITORI["groq"]) is None)
        s = quota.stato(orr_); esito("stato: usate = il maggiore tra ufficiale e registro, rimaste", s["usate"] >= 3 and s["usate"] == max(3, quota.usate_locali(orr_)) and s["rimaste"] == 10**6 - s["usate"], s)
        esito("la lettura di /key porta la chiave di OpenRouter", any(r_[0] == "GET" and r_[1] == "/or/key" and r_[2] == "Bearer chiave-di-prova-segreta" for r_ in stato["richieste"]))
        n = len([r_ for r_ in stato["richieste"] if r_[0] == "GET"]); quota.usate_ufficiali(orr_); esito("il valore è tenuto in memoria 60 secondi", len([r_ for r_ in stato["richieste"] if r_[0] == "GET"]) == n)
        def con_ufficiali(n): quota.azzera_cache(); stato["key"] = (200, {"data": {"free_model_daily_requests": {"used": n, "limit": 50, "remaining": 50 - n}}})
        con_ufficiali(0); esito("ammesso: segnalazione e commento a quota libera", quota.ammesso("segnalazione")[0] and quota.ammesso("commento")[0])
        with override_settings(IA_QUOTA_SOGLIA_COMMENTI=44):
            con_ufficiali(44); esito("da 44 in su: commenti no, segnalazioni sì", not quota.ammesso("commento")[0] and quota.ammesso("segnalazione")[0])
        with override_settings(IA_QUOTA_GIORNALIERA=50):
            con_ufficiali(50); a = quota.ammesso("segnalazione"); esito("a 50: nessuno, con il motivo", not a[0] and a[1] == quota.MOTIVO_ESAURITA and not quota.ammesso("commento")[0], a)
        # più fornitori: ammesso se ne basta uno
        with override_settings(IA_QUOTA_GIORNALIERA=50, GROQ_API_KEY="chiave-groq", IA_FORNITORI=["openrouter", "groq"]):
            con_ufficiali(50)
            esito("OpenRouter senza quota ma Groq con quota: il lavoro è ammesso", quota.ammesso("segnalazione")[0] and quota.ammesso("commento")[0])
            esito("quota per fornitore: ognuno ha i suoi limiti e contatori", quota.stato(forn.FORNITORI["groq"])["limite"] == 500 and quota.stato(orr_)["limite"] == 50 and quota.stato(forn.FORNITORI["groq"])["limiti"]["segnalazioni"] == 360)
            with override_settings(IA_ENV=con_env(GROQ_RPD="10")):
                l = forn.limiti(forn.FORNITORI["groq"]); esito("limiti di un fornitore da configurazione (GROQ_RPD=10 → 7 segnalazioni, 2 commenti, soglia 9)", (l["rpd"], l["segnalazioni"], l["commenti"], l["soglia"]) == (10, 7, 2, 9), l)
        with override_settings(GROQ_API_KEY="", IA_FORNITORI=["openrouter", "groq"], IA_QUOTA_GIORNALIERA=50):
            con_ufficiali(50); esito("nessun fornitore con quota: non ammesso", not quota.ammesso("segnalazione")[0])
        with override_settings(OPENROUTER_API_KEY="", IA_FORNITORI=["openrouter"]):
            a = quota.ammesso("segnalazione"); esito("nessun fornitore configurato: «nessun fornitore configurato»", not a[0] and a[1] == "nessun fornitore configurato", a)
        stato["key"] = (500, {}); quota.azzera_cache(); locali = quota.usate_locali(orr_)
        esito("/key non disponibile: si usa il registro locale", quota.usate_ufficiali(orr_, forza=True) is None and quota.stato(orr_)["usate"] == locali)
        with override_settings(IA_URL={"openrouter": "http://127.0.0.1:1"}):
            quota.azzera_cache(); esito("rete assente: nessun errore, si usa il registro", quota.usate_ufficiali(orr_, forza=True) is None)
        stato["key"] = (200, {"data": {"free_model_daily_requests": {"used": 0, "limit": 50, "remaining": 50}}}); quota.azzera_cache()
        with override_settings(**{**ALTA, "IA_QUOTA_SEGNALAZIONI": quota.usate_locali(orr_, "segnalazione") + 1}):
            quota.azzera_cache(); esito("sotto il tetto delle segnalazioni: ammessa", quota.ammesso("segnalazione")[0])
            quota.registra_richiesta("segnalazione", "openrouter", "m1:free", 200, 1.0, True); esito("tetto delle segnalazioni (impostazione) raggiunto", not quota.ammesso("segnalazione")[0])
        with override_settings(**{**ALTA, "IA_QUOTA_COMMENTI": quota.usate_locali(orr_, "commento") + 1}):
            quota.azzera_cache(); esito("sotto il tetto dei commenti: ammesso", quota.ammesso("commento")[0])
            quota.registra_richiesta("commento", "openrouter", "m1:free", 200, 1.0, True); esito("tetto dei commenti raggiunto", not quota.ammesso("commento")[0])
        quota.registra_richiesta("segnalazione", "openrouter", "m1:free", 404, 0.1, False)
        c = quota.usate_locali(orr_); quota.registra_richiesta("segnalazione", "openrouter", "m1:free", 429, 0.1, False); esito("le richieste non contate non aumentano il totale", quota.usate_locali(orr_) == c)
        quota.registra_richiesta("segnalazione", "groq", "m", 200, 1.0, True)
        esito("il contatore di un fornitore non conta le richieste di un altro", quota.usate_locali(forn.FORNITORI["groq"]) >= 1 and quota.usate_locali(orr_) == c)
        raise Rollback()
except Rollback:
    pass
srv.shutdown()
esito("nessuna riga lasciata nel registro dalla prova", all(LogAttivita.objects.filter(tabella=n).count() == PRIMA[n] for n in forn.FORNITORI))
