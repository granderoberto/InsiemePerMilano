"""Azioni dell'autore sulla propria segnalazione: modifica, eliminazione, richiesta di revisione."""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Categoria, Classificazione, Media, RichiestaRevisione, Segnalazione, VerificaIdentita
from core.services import geo, ia, log, media as servizio_media
from core.services.errori import RegolaViolata, traduci

from .forms import SegnalazioneForm
from .views import attivo_richiesto, notifica


def _file_media(m):
    return Path(settings.MEDIA_ROOT) / m.percorso


@attivo_richiesto
def modifica(request, pk):
    s = get_object_or_404(Segnalazione.objects.select_related("quartiere"), pk=pk, autore=request.user)
    if not s.modificabile:
        messages.error(request, "Puoi modificare una segnalazione solo finché è Ricevuta o In attesa.")
        return redirect("dettaglio", pk=pk)
    esistenti = list(s.media.all())
    iniziale = {"tipo": s.tipo, "titolo": s.titolo, "descrizione": s.descrizione, "latitudine": float(s.latitudine),
                "longitudine": float(s.longitudine), "indirizzo": s.indirizzo,
                "categorie": [c.categoria_id for c in Classificazione.objects.filter(segnalazione=s)]}
    form = SegnalazioneForm(request.POST or None, request.FILES or None, initial=iniziale)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        rimuovi = {int(x) for x in request.POST.getlist("rimuovi_media") if x.isdigit()}
        tenuti = [m for m in esistenti if m.id not in rimuovi]
        files = request.FILES.getlist("media")
        nuovi = []
        try:
            qid = geo.quartiere_da_punto(d["latitudine"], d["longitudine"])
            if qid is None:
                raise RegolaViolata("Il punto scelto è fuori dal Comune di Milano: sposta il segnaposto sulla mappa.")
            if not 1 <= len(tenuti) + len(files) <= 10:
                raise RegolaViolata("La segnalazione deve avere da 1 a 10 file tra foto e video.")
            for f in files:
                nuovi.append(servizio_media.salva(f))
            prima = {"titolo": s.titolo, "descrizione": s.descrizione, "tipo": s.tipo, "indirizzo": s.indirizzo,
                     "latitudine": str(s.latitudine), "longitudine": str(s.longitudine), "id_quartiere": s.quartiere_id,
                     "categorie": iniziale["categorie"], "n_media": len(esistenti)}
            esito, p_mod = ia.controlla_testo(f"{d['titolo']} {d['descrizione']}")
            p_coer = ia.coerenza_immagine_testo(d["titolo"], d["descrizione"], len(tenuti) + len(nuovi))
            suggerite = dict(ia.suggerisci_categorie(d["titolo"], d["descrizione"]))
            with transaction.atomic():
                s.tipo, s.titolo, s.descrizione, s.indirizzo = d["tipo"], d["titolo"], d["descrizione"], d.get("indirizzo") or None
                s.latitudine = Decimal(str(d["latitudine"])).quantize(Decimal("0.000001"))
                s.longitudine = Decimal(str(d["longitudine"])).quantize(Decimal("0.000001"))
                s.quartiere_id, s.esito_moderazione = qid, esito
                s.punteggio_moderazione, s.punteggio_coerenza = Decimal(str(p_mod)), Decimal(str(p_coer))
                s.aggiornata_il = timezone.now()
                s.save(update_fields=["tipo", "titolo", "descrizione", "indirizzo", "latitudine", "longitudine", "quartiere",
                                      "esito_moderazione", "punteggio_moderazione", "punteggio_coerenza", "aggiornata_il"])
                Classificazione.objects.filter(segnalazione=s).delete()
                for cat in d["categorie"]:
                    conf = suggerite.get(cat.nome)
                    Classificazione.objects.create(segnalazione=s, categoria=cat, origine="ia" if conf else "utente",
                                                   confidenza=Decimal(str(conf)) if conf else None)
                # i media si ricreano nell'ordine nuovo: (id_segnalazione, ordine) è UNIQUE e la copertina è una sola
                Media.objects.filter(segnalazione=s).delete()
                ordine = 0
                for m in tenuti:
                    ordine += 1
                    Media.objects.create(segnalazione=s, tipo=m.tipo, percorso=m.percorso, mime_type=m.mime_type,
                                         dimensione_byte=m.dimensione_byte, durata_sec=m.durata_sec, ordine=ordine,
                                         copertina=(ordine == 1), exif_lat=m.exif_lat, exif_lon=m.exif_lon,
                                         esito_visione=m.esito_visione, punteggio_sessuale=m.punteggio_sessuale,
                                         punteggio_violenza=m.punteggio_violenza)
                for m in nuovi:
                    ordine += 1
                    Media.objects.create(segnalazione=s, tipo=m["tipo"], percorso=m["percorso"], mime_type=m["mime"],
                                         dimensione_byte=m["dimensione"], durata_sec=m["durata"], ordine=ordine,
                                         copertina=(ordine == 1), esito_visione="ok", punteggio_sessuale=Decimal("0.020"),
                                         punteggio_violenza=Decimal("0.020"))
            for m in esistenti:
                if m.id in rimuovi:
                    _file_media(m).unlink(missing_ok=True)
            dopo = {"titolo": s.titolo, "descrizione": s.descrizione, "tipo": s.tipo, "indirizzo": s.indirizzo,
                    "latitudine": str(s.latitudine), "longitudine": str(s.longitudine), "id_quartiere": qid,
                    "categorie": [c.id for c in d["categorie"]], "n_media": len(tenuti) + len(nuovi)}
            log.registra(request.user, "modifica", "segnalazioni", s.id, prima, dopo)  # versione precedente nel registro
            log.registra(None, "decisione_ia", "segnalazioni", s.id, None,
                         {"esito_moderazione": esito, "punteggio_moderazione": p_mod, "punteggio_coerenza": p_coer})
            if esito == "bloccato":
                notifica(request.user, "contenuto_bloccato",
                         f"La tua segnalazione «{s.titolo}» è stata bloccata dai controlli automatici: un moderatore la riesaminerà.",
                         reverse("dettaglio", args=[s.id]))
        except (RegolaViolata, servizio_media.MediaNonValido) as e:
            for m in nuovi:
                (Path(settings.MEDIA_ROOT) / m["percorso"]).unlink(missing_ok=True)
            form.add_error(None, str(e))
        except DatabaseError as e:
            for m in nuovi:
                (Path(settings.MEDIA_ROOT) / m["percorso"]).unlink(missing_ok=True)
            form.add_error(None, str(traduci(e)))
        else:
            messages.success(request, "Segnalazione aggiornata. Ha ripassato i controlli automatici.")
            return redirect("dettaglio", pk=s.id)
    return render(request, "portale/nuova.html", {"form": form, "categorie": list(Categoria.objects.filter(attiva=True)),
                                                  "modifica": True, "s": s, "media_esistenti": esistenti})


@require_POST
@attivo_richiesto
def elimina(request, pk):
    s = get_object_or_404(Segnalazione, pk=pk, autore=request.user)
    if not s.modificabile:
        messages.error(request, "Puoi eliminare una segnalazione solo finché è Ricevuta o In attesa.")
        return redirect("dettaglio", pk=pk)
    s.eliminata_il = timezone.now()
    s.save(update_fields=["eliminata_il"])  # eliminazione logica: resta traccia nel database
    log.registra(request.user, "eliminazione", "segnalazioni", s.id, {"eliminata_il": None}, {"eliminata_il": s.eliminata_il})
    messages.info(request, "Segnalazione eliminata.")
    return redirect("profilo")


@require_POST
@attivo_richiesto
def richiedi_revisione_segnalazione(request, pk):
    s = get_object_or_404(Segnalazione, pk=pk, autore=request.user)
    motivo = request.POST.get("motivo", "").strip()
    if s.esito_moderazione != "bloccato" or not s.modificabile:
        messages.error(request, "Si può chiedere la revisione solo di una segnalazione bloccata dai controlli automatici.")
    elif not motivo:
        messages.error(request, "Spiega perché chiedi la revisione.")
    elif RichiestaRevisione.objects.filter(segnalazione=s, stato="aperta").exists():
        messages.info(request, "Hai già una richiesta di revisione aperta per questa segnalazione.")
    else:
        r = RichiestaRevisione.objects.create(richiedente=request.user, segnalazione=s, motivo=motivo)
        log.registra(request.user, "creazione", "richieste_revisione", r.id, None, {"tipo": "segnalazione", "id_segnalazione": s.id})
        messages.success(request, "Richiesta inviata: un moderatore la esaminerà.")
    return redirect("dettaglio", pk=pk)


@require_POST
def richiedi_revisione_verifica(request, vid):
    """Dopo un rifiuto l'utente può sempre chiedere la revisione di una persona (anche se l'account è in attesa)."""
    if not request.user.is_authenticated:
        return redirect("accedi")
    v = get_object_or_404(VerificaIdentita, pk=vid, utente=request.user)
    motivo = request.POST.get("motivo", "").strip()
    if v.esito_ia != "rifiutata" or v.revisore_id is not None:
        messages.error(request, "Questa verifica non può essere rivista.")
    elif not motivo:
        messages.error(request, "Spiega perché chiedi la revisione.")
    elif RichiestaRevisione.objects.filter(verifica=v, stato="aperta").exists():
        messages.info(request, "Hai già una richiesta aperta per questa verifica.")
    else:
        r = RichiestaRevisione.objects.create(richiedente=request.user, verifica=v, motivo=motivo)
        log.registra(request.user, "creazione", "richieste_revisione", r.id, None, {"tipo": "verifica", "id_verifica": v.id})
        messages.success(request, "Richiesta inviata: un moderatore la esaminerà.")
    return redirect("profilo")
