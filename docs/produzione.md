# Messa in produzione

Obiettivo: sito raggiungibile su un dominio in HTTPS, con email vere, database su Aiven e file caricati su disco persistente.
Lo stato SPID/CIE reale è in [`spid_produzione.md`](spid_produzione.md) (richiede un ente).

## Perché non Vercel

Vercel esegue funzioni «serverless»: senza disco persistente, con processi di breve durata. Questo sito salva su disco foto e video
(`MEDIA_ROOT`) e un archivio temporaneo cifrato per la verifica del documento, tiene connessioni MySQL e ha un secondo servizio
(SPID/CIE) con database proprio. Su Vercel servirebbero: archiviazione esterna dei file (S3/R2), riscrittura dei percorsi dei media,
un host diverso per il servizio SPID. Si può fare, ma è più lavoro e più fragile. Soluzione scelta: **hosting a contenitori**
(Render o Railway) con il `Dockerfile` di `apps/web/`.

## Passi rapidi (Render, piano gratuito)

1. Render → **New → Blueprint** → scegli il repository `granderoberto/InsiemePerMilano`.
2. Nel pannello del servizio, *Environment*: incolla il contenuto di `.env.produzione` (file locale, non versionato; generato con la chiave segreta e i valori del database).
3. Su Render host e origine CSRF si ricavano da soli (`RENDER_EXTERNAL_HOSTNAME`); `SITE_URL` serve per i link nelle email. Con un dominio tuo imposta anche `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_ORIGINS`. (Prima versione: copia l'indirizzo (es. `https://la-nostra-citta.onrender.com`) e imposta `DJANGO_ALLOWED_HOSTS` (solo il nome host), `DJANGO_CSRF_ORIGINS` (con `https://`) e `SITE_URL`; poi *Manual Deploy*.)
4. Apri `/salute/?db=1`: deve rispondere `ok`.

## 1. Database (Aiven)

Già pronto (`defaultdb`). Prima del primo avvio in produzione:

```bash
tools/db/migrate.sh defaultdb                                   # schema del dominio (001-004)
cd apps/web && DJANGO_DB_NAME=defaultdb .venv/bin/python manage.py migrate   # tabelle di Django (se non già fatto)
```

Serve il testo del certificato CA di Aiven (`certs/ca.pem`) nella variabile `DB_CA_PEM` (a capo come `\n`).
Cambiare la password di `avnadmin` e creare un utente applicativo con soli i permessi sul database.

## 2. Hosting (Render, con `render.yaml`)

1. Crea un account su Render e collega il repository GitHub: **New → Blueprint** (legge `render.yaml`).
2. Compila le variabili marcate `sync: false` (vedi `.env.example`): `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_ORIGINS`, `SITE_URL`, `DB_*`, `DB_CA_PEM`, `EMAIL_*`.
3. `render.yaml` usa il **piano gratuito** (nessun costo, nessun disco: le foto caricate si perdono a ogni riavvio e il sito si addormenta dopo un po' di inattività, la prima richiesta è lenta). Per conservare i file: `plan: starter` e decommentare il blocco `disk`. Il disco persistente (`/data`, variabile `DATA_DIR`) **non esiste nel piano gratuito**: serve un piano a pagamento (verificare prezzi sul sito). Senza disco, i file sul disco spariscono a ogni riavvio, ma sono anche copiati nel database (tabella `media_contenuti`) e si ripristinano da lì alla prima richiesta.
4. `DJANGO_SECRET_KEY` viene generata alla creazione e **non deve cambiare**: da essa derivano le chiavi che cifrano i segreti 2FA e l'archivio temporaneo.
5. Dominio: *Settings → Custom Domains* e record DNS indicati da Render; HTTPS è automatico.
6. Controllo di stato: `/salute/` (con `?db=1` verifica anche il database).

Railway funziona allo stesso modo con il `Dockerfile` e un *Volume* montato su `/data`.
Il `Dockerfile` non è stato provato in questo ambiente (Docker non installato): al primo deploy controllare i log di build.

## 3. Email (Brevo)

1. Registrati su Brevo, **SMTP & API → SMTP**: ricavi server (`smtp-relay.brevo.com`), porta 587, login e chiave SMTP.
2. Metti in variabili d'ambiente: `EMAIL_HOST`, `EMAIL_PORT=587`, `EMAIL_TLS=1`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM`.
3. Verifica il **mittente o il dominio** in Brevo e, per un dominio tuo, aggiungi i record **SPF e DKIM** (e DMARC) indicati: senza, i messaggi finiscono nello spam o vengono rifiutati.
4. Prova: `python manage.py prova_email tuo@indirizzo.it` (sull'hosting dalla shell del servizio).
5. Con `EMAIL_HOST` impostato il link di conferma/recupero non compare più a schermo: arriva solo per email (già implementato).

I limiti del piano gratuito di Brevo vanno verificati sul sito del fornitore.

### Su Render gratuito: Gmail API (HTTPS)

**Render nel piano gratuito blocca l'SMTP in uscita** (porte 25, 465 e 587): con l'SMTP di Gmail il sito dice «non siamo riusciti a spedire l'email di conferma». Si risolve inviando con l'**API di Gmail** (porta 443), gratis e senza dominio proprio. Il codice è `core/email_backend.py`; basta compilare tre variabili.

1. Vai su <https://console.cloud.google.com> con l'account Gmail e crea un **progetto** (nome libero, per esempio «La Nostra Citta»).
2. **API e servizi → Libreria → Gmail API → Abilita**.
3. **Schermata di consenso OAuth** (Google Auth platform): tipo di utente *Esterno*; nome app, email di assistenza e di contatto; negli **ambiti** aggiungi `.../auth/gmail.send`; tra gli **utenti di test** aggiungi il tuo indirizzo Gmail. Poi premi **Pubblica l'app** (stato «In produzione»): senza, il token scade dopo 7 giorni. Google mostrerà «app non verificata»: per uso personale va bene.
4. **Credenziali → Crea credenziali → ID client OAuth → Tipo: App desktop**. Copia *ID client* e *Client secret*.
5. Nel `.env` scrivi `GMAIL_CLIENT_ID=` e `GMAIL_CLIENT_SECRET=` (e `EMAIL_FROM=La Nostra Città <tuoindirizzo@gmail.com>`; deve essere l'account autenticato).
6. Lancia `tools/.venv/bin/python tools/email/ottieni_token_gmail.py`: si apre il browser, accedi, scegli «Avanzate → Vai a … (non sicuro)» e consenti l'invio di email. Lo script scrive `GMAIL_REFRESH_TOKEN` nel `.env` senza mostrarlo.
7. Prova: `cd apps/web && .venv/bin/python manage.py prova_email tuoindirizzo@gmail.com`.
8. Su Render aggiungi `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `EMAIL_FROM` e `SITE_URL`; poi *Manual Deploy*. Con le variabili `GMAIL_*` presenti, l'API ha la precedenza sull'SMTP.

La prova automatica `apps/web/smoke/gmail_api.py` controlla il codice contro un finto server (nessuna email vera).

### Alternativa: Gmail con SMTP (in locale o su un hosting che non lo blocca)

Va bene per una demo o un uso piccolo (circa 500 messaggi al giorno; il mittente è sempre l'indirizzo Gmail).

1. Sull'account Google attiva la **verifica in due passaggi** (Sicurezza → Verifica in due passaggi).
2. Crea una **password per le app**: <https://myaccount.google.com/apppasswords> → nome «La Nostra Città» → Google mostra 16 caratteri (si usa senza spazi). Non è la password dell'account e si può revocare.
3. In `.env` (locale) e nelle variabili di Render imposta:
   - `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_TLS=1`
   - `EMAIL_USER=tuoindirizzo@gmail.com`
   - `EMAIL_PASSWORD=` la password per le app
   - `EMAIL_FROM=La Nostra Città <tuoindirizzo@gmail.com>` (Gmail sostituisce comunque il mittente con l'account autenticato)
   - `SITE_URL=https://la-nostra-citta.onrender.com` (per i link nelle email)
4. Prova: `cd apps/web && .venv/bin/python manage.py prova_email tuoindirizzo@gmail.com`. Se arriva, la registrazione e il recupero password funzionano.

Su Render gratuito questo metodo **non funziona** (SMTP bloccato): usa la Gmail API qui sopra. Se Google rifiuta l'accesso: la verifica in due passaggi non è attiva, la password per le app è sbagliata o ha spazi, oppure l'account è un account di lavoro/scuola che blocca le password per le app.

## 4. Dopo il primo avvio

- Accedi come amministratore e controlla `/amministrazione/`. Crea l'amministratore vero e disattiva quelli demo (password `DemoMilano2026!` pubblica nel repository).
- Svuota i dati demo o usa un database di produzione senza seed (`tools/seed/seed.py` **non** va eseguito sul database di produzione).
- Alza `DJANGO_HSTS_SECONDS` a 31536000 quando tutto funziona.
- `python manage.py check --deploy` deve restare senza avvisi gravi.
- Backup del database (Aiven) e del disco `/data`.
- Normative: sostituire i testi segnaposto con quelli del comitato (GDPR, termini, cookie).

## 5. IA con OpenRouter (gratuita)

I controlli su testi, commenti e foto con modelli veri sono **spenti** finché non si imposta questo (decisioni e limiti in [`piano_ia_openrouter.md`](piano_ia_openrouter.md)):

| Variabile | Valore |
|---|---|
| `OPENROUTER_API_KEY` | chiave da <https://openrouter.ai/keys>; account gratuito, nessun credito. **Mai** nel repository |
| `IA_MODALITA` | `coda` per attivare il prefiltro locale e la coda; `sincrona` (predefinito) lascia i controlli simulati |
| `IA_LAVORATORE` | `1` per far girare il lavoratore dentro il sito (un solo processo gunicorn) |
| `IA_MODELLI_TESTO`, `IA_MODELLI_VISIONE` | facoltative; identificativi dei modelli `:free` separati da virgola, in ordine di preferenza |
| `IA_RILEGGI_PULITI` | `1` (predefinito): i commenti senza segnali si rileggono col modello con la quota avanzata; `0` per spendere richieste solo sui sospetti |

Prima di attivare: nelle impostazioni di privacy dell'account OpenRouter vieta l'uso dei dati per l'addestramento; controlla con `python manage.py ia_lavora --stato` o dal pannello `/amministrazione/ia/` che la chiave sia riconosciuta e la quota visibile. Il piano gratuito ha 50 richieste al giorno (si azzerano a mezzanotte UTC); quando finiscono i contenuti aspettano in coda e, dopo 24 ore, passano al moderatore. Il sito dorme dopo circa 15 minuti senza visite: la coda resta nel database e riparte al primo avvio.

### Più fornitori (a costo zero)

OpenRouter ha un solo account e 50 richieste al giorno, e i suoi modelli gratuiti a volte sono saturi. Per questo i controlli usano una **catena di fornitori**: si passa al successivo se uno non risponde o ha finito la quota. Ogni fornitore ha chiave, quota e contatore propri (pannello `/amministrazione/ia/`, comando `python manage.py ia_lavora --stato`). **Un fornitore senza chiave è «non configurato»: viene saltato, non è un errore.** Non si creano più account sullo stesso fornitore (violerebbe i termini).

| Fornitore | Variabili | Stato | Limiti usati da noi | Trattamento dei dati (piano gratuito, verificato il 2026-10-26) |
|---|---|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | attivo | 50 al giorno (limite del fornitore) | richiesta `data_collection=deny`: restano pochi modelli che non addestrano |
| **Groq** | `GROQ_API_KEY` | **attivo se c'è la chiave** | 500 al giorno, 20 al minuto (scelta nostra, prudente: i limiti ufficiali stanno nella console dell'account) | il contratto (Services Agreement, 4.2) vieta di usare input e output per addestrare; nessuna conservazione di default, log di sicurezza fino a 30 giorni; server negli USA. Modelli: `llama-3.3-70b-versatile`, `openai/gpt-oss-20b`; foto con `qwen/qwen3.8-27b` (3 immagini) |
| Cloudflare Workers AI | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | predisposto, spento | 100 al giorno (10.000 «neuroni» al giorno, azzeramento 00:00 UTC: la corrispondenza richieste/neuroni è approssimata) | la documentazione dice che non usa i contenuti dei clienti per addestrare. Modelli provati il 2026-10-26: `@cf/meta/llama-3.3-70b-instruct-fp8-fast` (testo, 10/10) e `@cf/mistralai/mistral-small-3.1-24b-instruct` (testo 10/10 e foto, 1 immagine per richiesta). `@cf/meta/llama-3.2-11b-vision-instruct` chiede di accettare la licenza Meta (un «agree» inviato dall'account): non usato |
| Cerebras | `CEREBRAS_API_KEY` | predisposto, spento | 200 al giorno, 5 al minuto | prompt non conservati; sull'addestramento le fonti non sono concordi; crediti di prova che scadono dopo 30 giorni |
| ~~Mistral~~ | `MISTRAL_API_KEY` + `MISTRAL_NIENTE_ADDESTRAMENTO=1` | **non usare** | | risulta **a pagamento** (verificato dall'autore il 2026-10-26); in passato il piano gratuito poteva addestrare sui dati. Il codice è predisposto ma resta spento |
| ~~Google AI Studio / Gemini~~ | | **escluso** | | nel piano gratuito Google usa i contenuti per migliorare i prodotti (con revisori umani) e i termini consentono solo il piano a pagamento per servire utenti nello Spazio economico europeo, Svizzera e Regno Unito |

Per attivare un fornitore: crea l'account (uno solo), genera la chiave, mettila nelle variabili d'ambiente di Render, aggiungi il nome a `IA_FORNITORI` (l'ordine è l'ordine di preferenza) e controlla il pannello. Per provarlo prima senza toccare il sito: `apps/web/.venv/bin/python tools/ia/sonda_modelli.py --fornitore groq --elenco` (elenco dei modelli, nessuna quota), poi senza `--elenco` (poche richieste), e per confrontarlo con gli altri sugli stessi 159 contenuti `apps/web/.venv/bin/python tools/ia/valuta.py --esegui --confronta openrouter,groq --max 6`.

L'informativa sull'intelligenza artificiale deve dire che testi e foto delle segnalazioni (senza metadati e con i volti sfocati) vanno ai fornitori esterni della catena (elenco aggiornato nel pannello): bozza in [`informativa_ia_bozza.md`](informativa_ia_bozza.md). Documento e selfie non escono mai dal sito.

## Variabili riassunte

Vedi [`.env.example`](../.env.example).
