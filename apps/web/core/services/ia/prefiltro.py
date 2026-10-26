"""Prefiltro locale (senza IA): decide se un testo va al modello (docs/piano_ia_openrouter.md, §3 bis).

Solo libreria standard, nessuna richiesta di rete. Tre esiti:
  bloccato    segnale grave e certo (minaccia): il modello non serve, esito `bloccato`
  doppione    lo stesso testo già inviato dallo stesso autore: esito `dubbio`, il modello non serve
  da_inviare  segnale dubbio, oppure ci sono foto, oppure manca una categoria sicura: entra nella coda del modello
  pulito      nessun segnale: esito `ok` marcato «solo controllo locale», nessuna richiesta
Produce anche un rischio 0-100 (decide la priorità nella coda) e l'impronta del testo (SHA-256 del testo normalizzato).
Le liste di parole sono volutamente corte: il prefiltro prende i casi evidenti, il resto lo giudica il modello."""
import difflib
import hashlib
from collections import Counter
import re
import unicodedata
from dataclasses import dataclass, field

from .simulato import suggerisci_categorie as _categorie_locali

SOGLIA_CATEGORIA = 0.6   # confidenza locale oltre la quale un testo senza foto può restare «pulito»

INSULTI = ("idiota", "imbecille", "stronzo", "stronza", "merda", "cretino", "cretina", "schifoso", "bastardo", "bastarda",
           "coglione", "cogliona", "vaffanculo", "fottiti", "puttana", "troia", "deficiente", "ritardato", "rincoglionito",
           "pirla", "pirlone", "parassita", "parassiti", "buffone", "buffoni", "testa di cazzo")
OSTILI = ("incapace", "incapaci", "inetto", "inetti", "gentaglia", "feccia", "sfaccendati", "ignorante", "ignoranti", "vergognatevi",
          "vergognati", "pecore", "inutile", "zero cervello", "senza cervello", "buoni a nulla", "fate ridere", "fai ridere",
          "tornatevene", "a casa vostra", "pulite le strade", "invaso da", "voi stranieri", "questa gente", "gente così")
ACCUSE = ("ladro", "ladri", "ladra", "delinquente", "delinquenti", "farabutto", "farabutti", "mafioso", "mafiosi", "corrotto", "corrotti",
          "truffatore", "truffatori", "truffa", "criminale", "criminali")
PAROLE_SPAM = ("compra", "guadagna", "guadagni", "offerta", "gratis", "sconto", "casino", "bitcoin", "prestito", "vincita", "clicca")

RE_AUGURIO_MORTE = re.compile(r"\b(?:spero|speriamo|auguro|mi auguro)\b.{0,30}\b(?:muoi\w*|morir\w*|mort\w*|crep\w*|investa\w*|ammazz\w*)\b")
RE_MINACCIA = re.compile(
    r"\b(?:ti|vi|la|lo|le|li|gli)\s+(?:ammazz\w*|uccid\w*|uccis\w*|spacc\w*|distrugg\w*|brucio|bruc\w+|rompo|picch\w+|sfascio|apro)\b"
    r"|\b(?:ti|vi)\s+(?:butto|sparo|taglio|sfregio|affogo|picchio)\b|\bbruc(?:io|erò|eremo)\s+(?:la|le|il|i|lo|gli)\s+\w+|\b(?:ti|vi)\s+faccio\s+(?:fuori|male|pagare)\b|\bte la faccio pagare\b|\bvi trovo sotto casa\b|\bmorte a\b|\bviolenza su\b"
    r"|\bguardar\w+\s+le\s+spalle\b|\baspett\w+\s+sotto\s+casa\b")
RE_TELEFONO = re.compile(r"(?<![\d\w])(?:(?:\+|00)39[\s.\-]?)?(?:3\d{2}[\s.\-]?\d{6,7}|0\d{1,3}[\s.\-]?\d{5,8})(?![\d\w])")
RE_INDIRIZZO_CASA = re.compile(r"\b(?:abit\w+|vive|vivo|dimora|residente|casa)\b.{0,40}\b(?:via|viale|piazza|corso|largo|vicolo)\s+[\w' ]{3,30}\s\d{1,3}\b", re.I)
RE_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
RE_TARGA = re.compile(r"\b[A-Z]{2}\s?\d{3}\s?[A-Z]{2}\b")
RE_CF = re.compile(r"\b[A-Za-z]{6}\d{2}[A-Za-z]\d{2}[A-Za-z]\d{3}[A-Za-z]\b")
RE_IBAN = re.compile(r"\bIT\d{2}(?:\s?[0-9A-Z]){23}(?![0-9A-Z])")
RE_URL = re.compile(r"https?://|www\.|\b[a-z0-9\-]+\.(?:com|net|org|it|info|xyz|ru|cn)\b", re.I)

_LEET = str.maketrans({"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t", "@": "a", "$": "s"})


@dataclass
class Esito:
    esito: str                 # bloccato | doppione | da_inviare | pulito
    rischio: int               # 0-100
    segnali: list = field(default_factory=list)
    impronta: str = ""
    categorie: list = field(default_factory=list)   # [(nome, confidenza)] locali

    @property
    def esito_locale(self):
        """Esito da scrivere subito sul contenuto, o None se deve aspettare il modello."""
        return {"bloccato": "bloccato", "doppione": "dubbio", "pulito": "ok"}.get(self.esito)

    @property
    def punteggio(self):
        """Punteggio di rischio 0-1 per `punteggio_moderazione`."""
        return {"bloccato": 0.93, "doppione": 0.5, "pulito": 0.05}.get(self.esito, round(self.rischio / 100, 2))


def normalizza(testo):
    """Minuscole, senza accenti né caratteri invisibili, sostituzioni tipo «c4zzo», lettere ripetute ridotte a due."""
    t = unicodedata.normalize("NFKD", testo).lower()
    t = "".join(c for c in t if not unicodedata.combining(c) and unicodedata.category(c) not in ("Cf", "Cc") or c in "\n\t ")
    t = re.sub(r"\b(?:[a-z0-9][\s.\-_*]+){3,}[a-z0-9]\b", lambda m: re.sub(r"[\s.\-_*]+", "", m.group(0)), t)  # «i d i o t a» → «idiota»
    t = t.translate(_LEET)
    return re.sub(r"(.)\1{2,}", r"\1\1", t)


def impronta(testo):
    base = re.sub(r"[^a-z0-9]+", " ", normalizza(testo)).strip()
    return hashlib.sha256(base.encode()).hexdigest()


def _cf_valido(cf):
    cf = cf.upper()
    dispari = {**dict(zip("0123456789", [1, 0, 5, 7, 9, 13, 15, 17, 19, 21])),
               **dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23]))}
    pari = {**{c: i for i, c in enumerate("0123456789")}, **{c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}}
    tot = sum(dispari[c] if i % 2 == 0 else pari[c] for i, c in enumerate(cf[:15]))
    return cf[15] == chr(ord("A") + tot % 26)


def _iban_valido(iban):
    r = iban[4:] + iban[:4]
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1


SOLO_ESATTE = {"ritardato", "parassita", "parassiti", "buffone", "buffoni"}   # troppo vicine a parole comuni («ritardo», «parassiti»): niente confronto approssimato


def _parola_vicina(token, elenco):
    """Variante scritta male di una parola dell'elenco (stessa lunghezza ±1)."""
    vicini = [p for p in elenco if p not in SOLO_ESATTE and abs(len(p) - len(token)) <= 1]
    return len(token) >= 5 and bool(difflib.get_close_matches(token, vicini, n=1, cutoff=0.84))


def analizza(testo, *, ha_media=False, tipo="segnalazione", recenti=()):
    """`recenti`: impronte dei testi che lo stesso autore ha inviato di recente (per i doppioni)."""
    imp = impronta(testo)
    norm = normalizza(testo)
    segnali, rischi = [], []

    if RE_MINACCIA.search(norm) or RE_AUGURIO_MORTE.search(norm):
        return Esito("bloccato", 95, ["minaccia"], imp)
    if imp in set(recenti):
        return Esito("doppione", 30, ["doppione"], imp)

    parole = re.findall(r"[a-z]+", norm)
    singoli = [p for p in INSULTI if " " not in p]
    if any(i in norm for i in INSULTI if " " in i) or any(p in singoli or _parola_vicina(p, singoli) for p in parole):
        segnali.append("insulto"); rischi.append(70)
    if RE_INDIRIZZO_CASA.search(testo):
        segnali.append("indirizzo"); rischi.append(60)
    if any(o in norm for o in OSTILI if " " in o) or any(o in parole for o in OSTILI if " " not in o):
        segnali.append("ostilita"); rischi.append(45)
    if any(a in parole for a in ACCUSE):
        segnali.append("accusa"); rischi.append(45)
    if len(parole) >= 8 and Counter(parole).most_common(1)[0][1] / len(parole) >= 0.5:
        segnali.append("ripetizione"); rischi.append(30)
    if RE_TELEFONO.search(testo) and sum(c.isdigit() for c in RE_TELEFONO.search(testo).group(0)) >= 9:
        segnali.append("telefono"); rischi.append(55)
    if RE_EMAIL.search(testo):
        segnali.append("email"); rischi.append(55)
    if RE_TARGA.search(testo.upper()):
        segnali.append("targa"); rischi.append(55)
    if any(_cf_valido(m) for m in RE_CF.findall(testo)):
        segnali.append("codice_fiscale"); rischi.append(60)
    if any(_iban_valido(re.sub(r"\s", "", m)) for m in RE_IBAN.findall(testo.upper())):
        segnali.append("iban"); rischi.append(60)
    n_url = len(RE_URL.findall(testo))
    if n_url >= 2 or (n_url == 1 and any(p in parole for p in PAROLE_SPAM)):
        segnali.append("spam"); rischi.append(50)
    lettere = [c for c in testo if c.isalpha()]
    if len(lettere) >= 15 and sum(c.isupper() for c in lettere) / len(lettere) > 0.7:
        segnali.append("maiuscole"); rischi.append(25)
    if re.search(r"[!?]{4,}", testo):
        segnali.append("punteggiatura"); rischi.append(20)
    if not lettere:
        segnali.append("senza_lettere"); rischi.append(20)

    categorie = _categorie_locali(testo, "") if tipo == "segnalazione" else []
    if rischi:
        rischio = min(90, max(rischi) + 5 * (len(rischi) - 1))
        return Esito("da_inviare", rischio, segnali, imp, categorie)
    if ha_media:
        return Esito("da_inviare", 10, ["foto"], imp, categorie)  # la visione serve sempre
    if tipo == "segnalazione" and not (categorie and categorie[0][1] >= SOGLIA_CATEGORIA):
        return Esito("da_inviare", 10, ["categoria_incerta"], imp, categorie)
    return Esito("pulito", 0, [], imp, categorie)
