"""Segnalazioni simili già presenti nella stessa zona (par. 5.3): si mostrano prima dell'invio,
così chi vede che il problema è già stato segnalato può sostenerlo invece di creare un doppione."""
import math
import re

from django.db.models import Prefetch

from core.models import Classificazione, Media, Segnalazione
from core.queries import con_conteggi

RAGGIO_M = 800          # oltre questa distanza non è "la stessa zona"
SOGLIA_TESTO = 0.10     # somiglianza minima del testo per proporla da sola
PAROLE_VUOTE = set("""il lo la i gli le un uno una di a da in con su per tra fra e ed o ma che non è sono c' l' un' del dello della dei degli delle
al allo alla ai agli alle dal dallo dalla dai dagli dalle nel nello nella nei negli nelle sul sullo sulla sui sugli sulle
più molto anche come quando dove ho ha hanno si ci ne mi ti questo questa questi queste quello quella poi già ancora
sempre solo tutti tutto ogni stato stata stati state essere fare fatto""".split())


def _radici(testo: str) -> set:
    """Parole significative ridotte alla radice (prime 5 lettere): 'panchine' e 'panchina' coincidono."""
    return {p[:5] for p in re.findall(r"[a-zàèéìòù]{3,}", testo.lower()) if p not in PAROLE_VUOTE}


def distanza_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def trova_simili(lat, lon, titolo="", descrizione="", categorie=(), escludi=None, limite=5):
    """Segnalazioni pubbliche entro RAGGIO_M, ordinate per somiglianza. Una sola lettura dal database (più le categorie)."""
    dlat = RAGGIO_M / 111_000
    dlon = RAGGIO_M / (111_000 * math.cos(math.radians(lat)))
    qs = con_conteggi(Segnalazione.objects.filter(
        stato__pubblico=True, nascosta=False, eliminata_il__isnull=True,
        latitudine__range=(lat - dlat, lat + dlat), longitudine__range=(lon - dlon, lon + dlon)).select_related("quartiere", "stato"))
    if escludi:
        qs = qs.exclude(pk=escludi)
    qs = qs.prefetch_related(Prefetch("classificazioni", queryset=Classificazione.objects.only("segnalazione", "categoria"), to_attr="cat_ids"))
    mie = _radici(f"{titolo} {descrizione}")
    cat_mie = {int(c) for c in categorie}
    risultati = []
    for s in qs:
        d = distanza_m(lat, lon, float(s.latitudine), float(s.longitudine))
        if d > RAGGIO_M:
            continue
        loro = _radici(f"{s.titolo} {s.descrizione}")
        testo = len(mie & loro) / len(mie | loro) if mie and loro else 0.0
        stessa_cat = bool(cat_mie & {c.categoria_id for c in s.cat_ids})
        vicino = 1 - d / RAGGIO_M
        if testo < SOGLIA_TESTO and not (stessa_cat and d <= 250):
            continue  # né parole in comune né stessa categoria a due passi: non è la stessa cosa
        punteggio = 0.55 * min(1, testo * 3) + 0.30 * vicino + 0.15 * (1 if stessa_cat else 0)
        risultati.append((punteggio, d, testo, s))
    risultati.sort(key=lambda x: -x[0])
    return [{"id": s.id, "titolo": s.titolo, "tipo": s.tipo, "stato": s.stato.nome, "quartiere": s.quartiere.nome_leggibile,
             "distanza_m": round(d / 10) * 10, "sostegni": s.n_sostegni, "commenti": s.n_commenti,
             "somiglianza": round(100 * p), "url": f"/segnalazioni/{s.id}/", "autore_id": s.autore_id}
            for p, d, t, s in risultati[:limite]]
