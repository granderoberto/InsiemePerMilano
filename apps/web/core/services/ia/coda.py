"""Coda persistente dei controlli IA (tabella `coda_ia`, migrazione 006).

Un solo lavoratore la consuma (vedi lavoratore.py). Qui solo le operazioni sulla tabella:
  accoda          inserisce un lavoro; un lavoro precedente dello stesso contenuto ancora in coda diventa `saltato`
  scegli          sceglie il prossimo lavoro: una segnalazione (priorità, poi età) oppure un blocco di commenti pronti
  prendi/rilascia/chiudi   cambi di stato di una riga
  riprendi_bloccate        righe `in_corso` da troppo tempo (processo riavviato) tornano in coda"""
from datetime import timedelta

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from core.models import CodaIA


def accoda(esito_prefiltro, *, segnalazione=None, commento=None):
    assert (segnalazione is None) != (commento is None)
    filtro = {"segnalazione": segnalazione} if segnalazione else {"commento": commento}
    CodaIA.objects.filter(stato="in_coda", **filtro).update(stato="saltato", finita_il=timezone.now(), errore="sostituita da una modifica")
    return CodaIA.objects.create(priorita=esito_prefiltro.rischio, impronta=esito_prefiltro.impronta, segnali=esito_prefiltro.segnali, **filtro)


def _pronte(adesso):
    return CodaIA.objects.filter(stato="in_coda", non_prima_di__lte=adesso)


def scegli(adesso=None):
    """-> ("segnalazione", [riga]) | ("commento", [righe]) | None."""
    adesso = adesso or timezone.now()
    riga = (_pronte(adesso).filter(segnalazione__isnull=False).select_related("segnalazione")
            .order_by("-priorita", "creata_il").first())
    if riga:
        return "segnalazione", [riga]
    commenti = list(_pronte(adesso).filter(commento__isnull=False).select_related("commento")
                    .order_by("-priorita", "creata_il")[:settings.IA_COMMENTI_BLOCCO])
    if commenti:
        vecchio = min(c.creata_il for c in commenti)
        if len(commenti) >= settings.IA_COMMENTI_MINIMO or adesso - vecchio >= timedelta(hours=settings.IA_COMMENTI_ATTESA_ORE):
            return "commento", commenti
    return None


def prendi(righe):
    CodaIA.objects.filter(pk__in=[r.pk for r in righe]).update(stato="in_corso", presa_il=timezone.now(), tentativi=F("tentativi") + 1)


def rilascia(righe, minuti=15, errore=""):
    """Torna in coda, da riprovare tra `minuti`."""
    CodaIA.objects.filter(pk__in=[r.pk for r in righe]).update(
        stato="in_coda", non_prima_di=timezone.now() + timedelta(minutes=minuti), errore=errore[:200] or None)


def chiudi(righe, stato, errore=""):
    CodaIA.objects.filter(pk__in=[r.pk for r in righe]).update(stato=stato, finita_il=timezone.now(), errore=errore[:200] or None)


def riprendi_bloccate(minuti=10):
    return CodaIA.objects.filter(stato="in_corso", presa_il__lt=timezone.now() - timedelta(minutes=minuti)).update(stato="in_coda")


def scadute(adesso=None):
    """Righe in coda da più di IA_ATTESA_MASSIMA_ORE."""
    limite = (adesso or timezone.now()) - timedelta(hours=settings.IA_ATTESA_MASSIMA_ORE)
    return list(CodaIA.objects.filter(stato="in_coda", creata_il__lt=limite).select_related("segnalazione", "commento"))


def conteggi():
    """{stato: n} per il pannello amministratore."""
    from django.db.models import Count
    return {r["stato"]: r["n"] for r in CodaIA.objects.values("stato").annotate(n=Count("id"))}
