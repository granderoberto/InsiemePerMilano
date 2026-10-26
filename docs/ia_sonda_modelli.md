# Fase 0: prova dei modelli gratuiti di OpenRouter (2026-10-26)

Eseguita con `tools/ia/sonda_modelli.py` (13 richieste in tutto; risultati grezzi in `tools/ia/risultati/`, non versionati). Ogni richiesta chiedeva `provider.data_collection = "deny"`. Il test usa 10 commenti etichettati e 5 foto **disegnate** (quelle dei dati demo), quindi la qualità sulle foto è solo indicativa.

## Risultati

| Modello | Esito | Note |
|---|---|---|
| `recursive/flint-v1.0:free` (testo) | **funziona**: JSON valido, id completi, **10/10 giudizi corretti**, motivazioni di 5 parole al massimo | è un modello che «ragiona»: 12 secondi e circa 1760 token con `max_tokens` 2000; con 400 token la risposta resta vuota |
| `dots-studio/dots-3-note-preview:free` (testo+foto) | funziona solo con molti token: JSON valido con `max_tokens` 6000, **coerenza giusta 3/5**, nessuna foto segnalata | 41 secondi e circa 6200 token per 5 foto; con 2000 token la risposta resta vuota (`finish: length`) |
| `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free` | **non utilizzabili ora**: 429 «rate-limited upstream» da Google AI Studio, riprovato 3 volte a distanza di minuti | superano il filtro privacy, ma il fornitore a monte è saturo; da riprovare in altre ore |
| `xingchen-agi/xing4.0-29b-a4b:free` | 429 upstream (fornitore Phala), riprovato 2 volte | come sopra |
| `nvidia/nemotron-3-super-120b-a12b:free`, `nvidia/nemotron-3.5-super-vl:free`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`, `liquid/lfm-2.5-2.6b:free` | **esclusi dalla privacy**: 404 «No endpoints found matching your data policy (Free model training)» | questi modelli gratuiti richiedono di consentire l'addestramento sui dati |
| `thinkingmachines/inkling:free` | 403 «only available on agentic harnesses» | non si può usare da un'applicazione normale |

## Cosa cambia nel piano

1. **La privacy restringe molto la scelta.** Con `deny` restano pochi modelli: oggi `flint` per il testo e `dots-3` per le foto. Gemma sarebbe la scelta migliore ma è bloccata a monte. Il vincolo «nessun addestramento sui dati» **resta**: i modelli di NVIDIA e Liquid si escludono.
2. **Modelli che ragionano = risposte lente.** 12-40 secondi per richiesta e `max_tokens` alti (2000 per il testo, 6000 per le foto). Conferma la scelta della coda in background: l'utente non aspetta mai l'IA. Il tempo massimo del lavoratore va portato da 25 a **90 secondi**.
3. **La quota ha un contatore ufficiale.** `GET /api/v1/key` (gratuito, non consuma richieste) restituisce `free_model_daily_requests` con `used`, `limit` (50) e `remaining`. Il contatore del piano si legge da lì, con il registro locale come riserva.
4. **Gli errori non consumano quota**: le risposte 404, 403 e 429 «upstream» non hanno aumentato `used`; hanno contato solo le risposte 200. Il lavoratore può quindi passare al modello successivo dopo un 429 a monte senza perdere richieste.
5. **Qualità sulle foto da verificare.** 3/5 su disegni non basta per decidere: la taratura (fase 5) userà foto vere. Se `dots-3` resta troppo lento o impreciso, le foto restano al solo controllo locale.
6. **La catena di riserva è corta.** Il piano prevedeva più modelli: oggi sono due, e ogni giorno possono cambiare. Serve un controllo periodico (`--elenco` e la sonda) e il comportamento «nessun modello disponibile» deve essere un caso normale (`dubbio`, la segnalazione aspetta).

## Ancora da verificare

- Orario di azzeramento della quota: `used` va letto prima e dopo mezzanotte UTC (il campo `/key` non indica l'orario).
- Se Gemma torna disponibile in altre ore.
