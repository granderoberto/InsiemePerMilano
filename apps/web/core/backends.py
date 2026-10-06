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
        if u is None or u.stato_account == "eliminato":
            return None
        if u.stato_account == "sospeso":
            from .services.utenti import riattiva_se_scaduta
            riattiva_se_scaduta(u)  # la sospensione a tempo finisce da sola
        return u
