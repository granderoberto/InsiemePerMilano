from django.http import HttpResponse


class ControlloDiStato:
    """Risponde a /salute/ prima di ogni altro controllo: il controllo di stato dell'hosting arriva con un indirizzo
    interno (non in ALLOWED_HOSTS) e senza HTTPS, quindi altrimenti verrebbe respinto e il deploy risulterebbe fallito."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/salute/" and not request.GET.get("db"):
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
