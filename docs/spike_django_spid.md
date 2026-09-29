# Prova tecnica Django + SDK SPID/CIE (2026-09-29)

Eseguita in `spike/django-spid/` (non versionata). Nessuna modifica a `defaultdb`; le tabelle create nel
database di test sono state eliminate a fine prova.

| # | Esito | Sintesi |
|---|---|---|
| 1 | NON OK | `spid-cie-oidc-django` 1.6.3 dichiara `Django>=4.0,<5.0`, `pydantic<2`: installa Django 4.2.30 (sicurezza scaduta il 2026-04-07). Con Django 5.2.17 (LTS, fino al 2028-04-30) migrazioni, `check` e login funzionano, ma fuori dal supporto dell'SDK. Python 3.12.6 ok (fino al 2028-10-31); il Dockerfile usa 3.10 (fino al 2026-10-31). |
| 2 | NON OK così com'è / OK con aggiramento | Docker non installato: non provato. Demo locale (TA :8000, RP :8001, OP :8002): login di test fino all'RP con i dati identità. Serve rigenerare la catena di fiducia dell'RP nel Provider (patch anti-SSRF del 2026-08-05: catene scadute e host loopback rifiutati) perché `fetch_openid_relying_parties` ha un `TypeError`. Il link della landing punta alla porta sbagliata; `design-django-theme==v1.4.8` non è nelle dipendenze. |
| 3 | NON OK senza patch / OK con patch | `migrate` su MySQL 8.4: errore 1071 (`kid` `CharField(1024, unique)` in utf8mb4 = 4096 byte > 3072). Con `max_length` 700 nelle migrazioni tutto passa e il login funziona con RP su MySQL. 15 tabelle `spid_cie_oidc_*` + 7 `django_*`/`auth_*`, nessuna collisione col dominio. |
| 4 | OK | Modello `inspectdb` (`managed=False`) su `utenti`: lettura/scrittura ok. Trigger età = `OperationalError` 1644; CHECK = `IntegrityError` 3819; UNIQUE 1062; ENUM non valido = `DataError` 1265. Da correggere a mano: booleani, `db_default`, ENUM. |
| 5 | OK | Modello utente personalizzato su `utenti` senza `auth_user`; bcrypt del seed; login/sessione/admin per ruolo ok. Servono `id = AutoField` (con BigAutoField `admin.0001` fallisce, errore 3780) e `last_login = None`. Non provato: far usare `utenti` all'RP dell'SDK (usa il suo `spid_cie_oidc_accounts.User`; `user_reunification` è sovrascrivibile). |

Scoperta trasversale: due progetti Django sullo stesso database si scontrano su `django_migrations`,
`django_content_type`, `auth_*` (`InconsistentMigrationHistory`).

Non provato: Node (SDK solo RP), PHP, Java, .NET.
