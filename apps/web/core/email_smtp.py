"""SMTP con lo stesso filtro dei domini riservati dell'API di Gmail: mai email verso indirizzi di esempio."""
from django.core.mail.backends.smtp import EmailBackend

from .email_backend import senza_riservati


class SmtpSicuro(EmailBackend):
    def send_messages(self, email_messages):
        return super().send_messages(senza_riservati(list(email_messages)))
