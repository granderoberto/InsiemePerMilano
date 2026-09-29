-- Dati di riferimento: stati, transizioni ammesse, categorie.

SET NAMES utf8mb4;
SET time_zone = '+00:00';

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
