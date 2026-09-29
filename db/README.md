# Database: come ricrearlo da zero

MySQL 8 (Aiven Free: 1 GB, un nodo, si spegne se inattivo). Tutti i DATETIME sono in UTC.

## Prerequisiti

- Client `mysql` (serve per `DELIMITER` nei trigger), Python 3.11+.
- `.env` nella radice del progetto (non versionato):
  ```
  DB_HOST=...  DB_PORT=...  DB_USER=...  DB_PASSWORD=...  DB_NAME=...
  ```
- `certs/ca.pem`: certificato CA del servizio (console Aiven → Overview → CA certificate). Non versionato.
- Ambiente Python:
  ```bash
  python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt
  ```

## Procedura

1. **Database vuoto.** In un servizio Aiven nuovo `defaultdb` esiste già. Per il database di test:
   ```sql
   CREATE DATABASE la_nostra_citta_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   ```
2. **Migrazioni** (schema, trigger, viste, dati di riferimento):
   ```bash
   tools/db/migrate.sh defaultdb
   ```
   Lo script è idempotente: registra ogni migrazione in `schema_migrations` solo se riuscita e si ferma al primo
   errore. Le DDL MySQL fanno commit implicito: se una migrazione fallisce a metà, elimina e ricrea il database e
   riparti (`DROP DATABASE` + `CREATE DATABASE`).
3. **Quartieri** (88 NIL da `db/data/`, upsert idempotente):
   ```bash
   tools/.venv/bin/python tools/geo/import_quartieri.py defaultdb
   ```
4. **Dati demo** (opzionale; svuota le tabelle non di riferimento):
   ```bash
   tools/.venv/bin/python tools/seed/seed.py defaultdb
   ```
   Password demo: vedi `tools/seed/README.md`.
5. **Test dei vincoli** (solo su un database di test appena migrato e con `quartieri` vuota: inserisce l'id 1):
   ```bash
   tools/db/migrate.sh la_nostra_citta_test
   mysql --force la_nostra_citta_test < db/test_vincoli.sql   # devono fallire solo le 10 righe ERRORE ATTESO
   ```

## Verifica rapida

```sql
SELECT VERSION(), @@sql_require_primary_key, @@log_bin_trust_function_creators;
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'; -- 22
SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = DATABASE();                            -- 7
```

## File

| Percorso | Scopo |
|---|---|
| `db/schema.sql` | schema completo di riferimento (tabelle, trigger, viste, dati iniziali) |
| `db/migrations/001_schema.sql` | schema senza dati iniziali |
| `db/migrations/002_dati_riferimento.sql` | stati, transizioni ammesse, categorie |
| `db/schema.dbml` | per dbdiagram.io (solo tabelle e relazioni) |
| `db/test_vincoli.sql` | casi di test dei vincoli |
| `db/data/` | GeoJSON dei NIL e dei Municipi, con fonte e licenza |

## Problemi noti

- Connessione rifiutata o timeout: il servizio Free potrebbe essere spento, riaccenderlo dalla console Aiven.
- Errore 1419 alla creazione dei trigger: attivare `log_bin_trust_function_creators`
  dalla Advanced configuration del servizio (oggi è già ON).
- Se lo schema cambia, aggiungere una nuova migrazione (`003_...sql`) e tenere allineati `schema.sql`, `schema.dbml` e `tools/er/gen.py`.
