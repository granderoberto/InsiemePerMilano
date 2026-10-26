import time

from django.core.management.base import BaseCommand

from core.services.ia import coda, fornitori, lavoratore, quota


class Command(BaseCommand):
    help = "Esegue i controlli IA in coda (docs/piano_ia_openrouter.md). Senza opzioni gira finché non lo si ferma."

    def add_arguments(self, parser):
        parser.add_argument("--una-volta", action="store_true", help="esce quando la coda è vuota o la quota è finita")
        parser.add_argument("--stato", action="store_true", help="mostra coda e quota e termina")

    def handle(self, *args, **o):
        if o["stato"]:
            for q in quota.stato_tutti(forza=True):
                if not q["configurato"]:
                    self.stdout.write(f"{q['etichetta']}: non configurato ({q['motivo']})")
                    continue
                uff = f", contatore del fornitore {q['ufficiale']}" if q["ufficiale"] is not None else ""
                self.stdout.write(f"{q['etichetta']}: {q['usate']}/{q['limite']} oggi (segnalazioni {q['segnalazioni']}/{q['limiti']['segnalazioni']}, "
                                  f"commenti {q['commenti']}/{q['limiti']['commenti']}{uff}){' — messo da parte' if q['messo_da_parte'] else ''}")
            self.stdout.write("Catena testo: " + (" → ".join(f"{f.nome}:{m}" for f, m in fornitori.catena(False)) or "nessun fornitore configurato"))
            self.stdout.write("Catena foto:  " + (" → ".join(f"{f.nome}:{m}" for f, m in fornitori.catena(True)) or "nessun fornitore configurato"))
            self.stdout.write("Coda: " + (", ".join(f"{k} {v}" for k, v in sorted(coda.conteggi().items())) or "vuota"))
            return
        while True:
            esito = lavoratore.passo()
            self.stdout.write(esito)
            if o["una_volta"] and esito in ("vuoto", "quota"):
                return
            time.sleep(lavoratore.ATTESA[esito] if not o["una_volta"] else 0)
