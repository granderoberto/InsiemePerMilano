# Handoff (2026-09-29)

## Dove siamo

- Fase 1 (database su Aiven) **conclusa**. Prova tecnica su Django + SDK SPID/CIE **conclusa**, stack **deciso** (ultimo commit: `4804fd0`).
- Leggere prima `CLAUDE.md` (regole, comandi, stack, regola migrazioni SQL/Django), `db/README.md` (ricreare il DB) e `docs/spike_django_spid.md` (esiti della prova).
- `defaultdb` (principale): 22 tabelle, 7 trigger, 3 viste, 88 NIL, dati demo (154 utenti, 300 segnalazioni, 1916 sostegni, 397 commenti, 5095 log), ~5 MB.
- `la_nostra_citta_test`: stesso schema e dati; per le prove distruttive. Server MySQL 8.4.8.
- Credenziali in `.env` e `certs/ca.pem` (non versionati). Password demo degli utenti: `tools/seed/README.md`.

## Decisioni

- **Stack**: Django 5.2 LTS (app principale) + SDK `spid-cie-oidc-django` isolato in un servizio separato (progetto e database propri). L'SDK dichiara `Django<5.0` (fuori supporto): va forzato su 5.2 e le sue migrazioni MySQL richiedono `max_length` 1024 → 700 (campo `kid`). Fallback: Node.js (solo RP).
- Modelli Django sul dominio: `managed=False`; utente di autenticazione su `utenti` (niente `auth_user`); vedi le 11 regole in `CLAUDE.md`.
- `quartieri.id` = `ID_NIL`; `municipio` approssimato per 16 NIL su 88.
- Contenuto bloccato dall'IA: resta non pubblico; revisione accolta = approvato con `esito_moderazione` ancora `bloccato`.
- Modifiche allo schema: nuova migrazione `003_...`, non si toccano 001/002.

## Prossimo passo

Il sito gira (`apps/web/`, vedi il suo README): elenco, mappa, dettaglio, accesso, nuova segnalazione, moderazione, statistiche. Mancano modifica/eliminazione della propria segnalazione, richieste di revisione, dashboard admin, email/2FA, CSV, e il servizio SPID/CIE separato (oggi simulato).

Attenzione: il servizio Aiven Free si spegne dopo pochi giorni di inattività e può cambiare stato; se `nslookup` dell'host dà NXDOMAIN, riaccenderlo dalla console.

## Aperto

1. **SPID/CIE reali** (obiettivo didattico): serve un ente che aderisca (probabilmente la scuola) o un soggetto aggregatore; non avviato. Sviluppo con il demo locale dell'SDK. Non provato: far usare `utenti` all'RP dell'SDK (`user_reunification` è sovrascrivibile).
2. Materiale 3 della traccia: schema a blocchi dell'architettura IA (non iniziato).
3. Colonna spaziale per `quartieri.confine`: rinviata; 2 poligoni (`CASCINA MERLATA`, `ASSIANO`) invalidi per MySQL.
4. Filtro per tabella nella vista `v_statistiche_utenti`: da valutare (nuova migrazione).
5. **Cambiare la password di `avnadmin` su Aiven** (condivisa in chiaro in chat).
6. `spike/` (317 MB, ignorata da git): tenere o eliminare.

## Attenzione

- Il servizio Aiven Free si spegne se inattivo: se la connessione fallisce, riaccenderlo dalla console.
- `tools/seed/seed.py` è distruttivo sulle tabelle non di riferimento; `test_vincoli.sql` va eseguito solo su un database di test con `quartieri` vuota.
- Le migrazioni Django su MySQL non sono atomiche: provarle prima su `la_nostra_citta_test`.
- Non stampare mai la password né scriverla in file versionati.
