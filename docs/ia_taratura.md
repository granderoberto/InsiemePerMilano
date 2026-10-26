# Taratura dei controlli IA (2026-10-26)

Eseguita con `tools/ia/valuta.py` su `tools/ia/dataset/bozza_contenuti.csv` e `bozza_contenuti_2.csv` (159 contenuti). **Le etichette le ho riviste e ampliate io** (l'autore ha delegato): regole in `tools/ia/dataset/LEGGIMI.md`. Modello: `recursive/flint-v1.0:free`. Richieste usate in tutto oggi: 44 su 50.

**Il rapporto è incompleto**: 18 commenti non hanno ancora la risposta del modello perché la quota giornaliera dei commenti (8 richieste) è finita. Sono contati come `dubbio` e gonfiano i «contenuti buoni segnalati»: 11 dei 13 sono solo mancanza di risposta. Per completarlo dopo mezzanotte UTC: `apps/web/.venv/bin/python tools/ia/valuta.py --esegui --max 2 --rapporto docs/ia_taratura.md` (2 richieste; le altre risposte sono in memoria).

## Che cosa si può già dire

- **Minacce: 18 bloccate su 18** dal controllo locale (dopo aver aggiunto «guardarvi le spalle», «ti aspetto sotto casa», auguri di morte). È ottimistico: i modelli di frasi li ho visti prima di scriverli.
- **Il modello, dove ha risposto, sbaglia poco**: 55 giusti su 57. Errori: «ok ok ok…» approvato (etichetta discutibile) e la segnalazione sul vicino con nome e cognome approvata. Per quest'ultima ho precisato il prompt (nome e cognome associati a insulti o accuse), da riprovare.
- **La rilettura dei commenti «puliti» serve**: 31 riletti tutti confermati; 2 su 13 con risposta bocciati a torto («numero di telefono» di un ente pubblico, ora ammesso dal prompt; «gente maleducata», discutibile). Il resto dei commenti che il controllo locale lascia passare e sono dubbi (sarcasmo, persona nominata, accusa senza parole in elenco, ricatto, intimidazione) **resta da vedere** perché non hanno ancora la risposta del modello.
- **Senza rilettura** il controllo locale lascerebbe passare tutti questi: per questo `IA_RILEGGI_PULITI` è attivo di default.

## Problema trovato: blocchi di commenti con risposta vuota

Il modello «ragiona» prima di rispondere e talvolta finisce i token senza dare il JSON: su 8 richieste a blocchi, 3 sono tornate vuote (e consumano quota). Mitigazioni fatte: blocchi da 20 commenti, 2000 + 150 token per commento, metà in più a ogni nuovo tentativo, `finish_reason` nel messaggio d'errore. Se continua, ridurre `IA_COMMENTI_BLOCCO` a 10 (più richieste, meno sprechi).

Contenuti: 159 da `bozza_contenuti.csv, bozza_contenuti_2.csv` · richieste al modello in questa esecuzione: 0 · risposte del modello in memoria: 103

> **Attenzione**: 18 contenuti non hanno la risposta del modello e sono contati come `dubbio`: il risultato non è completo.

## Esito finale rispetto alle tue etichette

| etichetta \ esito | ok | dubbio | bloccato | totale |
|---|---|---|---|---|
| **ok** | 69 | 13 | 0 | 82 |
| **dubbio** | 7 | 52 | 0 | 59 |
| **bloccato** | 0 | 0 | 18 | 18 |

Corretti: **139 su 159** (87%).

- **Contenuti buoni segnalati** (ok → dubbio/bloccato, fastidio per gli utenti e lavoro per il moderatore): **13** su 82
- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **7** su 77
- **Minacce non bloccate** (bloccato → ok/dubbio): **0** su 18

## Chi ha deciso

| fonte | contenuti | corretti |
|---|---|---|
| prefiltro (riletto) | 31 | 31 |
| prefiltro | 40 | 35 |
| senza risposta del modello | 18 | 7 |
| modello | 57 | 55 |
| rilettura del modello | 13 | 11 |

## Errori (20)

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
| 149 | commento | ok | dubbio | rilettura del modello | numero di telefono presente · numero di telefono presente | La polizia locale risponde al 02 0202 per i rumori notturni, io l'ho provato e funziona. |
| 150 | commento | ok | dubbio | rilettura del modello | insulto verso altri · insulto verso altri | Il cassonetto è pieno di roba di gente maleducata che non fa la differenziata: serve più c |
