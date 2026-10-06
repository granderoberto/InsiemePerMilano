import csv
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import (Categoria, DocumentoNormativo, LogAttivita, Notifica, Quartiere, Segnalazione, Sospensione, Utente)
from core.services import log, normative, utenti as servizio
from core.services.errori import RegolaViolata, traduci

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
