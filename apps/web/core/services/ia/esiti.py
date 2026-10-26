"""Ultima decisione automatica su segnalazioni e commenti, letta dal registro (`log_attivita`, operazione `decisione_ia`).
Serve a mostrare al moderatore il motivo dell'esito: il modello dà una motivazione di poche parole e il prefiltro dei segnali."""
from core.models import LogAttivita

ETICHETTE = {
    "foto": "con foto", "insulto": "insulto", "telefono": "numero di telefono", "email": "indirizzo email", "targa": "targa",
    "codice_fiscale": "codice fiscale", "iban": "IBAN", "spam": "possibile spam", "maiuscole": "tutto maiuscolo",
    "punteggiatura": "punteggiatura eccessiva", "senza_lettere": "senza lettere", "categoria_incerta": "categoria incerta",
    "doppione": "testo già inviato", "minaccia": "minaccia", "testo_nelle_foto": "testo nelle foto",
    "foto_non_verificabili": "foto non verificabili", "indirizzo": "indirizzo di casa", "ostilita": "tono ostile", "rilettura": "rilettura di controllo", "accusa": "accusa a persone", "ripetizione": "testo ripetitivo", "volti_non_sfocati": "volti non sfocati",
}


def etichetta(segnale):
    if str(segnale).startswith("volti_sfocati"):
        return "volti sfocati: " + str(segnale).split(":")[-1]
    return ETICHETTE.get(segnale, str(segnale))


def ultime_decisioni(tabella, ids):
    """{id oggetto: {esito, motivazione, segnali, modello, fornitore, quando}} per gli oggetti che hanno una decisione."""
    ids = list(ids)
    if not ids:
        return {}
    out = {}
    for r in LogAttivita.objects.filter(tabella=tabella, operazione="decisione_ia", id_oggetto__in=ids).order_by("id"):
        d = r.dati_nuovi or {}
        out[r.id_oggetto] = {"esito": d.get("esito_moderazione"), "motivazione": d.get("motivazione") or "",
                             "segnali": [etichetta(x) for x in (d.get("segnali") or [])], "modello": d.get("modello"),
                             "fornitore": d.get("fornitore"), "errore": d.get("errore"), "quando": r.avvenuto_il}
    return out


def collega(oggetti, tabella):
    """Aggiunge `.ia` a ogni oggetto (segnalazione o commento) della lista."""
    oggetti = list(oggetti)
    d = ultime_decisioni(tabella, [o.id for o in oggetti])
    for o in oggetti:
        o.ia = d.get(o.id)
    return oggetti
