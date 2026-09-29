-- Test dei vincoli (MySQL). Eseguire con: mysql --force <db> < test_vincoli.sql
-- Le righe marcate "ERRORE ATTESO" devono fallire, tutte le altre devono riuscire.
SET time_zone = '+00:00';
INSERT INTO quartieri (nome, municipio) VALUES ('Isola', 9);
INSERT INTO utenti (nome,cognome,email,password_hash,codice_fiscale_hash,data_nascita,metodo_registrazione,stato_account)
 VALUES ('Mario','Rossi','m@x.it','h',NULL,'1990-01-01','credenziali','attivo'),
        ('Anna','Bianchi','a@x.it',NULL,REPEAT('a',64),'1995-01-01','spid','attivo');
-- ERRORE ATTESO: SPID senza codice fiscale
INSERT INTO utenti (nome,cognome,email,data_nascita,metodo_registrazione) VALUES ('X','Y','x@x.it','1990-01-01','spid');
-- ERRORE ATTESO: età minima
INSERT INTO utenti (nome,cognome,email,password_hash,data_nascita,metodo_registrazione) VALUES ('X','Y','y@x.it','h','2020-01-01','credenziali');
-- ERRORE ATTESO: email non valida
INSERT INTO utenti (nome,cognome,email,password_hash,data_nascita,metodo_registrazione) VALUES ('X','Y','nonvalida','h','1990-01-01','credenziali');
INSERT INTO segnalazioni (id_autore,tipo,titolo,descrizione,latitudine,longitudine,id_quartiere)
 VALUES (1,'problema','Buca','Buca profonda in via Borsieri davanti al civico 12',45.487,9.188,1);
INSERT INTO media (id_segnalazione,tipo,percorso,mime_type,dimensione_byte,ordine,copertina) VALUES (1,'foto','/a.jpg','image/jpeg',100000,1,TRUE);
-- ERRORE ATTESO: seconda copertina sulla stessa segnalazione
INSERT INTO media (id_segnalazione,tipo,percorso,mime_type,dimensione_byte,ordine,copertina) VALUES (1,'foto','/b.jpg','image/jpeg',100000,2,TRUE);
-- ERRORE ATTESO: video oltre 60 secondi
INSERT INTO media (id_segnalazione,tipo,percorso,mime_type,dimensione_byte,durata_sec,ordine) VALUES (1,'video','/v.mp4','video/mp4',1000,90,2);
-- ERRORE ATTESO: sostegno su segnalazione non pubblica
INSERT INTO sostegni (id_utente,id_segnalazione) VALUES (2,1);
-- ERRORE ATTESO: transizione 1 -> 3
INSERT INTO cambi_stato (id_segnalazione,id_stato_da,id_stato_a) VALUES (1,1,3);
INSERT INTO cambi_stato (id_segnalazione,id_stato_da,id_stato_a) VALUES (1,1,2);
INSERT INTO cambi_stato (id_segnalazione,id_stato_da,id_stato_a,id_operatore) VALUES (1,2,3,2);
INSERT INTO sostegni (id_utente,id_segnalazione) VALUES (2,1);
-- ERRORE ATTESO: l'autore sostiene la propria segnalazione
INSERT INTO sostegni (id_utente,id_segnalazione) VALUES (1,1);
INSERT INTO commenti (id_segnalazione,id_autore,testo) VALUES (1,2,'Confermo');
INSERT INTO commenti (id_segnalazione,id_autore,id_padre,testo) VALUES (1,1,1,'Grazie');
INSERT INTO log_attivita (attore,id_utente,operazione,tabella,id_oggetto) VALUES ('utente',2,'sostegno','sostegni',1);
-- ERRORE ATTESO: log immutabile
DELETE FROM log_attivita;
-- ERRORE ATTESO: richiesta di revisione su due oggetti
INSERT INTO richieste_revisione (id_richiedente,id_segnalazione,id_commento,motivo) VALUES (1,1,1,'x');
SELECT * FROM v_classifica_segnalazioni;
SELECT id,nome,n_segnalazioni,n_commenti_scritti,n_sostegni_ricevuti,n_commenti_ricevuti,attivita_30_giorni FROM v_statistiche_utenti;
SELECT * FROM v_classifica_utenti_pubblica;
