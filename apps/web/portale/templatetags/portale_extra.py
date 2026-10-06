from django import template

register = template.Library()


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
