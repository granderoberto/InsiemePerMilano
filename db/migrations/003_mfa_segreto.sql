-- Autenticazione a due fattori con app di autenticazione (TOTP).
-- `mfa_segreto` contiene il segreto CIFRATO dall'applicazione (mai in chiaro); è NULL finché la 2FA non è attiva.
SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- Un flag acceso senza segreto è uno stato incoerente (i dati demo avevano il flag senza segreto): lo si spegne prima del vincolo.
UPDATE utenti SET mfa_attiva = FALSE WHERE mfa_attiva;

ALTER TABLE utenti
  ADD COLUMN mfa_segreto VARCHAR(255) NULL AFTER mfa_attiva,
  ADD CONSTRAINT chk_mfa_segreto CHECK (NOT mfa_attiva OR mfa_segreto IS NOT NULL);
