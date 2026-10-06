import hashlib
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import (APPROVATA, PRESENTATA, Candidato, Categoria, Classificazione, Commento, Consenso,
                         DocumentoNormativo, Media, Notifica, PreferenzaNotifica, Quartiere, RichiestaRevisione, Segnalazione, Sostegno, Stato,
                         Utente, VerificaIdentita)
from core.queries import con_conteggi
from core.services import geo, ia_simulata, log, media as servizio_media, normative, simili
from core.services.errori import RegolaViolata, traduci
from core.services.stati import cambia_stato

from . import verifica as verifica_identita
from .forms import RegistrazioneForm, SegnalazioneForm, nuova_sfida

PER_PAGINA = 12


# ------------------------------------------------------------------ utilità
def attivo_richiesto(vista):
    """Solo account attivi possono interagire (gli altri consultano soltanto)."""
    @login_required
    def _v(request, *a, **kw):
        if not request.user.puo_interagire:
            messages.warning(request, "Il tuo account non può ancora interagire: è in attesa di verifica o sospeso.")
            return redirect(request.META.get("HTTP_REFERER") or "home")
        if normative.da_accettare(request.user):  # nuova versione di un documento: serve una nuova accettazione
            messages.warning(request, "Prima di continuare devi accettare la nuova versione dei documenti normativi.")
            return redirect("accetta_normative")
        return vista(request, *a, **kw)
    _v.__name__ = vista.__name__
    return _v


def destinazione_sicura(request, dest):
    """Il parametro `next` si accetta solo se resta su questo sito: «//sito-esterno.it» o «https://altro.it» non valgono."""
    if dest and url_has_allowed_host_and_scheme(dest, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return dest
    return "/"


def notifica(utente, tipo, messaggio, link=None):
    """Crea una notifica nell'app (e, se l'utente l'ha chiesto, un'email) rispettando le sue preferenze.
    Quelle su account e normative sono obbligatorie."""
    from .views_account import OBBLIGATORIE
    pref = None if tipo in OBBLIGATORIE else PreferenzaNotifica.objects.filter(utente=utente, tipo=tipo).first()
    if pref is None or pref.in_app:
        Notifica.objects.create(utente=utente, tipo=tipo, messaggio=messaggio[:500], link=link)
    if pref is not None and pref.email:
        send_mail("Novità su La Nostra Città", messaggio, settings.DEFAULT_FROM_EMAIL, [utente.email], fail_silently=True)


def notifica_quartiere(s):
    """Quando una segnalazione diventa pubblica, avvisa chi abita nel suo quartiere."""
    for u in Utente.objects.filter(quartiere_id=s.quartiere_id, stato_account="attivo").exclude(pk=s.autore_id):
        notifica(u, "nuova_segnalazione_quartiere", f"Nuova segnalazione nel tuo quartiere: «{s.titolo}».", reverse("dettaglio", args=[s.id]))


def pubbliche():
    """Segnalazioni visibili a tutti: stato pubblico, non nascoste né eliminate."""
    return con_conteggi(Segnalazione.objects.filter(stato__pubblico=True, nascosta=False, eliminata_il__isnull=True)
                        .select_related("quartiere", "stato", "autore"))


def applica_filtri(qs, g):
    if g.get("q", "").strip():
        t = g["q"].strip()
        qs = qs.filter(Q(titolo__icontains=t) | Q(descrizione__icontains=t))
    if g.get("quartiere", "").isdigit():
        qs = qs.filter(quartiere_id=int(g["quartiere"]))
    if g.get("categoria", "").isdigit():
        qs = qs.filter(classificazioni__categoria_id=int(g["categoria"]))
    if g.get("stato") in ("3", "5"):
        qs = qs.filter(stato_id=int(g["stato"]))
    if g.get("tipo") in ("proposta", "problema"):
        qs = qs.filter(tipo=g["tipo"])
    return qs.order_by("-n_sostegni", "-creata_il") if g.get("ordine") == "sostegni" else qs.order_by("-creata_il")


def con_dettagli(qs):
    return qs.prefetch_related(
        Prefetch("media", queryset=Media.objects.filter(copertina=True), to_attr="copertina_lista"),
        Prefetch("classificazioni", queryset=Classificazione.objects.select_related("categoria"), to_attr="cat_lista"))


# ------------------------------------------------------------------ pubblico
def home(request):
    g = request.GET
    qs = con_dettagli(applica_filtri(pubbliche(), g))
    pagina = Paginator(qs, PER_PAGINA).get_page(g.get("pagina"))
    parametri = g.copy()
    parametri.pop("pagina", None)
    parametri.pop("vista", None)
    return render(request, "portale/home.html", {
        "pagina": pagina, "filtri": g, "vista": "mappa" if g.get("vista") == "mappa" else "elenco",
        "quartieri": Quartiere.objects.all(), "categorie": Categoria.objects.filter(attiva=True),
        "querystring": parametri.urlencode(),
        "totale": pagina.paginator.count,
    })


def geojson(request):
    qs = applica_filtri(pubbliche(), request.GET)[:600]
    feats = [{"type": "Feature", "id": s.id,
              "geometry": {"type": "Point", "coordinates": [float(s.longitudine), float(s.latitudine)]},
              "properties": {"titolo": s.titolo, "stato": s.stato.nome, "sostegni": s.n_sostegni, "tipo": s.tipo,
                             "quartiere": s.quartiere.nome_leggibile, "url": reverse("dettaglio", args=[s.id])}} for s in qs]
    return JsonResponse({"type": "FeatureCollection", "features": feats})


def puo_vedere(user, s):
    if s.e_pubblica:
        return True
    if not user.is_authenticated:
        return False
    return user.e_moderatore or (s.autore_id == user.id and s.eliminata_il is None)


def albero_commenti(seg):
    visibili = list(seg.commenti.select_related("autore").filter(nascosto=False, eliminato_il__isnull=True))
    figli = {}
    for c in visibili:
        figli.setdefault(c.padre_id, []).append(c)
    ids = {c.id for c in visibili}
    ordine = []

    def visita(padre_id, livello):
        for c in figli.get(padre_id, []):
            c.livello = min(livello, 4)
            ordine.append(c)
            visita(c.id, livello + 1)

    # i commenti con padre nascosto/eliminato restano visibili come radice
    for c in visibili:
        if c.padre_id is not None and c.padre_id not in ids:
            figli.setdefault(None, []).append(c)
    visita(None, 0)
    return ordine


def dettaglio(request, pk):
    s = get_object_or_404(Segnalazione.objects.select_related("quartiere", "stato", "autore"), pk=pk)
    if not puo_vedere(request.user, s):
        raise Http404()
    u = request.user
    return render(request, "portale/dettaglio.html", {
        "s": s, "media": list(s.media.all()),
        "categorie": Classificazione.objects.filter(segnalazione=s).select_related("categoria"),
        "cronologia": s.cambi_stato.select_related("stato_a", "operatore"),
        "commenti": albero_commenti(s),
        "n_sostegni": s.sostegni.count(),
        "ha_sostenuto": u.is_authenticated and Sostegno.objects.filter(utente=u, segnalazione=s).exists(),
        "candidati": [i.candidato for i in s.invii.select_related("candidato")] if s.stato_id == PRESENTATA else [],
        "url_assoluto": request.build_absolute_uri(),
        "richiesta_aperta": u.is_authenticated and RichiestaRevisione.objects.filter(segnalazione=s, stato="aperta").exists(),
    })


def imposta_sostegno(utente, s):
    """Aggiunge o ritira il sostegno. -> (sostenuta: bool, numero di sostegni). Solleva RegolaViolata se un trigger lo vieta."""
    esistente = Sostegno.objects.filter(utente=utente, segnalazione=s)
    if esistente.exists():
        esistente.delete()
        sostenuta = False
    else:
        try:
            with transaction.atomic():
                Sostegno.objects.create(utente=utente, segnalazione=s)
        except DatabaseError as e:
            raise traduci(e) from e
        log.registra(utente, "sostegno", "sostegni", s.id, None, {"id_utente": utente.id, "id_segnalazione": s.id})
        sostenuta = True
    return sostenuta, s.sostegni.count()


@require_POST
@attivo_richiesto
def sostieni_json(request, pk):
    """Come `sostieni`, ma per la pagina «Nuova segnalazione»: risponde in JSON, senza spostare l'utente."""
    s = get_object_or_404(Segnalazione, pk=pk)
    try:
        sostenuta, n = imposta_sostegno(request.user, s)
    except RegolaViolata as e:
        return JsonResponse({"errore": str(e)}, status=400)
    return JsonResponse({"sostenuta": sostenuta, "sostegni": n})


def segnalazioni_simili(request):
    try:
        lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
    except (KeyError, ValueError):
        return JsonResponse({"simili": []})
    cat = [c for c in request.GET.get("categorie", "").split(",") if c.isdigit()]
    escludi = int(request.GET["escludi"]) if request.GET.get("escludi", "").isdigit() else None
    elenco = simili.trova_simili(lat, lon, request.GET.get("titolo", ""), request.GET.get("descrizione", ""), cat, escludi)
    u = request.user
    sostenute = set(Sostegno.objects.filter(utente=u, segnalazione_id__in=[x["id"] for x in elenco]).values_list("segnalazione_id", flat=True)) if u.is_authenticated and elenco else set()
    for x in elenco:
        x["propria"] = u.is_authenticated and x.pop("autore_id") == u.id
        x["sostenuta"] = x["id"] in sostenute
    return JsonResponse({"simili": elenco, "puo_sostenere": u.is_authenticated and u.puo_interagire})


@require_POST
@attivo_richiesto
def sostieni(request, pk):
    s = get_object_or_404(Segnalazione, pk=pk)
    try:
        sostenuta, _ = imposta_sostegno(request.user, s)
        messages.success(request, "Grazie, hai sostenuto questa segnalazione.") if sostenuta else messages.info(request, "Hai ritirato il tuo sostegno.")
    except RegolaViolata as e:
        messages.error(request, str(e))
    return redirect("dettaglio", pk=pk)


@require_POST
@attivo_richiesto
def commenta(request, pk):
    s = get_object_or_404(Segnalazione, pk=pk)
    testo = request.POST.get("testo", "").strip()
    if not testo or len(testo) > 1000:
        messages.error(request, "Il commento deve contenere da 1 a 1000 caratteri.")
        return redirect("dettaglio", pk=pk)
    padre = None
    if request.POST.get("padre", "").isdigit():
        padre = Commento.objects.filter(pk=int(request.POST["padre"]), segnalazione=s).first()
    esito, punteggio = ia_simulata.controlla_testo(testo)
    if esito == "bloccato":
        messages.error(request, "Il commento è stato bloccato dai controlli automatici perché contiene una minaccia. "
                                "Riscrivilo in modo rispettoso.")
        return redirect("dettaglio", pk=pk)
    try:
        with transaction.atomic():
            c = Commento.objects.create(segnalazione=s, autore=request.user, padre=padre, testo=testo,
                                        esito_moderazione=esito, punteggio_moderazione=Decimal(str(punteggio)))
    except DatabaseError as e:
        messages.error(request, str(traduci(e)))
        return redirect("dettaglio", pk=pk)
    log.registra(request.user, "commento", "commenti", c.id, None, {"id_segnalazione": s.id, "id_padre": padre.id if padre else None})
    log.registra(None, "decisione_ia", "commenti", c.id, None, {"esito_moderazione": esito, "punteggio_moderazione": punteggio})
    if padre and padre.autore_id != request.user.id:
        notifica(padre.autore, "risposta_commento", f"{request.user.nome} ha risposto al tuo commento.", reverse("dettaglio", args=[pk]))
    elif s.autore_id != request.user.id:
        notifica(s.autore, "nuovo_commento", f"{request.user.nome} ha commentato «{s.titolo}».", reverse("dettaglio", args=[pk]))
    if esito == "dubbio":
        messages.warning(request, "Il commento è stato pubblicato ma un moderatore lo controllerà.")
    else:
        messages.success(request, "Commento pubblicato.")
    return redirect(reverse("dettaglio", args=[pk]) + f"#commento-{c.id}")


@require_POST
@attivo_richiesto
def elimina_commento(request, pk, cid):
    c = get_object_or_404(Commento, pk=cid, segnalazione_id=pk, autore=request.user)
    c.eliminato_il = timezone.now()
    c.save(update_fields=["eliminato_il"])
    log.registra(request.user, "eliminazione", "commenti", c.id, {"eliminato_il": None}, {"eliminato_il": c.eliminato_il})
    messages.info(request, "Commento eliminato.")
    return redirect("dettaglio", pk=pk)


# ------------------------------------------------------------------ nuova segnalazione
@attivo_richiesto
def nuova(request):
    form = SegnalazioneForm(request.POST or None, request.FILES or None)
    categorie = list(Categoria.objects.filter(attiva=True))
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        oggi = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        if Segnalazione.objects.filter(autore=request.user, creata_il__gte=oggi).count() >= 5:
            form.add_error(None, "Hai raggiunto il limite di 5 segnalazioni al giorno. Riprova domani.")
        else:
            qid = geo.quartiere_da_punto(d["latitudine"], d["longitudine"])
            files = request.FILES.getlist("media")
            salvati = []
            try:
                if qid is None:
                    raise RegolaViolata("Il punto scelto è fuori dal Comune di Milano: sposta il segnaposto sulla mappa.")
                if not 1 <= len(files) <= 10:
                    raise RegolaViolata("Allega da 1 a 10 file tra foto e video.")
                for f in files:
                    salvati.append(servizio_media.salva(f))
                s = crea_segnalazione(request.user, d, qid, salvati, d["categorie"])
            except (RegolaViolata, servizio_media.MediaNonValido) as e:
                for m in salvati:
                    (Path(settings.MEDIA_ROOT) / m["percorso"]).unlink(missing_ok=True)
                form.add_error(None, str(e))
            except DatabaseError as e:
                for m in salvati:
                    (Path(settings.MEDIA_ROOT) / m["percorso"]).unlink(missing_ok=True)
                form.add_error(None, str(traduci(e)))
            else:
                messages.success(request, "Segnalazione inviata: ora è in attesa della valutazione di un moderatore.")
                return redirect("dettaglio", pk=s.id)
    return render(request, "portale/nuova.html", {"form": form, "categorie": categorie})


def crea_segnalazione(utente, d, qid, file_salvati, categorie_scelte):
    esito, p_mod = ia_simulata.controlla_testo(f"{d['titolo']} {d['descrizione']}")
    p_coer = ia_simulata.coerenza_immagine_testo(d["titolo"], d["descrizione"], len(file_salvati))
    suggerite = dict(ia_simulata.suggerisci_categorie(d["titolo"], d["descrizione"]))
    with transaction.atomic():
        s = Segnalazione.objects.create(
            autore=utente, tipo=d["tipo"], titolo=d["titolo"], descrizione=d["descrizione"],
            latitudine=Decimal(str(d["latitudine"])).quantize(Decimal("0.000001")),
            longitudine=Decimal(str(d["longitudine"])).quantize(Decimal("0.000001")),
            indirizzo=d.get("indirizzo") or None, quartiere_id=qid,
            esito_moderazione=esito, punteggio_moderazione=Decimal(str(p_mod)), punteggio_coerenza=Decimal(str(p_coer)))
        for i, m in enumerate(file_salvati, 1):  # almeno un media: stessa transazione della segnalazione
            Media.objects.create(segnalazione=s, tipo=m["tipo"], percorso=m["percorso"], mime_type=m["mime"],
                                 dimensione_byte=m["dimensione"], durata_sec=m["durata"], ordine=i, copertina=(i == 1),
                                 esito_visione="ok", punteggio_sessuale=Decimal("0.020"), punteggio_violenza=Decimal("0.020"))
        for cat in categorie_scelte:
            conf = suggerite.get(cat.nome)
            Classificazione.objects.create(segnalazione=s, categoria=cat, origine="ia" if conf else "utente",
                                           confidenza=Decimal(str(conf)) if conf else None)
    log.registra(utente, "creazione", "segnalazioni", s.id, None, {"titolo": s.titolo, "tipo": s.tipo, "id_quartiere": qid})
    log.registra(None, "decisione_ia", "segnalazioni", s.id, None,
                 {"esito_moderazione": esito, "punteggio_moderazione": p_mod, "punteggio_coerenza": p_coer})
    cambia_stato(s, 2, None, "Controlli automatici completati")
    if esito == "bloccato":
        notifica(utente, "contenuto_bloccato",
                 f"La tua segnalazione «{s.titolo}» è stata bloccata dai controlli automatici: un moderatore la riesaminerà.",
                 reverse("dettaglio", args=[s.id]))
    return s


def suggerisci_categorie(request):
    sug = ia_simulata.suggerisci_categorie(request.GET.get("titolo", ""), request.GET.get("descrizione", ""))
    ids = {c.nome: c.id for c in Categoria.objects.all()}
    return JsonResponse({"categorie": [{"id": ids[n], "nome": n, "confidenza": c} for n, c in sug if n in ids]})


def quartiere_da_posizione(request):
    try:
        qid = geo.quartiere_da_punto(float(request.GET["lat"]), float(request.GET["lon"]))
    except (KeyError, ValueError):
        return JsonResponse({"errore": "coordinate non valide"}, status=400)
    q = Quartiere.objects.filter(pk=qid).first() if qid else None
    return JsonResponse({"dentro_milano": q is not None, "quartiere": q.nome_leggibile if q else None})


# ------------------------------------------------------------------ accesso
def accedi(request):
    if request.user.is_authenticated:
        return redirect("home")
    errore = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        pw = request.POST.get("password", "")
        u = Utente.objects.filter(email=email).first()
        if u and u.bloccato_fino and u.bloccato_fino > timezone.now():
            errore = "Troppi tentativi falliti: l'account è bloccato per 15 minuti."
        else:
            user = authenticate(request, email=email, password=pw)
            if user is None or user.stato_account == "eliminato":
                errore = "Email o password non corretti."
                if u:
                    u.tentativi_falliti += 1
                    if u.tentativi_falliti >= 5:
                        u.bloccato_fino, u.tentativi_falliti = timezone.now() + timedelta(minutes=15), 0
                    u.save(update_fields=["tentativi_falliti", "bloccato_fino"])
            else:
                user.tentativi_falliti, user.bloccato_fino = 0, None
                user.save(update_fields=["tentativi_falliti", "bloccato_fino"])
                dest = destinazione_sicura(request, request.POST.get("next") or request.GET.get("next"))
                if user.mfa_attiva:  # password giusta ma non ancora autenticato: manca il codice dell'app
                    request.session.flush()
                    request.session["mfa_utente"] = user.id
                    request.session["mfa_scade"] = (timezone.now() + timedelta(minutes=5)).timestamp()
                    request.session["mfa_next"] = dest
                    return redirect("accedi_2fa")
                login(request, user)
                log.registra(user, "accesso", "utenti", user.id, None, {"metodo": "credenziali"})
                return redirect(dest)
    return render(request, "portale/accedi.html", {"errore": errore, "next": request.GET.get("next", "")})


def esci(request):
    if request.method == "POST":
        logout(request)
    return redirect("home")


def _documenti():
    return {d.tipo: d for d in DocumentoNormativo.objects.all()}


def registra_consensi(utente, tipi, log_extra=()):
    """Salva i consensi e le relative righe di registro con due soli inserimenti. log_extra: altre voci di registro."""
    per_tipo = _documenti()  # una sola lettura
    docs = [per_tipo[t] for t in tipi if t in per_tipo]
    Consenso.objects.bulk_create([Consenso(utente=utente, documento=d) for d in docs])
    log.registra_molti([(utente, "accettazione_normativa", "documenti_normativi", d.id, None, {"versione": d.versione}) for d in docs]
                       + list(log_extra))


def registrati(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrazioneForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            with transaction.atomic():
                u = Utente(nome=d["nome"], cognome=d["cognome"], email=d["email"], data_nascita=d["data_nascita"],
                           metodo_registrazione="credenziali", quartiere=d.get("quartiere"),
                           stato_account="in_attesa_verifica")
                u.set_password(d["password"])
                u.save(force_insert=True)
                registra_consensi(u, ["privacy", "biometrici", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"])
                # verifica del documento (controlli IA simulati): file in area temporanea cifrata, cancellati a fine verifica
                verifica = verifica_identita.esegui(u, 1, d["tipo_documento"], d["_fronte"], d.get("_retro"), d["_selfie"])
        except DatabaseError as e:
            form.add_error(None, str(traduci(e)))
        else:
            from .views_account import invia_conferma
            esito_posta = invia_conferma(request, u)
            login(request, u)
            if esito_posta:
                messages.success(request, "Registrazione completata. Ti abbiamo inviato un'email: conferma l'indirizzo per attivare l'account (controlla anche lo spam).")
            else:
                messages.warning(request, "Registrazione completata, ma non siamo riusciti a spedire l'email di conferma: usa «Invia di nuovo il link» qui sotto.")
            if verifica.esito_ia == "da_rivedere":
                messages.info(request, "La verifica del documento è in revisione: un moderatore la controllerà.")
            elif verifica.esito_ia == "rifiutata":
                messages.error(request, f"La verifica del documento non è stata superata ({verifica.motivo}). Puoi riprovare dal profilo (3 tentativi in totale).")
            return redirect("profilo")
    return render(request, "portale/registrati.html", {"form": form, "sfida": nuova_sfida()})


# ------------------------------------------------------------------ profilo, notifiche
@login_required
def profilo(request):
    u = request.user
    if request.method == "POST":
        u.profilo_pubblico = request.POST.get("profilo_pubblico") == "on"
        qid = request.POST.get("quartiere", "")
        u.quartiere = Quartiere.objects.filter(pk=int(qid)).first() if qid.isdigit() else None
        u.save(update_fields=["profilo_pubblico", "quartiere"])
        messages.success(request, "Profilo aggiornato.")
        return redirect("profilo")
    mie = con_dettagli(con_conteggi(Segnalazione.objects.filter(autore=u, eliminata_il__isnull=True).select_related("stato", "quartiere")))
    ultima = u.verifiche.order_by("-creata_il").first()
    rifiutata = ultima if ultima and ultima.esito_ia == "rifiutata" and ultima.revisore_id is None else None
    return render(request, "portale/profilo.html", {
        "verifica_rifiutata": rifiutata,
        "tentativi_usati": u.verifiche.count(),
        "richiesta_verifica_aperta": bool(rifiutata) and RichiestaRevisione.objects.filter(verifica=rifiutata, stato="aperta").exists(),
        "mie": mie, "quartieri": Quartiere.objects.all(),
        "n_segnalazioni": mie.count(), "n_commenti": u.commenti.filter(eliminato_il__isnull=True).count(),
        "n_sostegni_dati": u.sostegni.count(),
        "n_sostegni_ricevuti": Sostegno.objects.filter(segnalazione__autore=u).count(),
    })


@login_required
def notifiche(request):
    elenco = list(request.user.notifiche.all()[:60])
    if request.method == "POST":
        request.user.notifiche.filter(letta=False).update(letta=True)
        return redirect("notifiche")
    return render(request, "portale/notifiche.html", {"notifiche": elenco})


# ------------------------------------------------------------------ statistiche
def statistiche(request):
    g = request.GET
    pubbl = pubbliche()
    if g.get("periodo") == "30":
        pubbl = pubbl.filter(creata_il__gte=timezone.now() - timedelta(days=30))
    classifica = con_dettagli(applica_filtri(pubbl, {**g.dict(), "ordine": "sostegni"}))[:10]
    per_stato = list(Stato.objects.annotate(n=Count("segnalazioni", filter=Q(segnalazioni__eliminata_il__isnull=True))).order_by("id"))
    per_quartiere = list(Quartiere.objects.annotate(n=Count("segnalazioni", filter=Q(segnalazioni__stato__pubblico=True,
                         segnalazioni__nascosta=False, segnalazioni__eliminata_il__isnull=True))).filter(n__gt=0).order_by("-n")[:10])
    per_categoria = list(Categoria.objects.annotate(n=Count("classificazioni__segnalazione", filter=Q(classificazioni__segnalazione__stato__pubblico=True,
                         classificazioni__segnalazione__nascosta=False))).order_by("-n"))
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute("SELECT nome, cognome, n_segnalazioni, n_commenti_scritti, n_sostegni_ricevuti, attivita_30_giorni "
                    "FROM v_classifica_utenti_pubblica ORDER BY n_segnalazioni DESC, n_sostegni_ricevuti DESC LIMIT 10")
        utenti = [dict(zip(("nome", "cognome", "n_segnalazioni", "n_commenti", "n_sostegni_ricevuti", "attivita"), r)) for r in cur.fetchall()]
    massimo = lambda lst: max([x.n for x in lst] or [1]) or 1
    return render(request, "portale/statistiche.html", {
        "classifica": classifica, "filtri": g, "quartieri": Quartiere.objects.all(), "categorie": Categoria.objects.filter(attiva=True),
        "per_stato": per_stato, "max_stato": massimo(per_stato),
        "per_quartiere": per_quartiere, "max_quartiere": massimo(per_quartiere),
        "per_categoria": per_categoria, "max_categoria": massimo(per_categoria), "utenti": utenti,
    })


# ------------------------------------------------------------------ file multimediali
def media_file(request, path):
    radice = (Path(settings.MEDIA_ROOT) / "media").resolve()
    f = (radice / path).resolve()
    if f.is_file() and radice in f.parents:
        return FileResponse(open(f, "rb"))
    # i dati demo hanno percorsi fittizi: restituisco un segnaposto
    tinta = int(hashlib.md5(path.encode()).hexdigest()[:6], 16) % 360
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400" role="img" aria-label="Immagine di esempio">'
           f'<rect width="640" height="400" fill="hsl({tinta} 35% 82%)"/><circle cx="320" cy="170" r="54" fill="hsl({tinta} 30% 62%)"/>'
           f'<path d="M0 400 L180 250 L300 330 L430 220 L640 400Z" fill="hsl({tinta} 32% 70%)"/>'
           f'<text x="320" y="360" text-anchor="middle" font-family="sans-serif" font-size="22" fill="hsl({tinta} 30% 28%)">Foto di esempio (dati demo)</text></svg>')
    return HttpResponse(svg, content_type="image/svg+xml")


# ------------------------------------------------------------------ normative
def pagina_normative(request):
    return render(request, "portale/normative.html", {"documenti": normative.ultime_versioni().values()})


@login_required
def accetta_normative(request):
    mancanti = normative.da_accettare(request.user)
    if request.method == "POST":
        spuntati = {int(x) for x in request.POST.getlist("documento") if x.isdigit()}
        if {d.id for d in mancanti} - spuntati:
            messages.error(request, "Per continuare devi accettare tutti i documenti elencati.")
        else:
            for d in mancanti:
                Consenso.objects.create(utente=request.user, documento=d)
                log.registra(request.user, "accettazione_normativa", "documenti_normativi", d.id, None, {"versione": d.versione})
            request.user.notifiche.filter(tipo="normativa_aggiornata").update(letta=True)
            messages.success(request, "Grazie, hai accettato le nuove versioni.")
            return redirect("home")
    return render(request, "portale/accetta_normative.html", {"mancanti": mancanti})
