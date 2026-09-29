# Fase 1: database MySQL su Aiven

Leggi CLAUDE.md, docs/specifiche_utente.md e db/schema.sql prima di iniziare.

## Obiettivo

Creare, migrare e popolare il database MySQL 8 su Aiven (piano Free).
NON scegliere né installare lo stack applicativo: verrà deciso in una fase successiva.

## Vincoli

- Aiven Free: 1 GB di disco, un solo nodo, niente connection pooling. Tieni il database leggero (obiettivo < 100 MB) e non salvare file multimediali nel database, solo percorsi.
- Il servizio Free si spegne se resta inattivo: se la connessione fallisce, chiedimi di riaccenderlo dalla console prima di fare altre ipotesi.
- Credenziali:
  - Leggile solo da `.env`, con le variabili `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
  - Usa il certificato `certs/ca.pem` con `--ssl-mode=VERIFY_IDENTITY`.
  - Non stampare mai la password e non scriverla in file versionati; per il client mysql usa un file `--defaults-extra-file` temporaneo con permessi 600, fuori dalla repo o in .gitignore.
  - Prima di qualsiasi commit verifica che `.env` e `certs/` siano in `.gitignore`.
- Esegui lo schema con il client `mysql`, perché usa `DELIMITER` per i trigger.
- Lavora uno step alla volta. Alla fine di ogni step mostrami cosa hai fatto e il risultato delle verifiche, poi fermati e aspetta la mia conferma.
- Un commit per step, messaggi in italiano.
- Se una scelta non è coperta dalla specifica, proponila e aspetta conferma: non inventare.

## Step 1: connessione

- Verifica la connessione e riporta:
  - `SELECT VERSION()`;
  - i valori di `sql_require_primary_key`, `log_bin_trust_function_creators` e `time_zone`.
- Crea nello stesso servizio un secondo database `la_nostra_citta_test` (utf8mb4) per i test distruttivi.

Se la creazione dei trigger fallisce con errore 1419 (SUPER privilege / binary logging), fermati: mi dirai tu se attivare `log_bin_trust_function_creators` dalla Advanced configuration del servizio su Aiven. Non cercare workaround che eliminino i trigger.

## Step 2: migrazioni

- Riorganizza lo schema in `db/migrations/`:
  - `001_schema.sql`: tutto `db/schema.sql` tranne i dati iniziali;
  - `002_dati_riferimento.sql`: stati, transizioni_ammesse, categorie.
- Crea `tools/db/migrate.sh`:
  - idempotente;
  - con una tabella `schema_migrations` dotata di PRIMARY KEY, perché Aiven può richiederla su ogni tabella;
  - database di destinazione passato come parametro.
- Nota: MySQL fa commit implicito sulle istruzioni DDL, quindi una migrazione fallita a metà non si annulla da sola. Lo script deve fermarsi al primo errore, registrare la migrazione solo se è andata a buon fine, e le migrazioni vanno scritte in modo da poter essere riapplicate su un database pulito.
- Applica prima su `la_nostra_citta_test` ed esegui `mysql --force la_nostra_citta_test < db/test_vincoli.sql`. Devono fallire esattamente le 10 righe marcate ERRORE ATTESO, nessun'altra.
- Poi applica sul database principale.
- Se cambi lo schema, tieni sincronizzati `db/schema.dbml` e `tools/er/gen.py`.

## Step 3: quartieri di Milano

- Popola `quartieri` con i NIL (Nuclei d'Identità Locale) del Comune di Milano:
  - nome;
  - municipio;
  - confine GeoJSON.
- Usa gli open data ufficiali del Comune. Verifica fonte e licenza, salva il file sorgente in `db/data/` con un README che citi la fonte, e scrivi lo script di import.
- Se la fonte non è raggiungibile fermati e dimmelo: non inventare confini.
- Valuta se convertire `quartieri.confine` da JSON a tipo spaziale MySQL (`POLYGON`/`MULTIPOLYGON` con SRID 4326 e indice SPATIAL). Servirebbe a ricavare il quartiere dalla posizione con `ST_Contains`. Proponilo con pro e contro, non applicarlo senza conferma.

## Step 4: dati demo

Script in `tools/seed/` (Python, PyMySQL, Faker it_IT).

Requisiti dello script:
- deterministico, con seed fisso;
- ricreabile: il reset esegue `SET FOREIGN_KEY_CHECKS=0`, poi `TRUNCATE` delle tabelle non di riferimento, poi `SET FOREIGN_KEY_CHECKS=1`. Usa TRUNCATE perché non attiva il trigger che blocca i DELETE su `log_attivita`.

Contenuto:
- Utenti:
  - 1 amministratore, 3 moderatori, circa 150 utenti;
  - mix SPID/CIE/credenziali e stati account vari;
  - età da 14 anni in su, con una quota consistente tra 14 e 25;
  - circa il 40% con profilo pubblico.
- Verifiche d'identità per gli utenti con credenziali: punteggi coerenti con l'esito, alcuni casi da_rivedere e revisionati.
- Documenti normativi versione 1, con testi segnaposto dichiarati come tali, e consensi coerenti con il metodo di registrazione.
- 5 candidati fittizi.
- Circa 300 segnalazioni:
  - posizioni dentro il confine del quartiere assegnato;
  - da 1 a 4 media ciascuna, con percorsi fittizi `media/demo/<id>.jpg` e una sola copertina;
  - classificazioni con origine ia e utente.
- Storia degli stati inserita SOLO tramite `cambi_stato`, mai con UPDATE diretto di `id_stato`. Distribuzione realistica tra tutti gli stati.
- Sostegni:
  - distribuzione a coda lunga (poche segnalazioni molto sostenute);
  - inseriti solo dopo l'approvazione;
  - mai sulla propria segnalazione.
- Commenti con risposte, alcuni nascosti con motivo.
- Alcune sospensioni, richieste di revisione, notifiche e preferenze di notifica.
- `log_attivita` coerente con tutte le azioni inserite.

Regole sui dati:
- Timestamp in UTC e in ordine cronologico coerente: registrazione, poi segnalazione, poi cambi di stato, poi sostegni e commenti.
- Password demo unica, hashata con bcrypt, documentata in `tools/seed/README.md`.
- Codici fiscali fittizi, salvati solo come hash SHA-256.
- Nessun dato reale di persone.
- Inserimenti a blocchi (executemany) per restare veloci sulla connessione remota.

## Step 5: verifica

Sul database principale riporta:
- conteggio righe per tabella;
- output delle tre viste di statistica (prime 10 righe);
- conferma che nessuna segnalazione sia senza media;
- conferma che nessun sostegno sia dell'autore o su segnalazioni non pubbliche;
- spazio occupato, calcolato da `information_schema.TABLES`.

## Step 6: documentazione

- Aggiorna CLAUDE.md con:
  - comandi di migrazione e seed;
  - nuova struttura delle cartelle;
  - stato della fase.
- Aggiungi `db/README.md` con le istruzioni per ricreare il database da zero.
