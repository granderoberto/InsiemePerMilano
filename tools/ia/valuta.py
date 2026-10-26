#!/usr/bin/env python3
"""Taratura dei controlli IA (docs/piano_ia_openrouter.md, fase 5 e «Multi-fornitore»): confronta le etichette scritte a mano con gli
esiti dei controlli, per uno o più fornitori sugli stessi contenuti.

Legge uno o più CSV di contenuti etichettati (predefinito: tools/ia/dataset/bozza_contenuti.csv e bozza_contenuti_2.csv; colonne id, tipo,
testo, etichetta, nota) e mette alla prova la stessa catena del sito:
  1. prefiltro locale (gratuito, nessuna richiesta): decide `bloccato`, `ok` (pulito) oppure «al modello»;
  2. modello (solo con --esegui): i commenti a blocchi, ogni segnalazione da sola. Consuma richieste della quota giornaliera!
Esito finale di un contenuto: bloccato dal prefiltro → bloccato; pulito → ok; altrimenti il modello: approvato → ok, no → dubbio;
senza risposta del modello → dubbio (come fa il sito). Con IA_RILEGGI_PULITI (predefinito attivo) anche i commenti «puliti» si mandano
al modello: restano `ok` finché il modello non li giudica non approvati (allora `dubbio`); senza risposta restano `ok`.

Scelta del fornitore (una chiave mancante significa «fornitore non configurato»: si salta, non è un errore):
  senza opzioni         la catena configurata nel sito (come prima)
  --fornitore groq      solo quel fornitore, con i suoi modelli predefiniti (o --modello ID per uno solo)
  --confronta a,b,c     ogni fornitore sugli stessi contenuti, con il tetto --max PER FORNITORE, e una tabella di confronto

Uso (dalla radice del progetto, con il Python del sito):
  apps/web/.venv/bin/python tools/ia/valuta.py                                     # solo prefiltro e piano delle richieste (nessuna richiesta)
  apps/web/.venv/bin/python tools/ia/valuta.py --esegui --max 8                    # catena predefinita, al massimo 8 richieste
  apps/web/.venv/bin/python tools/ia/valuta.py --esegui --fornitore groq --modello llama-3.3-70b-versatile --max 8
  apps/web/.venv/bin/python tools/ia/valuta.py --esegui --confronta openrouter,groq --max 6 --rapporto docs/ia_confronto.md
Le risposte si tengono in tools/ia/risultati/valuta_modello.json (una per fornitore, modello e testo): una seconda esecuzione sugli stessi
testi non consuma altre richieste (--ricalcola per rifarle)."""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE / "apps/web"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("LNC_PROVE", "1")   # nessuna email vera; il registro delle richieste invece è quello vero
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

from core.services.ia import fornitori, lavoratore, prefiltro, prompt, quota, router  # noqa: E402

ETICHETTE = ["ok", "dubbio", "bloccato"]
CACHE = Path(__file__).parent / "risultati" / "valuta_modello.json"
DATASET = Path(__file__).parent / "dataset"


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


def chiave_cache(r, sigla):
    """sigla vuota = catena predefinita (stessa chiave delle esecuzioni precedenti); altrimenti «fornitore:modello»."""
    base = f"{sigla}|{r['tipo']}|{r['testo']}" if sigla else f"{r['tipo']}|{r['testo']}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def locale(r):
    """Esito del prefiltro come nel sito: le segnalazioni hanno sempre foto, quindi vanno sempre al modello se non sono bloccate."""
    testo = r["testo"].replace(" | ", "\n")
    e = prefiltro.analizza(testo, ha_media=(r["tipo"] == "segnalazione"), tipo=r["tipo"])
    return {"bloccato": "bloccato", "pulito": "ok", "da_inviare": "modello", "doppione": "dubbio"}[e.esito], e


def catena_di(nome, modello):
    f = fornitori.FORNITORI[nome]
    return [(f, m) for m in ([modello] if modello else fornitori.modelli(f))]


def interroga(da_inviare, cache, massimo, ricalcola, sigla="", catena=None):
    """Manda al modello i contenuti non ancora in cache. Aggiorna `cache` ({chiave: {approvato, motivazione, modello}}). -> richieste fatte."""
    nuovi = [r for r in da_inviare if ricalcola or chiave_cache(r, sigla) not in cache]
    commenti = [r for r in nuovi if r["tipo"] == "commento"]
    segnalazioni = [r for r in nuovi if r["tipo"] == "segnalazione"]
    lavori = [("commento", commenti[i:i + settings.IA_COMMENTI_BLOCCO]) for i in range(0, len(commenti), settings.IA_COMMENTI_BLOCCO)]
    lavori += [("segnalazione", [r]) for r in segnalazioni]
    fatte, tentativi_attesa = 0, 0
    while lavori:
        tipo, gruppo = lavori.pop(0)
        if fatte >= massimo:
            print(f"  tetto di {massimo} richieste raggiunto: i contenuti restanti non hanno risposta del modello")
            break
        ok, motivo = quota.ammesso_da(catena[0][0], tipo) if catena else quota.ammesso(tipo)
        if not ok:
            print(f"  quota: {motivo}; mi fermo")
            break
        try:
            if tipo == "commento":
                utente = "\n".join(f'<commento id="{i}">{prompt.pulisci(r["testo"])}</commento>' for i, r in enumerate(gruppo, 1))
                risp = router.chiedi("commento", prompt.SISTEMA_COMMENTI, utente, prompt.SCHEMA_COMMENTI, catena=catena,
                                     max_token=lavoratore.max_token_commenti(len(gruppo)))
                per_id = {}
                for x in risp.dati["risultati"]:
                    per_id.setdefault(x["id"], x)
                for i, r in enumerate(gruppo, 1):
                    x = per_id.get(i)
                    if x:
                        cache[chiave_cache(r, sigla)] = {"approvato": x["approvato"], "motivazione": x["motivazione"], "modello": f"{risp.fornitore}:{risp.modello}"}
            else:
                r = gruppo[0]
                titolo, _, descrizione = r["testo"].partition(" | ")
                utente = f"<segnalazione>\n<titolo>{prompt.pulisci(titolo)}</titolo>\n<descrizione>{prompt.pulisci(descrizione)}</descrizione>\n</segnalazione>"
                risp = router.chiedi("segnalazione", prompt.SISTEMA_SEGNALAZIONE, utente, prompt.SCHEMA_SEGNALAZIONE, catena=catena,
                                     max_token=settings.IA_MAX_TOKEN_TESTO)
                cache[chiave_cache(r, sigla)] = {"approvato": risp.dati["approvato"], "motivazione": risp.dati["motivazione"], "modello": f"{risp.fornitore}:{risp.modello}"}
            fatte += 1
            print(f"  richiesta {fatte}: {tipo} ({len(gruppo)}) → {risp.fornitore}:{risp.modello} in {risp.secondi:.0f} s")
        except router.QuotaEsaurita:
            attesa = max((quota.secondi_residui(f) for f, _ in (catena or [])), default=0)
            if catena and 0 < attesa <= 150 and tentativi_attesa < 8:   # limite al minuto (token o richieste): si aspetta e si riprova lo stesso lavoro
                tentativi_attesa += 1
                print(f"  limite al minuto raggiunto: aspetto {attesa:.0f} s e riprovo")
                time.sleep(attesa + 1)
                lavori.insert(0, (tipo, gruppo))
                continue
            print("  quota esaurita: mi fermo")
            break
        except router.ErroreIA as e:
            fatte += 1
            print(f"  richiesta non riuscita ({tipo}): {e}")
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return fatte


def esiti_finali(righe, cache, sigla, rilettura):
    """Copia delle righe con l'esito finale di una catena."""
    out = []
    for r in righe:
        r = dict(r)
        m = cache.get(chiave_cache(r, sigla))
        if r["locale"] == "ok" and rilettura and r["tipo"] == "commento":   # già ok per il prefiltro: il modello può solo peggiorarlo
            if m is not None and not m["approvato"]:
                r["finale"], r["fonte"], r["motivazione"] = "dubbio", "rilettura del modello", m["motivazione"]
            else:
                r["finale"], r["fonte"] = "ok", "prefiltro" + (" (riletto)" if m is not None else "")
        elif r["locale"] in ("bloccato", "ok", "dubbio"):
            r["finale"], r["fonte"] = r["locale"], "prefiltro"
        elif m is None:
            r["finale"], r["fonte"], r["motivazione"] = "dubbio", "senza risposta del modello", ""
        else:
            r["finale"], r["fonte"], r["motivazione"] = ("ok" if m["approvato"] else "dubbio"), "modello", m["motivazione"]
        out.append(r)
    return out


def metriche(righe):
    mat = Counter((r["etichetta"], r["finale"]) for r in righe)
    return {"tot": len(righe), "corretti": sum(v for (e, f), v in mat.items() if e == f), "matrice": mat,
            "buoni_segnalati": sum(1 for r in righe if r["etichetta"] == "ok" and r["finale"] != "ok"), "n_ok": sum(r["etichetta"] == "ok" for r in righe),
            "passati": sum(1 for r in righe if r["etichetta"] != "ok" and r["finale"] == "ok"), "n_da_controllare": sum(r["etichetta"] != "ok" for r in righe),
            "minacce_mancate": sum(1 for r in righe if r["etichetta"] == "bloccato" and r["finale"] != "bloccato"), "n_minacce": sum(r["etichetta"] == "bloccato" for r in righe),
            "senza_risposta": sum(1 for r in righe if r["fonte"] == "senza risposta del modello")}


def sezione(titolo, righe, fatte):
    m = metriche(righe)
    out = [f"## {titolo}", "", f"Richieste in questa esecuzione: {fatte}", ""]
    if m["senza_risposta"]:
        out += [f"> **Attenzione**: {m['senza_risposta']} contenuti non hanno la risposta del modello e sono contati come `dubbio`: il risultato non è completo.", ""]
    out += ["| etichetta \\ esito | ok | dubbio | bloccato | totale |", "|---|---|---|---|---|"]
    for e in ETICHETTE:
        riga = [m["matrice"][(e, f)] for f in ETICHETTE]
        out.append(f"| **{e}** | " + " | ".join(map(str, riga)) + f" | {sum(riga)} |")
    out += ["", f"Corretti: **{m['corretti']} su {m['tot']}** ({100 * m['corretti'] / m['tot']:.0f}%).", "",
            f"- **Contenuti buoni segnalati** (ok → dubbio/bloccato): **{m['buoni_segnalati']}** su {m['n_ok']}",
            f"- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **{m['passati']}** su {m['n_da_controllare']}",
            f"- **Minacce non bloccate**: **{m['minacce_mancate']}** su {m['n_minacce']}", ""]
    per_fonte = Counter(r["fonte"] for r in righe)
    out += ["| deciso da | contenuti | corretti |", "|---|---|---|"]
    for f, n in per_fonte.items():
        out.append(f"| {f} | {n} | {sum(1 for r in righe if r['fonte'] == f and r['etichetta'] == r['finale'])} |")
    sbagliati = [r for r in righe if r["etichetta"] != r["finale"]]
    out += ["", f"**Errori ({len(sbagliati)})**", ""]
    if sbagliati:
        out += ["| id | tipo | atteso | esito | deciso da | segnali o motivo | testo |", "|---|---|---|---|---|---|---|"]
        for r in sbagliati:
            motivo = ", ".join(r["pf"].segnali)
            if r.get("motivazione"):
                motivo = (motivo + " · " if motivo else "") + r["motivazione"]
            out.append(f"| {r['id']} | {r['tipo']} | {r['etichetta']} | {r['finale']} | {r['fonte']} | {motivo} | {r['testo'][:90].replace('|', '/')} |")
    else:
        out.append("Nessuno.")
    out.append("")
    return out, m


def principale():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", nargs="+", default=[str(DATASET / "bozza_contenuti.csv"), str(DATASET / "bozza_contenuti_2.csv")], help="uno o più CSV")
    ap.add_argument("--esegui", action="store_true", help="manda al modello i contenuti che il prefiltro non decide (consuma quota)")
    ap.add_argument("--max", type=int, default=8, help="massimo di richieste al modello per ogni fornitore (predefinito 8)")
    ap.add_argument("--fornitore", help="usa solo questo fornitore (openrouter, groq, …)")
    ap.add_argument("--modello", help="con --fornitore: un solo modello al posto di quelli predefiniti")
    ap.add_argument("--confronta", help="fornitori da confrontare sugli stessi contenuti, separati da virgola")
    ap.add_argument("--senza-rilettura", action="store_true", help="i commenti puliti non vanno al modello")
    ap.add_argument("--ricalcola", action="store_true", help="rifà le richieste anche se la risposta è già in memoria")
    ap.add_argument("--rapporto", help="scrive il rapporto in un file Markdown")
    a = ap.parse_args()

    righe, scartate = [], []
    for f in a.file:
        r_, s_ = leggi(f)
        righe += r_; scartate += s_
    nome_file = ", ".join(Path(f).name for f in a.file)
    print(f"{len(righe)} contenuti letti da {nome_file}" + (f", {len(scartate)} righe scartate (tipo o etichetta non validi, testo vuoto)" if scartate else ""))
    print("etichette:", dict(Counter(r["etichetta"] for r in righe)))

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    rilettura = settings.IA_RILEGGI_PULITI and not a.senza_rilettura
    for r in righe:
        r["locale"], r["pf"] = locale(r)
    da_inviare = [r for r in righe if r["locale"] == "modello" or (rilettura and r["locale"] == "ok" and r["tipo"] == "commento")]
    print(f"prefiltro: {sum(r['locale'] == 'bloccato' for r in righe)} bloccati, {sum(r['locale'] == 'ok' for r in righe)} ok, {len(da_inviare)} da mandare al modello")

    # esecuzioni: (etichetta, sigla della cache, nome del fornitore o None per la catena configurata)
    def sigla_di(n):   # le risposte di OpenRouter con i modelli predefiniti sono quelle già in memoria dalla prima taratura
        return "" if n == "openrouter" and not a.modello else f"{n}:{a.modello or ''}"
    if a.confronta:
        esecuzioni = [(n.strip(), sigla_di(n.strip()), n.strip()) for n in a.confronta.split(",") if n.strip()]
    elif a.fornitore:
        esecuzioni = [(a.fornitore, sigla_di(a.fornitore), a.fornitore)]
    else:
        esecuzioni = [("catena configurata", "", None)]

    tutte, riepilogo = [], []
    for etichetta, sigla, nome in esecuzioni:
        catena = None
        if nome:
            if nome not in fornitori.FORNITORI:
                print(f"\n- {nome}: fornitore sconosciuto ({', '.join(fornitori.FORNITORI)})")
                continue
            f = fornitori.FORNITORI[nome]
            if not fornitori.configurato(f, True):
                print(f"\n- {f.etichetta}: non configurato ({fornitori.motivo_non_configurato(f, True)}), salto")
                riepilogo.append((f.etichetta, None))
                continue
            catena = catena_di(nome, a.modello)
        elif not fornitori.catena(False):
            print("\n- nessun fornitore configurato: i contenuti da mandare al modello restano senza risposta")
        nuovi = [r for r in da_inviare if a.ricalcola or chiave_cache(r, sigla) not in cache]
        n_comm = len([r for r in nuovi if r["tipo"] == "commento"])
        richieste = -(-n_comm // settings.IA_COMMENTI_BLOCCO) + len([r for r in nuovi if r["tipo"] == "segnalazione"])
        print(f"\n- {etichetta}: {len(da_inviare) - len(nuovi)} risposte già in memoria, richieste necessarie: {richieste}")
        fatte = 0
        if a.esegui and nuovi:
            fatte = interroga(da_inviare, cache, a.max, a.ricalcola, sigla, catena)
        elif nuovi:
            print("  (nessuna richiesta fatta: aggiungi --esegui per usare il modello)")
        righe_rapporto, m = sezione(etichetta, esiti_finali(righe, cache, sigla, rilettura), fatte)
        tutte += righe_rapporto
        riepilogo.append((etichetta, m))

    out = ["# Taratura dei controlli IA", "", f"Contenuti: {len(righe)} da `{nome_file}`. Risposte in memoria: {len(cache)}.", ""]
    if len(esecuzioni) > 1:
        out += ["## Confronto", "", "| fornitore | corretti | buoni segnalati | dubbi passati | minacce mancate | senza risposta |", "|---|---|---|---|---|---|"]
        for nome, m in riepilogo:
            out.append(f"| {nome} | non configurato | | | | |" if m is None else
                       f"| {nome} | {m['corretti']}/{m['tot']} | {m['buoni_segnalati']}/{m['n_ok']} | {m['passati']}/{m['n_da_controllare']} | {m['minacce_mancate']}/{m['n_minacce']} | {m['senza_risposta']} |")
        out.append("")
    out += tutte
    testo = "\n".join(out) + "\n"
    print("\n" + testo)
    if a.rapporto:
        Path(a.rapporto).write_text(testo, encoding="utf-8")
        print(f"rapporto scritto in {a.rapporto}")


if __name__ == "__main__":
    principale()
