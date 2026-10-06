"""Statistiche complete (par. 9.3): ogni insieme di dati serve sia alla pagina HTML sia all'esportazione CSV."""
from collections import Counter, OrderedDict
from datetime import date, timedelta

from django.db import connection
from django.utils import timezone

from core.models import Utente

FASCE = [(14, 17, "14-17"), (18, 25, "18-25"), (26, 35, "26-35"), (36, 50, "36-50"), (51, 65, "51-65"), (66, 200, "66 e oltre")]


def _q(sql, params=()):
    with connection.cursor() as c:
        c.execute(sql, params or None)  # senza parametri il driver non deve interpretare i "%" di DATE_FORMAT
        return c.fetchall()


def _nome(r):
    return f"{r[1]} {r[2]}"


def dataset(periodo="30"):
    giorni = {"7": 7, "30": 30}.get(periodo)
    da = timezone.now() - timedelta(days=giorni) if giorni else None
    etichetta_periodo = f"ultimi {giorni} giorni" if giorni else "dall'inizio"
    D = OrderedDict()

    D["utenti_piu_segnalazioni"] = dict(titolo="Utenti con più segnalazioni", intestazioni=["Utente", "Segnalazioni"], righe=[
        [_nome(r), r[3]] for r in _q("SELECT id, nome, cognome, n_segnalazioni FROM v_statistiche_utenti ORDER BY n_segnalazioni DESC, id LIMIT 10")])
    D["utenti_piu_interazioni"] = dict(titolo="Utenti con più interazioni ricevute (sostegni e commenti alle proprie segnalazioni)",
        intestazioni=["Utente", "Sostegni", "Commenti", "Totale"], righe=[
        [_nome(r), r[3], r[4], r[3] + r[4]] for r in _q("SELECT id, nome, cognome, n_sostegni_ricevuti, n_commenti_ricevuti FROM v_statistiche_utenti "
                                                         "ORDER BY n_sostegni_ricevuti + n_commenti_ricevuti DESC, id LIMIT 10")])
    D["utenti_piu_commenti"] = dict(titolo="Utenti con più commenti scritti", intestazioni=["Utente", "Commenti"], righe=[
        [_nome(r), r[3]] for r in _q("SELECT id, nome, cognome, n_commenti_scritti FROM v_statistiche_utenti ORDER BY n_commenti_scritti DESC, id LIMIT 10")])
    # attività = segnalazioni + commenti + sostegni nel periodo; il filtro sulla tabella evita di contare altre "creazioni"
    D["utenti_piu_attivi"] = dict(titolo=f"Utenti più attivi ({etichetta_periodo})", intestazioni=["Utente", "Azioni"], righe=[
        [_nome(r), r[3]] for r in _q(
            "SELECT u.id, u.nome, u.cognome, COUNT(*) n FROM log_attivita l JOIN utenti u ON u.id = l.id_utente "
            "WHERE l.operazione IN ('creazione','commento','sostegno') AND l.tabella IN ('segnalazioni','commenti','sostegni') "
            + ("AND l.avvenuto_il >= %s " if da else "") + "GROUP BY u.id, u.nome, u.cognome ORDER BY n DESC, u.id LIMIT 10", (da,) if da else ())])
    D["registrazioni_per_mese"] = dict(titolo="Registrazioni nel tempo", intestazioni=["Mese", "Registrazioni"], righe=[
        [r[0], r[1]] for r in _q("SELECT DATE_FORMAT(creato_il, '%Y-%m') m, COUNT(*) FROM utenti GROUP BY m ORDER BY m")])

    oggi = date.today()
    fasce, quartieri = Counter(), Counter()
    for nascita, quartiere in Utente.objects.exclude(stato_account="eliminato").values_list("data_nascita", "quartiere__nome"):
        eta = oggi.year - nascita.year - ((oggi.month, oggi.day) < (nascita.month, nascita.day))
        fasce[next(n for a, b, n in FASCE if a <= eta <= b)] += 1
        quartieri[(quartiere or "—").title()] += 1
    tot = sum(fasce.values()) or 1
    D["utenti_per_fascia_eta"] = dict(titolo="Utenti per fascia d'età (partecipazione dei giovani)", intestazioni=["Fascia", "Utenti", "%"],
                                      righe=[[n, fasce[n], round(100 * fasce[n] / tot)] for _, _, n in FASCE])
    D["utenti_per_quartiere"] = dict(titolo="Utenti per quartiere di residenza (primi 12)", intestazioni=["Quartiere", "Utenti"],
                                     righe=[[k, v] for k, v in quartieri.most_common(12)])

    v = {r[0]: r[1] for r in _q("SELECT esito_ia, COUNT(*) FROM verifiche_identita GROUP BY esito_ia")}
    n_ver = sum(v.values()) or 1
    umane = _q("SELECT COUNT(*) FROM verifiche_identita WHERE esito_ia = 'da_rivedere' OR id_revisore IS NOT NULL")[0][0]
    ribaltate_v = _q("SELECT COUNT(*) FROM verifiche_identita WHERE esito_finale IS NOT NULL AND esito_finale <> esito_ia")[0][0]
    D["verifiche_identita"] = dict(titolo="Esiti delle verifiche d'identità", intestazioni=["Voce", "Valore"], righe=[
        ["Approvate dall'IA", v.get("approvata", 0)], ["Da rivedere (coda moderatore)", v.get("da_rivedere", 0)], ["Rifiutate dall'IA", v.get("rifiutata", 0)],
        ["Quota passata alla revisione umana", f"{round(100 * umane / n_ver)}%"], ["Decisioni dell'IA ribaltate dai moderatori", ribaltate_v]])

    blocc = _q("SELECT COUNT(*) FROM segnalazioni WHERE esito_moderazione = 'bloccato' AND eliminata_il IS NULL")[0][0]
    blocc_ok = _q("SELECT COUNT(*) FROM segnalazioni WHERE esito_moderazione = 'bloccato' AND eliminata_il IS NULL AND id_stato IN (3, 5)")[0][0]
    D["contenuti_bloccati"] = dict(titolo="Contenuti bloccati dall'IA", intestazioni=["Voce", "Valore"], righe=[
        ["Segnalazioni bloccate dall'IA", blocc], ["…poi approvate da un moderatore (decisione ribaltata)", blocc_ok],
        ["Quota ribaltata", f"{round(100 * blocc_ok / blocc)}%" if blocc else "—"],
        ["Commenti nascosti", _q("SELECT COUNT(*) FROM commenti WHERE nascosto")[0][0]]])

    ore = _q("SELECT AVG(TIMESTAMPDIFF(MINUTE, s.creata_il, c.avvenuto_il)) / 60 FROM segnalazioni s JOIN cambi_stato c "
             "ON c.id_segnalazione = s.id AND c.id_stato_a = 3")[0][0]
    D["tempi"] = dict(titolo="Tempo medio tra ricezione e approvazione", intestazioni=["Voce", "Valore"],
                      righe=[["Ore medie", round(float(ore), 1) if ore is not None else "—"],
                             ["Segnalazioni approvate", _q("SELECT COUNT(DISTINCT id_segnalazione) FROM cambi_stato WHERE id_stato_a = 3")[0][0]]])
    return D
