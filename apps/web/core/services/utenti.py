"""Sospensione, riattivazione, cambio ruolo e modifica dati degli utenti (con motivo e log)."""
from datetime import timedelta

import hashlib
from datetime import date

from django.db import DatabaseError, transaction
from django.utils import timezone

from core.models import Notifica, Sospensione, Utente
from . import log
from .errori import RegolaViolata, traduci

RUOLI = ("utente", "moderatore", "amministratore")


def _notifica(utente, messaggio):
    Notifica.objects.create(utente=utente, tipo="stato_account", messaggio=messaggio[:500], link="/profilo/")


def sospendi(utente: Utente, da: Utente, motivo: str, giorni=None):
    if not motivo.strip():
        raise RegolaViolata("Indica il motivo della sospensione.")
    if utente.id == da.id:
        raise RegolaViolata("Non puoi sospendere te stesso.")
    if utente.stato_account != "attivo":
        raise RegolaViolata("Si possono sospendere solo account attivi.")
    fine = timezone.now() + timedelta(days=giorni) if giorni else None
    try:
        with transaction.atomic():
            s = Sospensione.objects.create(utente=utente, moderatore=da, motivo=motivo.strip(), fine=fine)
            utente.stato_account = "sospeso"
            utente.save(update_fields=["stato_account"])
    except DatabaseError as e:
        raise traduci(e) from e
    log.registra(da, "sospensione", "sospensioni", s.id, {"stato_account": "attivo"},
                 {"stato_account": "sospeso", "motivo": motivo.strip(), "fine": fine})
    _notifica(utente, f"Il tuo account è stato sospeso. Motivo: {motivo.strip()}")
    return s


def riattiva(utente: Utente, da: Utente | None):
    """Revoca la sospensione aperta. da=None: scadenza automatica (decide il sistema)."""
    aperta = Sospensione.objects.filter(utente=utente, revocata_il__isnull=True).order_by("-inizio").first()
    if utente.stato_account != "sospeso" or aperta is None:
        raise RegolaViolata("L'account non risulta sospeso.")
    revocante = da or aperta.moderatore  # il vincolo del DB vuole sempre un revocante: alla scadenza risulta chi ha sospeso
    with transaction.atomic():
        aperta.revocata_il, aperta.revocante = timezone.now(), revocante
        aperta.save(update_fields=["revocata_il", "revocante"])
        utente.stato_account = "attivo"
        utente.save(update_fields=["stato_account"])
    log.registra(da, "sospensione", "sospensioni", aperta.id, {"stato_account": "sospeso"},
                 {"stato_account": "attivo", "revocata": True, "motivo": "scadenza" if da is None else "revoca manuale"})
    _notifica(utente, "Il tuo account è stato riattivato.")


def riattiva_se_scaduta(utente: Utente) -> bool:
    """Alla scadenza della durata l'account torna attivo da solo."""
    if utente.stato_account != "sospeso":
        return False
    aperta = Sospensione.objects.filter(utente=utente, revocata_il__isnull=True).order_by("-inizio").first()
    if aperta and aperta.fine and aperta.fine <= timezone.now():
        riattiva(utente, None)
        return True
    return False


def cambia_ruolo(utente: Utente, da: Utente, nuovo: str):
    if nuovo not in RUOLI:
        raise RegolaViolata("Ruolo non valido.")
    if utente.id == da.id:
        raise RegolaViolata("Nessuno può cambiare il proprio ruolo.")
    if utente.ruolo == nuovo:
        raise RegolaViolata("L'utente ha già questo ruolo.")
    prima = utente.ruolo
    utente.ruolo = nuovo
    utente.save(update_fields=["ruolo"])
    log.registra(da, "cambio_ruolo", "utenti", utente.id, {"ruolo": prima}, {"ruolo": nuovo})
    return prima


def modifica_dati(utente: Utente, da: Utente, nuovi: dict, motivo: str):
    """L'amministratore corregge i dati di un utente indicando sempre il motivo; finisce nel log."""
    if not motivo.strip():
        raise RegolaViolata("Indica il motivo della modifica.")
    campi = ("nome", "cognome", "email", "data_nascita", "quartiere")
    prima = {c: str(getattr(utente, c + "_id" if c == "quartiere" else c)) for c in campi}
    for c in campi:
        setattr(utente, c, nuovi[c])
    try:
        with transaction.atomic():
            utente.save(update_fields=list(campi))
    except DatabaseError as e:
        raise traduci(e) from e
    dopo = {c: str(getattr(utente, c + "_id" if c == "quartiere" else c)) for c in campi}
    log.registra(da, "modifica", "utenti", utente.id, prima, {**dopo, "motivo": motivo.strip()})


def elimina_account(utente: Utente):
    """Eliminazione dell'account (par. 4): si rimuovono i dati personali; segnalazioni, commenti, sostegni e registro delle
    attività restano, in forma anonima, così non si altera la tracciabilità né la classifica.
    Dell'utente restano: id, ruolo, anno di nascita (1° gennaio: la colonna è obbligatoria), metodo di accesso e date."""
    if utente.stato_account == "eliminato":
        raise RegolaViolata("L'account è già stato eliminato.")
    if utente.ruolo == "amministratore" and not Utente.objects.filter(ruolo="amministratore", stato_account="attivo").exclude(pk=utente.pk).exists():
        raise RegolaViolata("Sei l'ultimo amministratore: nomina prima un altro amministratore, poi potrai eliminare l'account.")
    adesso = timezone.now()
    with transaction.atomic():
        utente.nome, utente.cognome = "Utente", "eliminato"
        utente.email = f"eliminato-{utente.id}@anonimo.invalid"
        utente.password = "!" if utente.metodo_registrazione == "credenziali" else None      # il vincolo del DB vuole la password solo con le credenziali
        utente.codice_fiscale_hash = (hashlib.sha256(f"eliminato-{utente.id}".encode()).hexdigest()
                                      if utente.metodo_registrazione in ("spid", "cie") else None)  # il vincolo vuole un valore per SPID/CIE
        utente.data_nascita = date(utente.data_nascita.year, 1, 1)
        utente.quartiere = None
        utente.profilo_pubblico = False
        utente.mfa_attiva, utente.mfa_segreto = False, None
        utente.tentativi_falliti, utente.bloccato_fino = 0, None
        utente.stato_account, utente.eliminato_il = "eliminato", adesso
        utente.save(update_fields=["nome", "cognome", "email", "password", "codice_fiscale_hash", "data_nascita", "quartiere", "profilo_pubblico",
                                   "mfa_attiva", "mfa_segreto", "tentativi_falliti", "bloccato_fino", "stato_account", "eliminato_il"])
        utente.notifiche.all().delete()      # le notifiche sono personali: non si conservano
        utente.preferenze.all().delete()
    log.registra(utente, "eliminazione", "utenti", utente.id, {"stato_account": "attivo"}, {"stato_account": "eliminato"})  # senza dati personali
