# Taratura dei controlli IA: primo rapporto (2026-10-26)

Eseguito con `tools/ia/valuta.py --esegui` su `tools/ia/dataset/bozza_contenuti.csv` con le **etichette della bozza**: le correzioni dell'autore non erano ancora nel file. Le risposte del modello sono in memoria (`tools/ia/risultati/valuta_modello.json`): quando le etichette saranno corrette basta rilanciare `valuta.py --rapporto docs/ia_taratura.md`, senza altre richieste.

Modello: `recursive/flint-v1.0:free`. Richieste usate: 20 (19 + 1 per un blocco di commenti che con 2000 token di risposta tornava vuoto: ora i token crescono con il numero di commenti).

## Come leggere il risultato

- **Il test è ottimistico**: il prefiltro è stato rifinito guardando questi stessi contenuti (ho aggiunto minacce, accuse e indirizzi dopo aver visto gli errori) e le etichette le ho scritte io. Il numero vero si vedrà con contenuti nuovi.
- **Il modello non è stato messo alla prova sui commenti buoni**: nel set tutti i commenti `ok` sono «puliti» e il prefiltro li fa passare senza modello. Al modello arrivano solo commenti già sospetti (tutti `dubbio` o `bloccato` nelle etichette), quindi qui non si può misurare quanti commenti buoni scambierebbe per dubbi. Servono commenti `ok` che il prefiltro manda comunque al modello (con una email, un numero, un nome...).
- **Segnalazioni**: per sicurezza vanno sempre al modello perché hanno foto, ma qui sono giudicate sul solo testo.

Contenuti: 80 da `bozza_contenuti.csv` · richieste al modello in questa esecuzione: 1 · risposte del modello in memoria: 38

## Esito finale rispetto alle tue etichette

| etichetta \ esito | ok | dubbio | bloccato | totale |
|---|---|---|---|---|
| **ok** | 42 | 0 | 0 | 42 |
| **dubbio** | 2 | 24 | 0 | 26 |
| **bloccato** | 0 | 0 | 12 | 12 |

Corretti: **78 su 80** (98%).

- **Contenuti buoni segnalati** (ok → dubbio/bloccato, fastidio per gli utenti e lavoro per il moderatore): **0** su 42
- **Contenuti da controllare passati** (dubbio/bloccato → ok, il caso più grave): **2** su 38
- **Minacce non bloccate** (bloccato → ok/dubbio): **0** su 12

## Chi ha deciso

| fonte | contenuti | corretti |
|---|---|---|
| prefiltro | 42 | 42 |
| modello | 38 | 36 |

## Errori (2)

| id | tipo | atteso | esito | deciso da | segnali o motivo | testo |
|---|---|---|---|---|---|---|
| 50 | commento | dubbio | ok | modello | ripetizione | ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok ok |
| 78 | segnalazione | dubbio | ok | modello | foto | Un cartello / Ho visto un cartello. Boh. |
