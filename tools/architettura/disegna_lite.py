"""Versione «lite» dell'architettura, a icone (docs/architettura_lite.svg).
Uso: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib tools/.venv/bin/python tools/architettura/disegna_lite.py"""
import html, pathlib

RADICE = pathlib.Path(__file__).resolve().parents[2]
W, H = 1400, 910
INK, ROSSO, VERDE, GIALLO, BLU, VIOLA = "#101010", "#e30613", "#009a44", "#ffc400", "#0a5eb0", "#8e4ea0"
o = []


def t(x, y, s, size=16, peso=400, colore=INK, ancora="middle"):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" fill="{colore}" text-anchor="{ancora}">{html.escape(s)}</text>')


import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from icone import icona  # noqa: E402


def nodo(x, y, nome, titolo, didascalia, colore, tratteggio=False, r=78):
    dash = ' stroke-dasharray="10 7"' if tratteggio else ""
    o.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{colore}" stroke="{INK}" stroke-width="5"{dash}/>')
    o.append(f'<circle cx="{x}" cy="{y}" r="{r - 12}" fill="#ffffff" stroke="{INK}" stroke-width="3"/>')
    o.append(f'<g transform="translate({x},{y}) scale({r / 78:.3f})">{icona(nome)}</g>')
    t(x, y + r + 30, titolo, 22, 800)
    for i, riga in enumerate(didascalia): t(x, y + r + 52 + i * 19, riga, 14, 400, "#444")


def freccia(punti, etichetta=None, ex=None, ey=None, doppia=False, tratteggio=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in punti)
    dash = ' stroke-dasharray="10 7"' if tratteggio else ""
    inizio = ' marker-start="url(#fr)"' if doppia else ""
    o.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="5" stroke-linejoin="round"{dash}{inizio} marker-end="url(#fr)"/>')
    if etichetta:
        x = ex if ex is not None else (punti[0][0] + punti[-1][0]) / 2
        y = ey if ey is not None else (punti[0][1] + punti[-1][1]) / 2
        larg = 9.2 * len(etichetta)
        o.append(f'<rect x="{x - larg / 2 - 6}" y="{y - 17}" width="{larg + 12}" height="26" fill="#ffffff"/>')
        t(x, y + 3, etichetta, 15, 800)


o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">')
o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/><rect width="{W}" height="8" fill="{ROSSO}"/>')
o.append(f'<defs><marker id="fr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>')
t(50, 56, "Come funziona La Nostra Città", 32, 800, INK, "start")
t(50, 84, "L'architettura in breve", 17, 400, "#444", "start")
# linea di marca in alto a destra
o.append(f'<line x1="1100" y1="50" x2="1340" y2="50" stroke="{INK}" stroke-width="4"/>')
for i, c in enumerate([ROSSO, VERDE, GIALLO, BLU, VIOLA]): o.append(f'<circle cx="{1100 + i * 60}" cy="50" r="12" fill="{c}" stroke="{INK}" stroke-width="3.5"/>')

# riga principale
nodo(200, 330, "persone", "Persone", ["cittadini, moderatori,", "amministratore"], ROSSO)
nodo(700, 330, "sito", "Il sito web", ["Django su Render", "con mappe e moduli"], VERDE)
nodo(1200, 330, "database", "Il database", ["MySQL su Aiven"], GIALLO)
freccia([(284, 330), (616, 330)], "HTTPS", 450, 310)
freccia([(784, 330), (1116, 330)], "dati", 950, 310, doppia=True)
# GitHub sopra il sito
nodo(700, 128, "git", "", [], VIOLA, r=48)
t(770, 122, "GitHub", 22, 800, INK, "start")
t(770, 146, "il codice e i documenti", 14, 400, "#444", "start")
freccia([(700, 182), (700, 244)], "deploy", 748, 214)
# satelliti
nodo(200, 690, "mappa", "OpenStreetMap", ["sfondo delle mappe", "e ricerca indirizzi"], BLU, r=64)
nodo(560, 690, "email", "Email", ["Gmail"], GIALLO, r=64)
nodo(840, 690, "identita", "SPID / CIE", ["ambiente di prova"], VIOLA, tratteggio=True, r=64)
nodo(1120, 690, "ia", "Intelligenza", ["artificiale simulata"], VERDE, tratteggio=True, r=64)
freccia([(200, 540), (200, 622)], "dal browser", 200, 586)
# dal sito: una linea comune che si divide verso email, SPID/CIE e IA
o.append(f'<path d="M700 520 L700 548 M560 548 L1120 548" fill="none" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
freccia([(560, 548), (560, 622)], "email", 560, 590)
freccia([(840, 548), (840, 622)], "accesso", 840, 590, tratteggio=True)
freccia([(1120, 548), (1120, 622)], "controlli", 1120, 590, tratteggio=True)
# legenda
o.append(f'<line x1="50" y1="876" x2="110" y2="876" stroke="{INK}" stroke-width="5"/>')
t(122, 881, "in uso", 15, 400, INK, "start")
o.append(f'<line x1="230" y1="876" x2="290" y2="876" stroke="{INK}" stroke-width="5" stroke-dasharray="10 7"/>')
t(302, 881, "simulato o di prova", 15, 400, INK, "start")
o.append("</svg>")
svg = "\n".join(o)
(RADICE / "docs" / "architettura_lite.svg").write_text(svg, encoding="utf-8")
print("ok")
