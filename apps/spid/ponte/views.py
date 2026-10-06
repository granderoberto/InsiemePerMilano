"""Ponte tra l'SDK SPID/CIE e il sito.

1. Il sito manda l'utente a /ponte/avvia/?profilo=spid|cie.
2. Il ponte ricorda il profilo e avvia l'autenticazione OpenID Connect (SDK) verso l'identity provider.
3. Al ritorno l'SDK verifica firme e token, legge gli attributi e manda a /ponte/consegna/.
4. Qui si firma un token a scadenza con l'identità, si CANCELLANO i dati temporanei dell'SDK e si rimanda l'utente al sito.
Il sito non si fida del browser: accetta solo token firmati con il segreto condiviso (SPID_BRIDGE_SECRET)."""
import logging
import re
import uuid
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import logout
from django.core import signing
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import redirect

from spid_cie_oidc.relying_party.models import OidcAuthentication, OidcAuthenticationToken

log = logging.getLogger("ponte")
SALT = "lnc-ponte-spid"


def normalizza_cf(valore: str) -> str:
    """«TINIT-RSSMRA80A01F205X» → «RSSMRA80A01F205X»."""
    return re.sub(r"^TINIT-", "", (valore or "").strip(), flags=re.I).upper().replace(" ", "")


def salute(request):
    return HttpResponse("ok" if settings.PONTE_SEGRETO else "manca SPID_BRIDGE_SECRET", status=200 if settings.PONTE_SEGRETO else 500)


def avvia(request):
    profilo = request.GET.get("profilo")
    if profilo not in ("spid", "cie"):
        return HttpResponseBadRequest("profilo non valido")
    request.session["profilo"] = profilo
    if profilo == "spid" and getattr(settings, "SPID_SCELTA_IDP", False):
        return redirect("/oidc/rp/landing")  # in produzione l'utente sceglie il proprio gestore SPID dall'elenco
    provider = settings.PROVIDER_CIE if profilo == "cie" else settings.PROVIDER_SPID
    return redirect(f"/oidc/rp/authorization?provider={quote(provider, safe='')}&profile={profilo}")


def _purga(utente):
    """Dopo la consegna non resta nulla dell'identità nel servizio (dati personali = minimizzazione)."""
    tokens = OidcAuthenticationToken.objects.filter(user=utente)
    OidcAuthentication.objects.filter(pk__in=list(tokens.values_list("authz_request", flat=True))).delete()
    tokens.delete()
    utente.delete()


def consegna(request):
    if not settings.PONTE_SEGRETO:
        log.error("SPID_BRIDGE_SECRET non configurato")
        return HttpResponseServerError("Servizio non configurato.")
    attrs = request.session.get("oidc_rp_user_attrs")
    if not request.user.is_authenticated or not attrs:
        return HttpResponseBadRequest("Nessuna identità da consegnare.")
    cf = normalizza_cf(attrs.get("fiscal_number"))
    if not cf:
        log.warning("identità senza codice fiscale: non consegnata")
        logout(request)
        return redirect(f"{settings.SITO_URL}/accedi/spid/ritorno/?errore=cf")
    dati = {"metodo": request.session.get("profilo", "spid"), "cf": cf, "nome": attrs.get("first_name") or "",
            "cognome": attrs.get("last_name") or "", "email": (attrs.get("email") or "").lower(), "nascita": attrs.get("birthdate") or "",
            "emittente": (attrs.get("username") or "").split("__")[0], "nonce": uuid.uuid4().hex}
    token = signing.dumps(dati, key=settings.PONTE_SEGRETO, salt=SALT)
    utente = request.user
    logout(request)
    _purga(utente)
    log.info("identità %s consegnata al sito (emittente %s)", dati["metodo"], dati["emittente"])  # nessun dato personale nel log
    return redirect(f"{settings.SITO_URL}/accedi/spid/ritorno/?t={token}")
