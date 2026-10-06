"""Autenticazione a due fattori (TOTP): attivazione, disattivazione, secondo passo all'accesso."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Utente
from core.services import log, mfa


def _solo_credenziali(request):
    if request.user.metodo_registrazione != "credenziali":
        messages.info(request, "Con SPID o CIE la sicurezza dell'accesso è già gestita dal tuo gestore di identità.")
        return False
    return True


@login_required
def attiva(request):
    u = request.user
    if not _solo_credenziali(request):
        return redirect("profilo")
    if u.mfa_attiva:
        messages.info(request, "L'autenticazione a due fattori è già attiva.")
        return redirect("profilo")
    segreto = request.session.get("mfa_pendente")
    if not segreto:  # il segreto in attesa di conferma sta solo nella sessione, non nel database
        segreto = request.session["mfa_pendente"] = mfa.nuovo_segreto()
    if request.method == "POST":
        if mfa.codice_valido(segreto, request.POST.get("codice", "")):
            u.mfa_segreto, u.mfa_attiva = mfa.cifra(segreto), True
            u.save(update_fields=["mfa_segreto", "mfa_attiva"])
            request.session.pop("mfa_pendente", None)
            log.registra(u, "modifica", "utenti", u.id, {"mfa_attiva": False}, {"mfa_attiva": True})
            messages.success(request, "Autenticazione a due fattori attivata: da ora all'accesso ti chiederemo anche il codice dell'app.")
            return redirect("profilo")
        messages.error(request, "Il codice non è corretto. Controlla l'ora del telefono e riprova.")
    uri = mfa.uri_provisioning(u, segreto)
    return render(request, "portale/mfa_attiva.html", {"qr": mfa.qr_svg(uri), "segreto": segreto})


@require_POST
@login_required
def disattiva(request):
    u = request.user
    if not u.mfa_attiva:
        return redirect("profilo")
    if u.check_password(request.POST.get("password", "")) and mfa.verifica_utente(u, request.POST.get("codice", "")):
        u.mfa_attiva, u.mfa_segreto = False, None
        u.save(update_fields=["mfa_attiva", "mfa_segreto"])
        log.registra(u, "modifica", "utenti", u.id, {"mfa_attiva": True}, {"mfa_attiva": False})
        messages.success(request, "Autenticazione a due fattori disattivata.")
    else:
        messages.error(request, "Per disattivarla servono la password e un codice corretto.")
    return redirect("profilo")


def secondo_passo(request):
    """Dopo la password giusta: serve anche il codice dell'app. L'utente è autenticato solo dopo questo passaggio."""
    uid, scade = request.session.get("mfa_utente"), request.session.get("mfa_scade", 0)
    u = Utente.objects.filter(pk=uid).first() if uid else None
    if u is None or timezone.now().timestamp() > scade or not u.mfa_attiva:
        request.session.pop("mfa_utente", None)
        messages.error(request, "Sessione di accesso scaduta: inserisci di nuovo email e password.")
        return redirect("accedi")
    errore = None
    if u.bloccato_fino and u.bloccato_fino > timezone.now():
        errore = "Troppi tentativi falliti: l'account è bloccato per 15 minuti."
    elif request.method == "POST":
        if mfa.verifica_utente(u, request.POST.get("codice", "")):
            u.tentativi_falliti, u.bloccato_fino = 0, None
            u.save(update_fields=["tentativi_falliti", "bloccato_fino"])
            dest = request.session.pop("mfa_next", "") or "/"
            for k in ("mfa_utente", "mfa_scade"):
                request.session.pop(k, None)
            u.backend = "core.backends.UtenteBackend"
            login(request, u)
            log.registra(u, "accesso", "utenti", u.id, None, {"metodo": "credenziali", "secondo_fattore": True})
            return redirect(dest)
        u.tentativi_falliti += 1
        if u.tentativi_falliti >= 5:
            u.bloccato_fino, u.tentativi_falliti = timezone.now() + timedelta(minutes=15), 0
            request.session.pop("mfa_utente", None)
        u.save(update_fields=["tentativi_falliti", "bloccato_fino"])
        errore = "Codice non corretto."
    return render(request, "portale/accedi_2fa.html", {"errore": errore})
