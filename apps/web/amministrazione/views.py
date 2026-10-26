import csv
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import (Categoria, DocumentoNormativo, LogAttivita, Notifica, Quartiere, Segnalazione, Sospensione, Utente, VerificaIdentita)
from core.services import log, normative, utenti as servizio
from core.services.errori import RegolaViolata, traduci

from core.services.ia import coda as coda_ia, esiti, fornitori, lavoratore, quota

from . import statistiche as stat

RUOLI = ["utente", "moderatore", "amministratore"]
STATI_ACCOUNT = ["in_attesa_verifica", "attivo", "sospeso", "eliminato"]
METODI = ["credenziali", "spid", "cie"]
TIPI_DOCUMENTO = ["privacy", "biometrici", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"]


def amministratore_richiesto(vista):
    @login_required
    def _v(request, *a, **kw):
        if not (request.user.is_active and request.user.ruolo == "amministratore"):
            raise Http404()
        return vista(request, *a, **kw)
    _v.__name__ = vista.__name__
    return _v


@amministratore_richiesto
def indice(request):
    return render(request, "amministrazione/indice.html", {
        "n_utenti": Utente.objects.exclude(stato_account="eliminato").count(),
        "n_sospesi": Utente.objects.filter(stato_account="sospeso").count(),
        "n_in_attesa": Utente.objects.filter(stato_account="in_attesa_verifica").count(),
        "n_segnalazioni": Segnalazione.objects.filter(eliminata_il__isnull=True).count()})


@amministratore_richiesto
def elenco_utenti(request):
    g = request.GET
    qs = Utente.objects.select_related("quartiere").order_by("-creato_il")
    if g.get("q", "").strip():
        t = g["q"].strip()
        qs = qs.filter(Q(nome__icontains=t) | Q(cognome__icontains=t) | Q(email__icontains=t) | Q(quartiere__nome__icontains=t))
    for campo, chiave in (("ruolo", "ruolo"), ("stato", "stato_account"), ("metodo", "metodo_registrazione")):
        if g.get(campo):
            qs = qs.filter(**{chiave: g[campo]})
    if g.get("identita") in ("si", "no"):
        approvata = Exists(VerificaIdentita.objects.filter(utente=OuterRef("pk")).filter(
            Q(esito_finale="approvata") | Q(esito_finale__isnull=True, esito_ia="approvata")))
        verificata = Q(metodo_registrazione__in=["spid", "cie"]) | Q(ruolo__in=["moderatore", "amministratore"]) | Q(ha_approvata=True)
        qs = qs.annotate(ha_approvata=approvata).filter(verificata if g["identita"] == "si" else ~verificata)
    pagina = Paginator(qs, 25).get_page(g.get("pagina"))
    p = g.copy(); p.pop("pagina", None)
    return render(request, "amministrazione/utenti.html", {"pagina": pagina, "filtri": g, "querystring": p.urlencode(),
                                                         "ruoli": RUOLI, "stati": STATI_ACCOUNT, "metodi": METODI})


@amministratore_richiesto
def scheda_utente(request, pk):
    u = get_object_or_404(Utente.objects.select_related("quartiere"), pk=pk)
    return render(request, "amministrazione/utente.html", {
        "u": u, "ruoli": RUOLI, "quartieri": Quartiere.objects.all(), "verifiche": u.verifiche.all(),
        "sospensioni": u.sospensioni.select_related("moderatore"),
        "n_segnalazioni": u.segnalazioni.filter(eliminata_il__isnull=True).count(),
        "n_commenti": u.commenti.filter(eliminato_il__isnull=True).count(), "n_sostegni": u.sostegni.count(),
        "log": LogAttivita.objects.filter(Q(utente=u) | Q(tabella="utenti", id_oggetto=u.id)).order_by("-avvenuto_il")[:40],
        "consensi": u.consensi.select_related("documento"), "segnalazioni": u.segnalazioni.select_related("stato").order_by("-creata_il")[:10]})


@require_POST
@amministratore_richiesto
def azione_utente(request, pk, azione):
    u = get_object_or_404(Utente, pk=pk)
    p, me = request.POST, request.user
    try:
        if u.stato_account == "eliminato":
            raise RegolaViolata("L'account è stato eliminato: i dati sono anonimizzati.")
        if azione == "modifica":
            nuovi = {"nome": p.get("nome", "").strip(), "cognome": p.get("cognome", "").strip(), "email": p.get("email", "").strip().lower(),
                     "data_nascita": date.fromisoformat(p["data_nascita"]) if p.get("data_nascita") else None,
                     "quartiere": Quartiere.objects.filter(pk=int(p["quartiere"])).first() if p.get("quartiere", "").isdigit() else None}
            if not all([nuovi["nome"], nuovi["cognome"], nuovi["email"], nuovi["data_nascita"]]):
                raise RegolaViolata("Nome, cognome, email e data di nascita sono obbligatori.")
            servizio.modifica_dati(u, me, nuovi, p.get("motivo", ""))
            messages.success(request, "Dati aggiornati e registrati nel log.")
        elif azione == "ruolo":
            prima = servizio.cambia_ruolo(u, me, p.get("ruolo", ""))
            messages.success(request, f"Ruolo cambiato: {prima} → {u.ruolo}.")
        elif azione == "sospendi":
            giorni = int(p["giorni"]) if p.get("giorni", "").isdigit() and int(p["giorni"]) > 0 else None
            servizio.sospendi(u, me, p.get("motivo", ""), giorni)
            messages.success(request, "Account sospeso.")
        elif azione == "mfa_reset":
            if not u.mfa_attiva:
                raise RegolaViolata("L'utente non ha la verifica in due passaggi attiva.")
            if not p.get("motivo", "").strip():
                raise RegolaViolata("Indica il motivo (per esempio: telefono perso, identità verificata).")
            u.mfa_attiva, u.mfa_segreto = False, None
            u.save(update_fields=["mfa_attiva", "mfa_segreto"])
            log.registra(me, "modifica", "utenti", u.id, {"mfa_attiva": True}, {"mfa_attiva": False, "motivo": p["motivo"].strip()})
            Notifica.objects.create(utente=u, tipo="stato_account", messaggio="La verifica in due passaggi del tuo account è stata azzerata da un amministratore.", link="/profilo/")
            messages.success(request, "Verifica in due passaggi azzerata.")
        elif azione == "conferma_email":
            if u.email_verificata_il:
                raise RegolaViolata("L'email è già confermata.")
            if not p.get("motivo", "").strip():
                raise RegolaViolata("Indica il motivo (per esempio: invio email non attivo, identità verificata di persona).")
            from portale.views_account import ricalcola_attivazione
            u.email_verificata_il = timezone.now()
            u.save(update_fields=["email_verificata_il"])
            log.registra(me, "modifica", "utenti", u.id, {"email_verificata_il": None}, {"email_verificata_il": u.email_verificata_il, "confermata_da_admin": True, "motivo": p["motivo"].strip()})
            attivato = ricalcola_attivazione(u)
            messages.success(request, "Email confermata dall'amministratore." + (" L'account ora è attivo." if attivato else " Resta da completare la verifica dell'identità."))
        elif azione == "verifica_identita":
            if u.identita_verificata:
                raise RegolaViolata("L'identità di questo utente risulta già verificata.")
            motivo = p.get("motivo", "").strip()
            if not motivo:
                raise RegolaViolata("Indica come hai verificato l'identità (per esempio: documento visto di persona).")
            now = timezone.now()
            with transaction.atomic():
                ultima = u.verifiche.order_by("-tentativo").first()
                if ultima is not None:
                    # c'è già una richiesta (rifiutata o da rivedere): la decisione dell'amministratore prevale
                    ultima.revisore, ultima.esito_finale, ultima.motivo_revisione, ultima.revisionata_il = me, "approvata", "Verifica manuale: " + motivo, now
                    ultima.save(update_fields=["revisore", "esito_finale", "motivo_revisione", "revisionata_il"])
                    vid = ultima.id
                else:
                    nuova = VerificaIdentita.objects.create(
                        utente=u, tentativo=1, tipo_documento="carta_identita", ok_lettura_ocr=True, ok_corrispondenza_dati=True,
                        ok_validita=True, ok_autenticita=True, ok_confronto_volto=True, punteggio=100, esito_ia="approvata",
                        motivo="Nessun controllo automatico: verifica manuale dell'amministratore.",
                        revisore=me, esito_finale="approvata", motivo_revisione="Verifica manuale: " + motivo, revisionata_il=now)
                    vid = nuova.id
                log.registra(me, "revisione_moderatore", "verifiche_identita", vid, None, {"esito_finale": "approvata", "manuale": True, "id_utente": u.id, "motivo": motivo})
            Notifica.objects.create(utente=u, tipo="verifica_account", messaggio="La tua identità è stata verificata da un amministratore: ora puoi pubblicare segnalazioni.", link="/profilo/")
            from portale.views_account import ricalcola_attivazione
            ricalcola_attivazione(u)
            messages.success(request, "Identità verificata manualmente e registrata nel log.")
        elif azione == "revoca_verifica":
            motivo = p.get("motivo", "").strip()
            if not motivo:
                raise RegolaViolata("Indica il motivo della revoca.")
            da_revocare = [x for x in u.verifiche.all() if (x.esito_finale or x.esito_ia) == "approvata"]
            if not da_revocare:
                raise RegolaViolata("Non c'è una verifica del documento da revocare" + (" (l'identità viene da SPID/CIE o dal ruolo)." if u.identita_verificata else "."))
            now = timezone.now()
            with transaction.atomic():
                for x in da_revocare:
                    x.revisore, x.esito_finale, x.motivo_revisione, x.revisionata_il = me, "rifiutata", "Revoca: " + motivo, now
                    x.save(update_fields=["revisore", "esito_finale", "motivo_revisione", "revisionata_il"])
                    log.registra(me, "revisione_moderatore", "verifiche_identita", x.id, {"esito_finale": "approvata"}, {"esito_finale": "rifiutata", "revoca": True, "motivo": motivo})
            Notifica.objects.create(utente=u, tipo="verifica_account", messaggio="La verifica della tua identità è stata revocata da un amministratore.", link="/profilo/")
            messages.success(request, "Verifica revocata.")
        elif azione == "riattiva":
            servizio.riattiva(u, me)
            messages.success(request, "Account riattivato.")
        else:
            raise Http404()
    except RegolaViolata as e:
        messages.error(request, str(e))
    except (ValueError, DatabaseError) as e:
        messages.error(request, str(traduci(e)) if isinstance(e, DatabaseError) else "Dati non validi.")
    return redirect("amm_utente", pk=pk)


@amministratore_richiesto
def registro(request):
    g = request.GET
    qs = LogAttivita.objects.select_related("utente").order_by("-avvenuto_il", "-id")
    if g.get("operazione"):
        qs = qs.filter(operazione=g["operazione"])
    if g.get("tabella"):
        qs = qs.filter(tabella=g["tabella"])
    if g.get("utente", "").strip():
        qs = qs.filter(Q(utente__email__icontains=g["utente"].strip()) | Q(utente__cognome__icontains=g["utente"].strip()))
    if g.get("attore") in ("utente", "sistema"):
        qs = qs.filter(attore=g["attore"])
    pagina = Paginator(qs, 40).get_page(g.get("pagina"))
    p = g.copy(); p.pop("pagina", None)
    operazioni = list(LogAttivita.objects.order_by().values_list("operazione", flat=True).distinct())
    tabelle = list(LogAttivita.objects.order_by().values_list("tabella", flat=True).distinct())
    return render(request, "amministrazione/registro.html", {"pagina": pagina, "filtri": g, "querystring": p.urlencode(),
                                                             "operazioni": sorted(operazioni), "tabelle": sorted(tabelle)})


@amministratore_richiesto
def statistiche_complete(request):
    periodo = request.GET.get("periodo", "30")
    return render(request, "amministrazione/statistiche.html", {"dati": stat.dataset(periodo), "periodo": periodo})


@amministratore_richiesto
def esporta_csv(request, nome):
    d = stat.dataset(request.GET.get("periodo", "30")).get(nome)
    if d is None:
        raise Http404()
    r = HttpResponse(content_type="text/csv; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{nome}.csv"'
    r.write("﻿")  # BOM: Excel riconosce l'UTF-8
    w = csv.writer(r, delimiter=";")
    w.writerow(d["intestazioni"])
    w.writerows(d["righe"])
    return r


@amministratore_richiesto
def categorie(request):
    if request.method == "POST":
        azione = request.POST.get("azione")
        if azione == "aggiungi":
            nome = request.POST.get("nome", "").strip()
            if not nome or len(nome) > 50:
                messages.error(request, "Il nome della categoria è obbligatorio (massimo 50 caratteri).")
            elif Categoria.objects.filter(nome__iexact=nome).exists():
                messages.error(request, "Esiste già una categoria con questo nome.")
            else:
                c = Categoria.objects.create(nome=nome, descrizione=request.POST.get("descrizione", "").strip() or None)
                log.registra(request.user, "creazione", "categorie", c.id, None, {"nome": nome})
                messages.success(request, "Categoria aggiunta.")
        elif azione == "attiva":
            c = get_object_or_404(Categoria, pk=request.POST.get("id"))
            c.attiva = not c.attiva
            c.save(update_fields=["attiva"])
            log.registra(request.user, "modifica", "categorie", c.id, {"attiva": not c.attiva}, {"attiva": c.attiva})
            messages.success(request, f"Categoria «{c.nome}» {'attivata' if c.attiva else 'disattivata'}.")
        return redirect("amm_categorie")
    return render(request, "amministrazione/categorie.html", {"categorie": Categoria.objects.annotate(n=Count("classificazioni__segnalazione"))})


@amministratore_richiesto
def documenti(request):
    if request.method == "POST":
        tipo, versione, testo = request.POST.get("tipo", ""), request.POST.get("versione", "").strip(), request.POST.get("testo", "").strip()
        if tipo not in TIPI_DOCUMENTO or not versione or not testo:
            messages.error(request, "Tipo, versione e testo sono obbligatori.")
        elif DocumentoNormativo.objects.filter(tipo=tipo, versione=versione).exists():
            messages.error(request, "Questa versione esiste già.")
        else:
            d = DocumentoNormativo.objects.create(tipo=tipo, versione=versione, testo=testo, amministratore=request.user)
            log.registra(request.user, "creazione", "documenti_normativi", d.id, None, {"tipo": tipo, "versione": versione})
            n = 0
            for u in Utente.objects.filter(stato_account__in=["attivo", "in_attesa_verifica", "sospeso"]):
                if tipo == "biometrici" and u.metodo_registrazione != "credenziali":
                    continue
                Notifica.objects.create(utente=u, tipo="normativa_aggiornata", messaggio=f"Nuova versione ({versione}) del documento «{tipo}»: devi accettarla per continuare a interagire.", link="/normative/accetta/")
                n += 1
            messages.success(request, f"Versione pubblicata. Notificati {n} utenti: la accetteranno al prossimo accesso.")
        return redirect("amm_documenti")
    return render(request, "amministrazione/documenti.html", {"documenti": DocumentoNormativo.objects.order_by("-id"),
                                                              "ultime": normative.ultime_versioni(), "tipi": TIPI_DOCUMENTO})


# ------------------------------------------------------------------ controlli IA (docs/piano_ia_openrouter.md)
@amministratore_richiesto
def controlli_ia(request):
    from django.conf import settings
    from core.models import CodaIA
    stati = quota.stato_tutti()
    attivi = (CodaIA.objects.filter(stato__in=["in_coda", "in_corso", "fallito"]).select_related("segnalazione", "commento__segnalazione")
              .order_by("stato", "-priorita", "creata_il")[:60])
    ultime = LogAttivita.objects.filter(tabella__in=list(fornitori.FORNITORI), operazione="decisione_ia").order_by("-id")[:25]
    t = lavoratore._thread[0]
    recenti = esiti.righe_controlli(LogAttivita.objects.filter(operazione="decisione_ia", tabella__in=["segnalazioni", "commenti"]).order_by("-id")[:15])
    return render(request, "amministrazione/ia.html", {"recenti": recenti,
        "fornitori": [{**s, "pct": round(100 * s["usate"] / s["limite"]) if s["limite"] else 0} for s in stati],
        "conteggi": coda_ia.conteggi(), "attivi": attivi, "ultime": ultime,
        "config": {"modalita": settings.IA_MODALITA, "lavoratore": settings.IA_LAVORATORE, "thread_vivo": bool(t and t.is_alive()),
                   "catena_testo": [f"{f.nome}: {m}" for f, m in fornitori.catena(False)],
                   "catena_visione": [f"{f.nome}: {m}" for f, m in fornitori.catena(True)]}})


@amministratore_richiesto
def controlli_eseguiti(request):
    """Tutti i controlli automatici fatti su segnalazioni e commenti, con esito e motivazione."""
    g = request.GET
    qs = LogAttivita.objects.filter(operazione="decisione_ia", tabella__in=["segnalazioni", "commenti"]).order_by("-id")
    if g.get("tipo") in ("segnalazioni", "commenti"):
        qs = qs.filter(tabella=g["tipo"])
    if g.get("esito") in ("ok", "dubbio", "bloccato"):
        qs = qs.filter(dati_nuovi__esito_moderazione=g["esito"])
    if g.get("fonte") == "modello":
        qs = qs.filter(dati_nuovi__has_key="fornitore").exclude(dati_nuovi__fornitore="locale")
    elif g.get("fonte") == "locale":
        qs = qs.filter(dati_nuovi__fornitore="locale")
    elif g.get("fonte") == "simulato":
        qs = qs.exclude(dati_nuovi__has_key="fornitore")
    if g.get("fornitore") in fornitori.FORNITORI:
        qs = qs.filter(dati_nuovi__fornitore=g["fornitore"])
    if g.get("q", "").strip():
        qs = qs.filter(dati_nuovi__motivazione__icontains=g["q"].strip())
    pagina = Paginator(qs, 30).get_page(g.get("pagina"))
    p = g.copy(); p.pop("pagina", None)
    return render(request, "amministrazione/ia_controlli.html", {"pagina": pagina, "righe": esiti.righe_controlli(pagina.object_list),
                                                                "filtri": g, "querystring": p.urlencode(), "nomi": list(fornitori.FORNITORI)})


@amministratore_richiesto
def richieste_fornitori(request):
    """Tutte le richieste fatte ai fornitori: modello, risposta, tempo, se hanno consumato quota."""
    g = request.GET
    qs = LogAttivita.objects.filter(tabella__in=list(fornitori.FORNITORI), operazione="decisione_ia").order_by("-id")
    if g.get("fornitore") in fornitori.FORNITORI:
        qs = qs.filter(tabella=g["fornitore"])
    if g.get("consumata") in ("si", "no"):
        qs = qs.filter(dati_nuovi__contata=(g["consumata"] == "si"))
    if g.get("tipo") in ("segnalazione", "commento"):
        qs = qs.filter(dati_nuovi__tipo=g["tipo"])
    pagina = Paginator(qs, 50).get_page(g.get("pagina"))
    p = g.copy(); p.pop("pagina", None)
    return render(request, "amministrazione/ia_richieste.html", {"pagina": pagina, "filtri": g, "querystring": p.urlencode(), "nomi": list(fornitori.FORNITORI)})


@require_POST
@amministratore_richiesto
def azione_ia(request, azione):
    from django.conf import settings
    from django.utils import timezone
    from core.models import CodaIA
    if azione == "riprova_falliti":
        n = CodaIA.objects.filter(stato="fallito").update(stato="in_coda", tentativi=0, errore=None, non_prima_di=timezone.now())
        log.registra(request.user, "modifica", "coda_ia", 0, None, {"azione": azione, "righe": n})
        messages.success(request, f"{n} controlli rimessi in coda." if n else "Nessun controllo da rimettere in coda.")
    elif azione == "esegui":
        if settings.IA_MODALITA != "coda":
            messages.error(request, "I controlli in coda non sono attivi (IA_MODALITA).")
        else:
            esito = lavoratore.passo()
            log.registra(request.user, "modifica", "coda_ia", 0, None, {"azione": azione, "esito": esito})
            messages.success(request, {"fatto": "Un controllo eseguito.", "vuoto": "Niente da controllare in questo momento.",
                                       "quota": "Quota giornaliera esaurita: i controlli riprendono a mezzanotte UTC.",
                                       "errore": "Il controllo non è riuscito: ritenterà da solo più tardi."}[esito])
    else:
        raise Http404()
    return redirect("amm_ia")
