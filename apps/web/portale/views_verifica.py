"""Verifica dell'identità con il documento (par. 3.3): facoltativa alla registrazione, necessaria per pubblicare. Massimo 3 tentativi."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.shortcuts import redirect, render

from core.models import Consenso
from core.services import normative
from core.services.errori import traduci

from . import verifica
from .forms import VerificaForm, nuova_sfida
from .views import registra_consensi
from .views_account import ricalcola_attivazione


@login_required
def riprova(request):
    u = request.user
    if u.metodo_registrazione != "credenziali" or u.ruolo != "utente":
        messages.info(request, "Il tuo accesso è già certificato: non serve verificare il documento.")
        return redirect("profilo")
    if not u.puo_interagire:
        messages.warning(request, "Conferma prima il tuo indirizzo email: la verifica del documento si fa dopo.")
        return redirect("profilo")
    if u.identita_verificata:
        messages.info(request, "La tua identità è già verificata: puoi pubblicare segnalazioni.")
        return redirect("profilo")
    tentativi = list(u.verifiche.order_by("tentativo"))
    ultima = tentativi[-1] if tentativi else None
    if ultima and ultima.esito_ia == "da_rivedere" and not ultima.esito_finale:
        messages.info(request, "La tua verifica è in revisione: un moderatore la controllerà e ti avviseremo dell'esito.")
        return redirect("profilo")
    if ultima and ultima.esito_ia != "rifiutata" and not ultima.revisore_id:
        messages.info(request, "L'ultima verifica non è stata rifiutata: non c'è nulla da rifare.")
        return redirect("profilo")
    if len(tentativi) >= verifica.MAX_TENTATIVI:
        messages.warning(request, "Hai usato tutti e 3 i tentativi: puoi chiedere la revisione di un moderatore dal profilo.")
        return redirect("profilo")
    biometrico = normative.ultime_versioni().get("biometrici")
    gia_dato = biometrico is None or Consenso.objects.filter(utente=u, documento=biometrico).exists()
    form = VerificaForm(request.POST or None, request.FILES or None, consenso_gia_dato=gia_dato)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            with transaction.atomic():
                if not gia_dato:
                    registra_consensi(u, ["biometrici"])
                v = verifica.esegui(u, len(tentativi) + 1, d["tipo_documento"], d["_fronte"], d.get("_retro"), d["_selfie"])
        except DatabaseError as e:
            form.add_error(None, str(traduci(e)))
        else:
            if v.esito_ia == "approvata":
                ricalcola_attivazione(u)
                messages.success(request, "Identità verificata: ora puoi pubblicare segnalazioni.")
                return redirect("nuova")
            elif v.esito_ia == "da_rivedere":
                messages.info(request, "La verifica è in revisione: un moderatore la controllerà e ti avviseremo dell'esito.")
            else:
                messages.error(request, f"Verifica non superata ({v.motivo}).")
            return redirect("profilo")
    return render(request, "portale/riprova_verifica.html", {"form": form, "sfida": nuova_sfida(), "tentativo": len(tentativi) + 1})
