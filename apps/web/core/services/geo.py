from functools import lru_cache

from shapely.geometry import Point, mapping, shape

from core.models import Quartiere


@lru_cache(maxsize=1)
def _poligoni():
    return [(q.id, shape(q.confine)) for q in Quartiere.objects.exclude(confine__isnull=True)]


@lru_cache(maxsize=1)
def contorni_geojson():
    """I 88 quartieri come GeoJSON semplificato (circa 20 m) per la mappa di scelta: leggero da scaricare."""
    feats = []
    for q in Quartiere.objects.exclude(confine__isnull=True):
        g = shape(q.confine).simplify(0.0002, preserve_topology=True)
        feats.append({"type": "Feature", "id": q.id, "geometry": mapping(g), "properties": {"id": q.id, "nome": q.nome_leggibile}})
    return {"type": "FeatureCollection", "features": feats}


def quartiere_da_punto(lat, lon):
    """Id del quartiere (NIL) che contiene il punto, o None se è fuori dal Comune di Milano."""
    p = Point(float(lon), float(lat))
    for qid, poly in _poligoni():
        if poly.contains(p):
            return qid
    return None
