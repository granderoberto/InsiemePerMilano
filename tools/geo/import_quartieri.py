#!/usr/bin/env python3
"""Importa i 88 NIL del Comune di Milano nella tabella `quartieri`.

Uso: tools/.venv/bin/python tools/geo/import_quartieri.py <database> [--dry-run]

Fonti (vedi db/data/README.md): nil_vigenti_pgt2030.geojson (nome e confine)
e municipi.geojson (usato solo per ricavare il municipio di ciascun NIL).
Idempotente: l'id in `quartieri` è ID_NIL della fonte, l'import fa upsert.
Credenziali da .env, certificato certs/ca.pem.
"""
import json
import sys
from pathlib import Path

import pymysql
from shapely.geometry import shape
from shapely.validation import explain_validity

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "db" / "data"


def leggi_env():
    env = {}
    for riga in (ROOT / ".env").read_text().splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            k, v = riga.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def municipio_di(geom, municipi):
    """Municipio con la maggiore area di intersezione; restituisce anche la quota."""
    aree = {m: geom.intersection(g).area for m, g in municipi.items()}
    tot = geom.area
    best = max(aree, key=aree.get)
    return best, aree[best] / tot


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    db = sys.argv[1]
    dry = "--dry-run" in sys.argv

    nil = json.loads((DATA / "nil_vigenti_pgt2030.geojson").read_text())["features"]
    muni = json.loads((DATA / "municipi.geojson").read_text())["features"]
    municipi = {f["properties"]["MUNICIPIO"]: shape(f["geometry"]) for f in muni}
    assert sorted(municipi) == list(range(1, 10)), "attesi i municipi 1-9"

    righe, ambigui = [], []
    for f in nil:
        p = f["properties"]
        g = shape(f["geometry"])
        if not g.is_valid:
            sys.exit(f"Geometria non valida per NIL {p['ID_NIL']}: {explain_validity(g)}")
        m, quota = municipio_di(g, municipi)
        if quota < 0.95:
            ambigui.append((p["ID_NIL"], p["NIL"], m, round(quota * 100, 1)))
        righe.append((p["ID_NIL"], p["NIL"], m, json.dumps(f["geometry"], separators=(",", ":"))))

    print(f"{len(righe)} NIL letti; {len(ambigui)} con quota nel municipio scelto < 95%:")
    for a in ambigui:
        print("  NIL %d %s -> municipio %d (%.1f%%)" % a)
    if dry:
        return

    env = leggi_env()
    con = pymysql.connect(
        host=env["DB_HOST"], port=int(env["DB_PORT"]), user=env["DB_USER"],
        password=env["DB_PASSWORD"], database=db, charset="utf8mb4",
        ssl_ca=str(ROOT / "certs" / "ca.pem"), ssl_verify_cert=True, ssl_verify_identity=True,
    )
    with con, con.cursor() as cur:
        cur.execute("SET time_zone = '+00:00'")
        cur.executemany(
            "INSERT INTO quartieri (id, nome, municipio, confine) VALUES (%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE nome=VALUES(nome), municipio=VALUES(municipio), confine=VALUES(confine)",
            righe,
        )
        con.commit()
        cur.execute("SELECT COUNT(*), COUNT(confine), MIN(municipio), MAX(municipio) FROM quartieri")
        print("in %s: righe=%d, con confine=%d, municipi %d-%d" % ((db,) + cur.fetchone()))


if __name__ == "__main__":
    main()
