#!/usr/bin/env python3
"""Fase 5 del piano IA (docs/piano_ia_openrouter.md): confronta le etichette scritte a mano con gli esiti dei controlli.

Legge un CSV di contenuti etichettati (predefinito: tools/ia/dataset/bozza_contenuti.csv; colonne id, tipo, testo, etichetta, nota)
e mette alla prova la stessa catena del sito:
  1. prefiltro locale (gratuito, nessuna richiesta): decide `bloccato`, `ok` (pulito) oppure «al modello»;
  2. modello (solo con --esegui): i commenti a blocchi di 25, ogni segnalazione da sola. Consuma richieste della quota giornaliera!
Esito finale di un contenuto: bloccato dal prefiltro → bloccato; pulito → ok; altrimenti il modello: approvato → ok, no → dubbio;
senza risposta del modello → dubbio (come fa il sito).

Uso (dalla radice del progetto, con il Python del sito):
  apps/web/.venv/bin/python tools/ia/valuta.py                       # solo prefiltro e piano delle richieste (nessuna richiesta)
  apps/web/.venv/bin/python tools/ia/valuta.py --esegui --max 8      # usa il modello, al massimo 8 richieste
  apps/web/.venv/bin/python tools/ia/valuta.py --file altro.csv --rapporto docs/ia_taratura.md
Le risposte del modello si tengono in tools/ia/risultati/valuta_modello.json: una seconda esecuzione sugli stessi testi non
consuma altre richieste (--ricalcola per rifarle). Il rapporto è un file Markdown con matrice di confusione ed errori."""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "apps/web"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("LNC_PROVE", "1")   # nessuna email vera; il registro delle richieste invece è quello vero
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

from core.services.ia import openrouter, prefiltro, prompt, quota  # noqa: E402

ETICHETTE = ["ok", "dubbio", "bloccato"]
CACHE = Path(__file__).parent / "risultati" / "valuta_modello.json"


def leggi(percorso):
    testo = Path(percorso).read_text(encoding="utf-8-sig")
    dialetto = csv.Sniffer().sniff(testo.split("\n", 1)[0] + "\n", delimiters=",;\t")
    righe, scartate = [], []
    for r in csv.DictReader(testo.splitlines(), dialect=dialetto):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        r["etichetta"] = r.get("etichetta", "").lower()
        if r.get("testo") and r.get("tipo") in ("commento", "segnalazione") and r["etichetta"] in ETICHETTE:
            righe.append(r)
        else:
            scartate.append(r)
    return righe, scartate


def impronta(r):
    return hashlib.sha256(f"{r['tipo']}|{r['testo']}".encode()).hexdigest()[:16]


def locale(r):
    """Esito del prefiltro come nel sito: le segnalazioni hanno sempre foto, quindi vanno sempre al modello se non sono bloccate."""
    testo = r["testo"].replace(" | ", "\n")
    e = prefiltro.analizza(testo, ha_media=(r["tipo"] == "segnalazione"), tipo=r["tipo"])
    return {"bloccato": "bloccato", "pulito": "ok", "da_inviare": "modello", "doppione": "dubbio"}[e.esito], e


def interroga(da_inviare, cache, massimo, ricalcola):
    """Manda al modello i contenuti non ancora in cache. Aggiorna `cache` ({impronta: {approvato, motivazione}}). -> richieste fatte."""
    nuovi = [r for r in da_inviare if ricalcola or impronta(r) not in cache]
    commenti = [r for r in nuovi if r["tipo"] == "commento"]
    segnalazioni = [r for r in nuovi if r["tipo"] == "segnalazione"]
    lavori = [("commento", commenti[i:i + settings.IA_COMMENTI_BLOCCO]) for i in range(0, len(commenti), settings.IA_COMMENTI_BLOCCO)]
    lavori += [("segnalazione", [r]) for r in segnalazioni]
    fatte = 0
    for tipo, gruppo in lavori:
        if fatte >= massimo:
            print(f"  tetto di {massimo} richieste raggiunto: i contenuti restanti non hanno risposta del modello")
            break
        ok, motivo = quota.ammesso(tipo)
        if not ok:
            print(f"  quota: {motivo}; mi fermo")
            break
        try:
            if tipo == "commento":
                utente = "\n".join(f'<commento id="{i}">{prompt.pulisci(r["testo"])}</commento>' for i, r in enumerate(gruppo, 1))
                risp = openrouter.chiedi("commento", prompt.SISTEMA_COMMENTI, utente, prompt.SCHEMA_COMMENTI,
                                         modelli=settings.IA_MODELLI_TESTO, max_token=settings.IA_MAX_TOKEN_TESTO)
                per_id = {}
                for x in risp.dati["risultati"]:
                    per_id.setdefault(x["id"], x)
                for i, r in enumerate(gruppo, 1):
                    x = per_id.get(i)
                    if x:
                        cache[impronta(r)] = {"approvato": x["approvato"], "motivazione": x["motivazione"], "modello": risp.modello}
            else:
                r = gruppo[0]
                titolo, _, descrizione = r["testo"].partition(" | ")
                utente = f"<segnalazione>\n<titolo>{prompt.pulisci(titolo)}</titolo>\n<descrizione>{prompt.pulisci(descrizione)}</descrizione>\n</segnalazione>"
                risp = openrouter.chiedi("segnalazione", prompt.SISTEMA_SEGNALAZIONE, utente, prompt.SCHEMA_SEGNALAZIONE,
                                         modelli=settings.IA_MODELLI_TESTO, max_token=settings.IA_MAX_TOKEN_TESTO)
                cache[impronta(r)] = {"approvato": risp.dati["approvato"], "motivazione": risp.dati["motivazione"], "modello": risp.modello}
            fatte += 1
            print(f"  richiesta {fatte}: {tipo} ({len(gruppo)}) → {risp.modello} in {risp.secondi:.0f} s")
        except openrouter.QuotaEsaurita:
            print("  quota di OpenRouter esaurita: mi fermo")
            break
        except openrouter.ErroreIA as e:
            fatte += 1
            print(f"  richiesta non riuscita ({tipo}): {e}")
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return fatte


def principale():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(Path(__file__).parent / "dataset" / "bozza_contenuti.csv"))
    ap.add_argument("--esegui", action="store_true", help="manda al modello i contenuti che il prefiltro non decide (consuma quota)")
    ap.add_argument("--max", type=int, default=8, help="massimo di richieste al modello (predefinito 8)")
    ap.add_argument("--ricalcola", action="store_true", help="rifà le richieste anche se la risposta è già in memoria")
    ap.add_argument("--rapporto", help="scrive il rapporto in un file Markdown")
    a = ap.parse_args()

    righe, scartate = leggi(a.file)
    print(f"{len(righe)} contenuti letti da {Path(a.file).name}" + (f", {len(scartate)} righe scartate (tipo o etichetta non validi, testo vuoto)" if scartate else ""))
    print("etichette:", dict(Counter(r["etichetta"] for r in righe)))

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    for r in righe:
        r["locale"], r["pf"] = locale(r)
    da_inviare = [r for r in righe if r["locale"] == "modello"]
    nuovi = [r for r in da_inviare if a.ricalcola or impronta(r) not in cache]
    n_comm = len([r for r in nuovi if r["tipo"] == "commento"])
    richieste = -(-n_comm // settings.IA_COMMENTI_BLOCCO) + len([r for r in nuovi if r["tipo"] == "segnalazione"])
    print(f"prefiltro: {sum(r['locale'] == 'bloccato' for r in righe)} bloccati, {sum(r['locale'] == 'ok' for r in righe)} ok, "
          f"{len(da_inviare)} al modello ({len(da_inviare) - len(nuovi)} già in memoria)")
    print(f"richieste al modello necessarie: {richieste}")

    fatte = 0
    if a.esegui and nuovi:
        s = quota.stato(forza=True)
        print(f"quota oggi: {s['usate']}/{s['limite']} usate; ne servono {richieste}, tetto {a.max}")
        fatte = interroga(da_inviare, cache, a.max, a.ricalcola)
    elif nuovi:
        print("(nessuna richiesta fatta: aggiungi --esegui per usare il modello)")

    for r in righe:
        if r["locale"] in ("bloccato", "ok", "dubbio"):
            r["finale"], r["fonte"] = r["locale"], "prefiltro"
        else:
            m = cache.get(impronta(r))
            if m is None:
                r["finale"], r["fonte"], r["motivazione"] = "dubbio", "senza risposta del modello", ""
            else:
                r["finale"], r["fonte"], r["motivazione"] = ("ok" if m["approvato"] else "dubbio"), "modello", m["motivazione"]
    rapporto(righe, a, fatte, cache)


def rapporto(righe, a, fatte, cache):
    senza = [r for r in righe if r["fonte"] == "senza risposta del modello"]
    matrice = Counter((r["etichetta"], r["finale"]) for r in righe)
    giusti = sum(v for (e, f), v in matrice.items() if e == f)
    out = [f"# Taratura dei controlli IA", "",
           f"Contenuti: {len(righe)} da `{Path(a.file).name}` · richieste al modello in questa esecuzione: {fatte} · risposte del modello in memoria: {len(cache)}", ""]
    if senza:
        out += [f"> **Attenzione**: {len(senza)} contenuti non hanno la risposta del modello e sono contati come `dubbio`: il risultato non è completo.", ""]
    out += ["## Esito finale rispetto alle tue etichette", "", "| etichetta \\ esito | ok | dubbio | bloccato | totale |", "|---|---|---|---|---|"]
    for e in ETICHETTE:
        riga = [matrice[(e, f)] for f in ETICHETTE]
        out.append(f"| **{e}** | " + " | ".join(map(str, riga)) + f" | {sum(riga)} |")
    out += ["", f"Corretti: **{giusti} su {len(righe)}** ({100 * giusti / len(righe):.0f}%).", ""]
    fp = [r for r in righe if r["etichetta"] == "ok" and r["finale"] != "ok"]
    fn = [r for r in righe if r["etichetta"] != "ok" and r["finale"] == "ok"]
    gravi = [r for r in righe if r["etichetta"] == "bloccato" and r["finale"] != "bloccato"]
    out += [f"- **Contenuti buoni segnalati** (ok → dubbio/bloccato, fastidio per gli utenti e lavoro per il moderatore): **{len(fp)}** su {sum(r['etichetta'] == 'ok' for r in righe)}",
            f"- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **{len(fn)}** su {sum(r['etichetta'] != 'ok' for r in righe)}",
            f"- **Minacce non bloccate** (bloccato → ok/dubbio): **{len(gravi)}** su {sum(r['etichetta'] == 'bloccato' for r in righe)}", ""]
    per_fonte = Counter(r["fonte"] for r in righe)
    out += ["## Chi ha deciso", "", "| fonte | contenuti | corretti |", "|---|---|---|"]
    for f, n in per_fonte.items():
        out.append(f"| {f} | {n} | {sum(1 for r in righe if r['fonte'] == f and r['etichetta'] == r['finale'])} |")
    sbagliati = [r for r in righe if r["etichetta"] != r["finale"]]
    out += ["", f"## Errori ({len(sbagliati)})", ""]
    if sbagliati:
        out += ["| id | tipo | atteso | esito | deciso da | segnali o motivo | testo |", "|---|---|---|---|---|---|---|"]
        for r in sbagliati:
            motivo = ", ".join(r["pf"].segnali) or r.get("motivazione", "")
            if r.get("motivazione"):
                motivo = (motivo + " · " if motivo else "") + r["motivazione"]
            out.append(f"| {r['id']} | {r['tipo']} | {r['etichetta']} | {r['finale']} | {r['fonte']} | {motivo} | {r['testo'][:90].replace('|', '/')} |")
    else:
        out.append("Nessuno.")
    testo = "\n".join(out) + "\n"
    print("\n" + testo)
    if a.rapporto:
        Path(a.rapporto).write_text(testo, encoding="utf-8")
        print(f"rapporto scritto in {a.rapporto}")


if __name__ == "__main__":
    principale()
