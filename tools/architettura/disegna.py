"""Disegna l'architettura del sistema (docs/architettura_sistema.svg e .png): a livelli, con frecce numerate e legenda tecnica.
Uso: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib tools/.venv/bin/python tools/architettura/disegna.py"""
import html, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from icone import icona

RADICE = pathlib.Path(__file__).resolve().parents[2]
W, H = 1860, 1370
INK, ROSSO, VERDE, GIALLO, BLU, VIOLA = "#101010", "#e30613", "#009a44", "#ffc400", "#0a5eb0", "#8e4ea0"
GRIGIO = "#f2f2f0"
o = []


def t(x, y, s, size=15, peso=400, colore=INK, ancora="start"):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" fill="{colore}" text-anchor="{ancora}">{html.escape(s)}</text>')


def distintivo(x, y, nome, r=14):
    """Icona in un cerchio bianco nell'angolo dell'intestazione."""
    o.append(f'<circle cx="{x}" cy="{y}" r="{r + 2}" fill="#ffffff" stroke="{INK}" stroke-width="2"/><g transform="translate({x},{y}) scale({r / 52:.3f})">{icona(nome)}</g>')


def box(x, y, w, h, titolo, righe=(), banda=INK, tratteggio=False, fondo="#ffffff", size=15, icon=None):
    dash = ' stroke-dasharray="9 6"' if tratteggio else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fondo}" stroke="{INK}" stroke-width="2.5"{dash}/>')
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="32" fill="{INK}"/><rect x="{x}" y="{y + 27}" width="{w}" height="5" fill="{banda}"/>')
    t(x + 12, y + 22, titolo, 17, 800, "#ffffff")
    if icon: distintivo(x + w - 26, y + 16, icon)
    for i, r in enumerate(righe):
        t(x + 12, y + 56 + i * (size + 6), r, size)


def cornice(x, y, w, h, titolo, banda, fondo=GRIGIO, icon=None):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fondo}" stroke="{INK}" stroke-width="3"/>')
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="36" fill="{INK}"/><rect x="{x}" y="{y + 31}" width="{w}" height="5" fill="{banda}"/>')
    t(x + 14, y + 25, titolo, 19, 800, "#ffffff")
    if icon: distintivo(x + w - 30, y + 18, icon, 16)


def livello(x, y, w, h, nome):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>')
    o.append(f'<rect x="{x}" y="{y}" width="26" height="{h}" fill="{INK}"/>')
    o.append(f'<text transform="translate({x + 18},{y + h / 2}) rotate(-90)" font-size="14" font-weight="800" fill="#ffffff" text-anchor="middle">{html.escape(nome)}</text>')


def freccia(punti, n, doppia=False, tratteggio=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in punti)
    dash = ' stroke-dasharray="9 6"' if tratteggio else ""
    inizio = ' marker-start="url(#fr)"' if doppia else ""
    o.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"{dash}{inizio} marker-end="url(#fr)"/>')
    # numero sul tratto più lungo
    best = max(range(len(punti) - 1), key=lambda i: abs(punti[i + 1][0] - punti[i][0]) + abs(punti[i + 1][1] - punti[i][1]))
    (x1, y1), (x2, y2) = punti[best], punti[best + 1]
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    o.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{ROSSO}" stroke="{INK}" stroke-width="2.5"/>')
    t(cx, cy + 6, str(n), 17, 800, "#ffffff", "middle")


o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">')
o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/><rect width="{W}" height="9" fill="{ROSSO}"/>')
o.append(f'<defs><marker id="fr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>')
t(40, 58, "Architettura di «La Nostra Città, Il Nostro Futuro»", 32, 800)
t(40, 88, "Piattaforma civica per il comitato «Insieme per Milano» · stato a ottobre 2026 · i numeri rimandano alla legenda in fondo", 16, 400, "#444")
o.append(f'<line x1="1540" y1="52" x2="1800" y2="52" stroke="{INK}" stroke-width="4"/>')
for i, c in enumerate([ROSSO, VERDE, GIALLO, BLU, VIOLA]): o.append(f'<circle cx="{1540 + i * 65}" cy="52" r="13" fill="{c}" stroke="{INK}" stroke-width="3.5"/>')

# ---------------- colonna sinistra: client e rilascio
t(40, 138, "CLIENT", 14, 800, "#666")
o.append(f'<rect x="40" y="150" width="290" height="170" fill="#ffffff" stroke="{INK}" stroke-width="3"/><rect x="40" y="150" width="290" height="36" fill="{INK}"/>')
for k, c in enumerate([ROSSO, GIALLO, VERDE]): o.append(f'<circle cx="{60 + k * 22}" cy="168" r="6.5" fill="{c}" stroke="#ffffff" stroke-width="1.5"/>')
t(130, 174, "Browser", 17, 800, "#ffffff")
for k, r in enumerate(["Cittadino o visitatore", "Moderatore", "Amministratore", "telefono o computer"]):
    t(94, 214 + k * 25, r, 15)
    if k < 3: o.append(f'<g transform="translate(66,{208 + k * 25}) scale(0.2)">{icona("utente")}</g>')
box(40, 370, 290, 110, "OpenStreetMap", ["sfondo delle mappe", "ricerca indirizzi (Nominatim)"], BLU, tratteggio=True, icon="mappa")
freccia([(185, 320), (185, 370)], 6)
t(40, 548, "RILASCIO", 14, 800, "#666")
box(40, 560, 290, 90, "Sviluppatore", ["VS Code · prove automatiche"], VERDE, icon="laptop")
box(40, 700, 290, 90, "GitHub", ["ramo main · codice e documenti"], VIOLA, icon="git")
freccia([(185, 650), (185, 700)], 8)
freccia([(330, 745), (400, 745)], 9)

# ---------------- Render
cornice(400, 110, 960, 880, "Render · servizio web  (Docker · gunicorn · HTTPS gestito da Render)", ROSSO, icon="server")
livello(420, 160, 920, 140, "PRESENTAZIONE")
box(460, 172, 280, 116, "Template", ["HTML lato server", "Django Templates"], ROSSO)
box(755, 172, 280, 116, "Statici", ["CSS · font Archivo", "WhiteNoise"], ROSSO)
box(1050, 172, 280, 116, "JavaScript", ["Leaflet (mappe)", "selfie, quartiere, modulo"], ROSSO)
livello(420, 316, 920, 140, "APPLICAZIONE")
box(460, 328, 280, 116, "portale", ["pubblico, utente, autore", "registrazione, accesso, 2FA"], VERDE)
box(755, 328, 280, 116, "moderazione", ["code e decisioni", "verifiche, revisioni"], VERDE)
box(1050, 328, 280, 116, "amministrazione", ["utenti e ruoli, registro", "statistiche, normative"], VERDE)
livello(420, 472, 920, 250, "SERVIZI  (core)")
box(460, 484, 280, 108, "Account e sicurezza", ["bcrypt · TOTP · token firmati", "criteri password"], GIALLO)
box(755, 484, 280, 108, "Segnalazioni", ["ciclo di vita · geo (NIL)", "segnalazioni simili"], GIALLO)
box(1050, 484, 280, 108, "File multimediali", ["Pillow · ffmpeg", "senza EXIF, copia nel DB"], GIALLO)
box(460, 604, 280, 106, "Interfaccia IA", ["testo, categorie, coerenza,", "documento (fornitore: simulato)"], GIALLO, icon="ia")
box(755, 604, 280, 106, "Email", ["API di Gmail (HTTPS)", "oppure SMTP / console"], GIALLO, icon="email")
box(1050, 604, 280, 106, "Registro attività", ["solo aggiunte", "(trigger nel database)"], GIALLO)
livello(420, 738, 920, 230, "ESECUZIONE")
box(460, 750, 280, 94, "Processo web", ["gunicorn: 1 processo × 4 thread"], BLU, size=15)
box(755, 750, 280, 94, "Immagine Docker", ["Python 3.12 · ffmpeg"], BLU, icon="container")
box(1050, 750, 280, 94, "Configurazione", ["variabili d'ambiente (.env)"], BLU)
box(460, 858, 570, 100, "Disco /data (temporaneo sul piano gratuito)", ["media/ foto e video · tmp_verifiche/ documenti cifrati", "se manca un file: ripristino dal database"], BLU, tratteggio=True, icon="disco")
box(1050, 858, 280, 100, "Controllo di stato", ["/salute/ per Render"], BLU)
freccia([(330, 235), (400, 235)], 1)

# ---------------- servizio SPID
box(400, 1050, 960, 120, "Servizio SPID/CIE · apps/spid (Django separato, database proprio)",
    ["Relying Party OpenID Connect con federazione (SDK spid-cie-oidc-django)", "oggi sull'ambiente di prova · all'utente consegna solo l'hash del codice fiscale"], VIOLA, tratteggio=True, icon="identita")
freccia([(880, 990), (880, 1050)], 5, doppia=True)

# ---------------- colonna destra: dati e servizi esterni
t(1420, 138, "DATI", 14, 800, "#666")
def cilindro(x, y, w, h, titolo, banda):
    ry = 26
    o.append(f'<path d="M{x},{y + ry} A{w / 2},{ry} 0 0 1 {x + w},{y + ry} L{x + w},{y + h - ry} A{w / 2},{ry} 0 0 1 {x},{y + h - ry} Z" fill="#ffffff" stroke="{INK}" stroke-width="3.5"/>')
    o.append(f'<ellipse cx="{x + w / 2}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" fill="{INK}" stroke="{INK}" stroke-width="3.5"/>')
    o.append(f'<path d="M{x},{y + ry + 8} A{w / 2},{ry} 0 0 0 {x + w},{y + ry + 8}" fill="none" stroke="{banda}" stroke-width="5"/>')
    t(x + w / 2, y + ry + 6, titolo, 19, 800, "#ffffff", "middle")


cilindro(1420, 150, 400, 430, "Aiven · MySQL 8.4", VERDE)
for i, (tit, c, r) in enumerate([("Utenti e accesso", ROSSO, ["utenti · verifiche · consensi", "quartieri (88 NIL)"]), ("Segnalazioni", VERDE, ["segnalazioni · media · stati", "media_contenuti (copia file)"]),
                                  ("Community", GIALLO, ["sostegni · commenti · invii"]), ("Moderazione e log", BLU, ["richieste · notifiche · log"])]):
    y = 214 + i * 84
    o.append(f'<rect x="1440" y="{y}" width="360" height="72" fill="#ffffff" stroke="{INK}" stroke-width="2"/><rect x="1440" y="{y}" width="10" height="72" fill="{c}"/>')
    t(1462, y + 24, tit, 16, 800)
    for k, rr in enumerate(r): t(1462, y + 46 + k * 18, rr, 14)
t(1620, 556, "22 tabelle · 7 trigger · 3 viste · vincoli CHECK", 14, 800, INK, "middle")
freccia([(1360, 350), (1420, 350)], 2, doppia=True)

t(1420, 598, "SERVIZI ESTERNI", 14, 800, "#666")
box(1420, 610, 400, 100, "Gmail", ["API (HTTPS, OAuth) per conferme", "e recupero password"], GIALLO, icon="email")
box(1420, 730, 400, 100, "Fornitori di IA", ["oggi simulati", "da scegliere (OCR, volto, moderazione)"], VIOLA, tratteggio=True, icon="ia")
box(1420, 850, 400, 120, "Federazione SPID/CIE", ["Trust Anchor e identity provider", "oggi: ambiente di prova"], VIOLA, tratteggio=True, icon="identita")
freccia([(1360, 660), (1420, 660)], 3)
freccia([(1360, 780), (1420, 780)], 4, tratteggio=True)
freccia([(1360, 1110), (1590, 1110), (1590, 970)], 7, doppia=True, tratteggio=True)

# ---------------- legenda
o.append(f'<rect x="40" y="1205" width="1780" height="2" fill="{INK}"/>')
t(40, 1240, "Legenda dei collegamenti", 19, 800)
voci = [("1", "Browser e sito: HTTPS (TLS), pagine HTML, JSON e file"), ("2", "Sito e database: SQL su TLS con certificato CA (mysqlclient)"),
        ("3", "Sito verso Gmail: API HTTPS con token OAuth (conferme email)"), ("4", "Sito verso il fornitore IA: interfaccia unica, oggi simulata"),
        ("5", "Sito e servizio SPID/CIE: token firmato, 120 s, monouso"), ("6", "Browser verso OpenStreetMap: tile e ricerca indirizzi"),
        ("7", "Servizio SPID/CIE e federazione: OpenID Connect"), ("8", "Sviluppatore verso GitHub: git push"),
        ("9", "GitHub verso Render: deploy automatico dal Dockerfile")]
for i, (n, testo) in enumerate(voci):
    x, y = 40 + (i // 3) * 600, 1278 + (i % 3) * 26
    o.append(f'<circle cx="{x + 12}" cy="{y - 5}" r="12" fill="{ROSSO}" stroke="{INK}" stroke-width="2"/>')
    t(x + 12, y, n, 14, 800, "#ffffff", "middle")
    t(x + 34, y, testo, 15)
o.append(f'<line x1="420" y1="1234" x2="490" y2="1234" stroke="{INK}" stroke-width="3.2"/>')
t(502, 1239, "in uso", 15)
o.append(f'<line x1="600" y1="1234" x2="670" y2="1234" stroke="{INK}" stroke-width="3.2" stroke-dasharray="9 6"/>')
t(682, 1239, "simulato o di prova", 15)
o.append("</svg>")
svg = "\n".join(o)
(RADICE / "docs" / "architettura_sistema.svg").write_text(svg, encoding="utf-8")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(RADICE / "docs" / "architettura_sistema.png"), output_width=2000)
except Exception as e:  # noqa: BLE001
    print("PNG non generato:", e)
print("ok")
