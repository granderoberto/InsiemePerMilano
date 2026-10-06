"""Criteri delle password.

Specifica (par. 3.2): almeno 8 caratteri, con una maiuscola, un numero e un simbolo; salvata solo come hash.
In più, per sicurezza reale:
- al massimo 72 byte (limite di bcrypt: oltre, la password verrebbe troncata o rifiutata);
- non una password notissima (nemmeno con cifre e simboli aggiunti: «Password1!» è «password»);
- non basata sui propri dati (nome, cognome, parte locale dell'email);
- non una serie banale (aaaaaaaa1!, 12345678A!).
Il server è l'autorità: i controlli in JavaScript (static/js/password.js) sono solo un aiuto in tempo reale e
usano le stesse regole."""
import re

MIN_CARATTERI = 8
MAX_BYTE = 72

# normalizzate: minuscole e senza cifre né simboli (vedi `_radice`)
_COMUNI = set("""password passw0rd pass admin administrator root qwerty qwertyuiop asdfgh asdfghjkl zxcvbn zxcvbnm azerty
abc abcd abcdef welcome login letmein iloveyou monkey dragon master sunshine princess football baseball shadow superman
batman trustno michael jordan hunter freedom whatever secret changeme default guest test prova ciao ciaociao
italia italiano italiana milano milan inter juventus juve napoli roma lazio fiorentina torino bologna atalanta
password password forzainter forzamilan forzajuve forzaroma forzanapoli amore amoremio tiamo tiamoo bellissima
sole luna stella ragazzo ragazza mamma papa famiglia francesco alessandro giuseppe giovanni andrea marco luca
matteo lorenzo davide simone federico giulia sara martina chiara francesca valentina elisa pizza pasta caffe
scuola studente galvani insiemepermilano lanostracitta lanostracittail milano2026 estate inverno primavera autunno""".split())

_SEQUENZE = ["abcdefghijklmnopqrstuvwxyz", "qwertyuiopasdfghjklzxcvbnm", "01234567890", "09876543210"]


_LEET = str.maketrans("013457@$", "oieastas")  # P4ssw0rd → password


def _radice(p: str) -> str:
    return re.sub(r"[^a-zà-ù]", "", p.lower().translate(_LEET))


def _sequenza_banale(p: str) -> bool:
    """Gran parte della password è una sequenza (1234, abcd, qwer) o lo stesso carattere ripetuto."""
    t = p.lower()
    if len(set(t)) <= 3:
        return True
    for seq in _SEQUENZE:
        run = best = 0
        for i in range(len(t)):
            if i and t[i - 1:i + 1] in seq:
                run += 1
                best = max(best, run + 1)
            else:
                run = 0
        if best >= 6:
            return True
    return False


def requisiti(p: str) -> dict:
    """Esito di ogni requisito (per la lista di controllo nell'interfaccia)."""
    return {
        "lunghezza": len(p) >= MIN_CARATTERI,
        "maiuscola": bool(re.search(r"[A-ZÀ-Ý]", p)),
        "numero": bool(re.search(r"\d", p)),
        "simbolo": bool(re.search(r"[^\w\s]|_", p)),
        "massimo": len(p.encode()) <= MAX_BYTE,
    }


def valida(p: str, nome="", cognome="", email="") -> list:
    """Elenco dei problemi (vuoto = password accettata)."""
    errori = []
    r = requisiti(p)
    if not r["lunghezza"]:
        errori.append(f"Almeno {MIN_CARATTERI} caratteri.")
    if not r["maiuscola"]:
        errori.append("Almeno una lettera maiuscola.")
    if not r["numero"]:
        errori.append("Almeno un numero.")
    if not r["simbolo"]:
        errori.append("Almeno un simbolo (per esempio ! ? % & # @ -).")
    if not r["massimo"]:
        errori.append(f"Al massimo {MAX_BYTE} byte (circa 70 caratteri): è il limite della cifratura usata.")
    if errori:
        return errori
    if _radice(p) in _COMUNI or any(c in _radice(p) for c in _COMUNI if len(c) >= 6 and len(_radice(p)) <= len(c) + 3):
        errori.append("È una password troppo comune: scegline una meno prevedibile.")
    if _sequenza_banale(p):
        errori.append("Evita ripetizioni e sequenze come 1234 o abcd.")
    parti = [x for x in (_radice(nome), _radice(cognome), _radice(email.split("@")[0] if email else "")) if len(x) >= 4]
    if any(x in _radice(p) for x in parti):
        errori.append("Non usare il tuo nome, cognome o email nella password.")
    return errori
