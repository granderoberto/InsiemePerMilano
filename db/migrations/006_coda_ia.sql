-- Coda dei controlli automatici (IA): segnalazioni e commenti in attesa di essere inviati al modello.
-- Tabella tecnica di supporto (come media_contenuti): non è un'entità del dominio e non compare nel modello ER.
-- Un solo lavoratore la consuma, rispettando la quota giornaliera: docs/piano_ia_openrouter.md, §6.
CREATE TABLE IF NOT EXISTS coda_ia (
  id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_segnalazione INT,
  id_commento     INT,
  stato           ENUM('in_coda','in_corso','fatto','saltato','fallito') NOT NULL DEFAULT 'in_coda',
  priorita        TINYINT UNSIGNED NOT NULL DEFAULT 50,     -- rischio del prefiltro locale (0-100): più alto = prima
  impronta        CHAR(64) CHARACTER SET ascii NOT NULL,    -- SHA-256 del testo controllato: una modifica ne crea una nuova
  segnali         JSON,                                     -- segnali del prefiltro (per il moderatore e per il registro)
  tentativi       TINYINT UNSIGNED NOT NULL DEFAULT 0,
  non_prima_di    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  creata_il       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  presa_il        DATETIME(3),
  finita_il       DATETIME(3),
  errore          VARCHAR(200),
  KEY idx_coda_prossima (stato, priorita, creata_il),
  CONSTRAINT fk_coda_segnalazione FOREIGN KEY (id_segnalazione) REFERENCES segnalazioni(id),
  CONSTRAINT fk_coda_commento FOREIGN KEY (id_commento) REFERENCES commenti(id),
  CONSTRAINT chk_coda_un_oggetto CHECK ((id_segnalazione IS NOT NULL) + (id_commento IS NOT NULL) = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
