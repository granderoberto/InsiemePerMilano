# Messa in produzione

Obiettivo: sito raggiungibile su un dominio in HTTPS, con email vere, database su Aiven e file caricati su disco persistente.
Lo stato SPID/CIE reale è in [`spid_produzione.md`](spid_produzione.md) (richiede un ente).

## Perché non Vercel

Vercel esegue funzioni «serverless»: senza disco persistente, con processi di breve durata. Questo sito salva su disco foto e video
(`MEDIA_ROOT`) e un archivio temporaneo cifrato per la verifica del documento, tiene connessioni MySQL e ha un secondo servizio
(SPID/CIE) con database proprio. Su Vercel servirebbero: archiviazione esterna dei file (S3/R2), riscrittura dei percorsi dei media,
un host diverso per il servizio SPID. Si può fare, ma è più lavoro e più fragile. Soluzione scelta: **hosting a contenitori**
(Render o Railway) con il `Dockerfile` di `apps/web/`.

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
3. Il disco persistente (`/data`, variabile `DATA_DIR`) **non esiste nel piano gratuito**: serve un piano a pagamento (verificare prezzi sul sito). Senza disco, le foto caricate sparirebbero a ogni riavvio.
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

## 4. Dopo il primo avvio

- Accedi come amministratore e controlla `/amministrazione/`. Crea l'amministratore vero e disattiva quelli demo (password `DemoMilano2026!` pubblica nel repository).
- Svuota i dati demo o usa un database di produzione senza seed (`tools/seed/seed.py` **non** va eseguito sul database di produzione).
- Alza `DJANGO_HSTS_SECONDS` a 31536000 quando tutto funziona.
- `python manage.py check --deploy` deve restare senza avvisi gravi.
- Backup del database (Aiven) e del disco `/data`.
- Normative: sostituire i testi segnaposto con quelli del comitato (GDPR, termini, cookie).

## Variabili riassunte

Vedi [`.env.example`](../.env.example).
