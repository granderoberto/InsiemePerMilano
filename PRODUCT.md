# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Django 5.2 LTS con template server-side, HTMX e Leaflet, CSS e JavaScript scritti a mano senza passo di build (`apps/web/static`). Confermato dall'autore: è aperto all'introduzione di un framework CSS (es. Tailwind) se serve; non è stato scelto nessuno.

## Users
- **Cittadini di Milano di almeno 14 anni** (utente principale): segnalano un problema o fanno una proposta sul proprio quartiere, spesso dallo smartphone, in strada o a casa; sostengono e commentano le segnalazioni degli altri. Livello digitale molto variabile, anche utenti poco esperti.
- **Moderatori e amministratore del comitato**: lavorano da computer, smistano le code (contenuti dubbi, verifiche d'identità, richieste di revisione), presentano le segnalazioni ai candidati Sindaco.
- **Visitatore non registrato**: legge i contenuti pubblici, non interagisce.

## Product Purpose
Piattaforma civica del comitato «Insieme per Milano»: i cittadini inseriscono segnalazioni e proposte sui quartieri, la community le sostiene e commenta, i moderatori le fanno avanzare (Ricevuta → In attesa → Approvata/Rifiutata → Presentata ai candidati). Successo: segnalazioni di qualità, verificate e sostenute, che arrivano davvero ai candidati Sindaco. Progetto d'esame (5° anno informatica) di Roberto Grande; i dati sono dimostrativi.

## Positioning
Non è un modulo di reclamo al Comune: ogni segnalazione ha un percorso pubblico e tracciabile fino ai candidati Sindaco, con identità verificata (SPID/CIE o documento + selfie) e un'IA che propone mentre l'ultima parola resta sempre a una persona.

## Operating Context
- Accesso con SPID/CIE (identità certificata, solo hash del codice fiscale) oppure credenziali + verifica del documento; 2FA TOTP opzionale per le credenziali.
- Segnalazione: tipo, titolo, descrizione, categorie, posizione dentro il Comune di Milano (88 NIL), 1-10 foto/video; massimo 5 al giorno.
- Moderazione IA su testo e media (esiti ok / dubbio / bloccato); oggi i controlli IA e la verifica del documento sono **simulati**; SPID/CIE gira su un ambiente di prova.
- Normative: GDPR (art. 13, 9, 22), termini, cookie; tutto in italiano.
- Database MySQL 8 su Aiven, schema gestito da migrazioni SQL.

## Capabilities and Constraints
- Lingua: italiano; termini tecnici standard in inglese.
- Accessibilità richiesta: WCAG 2.1 AA (contrasti, tastiera, screen reader, testo ridimensionabile).
- Ruoli: utente, moderatore, amministratore; stati account separati dal ruolo.
- Solo gli stati Approvata e Presentata sono pubblici; classifiche nominative solo per profili pubblici.
- Nessuna FK nel modello ER; vincoli applicativi elencati in `CLAUDE.md`.
- Da decidere: provider SMTP, adesione di un ente a SPID/CIE, fornitori IA veri, eventuale framework CSS.

## Brand Commitments
Nomi: «La Nostra Città, Il Nostro Futuro» (progetto) e «Insieme per Milano» (comitato). Non esistono logo ufficiale né colori del comitato: l'autore ha dichiarato nessun vincolo sull'identità visiva oltre ai nomi.

## Evidence on Hand
- Dati demo fittizi (154 utenti, 300 segnalazioni, foto segnaposto «Foto di esempio (dati demo)»); nessuna foto reale, testimonianza o dato del comitato: non vanno inventati.
- Confini dei quartieri: Comune di Milano, CC BY (`db/data`).
- Specifica completa in `docs/specifiche_utente.md`.

## Product Principles
1. **Fiducia prima di tutto**: identità, moderazione e cronologia degli stati sono visibili e comprensibili; ciò che è simulato lo si dichiara.
2. **L'IA propone, una persona decide**: l'interfaccia non nasconde mai la revisione umana.
3. **Un cittadino qualsiasi deve riuscire**: da telefono, con poca esperienza, in pochi passaggi.
4. **Il pubblico è parte del prodotto**: le segnalazioni approvate sono leggibili e condivisibili senza account.
5. **Onestà sui dati**: niente contenuti inventati presentati come reali.

## Accessibility & Inclusion
WCAG 2.1 AA come requisito della specifica (cap. 1): contrasti, navigazione da tastiera, alternative testuali, screen reader, testo ridimensionabile; rispetto di `prefers-reduced-motion` e dei temi chiaro/scuro. Verifiche manuali con screen reader ancora da fare (`docs/accessibilita.md`).
