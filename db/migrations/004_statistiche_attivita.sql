-- L'attività degli ultimi 30 giorni conta solo segnalazioni, commenti e sostegni:
-- le richieste di revisione (operazione 'creazione' su richieste_revisione) non la gonfiano più.
DROP VIEW IF EXISTS v_classifica_utenti_pubblica;
DROP VIEW IF EXISTS v_statistiche_utenti;

CREATE VIEW v_statistiche_utenti AS
SELECT u.id, u.nome, u.cognome, u.profilo_pubblico,
       (SELECT COUNT(*) FROM segnalazioni s WHERE s.id_autore = u.id AND s.eliminata_il IS NULL) AS n_segnalazioni,
       (SELECT COUNT(*) FROM commenti c WHERE c.id_autore = u.id AND c.eliminato_il IS NULL) AS n_commenti_scritti,
       (SELECT COUNT(*) FROM sostegni so WHERE so.id_utente = u.id) AS n_sostegni_dati,
       (SELECT COUNT(*) FROM sostegni so JOIN segnalazioni s ON s.id = so.id_segnalazione
         WHERE s.id_autore = u.id) AS n_sostegni_ricevuti,
       (SELECT COUNT(*) FROM commenti c JOIN segnalazioni s ON s.id = c.id_segnalazione
         WHERE s.id_autore = u.id AND c.id_autore <> u.id) AS n_commenti_ricevuti,
       (SELECT COUNT(*) FROM log_attivita l
         WHERE l.id_utente = u.id
           AND l.operazione IN ('creazione','commento','sostegno')
           AND l.tabella IN ('segnalazioni','commenti','sostegni')
           AND l.avvenuto_il >= UTC_TIMESTAMP(3) - INTERVAL 30 DAY) AS attivita_30_giorni
FROM utenti u
WHERE u.stato_account <> 'eliminato';

CREATE VIEW v_classifica_utenti_pubblica AS
SELECT id, nome, CONCAT(LEFT(cognome, 1), '.') AS cognome,
       n_segnalazioni, n_commenti_scritti, n_sostegni_ricevuti, attivita_30_giorni
FROM v_statistiche_utenti
WHERE profilo_pubblico;
