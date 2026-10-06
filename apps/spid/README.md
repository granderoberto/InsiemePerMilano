# Servizio SPID/CIE

Relying Party **OpenID Connect con federazione** (le regole tecniche comuni di AgID per SPID e CIE), basato sull'SDK
[`spid-cie-oidc-django`](https://github.com/italia/spid-cie-oidc-django) di Developers Italia. È un progetto Django **separato**
dal sito (regola 5 di `CLAUDE.md`): ha il suo database e le sue chiavi.

```
 Cittadino ──▶ Sito (:8000) ──▶ Servizio RP (:8011) ──▶ Gestore di identità (SPID / CIE)
                  ▲                    │                         │
                  └──── token firmato ◀┴── verifica firme/token ◀─┘
```

1. Il sito manda l'utente a `/ponte/avvia/?profilo=spid|cie`.
2. L'SDK avvia l'autenticazione verso il gestore: verifica la catena di fiducia della federazione, firma la richiesta con la chiave
   dell'RP (PKCE, `private_key_jwt`), riceve e **verifica firme e token** (ID token, access token, `at_hash`) e legge gli attributi.
3. Il **ponte** (`ponte/views.py`) firma un token a scadenza (120 s) con nome, cognome, email, data di nascita e codice fiscale,
   **cancella** utenti, autenticazioni e token temporanei dell'SDK e rimanda l'utente al sito.
4. Il sito (`apps/web/portale/views_spid.py`) accetta solo token firmati con il segreto condiviso, monouso e legati al browser che ha
   iniziato l'accesso. Alla prima volta chiede di completare il profilo (quartiere, normative); del codice fiscale salva **solo
   l'impronta SHA-256**. Un account per persona.

## Ambiente di prova (oggi)

Usa la federazione di **test** dell'SDK: un Trust Anchor e un gestore di identità finto. Il protocollo e il codice sono quelli veri; i dati
no. Credenziali del gestore di prova: utente `user`, password `oidcuser`.

```bash
# una tantum: ambiente Python, SDK a versione fissata, trust anchor e gestore di prova (porte 8010 e 8012)
apps/spid/demo/prepara.sh
# ogni volta: avvia trust anchor (8010), servizio RP (8011), gestore di prova (8012) e rinnova la catena di fiducia
apps/spid/demo/avvia.sh        # ferma con apps/spid/demo/ferma.sh
```

Nel file `.env` della radice servono `SPID_BRIDGE_SECRET` (lo stesso per sito e servizio) e `SPID_SERVIZIO_URL=http://127.0.0.1:8011`
(per il sito). Poi il sito mostra «Entra con SPID / CIE» in `/accedi/spid/`. Controlli: `apps/web/smoke/spid.py` (sicurezza del
ritorno, non richiede il servizio) e `apps/web/smoke/spid_e2e.py` (flusso completo, richiede servizio e sito accesi).

Il servizio gira su `127.0.0.1` come il sito e il gestore di prova: i cookie non distinguono le porte, quindi ogni servizio ha
cookie con nome proprio.

## Passare alla produzione (non fatto: richiede un ente)

L'accesso reale richiede l'**adesione di un ente** come Fornitore di Servizi (per esempio la scuola) a SPID e a CIE, oppure il
passaggio da un soggetto aggregatore. Dopo l'adesione, in sintesi (verificare i passaggi sulla documentazione ufficiale:
<https://docs.italia.it/italia/spid/spid-cie-oidc-docs/it/versione-corrente/>):

1. **Dominio pubblico in HTTPS** per sito e servizio; `SPID_SITO_URL`, `SITE_URL`, `SPID_VERIFICA_SSL=1`, `SPID_AMBIENTE_PROVA=0`, `SPID_DEBUG=0`.
2. **Chiavi e configurazione di federazione dell'RP** (entity configuration, metadati, `authority_hints`): generate dall'amministrazione
   del servizio (`/admin-spid/`) e non quelle di esempio contenute in `demo/`. Le chiavi di prova non vanno mai usate in produzione.
3. **Trust Anchor e identity provider ufficiali**: `SPID_TRUST_ANCHOR`, `SPID_PROVIDER_CIE`, l'elenco dei gestori SPID (`SPID_SCELTA_IDP=1`
   mostra la pagina di scelta dell'SDK) e i *trust mark* rilasciati dopo l'onboarding.
4. **Database proprio** (`SPID_DB_ENGINE=mysql`, schema separato) e server di produzione (gunicorn). Le migrazioni dell'SDK su MySQL
   richiedono `max_length` 1024 → 700 sul campo `kid` (vedi `docs/spike_django_spid.md`).
5. Superutente proprio del servizio (`createsuperuser`): `demo/prepara.sh` rimuove l'amministratore dimostrativo dell'SDK.
6. Pulizia periodica dei dati temporanei e controllo dei log (il ponte non scrive dati personali nei log).

## Note

- L'SDK dichiara `Django<5.0` (4.2 è fuori supporto): si installa senza dipendenze su Django 5.2 (`demo/prepara.sh`).
- L'esempio dell'SDK contiene catene di fiducia scadute: `avvia.sh` le rinnova (vale solo per questa demo).
- La data di nascita si chiede all'IdP (`birthdate`); se non la fornisce, il sito la chiede all'utente.
