"""Copia dei file caricati nel database (tabella `media_contenuti`, a pezzi da 4 MB).

Su un hosting con disco temporaneo (per esempio il piano gratuito di Render) i file sul disco spariscono a ogni riavvio.
Ogni file salvato viene quindi copiato anche nel database; se manca dal disco, `ripristina` lo rimette a posto.
La copia è «al meglio»: se il database non la accetta il caricamento riesce comunque e l'errore finisce nei log."""
import logging
from pathlib import Path

from django.conf import settings
from django.db import connection

log = logging.getLogger(__name__)
PEZZO = 4 * 1024 * 1024


def salva(percorso: str, file: Path) -> bool:
    """percorso: quello di media.percorso (relativo a MEDIA_ROOT)."""
    try:
        with connection.cursor() as cur, open(file, "rb") as f:
            cur.execute("DELETE FROM media_contenuti WHERE percorso = %s", [percorso])
            parte = 0
            while chunk := f.read(PEZZO):
                cur.execute("INSERT INTO media_contenuti (percorso, parte, dati) VALUES (%s, %s, %s)", [percorso, parte, chunk])
                parte += 1
        return True
    except Exception:  # noqa: BLE001 - la copia è un di più: non deve far fallire il caricamento
        log.exception("Copia di %s nel database non riuscita", percorso)
        return False


def ripristina(percorso: str) -> bool:
    """Riscrive sul disco un file presente nell'archivio ma mancante. -> True se l'ha trovato."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT dati FROM media_contenuti WHERE percorso = %s ORDER BY parte", [percorso])
            pezzi = cur.fetchall()
    except Exception:  # noqa: BLE001
        log.exception("Lettura di %s dall'archivio non riuscita", percorso)
        return False
    if not pezzi:
        return False
    dest = (Path(settings.MEDIA_ROOT) / percorso).resolve()
    if Path(settings.MEDIA_ROOT).resolve() not in dest.parents:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    with open(tmp, "wb") as f:
        for (dati,) in pezzi:
            f.write(dati)
    tmp.replace(dest)
    return True


def elimina(percorso: str) -> None:
    try:
        with connection.cursor() as cur:
            cur.execute("DELETE FROM media_contenuti WHERE percorso = %s", [percorso])
    except Exception:  # noqa: BLE001
        log.exception("Eliminazione di %s dall'archivio non riuscita", percorso)
