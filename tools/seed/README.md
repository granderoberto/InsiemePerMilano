# Dati demo

Tutti i dati sono **fittizi**: nomi generati da Faker (it_IT) con email `@example.*`, codici fiscali
casuali salvati solo come hash SHA-256, testi dei documenti normativi segnaposto. Nessun dato reale.

```bash
tools/.venv/bin/python tools/seed/seed.py <database> [--oggi AAAA-MM-GG]
```

- **Distruttivo**: `SET FOREIGN_KEY_CHECKS=0`, `TRUNCATE` di tutte le tabelle tranne quelle di Django (`django_*`, `auth_*`), `quartieri`, `stati`,
  `transizioni_ammesse`, `categorie`, `schema_migrations`, poi `FOREIGN_KEY_CHECKS=1`. Richiede `quartieri`
  già popolata (`tools/geo/import_quartieri.py`).
- **Deterministico**: seed fisso (`20260929`). Con lo stesso `--oggi` produce sempre gli stessi dati.
  Le date sono ancorate a "oggi" alle 00:00 UTC (default: data odierna); prima dell'orale rilancialo
  per avere attività negli ultimi 30 giorni.
- Genera tutto in memoria e scrive in una sola transazione dopo il reset.

**Password demo di tutti gli utenti con credenziali: `DemoMilano2026!`** (bcrypt costo 12, stesso hash
per tutti, salt fisso per riproducibilità: solo per la demo).

Nei dati demo la **2FA è spenta** per tutti (`mfa_attiva = 0`, `mfa_segreto` vuoto): non esistono segreti demo.

## Contenuto

| Cosa | Quantità |
|---|---|
| Utenti | 1 amministratore, 3 moderatori, 150 utenti (35% SPID, 20% CIE, 45% credenziali) |
| Segnalazioni | 300: 5 Ricevuta, 45 In attesa, 140 Approvata, 50 Rifiutata, 60 Presentata |
| Media | 1-4 per segnalazione, percorsi fittizi `media/demo/<id>.jpg` (video `.mp4`) |
| Sostegni | a coda lunga; le presentate ai candidati sono le più sostenute |
| Commenti | con risposte, alcuni nascosti/bloccati con motivo |

## Convenzioni e scelte (non coperte dalla specifica)

- Gli stati avanzano **solo** con `INSERT` in `cambi_stato` (il trigger aggiorna `id_stato`). Il trigger imposta
  `aggiornata_il` all'ora reale: lo script lo riallinea alla cronologia dei dati.
- `punteggio_moderazione` = rischio (0 = nessun problema, 1 = grave); `punteggio_coerenza` = coerenza (1 = coerente).
- Contenuto `bloccato` dall'IA: resta non pubblico. Se l'autore chiede la revisione e viene accolta, la
  segnalazione viene approvata dal moderatore e `esito_moderazione` resta `bloccato` (è la decisione dell'IA,
  ribaltata da una persona); se respinta, viene rifiutata; se aperta, resta In attesa.
- Segnalazioni nascoste: 3, approvate e senza sostegni/commenti (i trigger vietano interazioni su nascoste).
- Utenti eliminati: nome/email/password/quartiere svuotati; `codice_fiscale_hash` sostituito (il CHECK non
  ammette NULL per SPID/CIE) e `data_nascita` ridotta al 1° gennaio dell'anno (colonna NOT NULL).
- Le sospensioni e le eliminazioni sono posizionate dopo l'ultima attività dell'utente.
- `log_attivita`: `id_oggetto` dei sostegni è l'`id_segnalazione`, dei consensi l'`id_documento`.
  La registrazione utente non è loggata come `creazione` (la vista `v_statistiche_utenti` conta ogni
  `creazione` come attività senza filtrare la tabella); restano `creazione` le segnalazioni e le richieste di revisione.
- Percorsi verifica identità: approvata al primo tentativo, riprova dopo un rifiuto, da rivedere (revisionata
  o ancora in coda), rifiutata 3 volte con richiesta aperta, rifiutata con richiesta accolta/respinta.
