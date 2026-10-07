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
| Utente | registrazione (con consensi; l'account si attiva dopo la conferma dell'email), accesso (blocco 15 min dopo 5 errori), recupero password, cambio email con nuova conferma, verifica in due passaggi (app di autenticazione), preferenze di notifica, accettazione delle nuove versioni dei documenti normativi, nuova segnalazione (mappa, indirizzo, GPS, foto/video, categorie suggerite, EXIF rimosso, max 5 al giorno; prima dell'invio propone le **segnalazioni simili in zona** da sostenere), sostegno e ritiro, commenti, profilo, notifiche |
| Autore | modifica della propria segnalazione negli stati Ricevuta e In attesa (versione precedente nel log, nuovi controlli), eliminazione logica, richiesta di revisione se l'IA l'ha bloccata, richiesta di revisione di una verifica rifiutata |
| Moderatore (`/moderazione/`) | code: richieste di revisione, in attesa, contenuti segnalati dall'IA, da presentare (per sostegni), verifiche d'identità da rivedere; approva, rifiuta con motivo, presenta ai candidati, nascondi, sospendi e riattiva account |
| Amministratore (`/amministrazione/`) | elenco utenti con ricerca e filtri, scheda utente (verifiche, consensi, cronologia), correzione dati con motivo, cambio ruolo, azzeramento della 2FA, sospensione a tempo con scadenza automatica, registro delle attività con filtri, statistiche complete con esportazione CSV, categorie, nuove versioni dei testi normativi (gli utenti devono riaccettarle) |

## Simulato (da sostituire)

- **Verifica del documento IA** in registrazione: documento (fronte e retro) e selfie dal vivo si caricano davvero (controllo dei byte, max 5 MB, JPG/PNG/PDF), passano da un archivio temporaneo cifrato e vengono cancellati a fine verifica; fino a 3 tentativi. Il controllo è **simulato** (`core/services/verifica_documento.py`): un documento con il lato corto sotto 600 px va in revisione del moderatore, un selfie sotto 240 px viene rifiutato.
- **Controlli IA** su testi, categorie, coerenza: `core/services/ia_simulata.py` (stessa interfaccia dei servizi veri).
- **Accesso SPID/CIE**: vero protocollo OpenID Connect con federazione tramite il servizio `apps/spid` (README dedicato), oggi sull'**ambiente di prova** ufficiale (gestore di identità finto). Per l'uso reale serve l'adesione di un ente.
- **Email**: senza `EMAIL_HOST` in `.env` escono sulla console del server e il link compare a schermo (solo sviluppo). Con un server SMTP vero si configurano in `.env`: `EMAIL_HOST`, `EMAIL_PORT` (587 con STARTTLS, oppure 465 con `EMAIL_SSL=1`), `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM` e `SITE_URL` (l'indirizzo pubblico del sito, usato nei link). Il link non compare mai a schermo con SMTP vero. Limiti: 3 email all'ora per indirizzo e tipo, 10 richieste di recupero all'ora per IP.
- **Password** (`core/services/password.py`): almeno 8 caratteri con maiuscola, numero e simbolo (specifica), al massimo 72 byte (limite di bcrypt), non una password comune nemmeno con sostituzioni (`P4ssw0rd!`), non basata su nome, cognome o email, niente sequenze (`12345678A!`). Il profilo permette di cambiarla (serve quella attuale; le altre sessioni si chiudono e arriva un avviso via email).
- Recupero password: link a scadenza (2 ore) e monouso, risposta identica se l'indirizzo non esiste, avviso di sicurezza dopo il cambio.
- Eliminazione dell'account (profilo → «Elimina il mio account»): si cancellano i dati personali e le notifiche; segnalazioni, commenti, sostegni e registro restano come «Utente eliminato». L'ultimo amministratore non può eliminarsi.
- Accessibilità: vedi `docs/accessibilita.md`.
- Non c'è ancora: richiesta di revisione per i commenti bloccati, eliminazione dell'account, esportazione delle statistiche personali. `/gestione/` è l'admin standard di Django (non usato).

## Struttura

```
config/       impostazioni e URL
core/         modelli del dominio (managed=False), accesso, servizi (geo, stati, log, media, ia_simulata), query condivise
portale/      viste pubbliche e utente, form, template tag
moderazione/  area moderatore
templates/, static/   HTML, CSS, JavaScript (mappa.js, posizione.js)
smoke/        controlli di prova (letture, scrittura, autore, amministrazione, account, 2FA, simili) (scrivono nel DB di test: lanciarli solo lì)
```

Regole sullo schema: vedi "Regola di convivenza" in `CLAUDE.md`. I modelli rispecchiano `db/migrations/*.sql`.

## Controlli

```bash
.venv/bin/python manage.py check
.venv/bin/python smoke/letture.py      # GET di tutte le pagine, anche con utente e moderatore
.venv/bin/python smoke/scrittura.py    # azioni: sostegni, commenti, nuova segnalazione, moderazione, registrazione
.venv/bin/python smoke/autore.py       # modifica, eliminazione, richieste di revisione
.venv/bin/python smoke/amministrazione.py   # elenco utenti, ruoli, sospensioni, normative, CSV (lento: molte chiamate remote)
# .venv/bin/python smoke/account.py    # recupero password, cambio email, preferenze, attivazione
# .venv/bin/python smoke/mfa.py        # 2FA: attivazione, accesso in due passaggi, blocco, azzeramento
# .venv/bin/python smoke/simili.py     # segnalazioni simili in zona e sostegno diretto
# .venv/bin/python smoke/posta.py      # email via SMTP vero (locale), password, recupero, limiti (serve requirements-dev.txt)
# .venv/bin/python smoke/verifica.py   # documento e selfie: file, esiti, tentativi, cancellazione
# .venv/bin/python smoke/spid.py       # sicurezza del ritorno SPID/CIE (e reindirizzamenti)
# .venv/bin/python smoke/spid_e2e.py   # SPID/CIE di punta a punta (servizio acceso: apps/spid/demo/avvia.sh)
# I controlli creano utenti (email con suffisso casuale): dopo averli lanciati si ripristinano i dati demo.
# .venv/bin/python smoke/eliminazione.py   # eliminazione dell'account (dati anonimizzati, contenuti conservati)
# poi ripristinare i dati demo: tools/.venv/bin/python tools/seed/seed.py la_nostra_citta_test
```
