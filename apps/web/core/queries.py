"""Query condivise. I conteggi sono sottoquery correlate: unire sostegni, commenti e classificazioni in un
solo join moltiplica le righe (e sul piano Free di Aiven riempie lo spazio temporaneo del server)."""
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from .models import Commento, Sostegno


def con_conteggi(qs):
    sost = (Sostegno.objects.filter(segnalazione=OuterRef("pk")).order_by().values("segnalazione")
            .annotate(c=Count("utente")).values("c"))
    comm = (Commento.objects.filter(segnalazione=OuterRef("pk"), nascosto=False, eliminato_il__isnull=True).order_by()
            .values("segnalazione").annotate(c=Count("id")).values("c"))
    return qs.annotate(n_sostegni=Coalesce(Subquery(sost, output_field=IntegerField()), Value(0)),
                       n_commenti=Coalesce(Subquery(comm, output_field=IntegerField()), Value(0)))
