# Prompt: IA multi-fornitore a costo zero

Prompt operativo per la sessione di lavoro principale (stesso formato di `01_database.md`).

```text
Nuovo compito: rendere il sistema IA multi-fornitore, a costo zero. Lavora a partire da quanto già fatto sull'IA (piano in docs/piano_ia_openrouter.md, codice in apps/web/core/services/ia/).

Contesto:
- Oggi c'è un solo fornitore, OpenRouter (piano gratuito: 50 richieste al giorno, un solo account). Il client è core/services/ia/openrouter.py con la funzione chiedi(), la quota è in quota.py, il lavoratore in lavoratore.py.
- Abbiamo visto problemi reali: modelli saturi a monte (429 «upstream»), pochi modelli utilizzabili con data_collection="deny", risposte vuote nei blocchi di commenti.
- Vincoli invariati: costo zero, nessun addestramento sui nostri dati, documento e selfie non escono mai dal sito, il modello può solo peggiorare l'esito (ok/dubbio), se non risponde l'esito è dubbio, le prove automatiche non chiamano mai la rete.
- NON creare più account sullo stesso fornitore (violerebbe i termini). Più fornitori diversi vanno bene.

Cosa fare:
1. Trasforma il client in un router: una catena di coppie (fornitore, modello) in ordine di preferenza, configurabile separatamente per testo e per visione (le richieste con foto vanno solo a chi ha visione). Passa al successivo solo per errori che non consumano quota (404 privacy, 403, 429 a monte, rete); mantieni le regole attuali per 429 della nostra quota, risposta non valida, nuovo tentativo su errori 5xx.
2. Un adattatore per fornitore. Parti da Groq e Google AI Studio (API compatibili con OpenAI: cambiano URL, chiave, nome del modello, parametro di privacy). Predisponi Mistral, Cerebras e Cloudflare Workers AI come voci di configurazione da attivare quando l'autore avrà le chiavi. Variabili d'ambiente tipo GROQ_API_KEY, GEMINI_API_KEY ecc., mai nel repository né nei log; aggiorna .env.example e docs/produzione.md.
3. Quota separata per fornitore: ogni fornitore ha limiti e contatore propri (richieste al giorno e al minuto, azzeramento a mezzanotte UTC o altro), letti da configurazione e, dove esiste, dal contatore ufficiale. quota.ammesso() deve dire se almeno un fornitore della catena è disponibile per quel tipo di richiesta. Mostra la quota di ogni fornitore nel pannello /amministrazione/ia/ e nel comando ia_lavora --stato. Il registro (log_attivita, tabella «openrouter») va generalizzato con il nome del fornitore senza rompere i dati esistenti né richiedere modifiche allo schema.
4. Prima di aggiungere un fornitore alla catena controlla sul suo sito limiti attuali e trattamento dei dati nel piano gratuito (il piano gratuito di Google potrebbe usare i dati per addestrare: in quel caso tienilo fuori e dillo all'autore). Non fidarti della memoria: leggi la documentazione.
5. Adatta tools/ia/sonda_modelli.py (prova rapida di un modello con poche richieste) e tools/ia/valuta.py (valutazione sulle 159 etichette di tools/ia/dataset/) per scegliere fornitore e modello da riga di comando e confrontare i fornitori sugli stessi contenuti, con un tetto di richieste per fornitore. Una chiave mancante significa «fornitore non configurato», non un errore.
6. Prove automatiche senza rete (finto server locale, come smoke/ia_openrouter.py): catena che passa al successivo, quota per fornitore, visione solo ai fornitori con visione, chiave mancante, tutti i fornitori falliti → dubbio. Aggiorna smoke/ia_openrouter.py, ia_coda.py e ia_pannello.py; tutte devono restare verdi.
7. Aggiorna docs/piano_ia_openrouter.md (sezione sul multi-fornitore), docs/architettura_ia.md, docs/informativa_ia_bozza.md (elenco dei fornitori che ricevono testi e foto) e CLAUDE.md.

Prima di cominciare: controlla git status. Nell'ultima parte del lavoro precedente c'erano modifiche non committate (prefiltro, prompt, lavoratore con token crescenti sui nuovi tentativi, IA_COMMENTI_BLOCCO=20, valuta.py con rilettura dei commenti puliti) e una valutazione sui 159 contenuti ancora da concludere: verifica che i test ia_*.py passino, poi committa quel lavoro separatamente prima di iniziare il multi-fornitore. Non consumare quota di OpenRouter senza necessità (oggi ne restano poche richieste).

Quando hai finito, dimmi quali chiavi mi servono, dove metterle e come provare ogni fornitore.
```
