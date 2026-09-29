# Specifiche utente

**Progetto:** La Nostra Città, Il Nostro Futuro
**Committente:** Comitato "Insieme per Milano"

## 1. Descrizione generale

La piattaforma è una web app responsive, utilizzabile sia da smartphone sia da computer. Il comitato chiede uno strumento accessibile, moderno e fortemente visuale, quindi l'interfaccia deve restare semplice e intuitiva anche per chi ha poca dimestichezza con la tecnologia.

La web app rispetta le linee guida di accessibilità WCAG 2.1 livello AA:

- contrasti adeguati;
- testo ridimensionabile;
- navigazione completa da tastiera;
- descrizioni alternative per immagini e video;
- compatibilità con gli screen reader.

La homepage mostra le segnalazioni pubbliche in due modi: come elenco e su una mappa interattiva della città. Una barra di ricerca permette di filtrarle per parola chiave, quartiere, categoria e stato.

L'intelligenza artificiale supporta la piattaforma in quattro compiti:

- verifica dell'identità;
- classificazione delle segnalazioni;
- moderazione di testi e immagini;
- controllo di coerenza tra foto e descrizione.

L'ultima parola resta sempre a un essere umano: ogni decisione automatica può essere rivista da un moderatore.

## 2. Ruoli

| Ruolo | Chi è |
|---|---|
| Visitatore | chiunque navighi senza account o senza aver effettuato l'accesso |
| Utente | cittadino registrato con identità verificata |
| Moderatore | membro del comitato che supervisiona contenuti e verifiche |
| Amministratore | membro del comitato che gestisce utenti, ruoli e configurazione |

### Permessi

| Funzione | Visitatore | Utente | Moderatore | Amministratore |
|---|:-:|:-:|:-:|:-:|
| Vedere segnalazioni pubbliche, mappa, classifiche | sì | sì | sì | sì |
| Creare, modificare, eliminare le proprie segnalazioni | no | sì | sì | sì |
| Commentare e sostenere | no | sì | sì | sì |
| Cambiare lo stato delle segnalazioni | no | no | sì | sì |
| Nascondere segnalazioni e commenti | no | no | sì | sì |
| Rivedere verifiche d'identità incerte | no | no | sì | sì |
| Rivedere contenuti bloccati dall'IA | no | no | sì | sì |
| Presentare segnalazioni ai candidati | no | no | sì | sì |
| Sospendere e riattivare account | no | no | sì | sì |
| Vedere la lista completa degli utenti | no | no | no | sì |
| Modificare i dati di qualsiasi utente | no | no | no | sì |
| Cambiare ruolo agli utenti | no | no | no | sì |
| Gestire categorie e testi normativi | no | no | no | sì |
| Consultare log e statistiche complete | no | no | no | sì |

Il visitatore vede tutti i contenuti pubblici, ma quando prova a commentare, sostenere o creare una segnalazione il sistema lo invita ad accedere o a registrarsi.

Il primo amministratore viene creato all'installazione della piattaforma. Nessun utente può assegnarsi un ruolo da solo.

### Stati dell'account

| Stato | Significato | Cosa può fare |
|---|---|---|
| In attesa di verifica | registrato con credenziali, verifica non ancora conclusa | solo consultazione |
| Attivo | identità verificata | tutte le funzioni del suo ruolo |
| Sospeso | bloccato da un moderatore o amministratore | solo consultazione |
| Eliminato | cancellato dall'utente, dati anonimizzati | nessun accesso |

## 3. Registrazione e accesso

L'utente può registrarsi e accedere in due modi. Entrambi garantiscono che ogni account corrisponda a una persona reale, come richiede il comitato.

### 3.1 Accesso con SPID o CIE

L'utente sceglie "Entra con SPID" o "Entra con CIE" e si autentica presso il proprio gestore di identità. La piattaforma riceve:

- nome;
- cognome;
- data di nascita;
- codice fiscale;
- email.

L'identità risulta già certificata, quindi l'account diventa subito attivo senza caricare documenti. Al primo accesso l'utente completa il profilo con il quartiere di residenza, facoltativo, e accetta le normative (paragrafo 3.4).

Il sistema non salva il codice fiscale in chiaro, ma una sua impronta crittografica (hash). Questa basta a impedire che la stessa persona crei più account, senza conservare un dato sensibile.

### 3.2 Registrazione con credenziali

Chi non ha SPID o CIE si registra compilando un modulo:

| Dato | Obbligatorio | Vincoli |
|---|---|---|
| Nome | sì | massimo 50 caratteri |
| Cognome | sì | massimo 50 caratteri |
| Email | sì | formato valido, unica nel sistema, confermata tramite link |
| Password | sì | almeno 8 caratteri, con almeno una maiuscola, un numero e un simbolo; salvata solo come hash |
| Data di nascita | sì | età minima 14 anni |
| Quartiere di residenza | no | scelto da un elenco predefinito dei quartieri di Milano |
| Documento d'identità fronte e retro | sì | carta d'identità, patente o passaporto; JPG, PNG o PDF, massimo 5 MB per lato |
| Selfie | sì | scattato al momento dalla fotocamera, non caricato dalla galleria |

L'account resta in attesa finché l'utente non conferma l'email e il sistema non completa la verifica del documento.

### 3.3 Verifica automatica dell'identità

Il sistema verifica il documento con un modulo di intelligenza artificiale, senza intervento manuale del moderatore. Il modulo esegue questi controlli:

1. **Lettura del documento (OCR).** Estrae nome, cognome, data di nascita, numero e scadenza del documento.
2. **Corrispondenza dei dati.** Confronta i dati letti con quelli inseriti nel modulo.
3. **Validità.** Controlla che il documento non sia scaduto e che i codici di controllo stampati sul documento risultino corretti.
4. **Autenticità.** Cerca segni di alterazione o fotomontaggio.
5. **Confronto del volto.** Confronta il selfie con la foto sul documento.

Per ogni controllo il modulo produce un esito, e per la verifica nel suo complesso un punteggio di attendibilità da 0 a 100.

| Punteggio | Esito |
|---|---|
| 85 o più | approvata: l'account diventa attivo |
| da 50 a 84 | da rivedere: la verifica passa alla coda di un moderatore |
| sotto 50 | rifiutata: l'utente riceve il motivo e può riprovare |

L'utente può ripetere la verifica al massimo tre volte. Dopo un rifiuto può sempre chiedere la revisione di un moderatore.

Il moderatore vede, per ogni verifica:

- lo stato;
- il punteggio di attendibilità;
- l'esito dei singoli controlli.

Può confermare o ribaltare la decisione dell'IA, indicando il motivo.

Al termine della verifica il sistema cancella le immagini del documento e il selfie. Conserva solo l'esito, il punteggio, la data e, se presente, il moderatore che ha rivisto la decisione.

### 3.4 Normative e consensi

Durante la registrazione, o al primo accesso con SPID/CIE, l'utente legge e accetta i documenti previsti dalla normativa vigente. Ogni consenso ha la propria casella, mai preselezionata:

- **Informativa privacy** (GDPR, art. 13): quali dati la piattaforma raccoglie, perché, per quanto tempo e con quali diritti per l'utente.
- **Consenso al trattamento dei dati biometrici** (GDPR, art. 9): solo per chi si registra con credenziali, perché il confronto del selfie usa il volto.
- **Informativa sull'uso dell'intelligenza artificiale**: spiega che verifica, classificazione e moderazione avvengono in modo automatico e che l'utente ha sempre diritto alla revisione di una persona (GDPR, art. 22).
- **Termini d'uso e regolamento della community**: regole di comportamento, contenuti vietati, conseguenze delle violazioni.
- **Cookie policy**: con banner che permette di rifiutare i cookie non necessari.
- **Età minima**: dichiarazione di avere almeno 14 anni, l'età del consenso digitale in Italia.

Il sistema registra quale versione di ogni documento l'utente ha accettato, con data e ora. Quando un documento cambia, al primo accesso successivo l'utente deve accettare la nuova versione per continuare a interagire.

### 3.5 Accesso e sicurezza

L'utente registrato con credenziali accede con email e password. Può attivare l'autenticazione a due fattori tramite app di autenticazione.

Dopo cinque tentativi di accesso falliti, il sistema blocca temporaneamente l'account per 15 minuti. Se l'utente dimentica la password, la reimposta tramite un link inviato alla propria email.

## 4. Gestione del profilo

Dal profilo l'utente consulta:

- i propri dati;
- le segnalazioni che ha inserito, con il relativo stato;
- i commenti scritti;
- i sostegni espressi;
- le proprie statistiche personali.

Nome, cognome e data di nascita restano bloccati dopo la verifica, perché corrispondono all'identità certificata. L'utente può modificare liberamente quartiere, password e preferenze di notifica. Il cambio di email richiede una nuova conferma tramite link.

L'utente sceglie se rendere pubblico il proprio profilo:

- **Profilo pubblico**: gli altri vedono nome, iniziale del cognome, quartiere e statistiche, e l'utente può comparire nelle classifiche.
- **Profilo privato**: accanto ai suoi contenuti compare solo il nome con l'iniziale del cognome.

L'utente può eliminare il proprio account confermando l'operazione. Il sistema rimuove i suoi dati personali ma conserva in forma anonima segnalazioni, commenti, sostegni e registro delle attività. In questo modo non si compromette la tracciabilità e non si altera la classifica.

## 5. Segnalazioni e proposte

Un utente con account attivo crea una segnalazione tramite il pulsante "+" nella homepage.

| Dato | Vincoli |
|---|---|
| Tipo | proposta oppure segnalazione di un problema |
| Titolo | obbligatorio, massimo 100 caratteri |
| Descrizione | obbligatoria, tra 30 e 2000 caratteri |
| Categorie | almeno una; l'IA le suggerisce, l'utente conferma o cambia |
| Posizione | obbligatoria, all'interno del Comune di Milano |
| Quartiere | ricavato automaticamente dalla posizione |
| Media | da 1 a 10 file tra foto e video, combinabili liberamente |

### 5.1 Media

| Tipo | Formato | Limiti per file |
|---|---|---|
| Foto | JPG, PNG, HEIC | fino a 10 MB |
| Video | MP4, MOV | massimo 60 secondi e 50 MB |

Senza almeno un file il sistema non permette l'invio. L'utente può riordinare i file e sceglierne uno come copertina.

Prima della pubblicazione il sistema rimuove i metadati dai file. Così la posizione esatta e i dati del dispositivo dell'autore non restano accessibili a chi scarica l'immagine.

### 5.2 Posizione

L'utente indica il luogo della segnalazione in uno di questi modi:

- **"Usa la mia posizione"**: il sistema legge il GPS del dispositivo, previa autorizzazione del browser.
- **Mappa interattiva**: l'utente sposta un segnaposto sul punto esatto.
- **Ricerca per indirizzo**: il segnaposto si posiziona sull'indirizzo digitato.

Se una foto contiene coordinate nei metadati, il sistema le propone come posizione di partenza. In ogni caso l'utente può spostare il segnaposto: spesso chi segnala non si trova più sul posto.

Dalla posizione il sistema ricava automaticamente il quartiere. Se il punto cade fuori dal Comune di Milano, il sistema non accetta la segnalazione.

### 5.3 Prima dell'invio

Il sistema mostra le segnalazioni simili già presenti nella stessa zona. Se il problema è già stato segnalato, l'utente può sostenere quella esistente invece di crearne un doppione.

Per limitare lo spam, ogni utente può inserire al massimo 5 segnalazioni al giorno.

### 5.4 Modifica ed eliminazione

L'autore può modificare testo, categorie, posizione e media più volte, ma solo finché la segnalazione si trova negli stati Ricevuta o In attesa. Ogni modifica:

- salva la versione precedente nel registro delle attività;
- ripassa dai controlli automatici del capitolo 6.

Nella stessa fase l'autore può anche eliminare la segnalazione.

Il moderatore può nascondere una segnalazione in qualsiasi momento, indicando il motivo. La segnalazione nascosta non viene cancellata dal database, così ne resta traccia.

## 6. Controlli automatici con intelligenza artificiale

Ogni segnalazione, e ogni commento per la parte testuale, passa da una serie di controlli automatici al momento dell'invio.

### 6.1 Classificazione della categoria

Un modello di classificazione del testo analizza titolo e descrizione e propone una o più categorie, ciascuna con un livello di confidenza. Esempi di categorie:

- Ambiente;
- Mobilità urbana;
- Politiche giovanili;
- Decoro urbano;
- Sicurezza del territorio.

L'utente vede i suggerimenti già selezionati e può confermarli o cambiarli. Il sistema registra per ogni categoria se l'ha scelta l'IA, l'utente o un moderatore. Questo permette di misurare nel tempo la precisione del modello.

### 6.2 Moderazione del testo

Un modello di analisi del linguaggio controlla titolo, descrizione e commenti alla ricerca di:

- insulti;
- linguaggio volgare;
- incitamento all'odio;
- minacce;
- dati personali di terzi, come numeri di telefono o targhe.

### 6.3 Moderazione di immagini e video

Su ogni file multimediale il sistema esegue due analisi:

- **Classificazione visiva.** Un modello di visione riconosce contenuti sessuali, violenti o cruenti. Per i video analizza una serie di fotogrammi estratti a intervalli regolari.
- **OCR.** Estrae l'eventuale testo presente nell'immagine, come scritte, cartelli o screenshot, e lo passa al filtro del paragrafo 6.2. Così un insulto scritto dentro una foto non sfugge ai controlli.

### 6.4 Coerenza tra immagine e testo

Un modello di visione valuta se le immagini sono pertinenti con la descrizione e la categoria. Ad esempio, segnala il caso di una foto di un parco allegata a una segnalazione sul traffico.

### 6.5 Esito dei controlli

Ogni controllo produce un punteggio. Il sistema decide in base al risultato peggiore:

| Esito | Conseguenza |
|---|---|
| Nessun problema | la segnalazione procede normalmente nel ciclo di vita |
| Dubbio | la segnalazione resta In attesa e compare nella coda del moderatore con l'indicazione del problema rilevato |
| Contenuto grave (sessuale, violento, d'odio) | il sistema blocca la pubblicazione, avvisa l'autore con il motivo e segnala il caso ai moderatori |

L'autore di un contenuto bloccato può sempre chiedere la revisione di un moderatore.

## 7. Ciclo di vita della segnalazione

Una segnalazione attraversa questi stati:

1. **Ricevuta**: il sistema la assegna automaticamente all'invio e avvia i controlli del capitolo 6.
2. **In attesa**: la segnalazione aspetta la valutazione di un moderatore, eventualmente con le segnalazioni dell'IA.
3. **Approvata** oppure **Rifiutata**: il moderatore la pubblica oppure la respinge. Se la respinge, deve indicarne il motivo.
4. **Presentata ai candidati**: il moderatore inoltra una segnalazione approvata ai candidati Sindaco, scegliendo a quali. La classifica dei sostegni lo aiuta a decidere quali priorità presentare.

Solo il moderatore fa avanzare una segnalazione, e solo lungo questa sequenza. Rifiutata e Presentata ai candidati sono stati finali.

| Stato | Chi la vede |
|---|---|
| Ricevuta, In attesa | solo l'autore e i moderatori |
| Rifiutata | solo l'autore, con il motivo, e i moderatori |
| Approvata, Presentata ai candidati | tutti, anche i visitatori |

Ogni segnalazione pubblica mostra la propria cronologia degli stati, con la data di ogni passaggio.

## 8. Interazione della community

Solo gli utenti con account attivo possono interagire, e solo con le segnalazioni approvate.

**Sostegno.** Ogni utente può esprimere un solo sostegno per segnalazione e può ritirarlo in seguito. L'autore non può sostenere la propria segnalazione.

**Commenti.** L'utente può commentare una segnalazione oppure rispondere al commento di un altro utente, creando discussioni. Un commento contiene al massimo 1000 caratteri e passa dalla moderazione automatica del testo. L'utente può modificare o eliminare i propri commenti; il moderatore può nascondere quelli offensivi o fuori tema, indicando il motivo.

**Condivisione.** Ogni segnalazione ha un link condivisibile sui social e sulle app di messaggistica.

## 9. Statistiche

### 9.1 Statistiche pubbliche

Tutti, visitatori compresi, vedono:

- la classifica delle segnalazioni più sostenute, filtrabile per quartiere, categoria e periodo;
- il numero di segnalazioni per quartiere e per categoria, anche come mappa di calore;
- il numero di segnalazioni per stato, per mostrare quante sono state approvate e presentate ai candidati;
- le classifiche degli utenti con profilo pubblico: più segnalazioni, più sostegni ricevuti, più commenti, più attivi.

### 9.2 Statistiche personali

Ogni utente vede nel proprio profilo:

- quante segnalazioni ha creato e in che stato si trovano;
- quanti sostegni hanno ricevuto;
- quanti commenti ha scritto;
- la propria posizione nelle classifiche.

### 9.3 Statistiche complete (dashboard amministratore)

L'amministratore vede, per tutti gli utenti:

- utenti con più segnalazioni;
- utenti con più interazioni ricevute (sostegni e commenti alle proprie segnalazioni);
- utenti con più commenti scritti;
- utenti più attivi.

Per "attività" si intende il numero totale di azioni (segnalazioni, commenti, sostegni) in un periodo scelto, ad esempio ultimi 7 giorni, 30 giorni o dall'inizio.

La dashboard mostra anche:

- andamento delle registrazioni nel tempo;
- distribuzione degli utenti per fascia d'età e quartiere, per misurare la partecipazione dei giovani;
- esiti delle verifiche d'identità e quota di casi passati alla revisione umana;
- numero di contenuti bloccati dall'IA e quota di decisioni ribaltate dai moderatori;
- tempo medio tra ricezione e approvazione di una segnalazione.

Le statistiche si possono esportare in formato CSV.

## 10. Dashboard

### 10.1 Dashboard amministratore

L'amministratore dispone di un pannello riservato con queste funzioni:

- **Elenco utenti.** Mostra tutti gli utenti registrati, con ricerca per nome, email e quartiere e filtri per ruolo, stato dell'account e metodo di registrazione (SPID, CIE, credenziali).
- **Scheda utente.** Mostra dati, stato e punteggio della verifica d'identità, segnalazioni, commenti, statistiche e cronologia delle azioni.
- **Modifica dati.** L'amministratore può correggere i dati di un utente indicando sempre il motivo; ogni modifica finisce nel log.
- **Cambio ruolo.** L'amministratore promuove un utente a moderatore o amministratore, oppure lo riporta a utente.
- **Sospensione.** L'amministratore sospende o riattiva gli account, con motivo e durata.
- **Configurazione.** L'amministratore gestisce l'elenco delle categorie e pubblica nuove versioni dei documenti normativi.
- **Log e statistiche.** L'amministratore consulta il registro completo delle attività e le statistiche del paragrafo 9.3.

### 10.2 Area moderatore

Il moderatore dispone di tre code di lavoro:

- **Verifiche da rivedere.** Contiene i documenti con punteggio di attendibilità tra 50 e 84 e le richieste di revisione dopo un rifiuto.
- **Contenuti segnalati.** Contiene segnalazioni e commenti bloccati o messi in dubbio dall'IA, con il motivo e il punteggio.
- **Segnalazioni in attesa.** Contiene le segnalazioni da approvare o rifiutare, e quelle approvate da presentare ai candidati.

## 11. Notifiche

L'utente riceve una notifica nell'app, e facoltativamente via email, quando:

- la verifica del suo account si conclude, positivamente o no;
- il suo account viene sospeso o riattivato;
- una sua segnalazione cambia stato o viene bloccata dai controlli automatici;
- qualcuno commenta una sua segnalazione o risponde a un suo commento;
- viene pubblicata una nuova segnalazione nel suo quartiere;
- un documento normativo cambia e serve una nuova accettazione.

L'utente sceglie dal profilo quali notifiche ricevere, tranne quelle su account e normative, che sono obbligatorie.

## 12. Tracciabilità

Il sistema registra in un log ogni azione significativa:

- data e ora;
- autore, che può essere un utente oppure il sistema per le azioni automatiche dell'IA;
- tipo di operazione;
- elemento coinvolto;
- valore precedente e valore nuovo, per le modifiche.

Le operazioni registrate sono: accesso, creazione, modifica, eliminazione, commento, sostegno, cambio di stato, verifica d'identità, decisione dell'IA, revisione del moderatore, sospensione, cambio di ruolo, accettazione delle normative.

Solo l'amministratore consulta il log completo e nessuno può modificarlo o cancellarlo. Il pubblico vede la cronologia degli stati di ogni segnalazione.

In questo modo la piattaforma garantisce la trasparenza richiesta dal comitato. Ogni proposta presentata ai candidati porta con sé la storia completa: chi l'ha scritta, come è cambiata, quali controlli ha superato e quanti cittadini l'hanno sostenuta.
