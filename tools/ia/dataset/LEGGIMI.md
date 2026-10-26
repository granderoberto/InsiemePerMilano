# Contenuti etichettati per tarare i controlli IA (bozza)

`bozza_contenuti.csv` è una **bozza da correggere**: contenuti inventati (nessuno è di un utente vero) con l'etichetta che mi aspetto. Le persone, i telefoni, le email, le targhe e i codici sono finti.

Colonne: `id`, `tipo` (`commento` o `segnalazione`; per le segnalazioni il testo è «titolo | descrizione»), `testo`, `etichetta`, `nota` (perché l'ho messa così: serve solo a te per correggere).

## Regole che ho usato per le etichette

| Etichetta | Quando | Cosa succede nel sito |
|---|---|---|
| `ok` | rispettoso e in tema. Anche la critica dura al Comune o ai politici, il dialetto, lo sfogo, le parolacce non rivolte a persone («che schifo di strada»), il disaccordo | pubblicato; nessun avviso al moderatore |
| `dubbio` | insulto a una persona o a un gruppo, dati personali di terzi (telefono, email, targa, codice fiscale, IBAN, indirizzo), spam o pubblicità, accuse gravi a una persona riconoscibile, contenuto fuori tema o senza senso | pubblicato ma in coda al moderatore |
| `bloccato` | minacce o violenza esplicita, auguri di morte | non pubblicato (commento) o bloccato in attesa del moderatore (segnalazione) |

Il modello da solo decide solo tra `ok` e `dubbio`: `bloccato` lo dà il controllo locale sulle minacce.

## Come correggerla

1. Apri il file in un foglio di calcolo (o in un editor) e cambia solo la colonna `etichetta` dove non sei d'accordo. Le righe che ti sembrano sbagliate o strane si possono anche cancellare.
2. Aggiungi righe in fondo con esempi tuoi, soprattutto **casi difficili**: ironia, dialetto milanese, frasi ambigue, insulti scritti male, critiche forti ma legittime.
3. Tieni un numero simile di `ok`, `dubbio` e `bloccato`: la taratura serve a capire gli errori, non a battere un record di `ok`.

La bozza ha 80 righe: 30 commenti `ok`, 20 `dubbio`, 10 `bloccato`; 12 segnalazioni `ok`, 6 `dubbio`, 2 `bloccato`. Le segnalazioni qui sono solo testo: le foto si provano a parte.

## Seconda bozza: `bozza_contenuti_2.csv`

34 contenuti (id da 101) pensati per i punti deboli della prima:
- **18 commenti/segnalazioni `ok` che contengono un segnale** (un numero verde, «ladri» detto in generale, «merda» riferita ai cani, un insulto citato per condannarlo): il controllo locale li manda al modello, e qui si vede quanti buoni il modello scambia per dubbi.
- **10 commenti `dubbio` senza parole d'allarme** (sarcasmo ostile, insulti con parole non in elenco, odio velato, intimidazione): il controllo locale li considera «puliti» e **non li manda al modello**. Misurano quanto costa la scelta di non spendere richieste sui testi puliti.
- 6 segnalazioni, miste.

Alcune etichette sono volutamente discutibili (l'indirizzo o il telefono dell'autore, «tornatevene a casa vostra» che potrebbe essere `bloccato`): correggile con il tuo giudizio. Per valutarla: `apps/web/.venv/bin/python tools/ia/valuta.py --file tools/ia/dataset/bozza_contenuti_2.csv` (aggiungi `--esegui --max 7` per usare il modello).
