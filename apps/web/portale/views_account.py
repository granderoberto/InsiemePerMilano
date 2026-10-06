"""Email, password e preferenze di notifica."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Notifica, PreferenzaNotifica, Utente
from core.services import email as posta, log, token
from core.services.errori import traduci

from .forms import PasswordForm

TIPI_NOTIFICA = [
    ("verifica_account", "Esito della verifica del tuo account", True),
    ("stato_account", "Sospensione o riattivazione del tuo account", True),
    ("normativa_aggiornata", "Nuova versione di un documento normativo", True),
    ("stato_segnalazione", "Una tua segnalazione cambia stato", False),
    ("contenuto_bloccato", "Un tuo contenuto è bloccato dai controlli automatici", False),
    ("nuovo_commento", "Qualcuno commenta una tua segnalazione", False),
    ("risposta_commento", "Qualcuno risponde a un tuo commento", False),
    ("nuova_segnalazione_quartiere", "Nuova segnalazione nel tuo quartiere", False),
]
OBBLIGATORIE = {t for t, _, ob in TIPI_NOTIFICA if ob}


def preferenze(utente):
    """{tipo: (in_app, email)}; le righe mancanti si creano con i valori predefiniti."""
    righe = {p.tipo: p for p in PreferenzaNotifica.objects.filter(utente=utente)}
    for tipo, _, ob in TIPI_NOTIFICA:
        if tipo not in righe:
            righe[tipo] = PreferenzaNotifica.objects.create(utente=utente, tipo=tipo, in_app=True, email=False)
    return {t: (p.in_app, p.email) for t, p in righe.items()}


# ------------------------------------------------------------------ conferma email
def ha_verifica_approvata(u):
    return any((v.esito_finale or v.esito_ia) == "approvata" for v in u.verifiche.all())


def ricalcola_attivazione(u):
    """L'account diventa attivo quando l'email è confermata E la verifica d'identità è approvata."""
    if u.stato_account != "in_attesa_verifica" or not u.email_verificata_il:
        return False
    if u.metodo_registrazione == "credenziali" and not ha_verifica_approvata(u):
        return False
    u.stato_account = "attivo"
    u.save(update_fields=["stato_account"])
    Notifica.objects.create(utente=u, tipo="verifica_account", messaggio="Email e identità verificate: il tuo account è attivo.", link="/profilo/")
    return True


def invia_conferma(request, u):
    link = request.build_absolute_uri(reverse("conferma_email", args=[token.crea("conferma", u)]))
    posta.invia(request, u.email, "Conferma il tuo indirizzo email", "Conferma l'indirizzo per completare la registrazione.", link)


def conferma_email(request, tok):
    d = token.leggi(tok, "conferma")
    u = Utente.objects.filter(pk=d["u"]).first() if d else None
    if u is None:
        messages.error(request, "Il link non è valido o è scaduto: puoi richiederne uno nuovo dal profilo.")
        return redirect("home")
    if not u.email_verificata_il:
        u.email_verificata_il = timezone.now()
        u.save(update_fields=["email_verificata_il"])
        log.registra(u, "modifica", "utenti", u.id, {"email_verificata_il": None}, {"email_verificata_il": u.email_verificata_il})
    attivato = ricalcola_attivazione(u)
    messages.success(request, "Email confermata. " + ("Il tuo account è attivo." if attivato else "Resta da completare la verifica dell'identità."))
    return redirect("profilo" if request.user.is_authenticated else "accedi")


@require_POST
@login_required
def reinvia_conferma(request):
    if request.user.email_verificata_il:
        messages.info(request, "L'email è già confermata.")
    else:
        invia_conferma(request, request.user)
        messages.success(request, "Ti abbiamo inviato un nuovo link di conferma.")
    return redirect("profilo")


# ------------------------------------------------------------------ cambio email
@require_POST
@login_required
def cambia_email(request):
    nuova = request.POST.get("email", "").strip().lower()
    if "@" not in nuova or len(nuova) > 254:
        messages.error(request, "Inserisci un indirizzo email valido.")
    elif Utente.objects.filter(email=nuova).exists():
        messages.error(request, "Esiste già un account con questa email.")
    else:
        link = request.build_absolute_uri(reverse("conferma_nuova_email", args=[token.crea("email", request.user, nuova)]))
        posta.invia(request, nuova, "Conferma il nuovo indirizzo email", "Conferma il nuovo indirizzo: finché non lo fai resta valido quello attuale.", link)
        messages.success(request, f"Abbiamo inviato un link di conferma a {nuova}. L'indirizzo cambia solo dopo la conferma.")
    return redirect("profilo")


@login_required
def conferma_nuova_email(request, tok):
    d = token.leggi(tok, "email")
    if not d or d["u"] != request.user.id:
        messages.error(request, "Il link non è valido, è scaduto o appartiene a un altro account.")
        return redirect("profilo")
    prima = request.user.email
    request.user.email = d["x"]
    request.user.email_verificata_il = timezone.now()
    try:
        with transaction.atomic():
            request.user.save(update_fields=["email", "email_verificata_il"])
    except DatabaseError as e:
        request.user.email = prima
        messages.error(request, str(traduci(e)))
        return redirect("profilo")
    log.registra(request.user, "modifica", "utenti", request.user.id, {"email": prima}, {"email": d["x"]})
    ricalcola_attivazione(request.user)
    messages.success(request, "Indirizzo email aggiornato.")
    return redirect("profilo")


# ------------------------------------------------------------------ recupero password
def password_dimenticata(request):
    inviata = False
    if request.method == "POST":
        u = Utente.objects.filter(email=request.POST.get("email", "").strip().lower(), metodo_registrazione="credenziali").exclude(stato_account="eliminato").first()
        if u:  # la risposta è identica anche se l'email non esiste: non si rivela chi è registrato
            link = request.build_absolute_uri(reverse("reset_password", args=[token.crea("reset", u)]))
            posta.invia(request, u.email, "Reimposta la password", "Hai chiesto di reimpostare la password. Il link vale 2 ore.", link)
        inviata = True
    return render(request, "portale/password_dimenticata.html", {"inviata": inviata})


def reset_password(request, tok):
    d = token.leggi(tok, "reset")
    u = Utente.objects.filter(pk=d["u"]).first() if d else None
    if u is None or d.get("p") != token.impronta_password(u) or u.metodo_registrazione != "credenziali":
        return render(request, "portale/reset_password.html", {"non_valido": True})
    form = PasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u.set_password(form.cleaned_data["password"])
        u.tentativi_falliti, u.bloccato_fino = 0, None
        u.save(update_fields=["password", "tentativi_falliti", "bloccato_fino"])
        log.registra(u, "modifica", "utenti", u.id, None, {"password": "reimpostata"})
        messages.success(request, "Password aggiornata: ora puoi accedere.")
        return redirect("accedi")
    return render(request, "portale/reset_password.html", {"form": form})


# ------------------------------------------------------------------ preferenze di notifica
@login_required
def preferenze_notifica(request):
    if request.method == "POST":
        for tipo, _, ob in TIPI_NOTIFICA:
            PreferenzaNotifica.objects.filter(utente=request.user, tipo=tipo).update(
                in_app=True if ob else request.POST.get(f"app_{tipo}") == "on", email=request.POST.get(f"email_{tipo}") == "on")
        messages.success(request, "Preferenze salvate.")
        return redirect("preferenze_notifica")
    pref = preferenze(request.user)
    return render(request, "portale/preferenze.html", {"righe": [(t, e, ob, *pref[t]) for t, e, ob in TIPI_NOTIFICA]})
