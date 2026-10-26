"""Controllo iniziale di segnalazioni e commenti: lo usano le viste prima di salvare (docs/piano_ia_openrouter.md, §6).

Modalità «sincrona» (predefinita): come prima, i controlli simulati rispondono subito.
Modalità «coda» (IA_MODALITA=coda): il prefiltro locale decide i casi evidenti; gli altri si salvano senza esito (`NULL`)
e vanno in coda per il modello. L'utente vede subito la segnalazione «In attesa»; l'esito arriva dopo, dal lavoratore."""
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from core.models import Commento, Segnalazione

from . import coda, prefiltro
from . import simulato


def in_coda():
    return settings.IA_MODALITA == "coda"


@dataclass
class Controllo:
    esito: str | None             # ok | dubbio | bloccato | None = in attesa del modello
    punteggio_moderazione: Decimal | None
    punteggio_coerenza: Decimal | None = None
    suggerite: dict = field(default_factory=dict)
    prefiltro: object = None      # Esito del prefiltro, solo in modalità coda

    @property
    def da_accodare(self):
        if self.prefiltro is None:
            return False
        # un commento pulito si rilegge col modello se la quota lo permette (priorità minima)
        return self.prefiltro.esito == "da_inviare" or (self.prefiltro.esito == "pulito" and self.rilettura)

    rilettura: bool = False

    @property
    def bloccato(self):
        return self.esito == "bloccato"


def segnalazione(utente, titolo, descrizione, n_media, escludi_id=None):
    testo = f"{titolo}\n{descrizione}"
    if not in_coda():
        from . import controlla_testo, coerenza_immagine_testo, suggerisci_categorie
        esito, p = controlla_testo(f"{titolo} {descrizione}")
        return Controllo(esito, Decimal(str(p)), Decimal(str(coerenza_immagine_testo(titolo, descrizione, n_media))),
                         dict(suggerisci_categorie(titolo, descrizione)))
    recenti = [prefiltro.impronta(f"{s.titolo}\n{s.descrizione}") for s in
               Segnalazione.objects.filter(autore=utente, creata_il__gte=timezone.now() - timedelta(days=1)).exclude(pk=escludi_id)[:30]]
    pf = prefiltro.analizza(testo, ha_media=n_media > 0, tipo="segnalazione", recenti=recenti)
    suggerite = dict(simulato.suggerisci_categorie(titolo, descrizione))   # le categorie le propone il controllo locale
    return Controllo(pf.esito_locale, Decimal(str(pf.punteggio)) if pf.esito_locale else None, None, suggerite, pf)


def commento(utente, testo):
    if not in_coda():
        from . import controlla_testo
        esito, p = controlla_testo(testo)
        return Controllo(esito, Decimal(str(p)))
    recenti = [prefiltro.impronta(c.testo) for c in
               Commento.objects.filter(autore=utente, creato_il__gte=timezone.now() - timedelta(days=1))[:30]]
    pf = prefiltro.analizza(testo, tipo="commento", recenti=recenti)
    return Controllo(pf.esito_locale, Decimal(str(pf.punteggio)) if pf.esito_locale else None, None, {}, pf,
                     rilettura=settings.IA_RILEGGI_PULITI)


def accoda_se_serve(controllo, *, segnalazione=None, commento=None):
    """Da chiamare dopo aver salvato il contenuto (e fuori dalla transazione)."""
    if controllo.da_accodare:
        coda.accoda(controllo.prefiltro, segnalazione=segnalazione, commento=commento)
