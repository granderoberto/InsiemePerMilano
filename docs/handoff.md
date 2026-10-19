# Handoff (2026-10-19)

## Dove siamo

Il sito è **online** su https://la-nostra-citta.onrender.com (Render, piano gratuito, Docker) con il database su Aiven (`defaultdb`, dati demo). Il codice è su GitHub (`granderoberto/InsiemePerMilano`, ramo `main`).

Leggere prima `CLAUDE.md` (regole, comandi, decisioni, stack), `PRODUCT.md` (utenti e scopo), `DESIGN.md` (sistema grafico), `docs/produzione.md` (hosting ed email) e `db/README.md` (ricreare il database).

## Cosa c'è

- **Materiali della traccia**: analisi (`docs/specifiche_utente.md`), modello ER (`docs/modello_er.*`), **modello logico** (`docs/modello_logico.*`, generato da `db/schema.sql` con `tools/logico/genera.py`), schema a blocchi dell'IA (`docs/architettura_ia.*`).
- **Database** MySQL 8 su Aiven: 22 tabelle, 7 trigger, 3 viste, migrazioni 001-005. Dati demo: 154 utenti, 300 segnalazioni. `la_nostra_citta_test` per le prove distruttive.
- **Sito Django** (`apps/web`): pubblico, utente, autore, moderazione, amministrazione; registrazione con conferma email; **verifica del documento facoltativa, necessaria per pubblicare** (`Utente.identita_verificata`); 2FA; recupero password; eliminazione account; scelta del quartiere da mappa; foto e video con copia nel database; interfaccia unica per i controlli IA (`core/services/ia/`).
- **Grafica**: «segnaletica milanese» (Archivo self-hosted, linee M1-M5 come codice, percorso della segnalazione come linea della metropolitana).
- **SPID/CIE** (`apps/spid`): protocollo vero su ambiente di prova; per l'uso reale serve l'adesione di un ente (`docs/spid_produzione.md`).
- **Email**: SMTP configurabile da variabili d'ambiente (`EMAIL_*`, `SITE_URL`); provato con Gmail (password per le app). Comando `manage.py prova_email`.

## Decisioni

- Stack: Django 5.2 LTS; modelli sul dominio `managed=False`; schema solo da migrazioni SQL (regola di convivenza in `CLAUDE.md`).
- Hosting: Render (non Vercel: servono disco, processi di lunga durata e un secondo servizio). Piano gratuito: il disco è temporaneo, per questo i file caricati sono copiati nel database (`media_contenuti`).
- Contenuto bloccato dall'IA: resta non pubblico; revisione accolta = approvato con `esito_moderazione` ancora `bloccato`.
- I media dei dati demo mostrano immagini e video **di esempio disegnati** (`apps/web/static/demo/`), non fotografie.

## Parti simulate o di prova

- Verifica del documento e moderazione IA: simulate (`core/services/ia/simulato*.py`).
- SPID/CIE: gestore di identità di prova.
- Foto dei dati demo: illustrazioni.

## Da fare / aperto

1. **Sicurezza**: gli account demo (anche amministratore e moderatori) hanno una password pubblica nel repository e sono presenti online. Cambiarla o usare un database pulito prima di un uso vero. Cambiare anche la password di `avnadmin` su Aiven (era stata condivisa in chiaro).
2. **Aiven Free si spegne** dopo pochi giorni di inattività: se il sito non carica i dati, riaccenderlo dalla console.
3. **SPID/CIE reali**: richiesta di adesione dell'ente (`docs/spid_produzione.md`).
4. **IA vera** al posto della simulata (`docs/architettura_ia.md`, «Passi per l'IA vera»).
5. Accessibilità: prove con screen reader e dispositivi reali (`docs/accessibilita.md`).
6. Provare online registrazione, email e caricamento di foto e video (il `Dockerfile` non è stato provato in locale).
7. Colonna spaziale per `quartieri.confine` (2 poligoni invalidi per MySQL).
8. Normative: sostituire i testi segnaposto con quelli del comitato.

## Attenzione

- `tools/seed/seed.py` è distruttivo sulle tabelle non di riferimento: mai sul database di produzione se contiene dati veri.
- Non stampare né committare mai password o chiavi: `.env`, `.env.produzione` e `certs/` non sono versionati.
- Le migrazioni Django su MySQL non sono atomiche: provarle prima su `la_nostra_citta_test`.
- Le prove in `apps/web/smoke/` scrivono nel database di test: dopo averle usate, `tools/seed/seed.py la_nostra_citta_test`.
