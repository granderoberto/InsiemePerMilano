"""Modelli del dominio.

Tutti `managed = False`: lo schema è dei file db/migrations/*.sql (vedi CLAUDE.md, regola di convivenza).
Se cambi una colonna nel SQL, aggiorna qui il modello nello stesso commit.
"""
import bcrypt
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Now


class Quartiere(models.Model):
    id = models.SmallAutoField(primary_key=True)
    nome = models.CharField(max_length=100, unique=True)
    municipio = models.SmallIntegerField()
    confine = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "quartieri"
        ordering = ["nome"]

    def __str__(self):
        return self.nome.title()

    @property
    def nome_leggibile(self):
        return self.nome.title()


class UtenteManager(BaseUserManager):
    def get_by_natural_key(self, email):
        return self.get(email=email)


class Utente(AbstractBaseUser):
    """Utente di autenticazione: tabella `utenti`, niente auth_user."""

    id = models.AutoField(primary_key=True)
    password = models.CharField(max_length=255, db_column="password_hash", blank=True, null=True)
    last_login = None  # la tabella non ha last_login
    nome = models.CharField(max_length=50)
    cognome = models.CharField(max_length=50)
    email = models.CharField(max_length=254, unique=True)
    codice_fiscale_hash = models.CharField(max_length=64, unique=True, blank=True, null=True)
    data_nascita = models.DateField()
    metodo_registrazione = models.CharField(max_length=11)
    ruolo = models.CharField(max_length=14, db_default="utente")
    stato_account = models.CharField(max_length=18, db_default="in_attesa_verifica")
    quartiere = models.ForeignKey(Quartiere, models.DO_NOTHING, db_column="id_quartiere", blank=True, null=True)
    profilo_pubblico = models.BooleanField(db_default=False)
    mfa_attiva = models.BooleanField(db_default=False)
    mfa_segreto = models.CharField(max_length=255, blank=True, null=True)  # segreto TOTP cifrato (core.services.mfa)
    tentativi_falliti = models.SmallIntegerField(db_default=0)
    bloccato_fino = models.DateTimeField(blank=True, null=True)
    email_verificata_il = models.DateTimeField(blank=True, null=True)
    creato_il = models.DateTimeField(db_default=Now())
    eliminato_il = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UtenteManager()

    class Meta:
        managed = False
        db_table = "utenti"

    def __str__(self):
        return self.nome_pubblico

    # --- permessi derivati dal ruolo (nessun PermissionsMixin) ---
    @property
    def is_active(self):
        return self.stato_account == "attivo"

    @property
    def is_staff(self):
        return self.ruolo in ("moderatore", "amministratore")

    @property
    def is_superuser(self):
        return self.ruolo == "amministratore"

    @property
    def e_moderatore(self):
        return self.is_active and self.ruolo in ("moderatore", "amministratore")

    @property
    def puo_interagire(self):
        return self.stato_account == "attivo"

    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_active and self.is_staff

    @property
    def nome_pubblico(self):
        """Nome con l'iniziale del cognome: è ciò che vede il pubblico."""
        if self.stato_account == "eliminato":
            return "Utente eliminato"
        return f"{self.nome} {self.cognome[:1]}."

    # --- password: hash bcrypt puro, come salvato dal seed ---
    def check_password(self, raw):
        return bool(self.password) and bcrypt.checkpw(raw.encode(), self.password.encode())

    def set_password(self, raw):
        self.password = bcrypt.hashpw(raw.encode(), bcrypt.gensalt(12)).decode()


class Categoria(models.Model):
    id = models.SmallAutoField(primary_key=True)
    nome = models.CharField(max_length=50, unique=True)
    descrizione = models.TextField(blank=True, null=True)
    attiva = models.BooleanField(db_default=True)

    class Meta:
        managed = False
        db_table = "categorie"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Stato(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    nome = models.CharField(max_length=30, unique=True)
    finale = models.BooleanField()
    pubblico = models.BooleanField()

    class Meta:
        managed = False
        db_table = "stati"
        ordering = ["id"]

    def __str__(self):
        return self.nome


# id degli stati (tabella `stati`)
RICEVUTA, IN_ATTESA, APPROVATA, RIFIUTATA, PRESENTATA = 1, 2, 3, 4, 5


class Segnalazione(models.Model):
    id = models.AutoField(primary_key=True)
    autore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_autore", related_name="segnalazioni")
    tipo = models.CharField(max_length=8)
    titolo = models.CharField(max_length=100)
    descrizione = models.TextField()
    latitudine = models.DecimalField(max_digits=9, decimal_places=6)
    longitudine = models.DecimalField(max_digits=9, decimal_places=6)
    indirizzo = models.CharField(max_length=255, blank=True, null=True)
    quartiere = models.ForeignKey(Quartiere, models.DO_NOTHING, db_column="id_quartiere", related_name="segnalazioni")
    stato = models.ForeignKey(Stato, models.DO_NOTHING, db_column="id_stato", db_default=1, related_name="segnalazioni")
    esito_moderazione = models.CharField(max_length=8, blank=True, null=True)
    punteggio_moderazione = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    punteggio_coerenza = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    nascosta = models.BooleanField(db_default=False)
    motivo_nascosta = models.TextField(blank=True, null=True)
    moderatore_nascosta = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_moderatore_nascosta",
                                            blank=True, null=True, related_name="+")
    creata_il = models.DateTimeField(db_default=Now())
    aggiornata_il = models.DateTimeField(blank=True, null=True)
    eliminata_il = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "segnalazioni"
        ordering = ["-creata_il"]

    def __str__(self):
        return self.titolo

    @property
    def e_pubblica(self):
        return self.stato_id in (APPROVATA, PRESENTATA) and not self.nascosta and self.eliminata_il is None

    @property
    def modificabile(self):
        return self.stato_id in (RICEVUTA, IN_ATTESA) and self.eliminata_il is None


class Media(models.Model):
    id = models.AutoField(primary_key=True)
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", related_name="media")
    tipo = models.CharField(max_length=5)
    percorso = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=50)
    dimensione_byte = models.IntegerField()
    durata_sec = models.SmallIntegerField(blank=True, null=True)
    ordine = models.SmallIntegerField()
    copertina = models.BooleanField(db_default=False)
    # `copertina_di` è una colonna generata: non si dichiara, così non viene mai scritta
    exif_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    exif_lon = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    esito_visione = models.CharField(max_length=8, blank=True, null=True)
    punteggio_sessuale = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    punteggio_violenza = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    testo_ocr = models.TextField(blank=True, null=True)
    esito_testo_ocr = models.CharField(max_length=8, blank=True, null=True)
    caricato_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "media"
        ordering = ["ordine"]


class Classificazione(models.Model):
    pk = models.CompositePrimaryKey("segnalazione", "categoria")
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", related_name="classificazioni")
    categoria = models.ForeignKey(Categoria, models.DO_NOTHING, db_column="id_categoria", related_name="classificazioni")
    origine = models.CharField(max_length=10)
    confidenza = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "classificazioni"


class CambioStato(models.Model):
    id = models.AutoField(primary_key=True)
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", related_name="cambi_stato")
    stato_da = models.ForeignKey(Stato, models.DO_NOTHING, db_column="id_stato_da", related_name="+")
    stato_a = models.ForeignKey(Stato, models.DO_NOTHING, db_column="id_stato_a", related_name="+")
    operatore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_operatore", blank=True, null=True, related_name="+")
    nota = models.TextField(blank=True, null=True)
    avvenuto_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "cambi_stato"
        ordering = ["avvenuto_il", "id"]


class Sostegno(models.Model):
    pk = models.CompositePrimaryKey("utente", "segnalazione")
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", related_name="sostegni")
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", related_name="sostegni")
    creato_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "sostegni"


class Commento(models.Model):
    id = models.AutoField(primary_key=True)
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", related_name="commenti")
    autore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_autore", related_name="commenti")
    padre = models.ForeignKey("self", models.DO_NOTHING, db_column="id_padre", blank=True, null=True, related_name="risposte")
    testo = models.CharField(max_length=1000)
    esito_moderazione = models.CharField(max_length=8, blank=True, null=True)
    punteggio_moderazione = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    nascosto = models.BooleanField(db_default=False)
    motivo_nascosto = models.TextField(blank=True, null=True)
    moderatore_nascosto = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_moderatore_nascosto",
                                            blank=True, null=True, related_name="+")
    creato_il = models.DateTimeField(db_default=Now())
    modificato_il = models.DateTimeField(blank=True, null=True)
    eliminato_il = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "commenti"
        ordering = ["creato_il", "id"]


class Candidato(models.Model):
    id = models.SmallAutoField(primary_key=True)
    nome = models.CharField(max_length=50)
    cognome = models.CharField(max_length=50)
    lista = models.CharField(max_length=100)
    email = models.CharField(max_length=254, unique=True)

    class Meta:
        managed = False
        db_table = "candidati"
        ordering = ["cognome", "nome"]

    def __str__(self):
        return f"{self.nome} {self.cognome} ({self.lista})"


class Invio(models.Model):
    id = models.AutoField(primary_key=True)
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", related_name="invii")
    candidato = models.ForeignKey(Candidato, models.DO_NOTHING, db_column="id_candidato", related_name="invii")
    moderatore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_moderatore", related_name="+")
    inviato_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "invii"


class DocumentoNormativo(models.Model):
    id = models.SmallAutoField(primary_key=True)
    tipo = models.CharField(max_length=30)
    versione = models.CharField(max_length=20)
    testo = models.TextField()
    pubblicato_il = models.DateTimeField(db_default=Now())
    amministratore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_amministratore", related_name="+")

    class Meta:
        managed = False
        db_table = "documenti_normativi"
        ordering = ["id"]


class Consenso(models.Model):
    pk = models.CompositePrimaryKey("utente", "documento")
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", related_name="consensi")
    documento = models.ForeignKey(DocumentoNormativo, models.DO_NOTHING, db_column="id_documento", related_name="consensi")
    accettato_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "consensi"


class VerificaIdentita(models.Model):
    id = models.AutoField(primary_key=True)
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", related_name="verifiche")
    tentativo = models.SmallIntegerField()
    tipo_documento = models.CharField(max_length=14)
    ok_lettura_ocr = models.BooleanField()
    ok_corrispondenza_dati = models.BooleanField()
    ok_validita = models.BooleanField()
    ok_autenticita = models.BooleanField()
    ok_confronto_volto = models.BooleanField()
    punteggio = models.SmallIntegerField()
    esito_ia = models.CharField(max_length=11)
    motivo = models.TextField(blank=True, null=True)
    revisore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_revisore", blank=True, null=True, related_name="+")
    esito_finale = models.CharField(max_length=11, blank=True, null=True)
    motivo_revisione = models.TextField(blank=True, null=True)
    revisionata_il = models.DateTimeField(blank=True, null=True)
    creata_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "verifiche_identita"
        ordering = ["creata_il"]


class Notifica(models.Model):
    id = models.BigAutoField(primary_key=True)
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", related_name="notifiche")
    tipo = models.CharField(max_length=30)
    messaggio = models.CharField(max_length=500)
    link = models.CharField(max_length=500, blank=True, null=True)
    letta = models.BooleanField(db_default=False)
    creata_il = models.DateTimeField(db_default=Now())

    class Meta:
        managed = False
        db_table = "notifiche"
        ordering = ["-creata_il"]


class LogAttivita(models.Model):
    id = models.BigAutoField(primary_key=True)
    avvenuto_il = models.DateTimeField(db_default=Now())
    attore = models.CharField(max_length=7)
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", blank=True, null=True, related_name="+")
    operazione = models.CharField(max_length=30)
    tabella = models.CharField(max_length=50)
    id_oggetto = models.BigIntegerField()
    dati_precedenti = models.JSONField(blank=True, null=True)
    dati_nuovi = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "log_attivita"


class RichiestaRevisione(models.Model):
    """L'utente chiede a un moderatore di rivedere un contenuto bloccato o una verifica rifiutata.
    Esattamente uno tra segnalazione, commento, verifica è valorizzato (CHECK nel DB)."""
    id = models.AutoField(primary_key=True)
    richiedente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_richiedente", related_name="richieste")
    segnalazione = models.ForeignKey(Segnalazione, models.DO_NOTHING, db_column="id_segnalazione", blank=True, null=True, related_name="richieste")
    commento = models.ForeignKey(Commento, models.DO_NOTHING, db_column="id_commento", blank=True, null=True, related_name="richieste")
    verifica = models.ForeignKey(VerificaIdentita, models.DO_NOTHING, db_column="id_verifica", blank=True, null=True, related_name="richieste")
    motivo = models.TextField()
    stato = models.CharField(max_length=8, db_default="aperta")
    moderatore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_moderatore", blank=True, null=True, related_name="+")
    risposta = models.TextField(blank=True, null=True)
    creata_il = models.DateTimeField(db_default=Now())
    chiusa_il = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "richieste_revisione"
        ordering = ["creata_il"]


class Sospensione(models.Model):
    id = models.AutoField(primary_key=True)
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", related_name="sospensioni")
    moderatore = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_moderatore", related_name="+")
    motivo = models.TextField()
    inizio = models.DateTimeField(db_default=Now())
    fine = models.DateTimeField(blank=True, null=True)
    revocata_il = models.DateTimeField(blank=True, null=True)
    revocante = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_revocante", blank=True, null=True, related_name="+")

    class Meta:
        managed = False
        db_table = "sospensioni"
        ordering = ["-inizio"]


class PreferenzaNotifica(models.Model):
    pk = models.CompositePrimaryKey("utente", "tipo")
    utente = models.ForeignKey(Utente, models.DO_NOTHING, db_column="id_utente", related_name="preferenze")
    tipo = models.CharField(max_length=30)
    in_app = models.BooleanField(db_default=True)
    email = models.BooleanField(db_default=False)

    class Meta:
        managed = False
        db_table = "preferenze_notifica"
