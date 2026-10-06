"""Accesso con SPID/CIE di PUNTA A PUNTA sull'ambiente di prova ufficiale: sito → servizio RP → gestore di identità di prova
→ servizio RP → sito. Richiede: sito su :8000 e apps/spid/demo/avvia.sh in esecuzione."""
import os, re, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"
import django; django.setup()
import requests
from core.models import Utente, Consenso, LogAttivita
SITO = "http://127.0.0.1:8000"
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
def campo(html, nome):
    m = re.search(r'name="%s"[^>]*value="([^"]*)"' % nome, html) or re.search(r'value="([^"]*)"[^>]*name="%s"' % nome, html)
    return m.group(1) if m else None
def accedi_al_gestore(metodo):
    s = requests.Session(); r = s.get(f"{SITO}/accedi/spid/avvia/{metodo}/", timeout=60)
    assert "/oidc/op/authorization" in r.url, r.url
    r = s.post("http://127.0.0.1:8012/oidc/op/authorization", timeout=60, headers={"Referer": r.url}, data={
        "csrfmiddlewaretoken": campo(r.text, "csrfmiddlewaretoken"), "username": "user", "password": "oidcuser", "authz_request_object": campo(r.text, "authz_request_object") or ""})
    assert "/oidc/op/consent" in r.url, (r.url, r.text[:300])
    f = re.search(r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>', r.text)
    r = s.post("http://127.0.0.1:8012" + (f.group(1) if f and f.group(1) not in ("", "#") else "/oidc/op/consent"), timeout=90, headers={"Referer": r.url},
               data={"csrfmiddlewaretoken": campo(r.text, "csrfmiddlewaretoken"), "agree": "True"})
    return s, r
CONSENSI = {k: "on" for k in ["privacy", "intelligenza_artificiale", "termini_uso", "cookie", "eta_minima"]}
Utente.objects.filter(email="antonio@ema.il").exists() and print("(account di prova già presente da un test precedente: si verifica l'accesso diretto)")
nuovo = not Utente.objects.filter(metodo_registrazione="spid", codice_fiscale_hash=hashlib.sha256(b"AATTTJDFKSKDF89").hexdigest()).exists()
s, r = accedi_al_gestore("spid")
if nuovo:
    esito("1ª volta: il ritorno porta al completamento del profilo", r.url.endswith("/accedi/spid/completa/") and "peppe" in r.text, r.url)
    esito("data di nascita fornita dal gestore, non richiesta", "nato/a il" in r.text and 'name="data_nascita"' not in r.text)
    r2 = s.post(f"{SITO}/accedi/spid/completa/", data={"csrfmiddlewaretoken": campo(r.text, "csrfmiddlewaretoken"), "email": "antonio@ema.il", **CONSENSI}, timeout=90)
    esito("account creato e utente autenticato", r2.url.rstrip("/") == SITO and "Benvenuto" in r2.text and "peppe" in r2.text, r2.url)
u = Utente.objects.get(codice_fiscale_hash=hashlib.sha256(b"AATTTJDFKSKDF89").hexdigest())
esito("utente SPID: attivo, senza password, solo impronta del codice fiscale", u.stato_account == "attivo" and u.password is None and u.metodo_registrazione == "spid" and len(u.codice_fiscale_hash) == 64)
esito("5 consensi registrati (nessun consenso biometrico)", Consenso.objects.filter(utente=u).count() == 5)
esito("accesso nel registro", LogAttivita.objects.filter(utente=u, operazione="accesso", dati_nuovi__metodo="spid").exists())
# 2ª volta, browser nuovo: stesso utente, nessun completamento
s2, r = accedi_al_gestore("spid")
esito("2ª volta: accesso diretto, senza completamento", r.url.rstrip("/") == SITO and "peppe" in r.text, r.url)
esito("un solo account per persona", Utente.objects.filter(codice_fiscale_hash=u.codice_fiscale_hash).count() == 1)
# CIE
s3, r = accedi_al_gestore("cie"); esito("accesso con CIE sullo stesso flusso", r.url.rstrip("/") == SITO and "peppe" in r.text, r.url)
# il servizio non trattiene dati
import subprocess
out = subprocess.run([os.path.join("..", "spid", ".venv", "bin", "python"), "manage.py", "shell", "-c",
    "from spid_cie_oidc.accounts.models import User; from spid_cie_oidc.relying_party.models import OidcAuthentication as A, OidcAuthenticationToken as T; print(User.objects.count(), A.objects.count(), T.objects.count())"],
    cwd=os.path.join("..", "spid"), capture_output=True, text=True, env={**os.environ, "DJANGO_SETTINGS_MODULE": "servizio_rp.settings"}).stdout.strip().splitlines()[-1].split()
esito("il servizio SPID non conserva utenti, autenticazioni né token", out == ["0", "0", "0"], str(out))
