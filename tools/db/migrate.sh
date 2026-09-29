#!/usr/bin/env bash
# Applica le migrazioni di db/migrations/ al database indicato.
# Uso: tools/db/migrate.sh <nome_database>
# Credenziali da .env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD), certificato certs/ca.pem.
# Si ferma al primo errore; registra una migrazione in schema_migrations solo se riuscita.
# Idempotente: le migrazioni già registrate vengono saltate.
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Uso: $0 <nome_database>" >&2
  exit 2
fi
DB="$1"
if ! [[ "$DB" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "Nome database non valido: $DB" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
set -a; . "$ROOT/.env"; set +a

# File credenziali temporaneo (permessi 600), rimosso all'uscita
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CNF="$TMP/client.cnf"
( umask 077
  cat > "$CNF" <<CFG
[client]
host=$DB_HOST
port=$DB_PORT
user=$DB_USER
password="$DB_PASSWORD"
ssl-ca=$ROOT/certs/ca.pem
ssl-mode=VERIFY_IDENTITY
default-character-set=utf8mb4
CFG
)
my() { mysql --defaults-extra-file="$CNF" "$@"; }

my "$DB" -e "
CREATE TABLE IF NOT EXISTS schema_migrations (
  versione    VARCHAR(100) NOT NULL PRIMARY KEY,
  applicata_il DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"

applicate=0
for f in "$ROOT"/db/migrations/*.sql; do
  v="$(basename "$f" .sql)"
  gia="$(my -N -B "$DB" -e "SELECT COUNT(*) FROM schema_migrations WHERE versione='$v'")"
  if [ "$gia" != "0" ]; then
    echo "già applicata: $v"
    continue
  fi
  echo "applico: $v"
  if ! my "$DB" < "$f"; then
    echo "ERRORE in $v: migrazione NON registrata. Le DDL fanno commit implicito: se è a metà, ricrea il database e riparti." >&2
    exit 1
  fi
  my "$DB" -e "INSERT INTO schema_migrations (versione) VALUES ('$v')"
  applicate=$((applicate+1))
done
echo "fatto: $applicate migrazioni applicate su $DB"
