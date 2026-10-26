import time

from django.core.management.base import BaseCommand

from core.services.ia import coda, lavoratore, quota


class Command(BaseCommand):
    help = "Esegue i controlli IA in coda (docs/piano_ia_openrouter.md). Senza opzioni gira finché non lo si ferma."

    def add_arguments(self, parser):
        parser.add_argument("--una-volta", action="store_true", help="esce quando la coda è vuota o la quota è finita")
        parser.add_argument("--stato", action="store_true", help="mostra coda e quota e termina")

    def handle(self, *args, **o):
        if o["stato"]:
            s = quota.stato(forza=True)
            self.stdout.write(f"Quota oggi: {s['usate']}/{s['limite']} (segnalazioni {s['segnalazioni']}, commenti {s['commenti']}, ufficiale {s['ufficiale']})")
            self.stdout.write("Coda: " + (", ".join(f"{k} {v}" for k, v in sorted(coda.conteggi().items())) or "vuota"))
            return
        while True:
            esito = lavoratore.passo()
            self.stdout.write(esito)
            if o["una_volta"] and esito in ("vuoto", "quota"):
                return
            time.sleep(lavoratore.ATTESA[esito] if not o["una_volta"] else 0)
