# Modello Entità-Relazione

Progetto: La Nostra Città, Il Nostro Futuro

Notazione: ● attributo chiave (PK), ○ attributo semplice. Le chiavi esterne non compaiono: nel modello concettuale le rappresentano le associazioni, e diventano FK solo nello schema logico.

## Entità

### UTENTE
- **PK:** id
- **Attributi:** nome, cognome, email, password_hash, codice_fiscale_hash, data_nascita, metodo_registrazione, ruolo, stato_account, profilo_pubblico, mfa_attiva, tentativi_falliti, bloccato_fino, email_verificata_il, creato_il, eliminato_il

### QUARTIERE
- **PK:** id
- **Attributi:** nome, municipio, confine

### VERIFICA_IDENTITA
- **PK:** id
- **Attributi:** tentativo, tipo_documento, ok_lettura_ocr, ok_corrispondenza_dati, ok_validita, ok_autenticita, ok_confronto_volto, punteggio, esito_ia, motivo, esito_finale, motivo_revisione, revisionata_il, creata_il

### SOSPENSIONE
- **PK:** id
- **Attributi:** motivo, inizio, fine, revocata_il

### DOCUMENTO_NORMATIVO
- **PK:** id
- **Attributi:** tipo, versione, testo, pubblicato_il

### SEGNALAZIONE
- **PK:** id
- **Attributi:** tipo, titolo, descrizione, latitudine, longitudine, indirizzo, esito_moderazione, punteggio_moderazione, punteggio_coerenza, nascosta, motivo_nascosta, creata_il, aggiornata_il, eliminata_il

### MEDIA
- **PK:** id
- **Attributi:** tipo, percorso, mime_type, dimensione_byte, durata_sec, ordine, copertina, exif_lat, exif_lon, esito_visione, punteggio_sessuale, punteggio_violenza, testo_ocr, esito_testo_ocr, caricato_il

### STATO
- **PK:** id
- **Attributi:** nome, finale, pubblico

### CAMBIO_STATO
- **PK:** id
- **Attributi:** nota, avvenuto_il

### CATEGORIA
- **PK:** id
- **Attributi:** nome, descrizione, attiva

### COMMENTO
- **PK:** id
- **Attributi:** testo, esito_moderazione, punteggio_moderazione, nascosto, motivo_nascosto, creato_il, modificato_il, eliminato_il

### CANDIDATO
- **PK:** id
- **Attributi:** nome, cognome, lista, email

### RICHIESTA_REVISIONE
- **PK:** id
- **Attributi:** motivo, stato, risposta, creata_il, chiusa_il

### NOTIFICA
- **PK:** id
- **Attributi:** tipo, messaggio, link, letta, creata_il

### PREFERENZA_NOTIFICA (entità debole)
- **PK:** tipo (chiave parziale) + UTENTE
- **Attributi:** in_app, email

### LOG_ATTIVITA
- **PK:** id
- **Attributi:** avvenuto_il, attore, operazione, tabella, id_oggetto, dati_precedenti, dati_nuovi

## Associazioni

| Associazione | Entità e cardinalità | Attributi |
|---|---|---|
| RISIEDE | UTENTE (0,1) — QUARTIERE (0,N) | - |
| SI_TROVA | SEGNALAZIONE (1,1) — QUARTIERE (0,N) | - |
| CREA | UTENTE (0,N) — SEGNALAZIONE (1,1) | - |
| EFFETTUA | UTENTE (0,3) — VERIFICA_IDENTITA (1,1) | - |
| REVISIONA | UTENTE (0,N) — VERIFICA_IDENTITA (0,1) | - |
| SUBISCE | UTENTE (0,N) — SOSPENSIONE (1,1) | - |
| APPLICA | UTENTE (0,N) — SOSPENSIONE (1,1) | - |
| REVOCA | UTENTE (0,N) — SOSPENSIONE (0,1) | - |
| PUBBLICA | UTENTE (0,N) — DOCUMENTO_NORMATIVO (1,1) | - |
| ACCETTA | UTENTE (0,N) — DOCUMENTO_NORMATIVO (0,N) | accettato_il |
| CONTIENE | SEGNALAZIONE (1,10) — MEDIA (1,1) | - |
| CLASSIFICATA | SEGNALAZIONE (1,N) — CATEGORIA (0,N) | origine, confidenza |
| HA_STATO | SEGNALAZIONE (1,1) — STATO (0,N) | - |
| STORICO | SEGNALAZIONE (0,N) — CAMBIO_STATO (1,1) | - |
| DA | CAMBIO_STATO (1,1) — STATO (0,N) | - |
| A | CAMBIO_STATO (1,1) — STATO (0,N) | - |
| ESEGUE | UTENTE (0,N) — CAMBIO_STATO (0,1) | - |
| PRECEDE | STATO (0,N) da — STATO (0,N) a | - |
| SOSTIENE | UTENTE (0,N) — SEGNALAZIONE (0,N) | creato_il |
| NASCONDE | UTENTE (0,N) — SEGNALAZIONE (0,1) | - |
| SCRIVE | UTENTE (0,N) — COMMENTO (1,1) | - |
| RIGUARDA | SEGNALAZIONE (0,N) — COMMENTO (1,1) | - |
| RISPONDE | COMMENTO (0,N) padre — COMMENTO (0,1) figlio | - |
| NASCONDE | UTENTE (0,N) — COMMENTO (0,1) | - |
| INVIA | UTENTE (0,N) — SEGNALAZIONE (0,N) — CANDIDATO (0,N) | inviato_il |
| RICHIEDE | UTENTE (0,N) — RICHIESTA_REVISIONE (1,1) | - |
| GESTISCE | UTENTE (0,N) — RICHIESTA_REVISIONE (0,1) | - |
| SU_SEGNALAZIONE | RICHIESTA_REVISIONE (0,1) — SEGNALAZIONE (0,N) | - |
| SU_COMMENTO | RICHIESTA_REVISIONE (0,1) — COMMENTO (0,N) | - |
| SU_VERIFICA | RICHIESTA_REVISIONE (0,1) — VERIFICA_IDENTITA (0,N) | - |
| RICEVE | UTENTE (0,N) — NOTIFICA (1,1) | - |
| IMPOSTA | UTENTE (0,N) — PREFERENZA_NOTIFICA (1,1) | - |
| REGISTRA | UTENTE (0,N) — LOG_ATTIVITA (0,1) | - |

## Vincoli non esprimibili nel diagramma

- RICHIESTA_REVISIONE partecipa esattamente a una tra SU_SEGNALAZIONE, SU_COMMENTO e SU_VERIFICA.
- In RISPONDE, padre e figlio appartengono alla stessa SEGNALAZIONE.
- SOSTIENE: l'utente non può sostenere una segnalazione che ha creato (CREA).
- HA_STATO coincide con lo stato di arrivo dell'ultimo CAMBIO_STATO: ridondanza controllata.
- ESEGUE, REVISIONA, APPLICA, REVOCA, NASCONDE, INVIA, GESTISCE richiedono ruolo moderatore o amministratore; PUBBLICA richiede amministratore.
- EFFETTUA vale solo per utenti con metodo_registrazione = credenziali (massimo 3 tentativi).
- REGISTRA è (0,1) sul lato LOG_ATTIVITA perché le azioni automatiche dell'IA non hanno un utente.
