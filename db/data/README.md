# Dati sorgente: quartieri di Milano

Fonte: Comune di Milano, portale Open Data (https://dati.comune.milano.it), licenza **CC BY 4.0**
(attribuzione obbligatoria: «Dati: Comune di Milano, CC BY»). Scaricati il 2026-09-29.

| File | Dataset | Contenuto |
|---|---|---|
| `nil_vigenti_pgt2030.geojson` | [Nuclei d'Identità Locale (NIL) VIGENTI - PGT 2030](https://dati.comune.milano.it/en/dataset/ds964-nil-vigenti-pgt-2030) (aggiornato 2026-05-08) | 88 poligoni NIL, EPSG:4326 (lon, lat). Usato per `nome` e `confine`. |
| `municipi.geojson` | [Territorio: superficie dei Municipi](https://dati.comune.milano.it/dataset/ds379-infogeo-municipi-superficie) | 9 poligoni dei Municipi, EPSG:4326. Usato solo per ricavare `municipio`. |

Il file dei NIL non contiene il Municipio. `tools/geo/import_quartieri.py` lo ricava assegnando
a ogni NIL il Municipio con la maggiore area di sovrapposizione. 16 NIL su 88 attraversano più
Municipi (l'import li elenca): per questi il valore è un'approssimazione.

## Import

```bash
python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt
tools/.venv/bin/python tools/geo/import_quartieri.py <database>            # upsert, idempotente
tools/.venv/bin/python tools/geo/import_quartieri.py <database> --dry-run  # solo report
```

`quartieri.id` coincide con `ID_NIL` della fonte; `nome` è quello ufficiale (maiuscolo, com'è nella fonte).
