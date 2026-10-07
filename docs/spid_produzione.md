# SPID e CIE reali: cosa serve e come procedere

Il sito oggi parla il **protocollo vero** (OpenID Connect con federazione, SDK `spid-cie-oidc-django`) ma contro un gestore di
identità **di prova**. Per far entrare cittadini veri con SPID e CIE non basta il codice: il Fornitore di Servizi deve essere
**ammesso alla federazione**. Quello che segue è un riepilogo da **verificare sulla documentazione ufficiale** prima di agire
(le regole cambiano).

## Le strade possibili

| Strada | Chi aderisce | Note |
|---|---|---|
| **A. L'ente (scuola o comitato) aderisce direttamente** | Un soggetto pubblico o privato con i requisiti | Per i privati sono richiesti requisiti di onorabilità del rappresentante legale (CIE: art. 5 c. 2 del decreto) e la presentazione di una richiesta all'autorità della federazione. Tempi e costi: da chiedere. |
| **B. Soggetto aggregatore** | Un aggregatore di servizi (pubblici o privati) convenzionato con AgID | L'aggregatore aderisce e fa da intermediario: il tuo sito si collega a lui. Di solito a pagamento. Elenco ufficiale presso AgID. |
| **C. Resta l'ambiente di prova** | nessuno | Va bene per mostrare il protocollo all'esame; non per utenti reali. |

Per CIE esiste un manuale operativo per gli erogatori pubblici e privati
(<https://federazione.servizicie.interno.gov.it/docs/cie-manuale-operativo-docs>); per SPID OIDC le regole tecniche sono su
<https://docs.italia.it/italia/spid/spid-cie-oidc-docs/it/versione-corrente/>.

## Cosa fa l'ente (non automatizzabile)

1. Individuare il **soggetto aderente** (ente, rappresentante legale, referente tecnico, referente amministrativo).
2. Presentare la **richiesta di adesione** come Fornitore di Servizi (SPID e/o CIE) all'autorità di federazione (AgID per SPID, Ministero dell'Interno / IPZS per CIE) o all'aggregatore.
3. Indicare l'**URL pubblico** del servizio in HTTPS, i **dati richiesti** (nome, cognome, data di nascita, email, codice fiscale), la finalità e l'informativa privacy.
4. Superare le **verifiche tecniche** (la federazione controlla il tuo *entity configuration* e i flussi) e ricevere il **trust mark**.

## Cosa prepara il progetto (già pronto o da fare insieme)

| Elemento | Stato |
|---|---|
| Flusso OpenID Connect con federazione (RP) | fatto, provato su ambiente di prova (`apps/web/smoke/spid_e2e.py`) |
| Solo hash SHA-256 del codice fiscale, ponte firmato monouso | fatto |
| Dati richiesti: nome, cognome, email, data di nascita, codice fiscale | fatto (`RP_REQUIRED_CLAIMS` in `apps/spid/servizio_rp/settings.py`) |
| Dominio pubblico HTTPS | da fare con l'hosting (`docs/produzione.md`) |
| Chiavi e *entity configuration* dell'RP **veri** (non quelli di `demo/`) | da generare dall'amministrazione del servizio quando l'ente ha l'URL definitivo |
| Servizio SPID in produzione (gunicorn, database proprio MySQL, `SPID_VERIFICA_SSL=1`, `SPID_AMBIENTE_PROVA=0`) | da preparare dopo l'adesione (checklist in `apps/spid/README.md`) |
| Pagina di scelta del gestore SPID (`SPID_SCELTA_IDP=1`) e pulsanti ufficiali «Entra con SPID» / «Entra con CIE» | da collegare quando si conoscono gli IdP dalla federazione |
| Informativa privacy con il trattamento dei dati SPID/CIE | da aggiornare con i testi del comitato |

## Bozza di richiesta da portare alla scuola o al comitato

> Oggetto: richiesta di adesione come Fornitore di Servizi a SPID e CIE per la piattaforma «La Nostra Città, Il Nostro Futuro»
>
> La piattaforma web «La Nostra Città, Il Nostro Futuro» (comitato «Insieme per Milano») permette ai cittadini maggiorenni e
> maggiori di 14 anni di inviare segnalazioni e proposte sui quartieri di Milano. Per garantire un account per persona e
> l'autenticità dell'identità, si chiede di aderire a SPID e CIE come Fornitore di Servizi tramite OpenID Connect con federazione.
>
> Dati richiesti: nome, cognome, indirizzo email, data di nascita, codice fiscale (del quale si conserva solo l'impronta SHA-256).
> Sito: `https://<dominio>`. Referente tecnico: Roberto Grande. Referente legale: `<nome del rappresentante dell'ente>`.
> Finalità: autenticazione degli utenti della piattaforma civica; nessuna cessione a terzi.

## Quando l'adesione è stata approvata

Torna con: *entity id*, trust anchor, elenco degli IdP, trust mark, eventuali metadati da registrare. A quel punto si configura
`apps/spid` seguendo «Passare alla produzione» e si fa una prova con un'identità vera di un membro del comitato.
