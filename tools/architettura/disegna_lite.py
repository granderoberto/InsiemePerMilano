"""Versione «lite» dell'architettura, a icone (docs/architettura_lite.svg e .png).
Uso: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib tools/.venv/bin/python tools/architettura/disegna_lite.py"""
import html, pathlib

RADICE = pathlib.Path(__file__).resolve().parents[2]
W, H = 1400, 860
INK, ROSSO, VERDE, GIALLO, BLU, VIOLA = "#101010", "#e30613", "#009a44", "#ffc400", "#0a5eb0", "#8e4ea0"
o = []


def t(x, y, s, size=16, peso=400, colore=INK, ancora="middle"):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" fill="{colore}" text-anchor="{ancora}">{html.escape(s)}</text>')


# icone disegnate in un riquadro 100x100 centrato in (0,0): tratto nero spesso
def icona(nome):
    s = 'fill="none" stroke="#101010" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
    if nome == "persone":
        return (f'<g {s}><circle cx="-14" cy="-16" r="13" fill="#fff"/><path d="M-38 30 C-38 8 -26 0 -14 0 C-2 0 10 8 10 30 Z" fill="#fff"/>'
                f'<circle cx="20" cy="-8" r="11" fill="#fff"/><path d="M12 30 C12 14 20 8 28 8 C38 8 44 16 44 30 Z" fill="#fff"/></g>')
    if nome == "sito":
        return (f'<g {s}><rect x="-44" y="-34" width="88" height="68" rx="3" fill="#fff"/><line x1="-44" y1="-18" x2="44" y2="-18"/>'
                f'<circle cx="-34" cy="-26" r="2" fill="#101010"/><circle cx="-26" cy="-26" r="2" fill="#101010"/><circle cx="-18" cy="-26" r="2" fill="#101010"/>'
                f'<line x1="-32" y1="-4" x2="14" y2="-4"/><line x1="-32" y1="8" x2="32" y2="8"/><line x1="-32" y1="20" x2="2" y2="20"/></g>')
    if nome == "database":
        return (f'<g {s}><path d="M-36 -26 L-36 26 C-36 40 36 40 36 26 L36 -26" fill="#fff"/><ellipse cx="0" cy="-26" rx="36" ry="13" fill="#fff"/>'
                f'<path d="M-36 -2 C-36 12 36 12 36 -2"/><path d="M-36 14 C-36 28 36 28 36 14" stroke-width="0"/></g>')
    if nome == "email":
        return (f'<g {s}><rect x="-42" y="-28" width="84" height="56" rx="3" fill="#fff"/><path d="M-42 -26 L0 6 L42 -26"/></g>')
    if nome == "mappa":
        return (f'<g {s}><path d="M-40 -22 L-14 -32 L14 -22 L40 -32 L40 30 L14 40 L-14 30 L-40 40 Z" fill="#fff"/><line x1="-14" y1="-32" x2="-14" y2="30"/><line x1="14" y1="-22" x2="14" y2="40"/>'
                f'<path d="M0 -4 C-14 -22 -4 -40 0 -40 C4 -40 14 -22 0 -4 Z" fill="#e30613"/><circle cx="0" cy="-26" r="4" fill="#fff" stroke-width="3"/></g>')
    if nome == "identita":
        return (f'<g {s}><rect x="-44" y="-30" width="88" height="60" rx="4" fill="#fff"/><circle cx="-20" cy="-6" r="9"/><path d="M-34 22 C-34 10 -26 6 -20 6 C-14 6 -6 10 -6 22"/>'
                f'<line x1="8" y1="-12" x2="34" y2="-12"/><line x1="8" y1="0" x2="34" y2="0"/><line x1="8" y1="12" x2="24" y2="12"/></g>')
    if nome == "ia":
        pin = "".join(f'<line x1="{x}" y1="-40" x2="{x}" y2="-30"/><line x1="{x}" y1="30" x2="{x}" y2="40"/><line x1="-40" y1="{x}" x2="-30" y2="{x}"/><line x1="30" y1="{x}" x2="40" y2="{x}"/>' for x in (-14, 0, 14))
        return f'<g {s}><rect x="-30" y="-30" width="60" height="60" rx="5" fill="#fff"/>{pin}<text x="0" y="9" font-size="26" font-weight="800" text-anchor="middle" fill="#101010" stroke="none" font-family="Helvetica, Arial, sans-serif">IA</text></g>'
    if nome == "git":
        return (f'<g {s}><line x1="-22" y1="-26" x2="-22" y2="26"/><path d="M-22 6 C-22 -10 22 0 22 -22"/><circle cx="-22" cy="-30" r="9" fill="#fff"/>'
                f'<circle cx="-22" cy="30" r="9" fill="#fff"/><circle cx="22" cy="-26" r="9" fill="#fff"/></g>')
    return ""


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
nodo(700, 330, "sito", "Il sito web", ["Django su Render"], VERDE)
nodo(1200, 330, "database", "Il database", ["MySQL su Aiven"], GIALLO)
freccia([(284, 330), (616, 330)], "HTTPS", 450, 310)
freccia([(784, 330), (1116, 330)], "dati", 950, 310, doppia=True)
# GitHub sopra il sito
nodo(700, 128, "git", "", [], VIOLA, r=48)
t(770, 122, "GitHub", 22, 800, INK, "start")
t(770, 146, "il codice e i documenti", 14, 400, "#444", "start")
freccia([(700, 182), (700, 244)], "deploy", 748, 214)
# satelliti
nodo(200, 690, "mappa", "Mappe", ["OpenStreetMap"], BLU, r=64)
nodo(560, 690, "email", "Email", ["Gmail"], GIALLO, r=64)
nodo(840, 690, "identita", "SPID / CIE", ["ambiente di prova"], VIOLA, tratteggio=True, r=64)
nodo(1120, 690, "ia", "Intelligenza", ["artificiale simulata"], VERDE, tratteggio=True, r=64)
freccia([(200, 520), (200, 622)], "mappe e indirizzi", 200, 572)
# dal sito: una linea comune che si divide verso email, SPID/CIE e IA
o.append(f'<path d="M700 520 L700 548 M560 548 L1120 548" fill="none" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
freccia([(560, 548), (560, 622)], "email", 560, 590)
freccia([(840, 548), (840, 622)], "accesso", 840, 590, tratteggio=True)
freccia([(1120, 548), (1120, 622)], "controlli", 1120, 590, tratteggio=True)
# legenda
o.append(f'<line x1="50" y1="826" x2="110" y2="826" stroke="{INK}" stroke-width="5"/>')
t(122, 831, "in uso", 15, 400, INK, "start")
o.append(f'<line x1="230" y1="826" x2="290" y2="826" stroke="{INK}" stroke-width="5" stroke-dasharray="10 7"/>')
t(302, 831, "simulato o di prova", 15, 400, INK, "start")
o.append("</svg>")
svg = "\n".join(o)
(RADICE / "docs" / "architettura_lite.svg").write_text(svg, encoding="utf-8")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(RADICE / "docs" / "architettura_lite.png"), output_width=1600)
except Exception as e:  # noqa: BLE001
    print("PNG non generato:", e)
print("ok")
