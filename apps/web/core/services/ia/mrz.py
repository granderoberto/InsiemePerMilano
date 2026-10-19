"""Zona a lettura ottica (MRZ) di carta d'identità elettronica (TD1, 3 righe da 30) e passaporto (TD3, 2 righe da 44).

Si legge con l'OCR, quindi si cercano le righe che sembrano una MRZ e si verificano i **codici di controllo** (pesi 7-3-1):
un documento falso o un OCR sbagliato quasi mai li soddisfa. Qui non si usa nessun servizio esterno."""
import re
from datetime import date

PESI = (7, 3, 1)


def _valore(c: str) -> int:
    if c.isdigit():
        return int(c)
    if c == "<":
        return 0
    return ord(c) - 55   # A=10 ... Z=35


def controllo(campo: str) -> str:
    return str(sum(_valore(c) * PESI[i % 3] for i, c in enumerate(campo)) % 10)


def _cifre(s: str) -> str:
    """Nei campi numerici l'OCR confonde lettere e cifre: si riportano le più probabili."""
    return s.translate(str.maketrans("OQDIZSBG", "00011568"))


def _data(aammgg: str, futura: bool):
    """AAMMGG → date. L'anno a due cifre: per la nascita si sceglie il secolo che dà una data passata."""
    try:
        a, m, g = int(aammgg[0:2]), int(aammgg[2:4]), int(aammgg[4:6])
        anno = 2000 + a
        if not futura and anno > date.today().year:
            anno -= 100
        return date(anno, m, g)
    except (ValueError, IndexError):
        return None


def _righe(testo: str):
    out = []
    for r in testo.upper().splitlines():
        r = re.sub(r"[^A-Z0-9<]", "", r.replace(" ", "").replace("«", "<").replace("‹", "<"))
        if len(r) >= 28 and r.count("<") >= 2:
            out.append(r)
    return out


def leggi(testo: str):
    """-> dict {tipo, nascita, scadenza, controlli_ok, controlli_tot, numero} oppure None se non si trova una MRZ."""
    righe = _righe(testo)
    # TD3 (passaporto): due righe da 44
    for i in range(len(righe) - 1):
        a, b = righe[i], righe[i + 1]
        if len(b) in (43, 44, 45) and len(a) in (43, 44, 45) and a.startswith("P"):
            b = (b + "<" * 44)[:44]
            ok = controllo(b[0:9]) == _cifre(b[9])
            ok += controllo(_cifre(b[13:19])) == _cifre(b[19])
            ok += controllo(_cifre(b[21:27])) == _cifre(b[27])
            personale_vuoto = set(b[28:42]) == {"<"} and b[42] in "<0"
            ok += personale_vuoto or controllo(b[28:42]) == _cifre(b[42])
            composto = b[0:10] + b[13:20] + b[21:43]
            ok += controllo(composto) == _cifre(b[43])
            return {"tipo": "TD3", "nascita": _data(_cifre(b[13:19]), False), "scadenza": _data(_cifre(b[21:27]), True),
                    "controlli_ok": ok, "controlli_tot": 5, "numero": b[0:9]}
    # TD1 (carta d'identità): tre righe da 30
    for i in range(len(righe) - 2):
        a, b, c = righe[i], righe[i + 1], righe[i + 2]
        if all(len(x) in (29, 30, 31) for x in (a, b, c)) and a[0] in "ICA":
            a, b = (a + "<" * 30)[:30], (b + "<" * 30)[:30]
            ok = controllo(a[5:14]) == _cifre(a[14])
            ok += controllo(_cifre(b[0:6])) == _cifre(b[6])
            ok += controllo(_cifre(b[8:14])) == _cifre(b[14])
            composto = a[5:30] + b[0:7] + b[8:15] + b[18:29]
            ok += controllo(composto) == _cifre(b[29])
            return {"tipo": "TD1", "nascita": _data(_cifre(b[0:6]), False), "scadenza": _data(_cifre(b[8:14]), True),
                    "controlli_ok": ok, "controlli_tot": 4, "numero": a[5:14]}
    return None


# --- utilità per le prove: costruzione di una MRZ valida
def costruisci_td1(numero: str, nascita: str, scadenza: str, nome: str, cognome: str, nazione="ITA") -> str:
    a = ("I<" + nazione + numero.ljust(9, "<")[:9])
    a += controllo(a[5:14]) + "<" * 15
    b = nascita + controllo(nascita) + "M" + scadenza + controllo(scadenza) + nazione + "<" * 11
    b = b[:29]
    composto = a[5:30] + b[0:7] + b[8:15] + b[18:29]
    b += controllo(composto)
    c = (cognome + "<<" + nome).replace(" ", "<")
    c = (c + "<" * 30)[:30]
    return "\n".join([a[:30].ljust(30, "<"), b, c])


def costruisci_td3(numero: str, nascita: str, scadenza: str, nome: str, cognome: str, nazione="ITA") -> str:
    a = ("P<" + nazione + (cognome + "<<" + nome).replace(" ", "<")).ljust(44, "<")[:44]
    b = numero.ljust(9, "<")[:9] + controllo(numero.ljust(9, "<")[:9]) + nazione + nascita + controllo(nascita) + "F" + scadenza + controllo(scadenza)
    b += "<" * 14 + "0"
    b += controllo(b[0:10] + b[13:20] + b[21:43])
    return a + "\n" + b
