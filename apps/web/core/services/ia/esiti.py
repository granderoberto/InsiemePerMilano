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


def righe_controlli(righe_log):
    """Per il pannello amministratore: da righe `decisione_ia` su segnalazioni o commenti a righe leggibili, con il contenuto controllato,
    l'esito, la motivazione, i segnali, chi ha deciso e lo stato nella coda."""
    from core.models import CodaIA, Commento, Segnalazione
    righe_log = list(righe_log)
    ids_s = [r.id_oggetto for r in righe_log if r.tabella == "segnalazioni"]
    ids_c = [r.id_oggetto for r in righe_log if r.tabella == "commenti"]
    segn = Segnalazione.objects.in_bulk(ids_s)
    comm = Commento.objects.select_related("segnalazione").in_bulk(ids_c)
    coda_s, coda_c = {}, {}
    for c in CodaIA.objects.filter(segnalazione_id__in=ids_s).order_by("id"):
        coda_s[c.segnalazione_id] = c
    for c in CodaIA.objects.filter(commento_id__in=ids_c).order_by("id"):
        coda_c[c.commento_id] = c
    out = []
    for r in righe_log:
        d = r.dati_nuovi or {}
        sing = r.tabella == "segnalazioni"
        o = (segn if sing else comm).get(r.id_oggetto)
        coda = (coda_s if sing else coda_c).get(r.id_oggetto)
        out.append({
            "quando": r.avvenuto_il, "tipo": "segnalazione" if sing else "commento", "id": r.id_oggetto,
            "testo": (o.titolo if sing else o.testo) if o else ("(commento non pubblicato)" if r.id_oggetto == 0 else "(eliminato)"),
            "segnalazione_id": (o.id if sing else o.segnalazione_id) if o else None,
            "commento_id": None if sing else r.id_oggetto,
            "esito": d.get("esito_moderazione"), "motivazione": d.get("motivazione") or "",
            "segnali": [etichetta(x) for x in (d.get("segnali") or [])],
            "fonte": {"openrouter": "modello", "locale": "controllo locale"}.get(d.get("fornitore"), "controllo simulato"),
            "modello": d.get("modello"), "secondi": d.get("secondi"), "errore": d.get("errore") or "",
            "coda": coda.stato if coda else None, "tentativi": coda.tentativi if coda else None})
    return out
