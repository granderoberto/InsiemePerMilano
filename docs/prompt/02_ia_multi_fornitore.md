# Prompt: IA multi-fornitore a costo zero

Prompt operativo per la sessione di lavoro principale (stesso formato di `01_database.md`).

```text
Nuovo compito: rendere il sistema IA multi-fornitore, a costo zero. Lavora a partire da quanto già fatto sull'IA (piano in docs/piano_ia_openrouter.md, codice in apps/web/core/services/ia/).

Contesto:
- Oggi c'è un solo fornitore, OpenRouter (piano gratuito: 50 richieste al giorno, un solo account). Il client è core/services/ia/openrouter.py con la funzione chiedi(), la quota è in quota.py, il lavoratore in lavoratore.py.
- Abbiamo visto problemi reali: modelli saturi a monte (429 «upstream»), pochi modelli utilizzabili con data_collection="deny", risposte vuote nei blocchi di commenti.
- Vincoli invariati: costo zero, documento e selfie non escono mai dal sito (in ogni modalità), il modello può solo peggiorare l'esito (ok/dubbio), se non risponde l'esito è dubbio, le prove automatiche non chiamano mai la rete.
- NON creare più account sullo stesso fornitore (violerebbe i termini). Più fornitori diversi vanno bene.

Decisione dell'autore sulla privacy (progetto didattico): il vincolo «nessun addestramento sui nostri dati» diventa un'impostazione, non una regola fissa. Aggiungi IA_PRIVACY con due valori:
- rigida (PREDEFINITO): ogni richiesta chiede al fornitore di non usare i dati per l'addestramento (data_collection="deny" su OpenRouter, equivalente sugli altri) e si usano solo fornitori e modelli che lo garantiscono. È il comportamento di oggi.
- didattica: il vincolo si toglie; entrano nella catena anche i modelli e i fornitori che possono usare i dati per addestrare (modelli gratuiti NVIDIA/Liquid su OpenRouter, piano gratuito di Google AI Studio e simili). Va dichiarata nell'informativa.
In ENTRAMBE le modalità restano ferme: documento e selfie non vanno mai all'esterno; le foto partono senza metadati e con i volti sfocati; nessun nome, email o identificativo dell'autore nelle richieste. Ogni riga di registro di una richiesta segna la modalità privacy in cui è partita; il pannello /amministrazione/ia/ mostra la modalità in evidenza (con un avviso se è «didattica»). Ogni fornitore nella configurazione dichiara se il suo piano gratuito può addestrare sui dati: in modalità rigida quelli che possono sono esclusi dalla catena. Documenta il limite: la modalità «didattica» va bene finché i contenuti sono dimostrativi; con cittadini veri si torna a «rigida».

Cosa fare:
1. Trasforma il client in un router: una catena di coppie (fornitore, modello) in ordine di preferenza, configurabile separatamente per testo e per visione (le richieste con foto vanno solo a chi ha visione). Passa al successivo solo per errori che non consumano quota (404 privacy, 403, 429 a monte, rete); mantieni le regole attuali per 429 della nostra quota, risposta non valida, nuovo tentativo su errori 5xx.
2. Un adattatore per fornitore. Parti da Groq e Google AI Studio (API compatibili con OpenAI: cambiano URL, chiave, nome del modello, parametro di privacy). Predisponi Mistral, Cerebras e Cloudflare Workers AI come voci di configurazione da attivare quando l'autore avrà le chiavi. Variabili d'ambiente tipo GROQ_API_KEY, GEMINI_API_KEY ecc., mai nel repository né nei log; aggiorna .env.example e docs/produzione.md.
3. Quota separata per fornitore: ogni fornitore ha limiti e contatore propri (richieste al giorno e al minuto, azzeramento a mezzanotte UTC o altro), letti da configurazione e, dove esiste, dal contatore ufficiale. quota.ammesso() deve dire se almeno un fornitore della catena è disponibile per quel tipo di richiesta. Mostra la quota di ogni fornitore nel pannello /amministrazione/ia/ e nel comando ia_lavora --stato. Il registro (log_attivita, tabella «openrouter») va generalizzato con il nome del fornitore senza rompere i dati esistenti né richiedere modifiche allo schema.
4. Prima di aggiungere un fornitore alla catena controlla sul suo sito limiti attuali e trattamento dei dati nel piano gratuito, e registra in configurazione se può addestrare sui dati (per esempio il piano gratuito di Google): in modalità rigida è escluso, in didattica è ammesso. Non fidarti della memoria: leggi la documentazione.
5. Adatta tools/ia/sonda_modelli.py (prova rapida di un modello con poche richieste) e tools/ia/valuta.py (valutazione sulle 159 etichette di tools/ia/dataset/) per scegliere fornitore e modello da riga di comando e confrontare i fornitori sugli stessi contenuti, con un tetto di richieste per fornitore. Una chiave mancante significa «fornitore non configurato», non un errore.
6. Prove automatiche senza rete (finto server locale, come smoke/ia_openrouter.py): catena che passa al successivo, quota per fornitore, visione solo ai fornitori con visione, chiave mancante, tutti i fornitori falliti → dubbio. Aggiorna smoke/ia_openrouter.py, ia_coda.py e ia_pannello.py; tutte devono restare verdi.
7. Aggiorna docs/piano_ia_openrouter.md (sezione sul multi-fornitore), docs/architettura_ia.md, docs/informativa_ia_bozza.md (elenco dei fornitori che ricevono testi e foto e, se IA_PRIVACY=didattica, la dichiarazione che i contenuti possono essere usati dal fornitore per l'addestramento; la frase «chiediamo di non usarli» va tenuta solo in modalità rigida) e CLAUDE.md. Prove senza rete anche per IA_PRIVACY: la catena in modalità rigida salta i fornitori che possono addestrare e non omette mai data_collection=deny dove supportato; in modalità didattica li usa.

Prima di cominciare: controlla git status. Nell'ultima parte del lavoro precedente c'erano modifiche non committate (prefiltro, prompt, lavoratore con token crescenti sui nuovi tentativi, IA_COMMENTI_BLOCCO=20, valuta.py con rilettura dei commenti puliti) e una valutazione sui 159 contenuti ancora da concludere: verifica che i test ia_*.py passino, poi committa quel lavoro separatamente prima di iniziare il multi-fornitore. Non consumare quota di OpenRouter senza necessità (oggi ne restano poche richieste).

Quando hai finito, dimmi quali chiavi mi servono, dove metterle e come provare ogni fornitore.
```
