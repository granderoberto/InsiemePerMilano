# Sito web (Django 5.2)

Portale civico "La Nostra Città, Il Nostro Futuro". Template server-side, Leaflet per le mappe, nessuna build front-end.

## Avvio in locale

Servono `.env` e `certs/ca.pem` nella radice del repository (vedi `db/README.md`) e il servizio Aiven acceso.

```bash
cd apps/web
python3 -m venv .venv
# mysqlclient su macOS: serve il client MySQL di Homebrew
export MYSQLCLIENT_CFLAGS="$(mysql_config --cflags)" MYSQLCLIENT_LDFLAGS="$(mysql_config --libs) -L/opt/homebrew/lib -L$(brew --prefix openssl@3)/lib" ARCHFLAGS="-arch arm64"
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate        # crea solo le tabelle django_* e auth_*; il dominio è già nel DB
.venv/bin/python manage.py runserver      # http://127.0.0.1:8000
```

Database usato: `DJANGO_DB_NAME` (default `la_nostra_citta_test`, stessi dati demo del principale). Password demo di tutti gli utenti con credenziali: `DemoMilano2026!` (es. un moderatore: vedi `utenti` con `ruolo='moderatore'`).

## Funzioni

| Area | Cosa fa |
|---|---|
| Pubblico | elenco con filtri (parola chiave, quartiere, categoria, stato, tipo, ordine), mappa, dettaglio con cronologia stati, commenti e risposte, link condivisibile, statistiche e classifiche |
| Utente | registrazione (con consensi), accesso (blocco 15 min dopo 5 errori), nuova segnalazione (mappa, indirizzo, GPS, foto/video, categorie suggerite, EXIF rimosso, max 5 al giorno), sostegno e ritiro, commenti, profilo, notifiche |
| Moderatore (`/moderazione/`) | code: in attesa, contenuti segnalati dall'IA, da presentare (per sostegni), verifiche d'identità da rivedere; approva, rifiuta con motivo, presenta ai candidati, nascondi |

## Simulato (da sostituire)

- **Verifica del documento IA** in registrazione: approvata in automatico (`portale/views.py`, `registrati`).
- **Controlli IA** su testi, categorie, coerenza: `core/services/ia_simulata.py` (stessa interfaccia dei servizi veri).
- **Accesso SPID/CIE**: form `/accedi/spid/` che riproduce i dati dell'identity provider; sarà il servizio con l'SDK `spid-cie-oidc-django`.
- Non c'è ancora: invio email, 2FA, modifica/eliminazione della propria segnalazione, richieste di revisione dell'autore, dashboard amministratore (c'è `/gestione/`, l'admin di Django), esportazione CSV.

## Struttura

```
config/       impostazioni e URL
core/         modelli del dominio (managed=False), accesso, servizi (geo, stati, log, media, ia_simulata), query condivise
portale/      viste pubbliche e utente, form, template tag
moderazione/  area moderatore
templates/, static/   HTML, CSS, JavaScript (mappa.js, posizione.js)
smoke/        controlli di prova (scrivono nel DB di test: lanciarli solo lì)
```

Regole sullo schema: vedi "Regola di convivenza" in `CLAUDE.md`. I modelli rispecchiano `db/migrations/*.sql`.

## Controlli

```bash
.venv/bin/python manage.py check
.venv/bin/python smoke/letture.py      # GET di tutte le pagine, anche con utente e moderatore
.venv/bin/python smoke/scrittura.py    # azioni: sostegni, commenti, nuova segnalazione, moderazione, registrazione
# poi ripristinare i dati demo: tools/.venv/bin/python tools/seed/seed.py la_nostra_citta_test
```
