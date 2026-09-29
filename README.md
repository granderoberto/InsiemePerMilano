# La Nostra Città, Il Nostro Futuro

Progetto d'esame (5° anno, indirizzo informatica): piattaforma web civica per il comitato **"Insieme per Milano"**.
I cittadini inseriscono segnalazioni e proposte sui quartieri, la community le sostiene e le commenta, i moderatori
le fanno avanzare fino alla presentazione ai candidati Sindaco. L'intelligenza artificiale supporta verifica
dell'identità, classificazione, moderazione e controllo di coerenza, ma l'ultima parola resta sempre a una persona.

Autore: Roberto Grande (GitHub: [Bertox0](https://github.com/Bertox0)). Lingua del progetto: **italiano**.

## Stato

| Materiale richiesto dalla traccia | Stato | Dove |
|---|---|---|
| 1. Analisi dei requisiti | fatto | [`docs/specifiche_utente.md`](docs/specifiche_utente.md) |
| 2a. Modello ER (notazione di Chen) | fatto | [`docs/modello_er.pdf`](docs/modello_er.pdf), [`docs/modello_er.md`](docs/modello_er.md) |
| 2b. Schema logico normalizzato | fatto (MySQL 8) | [`db/schema.sql`](db/schema.sql), [`db/schema.dbml`](db/schema.dbml) |
| Database su Aiven con dati demo | fatto | [`db/`](db/README.md), [`tools/`](tools/) |
| 3. Architettura di integrazione IA (schema a blocchi) | da fare | |
| Implementazione della web app | da fare (stack scelto: Django) | [`docs/spike_django_spid.md`](docs/spike_django_spid.md) |

## Da dove iniziare a leggere

1. [`docs/specifiche_utente.md`](docs/specifiche_utente.md): che cosa deve fare la piattaforma. È la **fonte di verità**: ogni modifica funzionale parte da lì.
2. [`docs/modello_er.md`](docs/modello_er.md) e il diagramma [`docs/modello_er.png`](docs/modello_er.png): entità, associazioni e vincoli.
3. [`db/schema.sql`](db/schema.sql): come il modello diventa tabelle, trigger e viste.
4. [`CLAUDE.md`](CLAUDE.md): regole di lavoro, comandi, decisioni di dominio e di stack. È il documento più completo per chi (persona o assistente) deve continuare il lavoro.
5. [`docs/handoff.md`](docs/handoff.md): stato aggiornato e cosa resta da fare.

## Struttura del repository

```
.
├── README.md                  questo file
├── CLAUDE.md                  regole di lavoro, comandi, decisioni, stack, regola migrazioni SQL/Django
├── docs/
│   ├── specifiche_utente.md   specifica funzionale completa (fonte di verità)
│   ├── modello_er.md          entità, chiavi, associazioni con cardinalità, vincoli extra-diagramma
│   ├── modello_er.{pdf,svg,png}   diagramma ER generato
│   ├── handoff.md             stato del lavoro e prossimi passi
│   ├── spike_django_spid.md   esiti della prova tecnica su Django e sull'SDK SPID/CIE
│   └── prompt/
│       └── 01_database.md     prompt operativo della fase database (fase 1, conclusa)
├── db/
│   ├── README.md              come ricreare il database da zero
│   ├── schema.sql             schema completo di riferimento (tabelle, trigger, viste, dati iniziali)
│   ├── schema.dbml            stesso schema per dbdiagram.io (solo tabelle e relazioni)
│   ├── test_vincoli.sql       casi di test dei vincoli (le righe "ERRORE ATTESO" devono fallire)
│   ├── migrations/            001_schema.sql, 002_dati_riferimento.sql (applicate da migrate.sh)
│   └── data/                  GeoJSON sorgente di NIL e Municipi (Comune di Milano) + README con le fonti
└── tools/
    ├── requirements.txt       dipendenze Python degli script
    ├── db/migrate.sh          applica le migrazioni a un database (idempotente)
    ├── geo/import_quartieri.py   importa gli 88 NIL nella tabella `quartieri`
    ├── seed/                  seed.py: dati demo deterministici; README con la password demo
    └── er/                    gen.py (dati del modello ER) e pipeline che disegna il diagramma
```

Non sono nel repository, per scelta: `.env` (credenziali), `certs/` (certificato del servizio),
`tools/.venv/` (ambiente Python) e `spike/` (prove tecniche locali). Sono elencati in `.gitignore`.

## Il database in breve

MySQL 8 su Aiven (piano Free), InnoDB, utf8mb4, DATETIME sempre in UTC. **21 tabelle** (più `schema_migrations`, che tiene traccia delle migrazioni), 7 trigger, 3 viste.

- **Utenti e accesso:** `utenti`, `verifiche_identita`, `sospensioni`, `documenti_normativi`, `consensi`, `quartieri`.
- **Segnalazioni:** `segnalazioni`, `media`, `categorie`, `classificazioni`, `stati`, `transizioni_ammesse`, `cambi_stato`.
- **Community:** `sostegni`, `commenti`, `candidati`, `invii`.
- **Moderazione e tracciabilità:** `richieste_revisione`, `notifiche`, `preferenze_notifica`, `log_attivita` (solo aggiunte: i trigger bloccano UPDATE e DELETE).
- **Viste per le statistiche:** `v_classifica_segnalazioni`, `v_statistiche_utenti`, `v_classifica_utenti_pubblica`.

Ciclo di vita di una segnalazione: Ricevuta → In attesa → Approvata o Rifiutata; Approvata → Presentata ai candidati.
Le transizioni sono in `transizioni_ammesse` e imposte da un trigger. Sono pubblici solo gli stati Approvata e Presentata.

Vincoli che il database **non** impone e che spettano all'applicazione: almeno un media per segnalazione, limite di
5 segnalazioni al giorno, confine esatto di Milano, permessi per ruolo. L'elenco è in [`CLAUDE.md`](CLAUDE.md).

## Provarlo

Servono il client `mysql`, Python 3.11+ e le credenziali del servizio in un file `.env` (non versionato) con
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, più il certificato in `certs/ca.pem`.
Istruzioni complete in [`db/README.md`](db/README.md).

```bash
python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt

tools/db/migrate.sh <database>                                       # schema, trigger, viste, dati di riferimento
tools/.venv/bin/python tools/geo/import_quartieri.py <database>      # 88 quartieri (NIL) con confini
tools/.venv/bin/python tools/seed/seed.py <database>                 # dati demo (svuota le tabelle non di riferimento)
```

Per il diagramma ER: modificare `tools/er/gen.py` e lanciare `tools/er/run.sh`. Lo schema `db/schema.dbml` si incolla su
[dbdiagram.io](https://dbdiagram.io); `db/schema.sql` **no** (contiene `DELIMITER` e trigger che quel parser rifiuta).

## Regole da tenere a mente

- **Sincronizzazione:** `db/schema.sql`, `db/migrations/`, `db/schema.dbml` e `tools/er/gen.py` descrivono lo stesso schema e vanno aggiornati insieme. Le modifiche a uno schema già applicato su Aiven si fanno con una **nuova migrazione**, non riscrivendo la 001 o la 002.
- **Nomi:** `snake_case`, tabelle al plurale nello SQL (`utenti`), entità al singolare maiuscolo nell'ER (`UTENTE`).
- **Nel modello ER non compaiono chiavi esterne**: le rappresentano le associazioni.
- **Segreti:** mai nel repository. Credenziali solo in `.env`; gli script non stampano la password.
- **Dati demo:** tutti fittizi (nomi generati, email `@example.*`, codici fiscali casuali salvati solo come hash).

## Stack previsto

App principale in **Django 5.2 LTS**, con MySQL su Aiven. L'accesso SPID/CIE passa da un servizio separato basato
sull'SDK [`spid-cie-oidc-django`](https://github.com/italia/spid-cie-oidc-django). Motivi, prove e regole di convivenza
tra migrazioni SQL e Django: [`docs/spike_django_spid.md`](docs/spike_django_spid.md) e sezione "Stack applicativo" di
[`CLAUDE.md`](CLAUDE.md).

## Fonti e licenze dei dati

I confini di quartieri (NIL) e Municipi provengono dal portale Open Data del Comune di Milano
([dati.comune.milano.it](https://dati.comune.milano.it)), licenza **CC BY**: «Dati: Comune di Milano, CC BY».
Dettagli in [`db/data/README.md`](db/data/README.md).
