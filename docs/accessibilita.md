# Accessibilità (WCAG 2.1 livello AA)

La specifica (cap. 1) richiede il rispetto delle WCAG 2.1 AA: contrasti adeguati, testo ridimensionabile, navigazione completa da tastiera,
descrizioni alternative per immagini e video, compatibilità con gli screen reader.

## Come è costruito il sito

| Requisito | Come |
|---|---|
| Contrasti | colori definiti come variabili in `static/css/site.css`, con tema chiaro e scuro (`prefers-color-scheme`); i testi verificati sono sopra 4,5:1 |
| Testo ridimensionabile | dimensioni in `rem`, nessun testo in immagini; layout fluido |
| Tastiera | ordine naturale del documento, collegamento «Vai al contenuto» come primo elemento, contorno di focus di 3 px sempre visibile, nessuna trappola; pulsanti e collegamenti veri (non `div` cliccabili) |
| Alternative testuali | `alt` su ogni foto di segnalazione, `aria-label` sui video e sulla mappa; il segnaposto delle foto demo ha un'etichetta |
| Screen reader | punti di riferimento (`header`, `nav` con etichetta, `main`, `footer`), una sola `h1` per pagina, titoli in ordine, `<label>` per ogni campo, errori in `role="alert"`, messaggi in `role="status"`/`aria-live`, `aria-pressed` sui pulsanti a due stati, `aria-current` nel menu |
| Moduli | etichette e aiuti collegati ai campi, `autocomplete` corretti (`new-password`, `current-password`, `one-time-code`), requisiti della password annunciati in tempo reale |
| Mappa | la mappa interattiva ha un'alternativa equivalente: l'elenco (scheda «Elenco») e il modulo con indirizzo/GPS per scegliere il luogo |
| Movimento | `prefers-reduced-motion` rispettato |
| Dispositivi piccoli | layout a una colonna, bersagli di almeno 34-40 px, griglie con `min(…, 100%)` per non causare scorrimento orizzontale a 320 px |

## Verifiche fatte (2026-10-07)

Strumento automatico **axe-core 4.10** (regole WCAG 2.0/2.1/2.2 A e AA più le buone pratiche) lanciato nel browser sulle pagine reali,
in tema chiaro e scuro, anche da utente autenticato:

- pubbliche: elenco, mappa, dettaglio, statistiche, accesso, registrazione (con documento e selfie), SPID/CIE, normative;
- riservate: nuova segnalazione, profilo, moderazione, elenco utenti e statistiche dell'amministratore.

**Esito: nessuna violazione** (dopo aver sistemato l'ordine dei titoli nell'elenco). Prova manuale: primo `Tab` su «Vai al contenuto», `Invio` sposta il
focus sul contenuto principale.

## Cosa NON è stato verificato

Gli strumenti automatici coprono solo una parte dei criteri. Restano da fare, prima di dichiarare la conformità:

- prova con screen reader reali (VoiceOver su macOS e iOS, NVDA su Windows, TalkBack);
- prova di sola tastiera su tutti i flussi (compresa la mappa di Leaflet e il selfie con la fotocamera);
- zoom al 200% e 400% e larghezza di 320 px su un dispositivo vero (nel pannello di anteprima non è stato possibile);
- verifica dei testi di aiuto e degli errori con persone che usano tecnologie assistive;
- documento «Dichiarazione di accessibilità» (obbligo per le pubbliche amministrazioni, da valutare per il comitato).

## Come ripetere il controllo

Nel browser, su una pagina del sito, nella console:

```js
const t = await (await fetch('https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js')).text(); (0, eval)(t);
(await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}})).violations
```
