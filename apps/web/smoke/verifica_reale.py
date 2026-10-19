"""Verifica del documento con i controlli VERI, dal modulo del sito: approvazione, rifiuto, revisione, pubblicazione."""
import os, sys, datetime, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; os.environ["LNC_PROVE"] = "1"; os.environ["IA_DOCUMENTO"] = "reale"; django.setup()
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from core.models import *
from core.services import token, ia
from portale.forms import nuova_sfida
from smoke import _documenti as D
from smoke._aiuti import SFX
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
esito("il sito usa i controlli veri (non il simulato)", not ia.documento_e_simulato())
PW = "Ombrello-Verde7!"
CONS = {k: "on" for k in ["privacy", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"]}
def utente(n, nome="Mario", cognome="Rossi", nascita="1990-03-15"):
    c = Client(); email = f"reale.prova{n}{SFX}@example.org"
    c.post("/registrati/", {"nome": nome, "cognome": cognome, "email": email, "data_nascita": nascita, "password": PW, "password2": PW, **CONS})
    u = Utente.objects.get(email=email); c.get(f"/conferma-email/{token.crea('conferma', u)}/"); u.refresh_from_db(); return c, u
def invia(c, fr, re_, se, primo=True):
    f = lambda im, n: SimpleUploadedFile(n, D.jpeg(im), content_type="image/jpeg")
    d = {"tipo_documento": "carta_identita", "fronte": f(fr, "fronte.jpg"), "retro": f(re_, "retro.jpg"), "selfie": f(se, "selfie.jpg"), "sfida": nuova_sfida()}
    if primo: d["biometrici"] = "on"
    return c.post("/profilo/verifica/", d, follow=True)
c, u = utente(1)
r = invia(c, D.fronte(), D.retro(), D.selfie()); v = u.verifiche.get(); u = Utente.objects.get(pk=u.pk)
esito("documento in regola: verifica approvata (100) e identità verificata", v.esito_ia == "approvata" and v.punteggio == 100 and u.identita_verificata, f"{v.esito_ia} {v.punteggio}")
esito("tutti i cinque controlli registrati come superati", all([v.ok_lettura_ocr, v.ok_corrispondenza_dati, v.ok_validita, v.ok_autenticita, v.ok_confronto_volto]))
esito("ora si può aprire «nuova segnalazione»", c.get("/segnalazioni/nuova/").status_code == 200)
c2, u2 = utente(2)
invia(c2, D.fronte(cognome="VERDI"), D.retro(cognome="VERDI"), D.selfie()); v2 = u2.verifiche.get()
esito("documento con un altro cognome: in revisione (dati non corrispondono), non approvata", v2.esito_ia == "da_rivedere" and not v2.ok_corrispondenza_dati and not Utente.objects.get(pk=u2.pk).identita_verificata, f"{v2.esito_ia} {v2.punteggio}")
esito("il motivo spiega cosa non va", "dati" in (v2.motivo or "").lower())
c3, u3 = utente(3)
invia(c3, D.fronte(scadenza="14.02.2019"), D.retro(scadenza="190214"), D.selfie()); v3 = u3.verifiche.get()
esito("documento scaduto: rifiutata con motivo", v3.esito_ia == "rifiutata" and not v3.ok_validita and "scad" in (v3.motivo or "").lower(), f"{v3.esito_ia} {v3.punteggio}")
c4, u4 = utente(4)
invia(c4, D.fronte(), D.retro(), D.senza_volto()); v4 = u4.verifiche.get()
esito("selfie senza volto: rifiutata", v4.esito_ia == "rifiutata", f"{v4.esito_ia} {v4.punteggio}")
mod = Utente.objects.filter(ruolo="moderatore").first(); M = Client(); M.login(email=mod.email, password="DemoMilano2026!")
esito("la verifica in revisione compare nella coda del moderatore", f"/moderazione/verifiche/{v2.id}/decidi/" in M.get("/moderazione/").content.decode())
M.post(f"/moderazione/verifiche/{v2.id}/decidi/", {"esito": "approvata", "motivo": "Cognome con doppia grafia verificato a mano"})
esito("il moderatore approva: l'identità risulta verificata", Utente.objects.get(pk=u2.pk).identita_verificata)
import glob
from django.conf import settings
esito("dopo la verifica non restano immagini sul disco", not glob.glob(str(settings.TMP_VERIFICHE_DIR / "*" / "*")))
