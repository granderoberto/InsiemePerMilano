import json

from django.core.serializers.json import DjangoJSONEncoder

from core.models import LogAttivita


def _json(d):
    """Date e Decimal diventano testo: così qualunque dizionario si può scrivere nelle colonne JSON."""
    return None if d is None else json.loads(json.dumps(d, cls=DjangoJSONEncoder))


def registra(utente, operazione, tabella, id_oggetto, prima=None, dopo=None):
    """Scrive in log_attivita (append-only). utente=None: azione del sistema/IA."""
    LogAttivita.objects.create(
        attore="utente" if utente else "sistema", utente=utente, operazione=operazione,
        tabella=tabella, id_oggetto=id_oggetto, dati_precedenti=_json(prima), dati_nuovi=_json(dopo),
    )
