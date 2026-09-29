# Handoff (2026-09-29)

## Dove siamo

Fase 1 (database su Aiven) **conclusa**, 6 step su 6, un commit per step (ultimo: `32421d1`).
Leggere prima `CLAUDE.md` (regole, comandi, decisioni) e `db/README.md` (ricreare il DB).

- `defaultdb` (principale): 22 tabelle, 7 trigger, 3 viste, 88 NIL, dati demo (154 utenti, 300 segnalazioni, 1916 sostegni, 397 commenti, 5095 log), ~5 MB.
- `la_nostra_citta_test`: stesso schema e stessi dati demo; è il posto per le prove distruttive.
- Server: MySQL 8.4.8, `sql_require_primary_key=ON`, `log_bin_trust_function_creators=ON`.
- Credenziali in `.env` e `certs/ca.pem` (non versionati). Password demo degli utenti: `tools/seed/README.md`.

## Decisioni prese in questa fase

- `quartieri.id` = `ID_NIL` della fonte; `municipio` per maggiore sovrapposizione (approssimato per 16 NIL su 88).
- Contenuto bloccato dall'IA: resta non pubblico; revisione accolta = approvato dal moderatore con `esito_moderazione` che resta `bloccato`.
- Il seed non logga la registrazione utente come `creazione` (la vista `v_statistiche_utenti` conta ogni `creazione`).
- Modifiche allo schema: nuova migrazione `003_...`, non si toccano 001/002.

## Aperto

1. **Stack applicativo**: proposto Django (SDK `spid-cie-oidc-django` con RP, Provider di test e Trust Anchor). Da verificare i vincoli di versione dell'SDK con una prova di un'ora (installazione isolata + demo Docker). Fallback: Node.js (solo RP) o proxy RP PHP.
2. **SPID/CIE reali** (obiettivo didattico): serve un ente che aderisca (probabilmente la scuola, oppure un soggetto aggregatore); sviluppo in locale con gli ambienti di test di Developers Italia. Procedure e tempi di onboarding non verificati.
3. Colonna spaziale per `quartieri.confine`: rinviata; 2 poligoni (`CASCINA MERLATA`, `ASSIANO`) risultano invalidi per MySQL.
4. Filtro per tabella nella vista `v_statistiche_utenti`: da valutare (nuova migrazione).
5. Materiale 3 della traccia: schema a blocchi dell'architettura IA (non iniziato).
6. **Cambiare la password di `avnadmin` su Aiven** (condivisa in chiaro in chat).

## Attenzione

- Il servizio Aiven Free si spegne se inattivo: se la connessione fallisce, riaccenderlo dalla console.
- `tools/seed/seed.py` è distruttivo sulle tabelle non di riferimento; `test_vincoli.sql` va eseguito solo su un database di test con `quartieri` vuota.
- Non stampare mai la password né scriverla in file versionati.
