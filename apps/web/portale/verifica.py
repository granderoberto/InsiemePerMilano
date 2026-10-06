"""Esecuzione della verifica d'identità: i file passano dall'area temporanea cifrata e vengono cancellati a fine verifica."""
from core.models import Notifica, VerificaIdentita
from core.services import log, temporaneo, verifica_documento

MAX_TENTATIVI = 3


def esegui(utente, tentativo, tipo_documento, fronte, retro, selfie):
    """fronte/retro/selfie: tuple di core.services.file_documento.leggi. Crea la riga in verifiche_identita e restituisce l'oggetto.
    Del documento e del selfie non resta nulla: solo esito, punteggio, data (e, se c'è, il revisore)."""
    with temporaneo.archivio() as area:
        for f in (fronte, retro, selfie):
            if f:
                area.salva(f[0])  # qui in futuro: l'IA legge i file dall'area temporanea cifrata
        r = verifica_documento.controlla(fronte, selfie)
    v = VerificaIdentita.objects.create(
        utente=utente, tentativo=tentativo, tipo_documento=tipo_documento, punteggio=r["punteggio"], esito_ia=r["esito"], motivo=r["motivo"], **r["flag"])
    log.registra_molti([(utente, "verifica_identita", "verifiche_identita", v.id, None, {"tentativo": tentativo, "tipo_documento": tipo_documento}),
                        (None, "decisione_ia", "verifiche_identita", v.id, None, {"punteggio": v.punteggio, "esito_ia": v.esito_ia, "simulata": True})])
    rimasti = MAX_TENTATIVI - tentativo
    if v.esito_ia == "approvata":
        testo = "La verifica del documento è stata approvata. Per attivare l'account conferma anche l'indirizzo email."
    elif v.esito_ia == "da_rivedere":
        testo = "La verifica del documento è in revisione: un moderatore la controllerà e ti avviseremo dell'esito."
    else:
        testo = (f"La verifica del documento non è stata superata ({v.motivo}). " +
                 (f"Puoi riprovare: hai ancora {rimasti} tentativ{'o' if rimasti == 1 else 'i'}." if rimasti else
                  "Hai usato tutti e 3 i tentativi: puoi chiedere la revisione di un moderatore."))
    Notifica.objects.create(utente=utente, tipo="verifica_account", messaggio=testo[:500], link="/profilo/")
    return v
