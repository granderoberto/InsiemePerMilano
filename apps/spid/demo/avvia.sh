#!/usr/bin/env bash
# Avvia Trust Anchor (8010), identity provider di prova (8012) e il servizio RP (8011); poi rinnova la catena di fiducia
# dell'RP presso il provider di prova (necessario perché l'esempio contiene catene scadute: vale solo per questa demo).
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D/.."
PY="$PWD/.venv/bin/python"; AMB="$D/.ambiente"; mkdir -p "$D/log"
[ -d "$AMB" ] || { echo "Esegui prima demo/prepara.sh"; exit 1; }
SEGRETO="$(grep -E '^SPID_BRIDGE_SECRET=' ../../.env | cut -d= -f2-)"
[ -n "$SEGRETO" ] || { echo "Manca SPID_BRIDGE_SECRET nel file .env della radice (stesso valore per sito e servizio)."; exit 1; }
"$D/ferma.sh" >/dev/null 2>&1 || true
avvia() {  # avvia NOME CARTELLA PORTA
  ( cd "$2"; nohup "$PY" manage.py runserver "127.0.0.1:$3" --noreload > "$D/log/$1.log" 2>&1 &
    echo $! > "$D/log/$1.pid" )
}
avvia ta "$D/.ambiente/federation_authority" 8010
avvia op "$D/.ambiente/provider" 8012
avvia rp "$PWD" 8011
for p in 8010 8011 8012; do for i in $(seq 1 30); do curl -s -o /dev/null "http://127.0.0.1:$p/" && break; sleep 1; done; done
(cd "$D/.ambiente/provider" && "$PY" manage.py shell -c "
from spid_cie_oidc.entity.trust_chain_operations import get_or_create_trust_chain
from spid_cie_oidc.entity.settings import HTTPC_PARAMS
from django.conf import settings
tc = get_or_create_trust_chain(subject='http://127.0.0.1:8011', trust_anchor=settings.OIDCFED_TRUST_ANCHORS[0], force=True, httpc_params=HTTPC_PARAMS)
print('catena dell RP presso il provider di prova:', 'ok' if tc and tc.is_active else 'NON valida')" 2>&1 | tail -1)
echo "Servizio SPID/CIE pronto: RP http://127.0.0.1:8011  (provider di prova :8012, trust anchor :8010)."
echo "Credenziali del provider di prova: utente «user», password «oidcuser» (documentate dall'SDK)."
