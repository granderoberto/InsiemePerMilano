# Piano: intelligenza artificiale vera con OpenRouter, a costo zero

Bozza del 2026-10-26, da approvare prima di scrivere codice. Parte da `docs/architettura_ia.md` (flussi A, B, C e principi) e dall'interfaccia già pronta in `apps/web/core/services/ia/__init__.py`.

**Vincolo di progetto: nessuna spesa.** Niente crediti, niente piani a pagamento, niente secondi account per aggirare i limiti (violano i termini di OpenRouter). Il piano si costruisce attorno alla quota gratuita: **20 richieste al minuto e 50 al giorno** per l'intero account, valide per tutti i modelli `:free` insieme ([documentazione](https://openrouter.ai/docs/guides/routing/model-variants/free), conferma in [questa guida](https://pinggy.io/blog/free_ai_model_apis_unlimited_tokens_openrouter/)). Il numero va riverificato prima di fissarlo nel codice.

## 1. Punto di partenza

- L'interfaccia unica esiste già (`controlla_testo`, `suggerisci_categorie`, `coerenza_immagine_testo`, `verifica_documento`); il fornitore si sceglie con `IA_BACKEND`. Oggi dietro c'è il simulato (parole chiave).
- La verifica del documento è già **vera e locale** (Tesseract, MRZ, OpenCV). Non cambia e non usa quota.
- Se un controllo non risponde l'esito è `dubbio`, mai il silenzio. Con 50 richieste al giorno questo caso **sarà normale**, non eccezionale: è la regola da progettare bene.

## 2. Il budget: 50 richieste al giorno

Il giorno di OpenRouter si azzera a mezzanotte UTC (verifica da fare nella fase 0). Ripartizione proposta:

| Voce | Richieste al giorno | Note |
|---|---|---|
| Segnalazioni | 36 | una richiesta ciascuna, con testo, categorie, coerenza e foto insieme |
| Commenti in blocco | 8 | blocchi da 10 a 25 commenti in una sola richiesta, al massimo 8 al giorno |
| Riserva | 6 | errori, nuovi tentativi, prove a mano |

Ogni richiesta, anche se fallisce, conta. Quindi:

- **Nessun nuovo tentativo su 429**; un solo tentativo su errore del server o scadenza del tempo.
- **Nessuna chiamata per i dati demo** né per le modifiche che non cambiano testo o foto (si confronta un'impronta del contenuto).
- **Contatore nel database** senza nuove tabelle: si contano le righe di `log_attivita` con `decisione_ia` e fornitore `openrouter` del giorno UTC, registrando anche i fallimenti. Il pannello amministratore mostra «usate oggi N di 50».
- **Soglia di sicurezza**: oltre l'88% (44) l'IA lavora solo sulle segnalazioni; esaurita la quota, tutto passa dal controllo locale e va in coda al moderatore con il motivo «quota IA giornaliera esaurita».

Capacità: circa **36 segnalazioni controllate al giorno** e circa 50 commenti. Per un comitato cittadino al lancio basta; se i volumi crescono, le segnalazioni oltre quota non si perdono: restano `In attesa` per il moderatore.

## 3. Cosa gestisce l'IA e cosa resta locale

| # | Flusso | Chi lo fa | Costo in richieste |
|---|---|---|---|
| 1 | Prefiltro del testo (insulti, minacce, telefoni, email, targhe) | **locale**: regole del simulato + espressioni regolari | 0 |
| 2 | Moderazione del testo di una segnalazione | LLM di testo, JSON a schema fisso, **insieme** a categorie e coerenza | 1 per segnalazione |
| 3 | Categorie suggerite | stessa richiesta del punto 2; se manca la quota, suggerimento locale per parole chiave (già nel simulato) | 0 |
| 4 | Foto: contenuti sessuali o violenti e coerenza col testo | stessa richiesta, con 1-4 foto ridotte a 768 px; modello con visione | 0 in più |
| 5 | Testo nelle immagini (OCR) | **locale** (Tesseract), il testo letto passa al prefiltro e va nella richiesta | 0 |
| 6 | Video | fotogrammi campione con `ffmpeg` (al massimo 3) nella stessa richiesta del punto 4 | 0 in più |
| 7 | Commenti | **dopo la pubblicazione**: il prefiltro locale blocca i casi gravi subito; gli altri escono e la coda li fa rivedere dall'IA a blocchi, che segnala al moderatore quelli dubbi | 1 ogni fino a 25 commenti |
| 8 | Verifica del documento | **locale, mai verso OpenRouter** (dati biometrici, art. 9 GDPR) | 0 |

Una richiesta unica per segnalazione è la scelta che regge il budget: testo, categorie, foto e coerenza tornano in un solo JSON.

Per risparmiare ancora, da valutare in fase 3 (mie ipotesi):
- Un classificatore locale per nudità (modello ONNX piccolo) toglierebbe le foto dalla richiesta: da controllare licenza e peso sul piano da 512 MB di Render.
- Autori con molte segnalazioni già approvate potrebbero saltare l'IA e andare solo al prefiltro. Riduce la copertura: si decide dopo la taratura.

Fuori da questo piano: riassunti per il moderatore, rilevamento di doppioni con embedding, riassunti per i candidati.

## 3 bis. Il prefiltro locale decide se il modello serve

Prima di ogni invio il testo passa da controlli in Python, **senza IA**. Il prefiltro ha tre esiti, e solo uno consuma quota:

| Esito del prefiltro | Condizione | Cosa succede |
|---|---|---|
| **bloccato** | segnale grave e certo (insulto o minaccia esplicita, tentativo di aggirare i filtri) | nessuna richiesta al modello; esito `bloccato` |
| **da inviare** | segnale dubbio, oppure la segnalazione ha foto (la visione serve sempre), oppure testo lungo con più temi | entra nella coda del modello |
| **pulito** | nessun segnale, solo testo, categoria locale con confidenza alta | nessuna richiesta; esito `ok` marcato come «solo controllo locale» (scelta confermata dall'autore: nessuna richiesta sui testi puliti; la soglia si ricontrolla dopo la taratura) |

Controlli, con librerie standard o piccole (da valutare peso e licenza):
- **Normalizzazione**: `unicodedata` (accenti, caratteri simili, spazi invisibili), lettere ripetute e sostituzioni tipo `c4zzo`.
- **Elenco di parole offensive e di minaccia** in italiano e milanese, con confronto approssimato (`rapidfuzz`) per le varianti scritte male.
- **Dati personali di terzi**: telefoni (`phonenumbers`), email e indirizzi web (espressioni regolari), targhe, codici fiscali e IBAN (`python-stdnum`).
- **Spam e rumore**: maiuscole in eccesso, caratteri ripetuti, troppi indirizzi web, testo troppo corto o senza lettere; lingua non italiana (`lingua-py`, se il peso lo consente).
- **Doppioni**: impronta del testo normalizzato e somiglianza con le segnalazioni recenti dello stesso autore (`rapidfuzz`); un doppione esatto non rientra nel modello.
- **Categoria locale**: parole chiave per categoria (già nel simulato) con una confidenza; serve anche come riserva se manca la quota.

Il prefiltro produce un **punteggio di rischio** e un elenco di segnali. Il punteggio decide anche la **priorità** nella coda del modello (rischio alto prima).

## 4. Modelli gratuiti

Elenco attuale dall'API pubblica dei modelli (26 ottobre 2026): 17 modelli `:free`. Con visione `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free`, `nvidia/nemotron-3.5-super-vl:free`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`. Per la moderazione `nvidia/nemotron-3.5-content-safety:free` (testo e immagini). Di solo testo con JSON strutturato `nvidia/nemotron-3-super-120b-a12b:free`.

- Gli identificativi cambiano spesso: stanno in configurazione, con una **catena di riserva**. Passare al modello successivo dopo un errore **consuma una richiesta**, quindi la catena si usa solo su errore del server, non su risposta di bassa qualità.
- Qualità e tempi non sono garantiti.
- **Privacy**: la richiesta porta `provider.data_collection = "deny"` e l'account ha l'impostazione corrispondente. Se con quel vincolo nessun modello gratuito risponde, le foto non si inviano (restano al solo controllo locale) e si decide su testo e commenti.

## 5. Architettura

```
core/services/ia/__init__.py             interfaccia unica (invariata, +1 funzione per testo+foto in blocco)
core/services/ia/openrouter.py           client HTTP: timeout, 429 senza nuovi tentativi, JSON, catena di modelli
core/services/ia/quota.py                contatore giornaliero dal registro, soglie, motivo «quota esaurita»
core/services/ia/coda.py                 coda persistente: inserimento, priorità, presa in carico, esito
core/services/ia/lavoratore.py           ciclo che consuma la coda rispettando 20/min e 50/giorno
core/services/ia/backend_openrouter.py   funzioni del contratto, prompt, lettura e controllo del JSON
core/services/ia/prefiltro.py            regole locali e espressioni regolari sui dati personali
core/services/ia/prompt/                 testi dei prompt, versionati
```

Regole di decisione (estensione di «esito = il peggiore»):
1. Il prefiltro decide subito i casi evidenti (`bloccato`).
2. Il modello può solo **peggiorare** l'esito del prefiltro, mai migliorarlo.
3. Risposta non valida, scadenza, quota esaurita o modello assente: `dubbio` con motivo (comportamento già implementato).
4. Soglie dei punteggi in impostazioni, tarate nella fase 5.

### Risposta del modello sui commenti

Nella rilettura a blocchi il modello restituisce, per ogni commento, un oggetto con un valore **booleano** e una **motivazione**:

```json
{"risultati": [
  {"id": 812, "approvato": true,  "motivazione": ""},
  {"id": 813, "approvato": false, "motivazione": "insulto a un utente"}
]}
```

- `id`: l'identificativo del commento, ricevuto nella richiesta; il modello non inventa né cambia gli id.
- `approvato`: `true` se il commento rispetta le regole (nessun insulto, odio, minaccia, spam, dati personali di terzi), `false` altrimenti.
- `motivazione`: **poche parole** (al massimo 8, sotto i 60 caratteri), obbligatoria quando `approvato` è `false`, stringa vuota quando è `true`. Serve a spendere pochi token e basta al moderatore per capire il motivo. Il prompt chiede la forma «insulto a un utente», «minaccia», «numero di telefono», senza frasi complete; `max_tokens` della risposta è calcolato sul numero di commenti (circa 20 token ciascuno).

Regole di lettura:
1. Lo schema è fisso e validato: id mancanti, in più o ripetuti, tipi sbagliati o `approvato: false` senza motivazione rendono **dubbio** il commento interessato, non tutto il blocco.
2. `approvato: true` → `ok`. `approvato: false` → **`dubbio`** (coda del moderatore con la motivazione): il solo giudizio del modello non nasconde un commento. `bloccato` resta riservato al prefiltro locale e alla decisione del moderatore.
3. Un commento già segnato dal prefiltro non può essere riportato a `ok` dal modello.
4. La motivazione è testo del modello: si mostra come testo semplice (mai come HTML) e se supera i 60 caratteri si tronca.

La stessa forma (`approvato` + `motivazione`) vale per il commento singolo che arriva quando c'è quota di sobra. Per le segnalazioni il JSON è più ricco (punteggi, categorie, coerenza) e si definisce nella fase 2.

Testo ostile (*prompt injection*): il contenuto dell'utente va in un blocco delimitato e dichiarato come dato; il modello risponde solo con JSON a schema fisso; un campo fuori schema scarta la risposta; categorie solo dall'elenco chiuso; il modello non decide azioni, solo punteggi.

Tracciabilità: in `log_attivita` (`decisione_ia`) si salvano modello, versione del prompt, latenza, punteggi e se la richiesta è riuscita. Sono nel JSON del registro: **nessuna modifica allo schema**.

## 6. Esecuzione: il controllo avviene dietro le quinte

**L'utente non vede il lavoro del controllo.** Quando invia una segnalazione la vede subito in stato **In attesa**, come ora, e basta. Non c'è schermata di attesa né messaggio di errore dovuto all'IA: il controllo è un flusso del backend che gira per conto suo.

```
utente invia ──> salva segnalazione (stato 2 In attesa, esito_moderazione = NULL)
                   │ stessa transazione
                   └─> prefiltro locale ──> bloccato: esito subito, niente coda
                                        ├─> pulito: esito ok locale, niente coda
                                        └─> da inviare: riga in coda_ia (priorità = rischio)

lavoratore (backend)  ──> prende la riga più urgente ──> rispetta limite al minuto e al giorno
                      ──> richiesta al modello ──> valida il JSON ──> scrive esito, punteggi, log
                      ──> notifica l'autore solo se serve (bloccato) e aggiorna la coda del moderatore
```

**Coda persistente `coda_ia`** (nuova migrazione `006`, da riportare nei quattro artefatti: `schema.sql`, `migrations/`, `schema.dbml`, `tools/er/gen.py`, e nel modello logico). Campi: tipo (`segnalazione`, `commento`), id dell'oggetto, stato (`in_coda`, `in_corso`, `fatto`, `saltato`, `fallito`), priorità, impronta del contenuto, tentativi, `non_prima_di`, creata/presa/finita, errore breve. Perché una tabella e non un thread in memoria: il processo di Render si riavvia e si spegne dopo 15 minuti senza visite, e la coda non deve perdersi.

**Il lavoratore** è un solo ciclo, in un thread avviato con il sito, che:
1. prende **una sola riga alla volta** con un blocco su database (`GET_LOCK` o `UPDATE ... WHERE stato = 'in_coda'`), così non partono due richieste insieme anche con più thread;
2. ordina per priorità e poi per età; i commenti si raggruppano in blocchi fino a 25;
3. controlla prima la quota (`quota.py`) e distanzia le richieste (limite al minuto, con margine, per esempio una ogni 4 secondi): niente raffiche, niente 429;
4. applica un tempo massimo alla chiamata (25 secondi); su scadenza o errore del server riprova **una volta** dopo un'attesa, poi segna `fallito`;
5. a quota esaurita non fa nulla fino a mezzanotte UTC e le righe restano `in_coda`: le segnalazioni non diventano `dubbio` per questo motivo, **aspettano**; solo se restano in coda oltre 24 ore passano a `dubbio` («controllo non completato») per il moderatore.

**Cosa vede il moderatore in attesa dell'esito.** Una segnalazione con `esito_moderazione = NULL` compare nella coda con l'etichetta «controllo automatico in corso» e il pulsante di approvazione non attivo, per evitare che si pubblichi un contenuto non ancora controllato. Rifiutare resta sempre possibile. Dopo 24 ore dall'invio senza esito il pulsante si sblocca insieme al `dubbio`. Anche questa è una mia scelta, da confermare.

**Se il sito dorme.** Il piano gratuito di Render spegne il processo dopo circa 15 minuti senza visite; la coda resta nel database e il lavoratore riparte al primo avvio (`ia_riprendi` all'avvio). Un servizio di controllo esterno gratuito che visiti `/salute/` ogni 10 minuti terrebbe sveglio il sito e il lavoratore: opzionale, da decidere.

**Commenti.** Un commento è pubblicato subito, passa dal prefiltro e, se serve, entra nella stessa coda. Un blocco di commenti parte quando ce ne sono almeno 10 in coda o il più vecchio ha più di 6 ore: il passaggio non ha un orario fisso, quindi niente scheduler esterno.

## 7. Fasi

| Fase | Contenuto | Verifica |
|---|---|---|
| 0 | Account OpenRouter, chiave in `.env` e su Render, privacy; `tools/ia/sonda_modelli.py` prova i modelli (10 frasi italiane, 5 foto) **con meno di 15 richieste** e controlla l'orario di azzeramento della quota | tabella dei risultati nel repo; scelta dei modelli |
| 1 | Client `openrouter.py` e `quota.py` con prove su risposte simulate (429, scadenza, JSON rotto, quota esaurita) | prove in `smoke/` senza rete |
| 2 | Prefiltro locale con i tre esiti (bloccato, da inviare, pulito), migrazione `006_coda_ia` e modelli, coda e lavoratore, richiesta unica per le segnalazioni di solo testo; attivabile per ambiente con `IA_BACKEND` | prove su un set di frasi, sulla coda (ordine, blocco, ripresa) e sul limite al minuto |
| 3 | Foto, coerenza, video a fotogrammi; lavoratore con foto, `ia_riprendi`; valutazione del classificatore locale per la nudità | prove con foto di esempio |
| 4 | Commenti a blocchi nella stessa coda; coda del moderatore con «controllo in corso»; pannello amministratore con quota usata e coda | prova con quota bassa |
| 5 | Taratura: 60-100 contenuti italiani etichettati a mano, `tools/ia/valuta.py` (una richiesta per ogni gruppo di contenuti, non una per contenuto), soglie scelte sui risultati | rapporto in `docs/` |
| 6 | Documenti: `architettura_ia.md` (fornitore, quota, flussi), informativa IA (fornitore terzo, cosa si invia), `produzione.md` (variabili), `README` | rilettura |
| 7 | Messa online e prova reale di una segnalazione e di un commento | prova sul sito |

Le prove automatiche **non chiamano mai la rete** (ogni chiamata consuma quota). Solo `sonda_modelli.py` e `valuta.py` la usano, a mano e con un tetto di richieste.

## 8. Rischi

| Rischio | Risposta |
|---|---|
| La quota finisce a metà giornata | soglia di sicurezza, priorità alle segnalazioni, resto al moderatore con motivo chiaro; pannello con contatore |
| Un modello gratuito sparisce o peggiora | catena di riserva in configurazione; la sonda si può ripetere |
| Falsi positivi su italiano colloquiale | soglie tarate, `dubbio` invece di `bloccato` nei casi incerti, revisione umana richiedibile |
| Foto con volti o targhe inviate a terzi | scelta accettata dall'autore; EXIF già tolto, avviso nell'informativa, sfocatura dei volti con YuNet (già presente) prima dell'invio, da fare in fase 3 |
| Un abuso consuma la quota (spam di segnalazioni) | limite di 5 al giorno per utente già presente; si può aggiungere un tetto per utente sull'IA |
| Sito lento per le attese | nessuna: l'utente non attende mai l'IA, la richiesta parte dalla coda |
| Coda che si accumula (quota finita, sito spento) | priorità per rischio, età massima 24 ore, contatore e coda nel pannello amministratore |
| Chiave API esposta | solo variabile d'ambiente, mai nel repo né nei log |
| I termini del servizio gratuito cambiano | il backend è sostituibile con `IA_BACKEND`; il simulato resta il fallback |

## 9. Decisioni e domande aperte

**Decise dall'autore**
- Vincolo di costo zero: si lavora dentro la quota gratuita (sezione 2).
- I testi puliti (senza segnali e senza foto) restano al solo controllo locale: nessuna richiesta al modello.
- Le foto delle segnalazioni, già senza EXIF, **possono andare al fornitore esterno**, con avviso nell'informativa IA (fase 6). Restano esclusi documento e selfie. Resta la cautela sul parametro `data_collection = "deny"`: se nessun modello gratuito lo accetta, la fase 0 lo segnala e se ne riparla.

**Ancora aperta**
1. **Commenti dopo la pubblicazione**: la rilettura a blocchi costa poche richieste; un commento dubbio resta visibile fino al blocco successivo (al massimo circa 6 ore). Va bene?
2. **Approvazione bloccata** finché manca l'esito (sezione 6, fino a 24 ore): va bene per il moderatore?
