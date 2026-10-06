from django.db import DatabaseError, transaction

from core.models import CambioStato, Segnalazione
from . import log
from .errori import traduci


def cambia_stato(seg: Segnalazione, a_id: int, operatore=None, nota=None):
    """Fa avanzare una segnalazione SOLO inserendo in cambi_stato: il trigger controlla la transizione
    (tabella transizioni_ammesse) e aggiorna segnalazioni.id_stato."""
    seg.refresh_from_db(fields=["stato"])
    da_id = seg.stato_id
    try:
        with transaction.atomic():
            CambioStato.objects.create(segnalazione=seg, stato_da_id=da_id, stato_a_id=a_id, operatore=operatore, nota=nota)
    except DatabaseError as e:
        raise traduci(e) from e
    seg.refresh_from_db(fields=["stato", "aggiornata_il"])
    log.registra(operatore, "cambio_stato", "segnalazioni", seg.id, {"id_stato": da_id}, {"id_stato": a_id, "nota": nota})
