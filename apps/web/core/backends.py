from .models import Utente


class UtenteBackend:
    """Accesso con email e password (hash bcrypt della tabella utenti)."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        u = Utente.objects.filter(email=email.strip().lower()).first()
        if u is None:
            return None
        return u if u.check_password(password) else None

    def get_user(self, user_id):
        u = Utente.objects.filter(pk=user_id).first()
        return u if u and u.stato_account != "eliminato" else None
