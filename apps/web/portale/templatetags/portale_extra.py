from django import template

from django.utils.text import slugify

register = template.Library()


@register.filter
def classe_categoria(nome):
    """Classe CSS `cat-<slug>`: ogni categoria ha il colore di una linea della metropolitana di Milano."""
    return "cat-" + slugify(nome or "")


@register.filter
def url_media(percorso):
    return "/" + percorso.lstrip("/")


@register.filter
def etichetta_stato(stato_id):
    return {1: "Ricevuta", 2: "In attesa", 3: "Approvata", 4: "Rifiutata", 5: "Presentata ai candidati"}.get(stato_id, "")


@register.filter
def percento(valore, massimo):
    try:
        return round(100 * float(valore) / float(massimo))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0
