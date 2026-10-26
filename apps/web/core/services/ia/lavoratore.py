"""Lavoratore dei controlli IA: consuma la coda `coda_ia` in background (docs/piano_ia_openrouter.md, §6).

`passo()` esegue UN lavoro (una segnalazione, oppure un blocco di commenti) rispettando la quota; `ciclo()` lo ripete in un thread.
L'utente non aspetta mai l'IA: il contenuto è già salvato e visibile come «In attesa»; qui si scrive soltanto l'esito.
Regole: il modello può solo peggiorare (esito `ok` oppure `dubbio`, mai `bloccato`: quello è del prefiltro);
se il controllo non riesce (modello assente, risposta non valida dopo 3 tentativi, oltre 24 ore in coda) l'esito è `dubbio`
con il motivo: nel dubbio decide una persona."""
import logging
import threading
import time
from decimal import Decimal

from django.conf import settings
from django.db import OperationalError, close_old_connections, connection
from django.utils import timezone

from core.services import log

from . import coda, openrouter, prefiltro, prompt, quota

logger = logging.getLogger(__name__)
MAX_TENTATIVI = 3
ESITO_OK, ESITO_DUBBIO = ("ok", Decimal("0.050")), ("dubbio", Decimal("0.650"))
BLOCCO = "lnc_coda_ia"


def _registra(tipo, oggetto, esito, *, motivazione="", risposta=None, segnali=None, errore=""):
    dopo = {"esito_moderazione": esito, "fornitore": "openrouter" if risposta else "locale", "versione_prompt": prompt.VERSIONE}
    if motivazione:
        dopo["motivazione"] = motivazione
    if risposta:
        dopo.update(modello=risposta.modello, secondi=round(risposta.secondi, 1), token=risposta.token)
    if segnali:
        dopo["segnali"] = segnali
    if errore:
        dopo["errore"] = errore
    log.registra(None, "decisione_ia", "segnalazioni" if tipo == "segnalazione" else "commenti", oggetto.id, None, dopo)


def _scrivi_esito(tipo, oggetto, esito_punteggio, **kw):
    esito, punteggio = esito_punteggio
    oggetto.esito_moderazione, oggetto.punteggio_moderazione = esito, punteggio
    oggetto.save(update_fields=["esito_moderazione", "punteggio_moderazione"])
    _registra(tipo, oggetto, esito, **kw)


def _obsoleta(riga, oggetto, testo):
    """La riga non serve più: contenuto eliminato o modificato dopo l'accodamento."""
    if oggetto is None or getattr(oggetto, "eliminata_il", None) or getattr(oggetto, "eliminato_il", None):
        return True
    return prefiltro.impronta(testo) != riga.impronta


def _segnalazione(riga):
    s = riga.segnalazione
    testo = f"{s.titolo}\n{s.descrizione}"
    if _obsoleta(riga, s, testo):
        coda.chiudi([riga], "saltato", "contenuto eliminato o modificato")
        return
    utente = f"<segnalazione>\n<titolo>{prompt.pulisci(s.titolo)}</titolo>\n<descrizione>{prompt.pulisci(s.descrizione)}</descrizione>\n</segnalazione>"
    r = openrouter.chiedi("segnalazione", prompt.SISTEMA_SEGNALAZIONE, utente, prompt.SCHEMA_SEGNALAZIONE,
                          modelli=settings.IA_MODELLI_TESTO, max_token=settings.IA_MAX_TOKEN_TESTO)
    approvato = r.dati["approvato"]
    _scrivi_esito("segnalazione", s, ESITO_OK if approvato else ESITO_DUBBIO, motivazione=r.dati["motivazione"], risposta=r, segnali=riga.segnali)
    coda.chiudi([riga], "fatto")


def _commenti(righe):
    valide = []
    for riga in righe:
        if _obsoleta(riga, riga.commento, riga.commento.testo):
            coda.chiudi([riga], "saltato", "contenuto eliminato o modificato")
        else:
            valide.append(riga)
    if not valide:
        return
    utente = "\n".join(f'<commento id="{r.commento_id}">{prompt.pulisci(r.commento.testo)}</commento>' for r in valide)
    r = openrouter.chiedi("commento", prompt.SISTEMA_COMMENTI, utente, prompt.SCHEMA_COMMENTI,
                          modelli=settings.IA_MODELLI_TESTO, max_token=settings.IA_MAX_TOKEN_TESTO)
    per_id = {}
    for x in r.dati["risultati"]:
        per_id.setdefault(x["id"], x)  # se un id compare due volte vale il primo
    for riga in valide:
        x = per_id.get(riga.commento_id)
        if x is None:   # il modello ha saltato questo commento
            _scrivi_esito("commento", riga.commento, ESITO_DUBBIO, motivazione="controllo incompleto", risposta=r, segnali=riga.segnali)
        elif x["approvato"] is False and not x["motivazione"].strip():
            _scrivi_esito("commento", riga.commento, ESITO_DUBBIO, motivazione="senza motivazione", risposta=r, segnali=riga.segnali)
        else:
            _scrivi_esito("commento", riga.commento, ESITO_OK if x["approvato"] else ESITO_DUBBIO, motivazione=x["motivazione"], risposta=r, segnali=riga.segnali)
        coda.chiudi([riga], "fatto")


def _dubbio_senza_modello(riga, errore):
    """Il controllo non è riuscito: l'esito è `dubbio` e decide una persona."""
    oggetto = riga.segnalazione or riga.commento
    tipo = "segnalazione" if riga.segnalazione_id else "commento"
    if oggetto.esito_moderazione is None:
        _scrivi_esito(tipo, oggetto, (ESITO_DUBBIO[0], Decimal("0.500")), motivazione="controllo automatico non disponibile", segnali=riga.segnali, errore=errore)
    coda.chiudi([riga], "fallito", errore)


def _fallimento(righe, errore, minuti):
    for riga in righe:
        riga.refresh_from_db(fields=["tentativi"])
    ancora = [r for r in righe if r.tentativi < MAX_TENTATIVI]
    for riga in righe:
        if riga.tentativi >= MAX_TENTATIVI:
            _dubbio_senza_modello(riga, errore)
    if ancora:
        coda.rilascia(ancora, minuti=minuti, errore=errore)


def passo(adesso=None):
    """Un lavoro. -> «fatto» | «vuoto» | «quota» | «errore»."""
    adesso = adesso or timezone.now()
    coda.riprendi_bloccate()
    for riga in coda.scadute(adesso):   # oltre 24 ore senza esito: decide il moderatore
        _dubbio_senza_modello(riga, "oltre %d ore in coda" % settings.IA_ATTESA_MASSIMA_ORE)
    lavoro = coda.scegli(adesso)
    if lavoro is None:
        return "vuoto"
    tipo, righe = lavoro
    ammesso, motivo = quota.ammesso(tipo)
    if not ammesso:
        return "quota"
    coda.prendi(righe)
    try:
        _segnalazione(righe[0]) if tipo == "segnalazione" else _commenti(righe)
    except openrouter.QuotaEsaurita:
        coda.rilascia(righe, minuti=30, errore="quota esaurita")
        return "quota"
    except openrouter.RispostaNonValida as e:
        _fallimento(righe, str(e), minuti=30)   # la richiesta ha consumato quota: si aspetta prima di riprovare
        return "errore"
    except openrouter.NessunModello as e:
        _fallimento(righe, str(e), minuti=15)
        return "errore"
    return "fatto"


# ---------------------------------------------------------------- thread
ATTESA = {"fatto": 0, "vuoto": 30, "quota": 600, "errore": 60}
_thread = [None]


def _blocco_acquisito():
    with connection.cursor() as c:
        c.execute("SELECT GET_LOCK(%s, 0)", [BLOCCO])
        return c.fetchone()[0] == 1


def ciclo(ferma):
    """Ripete `passo`. Un solo lavoratore alla volta, anche con più processi: lo garantisce un blocco del database."""
    while not ferma.is_set():
        attesa = 60
        try:
            close_old_connections()
            if _blocco_acquisito():
                attesa = ATTESA[passo()]
        except OperationalError:
            logger.warning("IA: database non raggiungibile, riprovo")
            connection.close()
        except Exception:  # noqa: BLE001
            logger.exception("IA: errore imprevisto nel lavoratore")
        ferma.wait(attesa)


def avvia():
    """Avvia il thread (una sola volta per processo). -> il thread."""
    if _thread[0] is None or not _thread[0].is_alive():
        ferma = threading.Event()
        t = threading.Thread(target=ciclo, args=(ferma,), name="lavoratore-ia", daemon=True)
        t.ferma = ferma
        t.start()
        _thread[0] = t
    return _thread[0]
