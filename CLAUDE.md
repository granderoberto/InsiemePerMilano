# La Nostra Città, Il Nostro Futuro

Progetto d'esame (5° anno informatica): piattaforma web civica per il comitato "Insieme per Milano". I cittadini inseriscono segnalazioni e proposte sui quartieri, la community le sostiene e commenta, i moderatori le fanno avanzare fino alla presentazione ai candidati Sindaco.

Autore: Roberto Grande (GitHub: Bertox0). Lingua del progetto: **italiano** (documenti, nomi di tabelle e colonne, commenti). Termini tecnici standard restano in inglese.

## Stato del progetto

| Materiale richiesto dalla traccia | Stato | File |
|---|---|---|
| 1. Analisi dei requisiti | fatto | `docs/specifiche_utente.md` |
| 2a. Modello ER (Chen) | fatto | `docs/modello_er.pdf`, `docs/modello_er.md` |
| 2b. Schema logico normalizzato | fatto (MySQL 8) | `db/schema.sql`, `db/schema.dbml`, `docs/modello_logico.{md,png,svg}` |
| Database su Aiven (MySQL) | **fatto** (fase 1 completata: migrazioni, 88 NIL, dati demo, verifica) | `db/migrations/`, `db/README.md` |
| 3. Architettura di integrazione IA (schema a blocchi) | **fatto** | `docs/architettura_ia.md`, `docs/architettura_ia.png` (generato da `tools/ia/schema_blocchi.py`) |
| Implementazione della web app | **funzionante e online** (https://la-nostra-citta.onrender.com, Render + Aiven); SPID/CIE con protocollo vero su ambiente di prova; IA simulata | `apps/web/`, `apps/spid/`, `docs/spike_django_spid.md` |
| Modello logico | **fatto** (generato da `db/schema.sql`) | `docs/modello_logico.{md,png,svg}` |
| Messa online | **fatta** (Render, email Gmail) | `docs/produzione.md`, `render.yaml` |

## Struttura

```
PRODUCT.md, DESIGN.md      contesto del prodotto e sistema grafico («segnaletica milanese»)
render.yaml, .env.example  hosting su Render; variabili d'ambiente (senza valori)
docs/
  specifiche_utente.md   specifica funzionale completa (fonte di verità)
  produzione.md, spid_produzione.md, accessibilita.md, handoff.md   messa online ed email; adesione a SPID/CIE; accessibilità; stato del lavoro
  modello_er.md          entità, PK, associazioni con cardinalità, vincoli extra-diagramma
  modello_er.{pdf,svg,png}  diagramma Chen generato
  architettura_sistema.{md,svg,png}  disegno dell'architettura del sistema (generato da tools/architettura/disegna.py)
  modello_logico.{md,svg,png}  modello logico (schema relazionale, dizionario, normalizzazione): generato da db/schema.sql con tools/logico/genera.py
db/
  schema.sql             MySQL 8.0+: tabelle, ENUM, CHECK, trigger, viste, seed (riferimento completo)
  schema.dbml            stesso schema per dbdiagram.io (solo tabelle e relazioni)
  test_vincoli.sql       casi di test dei vincoli (righe "ERRORE ATTESO" devono fallire)
  migrations/            001_schema.sql, 002_dati_riferimento.sql, 003_mfa_segreto.sql, 004_statistiche_attivita.sql, 005_media_contenuti.sql (applicate da tools/db/migrate.sh)
  data/                  GeoJSON sorgente dei NIL e dei Municipi (Comune di Milano, CC BY) + README fonti
  README.md              come ricreare il database da zero
docs/prompt/
  01_database.md         prompt operativo per la fase database su Aiven
apps/web/                sito Django (README con avvio, funzioni e parti simulate)
apps/spid/               servizio SPID/CIE (Relying Party OpenID Connect con SDK) + ponte verso il sito; demo/ = ambiente di prova
tools/db/migrate.sh      applica le migrazioni a un database (idempotente, tabella schema_migrations)
tools/geo/import_quartieri.py   importa gli 88 NIL in `quartieri`
tools/ia/schema_blocchi.py   genera lo schema a blocchi dell'IA (docs/architettura_ia.{svg,png})
tools/architettura/disegna.py   disegna l'architettura del sistema (docs/architettura_sistema.*; icone in icone.py)
tools/demo/genera_foto.py    genera le immagini e i video di esempio dei dati demo (apps/web/static/demo/)
tools/seed/              seed.py (dati demo deterministici) + README con password demo e scelte
tools/requirements.txt   dipendenze Python (venv in tools/.venv, ignorato da git)
.env, certs/ca.pem       credenziali e certificato Aiven: NON versionati (.gitignore)
tools/er/
  gen.py                 DATI del modello ER: dict E (entità→attributi), lista R (associazioni)
  build.py, lay.js, pass2.py, render.py, run.sh   pipeline di disegno
```

## Regole di lavoro

- `docs/specifiche_utente.md` è la fonte di verità. Ogni modifica funzionale parte da lì, poi si propaga a ER e schema.
- **Quattro artefatti da tenere sincronizzati**: `db/schema.sql`, `db/migrations/`, `db/schema.dbml`, `tools/er/gen.py`. Se cambi una tabella o una colonna, aggiorna tutti, rigenera il diagramma ER e il modello logico (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib tools/.venv/bin/python tools/logico/genera.py`, legge `db/schema.sql`, non serve il database). Le modifiche allo schema già applicato su Aiven vanno in una **nuova migrazione** (`003_...sql`), non modificando 001/002.
- Nel modello ER **non compaiono FK**: le rappresentano le associazioni. Le tabelle ponte (`sostegni`, `classificazioni`, `consensi`) nell'ER sono associazioni N:N con attributi. `INVIA` è ternaria.
- `schema.dbml` va incollato nell'editor di dbdiagram.io. `schema.sql` **no**: contiene `DELIMITER` e trigger che il parser DBML rifiuta.
- **Database: MySQL 8** (scelta dell'autore; il servizio Aiven Free è 8.4.8, con `sql_require_primary_key=ON` e `log_bin_trust_function_creators=ON`: i trigger si creano senza privilegi extra). Convenzioni: InnoDB, utf8mb4, DATETIME(3) sempre in UTC (`SET time_zone = '+00:00'`), ENUM inline. Lo schema va eseguito con il client `mysql` (serve `DELIMITER`), non con un driver che invia una query alla volta.
- Limiti MySQL già gestiti: niente indici parziali (una copertina per segnalazione con colonna generata `copertina_di` + UNIQUE); niente CHECK su colonne AUTO_INCREMENT; niente `ON DELETE CASCADE` su `media.id_segnalazione` perché incompatibile con la colonna generata (le segnalazioni si eliminano solo logicamente con `eliminata_il`).
- Nomi: `snake_case`, tabelle al plurale nello SQL (`utenti`), entità al singolare maiuscolo nell'ER (`UTENTE`).

## Comandi

```bash
# Credenziali: .env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME) + certs/ca.pem. Mai stampare la password.
# Ambiente Python (una tantum)
python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt

# Migrazioni (idempotente) su un database Aiven
tools/db/migrate.sh la_nostra_citta_test        # database di test (per prove distruttive)
tools/db/migrate.sh defaultdb                   # database principale

# Sito web (vedi apps/web/README.md)
cd apps/web && .venv/bin/python manage.py runserver   # http://127.0.0.1:8000

# Servizio SPID/CIE (ambiente di prova: trust anchor :8010, RP :8011, gestore di prova :8012). Vedi apps/spid/README.md
apps/spid/demo/prepara.sh   # una tantum
apps/spid/demo/avvia.sh     # ogni volta (ferma.sh per fermare). In .env: SPID_BRIDGE_SECRET e SPID_SERVIZIO_URL

# Quartieri (88 NIL) e dati demo
tools/.venv/bin/python tools/geo/import_quartieri.py defaultdb
tools/.venv/bin/python tools/seed/seed.py defaultdb [--oggi AAAA-MM-GG]   # DISTRUTTIVO sulle tabelle non di riferimento

# Test dei vincoli: SOLO sul database di test, dopo migrate.sh (non sul principale)
mysql --force la_nostra_citta_test < db/test_vincoli.sql   # devono fallire solo le righe ERRORE ATTESO (10)

# Validare il DBML
npm i @dbml/core && node -e "const{Parser}=require('@dbml/core');new Parser().parse(require('fs').readFileSync('db/schema.dbml','utf8'),'dbml');console.log('ok')"

# Rigenerare il diagramma ER (dopo aver modificato tools/er/gen.py). Su macOS serve la libreria Cairo (brew install cairo):
# se l'ultimo passo fallisce con "no library called cairo", eseguire il blocco cairosvg a mano con DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
pip install cairosvg && tools/er/run.sh
```

## Decisioni di dominio già prese

**Ruoli:** `utente`, `moderatore`, `amministratore`. **Stato account** separato dal ruolo: `in_attesa_verifica`, `attivo`, `sospeso`, `eliminato`. Il visitatore non registrato legge i contenuti pubblici ma non interagisce.

**Accesso:** SPID/CIE (identità già certificata, account subito attivo, si salva solo l'hash SHA-256 del codice fiscale per garantire un account per persona) oppure credenziali: l'account diventa attivo con la conferma dell'email. La **verifica IA del documento è facoltativa alla registrazione ma necessaria per pubblicare segnalazioni** (`Utente.identita_verificata`: SPID/CIE, verifica approvata dall'IA o da un moderatore, oppure ruolo moderatore/amministratore). Chi non è verificato legge, sostiene e commenta; se prova a pubblicare viene portato a `/profilo/verifica/`. Il consenso biometrico (art. 9) si chiede solo all'avvio della verifica.

**Verifica IA del documento:** OCR, corrispondenza dati, validità, autenticità, confronto selfie/foto documento. Oggi **vera e locale** (`core/services/ia/documento_reale.py`: Tesseract, MRZ, OpenCV YuNet+SFace; modelli in `apps/web/modelli/` non versionati, `sh apps/web/modelli/scarica.sh`); l'autenticità è solo coerenza degli elementi (i dubbi vanno al moderatore); senza Tesseract/modelli si usa il simulato. Punteggio 0-100: ≥85 approvata, 50-84 da rivedere (coda moderatore), <50 rifiutata. Max 3 tentativi, revisione umana sempre richiedibile. Immagini cancellate dopo la verifica.

**Normative in registrazione:** informativa GDPR art. 13, informativa IA con diritto a revisione umana (art. 22), termini d'uso, cookie policy, età minima 14 anni. Si registra la versione accettata; nuova versione = nuova accettazione.

**Segnalazione:** tipo (proposta/problema), titolo ≤100, descrizione 30-2000, una o più categorie (suggerite dall'IA con confidenza), posizione dentro il Comune di Milano da GPS / mappa / indirizzo, quartiere ricavato dalla posizione, 1-10 media (foto JPG/PNG/HEIC ≤10 MB, video MP4/MOV ≤60 s e ≤50 MB). Metadati EXIF rimossi prima della pubblicazione. Max 5 segnalazioni/giorno. Modificabile dall'autore solo negli stati 1-2; ogni modifica va nel log.

**Ciclo di vita:** 1 Ricevuta → 2 In attesa → 3 Approvata | 4 Rifiutata; 3 → 5 Presentata ai candidati. 4 e 5 finali. Pubblici solo 3 e 5. Transizioni in tabella `transizioni_ammesse`, imposte da trigger.

**Moderazione IA:** NLP su testo e commenti; classificatore visivo per contenuti sessuali/violenti (sui video: fotogrammi campione); OCR sulle immagini con il testo estratto passato al filtro NLP; coerenza immagine/testo. Esito `ok` / `dubbio` (coda moderatore) / `bloccato` (autore avvisato, può chiedere revisione).

**Community:** un sostegno per utente per segnalazione, mai sulla propria; commenti con risposte (stessa segnalazione del padre); condivisione via link.

**Statistiche:** classifiche nominative pubbliche solo per utenti con `profilo_pubblico = true`; statistiche complete (più post, più interazioni, più commenti, più attivi negli ultimi 30 giorni) nella dashboard admin. Viste: `v_classifica_segnalazioni`, `v_statistiche_utenti`, `v_classifica_utenti_pubblica`.

**Log:** `log_attivita` append-only (trigger blocca UPDATE/DELETE), consultabile solo dall'amministratore. Il pubblico vede solo la cronologia stati. Il reset dei dati demo usa `SET FOREIGN_KEY_CHECKS=0; TRUNCATE ...`, perché TRUNCATE non attiva i trigger.

## Vincoli NON imposti dal database (vanno nell'applicazione)

- Almeno un media per segnalazione (inserire segnalazione + media nella stessa transazione).
- Limite di 5 segnalazioni al giorno.
- Confine preciso di Milano: il DB ha solo un rettangolo lat 45.38-45.54 / lon 9.04-9.28; il controllo esatto usa il poligono GeoJSON in `quartieri.confine`.
- Permessi per ruolo (chi può cambiare stato, nascondere, sospendere, cambiare ruoli).
- Limite di 3 tentativi di verifica è nel DB (CHECK), ma la logica "puoi riprovare" è applicativa.

## Stack applicativo (deciso 2026-09-29)

- **App principale: Django 5.2 LTS** (supporto di sicurezza fino al 2028-04-30), Python 3.12+, MySQL 8.4 su Aiven con `mysqlclient`, template server-side + HTMX + Leaflet.
- **SPID/CIE: realizzato** in `apps/spid/` (SDK `spid-cie-oidc-django` isolato in un servizio separato, con database proprio). Il sito lo raggiunge con un token firmato (segreto condiviso, 120 s, monouso, legato al browser che ha iniziato l'accesso); il codice fiscale si salva solo come hash SHA-256. L'SDK dichiara `Django<5.0` (4.2 fuori supporto): gira su Django 5.2 con l'SDK installato senza dipendenze; su MySQL servono `max_length` 1024 → 700 nelle sue migrazioni. Oggi funziona con la federazione di **prova** dell'SDK (protocollo e codice veri, gestore di identità finto). L'uso reale richiede l'adesione di un ente: README di `apps/spid` («Passare alla produzione»). Prove: `docs/spike_django_spid.md`, `apps/web/smoke/spid.py` e `spid_e2e.py`.
- Fallback: Node.js (SDK solo RP) se l'RP non regge su un ambiente di test SPID/CIE vero.
- Accesso reale a SPID/CIE: serve un ente che aderisca come Fornitore di Servizi (probabilmente la scuola) o un soggetto aggregatore; non ancora avviato.

### Regola di convivenza migrazioni SQL / migrazioni Django

1. Le migrazioni SQL (`db/migrations/`, `tools/db/migrate.sh`) sono l'unica fonte dello schema del dominio. I modelli Django sulle tabelle del dominio sono sempre `managed = False`: Django non le crea né le modifica.
2. Chi cambia una tabella con una nuova migrazione SQL aggiorna nello stesso commit il modello Django. Per i modelli `managed = False` Django **non** rileva né registra le modifiche ai campi: `makemigrations` non produce nulla e lo stato nelle migrazioni di Django resta indietro senza conseguenze. La fonte di verità sono il file SQL e il codice del modello: si verificano a mano (e con gli script in `apps/web/smoke/`).
3. Le tabelle di Django (`django_*`, `auth_*`, `<app>_*`) le crea solo `manage.py migrate`; le migrazioni SQL non le citano e non compaiono in `schema_migrations`.
4. Ordine di deploy: prima `tools/db/migrate.sh`, poi `manage.py migrate` (`django_admin_log` ha una FK verso `utenti`).
5. Un solo progetto Django per database (si condividono `django_migrations`, `django_content_type`, `auth_*`): il servizio SPID/CIE usa un database o uno schema separato.
6. Django non ha un prefisso globale: nessuna tabella del dominio può chiamarsi `django_*` o `auth_*`; i modelli del dominio hanno `db_table` esplicito.
7. `DEFAULT_AUTO_FIELD = "django.db.models.AutoField"` e `id` dichiarato esplicitamente sui modelli di tabelle esistenti (`AutoField` per INT, `SmallAutoField` per SMALLINT): una FK BIGINT verso `utenti.id` INT fallisce (errore 3780).
8. Nei modelli: booleani come `BooleanField`, ENUM come `CharField` con `choices`, default del DB con `db_default`, colonne generate (`copertina_di`) mai scrivibili.
9. Errori del DB: `OperationalError` con errno 1644 = regola dei trigger (da tradurre in messaggio all'utente); `IntegrityError` 3819 = CHECK violato.
10. Le migrazioni Django su MySQL non sono atomiche: se una fallisce a metà, ripulire le tabelle create prima di riprovare. Provarle prima su `la_nostra_citta_test`.
11. Utente di autenticazione: modello personalizzato su `utenti` (`managed=False`, `password` con `db_column="password_hash"`, `last_login = None`, permessi derivati da `ruolo`), backend che verifica gli hash bcrypt con `bcrypt.checkpw`. Niente `auth_user`.

## Autenticazione a due fattori (TOTP)

- Solo per chi accede con credenziali (con SPID/CIE la sicurezza è del gestore di identità). App di autenticazione standard (RFC 6238), `pyotp`.
- `utenti.mfa_segreto` (migrazione 003) contiene il segreto **cifrato** (Fernet, chiave derivata da `SECRET_KEY`): se cambia `SECRET_KEY` i segreti non si leggono più e l'amministratore deve azzerare la 2FA degli utenti. `CHECK`: il flag acceso richiede un segreto.
- Accesso in due passaggi: dopo la password l'utente non è ancora autenticato; ha 5 minuti per il codice; 5 errori bloccano l'account 15 minuti.
- Recupero: se l'utente perde il telefono, l'amministratore azzera la 2FA dalla scheda utente (motivo obbligatorio, finisce nel registro). Non ci sono codici di recupero.
- I dati demo hanno la 2FA spenta (non esistono segreti demo).

## Stato del database (fase 1 conclusa)

Su Aiven ci sono `defaultdb` (principale, popolato; usato dal sito online) e `la_nostra_citta_test` (prove distruttive). 22 tabelle (inclusa la tecnica `media_contenuti`), 7 trigger, 3 viste, circa 5 MB più i file in `media_contenuti`. Dati demo: 154 utenti, 300 segnalazioni, 1916 sostegni, 397 commenti, 5095 righe di log; password demo `DemoMilano2026!` (vedi `tools/seed/README.md`).

Note sui dati:
- `quartieri` = 88 NIL (Comune di Milano, CC BY). `quartieri.id` = `ID_NIL` della fonte. Il `municipio` è ricavato per maggiore sovrapposizione: per 16 NIL che attraversano più Municipi è un'approssimazione.
- `v_statistiche_utenti` conta come attività solo `creazione`/`commento`/`sostegno` su `segnalazioni`, `commenti`, `sostegni` (migrazione 004).
- Per `confine` si è valutato il tipo spaziale (`POLYGON SRID 4326` + SPATIAL): funziona con `ST_Contains(geom, ST_SRID(POINT(lon, lat), 4326))`, ma 2 poligoni (`CASCINA MERLATA`, `ASSIANO`) risultano invalidi per MySQL. Decisione rinviata; oggi il controllo punto-in-poligono va fatto nell'applicazione.
- Il servizio Free si spegne se inattivo: se la connessione fallisce, riaccenderlo dalla console Aiven.

## File caricati (foto e video)

Salvati su disco in `MEDIA_ROOT` (`DATA_DIR/media`), ridotti (lato massimo 2400 px), con EXIF e profilo colore tolti; i video senza metadati (serve `ffmpeg`/`ffprobe`, installato nel `Dockerfile`). Ogni file è copiato anche nel database, a pezzi da 4 MB, nella tabella tecnica `media_contenuti` (migrazione 005): se il disco dell'hosting è temporaneo (piano gratuito di Render) `/media/...` ripristina il file dal database. HEIC (iPhone) → JPEG. Le foto e i video dei **dati demo** hanno percorsi fittizi (`media/demo/<id>`): la vista `media_file` mostra immagini e video di esempio disegnati (`apps/web/static/demo/`, generati da `tools/demo/genera_foto.py`, non sono fotografie reali). Prova: `apps/web/smoke/media.py`.

## Prove automatiche e email

Le prove in `apps/web/smoke/` impostano `LNC_PROVE`: usano `locmem` (o il finto SMTP locale di `posta.py`) e **mai** Gmail, anche se `.env` ha le credenziali. In più i backend reali (`core/email_backend.py`, `core/email_smtp.py`) non inviano a domini riservati (`example.*`, `.invalid`, `.test`…). Il 2026-10-19 alcune prove avevano mandato email vere a indirizzi `@example.org` prima di questa protezione.

## Produzione

Guide: `docs/produzione.md` (hosting a contenitori, scelto Render/Railway al posto di Vercel; email con Brevo; `render.yaml`, `apps/web/Dockerfile`, `.env.example`) e `docs/spid_produzione.md` (adesione di un ente, bozza di richiesta). Il sito legge `DJANGO_DEBUG`, `DJANGO_SECRET_KEY` (obbligatoria con DEBUG=0), `DATA_DIR` (disco persistente per media e archivio verifica), `DB_CA_PEM`. Comando `manage.py prova_email`; controllo di stato `/salute/`. Docker non è stato provato in locale.

## Prossimi passi suggeriti

1. **Sicurezza**: gli account demo (anche amministratore e moderatori) hanno una password pubblica e sono online; cambiarla o usare un database pulito. Cambiare la password di `avnadmin` su Aiven (condivisa in chiaro in chat).
2. Provare online registrazione, email (Gmail) e caricamento di foto e video; il `Dockerfile` non è stato provato in locale.
3. Adesione di un ente a SPID/CIE (`docs/spid_produzione.md`).
4. Sostituire i controlli IA simulati con servizi veri (`docs/architettura_ia.md`, «Passi per l'IA vera»).
5. Accessibilità: prove con screen reader e dispositivi reali (`docs/accessibilita.md`).
6. Colonna spaziale per `confine`; normative con i testi veri del comitato.
7. Aiven Free si spegne se inattivo: se il sito non carica i dati, riaccenderlo.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
