from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import (APPROVATA, Utente, IN_ATTESA, PRESENTATA, RIFIUTATA, Candidato, Commento, Invio, RichiestaRevisione,
                         Segnalazione, VerificaIdentita)
from core.queries import con_conteggi
from core.services import log, utenti as servizio_utenti
from core.services.errori import RegolaViolata, traduci
from core.services.stati import cambia_stato
from portale.views import notifica, notifica_quartiere
from portale.views_account import ricalcola_attivazione


def moderatore_richiesto(vista):
    @login_required
    def _v(request, *a, **kw):
        if not request.user.e_moderatore:
            raise Http404()
        return vista(request, *a, **kw)
    _v.__name__ = vista.__name__
    return _v


@moderatore_richiesto
def dashboard(request):
    base = Segnalazione.objects.filter(eliminata_il__isnull=True).select_related("autore", "quartiere", "stato")
    in_attesa = base.filter(stato_id=IN_ATTESA).order_by("creata_il")
    segnalate = base.filter(esito_moderazione__in=["dubbio", "bloccato"], stato_id__in=[1, 2]).order_by("creata_il")
    commenti = (Commento.objects.filter(esito_moderazione__in=["dubbio", "bloccato"], eliminato_il__isnull=True)
                .select_related("autore", "segnalazione").order_by("-creato_il")[:30])
    da_presentare = con_conteggi(base.filter(stato_id=APPROVATA, nascosta=False)).order_by("-n_sostegni", "-creata_il")
    verifiche = (VerificaIdentita.objects.filter(esito_ia="da_rivedere", revisore__isnull=True).select_related("utente"))
    richieste = RichiestaRevisione.objects.filter(stato="aperta").select_related("richiedente", "segnalazione", "verifica__utente")
    return render(request, "moderazione/dashboard.html", {
        "richieste": richieste,
        "in_attesa": in_attesa, "segnalate": segnalate, "commenti": commenti, "da_presentare": da_presentare,
        "verifiche": verifiche, "candidati": Candidato.objects.all()})


@moderatore_richiesto
def segnalazione(request, pk):
    s = get_object_or_404(Segnalazione.objects.select_related("autore", "quartiere", "stato"), pk=pk)
    return render(request, "moderazione/segnalazione.html", {
        "s": s, "media": s.media.all(), "cronologia": s.cambi_stato.select_related("stato_a", "operatore"),
        "candidati": Candidato.objects.all(), "n_sostegni": s.sostegni.count(),
        "categorie": s.classificazioni.select_related("categoria")})


def _esegui(request, pk, azione):
    s = get_object_or_404(Segnalazione, pk=pk)
    u = request.user
    motivo = request.POST.get("motivo", "").strip()
    try:
        if azione == "approva":
            cambia_stato(s, APPROVATA, u, "Approvata dal moderatore")
            notifica(s.autore, "stato_segnalazione", f"La tua segnalazione «{s.titolo}» è stata approvata ed è ora pubblica.", reverse("dettaglio", args=[s.id]))
            notifica_quartiere(s)
            messages.success(request, "Segnalazione approvata e pubblicata.")
        elif azione == "rifiuta":
            if not motivo:
                raise RegolaViolata("Per rifiutare indica il motivo.")
            cambia_stato(s, RIFIUTATA, u, motivo)
            notifica(s.autore, "stato_segnalazione", f"La tua segnalazione «{s.titolo}» è stata rifiutata. Motivo: {motivo}", reverse("dettaglio", args=[s.id]))
            messages.success(request, "Segnalazione rifiutata.")
        elif azione == "presenta":
            ids = [int(x) for x in request.POST.getlist("candidati") if x.isdigit()]
            cand = list(Candidato.objects.filter(pk__in=ids))
            if not cand:
                raise RegolaViolata("Scegli almeno un candidato.")
            with transaction.atomic():
                cambia_stato(s, PRESENTATA, u, "Presentata a: " + ", ".join(f"{c.nome} {c.cognome}" for c in cand))
                for c in cand:
                    Invio.objects.create(segnalazione=s, candidato=c, moderatore=u)
            notifica(s.autore, "stato_segnalazione", f"La tua segnalazione «{s.titolo}» è stata presentata ai candidati Sindaco.", reverse("dettaglio", args=[s.id]))
            messages.success(request, "Segnalazione presentata ai candidati.")
        elif azione == "nascondi":
            if not motivo:
                raise RegolaViolata("Per nascondere indica il motivo.")
            s.nascosta, s.motivo_nascosta, s.moderatore_nascosta = True, motivo, u
            s.save(update_fields=["nascosta", "motivo_nascosta", "moderatore_nascosta"])
            log.registra(u, "revisione_moderatore", "segnalazioni", s.id, {"nascosta": False}, {"nascosta": True, "motivo": motivo})
            messages.success(request, "Segnalazione nascosta.")
        elif azione == "mostra":
            s.nascosta, s.motivo_nascosta, s.moderatore_nascosta = False, None, None
            s.save(update_fields=["nascosta", "motivo_nascosta", "moderatore_nascosta"])
            log.registra(u, "revisione_moderatore", "segnalazioni", s.id, {"nascosta": True}, {"nascosta": False})
            messages.success(request, "Segnalazione di nuovo visibile.")
    except RegolaViolata as e:
        messages.error(request, str(e))
    except DatabaseError as e:
        messages.error(request, str(traduci(e)))
    return redirect(request.POST.get("next") or "moderazione")


@require_POST
@moderatore_richiesto
def azione_segnalazione(request, pk, azione):
    if azione not in ("approva", "rifiuta", "presenta", "nascondi", "mostra"):
        raise Http404()
    return _esegui(request, pk, azione)


@require_POST
@moderatore_richiesto
def azione_commento(request, cid, azione):
    c = get_object_or_404(Commento, pk=cid)
    u = request.user
    if azione == "nascondi":
        motivo = request.POST.get("motivo", "").strip() or "Contenuto non conforme al regolamento"
        c.nascosto, c.motivo_nascosto, c.moderatore_nascosto = True, motivo, u
        messages.success(request, "Commento nascosto.")
    elif azione == "ripristina":
        c.nascosto, c.motivo_nascosto, c.moderatore_nascosto = False, None, None
        c.esito_moderazione = "ok"
        messages.success(request, "Commento ripristinato.")
    else:
        raise Http404()
    c.save(update_fields=["nascosto", "motivo_nascosto", "moderatore_nascosto", "esito_moderazione"])
    log.registra(u, "revisione_moderatore", "commenti", c.id, None, {"nascosto": c.nascosto, "motivo": c.motivo_nascosto})
    return redirect("moderazione")


@require_POST
@moderatore_richiesto
def decidi_verifica(request, vid):
    v = get_object_or_404(VerificaIdentita.objects.select_related("utente"), pk=vid, revisore__isnull=True)
    esito = request.POST.get("esito")
    motivo = request.POST.get("motivo", "").strip()
    if esito not in ("approvata", "rifiutata") or not motivo:
        messages.error(request, "Scegli l'esito e indica il motivo.")
        return redirect("moderazione")
    now = timezone.now()
    with transaction.atomic():
        v.revisore, v.esito_finale, v.motivo_revisione, v.revisionata_il = request.user, esito, motivo, now
        v.save(update_fields=["revisore", "esito_finale", "motivo_revisione", "revisionata_il"])
    if esito == "approvata":
        ricalcola_attivazione(v.utente)  # attivo solo se anche l'email è confermata
    log.registra(request.user, "revisione_moderatore", "verifiche_identita", v.id, {"esito_ia": v.esito_ia}, {"esito_finale": esito, "motivo": motivo})
    notifica(v.utente, "verifica_account", "La verifica del tuo documento è stata rivista: " + ("approvata." if esito == "approvata" else "non superata."), "/profilo/")
    messages.success(request, "Verifica rivista.")
    return redirect("moderazione")


@require_POST
@moderatore_richiesto
def decidi_richiesta(request, rid):
    """Accoglie o respinge una richiesta di revisione (segnalazione bloccata dall'IA o verifica rifiutata)."""
    r = get_object_or_404(RichiestaRevisione.objects.select_related("richiedente", "segnalazione", "verifica__utente"),
                          pk=rid, stato="aperta")
    esito = request.POST.get("esito")
    risposta = request.POST.get("risposta", "").strip()
    if esito not in ("accolta", "respinta") or not risposta:
        messages.error(request, "Scegli l'esito e scrivi la risposta per l'utente.")
        return redirect("moderazione")
    u, now = request.user, timezone.now()
    try:
        with transaction.atomic():
            if r.segnalazione_id:
                s = r.segnalazione
                if esito == "accolta":
                    cambia_stato(s, APPROVATA, u, f"Approvata dopo revisione: {risposta}")
                    notifica_quartiere(s)
                else:
                    cambia_stato(s, RIFIUTATA, u, f"Rifiutata dopo revisione: {risposta}")
                notifica(r.richiedente, "stato_segnalazione", f"Revisione della segnalazione «{s.titolo}»: {risposta}", reverse("dettaglio", args=[s.id]))
            elif r.verifica_id:
                v = r.verifica
                v.revisore, v.esito_finale, v.motivo_revisione, v.revisionata_il = u, "approvata" if esito == "accolta" else "rifiutata", risposta, now
                v.save(update_fields=["revisore", "esito_finale", "motivo_revisione", "revisionata_il"])
                if esito == "accolta":
                    ricalcola_attivazione(v.utente)
                notifica(r.richiedente, "verifica_account", f"Revisione della verifica: {risposta}", "/profilo/")
            r.stato, r.moderatore, r.risposta, r.chiusa_il = esito, u, risposta, now
            r.save(update_fields=["stato", "moderatore", "risposta", "chiusa_il"])
    except RegolaViolata as e:
        messages.error(request, str(e))
    except DatabaseError as e:
        messages.error(request, str(traduci(e)))
    else:
        log.registra(u, "revisione_moderatore", "richieste_revisione", r.id, {"stato": "aperta"}, {"stato": esito, "risposta": risposta})
        messages.success(request, "Richiesta di revisione chiusa.")
    return redirect("moderazione")


@require_POST
@moderatore_richiesto
def azione_utente(request, uid, azione):
    """Il moderatore può sospendere e riattivare gli account (non vede l'elenco completo degli utenti)."""
    u = get_object_or_404(Utente, pk=uid)
    try:
        if azione == "sospendi":
            g = request.POST.get("giorni", "")
            servizio_utenti.sospendi(u, request.user, request.POST.get("motivo", ""), int(g) if g.isdigit() and int(g) > 0 else None)
            messages.success(request, f"Account di {u.nome_pubblico} sospeso.")
        elif azione == "riattiva":
            servizio_utenti.riattiva(u, request.user)
            messages.success(request, f"Account di {u.nome_pubblico} riattivato.")
        else:
            raise Http404()
    except RegolaViolata as e:
        messages.error(request, str(e))
    return redirect(request.POST.get("next") or "moderazione")
