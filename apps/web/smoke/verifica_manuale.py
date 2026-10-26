"""Verifica manuale dell'identità da parte dell'amministratore (senza richiesta dell'utente) e revoca."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; django.setup()
from django.test import Client
from core.models import *
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
adm = Utente.objects.filter(ruolo="amministratore", stato_account="attivo").first()
from django.db import transaction
class Rollback(Exception): pass
u = next(x for x in Utente.objects.filter(ruolo="utente", metodo_registrazione="credenziali", stato_account="attivo", id__lte=154))
c = Client(); c.force_login(adm, backend="core.backends.UtenteBackend")
base = f"/amministrazione/utenti/{u.id}/"
try:
    with transaction.atomic():
        u.verifiche.all().delete()  # percorso senza richiesta precedente
        esito("la scheda mostra il pulsante", b"Segna come verificata" in c.get(base).content)
        esito("filtro 'non verificata' include l'utente", u.nome.encode() in c.get("/amministrazione/utenti/?identita=no&q=" + u.email).content)
        c.post(base + "verifica_identita/", {"motivo": ""}); u = Utente.objects.get(pk=u.pk); esito("senza motivo non verifica", not u.identita_verificata)
        c.post(base + "verifica_identita/", {"motivo": "prova: documento visto di persona"}); u = Utente.objects.get(pk=u.pk)
        esito("con motivo l'identità risulta verificata", u.identita_verificata)
        v = u.verifiche.get(); esito("riga con revisore e esito finale", v.revisore_id == adm.id and v.esito_finale == "approvata")
        esito("filtro 'verificata' include l'utente", u.nome.encode() in c.get("/amministrazione/utenti/?identita=si&q=" + u.email).content)
        esito("notifica all'utente", Notifica.objects.filter(utente=u, messaggio__contains="verificata da un amministratore").exists())
        esito("nel registro", LogAttivita.objects.filter(tabella="verifiche_identita", id_oggetto=v.id, operazione="revisione_moderatore").exists())
        c.post(base + "revoca_verifica/", {"motivo": "prova"}); u = Utente.objects.get(pk=u.pk); esito("la revoca toglie la verifica", not u.identita_verificata)
        # utente con richiesta rifiutata dall'IA: la decisione dell'amministratore prevale
        c.post(base + "verifica_identita/", {"motivo": "di nuovo"}); u = Utente.objects.get(pk=u.pk); esito("dopo la revoca si può riverificare", u.identita_verificata and u.verifiche.count() == 1)
        c2 = Client(); c2.force_login(Utente.objects.filter(ruolo="utente", stato_account="attivo").exclude(pk=u.pk).first(), backend="core.backends.UtenteBackend")
        esito("un utente normale non può", c2.post(base + "revoca_verifica/", {"motivo": "x"}).status_code in (302, 403, 404) and Utente.objects.get(pk=u.pk).identita_verificata)
        raise Rollback()
except Rollback:
    pass
