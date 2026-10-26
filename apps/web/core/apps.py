import os
import sys

from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Con IA_LAVORATORE=1 il lavoratore dei controlli IA gira in un thread del sito (solo dentro gunicorn o runserver)."""
        if not (settings.IA_LAVORATORE and settings.IA_MODALITA == "coda"):
            return
        eseguibile = os.path.basename(sys.argv[0])
        in_server = "gunicorn" in eseguibile or ("runserver" in sys.argv and os.environ.get("RUN_MAIN") == "true")
        if in_server:
            from core.services.ia import lavoratore
            lavoratore.avvia()
