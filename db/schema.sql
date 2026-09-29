-- La Nostra Città, Il Nostro Futuro
-- Schema MySQL 8.0+ (InnoDB, utf8mb4). Tutti i DATETIME sono in UTC.
-- Da eseguire con il client mysql (usa DELIMITER per i trigger).

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ==================== UTENTI E ACCESSO ====================

CREATE TABLE quartieri (
  id        SMALLINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nome      VARCHAR(100) NOT NULL UNIQUE,
  municipio SMALLINT NOT NULL,
  confine   JSON,
  CONSTRAINT chk_municipio CHECK (municipio BETWEEN 1 AND 9)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE utenti (
  id                   INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nome                 VARCHAR(50) NOT NULL,
  cognome              VARCHAR(50) NOT NULL,
  email                VARCHAR(254) NOT NULL UNIQUE,
  password_hash        VARCHAR(255),
  codice_fiscale_hash  CHAR(64) UNIQUE,
  data_nascita         DATE NOT NULL,
  metodo_registrazione ENUM('credenziali','spid','cie') NOT NULL,
  ruolo                ENUM('utente','moderatore','amministratore') NOT NULL DEFAULT 'utente',
  stato_account        ENUM('in_attesa_verifica','attivo','sospeso','eliminato') NOT NULL DEFAULT 'in_attesa_verifica',
  id_quartiere         SMALLINT,
  profilo_pubblico     BOOLEAN NOT NULL DEFAULT FALSE,
  mfa_attiva           BOOLEAN NOT NULL DEFAULT FALSE,
  tentativi_falliti    SMALLINT NOT NULL DEFAULT 0,
  bloccato_fino        DATETIME(3),
  email_verificata_il  DATETIME(3),
  creato_il            DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  eliminato_il         DATETIME(3),
  CONSTRAINT fk_utenti_quartiere FOREIGN KEY (id_quartiere) REFERENCES quartieri(id),
  CONSTRAINT chk_email CHECK (REGEXP_LIKE(email, '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$')),
  CONSTRAINT chk_tentativi CHECK (tentativi_falliti >= 0),
  CONSTRAINT chk_password_solo_credenziali
    CHECK ((metodo_registrazione = 'credenziali') = (password_hash IS NOT NULL)),
  CONSTRAINT chk_cf_solo_spid_cie
    CHECK ((metodo_registrazione IN ('spid','cie')) = (codice_fiscale_hash IS NOT NULL)),
  CONSTRAINT chk_eliminato
    CHECK ((stato_account = 'eliminato') = (eliminato_il IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE verifiche_identita (
  id                     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_utente              INT NOT NULL,
  tentativo              SMALLINT NOT NULL,
  tipo_documento         ENUM('carta_identita','patente','passaporto') NOT NULL,
  ok_lettura_ocr         BOOLEAN NOT NULL,
  ok_corrispondenza_dati BOOLEAN NOT NULL,
  ok_validita            BOOLEAN NOT NULL,
  ok_autenticita         BOOLEAN NOT NULL,
  ok_confronto_volto     BOOLEAN NOT NULL,
  punteggio              SMALLINT NOT NULL,
  esito_ia               ENUM('approvata','da_rivedere','rifiutata') NOT NULL,
  motivo                 TEXT,
  id_revisore            INT,
  esito_finale           ENUM('approvata','da_rivedere','rifiutata'),
  motivo_revisione       TEXT,
  revisionata_il         DATETIME(3),
  creata_il              DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uq_verifica_tentativo (id_utente, tentativo),
  CONSTRAINT fk_verifiche_utente FOREIGN KEY (id_utente) REFERENCES utenti(id),
  CONSTRAINT fk_verifiche_revisore FOREIGN KEY (id_revisore) REFERENCES utenti(id),
  CONSTRAINT chk_tentativo CHECK (tentativo BETWEEN 1 AND 3),
  CONSTRAINT chk_punteggio CHECK (punteggio BETWEEN 0 AND 100),
  CONSTRAINT chk_esito_da_punteggio CHECK (
    (punteggio >= 85 AND esito_ia = 'approvata') OR
    (punteggio BETWEEN 50 AND 84 AND esito_ia = 'da_rivedere') OR
    (punteggio < 50 AND esito_ia = 'rifiutata')
  ),
  CONSTRAINT chk_revisione_completa CHECK (
    (id_revisore IS NULL AND esito_finale IS NULL AND revisionata_il IS NULL) OR
    (id_revisore IS NOT NULL AND esito_finale IN ('approvata','rifiutata') AND revisionata_il IS NOT NULL)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sospensioni (
  id            INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_utente     INT NOT NULL,
  id_moderatore INT NOT NULL,
  motivo        TEXT NOT NULL,
  inizio        DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  fine          DATETIME(3),
  revocata_il   DATETIME(3),
  id_revocante  INT,
  CONSTRAINT fk_sosp_utente FOREIGN KEY (id_utente) REFERENCES utenti(id),
  CONSTRAINT fk_sosp_moderatore FOREIGN KEY (id_moderatore) REFERENCES utenti(id),
  CONSTRAINT fk_sosp_revocante FOREIGN KEY (id_revocante) REFERENCES utenti(id),
  CONSTRAINT chk_sosp_fine CHECK (fine IS NULL OR fine > inizio),
  CONSTRAINT chk_sosp_se_stesso CHECK (id_utente <> id_moderatore),
  CONSTRAINT chk_sosp_revoca CHECK ((revocata_il IS NULL) = (id_revocante IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE documenti_normativi (
  id                SMALLINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tipo              ENUM('privacy','biometrici','intelligenza_artificiale','termini_uso','cookie','eta_minima') NOT NULL,
  versione          VARCHAR(20) NOT NULL,
  testo             MEDIUMTEXT NOT NULL,
  pubblicato_il     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  id_amministratore INT NOT NULL,
  UNIQUE KEY uq_documento_versione (tipo, versione),
  CONSTRAINT fk_documenti_admin FOREIGN KEY (id_amministratore) REFERENCES utenti(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE consensi (
  id_utente    INT NOT NULL,
  id_documento SMALLINT NOT NULL,
  accettato_il DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id_utente, id_documento),
  CONSTRAINT fk_consensi_utente FOREIGN KEY (id_utente) REFERENCES utenti(id),
  CONSTRAINT fk_consensi_documento FOREIGN KEY (id_documento) REFERENCES documenti_normativi(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==================== SEGNALAZIONI ====================

CREATE TABLE stati (
  id       SMALLINT NOT NULL PRIMARY KEY,
  nome     VARCHAR(30) NOT NULL UNIQUE,
  finale   BOOLEAN NOT NULL DEFAULT FALSE,
  pubblico BOOLEAN NOT NULL DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE transizioni_ammesse (
  id_stato_da SMALLINT NOT NULL,
  id_stato_a  SMALLINT NOT NULL,
  PRIMARY KEY (id_stato_da, id_stato_a),
  CONSTRAINT fk_trans_da FOREIGN KEY (id_stato_da) REFERENCES stati(id),
  CONSTRAINT fk_trans_a  FOREIGN KEY (id_stato_a)  REFERENCES stati(id),
  CONSTRAINT chk_trans_diversi CHECK (id_stato_da <> id_stato_a)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE categorie (
  id          SMALLINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nome        VARCHAR(50) NOT NULL UNIQUE,
  descrizione TEXT,
  attiva      BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE segnalazioni (
  id                     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_autore              INT NOT NULL,
  tipo                   ENUM('proposta','problema') NOT NULL,
  titolo                 VARCHAR(100) NOT NULL,
  descrizione            TEXT NOT NULL,
  latitudine             DECIMAL(9,6) NOT NULL,
  longitudine            DECIMAL(9,6) NOT NULL,
  indirizzo              VARCHAR(255),
  id_quartiere           SMALLINT NOT NULL,
  id_stato               SMALLINT NOT NULL DEFAULT 1,
  esito_moderazione      ENUM('ok','dubbio','bloccato'),
  punteggio_moderazione  DECIMAL(4,3),
  punteggio_coerenza     DECIMAL(4,3),
  nascosta               BOOLEAN NOT NULL DEFAULT FALSE,
  motivo_nascosta        TEXT,
  id_moderatore_nascosta INT,
  creata_il              DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  aggiornata_il          DATETIME(3),
  eliminata_il           DATETIME(3),
  KEY idx_segnalazioni_quartiere_stato (id_quartiere, id_stato),
  CONSTRAINT fk_segn_autore FOREIGN KEY (id_autore) REFERENCES utenti(id),
  CONSTRAINT fk_segn_quartiere FOREIGN KEY (id_quartiere) REFERENCES quartieri(id),
  CONSTRAINT fk_segn_stato FOREIGN KEY (id_stato) REFERENCES stati(id),
  CONSTRAINT fk_segn_moderatore FOREIGN KEY (id_moderatore_nascosta) REFERENCES utenti(id),
  CONSTRAINT chk_descrizione CHECK (CHAR_LENGTH(descrizione) BETWEEN 30 AND 2000),
  CONSTRAINT chk_latitudine CHECK (latitudine BETWEEN 45.38 AND 45.54),
  CONSTRAINT chk_longitudine CHECK (longitudine BETWEEN 9.04 AND 9.28),
  CONSTRAINT chk_segn_punteggio_mod CHECK (punteggio_moderazione BETWEEN 0 AND 1),
  CONSTRAINT chk_segn_punteggio_coer CHECK (punteggio_coerenza BETWEEN 0 AND 1),
  CONSTRAINT chk_nascosta_con_motivo
    CHECK (NOT nascosta OR (motivo_nascosta IS NOT NULL AND id_moderatore_nascosta IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE media (
  id                 INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_segnalazione    INT NOT NULL,
  tipo               ENUM('foto','video') NOT NULL,
  percorso           VARCHAR(500) NOT NULL,
  mime_type          VARCHAR(50) NOT NULL,
  dimensione_byte    INT NOT NULL,
  durata_sec         SMALLINT,
  ordine             SMALLINT NOT NULL,
  copertina          BOOLEAN NOT NULL DEFAULT FALSE,
  -- una sola copertina per segnalazione (sostituisce l'indice parziale di PostgreSQL)
  copertina_di       INT AS (IF(copertina, id_segnalazione, NULL)) STORED,
  exif_lat           DECIMAL(9,6),
  exif_lon           DECIMAL(9,6),
  esito_visione      ENUM('ok','dubbio','bloccato'),
  punteggio_sessuale DECIMAL(4,3),
  punteggio_violenza DECIMAL(4,3),
  testo_ocr          TEXT,
  esito_testo_ocr    ENUM('ok','dubbio','bloccato'),
  caricato_il        DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uq_media_ordine (id_segnalazione, ordine),
  UNIQUE KEY uq_media_una_copertina (copertina_di),
  CONSTRAINT fk_media_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id),
  CONSTRAINT chk_media_ordine CHECK (ordine BETWEEN 1 AND 10),
  CONSTRAINT chk_media_dimensione CHECK (dimensione_byte > 0),
  CONSTRAINT chk_media_punt_sess CHECK (punteggio_sessuale BETWEEN 0 AND 1),
  CONSTRAINT chk_media_punt_viol CHECK (punteggio_violenza BETWEEN 0 AND 1),
  CONSTRAINT chk_limiti_media CHECK (
    (tipo = 'foto'  AND mime_type IN ('image/jpeg','image/png','image/heic')
                    AND dimensione_byte <= 10485760 AND durata_sec IS NULL) OR
    (tipo = 'video' AND mime_type IN ('video/mp4','video/quicktime')
                    AND dimensione_byte <= 52428800 AND durata_sec BETWEEN 1 AND 60)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE classificazioni (
  id_segnalazione INT NOT NULL,
  id_categoria    SMALLINT NOT NULL,
  origine         ENUM('ia','utente','moderatore') NOT NULL,
  confidenza      DECIMAL(4,3),
  PRIMARY KEY (id_segnalazione, id_categoria),
  CONSTRAINT fk_class_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id) ON DELETE CASCADE,
  CONSTRAINT fk_class_categoria FOREIGN KEY (id_categoria) REFERENCES categorie(id),
  CONSTRAINT chk_confidenza CHECK (confidenza BETWEEN 0 AND 1),
  CONSTRAINT chk_confidenza_solo_ia CHECK ((origine = 'ia') = (confidenza IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cambi_stato (
  id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_segnalazione INT NOT NULL,
  id_stato_da     SMALLINT NOT NULL,
  id_stato_a      SMALLINT NOT NULL,
  id_operatore    INT,
  nota            TEXT,
  avvenuto_il     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_cambi_stato_segnalazione (id_segnalazione, avvenuto_il),
  CONSTRAINT fk_cambi_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id),
  CONSTRAINT fk_cambi_da FOREIGN KEY (id_stato_da) REFERENCES stati(id),
  CONSTRAINT fk_cambi_a  FOREIGN KEY (id_stato_a)  REFERENCES stati(id),
  CONSTRAINT fk_cambi_operatore FOREIGN KEY (id_operatore) REFERENCES utenti(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==================== COMMUNITY ====================

CREATE TABLE sostegni (
  id_utente       INT NOT NULL,
  id_segnalazione INT NOT NULL,
  creato_il       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id_utente, id_segnalazione),
  KEY idx_sostegni_segnalazione (id_segnalazione),
  CONSTRAINT fk_sostegni_utente FOREIGN KEY (id_utente) REFERENCES utenti(id),
  CONSTRAINT fk_sostegni_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE commenti (
  id                     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_segnalazione        INT NOT NULL,
  id_autore              INT NOT NULL,
  id_padre               INT,
  testo                  VARCHAR(1000) NOT NULL,
  esito_moderazione      ENUM('ok','dubbio','bloccato'),
  punteggio_moderazione  DECIMAL(4,3),
  nascosto               BOOLEAN NOT NULL DEFAULT FALSE,
  motivo_nascosto        TEXT,
  id_moderatore_nascosto INT,
  creato_il              DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  modificato_il          DATETIME(3),
  eliminato_il           DATETIME(3),
  KEY idx_commenti_segnalazione (id_segnalazione, creato_il),
  CONSTRAINT fk_comm_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id),
  CONSTRAINT fk_comm_autore FOREIGN KEY (id_autore) REFERENCES utenti(id),
  CONSTRAINT fk_comm_padre FOREIGN KEY (id_padre) REFERENCES commenti(id),
  CONSTRAINT fk_comm_moderatore FOREIGN KEY (id_moderatore_nascosto) REFERENCES utenti(id),
  CONSTRAINT chk_comm_testo CHECK (CHAR_LENGTH(TRIM(testo)) > 0),
  CONSTRAINT chk_comm_punteggio CHECK (punteggio_moderazione BETWEEN 0 AND 1),
  CONSTRAINT chk_comm_nascosto
    CHECK (NOT nascosto OR (motivo_nascosto IS NOT NULL AND id_moderatore_nascosto IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE candidati (
  id      SMALLINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nome    VARCHAR(50) NOT NULL,
  cognome VARCHAR(50) NOT NULL,
  lista   VARCHAR(100) NOT NULL,
  email   VARCHAR(254) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE invii (
  id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_segnalazione INT NOT NULL,
  id_candidato    SMALLINT NOT NULL,
  id_moderatore   INT NOT NULL,
  inviato_il      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE KEY uq_invio (id_segnalazione, id_candidato),
  CONSTRAINT fk_invii_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id),
  CONSTRAINT fk_invii_candidato FOREIGN KEY (id_candidato) REFERENCES candidati(id),
  CONSTRAINT fk_invii_moderatore FOREIGN KEY (id_moderatore) REFERENCES utenti(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==================== MODERAZIONE, NOTIFICHE, LOG ====================

CREATE TABLE richieste_revisione (
  id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_richiedente  INT NOT NULL,
  id_segnalazione INT,
  id_commento     INT,
  id_verifica     INT,
  motivo          TEXT NOT NULL,
  stato           ENUM('aperta','accolta','respinta') NOT NULL DEFAULT 'aperta',
  id_moderatore   INT,
  risposta        TEXT,
  creata_il       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  chiusa_il       DATETIME(3),
  CONSTRAINT fk_rev_richiedente FOREIGN KEY (id_richiedente) REFERENCES utenti(id),
  CONSTRAINT fk_rev_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id),
  CONSTRAINT fk_rev_commento FOREIGN KEY (id_commento) REFERENCES commenti(id),
  CONSTRAINT fk_rev_verifica FOREIGN KEY (id_verifica) REFERENCES verifiche_identita(id),
  CONSTRAINT fk_rev_moderatore FOREIGN KEY (id_moderatore) REFERENCES utenti(id),
  CONSTRAINT chk_un_solo_oggetto CHECK (
    (id_segnalazione IS NOT NULL) + (id_commento IS NOT NULL) + (id_verifica IS NOT NULL) = 1
  ),
  CONSTRAINT chk_chiusura CHECK ((stato = 'aperta') = (chiusa_il IS NULL AND id_moderatore IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notifiche (
  id        BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_utente INT NOT NULL,
  tipo      ENUM('verifica_account','stato_account','stato_segnalazione','contenuto_bloccato',
                 'nuovo_commento','risposta_commento','nuova_segnalazione_quartiere','normativa_aggiornata') NOT NULL,
  messaggio VARCHAR(500) NOT NULL,
  link      VARCHAR(500),
  letta     BOOLEAN NOT NULL DEFAULT FALSE,
  creata_il DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  KEY idx_notifiche_utente_letta (id_utente, letta),
  CONSTRAINT fk_notifiche_utente FOREIGN KEY (id_utente) REFERENCES utenti(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE preferenze_notifica (
  id_utente INT NOT NULL,
  tipo      ENUM('verifica_account','stato_account','stato_segnalazione','contenuto_bloccato',
                 'nuovo_commento','risposta_commento','nuova_segnalazione_quartiere','normativa_aggiornata') NOT NULL,
  in_app    BOOLEAN NOT NULL DEFAULT TRUE,
  email     BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (id_utente, tipo),
  CONSTRAINT fk_pref_utente FOREIGN KEY (id_utente) REFERENCES utenti(id),
  CONSTRAINT chk_notifiche_obbligatorie CHECK (
    tipo NOT IN ('verifica_account','stato_account','normativa_aggiornata') OR in_app
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE log_attivita (
  id              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  avvenuto_il     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  attore          ENUM('utente','sistema') NOT NULL,
  id_utente       INT,
  operazione      ENUM('accesso','creazione','modifica','eliminazione','commento','sostegno','cambio_stato',
                       'verifica_identita','decisione_ia','revisione_moderatore','sospensione','cambio_ruolo',
                       'accettazione_normativa') NOT NULL,
  tabella         VARCHAR(50) NOT NULL,
  id_oggetto      BIGINT NOT NULL,
  dati_precedenti JSON,
  dati_nuovi      JSON,
  KEY idx_log_oggetto (tabella, id_oggetto),
  KEY idx_log_utente (id_utente, avvenuto_il),
  CONSTRAINT fk_log_utente FOREIGN KEY (id_utente) REFERENCES utenti(id),
  CONSTRAINT chk_log_attore CHECK ((attore = 'utente') = (id_utente IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==================== TRIGGER ====================

DELIMITER //

-- Età minima 14 anni (un CHECK non può usare CURDATE)
CREATE TRIGGER trg_eta_minima_ins BEFORE INSERT ON utenti FOR EACH ROW
BEGIN
  IF NEW.data_nascita > CURDATE() - INTERVAL 14 YEAR THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Età minima 14 anni';
  END IF;
END//

CREATE TRIGGER trg_eta_minima_upd BEFORE UPDATE ON utenti FOR EACH ROW
BEGIN
  IF NEW.data_nascita > CURDATE() - INTERVAL 14 YEAR THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Età minima 14 anni';
  END IF;
END//

-- Cambio di stato: solo transizioni ammesse, aggiorna lo stato attuale della segnalazione
CREATE TRIGGER trg_cambio_stato BEFORE INSERT ON cambi_stato FOR EACH ROW
BEGIN
  DECLARE v_attuale SMALLINT;
  SELECT id_stato INTO v_attuale FROM segnalazioni WHERE id = NEW.id_segnalazione FOR UPDATE;
  SET NEW.id_stato_da = v_attuale;
  IF NOT EXISTS (SELECT 1 FROM transizioni_ammesse
                 WHERE id_stato_da = v_attuale AND id_stato_a = NEW.id_stato_a) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Transizione di stato non ammessa';
  END IF;
  UPDATE segnalazioni SET id_stato = NEW.id_stato_a, aggiornata_il = CURRENT_TIMESTAMP(3)
  WHERE id = NEW.id_segnalazione;
END//

-- Sostegno: solo su segnalazioni pubbliche e mai sulla propria
CREATE TRIGGER trg_controllo_sostegno BEFORE INSERT ON sostegni FOR EACH ROW
BEGIN
  IF NOT EXISTS (SELECT 1 FROM segnalazioni s JOIN stati st ON st.id = s.id_stato
                 WHERE s.id = NEW.id_segnalazione AND st.pubblico AND NOT s.nascosta) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Si possono sostenere solo segnalazioni pubbliche';
  END IF;
  IF EXISTS (SELECT 1 FROM segnalazioni WHERE id = NEW.id_segnalazione AND id_autore = NEW.id_utente) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'L''autore non può sostenere la propria segnalazione';
  END IF;
END//

-- Commento: solo su segnalazioni pubbliche; la risposta resta nella stessa segnalazione del padre
CREATE TRIGGER trg_controllo_commento BEFORE INSERT ON commenti FOR EACH ROW
BEGIN
  IF NOT EXISTS (SELECT 1 FROM segnalazioni s JOIN stati st ON st.id = s.id_stato
                 WHERE s.id = NEW.id_segnalazione AND st.pubblico AND NOT s.nascosta) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Si possono commentare solo segnalazioni pubbliche';
  END IF;
  IF NEW.id_padre IS NOT NULL AND NOT EXISTS (
       SELECT 1 FROM commenti WHERE id = NEW.id_padre AND id_segnalazione = NEW.id_segnalazione) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La risposta deve riferirsi a un commento della stessa segnalazione';
  END IF;
END//

-- Log append-only (TRUNCATE non attiva i trigger: si usa solo per il reset dei dati demo)
CREATE TRIGGER trg_log_no_update BEFORE UPDATE ON log_attivita FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Il log delle attività non è modificabile';
END//

CREATE TRIGGER trg_log_no_delete BEFORE DELETE ON log_attivita FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Il log delle attività non è modificabile';
END//

DELIMITER ;

-- ==================== VISTE PER LE STATISTICHE ====================

CREATE VIEW v_classifica_segnalazioni AS
SELECT s.id, s.titolo, s.tipo, q.nome AS quartiere, st.nome AS stato,
       (SELECT COUNT(*) FROM sostegni so WHERE so.id_segnalazione = s.id) AS n_sostegni,
       (SELECT COUNT(*) FROM commenti c
         WHERE c.id_segnalazione = s.id AND NOT c.nascosto AND c.eliminato_il IS NULL) AS n_commenti,
       s.creata_il
FROM segnalazioni s
JOIN quartieri q ON q.id = s.id_quartiere
JOIN stati st ON st.id = s.id_stato
WHERE st.pubblico AND NOT s.nascosta AND s.eliminata_il IS NULL;

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
           AND l.avvenuto_il >= UTC_TIMESTAMP(3) - INTERVAL 30 DAY) AS attivita_30_giorni
FROM utenti u
WHERE u.stato_account <> 'eliminato';

-- Classifica pubblica: solo utenti con profilo pubblico, iniziale del cognome
CREATE VIEW v_classifica_utenti_pubblica AS
SELECT id, nome, CONCAT(LEFT(cognome, 1), '.') AS cognome,
       n_segnalazioni, n_commenti_scritti, n_sostegni_ricevuti, attivita_30_giorni
FROM v_statistiche_utenti
WHERE profilo_pubblico;

-- ==================== DATI INIZIALI ====================

INSERT INTO stati (id, nome, finale, pubblico) VALUES
  (1, 'Ricevuta',                FALSE, FALSE),
  (2, 'In attesa',               FALSE, FALSE),
  (3, 'Approvata',               FALSE, TRUE),
  (4, 'Rifiutata',               TRUE,  FALSE),
  (5, 'Presentata ai candidati', TRUE,  TRUE);

INSERT INTO transizioni_ammesse (id_stato_da, id_stato_a) VALUES
  (1, 2), (2, 3), (2, 4), (3, 5);

INSERT INTO categorie (nome) VALUES
  ('Ambiente'), ('Mobilità urbana'), ('Politiche giovanili'), ('Decoro urbano'), ('Sicurezza del territorio');
