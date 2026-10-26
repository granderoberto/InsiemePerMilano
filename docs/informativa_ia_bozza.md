# Bozza: informativa sull'uso dell'intelligenza artificiale

**Da rivedere dal comitato prima della pubblicazione.** È un testo di lavoro, non un parere legale. Pubblicarlo come nuova versione del documento «intelligenza artificiale» obbliga tutti gli utenti ad accettarlo di nuovo (le normative sono versionate): per questo non è stato inserito nel database.

## Che cosa fa l'intelligenza artificiale sul sito

Per aiutare i moderatori il sito controlla automaticamente le segnalazioni e i commenti:
- cerca insulti, minacce, odio, spam e dati personali di altre persone (numeri di telefono, email, targhe, indirizzi di casa);
- controlla che le foto non mostrino contenuti sessuali o violenti e che siano pertinenti alla descrizione;
- legge il testo scritto nelle foto.

**L'intelligenza artificiale non decide da sola.** Può solo segnalare un contenuto al moderatore. Un contenuto con una minaccia esplicita non viene pubblicato; in tutti gli altri casi la decisione finale spetta a una persona. Se un controllo non riesce, il contenuto passa a un moderatore.

## Quali dati escono dal sito

Per i controlli sono inviati a fornitori esterni di modelli di linguaggio, in questo ordine di preferenza e solo se il precedente non è disponibile: **OpenRouter** (che inoltra la richiesta a un modello che non addestra sui dati), **Groq** (Stati Uniti; il contratto vieta di usare i contenuti per addestrare e prevede log di sicurezza fino a 30 giorni). Altri fornitori (Cloudflare, Cerebras, Mistral) sono predisposti ma spenti: se verranno attivati l'elenco in questa pagina va aggiornato. Google non è usato. I contenuti sono:
- il titolo e la descrizione di una segnalazione, o il testo di un commento;
- le foto della segnalazione (per i video, due fotogrammi), **senza metadati** (posizione, dispositivo, data) e **con i volti sfocati**.

Non sono inviati: il tuo nome, la tua email, il tuo profilo, la tua posizione esatta, il documento e il selfie della verifica d'identità. Il documento e il selfie sono letti solo dal nostro sito e cancellati a verifica conclusa.

Chiediamo ai fornitori di non usare i contenuti per addestrare i modelli. I modelli usati sono gratuiti e i fornitori possono cambiare: l'elenco aggiornato è nel pannello dell'amministratore.

## I tuoi diritti

- Puoi chiedere la **revisione di una persona** su qualunque decisione presa o suggerita dai controlli automatici, dalla pagina della segnalazione o del commento (art. 22 GDPR).
- Puoi chiedere l'accesso, la correzione e la cancellazione dei tuoi dati con le modalità dell'informativa sulla privacy.
- Le decisioni automatiche e il motivo (poche parole) sono registrate e visibili ai moderatori.

## Cose da decidere prima di pubblicare (comitato)

1. Il nome e l'indirizzo del titolare del trattamento e come contattarlo.
2. Se il trasferimento dei dati fuori dall'Unione Europea (Groq e molti modelli di OpenRouter hanno sede o server negli Stati Uniti) è accettabile con fornitori gratuiti, o se serve un fornitore con sede e dati in UE e un accordo di trattamento (DPA).
3. Una valutazione d'impatto (DPIA) se si passa a un uso su larga scala.
4. Per quanto tempo si conservano gli esiti e le motivazioni.
