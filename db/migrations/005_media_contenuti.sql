-- Copia dei file caricati (foto e video) nel database, a pezzi da 4 MB.
-- Serve quando il disco dell'hosting è temporaneo (es. piano gratuito): se il file manca dal disco, l'applicazione lo ripristina da qui.
-- Tabella tecnica di supporto: non è un'entità del dominio (non compare nel modello ER). `percorso` è quello di media.percorso.
CREATE TABLE IF NOT EXISTS media_contenuti (
  percorso VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  parte    SMALLINT NOT NULL,
  dati     MEDIUMBLOB NOT NULL,
  PRIMARY KEY (percorso, parte)
) ENGINE=InnoDB;
