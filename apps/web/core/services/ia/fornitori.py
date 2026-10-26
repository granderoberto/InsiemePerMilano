"""Fornitori di modelli per i controlli IA (docs/piano_ia_openrouter.md, «Multi-fornitore»).

Ogni fornitore ha un'interfaccia compatibile con quella di OpenAI («chat/completions»): cambiano indirizzo, chiave, nome del modello,
parametro di privacy e limiti. Un fornitore è utilizzabile solo se è attivo (`IA_FORNITORI`), ha la chiave e, quando serve, la conferma
sul trattamento dei dati. Senza chiave è «non configurato»: si salta, non è un errore.

Trattamento dei dati nel piano gratuito (verificato sulla documentazione il 2026-10-26):
  openrouter  richiesta `data_collection = "deny"`: restano solo i fornitori che non addestrano sui dati (pochi modelli gratuiti)
  groq        il contratto vieta di usare input e output per addestrare (Services Agreement, 4.2); log di sicurezza fino a 30 giorni
  cloudflare  la documentazione dice che non usa i contenuti dei clienti per addestrare
  cerebras    nessuna conservazione dei prompt dichiarata; sull'addestramento le fonti non sono concordi: predisposto, spento
  mistral     il piano gratuito PUÒ addestrare sui dati se non si disattiva l'opzione nel pannello: usabile solo con MISTRAL_NIENTE_ADDESTRAMENTO=1
  google      ESCLUSO: nel piano gratuito usa i contenuti per migliorare i prodotti e i termini consentono solo il piano a pagamento per utenti nello SEE"""
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True, eq=False)   # eq=False: si confronta per identità (gli elementi sono unici) e si può usare come chiave
class Fornitore:
    nome: str
    etichetta: str
    url_base: str                      # per cloudflare contiene {account}
    env_chiave: str                    # nome dell'impostazione che contiene la chiave
    rpm: int                           # richieste al minuto consentite (il ritmo si calcola da qui)
    rpd: int                           # richieste al giorno: il tetto che ci diamo, non per forza quello del fornitore
    testo: tuple = ()                  # modelli predefiniti per il solo testo, in ordine di preferenza
    visione: tuple = ()                # modelli predefiniti con visione
    privacy: tuple = ()                # coppie (chiave, valore) da aggiungere al corpo della richiesta
    campo_token: str = "max_tokens"
    json_object: bool = True           # supporta response_format {"type": "json_object"}
    max_immagini: int = 5
    reset: str = "UTC"                 # fuso in cui si azzera la quota giornaliera
    contatore_ufficiale: bool = False  # esiste un'interfaccia che dice quante richieste abbiamo usato
    richiede: str = ""                 # variabile (in IA_ENV) che deve valere «1» per usarlo
    nota_dati: str = ""

    def env(self, suffisso, default=""):
        return settings.IA_ENV.get(f"{self.nome.upper()}_{suffisso}") or default


FORNITORI = {f.nome: f for f in (
    Fornitore("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", rpm=15, rpd=50,
              privacy=(("provider", {"data_collection": "deny"}),), contatore_ufficiale=True,
              nota_dati="data_collection=deny: solo fornitori che non addestrano"),
    Fornitore("groq", "Groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", rpm=20, rpd=500,
              testo=("llama-3.3-70b-versatile", "openai/gpt-oss-20b"), visione=("qwen/qwen3.8-27b",),
              campo_token="max_completion_tokens", max_immagini=3,
              nota_dati="il contratto vieta di addestrare su input e output; log di sicurezza fino a 30 giorni"),
    Fornitore("cloudflare", "Cloudflare Workers AI", "https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1", "CLOUDFLARE_API_TOKEN",
              rpm=20, rpd=100, testo=("@cf/meta/llama-3.3-70b-instruct-fp8-fast",), visione=("@cf/meta/llama-3.2-11b-vision-instruct",),
              json_object=False, max_immagini=1, nota_dati="non usa i contenuti dei clienti per addestrare (10.000 neuroni al giorno, azzeramento 00:00 UTC)"),
    Fornitore("cerebras", "Cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", rpm=5, rpd=200,
              testo=("gpt-oss-120b",), visione=("qwen-3.8-27b",), max_immagini=2,
              nota_dati="nessuna conservazione dei prompt dichiarata; addestramento da confermare; crediti di prova che scadono dopo 30 giorni"),
    Fornitore("mistral", "Mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", rpm=30, rpd=500,
              testo=("mistral-small-latest",), visione=("mistral-small-latest",), richiede="MISTRAL_NIENTE_ADDESTRAMENTO",
              nota_dati="il piano gratuito può addestrare: serve disattivare l'opzione nel pannello Mistral e impostare MISTRAL_NIENTE_ADDESTRAMENTO=1"),
)}


def lista_env(valore):
    return [x.strip() for x in str(valore).split(",") if x.strip()]


def chiave(f):
    return getattr(settings, f.env_chiave, "") or ""


def url_base(f):
    base = settings.IA_URL.get(f.nome) or f.url_base
    return base.replace("{account}", getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "") or "")


def limiti(f):
    """{rpm, rpd, segnalazioni, commenti, soglia}: per OpenRouter vale ciò che è nelle impostazioni (50 richieste al giorno: 36 + 8 + riserva)."""
    if f.nome == "openrouter":
        rpd = settings.IA_QUOTA_GIORNALIERA
        return {"rpm": int(f.env("RPM", f.rpm)), "rpd": int(f.env("RPD", rpd)), "segnalazioni": settings.IA_QUOTA_SEGNALAZIONI,
                "commenti": settings.IA_QUOTA_COMMENTI, "soglia": settings.IA_QUOTA_SOGLIA_COMMENTI}
    rpd = int(f.env("RPD", f.rpd))
    return {"rpm": int(f.env("RPM", f.rpm)), "rpd": rpd, "segnalazioni": round(rpd * 0.72), "commenti": round(rpd * 0.16), "soglia": round(rpd * 0.88)}


def attivi():
    """I fornitori attivi per impostazione, nell'ordine di preferenza."""
    return [FORNITORI[n] for n in settings.IA_FORNITORI if n in FORNITORI]


def configurato(f, esplicito=False):
    """Attivo, con la chiave e con la conferma sul trattamento dei dati quando serve. `esplicito`: scelto a mano (prove e confronti),
    quindi non serve che sia nell'elenco dei fornitori attivi."""
    if (f.nome not in settings.IA_FORNITORI and not esplicito) or not chiave(f):
        return False
    if f.nome == "cloudflare" and not getattr(settings, "CLOUDFLARE_ACCOUNT_ID", ""):
        return False
    return not f.richiede or settings.IA_ENV.get(f.richiede) == "1"


def motivo_non_configurato(f, esplicito=False):
    if f.nome not in settings.IA_FORNITORI and not esplicito:
        return "non attivo (IA_FORNITORI)"
    if not chiave(f):
        return f"manca {f.env_chiave}"
    if f.nome == "cloudflare" and not getattr(settings, "CLOUDFLARE_ACCOUNT_ID", ""):
        return "manca CLOUDFLARE_ACCOUNT_ID"
    if f.richiede and settings.IA_ENV.get(f.richiede) != "1":
        return f"serve {f.richiede}=1 (trattamento dei dati)"
    return ""


def modelli(f, visione=False):
    predefiniti = (settings.IA_MODELLI_VISIONE if visione else settings.IA_MODELLI_TESTO) if f.nome == "openrouter" else (f.visione if visione else f.testo)
    return lista_env(f.env("MODELLI_VISIONE" if visione else "MODELLI_TESTO")) or list(predefiniti)


def catena(visione=False):
    """[(fornitore, modello)] in ordine di preferenza, solo con i fornitori configurati. IA_CATENA_TESTO / IA_CATENA_VISIONE hanno la precedenza."""
    esplicita = lista_env(settings.IA_CATENA_VISIONE if visione else settings.IA_CATENA_TESTO)
    if esplicita:
        out = []
        for voce in esplicita:
            nome, _, modello = voce.partition(":")   # il modello può contenere altri «:» (es. «…:free»)
            f = FORNITORI.get(nome)
            if f and modello and configurato(f):
                out.append((f, modello))
        return out
    return [(f, m) for f in attivi() if configurato(f) for m in modelli(f, visione)]
