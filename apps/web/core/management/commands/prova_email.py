"""Invia un'email di prova con la configurazione attuale: `manage.py prova_email indirizzo@esempio.it`."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verifica la configurazione email inviando un messaggio di prova (nessun dato personale nel testo)."

    def add_arguments(self, parser):
        parser.add_argument("destinatario")

    def handle(self, *args, destinatario, **opzioni):
        if "console" in settings.EMAIL_BACKEND:
            raise CommandError("EMAIL_HOST non è impostato: le email escono solo sulla console. Vedi docs/produzione.md.")
        self.stdout.write(f"Server {settings.EMAIL_HOST}:{settings.EMAIL_PORT} (SSL={settings.EMAIL_USE_SSL}, STARTTLS={settings.EMAIL_USE_TLS}), mittente {settings.DEFAULT_FROM_EMAIL}")
        msg = EmailMultiAlternatives("Prova di invio · La Nostra Città", "Se leggi questo messaggio, l'invio delle email funziona.", settings.DEFAULT_FROM_EMAIL, [destinatario])
        msg.attach_alternative("<p>Se leggi questo messaggio, <strong>l'invio delle email funziona</strong>.</p>", "text/html")
        try:
            msg.send()
        except Exception as e:  # noqa: BLE001 - si mostra l'errore del server all'operatore
            raise CommandError(f"Invio non riuscito: {type(e).__name__}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Messaggio consegnato al server SMTP per {destinatario}. Controlla anche la cartella spam."))
