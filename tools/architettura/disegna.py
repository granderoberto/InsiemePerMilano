"""Disegna l'architettura del sistema (docs/architettura_sistema.svg e .png). Uso: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib tools/.venv/bin/python tools/architettura/disegna.py"""
import html, pathlib

RADICE = pathlib.Path(__file__).resolve().parents[2]
W, H = 1780, 1230
INK, ROSSO, VERDE, GIALLO, BLU, VIOLA = "#101010", "#e30613", "#009a44", "#ffc400", "#0a5eb0", "#8e4ea0"
o = []


def t(x, y, s, size=13, peso=400, colore=INK, ancora="start", corsivo=False):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" fill="{colore}" text-anchor="{ancora}"{" font-style=\"italic\"" if corsivo else ""}>{html.escape(s)}</text>')


def box(x, y, w, h, titolo, righe=(), banda=INK, tratteggio=False, fondo="#ffffff", testo_titolo="#ffffff", piccolo=False):
    dash = ' stroke-dasharray="8 5"' if tratteggio else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fondo}" stroke="{INK}" stroke-width="2"{dash}/>')
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="28" fill="{INK}"/><rect x="{x}" y="{y + 23}" width="{w}" height="5" fill="{banda}"/>')
    t(x + 10, y + 19, titolo, 14, 700, testo_titolo)
    for i, r in enumerate(righe):
        t(x + 10, y + 50 + i * (16 if piccolo else 18), r, 12 if piccolo else 13, 400, INK)


def freccia(punti, etichetta=None, posx=None, posy=None, doppia=False, tratteggio=False, colore=INK):
    d = "M" + " L".join(f"{x},{y}" for x, y in punti)
    dash = ' stroke-dasharray="7 5"' if tratteggio else ""
    inizio = ' marker-start="url(#fr)"' if doppia else ""
    o.append(f'<path d="{d}" fill="none" stroke="{colore}" stroke-width="2.2" stroke-linejoin="round"{dash}{inizio} marker-end="url(#fr)"/>')
    if etichetta:
        x, y = posx if posx is not None else (punti[0][0] + punti[-1][0]) / 2, posy if posy is not None else (punti[0][1] + punti[-1][1]) / 2 - 8
        larg = 7.0 * len(etichetta)
        o.append(f'<rect x="{x - larg / 2 - 4}" y="{y - 13}" width="{larg + 8}" height="19" fill="#ffffff"/>')
        t(x, y + 1, etichetta, 12, 700, INK, "middle")


o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">')
o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
o.append(f'<defs><marker id="fr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>')
# testata
o.append(f'<rect x="0" y="0" width="{W}" height="8" fill="{ROSSO}"/>')
t(40, 46, "Architettura di «La Nostra Città, Il Nostro Futuro»", 26, 800)
t(40, 68, "Piattaforma civica per il comitato «Insieme per Milano» · stato a ottobre 2026 · tratto pieno = in uso, tratteggiato = simulato, di prova o esterno", 13, 400, "#444")
for i, c in enumerate([ROSSO, VERDE, GIALLO, BLU, VIOLA]):
    o.append(f'<circle cx="{W - 220 + i * 40}" cy="40" r="9" fill="{c}" stroke="{INK}" stroke-width="2.5"/>')
o.append(f'<line x1="{W - 220}" y1="40" x2="{W - 60}" y2="40" stroke="{INK}" stroke-width="3" />')
for i, c in enumerate([ROSSO, VERDE, GIALLO, BLU, VIOLA]):
    o.append(f'<circle cx="{W - 220 + i * 40}" cy="40" r="9" fill="{c}" stroke="{INK}" stroke-width="2.5"/>')

# ---- attori
box(40, 110, 290, 110, "Cittadino / visitatore", ["Browser da telefono o computer", "legge, segnala, sostiene, commenta", "accesso: SPID/CIE o email + password"], ROSSO)
box(40, 250, 290, 90, "Moderatore", ["code: contenuti dubbi, verifiche,", "richieste di revisione, presentazioni"], VERDE)
box(40, 370, 290, 90, "Amministratore", ["utenti e ruoli, registro delle attività,", "statistiche, categorie, normative"], GIALLO)
box(40, 500, 290, 90, "Sviluppatore", ["VS Code · prove automatiche (smoke)", "migrazioni SQL, modello ER e logico"], BLU)
box(40, 640, 290, 100, "GitHub", ["granderoberto/InsiemePerMilano", "ramo main · documentazione e codice", "nessun segreto nel repository"], VIOLA)
freccia([(185, 590), (185, 640)], "git push", 232, 618)
freccia([(330, 165), (440, 165)], "HTTPS", 385, 154)
freccia([(330, 295), (440, 295)])
freccia([(330, 415), (440, 415)])
freccia([(330, 700), (440, 700)], "deploy automatico", 385, 689)

# ---- Render
o.append(f'<rect x="440" y="90" width="780" height="800" fill="#f2f2f0" stroke="{INK}" stroke-width="2"/>')
o.append(f'<rect x="440" y="90" width="780" height="30" fill="{INK}"/><rect x="440" y="115" width="780" height="5" fill="{ROSSO}"/>')
t(452, 111, "Render · servizio web (immagine Docker con ffmpeg · gunicorn 1 processo × 4 thread · HTTPS di Render)", 14, 700, "#ffffff")
box(460, 140, 235, 135, "portale", ["pubblico: elenco, mappa, dettaglio", "utente: registrazione, accesso, 2FA,", "profilo, verifica documento", "autore: nuova segnalazione, modifica"], ROSSO, piccolo=True)
box(712, 140, 235, 135, "moderazione", ["approva, rifiuta, presenta ai", "candidati, nascondi, decide le", "verifiche e le richieste di", "revisione"], VERDE, piccolo=True)
box(964, 140, 235, 135, "amministrazione", ["utenti, ruoli, sospensioni,", "azzeramento 2FA, registro,", "statistiche (CSV), categorie,", "testi normativi"], GIALLO, piccolo=True)
box(460, 295, 739, 225, "core · servizi condivisi (Django 5.2, template server-side)", [], BLU)
colonne = [
    ("Account", ["password (criteri) · bcrypt", "token firmati (email, reset)", "2FA TOTP (segreto cifrato)", "normative e consensi"]),
    ("Segnalazioni", ["stati e transizioni", "geo: quartiere dal punto (NIL)", "media: foto/video ridotti, senza EXIF", "segnalazioni simili in zona"]),
    ("Controlli e tracce", ["interfaccia IA unica (ia/): testo,", "categorie, coerenza, documento", "log delle attività (solo aggiunte)", "email: SMTP, limiti di invio"]),
]
for i, (tit, righe) in enumerate(colonne):
    x = 478 + i * 242
    t(x, 349, tit, 13, 800)
    for k, r in enumerate(righe): t(x, 371 + k * 19, r, 12)
box(478, 462, 703, 44, "", [], BLU, fondo="#ffffff", testo_titolo="#ffffff") if False else None
o.append(f'<rect x="478" y="460" width="703" height="48" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>')
t(490, 479, "Modelli del dominio: managed=False (lo schema viene solo dalle migrazioni SQL) · utente di accesso su `utenti` (bcrypt)", 12)
t(490, 497, "Archivio temporaneo cifrato per documento e selfie: cancellato a fine verifica · copia dei file nel database", 12)
box(460, 540, 360, 120, "Pagine e file statici", ["HTML server-side · CSS «segnaletica milanese»", "font Archivo (self-hosted) · JavaScript", "mappe (Leaflet), scelta del quartiere,", "immagini e video demo · WhiteNoise"], INK, piccolo=True)
box(838, 540, 361, 120, "Disco /data (temporaneo sul piano gratuito)", ["media/  foto e video caricati", "tmp_verifiche/  documenti, cifrati", "se manca un file: ripristino dal database", "(tabella media_contenuti)"], INK, piccolo=True, tratteggio=True)
box(460, 680, 739, 90, "Sicurezza e controllo", ["HTTPS obbligatorio · cookie protetti · CSRF · intestazioni di sicurezza · limiti di tentativi (blocco 15 min dopo 5 errori)", "controllo di stato /salute/ · variabili d'ambiente per chiavi e credenziali (mai nel codice) · migrazioni Django all'avvio"], INK, piccolo=True)
box(460, 790, 739, 80, "Cartella apps/web (stesso codice in locale)", ["In locale: `manage.py runserver` su 127.0.0.1:8000 con il database di prova la_nostra_citta_test e le email sulla console.", "In produzione: gli stessi file, con DJANGO_DEBUG=0 e il database principale."], INK, piccolo=True, tratteggio=True)

# ---- Aiven
o.append(f'<rect x="1320" y="90" width="440" height="540" fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
o.append(f'<rect x="1320" y="90" width="440" height="30" fill="{INK}"/><rect x="1320" y="115" width="440" height="5" fill="{VERDE}"/>')
t(1332, 111, "Aiven · MySQL 8.4 · defaultdb", 14, 700, "#ffffff")
gruppi = [
    (140, 100, ROSSO, "Utenti e accesso", ["utenti · verifiche_identita · sospensioni", "documenti_normativi · consensi · quartieri (88 NIL)"]),
    (255, 120, VERDE, "Segnalazioni", ["segnalazioni · media · media_contenuti", "classificazioni · categorie · stati", "transizioni_ammesse · cambi_stato"]),
    (390, 80, GIALLO, "Community", ["sostegni · commenti · candidati · invii"]),
    (485, 85, BLU, "Moderazione, notifiche e log", ["richieste_revisione · notifiche", "preferenze_notifica · log_attivita (solo aggiunte)"]),
]
for y, h, c, tit, righe in gruppi: box(1338, y, 404, h, tit, righe, c, piccolo=True)
t(1340, 603, "22 tabelle · 7 trigger (ciclo di vita, età minima, log) · 3 viste · CHECK", 12, 700)
freccia([(1220, 330), (1320, 330)], "SQL su TLS", 1270, 318, doppia=True)
t(1270, 350, "certificato CA", 11, 400, "#444", "middle")

# ---- servizi esterni a destra
box(1320, 660, 440, 90, "Fornitori di intelligenza artificiale", ["oggi simulati (core/services/ia/simulato)", "da scegliere: OCR, volto, moderazione, categorie"], VIOLA, tratteggio=True, piccolo=True)
freccia([(1220, 705), (1320, 705)], "IA_BACKEND", 1270, 693, tratteggio=True)
box(1320, 770, 440, 90, "Gmail · SMTP", ["smtp.gmail.com:587 (STARTTLS) · password per le app", "conferma dell'email, recupero password, avvisi"], GIALLO, piccolo=True)
freccia([(1220, 815), (1320, 815)], "SMTP", 1270, 803)
box(1320, 880, 440, 110, "Servizi esterni usati dal browser", ["Leaflet (libreria delle mappe, da unpkg)", "OpenStreetMap: sfondo delle mappe e ricerca indirizzi", "geolocalizzazione e fotocamera del dispositivo"], INK, tratteggio=True, piccolo=True)
freccia([(185, 220), (185, 245)], None)  # placeholder invisibile (non usato)
o.pop()

# ---- servizio SPID/CIE
box(440, 940, 780, 120, "Servizio SPID/CIE · apps/spid (Django separato, database proprio)", ["Relying Party OpenID Connect con federazione (SDK spid-cie-oidc-django, Django 5.2 con l'SDK senza dipendenze)", "ponte verso il sito: token firmato con segreto condiviso, 120 s, monouso, legato al browser che ha iniziato l'accesso", "del codice fiscale arriva al sito solo l'hash SHA-256 · oggi sull'ambiente di prova della federazione"], VIOLA, tratteggio=True, piccolo=True)
freccia([(700, 890), (700, 940)], "ponte: token firmato", 760, 918, doppia=True)
box(1320, 1010, 440, 110, "Federazione SPID/CIE", ["Trust Anchor e identity provider", "oggi: ambiente di prova (gestore di identità finto)", "uso reale: serve l'adesione di un ente"], VIOLA, tratteggio=True, piccolo=True)
freccia([(1220, 1065), (1320, 1065)], "OpenID Connect", 1270, 1053, doppia=True)

# ---- legenda e note
t(40, 1170, "Flussi principali", 14, 800)
t(40, 1192, "1. Registrazione: modulo > database > email di conferma (Gmail) > account attivo. La verifica del documento è facoltativa, necessaria per pubblicare.", 12)
t(40, 1210, "2. Segnalazione: modulo con foto/video > controlli IA (simulati) > stato «In attesa» > moderatore > pubblica > candidati. Ogni passaggio finisce nel registro.", 12)
o.append("</svg>")
(RADICE / "docs").mkdir(exist_ok=True)
svg = "\n".join(o)
(RADICE / "docs" / "architettura_sistema.svg").write_text(svg, encoding="utf-8")
try:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(RADICE / "docs" / "architettura_sistema.png"), output_width=1900)
except Exception as e:  # noqa: BLE001
    print("PNG non generato:", e)
print("ok")
