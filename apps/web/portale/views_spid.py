"""Accesso con SPID e CIE.

Il sito non parla direttamente con gli identity provider: lo fa il servizio apps/spid (SDK OpenID Connect con
federazione, verifica di firme e token). Al sito l'identità arriva in un token firmato con un segreto condiviso, a scadenza
(120 s), monouso e legato al browser che ha iniziato l'accesso. Del codice fiscale si salva solo l'impronta SHA-256."""
import hashlib
import re
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.core import signing
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import Utente
from core.services import log
from core.services.errori import traduci

from .forms import SpidCompletaForm
from .views import destinazione_sicura, registra_consensi

SALT = "lnc-ponte-spid"
VALIDITA_AVVIO = 15 * 60


def pagina(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "portale/spid.html", {"attivo": settings.SPID_CIE_ATTIVO})


def avvia(request, metodo):
    if not settings.SPID_CIE_ATTIVO or metodo not in ("spid", "cie"):
        raise Http404()
    request.session["spid_in_corso"] = {"metodo": metodo, "ts": time.time(), "next": request.GET.get("next", "")}
    return redirect(f"{settings.SPID_SERVIZIO_URL.rstrip('/')}/ponte/avvia/?profilo={metodo}")


def _errore(request, testo):
    messages.error(request, testo)
    return redirect("spid")


def _accedi(request, utente, metodo, dest):
    utente.backend = "core.backends.UtenteBackend"
    login(request, utente)
    log.registra(utente, "accesso", "utenti", utente.id, None, {"metodo": metodo})
    return redirect(destinazione_sicura(request, dest))


def ritorno(request):
    if request.GET.get("errore") == "cf":
        return _errore(request, "Il gestore di identità non ha fornito il codice fiscale: non possiamo creare l'account.")
    corso = request.session.pop("spid_in_corso", None)  # monouso: il ritorno vale solo per l'accesso appena iniziato
    if not settings.SPID_CIE_ATTIVO or not corso or time.time() - corso["ts"] > VALIDITA_AVVIO:
        return _errore(request, "La sessione di accesso non è valida o è scaduta: riparti da «Entra con SPID» o «Entra con CIE».")
    try:
        d = signing.loads(request.GET.get("t", ""), key=settings.SPID_BRIDGE_SECRET, salt=SALT, max_age=120)
    except signing.BadSignature:
        return _errore(request, "La risposta del servizio di identità non è valida o è scaduta: riprova.")
    if not cache.add(f"spid-nonce:{d.get('nonce')}", 1, 600) or d.get("metodo") != corso["metodo"]:
        return _errore(request, "La risposta del servizio di identità è già stata usata: riparti dall'inizio.")
    cf = re.sub(r"\s", "", str(d.get("cf", ""))).upper()
    if not re.fullmatch(r"[A-Z0-9]{8,20}", cf):
        return _errore(request, "Il codice fiscale ricevuto non è valido.")
    cf_hash = hashlib.sha256(cf.encode()).hexdigest()  # un account per persona, senza conservare il codice fiscale
    u = Utente.objects.filter(codice_fiscale_hash=cf_hash).first()
    if u:
        if u.stato_account == "eliminato":
            return _errore(request, "Questo account è stato eliminato.")
        return _accedi(request, u, d["metodo"], corso.get("next", ""))
    request.session["spid_nuovo"] = {"metodo": d["metodo"], "cf_hash": cf_hash, "nome": (d.get("nome") or "")[:50], "cognome": (d.get("cognome") or "")[:50],
                                     "email": d.get("email") or "", "nascita": d.get("nascita") or "", "ts": time.time(), "next": corso.get("next", "")}
    return redirect("spid_completa")


def completa(request):
    """Primo accesso: si completa il profilo e si accettano le normative (par. 3.1 e 3.4)."""
    n = request.session.get("spid_nuovo")
    if not n or time.time() - n["ts"] > VALIDITA_AVVIO:
        request.session.pop("spid_nuovo", None)
        return _errore(request, "La sessione di accesso è scaduta: riparti da «Entra con SPID» o «Entra con CIE».")
    nascita = None
    if n["nascita"]:
        try:
            nascita = timezone.datetime.fromisoformat(n["nascita"][:10]).date()
        except ValueError:
            nascita = None
    form = SpidCompletaForm(request.POST or None, nascita_idp=nascita, initial={"email": n["email"]})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            with transaction.atomic():
                u = Utente(nome=n["nome"], cognome=n["cognome"], email=d["email"], data_nascita=d["nascita"], metodo_registrazione=n["metodo"],
                           codice_fiscale_hash=n["cf_hash"], stato_account="attivo", quartiere=d.get("quartiere"),
                           email_verificata_il=timezone.now() if d["email"] == n["email"] else None)
                u.save(force_insert=True)  # l'identità è già certificata: account subito attivo
                registra_consensi(u, ["privacy", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"])
        except DatabaseError as e:
            form.add_error(None, str(traduci(e)))
        else:
            request.session.pop("spid_nuovo", None)
            messages.success(request, f"Benvenuto! Accesso con {n['metodo'].upper()} completato.")
            return _accedi(request, u, n["metodo"], n.get("next", ""))
    return render(request, "portale/spid_completa.html", {"form": form, "n": n, "nascita_idp": nascita})
