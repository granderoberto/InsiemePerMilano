"""Invio email. In sviluppo il backend è la console del server e il link si mostra anche a schermo."""
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail


def invia(request, destinatario, oggetto, testo, link):
    corpo = f"{testo}\n\n{link}\n\n— La Nostra Città, Il Nostro Futuro"
    send_mail(oggetto, corpo, settings.DEFAULT_FROM_EMAIL, [destinatario], fail_silently=True)
    if settings.DEBUG:
        messages.info(request, f"(Sviluppo) email a {destinatario}: «{oggetto}». Link: {link}")
