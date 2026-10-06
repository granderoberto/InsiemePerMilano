#!/usr/bin/env python3
"""Genera lo schema a blocchi dell'integrazione IA (materiale 3): docs/architettura_ia.{svg,png}.

Uso: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib tools/.venv/bin/python tools/ia/schema_blocchi.py
(su macOS serve la libreria Cairo di Homebrew: brew install cairo)
"""
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parents[2]
W, H = 1600, 1060
out = []

COL = {"web": "#dbeafe", "gw": "#fde68a", "ia": "#dcfce7", "prov": "#f3e8ff", "dati": "#e5e7eb", "umano": "#fee2e2", "utente": "#ffffff"}
BORDO = "#334155"


def testo(x, y, s, size=15, peso="400", ancora="start", colore="#0f172a"):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" text-anchor="{ancora}" fill="{colore}">{escape(s)}</text>')


def box(x, y, w, h, titolo, righe=(), tipo="web", num=None):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{COL[tipo]}" stroke="{BORDO}" stroke-width="1.6"/>')
    ty = y + 28
    if num:
        out.append(f'<circle cx="{x + 24}" cy="{y + 24}" r="14" fill="#166534"/>')
        testo(x + 24, y + 29, str(num), 15, "700", "middle", "#ffffff")
        testo(x + 46, ty, titolo, 16, "700")
    else:
        testo(x + 16, ty, titolo, 16, "700")
    for i, r in enumerate(righe):
        testo(x + 16, ty + 24 + 20 * i, r, 13.5, "400", colore="#1e293b")


def freccia(x1, y1, x2, y2, etichetta="", colore="#0f172a", tratteggio=False, dx=0, dy=-8):
    d = ' stroke-dasharray="7 5"' if tratteggio else ""
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colore}" stroke-width="2"{d} marker-end="url(#p)"/>')
    if etichetta:
        cx, cy = (x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy
        e = escape(etichetta)
        out.append(f'<text x="{cx}" y="{cy}" font-size="12.5" font-weight="700" text-anchor="middle" fill="#ffffff" stroke="#ffffff" stroke-width="6">{e}</text>')
        out.append(f'<text x="{cx}" y="{cy}" font-size="12.5" font-weight="700" text-anchor="middle" fill="{colore}">{e}</text>')


# ---------------------------------------------------------------- disegno
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">')
out.append('<defs><marker id="p" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
           '<path d="M0 0 L10 5 L0 10 z" fill="#0f172a"/></marker></defs>')
out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
testo(40, 46, "La Nostra Città, Il Nostro Futuro: integrazione dell'intelligenza artificiale", 25, "700")
testo(40, 72, "Schema a blocchi: l'IA propone, un essere umano decide. Ogni esito è registrato e può essere rivisto da un moderatore.", 15, colore="#475569")

# colonna 1: persone
box(40, 120, 250, 150, "Cittadino", ["Browser o smartphone", "Registra l'account, invia", "segnalazioni e commenti"], "utente")
box(40, 330, 250, 150, "Moderatore", ["Vede le code con motivo e", "punteggio; conferma o", "ribalta ogni decisione IA"], "umano")
box(40, 540, 250, 110, "Amministratore", ["Registro delle attività,", "statistiche, soglie"], "umano")

# colonna 2: web app
box(370, 120, 330, 530, "Web app (Django)", [], "web")
for i, (t, r) in enumerate([("Registrazione e accesso", "SPID/CIE oppure credenziali + documento"),
                            ("Nuova segnalazione", "testo, categorie, posizione, media"),
                            ("Commenti", "testo, risposte"),
                            ("Code del moderatore", "verifiche · contenuti · in attesa"),
                            ("Ciclo di vita", "stati da 1 a 5 imposti dal database")]):
    y = 175 + i * 94
    out.append(f'<rect x="388" y="{y}" width="294" height="78" rx="9" fill="#ffffff" stroke="{BORDO}" stroke-width="1.2"/>')
    testo(402, y + 28, t, 15, "700")
    testo(402, y + 52, r, 13, colore="#334155")

# colonna 3: gateway
box(790, 120, 340, 530, "Gateway IA (servizio interno)", [], "gw")
for i, (t, r) in enumerate([("Interfaccia unica", "un contratto per tutti i moduli"),
                            ("Coda dei compiti", "video e OCR in background"),
                            ("Regola della decisione", "vale l'esito peggiore"),
                            ("Sicurezza dei guasti", "se un modulo non risponde: «dubbio»"),
                            ("Registro decisioni", "punteggio, modello, data in log_attivita")]):
    y = 175 + i * 94
    out.append(f'<rect x="808" y="{y}" width="304" height="78" rx="9" fill="#ffffff" stroke="{BORDO}" stroke-width="1.2"/>')
    testo(822, y + 28, t, 15, "700")
    testo(822, y + 52, r, 13, colore="#334155")

# colonna 4: moduli IA
box(1210, 120, 350, 530, "Moduli di IA", [], "ia")
moduli = [("Verifica del documento", "OCR · corrispondenza dati · validità ·", "autenticità · confronto volto/selfie"),
          ("Classificazione categorie", "propone categorie con confidenza", ""),
          ("Moderazione del testo", "insulti · odio · minacce ·", "dati personali di terzi"),
          ("Moderazione di immagini/video", "contenuti sessuali o violenti; il testo letto", "con OCR passa al filtro; video a fotogrammi"),
          ("Coerenza immagine/testo", "la foto è pertinente alla descrizione?", "")]
for i, (t, a, b) in enumerate(moduli):
    y = 175 + i * 94
    out.append(f'<rect x="1228" y="{y}" width="314" height="78" rx="9" fill="#ffffff" stroke="#166534" stroke-width="1.4"/>')
    out.append(f'<circle cx="1250" cy="{y + 24}" r="12" fill="#166534"/>')
    testo(1250, y + 29, str(i + 1), 13, "700", "middle", "#ffffff")
    testo(1270, y + 29, t, 14.5, "700")
    testo(1242, y + 50, a, 12.5, colore="#334155")
    if b:
        testo(1242, y + 67, b, 12.5, colore="#334155")

# fornitori e dati
box(1210, 720, 350, 150, "Modelli e servizi (da scegliere)", ["Modelli di linguaggio e visione (API)", "OCR · riconoscimento del volto", "Si valutano: costo, DPA, dati in UE,", "nessun addestramento sui nostri dati"], "prov")
box(370, 720, 760, 150, "Dati", [], "dati")
testo(386, 776, "Database MySQL", 15, "700")
testo(386, 798, "utenti · verifiche_identita · segnalazioni · media · classificazioni", 13, colore="#334155")
testo(386, 816, "commenti · richieste_revisione · notifiche · log_attivita (solo aggiunte)", 13, colore="#334155")
testo(790, 776, "File multimediali", 15, "700")
testo(790, 798, "foto e video pubblicati senza metadati (EXIF)", 13, colore="#334155")
testo(790, 816, "documento e selfie: cancellati dopo la verifica", 13, colore="#334155")

# frecce
freccia(290, 195, 370, 195, "1", dy=-8)
freccia(370, 405, 290, 405, "6", dy=-8)
freccia(700, 250, 790, 250, "2  richiesta", dx=0)
freccia(790, 300, 700, 300, "3  esito", dx=0, dy=18)
freccia(1130, 220, 1210, 220, "4  compiti")
freccia(1210, 330, 1130, 330, "5  punteggi", dy=18)
freccia(1385, 650, 1385, 720, "chiamate protette", tratteggio=True, dx=-78, dy=4)
freccia(920, 650, 920, 720, "7  scrive esiti e log", dx=-90, dy=4)
freccia(540, 650, 540, 720, "legge e scrive", dx=-62, dy=4)
testo(40, 940, "Legenda", 15, "700")
testo(40, 964, "1 il cittadino invia il contenuto · 2 la web app chiede il controllo al gateway · 3 torna l'esito (ok, dubbio, bloccato) · 4 il gateway lancia i moduli necessari", 13.5, colore="#334155")
testo(40, 984, "5 i moduli rispondono con punteggi · 6 il moderatore vede le code e conferma o ribalta · 7 esiti e decisioni IA finiscono nel database e nel registro delle attività", 13.5, colore="#334155")
testo(40, 1010, "Esito = il peggiore tra i controlli. ok: procede. dubbio: resta In attesa e va in coda al moderatore. bloccato: non si pubblica, l'autore è avvisato e può chiedere la revisione.", 13.5, colore="#334155")
out.append("</svg>")

svg = "\n".join(out)
(ROOT / "docs" / "architettura_ia.svg").write_text(svg, encoding="utf-8")
cairosvg.svg2png(bytestring=svg.encode(), write_to=str(ROOT / "docs" / "architettura_ia.png"), output_width=1600)
print("scritti docs/architettura_ia.svg e .png")
