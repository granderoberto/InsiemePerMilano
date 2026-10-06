"""Controlli IA SIMULATI (segnaposto): stessa interfaccia che avranno i servizi veri.

Servono a far funzionare il flusso (esito ok/dubbio/bloccato, categorie suggerite, coerenza) senza modelli reali.
Vanno sostituiti da chiamate ai servizi di IA: vedi il materiale 3 (architettura di integrazione).
"""
import re

INSULTI = ("idiota", "imbecille", "stronzo", "merda", "cretino", "schifoso", "bastardo")
MINACCE = ("ti ammazzo", "ti uccido", "ti spacco", "ti butto giù", "vi ammazzo")
RE_TELEFONO = re.compile(r"(?<!\d)(\+39\s?)?3\d{2}[\s.\-]?\d{6,7}(?!\d)")
RE_TARGA = re.compile(r"\b[A-Z]{2}\s?\d{3}\s?[A-Z]{2}\b")

PAROLE_CATEGORIA = {
    "Ambiente": ("rifiut", "alber", "verde", "inquin", "aria", "polvere", "acqua", "fontanell", "differenziat", "cassonett", "parco", "orto"),
    "Mobilità urbana": ("semafor", "pista ciclabile", "bici", "fermata", "autobus", "tram", "metro", "parcheggi", "strisce", "traffico", "pedonal", "corse", "attraversament"),
    "Politiche giovanili": ("giovan", "ragazz", "student", "aula studio", "campetto", "biblioteca", "skate", "coworking", "sala prove", "under 25"),
    "Decoro urbano": ("marciapied", "panchin", "graffit", "scritte", "cestin", "aiuol", "decoro", "murales", "pulizia", "fioriere", "giardino"),
    "Sicurezza del territorio": ("lampion", "illuminazion", "buio", "sicurezza", "incrocio", "velocit", "pericol", "telecamere", "sottopasso", "cancello", "vigil"),
}


def controlla_testo(testo: str):
    """-> (esito, punteggio_rischio 0-1). bloccato: minacce; dubbio: insulti o dati personali di terzi."""
    t = testo.lower()
    if any(m in t for m in MINACCE):
        return "bloccato", 0.93
    if any(i in t for i in INSULTI):
        return "dubbio", 0.68
    if RE_TELEFONO.search(testo) or RE_TARGA.search(testo.upper()):
        return "dubbio", 0.61
    return "ok", 0.05


def suggerisci_categorie(titolo: str, descrizione: str):
    """-> [(nome_categoria, confidenza)] ordinate per confidenza, solo quelle con almeno un riscontro."""
    t = f"{titolo} {descrizione}".lower()
    punti = {c: sum(t.count(p) for p in parole) for c, parole in PAROLE_CATEGORIA.items()}
    tot = sum(punti.values())
    if tot == 0:
        return []
    ris = [(c, round(min(0.97, 0.45 + 0.5 * p / tot), 3)) for c, p in punti.items() if p > 0]
    return sorted(ris, key=lambda x: -x[1])[:3]


def coerenza_immagine_testo(_titolo, _descrizione, _n_media):
    """Punteggio di coerenza 0-1 (1 = coerente). Simulato."""
    return 0.9
