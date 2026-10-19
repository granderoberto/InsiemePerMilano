"""Genera il modello logico (docs/modello_logico.md, .svg, .png) leggendo db/schema.sql: nessun database necessario.
Uso: tools/.venv/bin/python tools/logico/genera.py   (per il PNG su macOS: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib)"""
import html, pathlib, re, sys

RADICE = pathlib.Path(__file__).resolve().parents[2]
SQL = (RADICE / "db" / "schema.sql").read_text(encoding="utf-8")

DOMINI = [
    ("Utenti e accesso", ["quartieri", "utenti", "verifiche_identita", "sospensioni", "documenti_normativi", "consensi"]),
    ("Segnalazioni", ["stati", "transizioni_ammesse", "categorie", "segnalazioni", "media", "classificazioni", "cambi_stato"]),
    ("Community", ["sostegni", "commenti", "candidati", "invii"]),
    ("Moderazione, notifiche e log", ["richieste_revisione", "notifiche", "preferenze_notifica", "log_attivita"]),
]
DESCRIZIONI = {
    "quartieri": "I 88 Nuclei di Identità Locale (NIL) di Milano, con il confine in GeoJSON.",
    "utenti": "Persone registrate, con ruolo e stato dell'account separati; per SPID/CIE si conserva solo l'hash del codice fiscale.",
    "verifiche_identita": "Tentativi di verifica del documento (al massimo 3 per utente): cinque controlli, punteggio, esito dell'IA ed eventuale revisione umana.",
    "sospensioni": "Periodi di sospensione di un account, con motivo e moderatore.",
    "documenti_normativi": "Versioni dei testi normativi (privacy, biometrici, IA, termini, cookie, età minima).",
    "consensi": "Quale versione di quale documento ha accettato ogni utente (associazione N:N con data).",
    "stati": "I cinque stati del ciclo di vita di una segnalazione.",
    "transizioni_ammesse": "Passaggi consentiti tra stati: li impone un trigger.",
    "categorie": "Categorie tematiche (ambiente, mobilità, decoro, sicurezza, giovani) attivabili dall'amministratore.",
    "segnalazioni": "Segnalazioni e proposte dei cittadini, con posizione, stato, esito della moderazione IA ed eliminazione logica.",
    "media": "Foto e video allegati (1-10 per segnalazione) con gli esiti dei controlli visivi.",
    "classificazioni": "Categorie assegnate a una segnalazione, con origine (IA, utente, moderatore) e confidenza (associazione N:N).",
    "cambi_stato": "Cronologia degli stati di una segnalazione, con chi e quando.",
    "sostegni": "Sostegno di un utente a una segnalazione (associazione N:N, uno per coppia).",
    "commenti": "Commenti e risposte (stessa segnalazione del commento padre), con esito di moderazione.",
    "candidati": "Candidati Sindaco a cui si presentano le segnalazioni.",
    "invii": "Presentazione di una segnalazione a un candidato da parte di un moderatore (associazione ternaria).",
    "richieste_revisione": "Richieste di revisione umana su una segnalazione bloccata, un commento nascosto o una verifica rifiutata.",
    "notifiche": "Notifiche per utente.",
    "preferenze_notifica": "Per ogni utente e tipo di evento, se riceverlo nell'app e per email.",
    "log_attivita": "Registro delle attività, solo aggiunte (trigger che bloccano UPDATE e DELETE).",
}


def spezza(corpo):
    """Divide per virgole di primo livello."""
    voci, prof, att, in_str = [], 0, [], False
    for ch in corpo:
        if ch == "'" : in_str = not in_str
        if not in_str:
            if ch == "(": prof += 1
            elif ch == ")": prof -= 1
            elif ch == "," and prof == 0:
                voci.append("".join(att).strip()); att = []; continue
        att.append(ch)
    if "".join(att).strip(): voci.append("".join(att).strip())
    return voci


def leggi_tabelle():
    t = {}
    for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\) ENGINE", SQL, re.S):
        nome, corpo = m.group(1), re.sub(r"--[^\n]*", "", m.group(2))
        info = {"colonne": [], "pk": [], "fk": [], "unique": [], "check": [], "indici": []}
        for v in spezza(corpo):
            v = " ".join(v.split())
            if not v: continue
            if v.startswith("PRIMARY KEY"):
                info["pk"] = [c.strip() for c in re.search(r"\((.*)\)", v).group(1).split(",")]
            elif v.startswith("CONSTRAINT") and "FOREIGN KEY" in v:
                r = re.search(r"CONSTRAINT (\w+) FOREIGN KEY \((\w+)\) REFERENCES (\w+)\((\w+)\)(.*)", v)
                info["fk"].append({"nome": r.group(1), "col": r.group(2), "rif": r.group(3), "rifcol": r.group(4), "extra": r.group(5).strip()})
            elif v.startswith("CONSTRAINT") and "CHECK" in v:
                r = re.search(r"CONSTRAINT (\w+) CHECK \((.*)\)$", v)
                info["check"].append((r.group(1), r.group(2).strip()))
            elif v.startswith("UNIQUE KEY"):
                r = re.search(r"UNIQUE KEY (\w+) \((.*)\)", v)
                info["unique"].append((r.group(1), [c.strip() for c in r.group(2).split(",")]))
            elif v.startswith("KEY"):
                r = re.search(r"KEY (\w+) \((.*)\)", v)
                info["indici"].append((r.group(1), [c.strip() for c in r.group(2).split(",")]))
            else:
                r = re.match(r"(\w+) (.*)", v)
                col, resto = r.group(1), r.group(2)
                tipo = re.match(r"(ENUM\(.*?\)|\w+(?:\(\d+(?:,\d+)?\))?(?: UNSIGNED)?)", resto).group(1)
                c = {"nome": col, "tipo": tipo, "null": "NOT NULL" not in resto and "PRIMARY KEY" not in resto,
                     "default": (re.search(r"DEFAULT (\S+(?:\(\d+\))?)", resto) or [None, None])[1],
                     "auto": "AUTO_INCREMENT" in resto, "unico": " UNIQUE" in resto, "gen": "GENERATED" in resto}
                if "PRIMARY KEY" in resto: info["pk"] = [col]
                info["colonne"].append(c)
        t[nome] = info
    return t


def trigger_e_viste():
    trig = re.findall(r"CREATE TRIGGER (\w+) (BEFORE|AFTER) (INSERT|UPDATE|DELETE) ON (\w+)", SQL)
    viste = re.findall(r"CREATE VIEW (\w+) AS", SQL)
    return trig, viste


def tipo_breve(t):
    return t.replace("DATETIME(3)", "DATETIME(3)").replace("BOOLEAN", "BOOLEAN")


def notazione(nome, info):
    fk = {f["col"] for f in info["fk"]}
    parti = []
    for c in info["colonne"]:
        n = c["nome"]
        if n in info["pk"] and n in fk: parti.append(f"<u>*{n}*</u>")
        elif n in info["pk"]: parti.append(f"<u>{n}</u>")
        elif n in fk: parti.append(f"*{n}*")
        else: parti.append(n)
    for n in info["pk"]:
        if n not in [c["nome"] for c in info["colonne"]]: parti.append(f"<u>{n}</u>")
    return f"**{nome.upper()}** ( " + ", ".join(parti) + " )"


def markdown(t):
    trig, viste = trigger_e_viste()
    L = []
    w = L.append
    w("# Modello logico\n")
    w("Progetto: La Nostra Città, Il Nostro Futuro\n")
    w("Il modello logico traduce il modello ER ([`modello_er.md`](modello_er.md)) in uno schema relazionale per **MySQL 8**. È generato da [`db/schema.sql`](../db/schema.sql) con `tools/logico/genera.py`: non si modifica a mano, si rigenera. Lo schema fisico (tipi, trigger, viste, dati iniziali) è in `db/schema.sql`; il diagramma è [`modello_logico.png`](modello_logico.png) (sorgente vettoriale [`modello_logico.svg`](modello_logico.svg)).\n")
    w("![Diagramma del modello logico](modello_logico.png)\n")
    w("## Notazione\n")
    w("- <u>sottolineato</u> = chiave primaria (PK); *corsivo* = chiave esterna (FK); <u>*sottolineato e corsivo*</u> = chiave primaria che è anche chiave esterna.")
    w("- Le tabelle sono al plurale e in `snake_case`, come richiede la regola del progetto. Nell'ER le stesse cose sono entità al singolare.")
    w("")
    w("## Schema relazionale\n")
    n = 0
    for dominio, tabelle in DOMINI:
        w(f"### {dominio}\n")
        for nome in tabelle:
            n += 1
            w(notazione(nome, t[nome]) + "\n")
        w("")
    w("## Dizionario delle tabelle\n")
    for dominio, tabelle in DOMINI:
        w(f"### {dominio}\n")
        for nome in tabelle:
            info = t[nome]
            w(f"#### `{nome}`\n")
            w(DESCRIZIONI[nome] + "\n")
            w("| Colonna | Tipo | Null | Note |")
            w("|---|---|---|---|")
            fkmap = {f["col"]: f for f in info["fk"]}
            for c in info["colonne"]:
                note = []
                if c["nome"] in info["pk"]: note.append("PK" + (" (composta)" if len(info["pk"]) > 1 else ""))
                if c["nome"] in fkmap: f = fkmap[c["nome"]]; note.append(f"FK → `{f['rif']}.{f['rifcol']}`" + (f" {f['extra']}" if f["extra"] else ""))
                if c["unico"]: note.append("UNIQUE")
                if c["auto"]: note.append("auto-incremento")
                if c["gen"]: note.append("colonna generata")
                if c["default"]: note.append(f"default {c['default']}")
                tipo = c["tipo"].replace("|", "\\|")
                w(f"| `{c['nome']}` | `{tipo}` | {'sì' if c['null'] else 'no'} | {'; '.join(note)} |")
            extra = []
            for nome_u, cols in info["unique"]: extra.append(f"UNIQUE `{nome_u}` ({', '.join(cols)})")
            for nome_i, cols in info["indici"]: extra.append(f"indice `{nome_i}` ({', '.join(cols)})")
            if extra: w("\nVincoli di unicità e indici: " + "; ".join(extra) + ".")
            if info["check"]:
                w("\nVincoli CHECK:\n")
                for nc, cl in info["check"]: w(f"- `{nc}`: `{cl}`")
            w("")
    w("## Associazioni tra le tabelle (chiavi esterne)\n")
    w("| Da (N) | Colonna | A (1) | Colonna | Azione |")
    w("|---|---|---|---|---|")
    for dominio, tabelle in DOMINI:
        for nome in tabelle:
            for f in t[nome]["fk"]:
                w(f"| `{nome}` | `{f['col']}` | `{f['rif']}` | `{f['rifcol']}` | {f['extra'] or 'RESTRICT (predefinita)'} |")
    w(f"\nTotale: {sum(len(v['fk']) for v in t.values())} chiavi esterne tra {len(t)} tabelle.\n")
    w("## Dal modello ER al modello logico\n")
    w("| Costrutto dell'ER | Regola applicata | Risultato |")
    w("|---|---|---|")
    w("| Entità | una tabella, con la chiave primaria surrogata `id` (intero auto-incrementale), salvo l'entità debole | 16 tabelle «entità» (le altre 5 vengono dalle associazioni) |")
    w("| Associazione 1:N | la chiave primaria del lato 1 diventa chiave esterna nel lato N | es. `segnalazioni.id_autore → utenti.id`, `commenti.id_segnalazione → segnalazioni.id` |")
    w("| Associazione N:N con attributi | una tabella ponte con chiave primaria composta dalle due chiavi esterne | `sostegni`, `classificazioni`, `consensi`, `transizioni_ammesse` (5 tabelle in tutto con `invii`) |")
    w("| Entità debole (esiste solo in funzione di un'altra) | chiave primaria composta che include la chiave dell'entità forte | `preferenze_notifica` (`id_utente`, `tipo`) |")
    w("| Associazione ternaria INVIA (segnalazione, candidato, moderatore) | una tabella con le tre chiavi esterne e unicità su (segnalazione, candidato) | `invii` |")
    w("| Associazione ricorsiva (risposta a un commento) | chiave esterna verso la stessa tabella | `commenti.id_padre → commenti.id` |")
    w("| Associazione ricorsiva su UTENTE (revisore, moderatore) | più chiavi esterne verso `utenti` con ruoli diversi | `verifiche_identita.id_revisore`, `segnalazioni.id_moderatore_nascosta`, `invii.id_moderatore` |")
    w("| Associazione «esclusiva» (la richiesta riguarda una cosa sola) | tre chiavi esterne facoltative e un CHECK che ne impone esattamente una | `richieste_revisione` (`chk_un_solo_oggetto`) |")
    w("| Attributo multivalore (categorie di una segnalazione) | tabella separata | `classificazioni` |")
    w("| Generalizzazione di ruoli (utente, moderatore, amministratore) | una sola tabella con attributo `ruolo` (ENUM), perché gli attributi coincidono | `utenti.ruolo` |\n")
    w("## Normalizzazione\n")
    w("Lo schema è in **terza forma normale** (3FN; per le tabelle con una sola chiave candidata coincide con la forma di Boyce-Codd).\n")
    w("- **1FN**: tutti gli attributi sono atomici. Le categorie di una segnalazione e i consensi dell'utente, che sarebbero attributi multivalore, stanno in tabelle proprie (`classificazioni`, `consensi`). Le due colonne `JSON` (`quartieri.confine`, `log_attivita.dati_*`) contengono un documento opaco che l'applicazione non interroga per campi: sono dati strutturati e non attributi multivalore del dominio.")
    w("- **2FN**: nelle tabelle con chiave composta (`sostegni`, `classificazioni`, `consensi`, `preferenze_notifica`, `transizioni_ammesse`) ogni attributo non chiave dipende dall'intera chiave (es. `classificazioni.origine` e `.confidenza` descrivono la coppia segnalazione-categoria, non una delle due).")
    w("- **3FN**: nessun attributo non chiave dipende da un altro attributo non chiave. Il quartiere e lo stato non si ripetono come testo: sono chiavi esterne verso `quartieri` e `stati`. Il nome del candidato non si ripete in `invii`.")
    w("\n**Scelte consapevoli (non sono violazioni):**\n")
    w("- `utenti.stato_account` e `utenti.eliminato_il`, `segnalazioni.nascosta` e `motivo_nascosta`: l'eliminazione e il nascondimento sono *logici*, per non perdere la storia; i CHECK (`chk_eliminato`, `chk_nascosta_con_motivo`) tengono coerenti flag e data/motivo.")
    w("- `verifiche_identita.esito_ia` è derivato dal `punteggio` (soglie 85 e 50): è memorizzato perché la soglia può cambiare nel tempo e l'esito storico non deve cambiare; il CHECK `chk_esito_da_punteggio` impedisce incoerenze.")
    w("- `media.copertina` e la colonna generata `copertina_di` servono a imporre con un UNIQUE «una sola copertina per segnalazione» (MySQL non ha indici parziali).")
    w("- Le viste (`v_classifica_segnalazioni`, `v_statistiche_utenti`, `v_classifica_utenti_pubblica`) calcolano i conteggi al momento della lettura: nessun contatore ridondante è salvato nelle tabelle.\n")
    w("## Vincoli e regole\n")
    w("### Nel database\n")
    w("- **Chiavi primarie, chiavi esterne, UNIQUE**: vedi il dizionario. Un account per persona: `utenti.codice_fiscale_hash` UNIQUE; un sostegno per coppia: PK composta.")
    w("- **CHECK** (MySQL 8.0.16+): formato dell'email, intervalli (punteggi 0-100 e 0-1, tentativi 1-3, municipio 1-9, riquadro geografico di Milano), coerenza tra metodo di accesso e password/codice fiscale, coerenza tra flag e date.")
    w("- **Trigger**: " + "; ".join(f"`{n}` ({q.lower()} {e.lower()} su `{tb}`)" for n, q, e, tb in trigger_e_viste()[0]) + ".")
    w("  - età minima di 14 anni (un CHECK non può usare la data corrente);")
    w("  - transizioni di stato ammesse solo se presenti in `transizioni_ammesse` e aggiornamento dello stato della segnalazione;")
    w("  - un utente non può sostenere la propria segnalazione né una non pubblica; un commento deve rispettare la stessa segnalazione del padre;")
    w("  - `log_attivita` è di sola aggiunta (blocca UPDATE e DELETE).")
    w("- **Viste**: " + ", ".join(f"`{v}`" for v in trigger_e_viste()[1]) + ".\n")
    w("### Nell'applicazione (non esprimibili nel database)\n")
    w("- Almeno un media per segnalazione (si inseriscono nella stessa transazione) e al massimo 10.")
    w("- Al massimo 5 segnalazioni al giorno per utente.")
    w("- Confine esatto di Milano: il database ha solo un riquadro; il controllo del punto nel poligono usa il GeoJSON di `quartieri.confine`.")
    w("- Permessi per ruolo (chi può cambiare stato, nascondere, sospendere, cambiare ruoli); pubblicare segnalazioni richiede l'identità verificata (SPID/CIE o documento approvato).")
    w("- La logica «puoi riprovare» della verifica del documento (il limite di 3 tentativi è invece nel database).\n")
    w("## Convenzioni dello schema fisico\n")
    w("MySQL 8, motore InnoDB, set di caratteri `utf8mb4`; tutti i `DATETIME(3)` sono in UTC. Chiavi primarie intere auto-incrementali (`SMALLINT` per tabelle piccole, `BIGINT` per `notifiche` e `log_attivita`). Le colonne `ENUM` sono dichiarate nella tabella.\n")
    return "\n".join(L)


# ---------------------------------------------------------------- diagramma
LARG = 250
RIGA = 20
INTESTAZIONE = 30
PASSO = 340            # distanza tra le colonne
MARGINE_SU = 90        # canale superiore per i collegamenti lunghi
COLONNE = [
    ["quartieri", "documenti_normativi", "consensi", "sospensioni", "verifiche_identita"],
    ["utenti", "notifiche", "preferenze_notifica", "log_attivita"],
    ["sostegni", "commenti", "richieste_revisione", "cambi_stato", "invii", "candidati"],
    ["segnalazioni", "media", "classificazioni"],
    ["stati", "transizioni_ammesse", "categorie"],
]
ALTEZZA_MINIMA = {"utenti": 150, "segnalazioni": 150, "stati": 90}
COL_DI = {n: i for i, ts in enumerate(COLONNE) for n in ts}
COLORI = ["#e30613", "#009a44", "#ffc400", "#0a5eb0"]
COLORI_DOMINIO = {n: COLORI[i] for i, (d, tabs) in enumerate(DOMINI) for n in tabs}


def colonne_chiave(info):
    fk = {f["col"] for f in info["fk"]}
    ch = [c for c in info["colonne"] if c["nome"] in info["pk"] or c["nome"] in fk]
    return ch, len(info["colonne"]) - len(ch), fk


def altezza(n, info):
    ch, altre, _ = colonne_chiave(info)
    return max(INTESTAZIONE + RIGA * (len(ch) + (1 if altre else 0)) + 10, ALTEZZA_MINIMA.get(n, 0))


def svg(t):
    box = {}
    for ci, tabs in enumerate(COLONNE):
        y = MARGINE_SU
        for n in tabs:
            h = altezza(n, t[n]); box[n] = (40 + ci * PASSO, y, LARG, h); y += h + 44
    W = 40 + (len(COLONNE) - 1) * PASSO + LARG + 60
    H = max(y + h for (x, y, w, h) in box.values()) + 90
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         '<defs><marker id="fr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#101010"/></marker></defs>']
    # legenda
    ly = H - 56
    for i, (d, _) in enumerate(DOMINI):
        lx = 40 + i * 300
        o.append(f'<rect x="{lx}" y="{ly}" width="16" height="16" fill="{COLORI[i]}" stroke="#101010" stroke-width="1.5"/><text x="{lx + 24}" y="{ly + 13}" font-size="14" fill="#101010">{html.escape(d)}</text>')
    o.append(f'<text x="40" y="{H - 16}" font-size="12.5" fill="#444">PK = chiave primaria · FK = chiave esterna. La freccia punta alla tabella riferita (lato «1»). Sono mostrate solo le colonne chiave: gli altri attributi sono nel dizionario.</text>')
    # collegamenti a squadra, che corrono solo nei corridoi tra le colonne e nel canale in alto
    uso_corr, uso_lati, n_alto = {}, {}, [0]
    def corridoio(ci, lato):   # x del corridoio a sinistra (-1) o a destra (+1) della colonna ci
        base = 40 + ci * PASSO
        return (base - (PASSO - LARG) / 2) if lato < 0 else (base + LARG + (PASSO - LARG) / 2)
    def sposta(chiave):
        k = uso_corr.get(chiave, 0); uso_corr[chiave] = k + 1
        return ((k % 9) - 4) * 6
    def ingresso(n, lato, h):
        k = uso_lati.get((n, lato), 0); uso_lati[(n, lato)] = k + 1
        return box[n][1] + INTESTAZIONE + 8 + (k * 8) % max(8, h - INTESTAZIONE - 14)
    for n, info in t.items():
        ch, altre, fk = colonne_chiave(info)
        for f in info["fk"]:
            r = f["rif"]
            x1, y1, w1, h1 = box[n]; x2, y2, w2, h2 = box[r]
            cc, pc = COL_DI[n], COL_DI[r]
            ya = y1 + INTESTAZIONE + RIGA * [c["nome"] for c in ch].index(f["col"]) + RIGA / 2
            if cc == pc:
                lato = 1
                xa, xb = x1 + w1, x2 + w2
                xg = corridoio(cc, 1) + sposta((cc, 1)) + 16
                yb = ingresso(r, lato, h2)
                pts = [(xa, ya), (xg, ya), (xg, yb), (xb, yb)]
            elif abs(cc - pc) == 1:
                dx = 1 if pc > cc else -1
                xa = x1 + w1 if dx > 0 else x1
                xb = x2 if dx > 0 else x2 + w2
                xg = (xa + xb) / 2 + sposta((min(cc, pc), "centro"))
                yb = ingresso(r, -dx, h2)
                pts = [(xa, ya), (xg, ya), (xg, yb), (xb, yb)]
            else:               # collegamento lungo: sale nel corridoio, corre nel canale in alto, scende fino alla tabella riferita
                dx = 1 if pc > cc else -1
                xa = x1 + w1 if dx > 0 else x1
                xb = x2 if dx > 0 else x2 + w2
                x_su = corridoio(cc, dx) + sposta((cc, dx))
                x_giu = corridoio(pc, -dx) + sposta((pc, -dx))
                n_alto[0] += 1
                y_alto = 20 + (n_alto[0] % 9) * 7
                yb = ingresso(r, -dx, h2)
                pts = [(xa, ya), (x_su, ya), (x_su, y_alto), (x_giu, y_alto), (x_giu, yb), (xb, yb)]
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            o.append(f'<path d="{d}" fill="none" stroke="#101010" stroke-opacity=".6" stroke-width="1.5" stroke-linejoin="round" marker-end="url(#fr)"/>')
            o.append(f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="3.2" fill="#101010"/>')
    for n, (x, y, w, h) in box.items():
        info = t[n]; ch, altre, fk = colonne_chiave(info)
        col = COLORI_DOMINIO[n]
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" stroke="#101010" stroke-width="2"/>')
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{INTESTAZIONE}" fill="#101010"/><rect x="{x}" y="{y + INTESTAZIONE - 5}" width="{w}" height="5" fill="{col}"/>')
        o.append(f'<text x="{x + 10}" y="{y + 20}" font-size="15" font-weight="700" fill="#ffffff">{html.escape(n)}</text>')
        for i, c in enumerate(ch):
            yy = y + INTESTAZIONE + RIGA * i + 15
            e_pk, e_fk = c["nome"] in info["pk"], c["nome"] in fk
            tag = ("PK " if e_pk else "") + ("FK" if e_fk else "")
            deco = ' text-decoration="underline"' if e_pk else ""
            o.append(f'<text x="{x + 10}" y="{yy}" font-size="13" font-weight="{700 if e_pk else 400}" fill="#101010"{deco}>{html.escape(c["nome"])}</text>')
            o.append(f'<text x="{x + w - 10}" y="{yy}" font-size="11" font-weight="700" text-anchor="end" fill="#555">{tag.strip()}</text>')
        if altre:
            yy = y + INTESTAZIONE + RIGA * len(ch) + 15
            o.append(f'<text x="{x + 10}" y="{yy}" font-size="12" fill="#666" font-style="italic">+ {altre} altri attributi</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    t = leggi_tabelle()
    mancanti = [n for _, ts in DOMINI for n in ts if n not in t]
    extra = [n for n in t if n not in COLORI_DOMINIO]
    if mancanti or extra: sys.exit(f"tabelle non allineate: mancanti {mancanti}, non classificate {extra}")
    docs = RADICE / "docs"
    (docs / "modello_logico.md").write_text(markdown(t), encoding="utf-8")
    (docs / "modello_logico.svg").write_text(svg(t), encoding="utf-8")
    try:
        import cairosvg
        cairosvg.svg2png(url=str(docs / "modello_logico.svg"), write_to=str(docs / "modello_logico.png"), output_width=1900)
    except Exception as e:  # noqa: BLE001
        print("PNG non generato:", e)
    print(len(t), "tabelle,", sum(len(v["fk"]) for v in t.values()), "chiavi esterne")


main()
