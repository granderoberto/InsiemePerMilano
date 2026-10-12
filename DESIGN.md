---
name: La Nostra Città, Il Nostro Futuro
description: Piattaforma civica «Insieme per Milano» in forma di segnaletica milanese, con le linee M1-M5 come codice e il percorso della segnalazione come linea della metropolitana.
colors:
  carta: "#ffffff"
  fondo: "#f2f2f0"
  inchiostro: "#101010"
  attenuato: "#4b4b4b"
  filetto-chiaro: "#cbcbc8"
  m1-rosso: "#e30613"
  m2-verde: "#009a44"
  m3-giallo: "#ffc400"
  m4-blu: "#0a5eb0"
  m5-viola: "#8e4ea0"
  azione-hover: "#c50010"
  fuoco: "#0a5eb0"
  ok: "#0a6b32"
  attenzione: "#7a4f00"
  errore: "#b00020"
  carta-scuro: "#151515"
  fondo-scuro: "#0b0b0b"
  inchiostro-scuro: "#f4f4f1"
typography:
  display:
    fontFamily: "Archivo, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"
    fontSize: "clamp(2rem, 5.4vw, 3.6rem)"
    fontWeight: 800
    lineHeight: 1.04
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 118"
  headline:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 800
    lineHeight: 1.04
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 108"
  title:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 700
    lineHeight: 1.15
    fontVariation: "'wdth' 104"
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.92rem"
    fontWeight: 700
    lineHeight: 1.15
  figure:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "3.6rem"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "-0.03em"
    fontVariation: "'wdth' 125"
rounded:
  none: "0"
  fermata: "50%"
spacing:
  xs: "6px"
  sm: "10px"
  md: "18px"
  lg: "28px"
  xl: "72px"
components:
  button-primary:
    backgroundColor: "{colors.inchiostro}"
    textColor: "{colors.carta}"
    rounded: "{rounded.none}"
    padding: "10px 18px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.azione-hover}"
    textColor: "#ffffff"
  button-lieve:
    backgroundColor: "transparent"
    textColor: "{colors.inchiostro}"
    rounded: "{rounded.none}"
    padding: "10px 18px"
    height: "44px"
  button-pericolo:
    backgroundColor: "transparent"
    textColor: "{colors.errore}"
    rounded: "{rounded.none}"
    padding: "10px 18px"
  input-campo:
    backgroundColor: "{colors.carta}"
    textColor: "{colors.inchiostro}"
    rounded: "{rounded.none}"
    padding: "10px 12px"
    height: "46px"
  riquadro:
    backgroundColor: "{colors.carta}"
    textColor: "{colors.inchiostro}"
    rounded: "{rounded.none}"
    padding: "22px 24px"
  scheda:
    backgroundColor: "{colors.carta}"
    textColor: "{colors.inchiostro}"
    rounded: "{rounded.none}"
    padding: "16px 18px 18px"
  tappa-attuale:
    backgroundColor: "{colors.m1-rosso}"
    rounded: "{rounded.fermata}"
    size: "20px"
---

# Design System: La Nostra Città, Il Nostro Futuro

## Overview

**Creative North Star: "La Linea"**

La piattaforma è una linea della metropolitana: fermate leggibili, colori come codice, nessuna decorazione. Il cittadino vede la mappa del suo quartiere, segnala, e segue la segnalazione di fermata in fermata fino ai candidati Sindaco. La forma è la segnaletica milanese: bianco carta e nero inchiostro, filetti da 2px, angoli vivi, un solo carattere (Archivo variabile, largo per i titoli). Il rosso della M1 è il colore dell'azione e del punto in cui ci si trova; gli altri quattro colori di linea compaiono solo come codice di categoria o di stato.

La densità è alta ma ordinata: griglie a celle separate da filetti, non carte fluttuanti. Tutto è piatto: la profondità è data dai filetti e dall'inversione (campo nero con testo carta), mai da ombre o sfumature. La leggibilità precede lo stile: contrasti WCAG AA, bersagli da 44px, focus blu sempre visibile, tema scuro automatico.

**Key Characteristics:**
- Carta e inchiostro con filetti da 2px; filetti da 1px chiari solo per separare righe interne.
- Angoli vivi ovunque; il cerchio esiste solo come fermata.
- Cinque colori di linea come codice, mai come riempimento decorativo.
- Un solo carattere variabile: la larghezza (`wdth`) distingue i titoli, il peso la gerarchia.
- Marchio a cinque fermate e «Percorso» come elementi firma.

## Colors

Strategia a codice: neutri quasi acromatici più cinque colori di linea saturi, con ruoli fissi. Il tema scuro inverte carta e inchiostro e schiarisce le linee (valori in `colors.*-scuro`; le linee scure sono `#ff4d57 #2ec26a #ffd23d #4a9be8 #c28bd6`).

### Primary
- **Rosso M1** (`colors.m1-rosso`): azione e posizione. Bordo superiore della testata e del piè di pagina, sottolineatura dei link, voce di navigazione corrente, fermata attuale del Percorso, pallino delle notifiche, categoria «Mobilità urbana», tipo «Problema». Hover dei pulsanti: Rosso M1 scurito (`colors.azione-hover`).

### Secondary
- **Verde M2** (`colors.m2-verde`): categoria «Ambiente»; stato «Approvata».
- **Giallo M3** (`colors.m3-giallo`): categoria «Decoro urbano»; stati 1-2 (in lavorazione); evidenziazione della selezione e avviso di simulazione.
- **Blu M4** (`colors.m4-blu`): categoria «Sicurezza del territorio»; tipo «Proposta». Lo stesso blu, schiarito nel tema scuro, è il colore del focus.
- **Viola M5** (`colors.m5-viola`): categoria «Politiche giovanili».

### Neutral
- **Carta** (`colors.carta`): superfici (testata, schede, riquadri, campi).
- **Fondo** (`colors.fondo`): sfondo pagina e hover delle schede.
- **Inchiostro** (`colors.inchiostro`): testo, filetti da 2px, pulsante primario, stato «Rifiutata».
- **Attenuato** (`colors.attenuato`): testo secondario e metadati.
- **Filetto chiaro** (`colors.filetto-chiaro`): separatori interni da 1px, riempimento dei segnaposto.
- **Semantici** (`colors.ok`, `colors.attenzione`, `colors.errore`): solo testo e bordi di avvisi, esiti dei controlli e azioni distruttive; sempre accompagnati da una parola («Fatto.», «Attenzione.», «Errore.»).

### Named Rules
**The Codice Rule.** Un colore di linea significa sempre la stessa cosa (categoria o stato) e compare accanto a un'etichetta di testo. Mai colore come unica informazione, mai colore come decorazione.

**The Un Rosso Rule.** Il rosso M1 segna l'azione o il punto in cui ci si trova. Non si usa per riempire sezioni.

## Typography

**Display Font:** Archivo variabile (self-hosted, `wght` 100-900, `wdth` 62-125%), con stack di sistema come ripiego.
**Body Font:** la stessa famiglia.
**Label/Mono Font:** nessuna; le cifre sono sempre tabulari (`font-variant-numeric: tabular-nums`).

**Character:** un carattere unico da cartello. I titoli sono larghi (`wdth` 104-125), pesanti e stretti di interlinea; il testo corrente è normale e arioso. La gerarchia si costruisce con larghezza e peso, non con famiglie diverse.

### Hierarchy
- **Display** (800, `clamp(2rem, 5.4vw, 3.6rem)`, 1.04, `wdth` 118): h1 di pagina; nella fascia della home `clamp(2rem, 4.8vw, 3.3rem)`.
- **Headline** (800, 1.35rem, 1.04, `wdth` 108): h2 di sezione.
- **Title** (700-800, 1.08-1.2rem, 1.15, `wdth` 104): h3 e titoli delle schede.
- **Body** (400, 1rem, 1.55): testo corrente; descrizioni lunghe entro 66ch.
- **Label** (700, 0.88-0.95rem): etichette dei campi, pulsanti, voci di navigazione, badge (800, 0.85rem).
- **Figure** (800, 2-3.6rem, `wdth` 125): numeri grandi (sostegni, contatori delle code).

### Named Rules
**The Larghezza Rule.** La larghezza variabile è il segnale dei titoli e dei numeri: più grande l'elemento, più largo il carattere. Il corpo del testo resta a larghezza normale.

**The Maiuscole Misurate Rule.** Il maiuscolo con spaziatura non è un tratto del sistema; le etichette si scrivono in minuscolo con peso 700-800.

## Layout

Contenitore centrato fino a 1200px con 20px di margine laterale (16px sotto 640px), mobile-first. La struttura è a celle: griglie di schede (`minmax(310px, 1fr)`), code della moderazione e riepiloghi sono tabelle di celle unite da filetti da 2px condivisi (bordo superiore e sinistro sul contenitore, destro e inferiore su ogni cella). La home apre con una fascia a due colonne (testo 5fr, mappa 7fr) che sotto 900px diventa colonna con la mappa subito dopo i pulsanti. Il dettaglio è 2fr + 1fr con colonna laterale sticky da 900px.

Ritmo: spazi da 6, 10, 18, 28px; sezioni a 36px sopra e 72px sotto il contenuto principale. Bersagli minimi 44px (40px per i pulsanti piccoli). Il menu di navigazione scorre in orizzontale su mobile; il pulsante di invio del modulo di segnalazione resta fisso in basso sotto 640px.

### Named Rules
**The Filetto Condiviso Rule.** Le celle adiacenti condividono un solo filetto da 2px; non si raddoppiano i bordi e non si lasciano interstizi tra celle.

## Elevation & Depth

Nessuna ombra, nessuna sfumatura, nessun effetto di vetro: il sistema è piatto. La gerarchia è data da filetti (2px per i contenitori, 1px chiaro per le righe interne), dal passaggio carta su fondo e dall'inversione di stato (hover e selezione diventano campo inchiostro con testo carta). La testata è sticky con filetto inferiore da 2px; i pannelli (menu account, popup della mappa) sono carta con filetto da 2px. I controlli di Leaflet sono ridisegnati senza ombra e senza raggio.

### Named Rules
**The Piatto Rule.** Niente `box-shadow` né gradienti. Per separare si usa un filetto, per enfatizzare si inverte.

## Shapes

Angoli vivi (raggio 0) su pulsanti, campi, schede, riquadri, badge, menu e popup. Le uniche forme tonde sono le fermate: i punti di categoria, i pin della mappa, le tappe del Percorso e le fermate del marchio. Il bordo è il linguaggio: 2px pieno in inchiostro per i contenitori; i selettori di stato sono quadratini con bordo da 2px (badge) e cerchi (categoria). Le immagini hanno sotto una barra da 5px nel colore della categoria.

### Named Rules
**The Fermata Rule.** Il cerchio significa «fermata»: luogo, categoria o tappa del percorso. Qualsiasi altro elemento è rettangolare.

## Components

### Buttons
- **Shape:** rettangolo vivo (0), bordo 2px, altezza minima 44px, `padding` 10px 18px, peso 700.
- **Primary:** campo inchiostro con testo carta (in tema scuro è l'inverso). Hover: campo e bordo Rosso M1 scurito, testo bianco. Active: sposta di 1px in basso.
- **Lieve:** trasparente con bordo inchiostro; hover inverte in campo inchiostro.
- **Pericolo:** trasparente con testo e bordo `errore`; hover riempie di `errore`.
- **Taglie:** piccolo (40px), grande (54px, 1.05rem). Il pulsante di invio dei moduli è a larghezza piena.

### Navigation
Testata sticky su carta con bordo superiore Rosso M1 da 6px e inferiore inchiostro da 2px. Voci da 44px con sottolineatura spessa da 4px: trasparente a riposo, grigia in hover, Rosso M1 per la pagina corrente (peso 800). Il marchio è il nome in `wdth` 118 sopra una linea a cinque fermate nei colori M1-M5. Il menu account è un `details` con pannello carta e voci a tutta larghezza che si invertono in hover.

### Cards / Containers
- **Scheda segnalazione:** cella carta nella griglia a filetti; immagine 16:10 con barra da 5px del colore della categoria, targhetta del luogo ancorata in basso a sinistra, tipo e stato come badge in alto a sinistra su carta; titolo in `wdth` 104 (intero blocco cliccabile); piede con sostegni e commenti separato da filetto chiaro. Hover: sfondo `fondo`.
- **Riquadro:** carta, filetto 2px, `padding` 22px 24px; il titolo h2 ha filetto inferiore da 2px.
- **Voce di coda:** `fondo` con filetto 1px, per le code di moderazione.

### Inputs / Fields
- **Style:** carta, bordo 2px inchiostro, raggio 0, altezza 46px, `padding` 10px 12px. Etichetta sopra, peso 700.
- **Focus:** contorno blu `fuoco` da 3px; vale per ogni elemento (`:focus-visible`).
- **Error:** bordo `errore` e messaggio in grassetto sotto il campo; l'errore non si affida al solo colore.
- **Selettori a pulsante** (tipo e categorie nel modulo): riquadri con bordo 2px che si invertono quando scelti.
- **Spunte:** quadrati nativi da 20px con `accent-color` inchiostro.

### Badge e categorie
Il badge è un quadratino da 10px con bordo inchiostro nel colore di stato o tipo, seguito dal nome in peso 800. La categoria è un cerchio da 14px (`.punto`) nel colore di linea, seguito dal nome. Il colore non è mai l'unico veicolo: il testo c'è sempre.

### Percorso (elemento firma)
La segnalazione è una linea della metropolitana: elenco verticale di tappe unite da un tratto inchiostro da 4px. Ogni tappa è un cerchio da 20px con bordo da 4px: piena in inchiostro se già superata, Rosso M1 con anello esterno da 3px se è la tappa attuale (con `aria-current="step"` e testo più grande), carta vuota con testo attenuato se futura. Nei contesti orizzontali (`.percorso` in home) lo stesso schema corre in riga: cerchi collegati da tratti da 3px, ultima fermata in rosso. Il Percorso descrive solo lo stato e non ha altra decorazione.

### Marchio a cinque fermate
Linea inchiostro da 3px con cinque cerchi da bordo 2.5px, riempiti in sequenza con M1-M5, larga 118px sotto il nome. Si usa solo come marchio, non come divisore.

### Mappa
Pin circolare da 22px con bordo bianco e contorno inchiostro: rosso per «problema», blu per «proposta». Il gruppo di pin è un quadrato nero da 36px con numero bianco. Legenda e popup su carta con filetto da 2px, senza ombra. Nel tema scuro i riquadri della mappa sono invertiti con filtro.

### Tabelle e barre
Tabella con filetto esterno da 2px, righe separate da 1px chiaro, intestazione con filetto da 2px; hover di riga su `fondo`. Barre di statistica: pista `filetto-chiaro` e riempimento inchiostro, alte 14px, con il valore numerico accanto.

## Do's and Don'ts

### Do:
- **Do** usare solo carta, fondo e inchiostro come base e i cinque colori di linea come codice di categoria o stato, sempre con etichetta di testo.
- **Do** costruire contenitori con filetti da 2px e angoli vivi; separare le righe interne con filetti da 1px chiari.
- **Do** riservare il Rosso M1 all'azione e alla posizione corrente.
- **Do** usare Archivo con `wdth` crescente per titoli e numeri grandi, e il peso 700-800 per le etichette.
- **Do** usare l'inversione carta/inchiostro per hover e selezione; bersagli minimi 44px; focus blu da 3px.
- **Do** disegnare ogni nuovo stato o avanzamento come fermate di una linea.

### Don't:
- **Don't** usare ombre, sfumature, trasparenze a vetro o raggi di curvatura sui contenitori.
- **Don't** introdurre un secondo carattere né un carattere di sistema per i titoli.
- **Don't** usare un colore di linea come riempimento decorativo o come unico segnale di significato.
- **Don't** rendere circolare qualcosa che non sia una fermata.
- **Don't** scrivere nuovo codice con etichette maiuscole spaziate né stili in linea nei template: i valori vivono nel foglio di stile e nelle variabili `:root`.

## Note di fedeltà

Il sistema registra ciò che il CSS fa oggi; non tutto è stato canonizzato (vedi l'ultima riga del rapporto di consegna). Il tema scuro è automatico (`prefers-color-scheme`), senza selettore manuale.
