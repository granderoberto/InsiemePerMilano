# Confronto dei fornitori sugli stessi 159 contenuti (2026-10-26)

`tools/ia/valuta.py --confronta openrouter,groq,cloudflare`: stesse etichette (`bozza_contenuti.csv` e `bozza_contenuti_2.csv`), stesso prefiltro locale, stessi prompt, solo il modello cambia. Le etichette sono le mie (l'autore ha delegato); il controllo locale è stato rifinito su questi stessi contenuti, quindi i numeri sono ottimistici in assoluto ma **confrontabili tra fornitori**.

## Lettura

- **I tre fornitori si equivalgono**: Cloudflare 148/159, Groq 146/159, OpenRouter 139/159 (ma 18 contenuti di OpenRouter sono senza risposta, quindi il suo valore è più basso del reale). **Nessuna minaccia mancata** in nessuno (la bloccano il controllo locale).
- **Contenuti buoni segnalati per errore**: Cloudflare 1 su 82, Groq 2, OpenRouter 13 (11 sono solo mancanza di risposta).
- **Dubbi lasciati passare**: 10-11 su 77 per Cloudflare e Groq, 7 per OpenRouter (dove ha risposto). Sono quasi sempre gli stessi: sarcasmo ostile, accuse a persone, testo ripetitivo («ok ok ok…»). Un controllo di questo tipo non li prende tutti: restano al moderatore.
- **Velocità**: Groq 1-3 s a richiesta; Cloudflare 5-13 s a blocco di commenti e circa 1 s per segnalazione; OpenRouter 10-40 s (modelli «ragionanti» gratuiti).
- **Limiti incontrati**: Groq ha un limite di token al minuto che i blocchi da 20 commenti superano ogni tanto (si aspetta il «riprova tra X s» indicato nella risposta); Cloudflare nessun limite sulle 36 richieste di prova; OpenRouter ha la quota quasi finita (50 al giorno).
- **Ordine consigliato della catena** (`IA_FORNITORI=groq,cloudflare,openrouter`): Groq per primo perché è il più veloce, Cloudflare come riserva precisa e senza limiti al minuto, OpenRouter per ultimo perché lento e con soli 50 richieste al giorno.
- Foto: non confrontate su immagini vere (i dati demo sono disegni): la qualità sulle foto resta da verificare in uso.

Contenuti: 159 da `bozza_contenuti.csv, bozza_contenuti_2.csv`. Risposte in memoria: 385.

## Confronto

| fornitore | corretti | buoni segnalati | dubbi passati | minacce mancate | senza risposta |
|---|---|---|---|---|---|
| openrouter | 139/159 | 13/82 | 7/77 | 0/18 | 18 |
| groq | 146/159 | 2/82 | 11/77 | 0/18 | 0 |
| cloudflare | 148/159 | 1/82 | 10/77 | 0/18 | 0 |

## openrouter

Richieste in questa esecuzione: 0

> **Attenzione**: 18 contenuti non hanno la risposta del modello e sono contati come `dubbio`: il risultato non è completo.

| etichetta \ esito | ok | dubbio | bloccato | totale |
|---|---|---|---|---|
| **ok** | 69 | 13 | 0 | 82 |
| **dubbio** | 7 | 52 | 0 | 59 |
| **bloccato** | 0 | 0 | 18 | 18 |

Corretti: **139 su 159** (87%).

- **Contenuti buoni segnalati** (ok → dubbio/bloccato): **13** su 82
- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **7** su 77
- **Minacce non bloccate**: **0** su 18

| deciso da | contenuti | corretti |
|---|---|---|
| prefiltro (riletto) | 31 | 31 |
| prefiltro | 40 | 35 |
| senza risposta del modello | 18 | 7 |
| modello | 57 | 55 |
| rilettura del modello | 13 | 11 |

**Errori (20)**

| id | tipo | atteso | esito | deciso da | segnali o motivo | testo |
|---|---|---|---|---|---|---|
| 26 | commento | ok | dubbio | senza risposta del modello | ostilita | Questa segnalazione è inutile e mal scritta, secondo me. |
| 50 | commento | dubbio | ok | modello | ripetizione | ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok |
| 101 | commento | ok | dubbio | senza risposta del modello | spam | Per segnalare i rifiuti abbandonati potete chiamare il numero verde del Comune, lo trovate |
| 103 | commento | ok | dubbio | senza risposta del modello | punteggiatura | ATTENZIONE: la buca in via Padova è profonda, fate attenzione se passate in bici!!!! |
| 105 | commento | ok | dubbio | senza risposta del modello | accusa | Attenti alla truffa del finto tecnico del gas, è successo a una signora del mio palazzo. |
| 106 | commento | ok | dubbio | senza risposta del modello | accusa | I ladri sono entrati in due negozi di via Settala la settimana scorsa: serve un presidio. |
| 107 | commento | ok | dubbio | senza risposta del modello | insulto | Nel parco ci sono parassiti sugli olmi: vanno fatti trattamenti, altrimenti gli alberi muo |
| 108 | commento | ok | dubbio | senza risposta del modello | insulto | Sul marciapiede c'è tanta merda di cani e nessuno pulisce, servono più sacchetti. |
| 109 | commento | ok | dubbio | senza risposta del modello | insulto | Il cartello all'ingresso dice «vietato ai cretini», forse è uno scherzo ma non è bello per |
| 110 | commento | ok | dubbio | senza risposta del modello | insulto | Non è giusto dare dell'idiota a chi ha fatto la segnalazione, ognuno può dire la sua con r |
| 115 | commento | ok | dubbio | senza risposta del modello | insulto | Bastardo di un tombino, mi ha rotto la ruota della bici! |
| 116 | commento | ok | dubbio | senza risposta del modello | accusa | Questo quartiere è un disastro, sono tutti criminali quelli che non rispettano le regole d |
| 120 | commento | dubbio | ok | prefiltro |  | Complimenti genio, ennesima idea geniale da chi non esce mai di casa. |
| 122 | commento | dubbio | ok | prefiltro |  | Il solito Rossi del civico 5 che lascia l'auto dove vuole, lo conoscono tutti. |
| 123 | commento | dubbio | ok | prefiltro |  | Quello della panetteria ha intascato i soldi del comitato, ne sono sicura. |
| 127 | commento | dubbio | ok | prefiltro |  | Pagatemi e vi dico io chi ha fatto la segnalazione, scrivetemi in privato. |
| 128 | commento | dubbio | ok | prefiltro |  | Sappiamo tutti dove lavora la signora che ha scritto, andiamo a chiederle spiegazioni. |
| 131 | segnalazione | dubbio | ok | modello | foto | Vicino che fa rumore / Il mio vicino del terzo piano, il signor Mario Bianchi, fa musica f |
| 149 | commento | ok | dubbio | rilettura del modello | numero di telefono presente | La polizia locale risponde al 02 0202 per i rumori notturni, io l'ho provato e funziona. |
| 150 | commento | ok | dubbio | rilettura del modello | insulto verso altri | Il cassonetto è pieno di roba di gente maleducata che non fa la differenziata: serve più c |

## groq

Richieste in questa esecuzione: 0

| etichetta \ esito | ok | dubbio | bloccato | totale |
|---|---|---|---|---|
| **ok** | 80 | 2 | 0 | 82 |
| **dubbio** | 11 | 48 | 0 | 59 |
| **bloccato** | 0 | 0 | 18 | 18 |

Corretti: **146 su 159** (92%).

- **Contenuti buoni segnalati** (ok → dubbio/bloccato): **2** su 82
- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **11** su 77
- **Minacce non bloccate**: **0** su 18

| deciso da | contenuti | corretti |
|---|---|---|
| prefiltro (riletto) | 52 | 50 |
| modello | 75 | 64 |
| prefiltro | 18 | 18 |
| rilettura del modello | 14 | 14 |

**Errori (13)**

| id | tipo | atteso | esito | deciso da | segnali o motivo | testo |
|---|---|---|---|---|---|---|
| 41 | commento | dubbio | ok | modello | accusa | Vota per il candidato X, è l'unico serio, tutti gli altri sono ladri e delinquenti. |
| 42 | commento | dubbio | ok | modello | accusa | Quel consigliere è un ladro, lo so per certo, ha preso soldi dal costruttore. |
| 50 | commento | dubbio | ok | modello | ripetizione | ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok |
| 75 | segnalazione | dubbio | ok | modello | telefono | Cantiere rumoroso / Il cantiere della ditta Bianchi Srl lavora di notte, chiamate il titol |
| 109 | commento | ok | dubbio | modello | insulto · insulto a gruppo | Il cartello all'ingresso dice «vietato ai cretini», forse è uno scherzo ma non è bello per |
| 116 | commento | ok | dubbio | modello | accusa · insulto a gruppo | Questo quartiere è un disastro, sono tutti criminali quelli che non rispettano le regole d |
| 117 | commento | dubbio | ok | modello | telefono | Se serve una mano per la raccolta firme, il mio numero è 02 55501234, ci sono volentieri. |
| 120 | commento | dubbio | ok | prefiltro (riletto) |  | Complimenti genio, ennesima idea geniale da chi non esce mai di casa. |
| 121 | commento | dubbio | ok | modello | ostilita | Gentaglia, ecco cosa c'è in questo quartiere. |
| 132 | segnalazione | dubbio | ok | modello | accusa | Parcheggi abusivi / Ogni sera ci sono auto in doppia fila davanti al bar, i proprietari so |
| 164 | commento | dubbio | ok | prefiltro (riletto) |  | Tutti i politici sono uguali, mangiano alle spalle dei cittadini. |
| 177 | segnalazione | dubbio | ok | modello | foto | Rumore notturno dal locale / Il locale all'angolo fa musica ad alto volume fino alle 3 di  |
| 179 | segnalazione | dubbio | ok | modello | foto | Spaccio e degrado / La piazza è piena di spacciatori e drogati, gente così va sbattuta fuo |

## cloudflare

Richieste in questa esecuzione: 0

| etichetta \ esito | ok | dubbio | bloccato | totale |
|---|---|---|---|---|
| **ok** | 81 | 1 | 0 | 82 |
| **dubbio** | 10 | 49 | 0 | 59 |
| **bloccato** | 0 | 0 | 18 | 18 |

Corretti: **148 su 159** (93%).

- **Contenuti buoni segnalati** (ok → dubbio/bloccato): **1** su 82
- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **10** su 77
- **Minacce non bloccate**: **0** su 18

| deciso da | contenuti | corretti |
|---|---|---|
| prefiltro (riletto) | 54 | 50 |
| modello | 75 | 68 |
| prefiltro | 18 | 18 |
| rilettura del modello | 12 | 12 |

**Errori (11)**

| id | tipo | atteso | esito | deciso da | segnali o motivo | testo |
|---|---|---|---|---|---|---|
| 43 | commento | dubbio | ok | modello | insulto | Sono tutti dei parassiti, i politici di questa città. |
| 45 | commento | dubbio | ok | modello | insulto | Fate schifo, voi del comitato, siete dei buffoni. |
| 46 | commento | dubbio | ok | modello | insulto | Cretino chi ha messo questo semaforo. |
| 50 | commento | dubbio | ok | modello | ripetizione | ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok |
| 111 | commento | dubbio | ok | modello | indirizzo | Abito in via Padova 12 e confermo che di sera quel tratto è completamente al buio. |
| 116 | commento | ok | dubbio | modello | accusa · odio verso gruppo | Questo quartiere è un disastro, sono tutti criminali quelli che non rispettano le regole d |
| 126 | commento | dubbio | ok | modello | ostilita | Zero cervello, complimenti a chi ha deciso di mettere la fermata qui. |
| 151 | commento | dubbio | ok | prefiltro (riletto) |  | Chi ha lasciato le sedie rotte nel cortile è uno sporcaccione, ma pulire spetta al condomi |
| 159 | commento | dubbio | ok | prefiltro (riletto) |  | Complimenti, il solito commento da persona che non ha mai lavorato un giorno in vita sua. |
| 160 | commento | dubbio | ok | prefiltro (riletto) |  | Che pena, davvero. Non c'è altro da dire su di te. |
| 164 | commento | dubbio | ok | prefiltro (riletto) |  | Tutti i politici sono uguali, mangiano alle spalle dei cittadini. |

