"""Caricamento di foto e video: formati, limiti, metadati, atomicità, archivio nel database, modifica, file demo."""
import io, os, sys, glob, shutil, subprocess, tempfile, datetime, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.chdir(sys.path[0]); os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup()
from pathlib import Path
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.utils import timezone
from PIL import Image
from core.models import *
def esito(n, c, e=""): print(("OK  " if c else "!!  ")+n+(f"  [{e}]" if e else ""))
MEDIA = Path(settings.MEDIA_ROOT) / "media"
TMP = Path(tempfile.mkdtemp(prefix="prova_media_"))
def file_su_disco(): return {p for p in glob.glob(str(MEDIA / "**" / "*"), recursive=True) if os.path.isfile(p)}
def righe_archivio():
    with connection.cursor() as cur: cur.execute("SELECT COUNT(*) FROM media_contenuti"); return cur.fetchone()[0]
def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)
def jpeg(w=800, h=600, exif=False, orient=None, nome="foto.jpg"):
    im = Image.new("RGB", (w, h), (90, 140, 200)); b = io.BytesIO()
    if exif:
        e = Image.Exif(); e[0x010F] = "MarcaTelefono"; e[0x0110] = "ModelloX"
        if orient: e[0x0112] = orient
        e.get_ifd(0x8825)[1] = "N"; e.get_ifd(0x8825)[2] = (45.0, 27.0, 50.0); e.get_ifd(0x8825)[3] = "E"; e.get_ifd(0x8825)[4] = (9.0, 11.0, 24.0)
        im.save(b, "JPEG", exif=e)
    else: im.save(b, "JPEG")
    return SimpleUploadedFile(nome, b.getvalue(), content_type="image/jpeg")
def png(w=400, h=300, nome="foto.png"):
    b = io.BytesIO(); Image.new("RGBA", (w, h), (200, 80, 60, 180)).save(b, "PNG"); return SimpleUploadedFile(nome, b.getvalue(), content_type="image/png")
def heic(nome="foto.heic"):
    import pillow_heif; pillow_heif.register_heif_opener()
    b = io.BytesIO(); Image.new("RGB", (500, 400), (60, 160, 90)).save(b, "HEIF"); return SimpleUploadedFile(nome, b.getvalue(), content_type="image/heic")
def video(nome="v.mp4", secondi=3, metadati=True, **k):
    p = TMP / nome; est = p.suffix
    arg = ["-f", "lavfi", "-i", f"testsrc=size=320x240:rate={k.get('fps', 10)}", "-t", str(secondi), "-pix_fmt", "yuv420p"]
    if metadati: arg += ["-metadata", "location=+45.4642+009.1900/", "-metadata", "title=Prova GPS"]
    ff(*arg, str(p)); return SimpleUploadedFile(nome, p.read_bytes(), content_type="video/mp4" if est == ".mp4" else "video/quicktime")
def solo_audio(nome="audio.mp4"):
    p = TMP / nome; ff("-f", "lavfi", "-i", "sine=frequency=440", "-t", "3", str(p)); return SimpleUploadedFile(nome, p.read_bytes(), content_type="video/mp4")
def tags(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.lower()
    return "prova gps" in out or "45.4642" in out

# --- utenti verificati e senza segnalazioni di oggi (il limite è 5 al giorno)
oggi = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
utenti = [u for u in Utente.objects.filter(ruolo="utente", stato_account="attivo", id__lte=154).order_by("id") if u.identita_verificata and not Segnalazione.objects.filter(autore=u, creata_il__gte=oggi).exists()][:6]
esito("ci sono utenti verificati con cui provare", len(utenti) >= 4)
cat = Categoria.objects.filter(attiva=True).first()
def invia(c, files, titolo="Prova di caricamento", lat="45.4642", lon="9.1900"):
    dati = {"tipo": "problema", "titolo": titolo, "descrizione": "Segnalazione di prova per verificare il caricamento di foto e video nel sistema.", "categorie": [cat.id], "latitudine": lat, "longitudine": lon, "indirizzo": "Via Prova 1"}
    if files: dati["media"] = files
    return c.post("/segnalazioni/nuova/", dati)
def cliente(u): c = Client(); c.force_login(u, backend="core.backends.UtenteBackend"); return c
def ultima(u): return Segnalazione.objects.filter(autore=u).order_by("-id").first()
creati = []

# --- foto: EXIF, rotazione, riduzione
u = utenti[0]; c = cliente(u)
prima = file_su_disco(); arch0 = righe_archivio()
r = invia(c, [jpeg(800, 600, exif=True, orient=6, nome="gps.jpg"), jpeg(5000, 3500, nome="grande.jpg"), png(), heic()])
s = ultima(u); creati.append(s)
esito("foto JPG con EXIF, grande, PNG e HEIC: segnalazione creata", r.status_code == 302 and s is not None and s.media.count() == 4, f"{r.status_code}")
m = list(s.media.order_by("ordine")); f0 = MEDIA.parent / m[0].percorso
im0 = Image.open(f0)
esito("EXIF e GPS rimossi", not im0.getexif() and "exif" not in im0.info)
esito("la rotazione dell'EXIF è applicata (800x600 con orientamento 6 → 600x800)", im0.size == (600, 800), str(im0.size))
esito("la foto da 5000x3500 è ridotta (lato massimo 2400)", max(Image.open(MEDIA.parent / m[1].percorso).size) <= 2400)
esito("il PNG resta PNG, l'HEIC diventa JPEG", m[2].percorso.endswith(".png") and m[3].percorso.endswith(".jpg") and m[3].mime_type == "image/jpeg")
esito("la prima foto è la copertina, una sola", [x.copertina for x in m] == [True, False, False, False])
esito("i file sono sul disco e copiati nel database", all((MEDIA.parent / x.percorso).is_file() for x in m) and righe_archivio() >= arch0 + 4)
r = Client().get("/media/" + m[0].percorso.split("media/", 1)[1]); esito("il file si serve (200, image/jpeg)", r.status_code == 200 and r["Content-Type"] == "image/jpeg")
# --- ripristino dal database
p = MEDIA.parent / m[2].percorso; p.unlink()
r = Client().get("/media/" + m[2].percorso.split("media/", 1)[1]); esito("se il file manca dal disco si ripristina dal database", r.status_code == 200 and p.is_file() and len(b"".join(r.streaming_content)) > 100)

# --- video
u = utenti[1]; c = cliente(u)
r = invia(c, [video("ok.mp4"), video("ok.mov")]); s = ultima(u); creati.append(s)
esito("video MP4 e MOV: segnalazione creata", r.status_code == 302 and s.media.count() == 2 and all(x.tipo == "video" for x in s.media.all()), f"{r.status_code}")
mv = list(s.media.order_by("ordine"))
esito("durata registrata (3 s) e file sul disco", all(x.durata_sec in (2, 3, 4) and (MEDIA.parent / x.percorso).is_file() for x in mv), str([x.durata_sec for x in mv]))
esito("i metadati del video (GPS, titolo) sono rimossi", all(not tags(MEDIA.parent / x.percorso) for x in mv))
r = Client().get("/media/" + mv[0].percorso.split("media/", 1)[1]); esito("il video si serve", r.status_code == 200)

# --- rifiuti: nessuna segnalazione, nessun file rimasto, nessuna riga nell'archivio
def rifiutato(nome, files, atteso=None, **k):
    u2 = k.pop("u"); c2 = cliente(u2); prima = file_su_disco(); n0 = Segnalazione.objects.filter(autore=u2).count(); a0 = righe_archivio()
    r = invia(c2, files, **k); testo = r.content.decode()
    pulito = file_su_disco() == prima and righe_archivio() == a0 and Segnalazione.objects.filter(autore=u2).count() == n0
    esito(nome, r.status_code == 200 and pulito and (atteso is None or atteso in testo), f"{r.status_code} {'pulito' if pulito else 'RESTANO FILE O RIGHE'}")
u = utenti[2]
rifiutato("nessun allegato: rifiutato", [], "Allega", u=u)
rifiutato("11 file: rifiutato", [jpeg(nome=f"{i}.jpg") for i in range(11)], "da 1 a 10", u=u)
rifiutato("un eseguibile travestito da .jpg", [SimpleUploadedFile("x.jpg", b"MZ\x90\x00 eseguibile", content_type="image/jpeg")], "immagine non valida", u=u)
rifiutato("un file di testo .png", [SimpleUploadedFile("x.png", b"solo testo", content_type="image/png")], "immagine non valida", u=u)
rifiutato("formato non ammesso (.gif)", [SimpleUploadedFile("a.gif", b"GIF89a....", content_type="image/gif")], "formato non ammesso", u=u)
rifiutato("estensione pericolosa (.exe)", [SimpleUploadedFile("a.exe", b"MZ....", content_type="application/octet-stream")], "formato non ammesso", u=u)
rifiutato("file vuoto", [SimpleUploadedFile("vuoto.jpg", b"", content_type="image/jpeg")], u=u)
rifiutato("foto oltre 10 MB", [SimpleUploadedFile("g.jpg", b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 + 10), content_type="image/jpeg")], "10 MB", u=u)
rifiutato("video oltre 50 MB", [SimpleUploadedFile("g.mp4", b"0" * (50 * 1024 * 1024 + 10), content_type="video/mp4")], "50 MB", u=u)
rifiutato("video oltre 60 secondi", [video("lungo.mp4", secondi=62, metadati=False, fps=1)], "60 secondi", u=u)
rifiutato("un .mp4 che contiene solo audio", [solo_audio()], "non è un video valido", u=u)
rifiutato("un .mp4 finto", [SimpleUploadedFile("finto.mp4", b"non sono un video", content_type="video/mp4")], u=u)
enorme = io.BytesIO(); Image.new("L", (9000, 9000), 255).save(enorme, "PNG")
rifiutato("immagine da 81 megapixel (troppo grande da elaborare)", [SimpleUploadedFile("enorme.png", enorme.getvalue(), content_type="image/png")], "troppo grande", u=u)
rifiutato("buona + cattiva: non resta nulla della buona", [jpeg(nome="buona.jpg"), SimpleUploadedFile("cattiva.jpg", b"xxxx", content_type="image/jpeg")], u=u)
rifiutato("fuori dal Comune di Milano: i file non restano", [jpeg()], "fuori dal Comune", u=u, lat="45.0", lon="9.0")
r = cliente(u).post("/segnalazioni/nuova/", {"tipo": "problema", "titolo": "x" * 101, "descrizione": "corta", "categorie": [cat.id], "latitudine": "45.46", "longitudine": "9.19", "media": [jpeg()]})
esito("titolo troppo lungo e descrizione corta: errore del modulo, niente file", r.status_code == 200 and file_su_disco() == file_su_disco())

# --- modifica: aggiungere e togliere file
u = utenti[3]; c = cliente(u)
invia(c, [jpeg(nome="a.jpg"), jpeg(nome="b.jpg")]); s = ultima(u); creati.append(s)
vecchi = list(s.media.order_by("ordine")); da_togliere = vecchi[1]
dati = {"tipo": "problema", "titolo": "Prova di caricamento", "descrizione": "Segnalazione di prova per verificare il caricamento di foto e video nel sistema.", "categorie": [cat.id], "latitudine": "45.4642", "longitudine": "9.1900", "rimuovi_media": [da_togliere.id], "media": [png(nome="nuova.png")]}
r = c.post(f"/segnalazioni/{s.id}/modifica/", dati); s.refresh_from_db(); nuovi = list(s.media.order_by("ordine"))
esito("modifica: un file tolto e uno aggiunto", r.status_code == 302 and len(nuovi) == 2 and da_togliere.id not in [x.id for x in nuovi], f"{r.status_code} {len(nuovi)}")
with connection.cursor() as cur: cur.execute("SELECT COUNT(*) FROM media_contenuti WHERE percorso=%s", [da_togliere.percorso]); in_arch = cur.fetchone()[0]
esito("il file tolto sparisce dal disco e dall'archivio", not (MEDIA.parent / da_togliere.percorso).exists() and in_arch == 0)
esito("dopo la modifica c'è sempre una sola copertina", [x.copertina for x in nuovi].count(True) == 1)
dati["rimuovi_media"] = [x.id for x in nuovi]; dati.pop("media"); n_file = len(file_su_disco())
r = c.post(f"/segnalazioni/{s.id}/modifica/", dati); esito("non si può togliere l'ultimo file (serve almeno un media)", r.status_code == 200 and s.media.count() == 2 and len(file_su_disco()) == n_file)

# --- file demo e percorsi pericolosi
r = Client().get("/media/demo/1.jpg"); esito("un media demo mostra un'immagine di esempio vera", r.status_code == 200 and r["Content-Type"] == "image/jpeg" and len(b"".join(r.streaming_content)) > 5000)
vid = Media.objects.filter(tipo="video", percorso__startswith="media/demo/").first()
if vid: r = Client().get("/media/" + vid.percorso.split("media/", 1)[1]); esito("un video demo mostra un video di esempio vero", r.status_code == 200 and r["Content-Type"] == "video/mp4")
esito("il percorso /media/../../etc/passwd non esce dalla cartella", Client().get("/media/../../../../etc/passwd").status_code in (301, 400, 404))
esito("un file che non esiste → 404", Client().get("/media/2020/01/non-esiste.jpg").status_code == 404)

# --- pulizia delle segnalazioni di prova (eliminazione logica) e dei file di questa prova
for s in creati:
    for x in s.media.all(): servizio = __import__("core.services.media", fromlist=["x"]); servizio.rimuovi(x.percorso)
shutil.rmtree(TMP, ignore_errors=True)
