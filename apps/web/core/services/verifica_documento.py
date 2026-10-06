"""Verifica automatica dell'identità (par. 3.3) — SIMULATA.

Stessa forma di risposta che avrà il servizio vero (vedi docs/architettura_ia.md, modulo 1): cinque controlli, un punteggio
0-100 e un esito. Qui i controlli sono sostituiti da prove sulla qualità dei file, così che tutte le strade si possano
provare: un documento a bassa risoluzione va in revisione umana, un selfie minuscolo viene rifiutato.
Da sostituire con OCR, confronto dei dati, validità, autenticità e riconoscimento del volto."""

MOTIVI = {"ok_lettura_ocr": "Documento non leggibile: foto troppo piccola o sfocata",
          "ok_corrispondenza_dati": "I dati non corrispondono a quelli inseriti",
          "ok_validita": "Documento scaduto o codici di controllo errati",
          "ok_autenticita": "Sospetta alterazione del documento",
          "ok_confronto_volto": "Il volto nel selfie non corrisponde alla foto del documento"}


def controlla(fronte, selfie):
    """fronte e selfie: (bytes, tipo, (larghezza, altezza)|None) come da file_documento.leggi."""
    dim_f, dim_s = fronte[2], selfie[2]
    flag = {
        "ok_lettura_ocr": dim_f is None or min(dim_f) >= 600,        # un PDF si considera leggibile
        "ok_corrispondenza_dati": True,
        "ok_validita": True,
        "ok_autenticita": True,
        "ok_confronto_volto": dim_s is not None and min(dim_s) >= 240,
    }
    punteggio = 96 - (30 if not flag["ok_lettura_ocr"] else 0) - (60 if not flag["ok_confronto_volto"] else 0)
    esito = "approvata" if punteggio >= 85 else "da_rivedere" if punteggio >= 50 else "rifiutata"
    motivo = "; ".join(MOTIVI[k] for k, v in flag.items() if not v) or None
    return {"flag": flag, "punteggio": punteggio, "esito": esito, "motivo": motivo}
