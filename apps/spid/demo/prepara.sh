#!/usr/bin/env bash
# Prepara l'AMBIENTE DI PROVA ufficiale della federazione SPID/CIE (Trust Anchor + identity provider di prova dell'SDK)
# e il servizio RP di questo progetto. Una tantum. Poi: demo/avvia.sh
# Porte (il sito resta su 8000): Trust Anchor 8010, Relying Party 8011, Identity Provider di prova 8012.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$PWD/.venv/bin/python"
SDK_COMMIT=e83e039091142f6a6a5a6976dfb0aa65733b1667
export MYSQLCLIENT_CFLAGS="${MYSQLCLIENT_CFLAGS:-$(mysql_config --cflags 2>/dev/null || true)}"
export MYSQLCLIENT_LDFLAGS="${MYSQLCLIENT_LDFLAGS:-$(mysql_config --libs 2>/dev/null || true) -L/opt/homebrew/lib}"
export ARCHFLAGS="-arch arm64"

[ -d .venv ] || python3.12 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
# L'SDK pretende Django<5.0 (fuori supporto): si installa senza le sue dipendenze, già elencate in requirements.txt con Django 5.2
.venv/bin/pip install -q --no-deps "git+https://github.com/italia/spid-cie-oidc-django.git@${SDK_COMMIT}"

SDK=demo/.sdk
if [ ! -d "$SDK" ]; then
  git clone -q https://github.com/italia/spid-cie-oidc-django.git "$SDK"
  git -C "$SDK" checkout -q "$SDK_COMMIT"
fi
AMB=demo/.ambiente; rm -rf "$AMB"; mkdir -p "$AMB"
for app in federation_authority provider; do
  cp -R "$SDK/examples/$app" "$AMB/$app"
  ( cd "$AMB/$app" && cp "$app/settingslocal.py.example" "$app/settingslocal.py" && rm -f db.sqlite3
    sed -i '' -e 's/127\.0\.0\.1:8000/127.0.0.1:8010/g' -e 's/127\.0\.0\.1:8001/127.0.0.1:8011/g' -e 's/127\.0\.0\.1:8002/127.0.0.1:8012/g' dumps/example.json "$app/settingslocal.py"
    # cookie con nomi propri: tutti i servizi stanno su 127.0.0.1 e i cookie non distinguono le porte
    printf '\nSESSION_COOKIE_NAME = "demo_%s_sessione"\nCSRF_COOKIE_NAME = "demo_%s_csrf"\n' "$app" "$app" >> "$app/settingslocal.py"
    "$PY" manage.py migrate -v0
    "$PY" manage.py loaddata dumps/example.json >/dev/null )
done
# Configurazione di federazione del NOSTRO RP: chiavi e metadati di prova dell'esempio, con le porte spostate
cp "$SDK/examples/relying_party/dumps/example.json" demo/rp_federazione.json
sed -i '' -e 's/127\.0\.0\.1:8000/127.0.0.1:8010/g' -e 's/127\.0\.0\.1:8001/127.0.0.1:8011/g' -e 's/127\.0\.0\.1:8002/127.0.0.1:8012/g' demo/rp_federazione.json
rm -f db.sqlite3
"$PY" manage.py migrate -v0
"$PY" manage.py loaddata demo/rp_federazione.json >/dev/null
# l'esempio dell'SDK include un amministratore con password nota (admin/oidcadmin): non deve esistere nel nostro servizio
"$PY" manage.py shell -c "from spid_cie_oidc.accounts.models import User; User.objects.all().delete()"
echo "Pronto. Avvia con: apps/spid/demo/avvia.sh"
