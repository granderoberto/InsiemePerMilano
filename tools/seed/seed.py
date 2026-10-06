#!/usr/bin/env python3
"""Popola il database con dati demo (deterministici, tutti fittizi).

Uso: tools/.venv/bin/python tools/seed/seed.py <database> [--oggi AAAA-MM-GG]

Il reset è distruttivo: SET FOREIGN_KEY_CHECKS=0, TRUNCATE di tutte le tabelle non di
riferimento (quartieri, stati, transizioni_ammesse, categorie, schema_migrations) e delle tabelle di Django
(django_*, auth_*), poi
FOREIGN_KEY_CHECKS=1. Serve TRUNCATE perché non attiva il trigger che blocca il DELETE
su log_attivita. Prima si genera tutto in memoria: se la generazione fallisce il
database non viene toccato.

Con lo stesso --oggi (default: data odierna UTC) lo script produce sempre gli stessi dati.
Le date sono ancorate a "oggi" alle 00:00 UTC, così nulla è nel futuro e la vista
`attivita_30_giorni` resta popolata: per l'orale rilancialo con la data del giorno.
"""
import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import bcrypt
import pymysql
from faker import Faker
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[2]
SEED = 20260929
PASSWORD_DEMO = "DemoMilano2026!"
SALT_FISSO = b"$2b$12$DemoMilanoSeedSalt202O"  # salt fisso: hash riproducibile (solo demo)
N_UTENTI, N_MODERATORI, N_SEGNALAZIONI, N_CANDIDATI = 150, 3, 300, 5
PREFISSI_DJANGO = ("django_", "auth_")
TABELLE_RIFERIMENTO = {"quartieri", "stati", "transizioni_ammesse", "categorie", "schema_migrations"}
NOTIFICHE_OBBLIGATORIE = {"verifica_account", "stato_account", "normativa_aggiornata"}
TIPI_NOTIFICA = ["verifica_account", "stato_account", "stato_segnalazione", "contenuto_bloccato",
                 "nuovo_commento", "risposta_commento", "nuova_segnalazione_quartiere", "normativa_aggiornata"]

rng = random.Random(SEED)
Faker.seed(SEED)
fake = Faker("it_IT")

# ---------------------------------------------------------------- testi segnaposto
TEMPLATES = {
    ("Ambiente", "problema"): [
        ("Rifiuti abbandonati accanto ai cestini", "Da giorni si accumulano sacchi di rifiuti e ingombranti accanto ai cestini {luogo}. Il cattivo odore e la presenza di topi rendono la zona poco vivibile."),
        ("Alberi malati con rami pericolanti", "Alcuni alberi {luogo} mostrano rami secchi e chioma rada. Dopo l'ultimo temporale un grosso ramo è caduto sul marciapiede."),
        ("Polvere e rumore dai cantieri", "I cantieri {luogo} sollevano polvere continuamente e i mezzi restano accesi per ore. Servirebbero controlli e barriere antipolvere."),
        ("Fontanella pubblica sempre rotta", "La fontanella {luogo} perde acqua da settimane e il getto è troppo debole per bere. L'acqua sprecata forma pozzanghere sul marciapiede."),
        ("Cassonetti sempre pieni e poco puliti", "I cassonetti {luogo} vengono svuotati troppo di rado e i rifiuti finiscono per terra, con cattivo odore soprattutto d'estate."),
    ],
    ("Ambiente", "proposta"): [
        ("Più alberi e verde lungo la strada", "Propongo di piantare nuovi alberi e aiuole {luogo}, dove il cemento domina e d'estate il caldo è insopportabile."),
        ("Orto urbano condiviso nell'area dismessa", "L'area dismessa {luogo} potrebbe diventare un orto urbano gestito dai residenti, con regole semplici e assegnazione a rotazione."),
        ("Raccolta differenziata più capillare", "Servono più punti di raccolta differenziata {luogo}, con contenitori per vetro, carta e organico facili da raggiungere."),
        ("Punto di raccolta per pile e olio esausto", "Chiedo un punto di raccolta per pile, farmaci scaduti e olio esausto {luogo}, oggi non c'è nulla nel raggio di un chilometro."),
        ("Casa dell'acqua di quartiere", "Una casa dell'acqua {luogo} ridurrebbe la plastica e farebbe risparmiare le famiglie: propongo di installarla vicino al parco."),
    ],
    ("Mobilità urbana", "problema"): [
        ("Semaforo pedonale troppo breve", "Il semaforo pedonale {luogo} dura pochi secondi: anziani e genitori con passeggino non riescono ad attraversare in tempo."),
        ("Buche pericolose per le biciclette", "Il fondo stradale {luogo} è pieno di buche e tombini sconnessi. Chi va in bici rischia cadute, soprattutto la sera."),
        ("Fermata senza pensilina né panchina", "La fermata dell'autobus {luogo} non ha pensilina né panchina, e con pioggia o caldo l'attesa diventa un disagio."),
        ("Auto parcheggiate sulle strisce pedonali", "Le auto in sosta selvaggia {luogo} bloccano le strisce pedonali e le rampe per le carrozzine, costringendo a scendere in strada."),
        ("Pista ciclabile interrotta", "La pista ciclabile {luogo} si interrompe all'improvviso e i ciclisti si ritrovano in mezzo al traffico senza alcuna indicazione."),
    ],
    ("Mobilità urbana", "proposta"): [
        ("Pista ciclabile protetta", "Propongo una pista ciclabile protetta {luogo}, separata dalle auto da cordoli, per collegare in sicurezza scuole e stazione."),
        ("Zona 30 davanti alla scuola", "Chiedo di istituire una zona 30 {luogo}, vicino alla scuola, con rallentatori e attraversamenti rialzati."),
        ("Più corse serali per la linea di superficie", "Le corse serali {luogo} sono troppo rade: propongo di aumentarle almeno nei fine settimana."),
        ("Rastrelliere e bike sharing", "Servono rastrelliere sicure e una stazione di bike sharing {luogo}, oggi le bici vengono legate ai pali e ai cancelli."),
        ("Attraversamento pedonale rialzato", "Un attraversamento rialzato {luogo} obbligherebbe le auto a rallentare e renderebbe la zona più sicura per i pedoni."),
    ],
    ("Politiche giovanili", "problema"): [
        ("Aula studio chiusa nel fine settimana", "L'aula studio {luogo} è chiusa sabato e domenica, proprio quando studenti e universitari ne avrebbero più bisogno."),
        ("Campetto sportivo chiuso e inutilizzato", "Il campetto {luogo} è chiuso con un lucchetto da mesi: i ragazzi non hanno un posto dove giocare e finiscono in strada."),
        ("Biblioteca con orari troppo ridotti", "La biblioteca {luogo} chiude alle 17 e non apre il sabato pomeriggio, molti giovani non riescono a frequentarla."),
        ("Mancano spazi di aggregazione per i ragazzi", "{luogo} non esiste un luogo pensato per i ragazzi: niente centro giovanile, niente spazi coperti dove ritrovarsi la sera."),
        ("Skatepark danneggiato", "Lo skatepark {luogo} ha rampe rotte e ferri scoperti che rendono pericoloso l'uso, e nessuno se ne occupa da tempo."),
    ],
    ("Politiche giovanili", "proposta"): [
        ("Spazio studio e coworking aperto fino a tardi", "Propongo di aprire uno spazio studio e coworking {luogo} con orari serali, gestito con associazioni giovanili del territorio."),
        ("Torneo sportivo di quartiere", "Un torneo sportivo annuale {luogo} avvicinerebbe i giovani allo sport e ridarebbe vita ai campetti oggi poco usati."),
        ("Sala prove musicale comunale", "Chiedo una sala prove a tariffe agevolate {luogo}: molti gruppi di ragazzi non hanno dove suonare senza disturbare."),
        ("Agevolazioni trasporti per under 25", "Propongo abbonamenti ridotti per gli under 25 residenti {luogo}, per aiutare studenti e giovani lavoratori."),
        ("Laboratori serali gratuiti", "Servirebbero laboratori serali gratuiti {luogo} su lavoro, competenze digitali e creatività, aperti ai ragazzi dai 14 anni."),
    ],
    ("Decoro urbano", "problema"): [
        ("Marciapiede dissestato e pericoloso", "Il marciapiede {luogo} è pieno di avvallamenti e lastre rotte: inciampare è facile, soprattutto per anziani e bambini."),
        ("Panchine rotte e fioriere abbandonate", "Le panchine {luogo} hanno assi mancanti e le fioriere sono piene di erbacce: la piazza dà un'immagine di abbandono."),
        ("Muri coperti di scritte", "I muri degli edifici {luogo} sono coperti di scritte e adesivi da mesi, e nessuno provvede alla pulizia."),
        ("Cestini stracolmi e non svuotati", "I cestini {luogo} sono sempre stracolmi, i rifiuti si spargono sul marciapiede e attirano insetti."),
        ("Aiuole trascurate e giardino incolto", "Il giardino pubblico {luogo} non viene tagliato da settimane: l'erba alta nasconde rifiuti e scoraggia le famiglie."),
    ],
    ("Decoro urbano", "proposta"): [
        ("Murales legali su un muro grigio", "Propongo di dedicare un muro grigio {luogo} a murales legali realizzati da artisti e studenti del territorio."),
        ("Riqualificazione dell'area giochi", "L'area giochi {luogo} è vecchia e poco curata: propongo giochi nuovi, pavimentazione antitrauma e più ombra."),
        ("Fioriere curate dai residenti", "Chiedo di affidare a gruppi di residenti la cura di fioriere e aiuole {luogo}, con un piccolo supporto del Comune."),
        ("Panchine e ombra in piazza", "La piazza {luogo} è priva di ombra e sedute: propongo panchine nuove e alberature per renderla un luogo da vivere."),
        ("Pulizia straordinaria dei portici", "I portici {luogo} avrebbero bisogno di una pulizia straordinaria e di una manutenzione regolare dell'illuminazione e dei pavimenti."),
    ],
    ("Sicurezza del territorio", "problema"): [
        ("Lampioni spenti in una strada buia", "Diversi lampioni {luogo} sono spenti da settimane e la sera la strada è completamente al buio: molti hanno paura a passare."),
        ("Incrocio pericoloso senza visibilità", "All'incrocio {luogo} le auto parcheggiate tolgono la visibilità e sono già avvenuti diversi quasi-incidenti con pedoni e bici."),
        ("Sottopasso poco sicuro la sera", "Il sottopasso {luogo} è poco illuminato e la sera è frequentato da persone che mettono a disagio chi torna a casa."),
        ("Auto troppo veloci vicino alla scuola", "Davanti alla scuola {luogo} molte auto superano i limiti di velocità all'orario di uscita dei bambini."),
        ("Cancello del parco lasciato aperto di notte", "Il cancello del parco {luogo} resta aperto anche di notte e il parco diventa luogo di bivacchi e rumore."),
    ],
    ("Sicurezza del territorio", "proposta"): [
        ("Più illuminazione sui percorsi pedonali", "Propongo di potenziare l'illuminazione dei percorsi pedonali {luogo}, con lampade a led più efficienti e ben distribuite."),
        ("Presidio nei punti critici", "Chiedo un maggiore presidio della polizia locale {luogo} nelle ore serali e all'uscita delle scuole."),
        ("Dissuasori di velocità", "Propongo dissuasori di velocità e cartelli luminosi {luogo}, dove le auto corrono nonostante i limiti."),
        ("Specchio parabolico all'incrocio", "Uno specchio parabolico all'incrocio {luogo} migliorerebbe la visibilità e ridurrebbe il rischio di incidenti."),
        ("Vigili di quartiere", "Propongo di ripristinare la figura del vigile di quartiere {luogo}, come punto di riferimento per i residenti."),
    ],
}
EXTRA = {
    "problema": ["Il problema dura ormai da più di un mese.", "Ho già provato a contattare gli uffici ma non ho avuto risposta.",
                 "Il disagio riguarda molti residenti, soprattutto anziani e famiglie con bambini.",
                 "Ho allegato alcune foto per mostrare la situazione.", "Chiedo un intervento in tempi brevi."],
    "proposta": ["Credo che questa iniziativa possa migliorare la vita di tutto il quartiere.",
                 "Sarei disponibile a collaborare con il comitato per realizzarla.",
                 "Ho visto una soluzione simile in altre città europee e funziona bene.",
                 "Il costo sarebbe contenuto rispetto ai benefici per i cittadini.",
                 "Propongo di partire con una fase di prova di alcuni mesi."],
}
CATEGORIE_AFFINI = {"Ambiente": "Decoro urbano", "Decoro urbano": "Ambiente", "Mobilità urbana": "Sicurezza del territorio",
                    "Sicurezza del territorio": "Mobilità urbana", "Politiche giovanili": "Decoro urbano"}
COMMENTI = ["Confermo, il problema c'è e mi è capitato più volte.", "Sono d'accordo, speriamo che il comitato la porti ai candidati.",
            "Grazie per la segnalazione, ho dato il mio sostegno.", "Passo di qui ogni giorno e la situazione è davvero questa.",
            "Ottima proposta, andrebbe estesa anche ad altre zone.", "Servirebbe capire i costi, ma l'idea mi sembra valida.",
            "Qualcuno sa se il Municipio è già stato informato?", "Aggiungo che la sera la situazione è anche peggio.",
            "Ho notato lo stesso problema in una via vicina.", "Bella idea, io parteciperei volentieri.",
            "Da residente non posso che appoggiare la richiesta.", "Speriamo che venga presa in carico presto.",
            "Ho parlato con altri vicini e sono tutti d'accordo.", "Sarebbe utile un sopralluogo per valutare la situazione.",
            "Concordo, una soluzione semplice potrebbe già migliorare le cose."]
RISPOSTE = ["Grazie per il contributo!", "Hai ragione, l'ho notato anche io.", "Non ne ero a conoscenza, buono a sapersi.",
            "Provo a chiedere informazioni al Municipio.", "Concordo, meglio segnalarlo con delle foto.",
            "Grazie, aggiungo altri dettagli appena posso."]
TESTO_OSCURATO = "[Testo di esempio: commento ritenuto offensivo e oscurato, dato demo]"
MOTIVI_NASCOSTO = ["Linguaggio offensivo", "Fuori tema", "Contiene dati personali di terzi"]
MOTIVI_RIFIUTO = ["Segnalazione duplicata: già presente una proposta analoga", "Non di competenza del Comune di Milano",
                  "Descrizione troppo generica per essere lavorata", "Contenuto non pertinente con la piattaforma"]
MOTIVI_SOSPENSIONE = ["Comportamento offensivo nei commenti", "Segnalazioni ripetute non pertinenti (spam)",
                      "Violazione del regolamento della community"]
TESTI_OCR = ["VIETATO IL TRANSITO", "PASSO CARRABILE", "DIVIETO DI SOSTA", "AREA CANI", "CANTIERE - LAVORI IN CORSO"]
LISTE = ["Lista Civica Demo Uno", "Lista Civica Demo Due", "Lista Civica Demo Tre", "Lista Civica Demo Quattro", "Lista Civica Demo Cinque"]
DOCUMENTI = [("privacy", "Informativa privacy (GDPR art. 13)"), ("biometrici", "Consenso al trattamento dei dati biometrici (GDPR art. 9)"),
             ("intelligenza_artificiale", "Informativa sull'uso dell'intelligenza artificiale"),
             ("termini_uso", "Termini d'uso e regolamento della community"), ("cookie", "Cookie policy"),
             ("eta_minima", "Dichiarazione di età minima (14 anni)")]
MOTIVI_FLAG = {"ok_lettura_ocr": "Documento non leggibile", "ok_corrispondenza_dati": "I dati non corrispondono a quelli inseriti",
               "ok_validita": "Documento scaduto o codici di controllo errati", "ok_autenticita": "Sospetta alterazione del documento",
               "ok_confronto_volto": "Il volto nel selfie non corrisponde alla foto del documento"}

# ---------------------------------------------------------------- utilità
def ms(d):
    return d.replace(microsecond=(d.microsecond // 1000) * 1000)


def rt(a, b, late=0.7):
    """Istante casuale in [a, b]; late<1 sposta la massa verso b (crescita nel tempo)."""
    if b <= a:
        return ms(a)
    return ms(a + (b - a) * (rng.random() ** late))


def giorni(n):
    return timedelta(days=n)


def minuti(n):
    return timedelta(minutes=n)


def js(d):
    return None if d is None else json.dumps(d, ensure_ascii=False, separators=(",", ":"), default=str)


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def sample_pesato(pool, pesi, k):
    """k elementi distinti, con probabilità proporzionale ai pesi (Efraimidis-Spirakis)."""
    chiavi = sorted(range(len(pool)), key=lambda i: rng.random() ** (1.0 / pesi[i]), reverse=True)
    return [pool[i] for i in chiavi[:k]]


# ---------------------------------------------------------------- generazione
class Demo:
    pass


def genera(anchor, categorie, nil):
    """Costruisce in memoria tutto il dataset. Restituisce l'oggetto Demo."""
    D = Demo()
    D.anchor = anchor
    lancio = anchor - giorni(240)
    D.lancio = lancio
    hash_pw = bcrypt.hashpw(PASSWORD_DEMO.encode(), SALT_FISSO).decode()
    log = []      # (t, attore, id_utente, operazione, tabella, id_oggetto, prev, new)
    notif = []    # (t, id_utente, tipo, messaggio, link)
    last_act = {}  # id_utente -> ultimo istante di attività

    def tocca(uid, t):
        if uid not in last_act or t > last_act[uid]:
            last_act[uid] = t

    def L(t, uid, op, tab, oid, prev=None, new=None):
        log.append((t, "utente" if uid else "sistema", uid, op, tab, oid, js(prev), js(new)))

    quartieri = [(f["properties"]["ID_NIL"], f["properties"]["NIL"], shape(f["geometry"])) for f in nil]
    qpesi = [rng.lognormvariate(0, 0.8) for _ in quartieri]
    cf_usati = set()
    email_usate = set()

    # ------------------------------------------------ utenti
    def nuovo_utente(ruolo_finale, metodo, reg, eta_min, eta_max, scenario=None):
        nome, cognome = fake.first_name(), fake.last_name()
        base = f"{slug(nome)}.{slug(cognome)}"
        n = rng.randint(1, 99)
        while f"{base}{n}" in email_usate:
            n += 1
        email_usate.add(f"{base}{n}")
        email = f"{base}{n}@{rng.choice(['example.com', 'example.org', 'example.net'])}"
        eta = rng.uniform(eta_min, eta_max)
        u = dict(nome=nome, cognome=cognome, email=email, metodo=metodo, ruolo_finale=ruolo_finale, scenario=scenario,
                 nascita=(reg.date() - timedelta(days=int(eta * 365.25))), creato=reg, stato="in_attesa_verifica",
                 quartiere=rng.choices(quartieri, qpesi)[0][0] if rng.random() < 0.7 else None,
                 pubblico=rng.random() < 0.40, mfa=rng.random() < 0.10, tentativi=rng.choice([0] * 9 + [1, 2]),
                 pwd=hash_pw if metodo == "credenziali" else None, cf=None, email_ver=None, attivo_da=None,
                 verifiche=[], richieste_verifica=[], peso=rng.lognormvariate(0, 1.0))
        if metodo != "credenziali":
            while True:
                h = hashlib.sha256(fake.ssn().encode()).hexdigest()
                if h not in cf_usati:
                    cf_usati.add(h)
                    break
            u["cf"] = h
            u["email_ver"] = reg
            u["stato"] = "attivo"
            u["attivo_da"] = reg + minuti(rng.uniform(1, 10))
        return u

    staff = []
    admin = nuovo_utente("amministratore", "credenziali", lancio, 30, 55)
    admin.update(stato="attivo", email_ver=lancio + minuti(3), attivo_da=lancio + minuti(5), pubblico=False)
    staff.append(admin)
    for _ in range(N_MODERATORI):
        m = nuovo_utente("moderatore", "credenziali", rt(lancio + giorni(1), lancio + giorni(3), 1), 25, 55)
        m.update(stato="attivo", email_ver=m["creato"] + minuti(5))
        m["attivo_da"] = m["creato"] + minuti(20)
        m["promosso_il"] = lancio + giorni(4) + minuti(rng.uniform(0, 600))
        m["verifiche"] = "auto"
        staff.append(m)
    mods = staff[1:]

    scenari = {"A": (0.60, giorni(5), None), "B": (0.10, giorni(5), giorni(7)), "C": (0.03, giorni(25), giorni(9)),
               "D": (0.08, giorni(5), giorni(4)), "E": (0.03, giorni(5), giorni(4)), "F": (0.04, giorni(12), giorni(0)),
               "G": (0.05, giorni(5), giorni(6)), "H": (0.03, giorni(5), giorni(6))}
    utenti_reg = []
    for _ in range(N_UTENTI):
        metodo = rng.choices(["spid", "cie", "credenziali"], [35, 20, 45])[0]
        sc = None
        if metodo == "credenziali":
            sc = rng.choices(list(scenari), [v[0] for v in scenari.values()])[0]
            _, finestra, fine_off = scenari[sc]
            if sc == "F":
                a, b = anchor - giorni(12), anchor - timedelta(hours=2)
            elif sc == "C":
                a, b = anchor - giorni(25), anchor - giorni(9)
            else:
                a, b = lancio + giorni(5), anchor - (fine_off or timedelta(hours=5))
        else:
            a, b = lancio + giorni(5), anchor - timedelta(hours=5)
        reg = rt(a, b)
        # ~40% dei registrati ha tra 14 e 25 anni
        if rng.random() < 0.42:
            eta = (14.05, 25.0)
        else:
            eta = (26.0, 75.0)
        utenti_reg.append(nuovo_utente("utente", metodo, reg, *eta, scenario=sc))
    utenti_reg.sort(key=lambda u: u["creato"])
    utenti = staff + utenti_reg
    for i, u in enumerate(utenti, 1):
        u["id"] = i
    D.utenti = utenti
    D.staff = staff
    D.mods = mods
    D.admin = admin
    per_id = {u["id"]: u for u in utenti}
    D.per_id = per_id

    # ------------------------------------------------ verifiche d'identità
    def mk_verifica(u, n, esito, t):
        f = {k: True for k in MOTIVI_FLAG}
        if esito == "approvata":
            punteggio = rng.randint(85, 99)
        elif esito == "da_rivedere":
            punteggio = rng.randint(50, 84)
            for k in rng.sample(list(MOTIVI_FLAG), 1 if punteggio >= 65 else 2):
                f[k] = False
        else:
            punteggio = rng.randint(8, 49)
            for k in rng.sample(list(MOTIVI_FLAG), rng.randint(2, 4)):
                f[k] = False
        motivo = "; ".join(MOTIVI_FLAG[k] for k, v in f.items() if not v) or None
        return dict(utente=u, tentativo=n, tipo=rng.choices(["carta_identita", "patente", "passaporto"], [60, 30, 10])[0],
                    flag=f, punteggio=punteggio, esito_ia=esito, motivo=motivo, revisore=None, finale=None,
                    motivo_rev=None, revisionata=None, creata=t)

    richieste = []   # richieste di revisione (dict con oggetto)
    for u in utenti:
        if u is admin:
            continue
        r = u["creato"]
        if u["metodo"] != "credenziali":
            continue
        if u["verifiche"] == "auto":  # moderatori: verifica approvata al primo tentativo
            v = mk_verifica(u, 1, "approvata", r + minuti(rng.uniform(3, 12)))
            u["verifiche"] = [v]
            continue
        sc = u["scenario"]
        t = r + minuti(rng.uniform(2, 20))
        vs = []
        u["email_ver"] = r + minuti(rng.uniform(1, 30))
        if sc == "A":
            vs = [mk_verifica(u, 1, "approvata", t)]
            u["stato"], u["attivo_da"] = "attivo", max(vs[0]["creata"], u["email_ver"]) + minuti(1)
        elif sc == "B":
            v1 = mk_verifica(u, 1, "rifiutata", t)
            v2 = mk_verifica(u, 2, "approvata", t + giorni(rng.uniform(0.3, 3)))
            vs = [v1, v2]
            u["stato"], u["attivo_da"] = "attivo", v2["creata"] + minuti(1)
        elif sc == "C":
            t1 = t
            vs = [mk_verifica(u, 1, "rifiutata", t1), mk_verifica(u, 2, "rifiutata", t1 + giorni(rng.uniform(0.5, 2))),
                  None]
            vs[2] = mk_verifica(u, 3, "rifiutata", vs[1]["creata"] + giorni(rng.uniform(0.5, 2)))
            richieste.append(dict(tipo="verifica", richiedente=u, oggetto=vs[2], motivo="Il documento è valido, chiedo una revisione manuale.",
                                  stato="aperta", moderatore=None, risposta=None,
                                  creata=vs[2]["creata"] + timedelta(hours=rng.uniform(2, 20)), chiusa=None))
        elif sc in ("D", "E"):
            v = mk_verifica(u, 1, "da_rivedere", t)
            rev = rng.choice(mods)
            v["revisore"] = rev
            v["revisionata"] = ms(t + timedelta(hours=rng.uniform(2, 48)))
            if sc == "D":
                v["finale"], v["motivo_rev"] = "approvata", "Documento verificato manualmente: dati e volto coerenti."
                u["stato"], u["attivo_da"] = "attivo", v["revisionata"] + minuti(1)
            else:
                v["finale"], v["motivo_rev"] = "rifiutata", "Il documento risulta alterato: verifica non superata."
            vs = [v]
        elif sc == "F":
            vs = [mk_verifica(u, 1, "da_rivedere", t)]
            if rng.random() < 0.5:
                u["email_ver"] = None
        elif sc in ("G", "H"):
            v = mk_verifica(u, 1, "rifiutata", t)
            rq = dict(tipo="verifica", richiedente=u, oggetto=v, motivo="Chiedo una revisione: ho caricato un documento valido.",
                      creata=ms(t + timedelta(hours=rng.uniform(1, 24))))
            rev = rng.choice(mods)
            rq["chiusa"] = ms(rq["creata"] + timedelta(hours=rng.uniform(10, 72)))
            rq["moderatore"] = rev
            v["revisore"], v["revisionata"] = rev, rq["chiusa"]
            if sc == "G":
                rq.update(stato="accolta", risposta="Dopo il controllo manuale il documento risulta valido.")
                v["finale"], v["motivo_rev"] = "approvata", rq["risposta"]
                u["stato"], u["attivo_da"] = "attivo", rq["chiusa"] + minuti(1)
            else:
                rq.update(stato="respinta", risposta="Il documento non supera i controlli anche dopo la revisione.")
                v["finale"], v["motivo_rev"] = "rifiutata", rq["risposta"]
            richieste.append(rq)
            vs = [v]
        u["verifiche"] = vs
        if u["stato"] == "attivo" and u["attivo_da"] and u["email_ver"] and u["attivo_da"] < u["email_ver"]:
            u["attivo_da"] = u["email_ver"] + minuti(1)
        if u["stato"] == "attivo" and u["email_ver"] is None:
            u["email_ver"] = r + minuti(5)
    for u in utenti_reg:  # utenti in attesa con email confermata da un altro percorso: nessun caso
        pass
    D.richieste = richieste

    # verifiche in ordine cronologico -> id
    tutte_verifiche = [v for u in utenti for v in (u["verifiche"] if u["verifiche"] != "auto" else [])]
    tutte_verifiche.sort(key=lambda v: (v["creata"], v["utente"]["id"]))
    for i, v in enumerate(tutte_verifiche, 1):
        v["id"] = i
    D.verifiche = tutte_verifiche
    for v in tutte_verifiche:
        u = v["utente"]
        tocca(u["id"], v["creata"])
        L(v["creata"], u["id"], "verifica_identita", "verifiche_identita", v["id"], None,
          {"tentativo": v["tentativo"], "tipo_documento": v["tipo"]})
        L(v["creata"] + minuti(0.5), None, "decisione_ia", "verifiche_identita", v["id"], None,
          {"punteggio": v["punteggio"], "esito_ia": v["esito_ia"]})
        if v["revisore"]:
            L(v["revisionata"], v["revisore"]["id"], "revisione_moderatore", "verifiche_identita", v["id"],
              {"esito_ia": v["esito_ia"]}, {"esito_finale": v["finale"], "motivo": v["motivo_rev"]})
        # notifica sull'esito
        if v["revisore"]:
            notif.append((v["revisionata"], u["id"], "verifica_account",
                          "La verifica del tuo documento è stata rivista: " + ("approvata." if v["finale"] == "approvata" else "non superata."), "/profilo"))
        elif v["esito_ia"] != "da_rivedere":
            notif.append((v["creata"] + minuti(1), u["id"], "verifica_account",
                          "Verifica dell'identità " + ("completata: il tuo account è attivo." if v["esito_ia"] == "approvata"
                                                       else "non superata: puoi riprovare o chiedere la revisione di un moderatore."), "/profilo"))

    # ------------------------------------------------ normative e consensi
    D.documenti = []
    for i, (tipo, titolo) in enumerate(DOCUMENTI, 1):
        D.documenti.append(dict(id=i, tipo=tipo, versione="1", pubblicato=lancio + timedelta(hours=1, minutes=i),
                                testo=f"[TESTO SEGNAPOSTO - documento demo, senza valore legale] {titolo}, versione 1. "
                                      "Il testo definitivo verrà redatto e pubblicato dall'amministratore."))
    for u in utenti:
        u["consensi"] = []
        if u is admin:
            docs = [d for d in D.documenti if d["tipo"] != "biometrici"]
        else:
            docs = [d for d in D.documenti if u["metodo"] == "credenziali" or d["tipo"] != "biometrici"]
        t = u["creato"] + timedelta(seconds=rng.uniform(20, 120))
        for d in docs:
            tt = max(t, d["pubblicato"] + minuti(1))
            u["consensi"].append((d["id"], tt))
            L(tt, u["id"], "accettazione_normativa", "documenti_normativi", d["id"], None, {"versione": d["versione"]})
            t = t + timedelta(seconds=rng.uniform(1, 8))
    for m in mods:
        L(m["promosso_il"], admin["id"], "cambio_ruolo", "utenti", m["id"], {"ruolo": "utente"}, {"ruolo": "moderatore"})

    # ------------------------------------------------ preferenze di notifica
    prefs = {}
    for u in utenti:
        for tipo in TIPI_NOTIFICA:
            ob = tipo in NOTIFICHE_OBBLIGATORIE
            in_app = True if ob else rng.random() < 0.9
            email = rng.random() < (0.35 if ob else 0.25)
            prefs[(u["id"], tipo)] = (in_app, email)
    D.prefs = prefs

    # ------------------------------------------------ candidati
    D.candidati = []
    for i in range(1, N_CANDIDATI + 1):
        nome, cognome = fake.first_name(), fake.last_name()
        D.candidati.append(dict(id=i, nome=nome, cognome=cognome, lista=LISTE[i - 1],
                                email=f"{slug(nome)}.{slug(cognome)}@candidati.example.org"))

    # ------------------------------------------------ segnalazioni
    cat_ids = categorie  # nome -> id
    stati_finali = (["ricevuta"] * 5 + ["attesa"] * 45 + ["approvata"] * 140 + ["rifiutata"] * 50 + ["presentata"] * 60)
    assert len(stati_finali) == N_SEGNALAZIONI
    rng.shuffle(stati_finali)
    autori = [u for u in utenti_reg if u["attivo_da"] is not None]
    per_giorno = {}
    segn = []
    for stato in stati_finali:
        s = dict(stato=stato, hidden=False, eliminata=None, modifica=None, richiesta=None)
        s["ritardo_ricevuta"] = timedelta(minutes=rng.uniform(1, 6))
        s["ritardo_dec"] = timedelta(days=min(6, rng.lognormvariate(-0.5, 0.9)) + 0.05)
        s["ritardo_pres"] = timedelta(days=rng.uniform(2, 45))
        if stato == "ricevuta":
            durata = timedelta(0)
        elif stato == "attesa":
            durata = s["ritardo_ricevuta"]
        elif stato in ("approvata", "rifiutata"):
            durata = s["ritardo_ricevuta"] + s["ritardo_dec"]
        else:
            durata = s["ritardo_ricevuta"] + s["ritardo_dec"] + s["ritardo_pres"]
        if stato == "ricevuta":
            fine_max = anchor - minuti(6)
            fine_min = anchor - timedelta(hours=3)
        elif stato == "attesa":
            fine_max, fine_min = anchor - minuti(30) - durata, anchor - giorni(20)
        else:
            fine_max, fine_min = anchor - durata - timedelta(hours=3), None
        s["finestra"] = (fine_min, fine_max)
        # autore (con pesi a coda lunga) e istante di creazione
        for _ in range(200):
            au = rng.choices(autori, [a["peso"] for a in autori])[0]
            a0 = au["attivo_da"] + minuti(30)
            lo = a0 if fine_min is None else max(a0, fine_min)
            if lo >= fine_max:
                continue
            t = rt(lo, fine_max, 0.75 if fine_min is None else 1)
            if per_giorno.get((au["id"], t.date()), 0) >= 5:
                continue
            per_giorno[(au["id"], t.date())] = per_giorno.get((au["id"], t.date()), 0) + 1
            s["autore"], s["creata"] = au, t
            break
        else:
            raise RuntimeError("autore non trovato per una segnalazione")
        s["tipo"] = rng.choices(["problema", "proposta"], [60, 40])[0]
        s["cat"] = rng.choice(list(cat_ids))
        segn.append(s)
    segn.sort(key=lambda s: s["creata"])
    for i, s in enumerate(segn, 1):
        s["id"] = i

    # popolarità latente (coda lunga); le presentate sono le più sostenute
    for s in segn:
        pop = (rng.paretovariate(1.15) - 1) * 3
        if s["stato"] == "presentata":
            pop += rng.uniform(8, 25)
        s["pop"] = pop

    stati_pubblici = ("approvata", "presentata")
    for s in segn:
        st = s["stato"]
        r = rng.random()
        if st == "ricevuta":
            esito = None
        elif st == "attesa":
            esito = "ok" if r < 0.60 else "dubbio" if r < 0.93 else "bloccato"
        elif st in stati_pubblici:
            esito = "ok" if r < 0.90 else "dubbio" if r < 0.96 else "bloccato"
        else:
            esito = "ok" if r < 0.35 else "dubbio" if r < 0.65 else "bloccato"
        s["esito"] = esito
        s["dubbio_tipo"] = rng.choices(["testo", "coerenza", "immagine"], [40, 30, 30])[0] if esito == "dubbio" else None
        s["bloccato_tipo"] = rng.choice(["testo", "immagine"]) if esito == "bloccato" else None
        if esito is None:
            s["p_mod"] = s["p_coer"] = None
        else:
            if esito == "ok":
                s["p_mod"], s["p_coer"] = rng.uniform(0.02, 0.25), rng.uniform(0.72, 0.98)
            elif esito == "dubbio":
                s["p_mod"] = rng.uniform(0.5, 0.8) if s["dubbio_tipo"] == "testo" else rng.uniform(0.05, 0.3)
                s["p_coer"] = rng.uniform(0.15, 0.45) if s["dubbio_tipo"] == "coerenza" else rng.uniform(0.6, 0.95)
            else:
                s["p_mod"] = rng.uniform(0.86, 0.99) if s["bloccato_tipo"] == "testo" else rng.uniform(0.05, 0.3)
                s["p_coer"] = rng.uniform(0.6, 0.95)
            s["p_mod"], s["p_coer"] = round(s["p_mod"], 3), round(s["p_coer"], 3)
        # testi
        nome_q = None
        s["quartiere"], geom = None, None
        qi = rng.choices(range(len(quartieri)), qpesi)[0]
        qid, qnome, qgeom = quartieri[qi]
        s["quartiere"] = qid
        minx, miny, maxx, maxy = qgeom.bounds
        while True:
            lon, lat = round(rng.uniform(minx, maxx), 6), round(rng.uniform(miny, maxy), 6)
            if qgeom.contains(Point(lon, lat)):
                break
        s["lat"], s["lon"] = lat, lon
        s["indirizzo"] = (f"{rng.choice(['Via', 'Viale', 'Piazza', 'Corso'])} {fake.last_name()} {rng.randint(1, 120)}, Milano"
                          if rng.random() < 0.6 else None)
        tit, corpo = rng.choice(TEMPLATES[(s["cat"], s["tipo"])])
        extra = rng.sample(EXTRA[s["tipo"]], rng.randint(1, 2))
        luogo = f"nella zona {qnome.title()}"
        base = corpo.format(luogo=luogo)
        s["titolo"] = tit
        s["descrizione"] = " ".join([base] + extra)
        s["descrizione_prec"] = " ".join([base] + extra[:-1]) if len(extra) > 1 and rng.random() < 0.6 else None
        # classificazioni
        cl = []
        primo = "ia" if rng.random() < 0.72 else "utente"
        cl.append((cat_ids[s["cat"]], primo, round(rng.uniform(0.62, 0.97), 3) if primo == "ia" else None))
        if rng.random() < 0.25:
            c2 = CATEGORIE_AFFINI[s["cat"]]
            o2 = "ia" if rng.random() < 0.5 else "utente"
            cl.append((cat_ids[c2], o2, round(rng.uniform(0.3, 0.6), 3) if o2 == "ia" else None))
        s["class"] = cl
        # media
        n = rng.choices([1, 2, 3, 4], [40, 30, 20, 10])[0]
        media = []
        cop = 0 if rng.random() < 0.75 else rng.randrange(n)
        img_dub = s["dubbio_tipo"] == "immagine"
        img_blk = s["bloccato_tipo"] == "immagine"
        problem_idx = rng.randrange(n)
        for k in range(n):
            video = rng.random() < 0.12
            m = dict(ordine=k + 1, copertina=(k == cop), tipo="video" if video else "foto",
                     mime="video/mp4" if video else "image/jpeg",
                     dim=rng.randint(3_000_000, 45_000_000) if video else rng.randint(300_000, 8_000_000),
                     durata=rng.randint(5, 60) if video else None,
                     exif=(round(s["lat"] + rng.uniform(-0.0005, 0.0005), 6), round(s["lon"] + rng.uniform(-0.0005, 0.0005), 6))
                     if (not video and rng.random() < 0.25) else None)
            if esito is None:
                m.update(visione=None, ps=None, pv=None, ocr=None, esito_ocr=None)
            else:
                m.update(visione="ok", ps=round(rng.uniform(0, 0.12), 3), pv=round(rng.uniform(0, 0.15), 3), ocr=None, esito_ocr=None)
                if rng.random() < 0.2 and not video:
                    m.update(ocr=rng.choice(TESTI_OCR), esito_ocr="ok")
                if k == problem_idx and img_dub:
                    m.update(visione="dubbio", ps=round(rng.uniform(0.5, 0.75), 3))
                if k == problem_idx and img_blk:
                    m.update(visione="bloccato", pv=round(rng.uniform(0.9, 0.99), 3))
            media.append(m)
        s["media"] = media
        # eventuale richiesta di revisione del contenuto bloccato
        if esito == "bloccato":
            if st in stati_pubblici:
                s["richiesta"] = "accolta"
            elif st == "attesa":
                s["richiesta"] = "aperta" if rng.random() < 0.7 else None
            else:
                s["richiesta"] = "respinta" if rng.random() < 0.4 else None
        elif s["richiesta"] is None:
            pass

    # segnalazioni nascoste (solo approvate senza attività della community), eliminate dall'autore (in attesa), modificate
    approvate = [s for s in segn if s["stato"] == "approvata"]
    for s in rng.sample(approvate, 3):
        s["hidden"] = True
    in_attesa = [s for s in segn if s["stato"] == "attesa" and s["richiesta"] is None]
    for s in rng.sample(in_attesa, min(3, len(in_attesa))):
        s["eliminata"] = s["creata"] + timedelta(hours=rng.uniform(2, 50))
    for s in segn:
        if s["stato"] != "ricevuta" and rng.random() < 0.12:
            fine = s["creata"] + s["ritardo_ricevuta"]
            s["modifica"] = rt(s["creata"] + minuti(2), max(s["creata"] + minuti(10), fine + timedelta(hours=1)), 1)
            if s["descrizione_prec"] is None:
                s["descrizione_prec"] = s["descrizione"][: max(60, len(s["descrizione"]) - 40)]
    D.segn = segn
    per_segn = {s["id"]: s for s in segn}

    # tempi delle transizioni di stato e moderatori responsabili
    cambi = []
    for s in segn:
        st = s["stato"]
        sid = s["id"]
        au = s["autore"]
        tocca(au["id"], s["creata"])
        L(s["creata"], au["id"], "creazione", "segnalazioni", sid, None, {"titolo": s["titolo"], "tipo": s["tipo"], "id_quartiere": s["quartiere"]})
        if s["esito"] is not None:
            L(s["creata"] + minuti(0.7), None, "decisione_ia", "segnalazioni", sid, None,
              {"esito_moderazione": s["esito"], "punteggio_moderazione": s["p_mod"], "punteggio_coerenza": s["p_coer"]})
        if s["esito"] == "bloccato":
            notif.append((s["creata"] + minuti(1), au["id"], "contenuto_bloccato",
                          f"La tua segnalazione «{s['titolo']}» è stata bloccata dai controlli automatici. Puoi chiedere la revisione di un moderatore.",
                          f"/segnalazioni/{sid}"))
        if s["modifica"]:
            tocca(au["id"], s["modifica"])
            L(s["modifica"], au["id"], "modifica", "segnalazioni", sid, {"descrizione": s["descrizione_prec"]}, {"descrizione": s["descrizione"]})
            L(s["modifica"] + minuti(0.7), None, "decisione_ia", "segnalazioni", sid, None, {"esito_moderazione": s["esito"] or "ok"})
        if s["eliminata"]:
            L(s["eliminata"], au["id"], "eliminazione", "segnalazioni", sid, {"eliminata_il": None}, {"eliminata_il": s["eliminata"]})
        if st == "ricevuta":
            s["t_ricevuta"] = s["t_dec"] = s["t_pres"] = None
            continue
        s["t_ricevuta"] = ms(s["creata"] + s["ritardo_ricevuta"])
        cambi.append(dict(s=s, da=1, a=2, t=s["t_ricevuta"], op=None, nota="Controlli automatici completati", wave=1))
        if st == "attesa":
            s["t_dec"] = s["t_pres"] = None
            continue
        s["t_dec"] = ms(s["t_ricevuta"] + s["ritardo_dec"])
        op = rng.choice(mods)
        s["mod_dec"] = op
        if st == "rifiutata":
            s["nota_rifiuto"] = rng.choice(MOTIVI_RIFIUTO)
            cambi.append(dict(s=s, da=2, a=4, t=s["t_dec"], op=op, nota=s["nota_rifiuto"], wave=2))
            s["t_pres"] = None
            continue
        cambi.append(dict(s=s, da=2, a=3, t=s["t_dec"], op=op, nota="Approvata dal moderatore" if s["esito"] != "dubbio" else "Approvata dopo verifica manuale del dubbio segnalato dall'IA", wave=2))
        if st == "approvata":
            s["t_pres"] = None
            continue
        s["t_pres"] = ms(s["t_dec"] + s["ritardo_pres"])
        s["mod_pres"] = rng.choice(mods)
        s["candidati"] = sorted(rng.sample(range(1, N_CANDIDATI + 1), rng.randint(1, 3)))
        cambi.append(dict(s=s, da=3, a=5, t=s["t_pres"], op=s["mod_pres"], nota="Presentata ai candidati " + ", ".join(map(str, s["candidati"])), wave=3))
    cambi.sort(key=lambda c: (c["t"], c["s"]["id"]))
    for i, c in enumerate(cambi, 1):
        c["id"] = i
    D.cambi = cambi
    nomi_stato = {2: "In attesa", 3: "Approvata", 4: "Rifiutata", 5: "Presentata ai candidati"}
    for c in cambi:
        s = c["s"]
        opid = c["op"]["id"] if c["op"] else None
        L(c["t"], opid, "cambio_stato", "segnalazioni", s["id"], {"id_stato": c["da"]}, {"id_stato": c["a"], "nota": c["nota"]})
        if c["a"] in (3, 4, 5):
            msg = {3: f"La tua segnalazione «{s['titolo']}» è stata approvata ed è ora pubblica.",
                   4: f"La tua segnalazione «{s['titolo']}» è stata rifiutata. Motivo: {c['nota']}.",
                   5: f"La tua segnalazione «{s['titolo']}» è stata presentata ai candidati Sindaco."}[c["a"]]
            notif.append((c["t"], s["autore"]["id"], "stato_segnalazione", msg, f"/segnalazioni/{s['id']}"))
        if c["a"] == 3 and not s["hidden"]:
            pass  # notifiche di quartiere costruite dopo, quando sono noti gli utenti attivi
        if c["a"] in (3, 4):
            tocca(c["op"]["id"], c["t"])
    # ultimo aggiornamento della segnalazione
    for s in segn:
        ev = [t for t in (s.get("t_ricevuta"), s.get("t_dec"), s.get("t_pres"), s.get("modifica")) if t]
        s["aggiornata"] = max(ev) if ev else None

    # richieste di revisione su segnalazioni bloccate
    for s in segn:
        if s["richiesta"]:
            t_req = ms(s["creata"] + timedelta(hours=rng.uniform(1, 20)))
            if s["stato"] in stati_pubblici:
                chiusa, stato_r, resp, mod = s["t_dec"], "accolta", "Dopo la revisione il contenuto è conforme al regolamento.", s["mod_dec"]
                t_req = min(t_req, chiusa - minuti(30))
            elif s["stato"] == "rifiutata":
                chiusa, stato_r, resp, mod = s["t_dec"], "respinta", "Il contenuto non è conforme al regolamento.", s["mod_dec"]
                t_req = min(t_req, chiusa - minuti(30))
            else:
                chiusa, stato_r, resp, mod = None, "aperta", None, None
            if t_req <= s["creata"]:
                t_req = s["creata"] + minuti(5)
            richieste.append(dict(tipo="segnalazione", richiedente=s["autore"], oggetto=s, motivo="Chiedo la revisione: il contenuto rispetta il regolamento.",
                                  stato=stato_r, moderatore=mod, risposta=resp, creata=t_req, chiusa=chiusa))

    # ------------------------------------------------ utenti che interagiscono
    pool = [u for u in utenti if u is not admin and u["attivo_da"] is not None]
    D.pool = pool
    pubbliche = [s for s in segn if s["stato"] in stati_pubblici and not s["hidden"]]

    # ------------------------------------------------ sostegni
    sostegni = []
    for s in pubbliche:
        k = min(45, int(s["pop"]))
        elig = [u for u in pool if u is not s["autore"] and u["attivo_da"] < anchor - timedelta(hours=2)]
        k = min(k, len(elig))
        if k <= 0:
            continue
        scelti = sample_pesato(elig, [max(0.05, u["peso"]) for u in elig], k)
        ap = s["t_dec"]
        for u in scelti:
            t = ap + timedelta(days=rng.expovariate(1 / 6.0))
            if t >= anchor - minuti(5):
                t = rt(ap, anchor - minuti(5), 1)
            t = max(t, u["attivo_da"] + timedelta(hours=1))
            if t >= anchor - minuti(1):
                continue
            sostegni.append(dict(u=u, s=s, t=ms(t)))
    sostegni.sort(key=lambda x: (x["t"], x["u"]["id"], x["s"]["id"]))
    D.sostegni = sostegni
    for x in sostegni:
        tocca(x["u"]["id"], x["t"])
        L(x["t"], x["u"]["id"], "sostegno", "sostegni", x["s"]["id"], None, {"id_utente": x["u"]["id"], "id_segnalazione": x["s"]["id"]})

    # ------------------------------------------------ commenti
    commenti = []
    for s in pubbliche:
        k = min(20, int(rng.expovariate(1.0 / (0.5 + 0.22 * s["pop"]))))
        if k == 0:
            continue
        ap = s["t_dec"]
        istanti = sorted(rt(ap + minuti(10), anchor - minuti(2), 0.55) for _ in range(k))
        mio = []
        for t in istanti:
            elig = [u for u in pool if u["attivo_da"] + timedelta(hours=1) < t]
            if not elig:
                continue
            padre = None
            if mio and rng.random() < 0.35:
                padre = rng.choice(mio)
            if rng.random() < 0.2 and s["autore"]["attivo_da"] < t:
                au = s["autore"]
            else:
                au = rng.choices(elig, [max(0.05, u["peso"]) for u in elig])[0]
            if padre is not None and au is padre["autore"]:
                au = rng.choices(elig, [max(0.05, u["peso"]) for u in elig])[0]
            testo = rng.choice(RISPOSTE if padre is not None else COMMENTI)
            c = dict(s=s, autore=au, padre=padre, testo=testo, creato=t, livello=(padre["livello"] + 1) if padre else 0,
                     esito="ok", punteggio=round(rng.uniform(0.01, 0.2), 3), nascosto=False, motivo=None, moderatore=None,
                     modificato=None, eliminato=None, richiesta=None, t_nascosto=None)
            r = rng.random()
            if r < 0.02:      # bloccato dall'IA
                c.update(esito="bloccato", punteggio=round(rng.uniform(0.88, 0.99), 3), testo=TESTO_OSCURATO,
                         nascosto=True, motivo="Bloccato dai controlli automatici: linguaggio offensivo", moderatore=rng.choice(mods))
                c["t_nascosto"] = t + minuti(0.5)
            elif r < 0.04:    # nascosto dal moderatore
                c.update(esito=rng.choice(["ok", "dubbio"]), punteggio=round(rng.uniform(0.3, 0.7), 3), testo=TESTO_OSCURATO,
                         nascosto=True, motivo=rng.choice(MOTIVI_NASCOSTO), moderatore=rng.choice(mods))
                c["t_nascosto"] = min(anchor - minuti(1), t + timedelta(hours=rng.uniform(1, 72)))
            elif r < 0.06:
                c.update(esito="dubbio", punteggio=round(rng.uniform(0.45, 0.7), 3))
            elif r < 0.10:
                c["modificato"] = min(anchor - minuti(1), t + timedelta(hours=rng.uniform(0.1, 30)))
            elif r < 0.12:
                c["eliminato"] = min(anchor - minuti(1), t + timedelta(hours=rng.uniform(1, 200)))
            mio.append(c)
            commenti.append(c)
    commenti.sort(key=lambda c: (c["creato"], c["s"]["id"]))
    for i, c in enumerate(commenti, 1):
        c["id"] = i
    D.commenti = commenti
    bloccati = [c for c in commenti if c["esito"] == "bloccato"]
    for c, stato_r in zip(bloccati[:3], ["accolta", "respinta", "aperta"]):
        t_req = ms(c["creato"] + timedelta(hours=rng.uniform(1, 12)))
        chiusa = ms(t_req + timedelta(hours=rng.uniform(5, 40))) if stato_r != "aperta" else None
        if chiusa and chiusa >= anchor:
            stato_r, chiusa = "aperta", None
        rq = dict(tipo="commento", richiedente=c["autore"], oggetto=c, motivo="Il mio commento non era offensivo, chiedo la revisione.",
                  stato=stato_r, moderatore=c["moderatore"] if chiusa else None,
                  risposta={"accolta": "Il commento è conforme: ripristinato.", "respinta": "Il commento viola il regolamento.", "aperta": None}[stato_r],
                  creata=t_req, chiusa=chiusa)
        if stato_r == "accolta":
            c.update(nascosto=False, motivo=None, moderatore=None, testo=rng.choice(COMMENTI), t_nascosto=None)
        richieste.append(rq)
        c["richiesta"] = rq
    for c in commenti:
        au, s = c["autore"], c["s"]
        tocca(au["id"], c["creato"])
        L(c["creato"], au["id"], "commento", "commenti", c["id"], None, {"id_segnalazione": s["id"], "id_padre": c["padre"]["id"] if c["padre"] else None})
        L(c["creato"] + minuti(0.2), None, "decisione_ia", "commenti", c["id"], None, {"esito_moderazione": c["esito"], "punteggio_moderazione": c["punteggio"]})
        if c["modificato"]:
            tocca(au["id"], c["modificato"])
            L(c["modificato"], au["id"], "modifica", "commenti", c["id"], {"testo": "(versione precedente)"}, {"testo": c["testo"]})
        if c["eliminato"]:
            tocca(au["id"], c["eliminato"])
            L(c["eliminato"], au["id"], "eliminazione", "commenti", c["id"], {"eliminato_il": None}, {"eliminato_il": c["eliminato"]})
        if c["nascosto"] and c["esito"] != "bloccato":
            L(c["t_nascosto"], c["moderatore"]["id"], "revisione_moderatore", "commenti", c["id"], {"nascosto": False}, {"nascosto": True, "motivo": c["motivo"]})
        if c["esito"] == "bloccato":
            notif.append((c["creato"] + minuti(1), au["id"], "contenuto_bloccato", "Il tuo commento è stato bloccato dai controlli automatici.", f"/segnalazioni/{s['id']}"))
        if not c["nascosto"] and not c["eliminato"]:
            if c["padre"] and c["padre"]["autore"] is not au:
                notif.append((c["creato"], c["padre"]["autore"]["id"], "risposta_commento", f"{au['nome']} ha risposto al tuo commento.", f"/segnalazioni/{s['id']}"))
            elif s["autore"] is not au:
                notif.append((c["creato"], s["autore"]["id"], "nuovo_commento", f"{au['nome']} ha commentato la tua segnalazione «{s['titolo']}».", f"/segnalazioni/{s['id']}"))

    # notifiche di nuova segnalazione nel quartiere (all'approvazione)
    for s in segn:
        if s["stato"] in stati_pubblici:
            dest = [u for u in pool if u["quartiere"] == s["quartiere"] and u is not s["autore"] and u["attivo_da"] < s["t_dec"]]
            for u in dest:
                notif.append((s["t_dec"] + minuti(1), u["id"], "nuova_segnalazione_quartiere",
                              f"Nuova segnalazione nel tuo quartiere: «{s['titolo']}».", f"/segnalazioni/{s['id']}"))

    # richieste di revisione: log e notifiche
    richieste.sort(key=lambda r: r["creata"])
    for i, r in enumerate(richieste, 1):
        r["id"] = i
        tocca(r["richiedente"]["id"], r["creata"])
        L(r["creata"], r["richiedente"]["id"], "creazione", "richieste_revisione", r["id"], None, {"tipo": r["tipo"]})
        if r["chiusa"]:
            L(r["chiusa"], r["moderatore"]["id"], "revisione_moderatore", "richieste_revisione", r["id"], {"stato": "aperta"}, {"stato": r["stato"], "risposta": r["risposta"]})
    D.richieste = richieste

    # ------------------------------------------------ sospensioni ed eliminazioni (dopo l'ultima attività dell'utente)
    reg_non_staff = [u for u in utenti_reg if u["attivo_da"] is not None and u["id"] in last_act and u["stato"] == "attivo"]
    cand = [u for u in reg_non_staff if last_act[u["id"]] + giorni(2) < anchor - giorni(14)]
    rng.shuffle(cand)
    sospesi, revocati, eliminati = cand[:5], cand[5:8], cand[8:12]
    sospensioni = []
    responsabili = mods + [admin]
    for u in sospesi + revocati:
        inizio = ms(last_act[u["id"]] + timedelta(days=rng.uniform(1, 2)))
        sp = dict(u=u, mod=rng.choice(responsabili), motivo=rng.choice(MOTIVI_SOSPENSIONE), inizio=inizio, fine=None, revocata=None, revocante=None)
        if u in sospesi:
            if rng.random() < 0.4:
                sp["fine"] = anchor + giorni(rng.randint(5, 30))
            u["stato_finale"] = "sospeso"
        else:
            sp["fine"] = ms(inizio + giorni(rng.randint(7, 30)))
            sp["revocata"] = ms(inizio + giorni(rng.uniform(3, 6)))
            sp["revocante"] = rng.choice(responsabili)
            if sp["revocata"] >= anchor:
                sp["revocata"] = anchor - minuti(30)
            u["stato_finale"] = "attivo"
        sospensioni.append(sp)
    sospensioni.sort(key=lambda x: x["inizio"])
    for i, sp in enumerate(sospensioni, 1):
        sp["id"] = i
        L(sp["inizio"], sp["mod"]["id"], "sospensione", "sospensioni", sp["id"], {"stato_account": "attivo"},
          {"stato_account": "sospeso", "motivo": sp["motivo"], "fine": sp["fine"]})
        notif.append((sp["inizio"], sp["u"]["id"], "stato_account", f"Il tuo account è stato sospeso. Motivo: {sp['motivo']}.", "/profilo"))
        if sp["revocata"]:
            L(sp["revocata"], sp["revocante"]["id"], "sospensione", "sospensioni", sp["id"], {"stato_account": "sospeso"}, {"stato_account": "attivo", "revocata": True})
            notif.append((sp["revocata"], sp["u"]["id"], "stato_account", "Il tuo account è stato riattivato.", "/profilo"))
    D.sospensioni = sospensioni
    D.eliminati = []
    for u in eliminati:
        t = ms(last_act[u["id"]] + timedelta(days=rng.uniform(1, 25)))
        t = min(t, anchor - giorni(3))
        u["eliminato_il"] = t
        u["stato_finale"] = "eliminato"
        D.eliminati.append(u)
        L(t, u["id"], "eliminazione", "utenti", u["id"], {"stato_account": "attivo"}, {"stato_account": "eliminato"})
    for u in utenti:
        u.setdefault("stato_finale", u["stato"])
        u.setdefault("eliminato_il", None)

    D.notif = notif
    D.log = log
    return D


# ---------------------------------------------------------------- scrittura
def ins(cur, tabella, colonne, righe, blocco=500):
    if not righe:
        return
    sql = f"INSERT INTO {tabella} ({colonne}) VALUES ({','.join(['%s'] * (colonne.count(',') + 1))})"
    for i in range(0, len(righe), blocco):
        cur.executemany(sql, righe[i:i + blocco])


def scrivi(cur, D, categorie):
    anchor = D.anchor
    # 1. reset
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
    tabelle = [r[0] for r in cur.fetchall()]
    # Django (progetto in apps/web) crea nello stesso database le sue tabelle django_*/auth_*: non sono dati demo
    da_svuotare = [t for t in tabelle if t not in TABELLE_RIFERIMENTO and not t.startswith(PREFISSI_DJANGO)]
    for t in da_svuotare:
        cur.execute(f"TRUNCATE TABLE `{t}`")
    cur.execute("SET FOREIGN_KEY_CHECKS=1")

    # 2. utenti (le verifiche/attivazioni hanno già stabilito lo stato di partenza)
    ins(cur, "utenti", "id,nome,cognome,email,password_hash,codice_fiscale_hash,data_nascita,metodo_registrazione,ruolo,stato_account,"
                       "id_quartiere,profilo_pubblico,mfa_attiva,tentativi_falliti,bloccato_fino,email_verificata_il,creato_il,eliminato_il",
        [(u["id"], u["nome"], u["cognome"], u["email"], u["pwd"], u["cf"], u["nascita"], u["metodo"],
          "amministratore" if u is D.admin else "utente", u["stato"], u["quartiere"], u["pubblico"], u["mfa"], u["tentativi"],
          None, u["email_ver"], u["creato"], None) for u in D.utenti])
    ins(cur, "documenti_normativi", "id,tipo,versione,testo,pubblicato_il,id_amministratore",
        [(d["id"], d["tipo"], d["versione"], d["testo"], d["pubblicato"], D.admin["id"]) for d in D.documenti])
    ins(cur, "consensi", "id_utente,id_documento,accettato_il", [(u["id"], d, t) for u in D.utenti for d, t in u["consensi"]])
    ins(cur, "verifiche_identita",
        "id,id_utente,tentativo,tipo_documento,ok_lettura_ocr,ok_corrispondenza_dati,ok_validita,ok_autenticita,ok_confronto_volto,"
        "punteggio,esito_ia,motivo,id_revisore,esito_finale,motivo_revisione,revisionata_il,creata_il",
        [(v["id"], v["utente"]["id"], v["tentativo"], v["tipo"], v["flag"]["ok_lettura_ocr"], v["flag"]["ok_corrispondenza_dati"],
          v["flag"]["ok_validita"], v["flag"]["ok_autenticita"], v["flag"]["ok_confronto_volto"], v["punteggio"], v["esito_ia"],
          v["motivo"], v["revisore"]["id"] if v["revisore"] else None, v["finale"], v["motivo_rev"], v["revisionata"], v["creata"])
         for v in D.verifiche])
    for m in D.mods:  # promozione a moderatore da parte dell'amministratore
        cur.execute("UPDATE utenti SET ruolo='moderatore' WHERE id=%s", (m["id"],))
    ins(cur, "candidati", "id,nome,cognome,lista,email", [(c["id"], c["nome"], c["cognome"], c["lista"], c["email"]) for c in D.candidati])

    # 3. segnalazioni: si inseriscono in stato 1; gli stati avanzano SOLO con cambi_stato
    ins(cur, "segnalazioni",
        "id,id_autore,tipo,titolo,descrizione,latitudine,longitudine,indirizzo,id_quartiere,id_stato,esito_moderazione,"
        "punteggio_moderazione,punteggio_coerenza,nascosta,motivo_nascosta,id_moderatore_nascosta,creata_il,aggiornata_il,eliminata_il",
        [(s["id"], s["autore"]["id"], s["tipo"], s["titolo"], s["descrizione"], s["lat"], s["lon"], s["indirizzo"], s["quartiere"], 1,
          s["esito"], s["p_mod"], s["p_coer"], s["hidden"], "Contenuto non pertinente (nascosta dal moderatore)" if s["hidden"] else None,
          D.mods[0]["id"] if s["hidden"] else None, s["creata"], None, s["eliminata"]) for s in D.segn])
    media_rows, mid = [], 0
    for s in D.segn:
        for m in s["media"]:
            mid += 1
            ext = "mp4" if m["tipo"] == "video" else "jpg"
            media_rows.append((mid, s["id"], m["tipo"], f"media/demo/{mid}.{ext}", m["mime"], m["dim"], m["durata"], m["ordine"], m["copertina"],
                               m["exif"][0] if m["exif"] else None, m["exif"][1] if m["exif"] else None, m["visione"], m["ps"], m["pv"],
                               m["ocr"], m["esito_ocr"], s["creata"] + timedelta(seconds=rng.uniform(5, 40))))
    ins(cur, "media", "id,id_segnalazione,tipo,percorso,mime_type,dimensione_byte,durata_sec,ordine,copertina,exif_lat,exif_lon,"
                      "esito_visione,punteggio_sessuale,punteggio_violenza,testo_ocr,esito_testo_ocr,caricato_il", media_rows)
    ins(cur, "classificazioni", "id_segnalazione,id_categoria,origine,confidenza",
        [(s["id"], c, o, cf) for s in D.segn for c, o, cf in s["class"]])

    # 4. cambi di stato, a ondate (le righe di una stessa segnalazione restano in ordine)
    for wave in (1, 2, 3):
        righe = [(c["id"], c["s"]["id"], c["da"], c["a"], c["op"]["id"] if c["op"] else None, c["nota"], c["t"])
                 for c in D.cambi if c["wave"] == wave]
        ins(cur, "cambi_stato", "id,id_segnalazione,id_stato_da,id_stato_a,id_operatore,nota,avvenuto_il", righe, 250)
    # il trigger imposta aggiornata_il all'orario reale: lo riallineo alla cronologia dei dati
    cur.executemany("UPDATE segnalazioni SET aggiornata_il=%s WHERE id=%s", [(s["aggiornata"], s["id"]) for s in D.segn])
    ins(cur, "invii", "id_segnalazione,id_candidato,id_moderatore,inviato_il",
        [(s["id"], c, s["mod_pres"]["id"], s["t_pres"]) for s in D.segn if s["stato"] == "presentata" for c in s["candidati"]])

    # 5. community
    ins(cur, "sostegni", "id_utente,id_segnalazione,creato_il", [(x["u"]["id"], x["s"]["id"], x["t"]) for x in D.sostegni], 500)
    for livello in range(0, 1 + max((c["livello"] for c in D.commenti), default=0)):
        ins(cur, "commenti",
            "id,id_segnalazione,id_autore,id_padre,testo,esito_moderazione,punteggio_moderazione,nascosto,motivo_nascosto,"
            "id_moderatore_nascosto,creato_il,modificato_il,eliminato_il",
            [(c["id"], c["s"]["id"], c["autore"]["id"], c["padre"]["id"] if c["padre"] else None, c["testo"], c["esito"], c["punteggio"],
              c["nascosto"], c["motivo"], c["moderatore"]["id"] if c["moderatore"] else None, c["creato"], c["modificato"], c["eliminato"])
             for c in D.commenti if c["livello"] == livello], 250)
    ins(cur, "richieste_revisione",
        "id,id_richiedente,id_segnalazione,id_commento,id_verifica,motivo,stato,id_moderatore,risposta,creata_il,chiusa_il",
        [(r["id"], r["richiedente"]["id"], r["oggetto"]["id"] if r["tipo"] == "segnalazione" else None,
          r["oggetto"]["id"] if r["tipo"] == "commento" else None, r["oggetto"]["id"] if r["tipo"] == "verifica" else None,
          r["motivo"], r["stato"], r["moderatore"]["id"] if r["moderatore"] else None, r["risposta"], r["creata"], r["chiusa"])
         for r in D.richieste])

    # 6. sospensioni ed eliminazioni
    ins(cur, "sospensioni", "id,id_utente,id_moderatore,motivo,inizio,fine,revocata_il,id_revocante",
        [(s["id"], s["u"]["id"], s["mod"]["id"], s["motivo"], s["inizio"], s["fine"], s["revocata"], s["revocante"]["id"] if s["revocante"] else None)
         for s in D.sospensioni])
    for u in D.utenti:
        if u["stato_finale"] == "sospeso":
            cur.execute("UPDATE utenti SET stato_account='sospeso' WHERE id=%s", (u["id"],))
    for u in D.eliminati:  # anonimizzazione: si tengono solo i campi obbligatori, svuotati
        cur.execute("UPDATE utenti SET nome='Utente', cognome='eliminato', email=%s, password_hash=IF(metodo_registrazione='credenziali','!',NULL),"
                    "codice_fiscale_hash=IF(metodo_registrazione IN ('spid','cie'),%s,NULL), data_nascita=MAKEDATE(YEAR(data_nascita),1),"
                    "id_quartiere=NULL, profilo_pubblico=FALSE, mfa_attiva=FALSE, stato_account='eliminato', eliminato_il=%s WHERE id=%s",
                    (f"eliminato-{u['id']}@anonimo.invalid", hashlib.sha256(f"eliminato-{u['id']}".encode()).hexdigest(), u["eliminato_il"], u["id"]))

    # 7. notifiche e preferenze
    ins(cur, "preferenze_notifica", "id_utente,tipo,in_app,email", [(uid, t, a, e) for (uid, t), (a, e) in sorted(D.prefs.items())])
    notif = [n for n in D.notif if D.prefs[(n[1], n[2])][0]]
    notif.sort(key=lambda n: (n[0], n[1]))
    ins(cur, "notifiche", "id,id_utente,tipo,messaggio,link,letta,creata_il",
        [(i, n[1], n[2], n[3][:500], n[4], rng.random() < (0.88 if n[0] < anchor - giorni(7) else 0.35), n[0]) for i, n in enumerate(notif, 1)])

    # 8. log delle attività
    log = sorted(D.log, key=lambda x: (x[0], x[3]))
    ins(cur, "log_attivita", "id,avvenuto_il,attore,id_utente,operazione,tabella,id_oggetto,dati_precedenti,dati_nuovi",
        [(i, x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7]) for i, x in enumerate(log, 1)])
    return da_svuotare


def leggi_env():
    env = {}
    for riga in (ROOT / ".env").read_text().splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            k, v = riga.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def connetti(db):
    env = leggi_env()
    return pymysql.connect(host=env["DB_HOST"], port=int(env["DB_PORT"]), user=env["DB_USER"], password=env["DB_PASSWORD"],
                           database=db, charset="utf8mb4", ssl_ca=str(ROOT / "certs" / "ca.pem"),
                           ssl_verify_cert=True, ssl_verify_identity=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("database")
    ap.add_argument("--oggi", help="data di riferimento AAAA-MM-GG (default: oggi UTC)")
    args = ap.parse_args()
    oggi = date.fromisoformat(args.oggi) if args.oggi else datetime.now(UTC).date()
    anchor = datetime.combine(oggi, time(0, 0))

    nil = json.loads((ROOT / "db" / "data" / "nil_vigenti_pgt2030.geojson").read_text())["features"]
    con = connetti(args.database)
    with con.cursor() as cur:
        cur.execute("SELECT nome, id FROM categorie WHERE attiva")
        categorie = dict(cur.fetchall())
        cur.execute("SELECT COUNT(*) FROM quartieri")
        if cur.fetchone()[0] != len(nil):
            sys.exit("La tabella quartieri non è popolata: esegui prima tools/geo/import_quartieri.py")
    print(f"Genero i dati in memoria (oggi = {oggi}) ...")
    D = genera(anchor, categorie, nil)
    print(f"Scrivo su {args.database} (reset delle tabelle non di riferimento) ...")
    try:
        with con.cursor() as cur:
            cur.execute("SET time_zone = '+00:00'")
            svuotate = scrivi(cur, D, categorie)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    print("Tabelle svuotate e ripopolate:", ", ".join(svuotate))
    print(f"Password demo di tutti gli utenti con credenziali: {PASSWORD_DEMO}")


if __name__ == "__main__":
    main()
