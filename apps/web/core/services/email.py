"""Invio delle email del sito (conferma indirizzo, recupero password, avvisi di sicurezza).

Configurazione in `.env` (vedi apps/web/README.md): EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD,
EMAIL_SSL (465) oppure TLS (587), EMAIL_FROM, SITE_URL. Senza EMAIL_HOST le email escono sulla console del server
(solo sviluppo) e il link compare anche a schermo; con un server SMTP vero il link NON si mostra mai a schermo."""
import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

log = logging.getLogger(__name__)


def e_console() -> bool:
    return "console" in settings.EMAIL_BACKEND


def link_assoluto(request, percorso: str) -> str:
    """Indirizzo completo per i link nelle email: SITE_URL se configurato (obbligatorio in produzione)."""
    base = getattr(settings, "SITE_URL", "").rstrip("/")
    return f"{base}{percorso}" if base else request.build_absolute_uri(percorso)


def consentito(chiave: str, massimo: int = 3, finestra: int = 3600) -> bool:
    """Limite di frequenza (contatore in cache): impedisce di usare il sito per inondare di email un indirizzo."""
    k = f"rl:{chiave}"
    if cache.add(k, 1, finestra):
        return True
    try:
        return cache.incr(k) <= massimo
    except ValueError:
        cache.set(k, 1, finestra)
        return True


def ip_di(request) -> str:
    return request.META.get("REMOTE_ADDR", "?")


def invia(request, destinatario, oggetto, titolo, paragrafi, pulsante=None, link=None, nota=None) -> bool:
    """Spedisce un messaggio (testo + HTML). -> True se il server di posta l'ha accettato."""
    ctx = {"titolo": titolo, "paragrafi": paragrafi, "pulsante": pulsante, "link": link, "nota": nota}
    testo = "\n\n".join([titolo, *paragrafi] + ([f"{pulsante}: {link}"] if link and pulsante else []) + ([nota] if nota else [])
                        + ["— La Nostra Città, Il Nostro Futuro"])
    try:
        msg = EmailMultiAlternatives(oggetto, testo, settings.DEFAULT_FROM_EMAIL, [destinatario])
        msg.attach_alternative(render_to_string("email/messaggio.html", ctx), "text/html")
        msg.send(fail_silently=False)
    except Exception:  # server irraggiungibile, credenziali errate, indirizzo rifiutato…
        log.exception("Invio email a %s non riuscito", destinatario)
        return False
    if link and e_console() and settings.DEBUG and request is not None:
        messages.info(request, f"(Sviluppo: le email escono sulla console) {oggetto}. Link: {link}")
    return True
