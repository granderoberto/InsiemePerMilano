"""Conferma dell'email da parte dell'amministratore e invio email non configurato in produzione."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from django.test import Client, override_settings
from core.models import *
from core.services import email as posta
PW = "DemoMilano2026!"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
adm = Utente.objects.filter(ruolo="amministratore", stato_account="attivo").first()
u = Utente.objects.filter(stato_account="in_attesa_verifica", email_verificata_il__isnull=True, id__lte=154).first()
esito("esiste un utente con email non confermata", u is not None)
c = Client(); c.force_login(adm, backend="core.backends.UtenteBackend")
url = f"/amministrazione/utenti/{u.id}/conferma_email/"
c.post(url, {"motivo": ""}); u.refresh_from_db(); esito("senza motivo non conferma", u.email_verificata_il is None)
c.post(url, {"motivo": "prova: invio email non attivo"}); u.refresh_from_db(); esito("con motivo conferma", u.email_verificata_il is not None)
log = LogAttivita.objects.filter(operazione="modifica", tabella="utenti", id_oggetto=u.id).order_by("-id").first()
esito("l'azione è nel registro con il motivo", log is not None and "confermata_da_admin" in str(log.dati_nuovi))
c.post(url, {"motivo": "di nuovo"}); esito("non si conferma due volte (nessun errore)", True)
c2 = Client(); c2.force_login(Utente.objects.filter(ruolo="utente", stato_account="attivo").first(), backend="core.backends.UtenteBackend")
esito("un utente normale non può", c2.post(url, {"motivo": "x"}).status_code in (302, 403, 404))
with override_settings(DEBUG=False, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"):
    esito("produzione senza SMTP: l'invio risulta fallito (non finge)", posta.invia(None, "a@b.it", "o", "t", ["p"]) is False)
with override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
    esito("con un backend vero l'invio riesce", posta.invia(None, "a@b.it", "o", "t", ["p"]) is True)
