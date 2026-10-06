from functools import lru_cache

from shapely.geometry import Point, shape

from core.models import Quartiere


@lru_cache(maxsize=1)
def _poligoni():
    return [(q.id, shape(q.confine)) for q in Quartiere.objects.exclude(confine__isnull=True)]


def quartiere_da_punto(lat, lon):
    """Id del quartiere (NIL) che contiene il punto, o None se è fuori dal Comune di Milano."""
    p = Point(float(lon), float(lat))
    for qid, poly in _poligoni():
        if poly.contains(p):
            return qid
    return None
