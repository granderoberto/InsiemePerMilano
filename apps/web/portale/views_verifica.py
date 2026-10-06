"""Nuovo tentativo di verifica del documento (massimo 3, par. 3.3)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import redirect, render

from core.services.errori import traduci

from . import verifica
from .forms import DocumentiForm, nuova_sfida
from .views_account import ricalcola_attivazione


@login_required
def riprova(request):
    u = request.user
    if u.metodo_registrazione != "credenziali" or u.stato_account != "in_attesa_verifica":
        messages.info(request, "Non c'è nessuna verifica del documento da rifare.")
        return redirect("profilo")
    tentativi = list(u.verifiche.order_by("tentativo"))
    ultima = tentativi[-1] if tentativi else None
    if ultima and (ultima.esito_ia != "rifiutata" or ultima.revisore_id):
        messages.info(request, "L'ultima verifica non è stata rifiutata: non c'è nulla da rifare.")
        return redirect("profilo")
    if len(tentativi) >= verifica.MAX_TENTATIVI:
        messages.warning(request, "Hai usato tutti e 3 i tentativi: puoi chiedere la revisione di un moderatore dal profilo.")
        return redirect("profilo")
    form = DocumentiForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            v = verifica.esegui(u, len(tentativi) + 1, d["tipo_documento"], d["_fronte"], d.get("_retro"), d["_selfie"])
        except DatabaseError as e:
            form.add_error(None, str(traduci(e)))
        else:
            if v.esito_ia == "approvata":
                attivato = ricalcola_attivazione(u)
                messages.success(request, "Verifica approvata." + (" Il tuo account è attivo." if attivato else " Conferma anche l'indirizzo email per attivarlo."))
            elif v.esito_ia == "da_rivedere":
                messages.info(request, "La verifica è in revisione: un moderatore la controllerà.")
            else:
                messages.error(request, f"Verifica non superata ({v.motivo}).")
            return redirect("profilo")
    return render(request, "portale/riprova_verifica.html", {"form": form, "sfida": nuova_sfida(), "tentativo": len(tentativi) + 1})
