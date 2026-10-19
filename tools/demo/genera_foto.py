"""Genera le immagini e i video di ESEMPIO dei dati demo: scene di quartiere disegnate al computer (non sono fotografie reali).
Uscita: apps/web/static/demo/<categoria>/NN.jpg e apps/web/static/demo/video/NN.mp4. Uso: tools/.venv/bin/python tools/demo/genera_foto.py"""
import math, pathlib, random, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageChops

RADICE = pathlib.Path(__file__).resolve().parents[2]
USCITA = RADICE / "apps" / "web" / "static" / "demo"
L, A = 1200, 750
PER_CATEGORIA = 8
CATEGORIE = ["ambiente", "mobilita-urbana", "politiche-giovanili", "decoro-urbano", "sicurezza-del-territorio"]

CIELI = [((196, 214, 228), (236, 240, 242)), ((170, 190, 205), (214, 222, 228)), ((236, 196, 160), (250, 232, 205)), ((120, 140, 168), (196, 206, 222))]
FACCIATE = [(204, 190, 170), (186, 170, 150), (214, 205, 190), (170, 160, 150), (196, 176, 158), (160, 168, 172), (222, 208, 184)]


def gradiente(img, alto, basso, y0, y1):
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0)
        d.line([(0, y), (L, y)], fill=tuple(int(alto[i] + (basso[i] - alto[i]) * t) for i in range(3)))


def edifici(d, r, orizzonte, notte=False):
    x = -40
    while x < L:
        w = r.randint(110, 230); h = r.randint(160, 330); col = r.choice(FACCIATE)
        if notte: col = tuple(int(c * .38) for c in col)
        d.rectangle([x, orizzonte - h, x + w, orizzonte], fill=col)
        d.rectangle([x, orizzonte - h, x + w, orizzonte - h + 10], fill=tuple(max(0, c - 28) for c in col))
        for fy in range(orizzonte - h + 34, orizzonte - 40, 46):
            for fx in range(x + 18, x + w - 30, 40):
                acceso = notte and r.random() < .45
                d.rectangle([fx, fy, fx + 22, fy + 30], fill=(255, 214, 120) if acceso else (74, 88, 104))
                d.line([(fx + 11, fy), (fx + 11, fy + 30)], fill=(col if not acceso else (255, 236, 180)), width=2)
        x += w - r.randint(0, 24)


def strada(d, orizzonte, tono=(92, 94, 96)):
    d.rectangle([0, orizzonte, L, A], fill=tono)
    d.rectangle([0, orizzonte, L, orizzonte + 64], fill=(176, 172, 164))   # marciapiede
    d.line([(0, orizzonte + 64), (L, orizzonte + 64)], fill=(120, 118, 112), width=5)
    for x in range(0, L, 180):
        d.line([(x, orizzonte + 64), (x + 60, orizzonte + 64)], fill=(150, 148, 142), width=2)


def albero(d, x, base, r, scala=1.0, sec=False):
    d.rectangle([x - 7 * scala, base - 120 * scala, x + 7 * scala, base], fill=(84, 64, 46))
    for dx, dy, rr in [(0, -150, 58), (-40, -118, 44), (40, -120, 46), (0, -100, 52)]:
        col = (76 + r.randint(-8, 8), 124 + r.randint(-10, 10), 70) if not sec else (150, 130, 70)
        d.ellipse([x + dx * scala - rr * scala, base + dy * scala - rr * scala, x + dx * scala + rr * scala, base + dy * scala + rr * scala], fill=col)


def cassonetto(d, x, base, colore, pieno=True, r=None):
    d.rectangle([x, base - 96, x + 78, base], fill=colore)
    d.rectangle([x - 5, base - 108, x + 83, base - 94], fill=tuple(max(0, c - 30) for c in colore))
    d.ellipse([x + 4, base - 12, x + 22, base + 4], fill=(30, 30, 30)); d.ellipse([x + 56, base - 12, x + 74, base + 4], fill=(30, 30, 30))
    if pieno and r:
        for _ in range(7):
            sx, sy = x + r.randint(-26, 88), base - r.randint(84, 130)
            d.ellipse([sx, sy, sx + r.randint(30, 52), sy + r.randint(26, 40)], fill=r.choice([(40, 44, 48), (200, 198, 190), (90, 120, 150), (170, 120, 80)]))
        for _ in range(9):   # sacchi e rifiuti a terra
            sx, sy = x + r.randint(-90, 150), base + r.randint(-4, 20)
            d.ellipse([sx, sy, sx + r.randint(30, 60), sy + r.randint(20, 36)], fill=r.choice([(36, 40, 44), (196, 194, 186), (84, 112, 140)]))


def semaforo(d, x, base, r, spento=False):
    d.rectangle([x - 5, base - 260, x + 5, base], fill=(60, 62, 64))
    d.rectangle([x - 20, base - 300, x + 20, base - 240], fill=(36, 38, 40))
    cols = [(90, 30, 30), (90, 80, 30), (30, 90, 50)]
    i = r.randint(0, 2)
    for k, c in enumerate(cols):
        acc = (230, 60, 50) if k == 0 else (240, 190, 40) if k == 1 else (60, 200, 100)
        d.ellipse([x - 11, base - 296 + k * 18, x + 11, base - 276 + k * 18], fill=(c if (spento or k != i) else acc))


def lampione(d, x, base, acceso, notte):
    d.rectangle([x - 4, base - 280, x + 4, base], fill=(54, 56, 58)); d.rectangle([x - 4, base - 280, x + 56, base - 272], fill=(54, 56, 58))
    d.ellipse([x + 36, base - 276, x + 70, base - 256], fill=(255, 240, 190) if acceso else (110, 110, 112))
    return acceso and notte


def luce_notte(img, x, y, raggio):
    alone = Image.new("RGB", (L, A), (0, 0, 0)); d = ImageDraw.Draw(alone)
    d.ellipse([x - raggio, y - raggio, x + raggio, y + raggio], fill=(120, 100, 50))
    alone = alone.filter(ImageFilter.GaussianBlur(raggio / 2))
    return ImageChops.add(img, alone)


def bici_pista(d, orizzonte, r):
    y = orizzonte + 200
    d.polygon([(0, y), (L, y - 20), (L, y + 80), (0, y + 110)], fill=(190, 70, 60))
    for x in range(40, L, 140): d.rectangle([x, y + 38 - x // 60, x + 70, y + 46 - x // 60], fill=(240, 240, 236))
    bx = r.randint(300, 900); by = y + 30
    for cx in (bx, bx + 70): d.ellipse([cx - 28, by, cx + 28, by + 56], outline=(30, 30, 30), width=5)
    d.line([(bx, by + 28), (bx + 34, by - 20), (bx + 70, by + 28)], fill=(30, 30, 34), width=5); d.line([(bx + 34, by - 20), (bx + 44, by - 36)], fill=(30, 30, 34), width=5)


def strisce(d, orizzonte, r):
    y = orizzonte + 130
    for x in range(100, 1100, 54): d.polygon([(x, y), (x + 36, y), (x + 44, y + 120), (x - 8, y + 120)], fill=(236, 236, 230))


def campetto(d, orizzonte, r, scrostato=True):
    d.rectangle([0, orizzonte, L, A], fill=(150, 90, 70))
    d.rectangle([90, orizzonte + 60, L - 90, A - 40], outline=(238, 238, 232), width=6)
    d.line([(L / 2, orizzonte + 60), (L / 2, A - 40)], fill=(238, 238, 232), width=6)
    d.ellipse([L / 2 - 80, (orizzonte + A) / 2 - 40, L / 2 + 80, (orizzonte + A) / 2 + 40], outline=(238, 238, 232), width=6)
    d.rectangle([60, orizzonte - 130, 70, orizzonte + 60], fill=(70, 72, 74)); d.rectangle([60, orizzonte - 130, 118, orizzonte - 118], fill=(70, 72, 74))
    d.ellipse([84, orizzonte - 110, 124, orizzonte - 96], outline=(220, 90, 40), width=4)
    if scrostato:
        for _ in range(38):
            x, y = r.randint(110, L - 110), r.randint(orizzonte + 70, A - 50)
            d.ellipse([x, y, x + r.randint(14, 40), y + r.randint(8, 20)], fill=(120, 78, 62))
    for x in range(0, L, 28): d.line([(x, orizzonte - 110), (x, orizzonte + 40)], fill=(96, 100, 104), width=2)   # recinzione
    for y in range(orizzonte - 110, orizzonte + 40, 26): d.line([(0, y), (L, y)], fill=(96, 100, 104), width=2)


def muro_graffiti(d, orizzonte, r):
    d.rectangle([0, 0, L, orizzonte + 40], fill=(196, 190, 180))
    for y in range(40, orizzonte + 40, 70): d.line([(0, y), (L, y)], fill=(180, 174, 164), width=2)
    for _ in range(9):
        col = r.choice([(220, 60, 60), (40, 120, 200), (240, 190, 40), (60, 170, 110), (150, 70, 170), (30, 30, 34)])
        x, y = r.randint(40, L - 300), r.randint(60, 340)
        pts = [(x + i * 30, y + math.sin(i * 1.3 + r.random()) * r.randint(14, 40)) for i in range(r.randint(5, 9))]
        d.line(pts, fill=col, width=r.randint(10, 18), joint="curve")


def panchina(d, x, base, rotta=False):
    d.rectangle([x, base - 64, x + 180, base - 52], fill=(150, 110, 70)); d.rectangle([x, base - 100, x + 180, base - 88], fill=(150, 110, 70))
    d.rectangle([x + 14, base - 52, x + 24, base], fill=(60, 60, 62)); d.rectangle([x + 156, base - 52, x + 166, base], fill=(60, 60, 62))
    if rotta:
        d.polygon([(x + 70, base - 64), (x + 120, base - 64), (x + 110, base - 30), (x + 76, base - 40)], fill=(150, 110, 70))
        d.line([(x + 82, base - 88), (x + 96, base - 100)], fill=(196, 190, 180), width=14)


def sottopasso(d, orizzonte, r):
    d.rectangle([0, 0, L, A], fill=(40, 44, 50)); d.rectangle([240, 150, 960, A], fill=(14, 16, 20))
    d.polygon([(240, 150), (960, 150), (860, 300), (340, 300)], fill=(26, 30, 36))
    for x in (400, 600, 800): d.rectangle([x, 160, x + 60, 176], fill=(70, 70, 66))
    d.rectangle([0, A - 160, L, A], fill=(52, 54, 56)); d.line([(0, A - 160), (L, A - 160)], fill=(110, 110, 106), width=6)


def scena(categoria, seme):
    r = random.Random(f"{categoria}-{seme}")
    notte = categoria == "sicurezza-del-territorio" and seme % 2 == 0
    alto, basso = ((22, 28, 48), (52, 60, 88)) if notte else r.choice(CIELI)
    img = Image.new("RGB", (L, A)); gradiente(img, alto, basso, 0, A)
    d = ImageDraw.Draw(img)
    orizzonte = r.randint(430, 480)
    if categoria == "politiche-giovanili":
        edifici(d, r, orizzonte - 40); campetto(d, orizzonte, r, scrostato=seme % 3 != 0)
    elif categoria == "decoro-urbano" and seme % 2 == 0:
        muro_graffiti(d, orizzonte, r); strada(d, orizzonte + 60); panchina(d, r.randint(120, 760), orizzonte + 120, rotta=seme % 4 == 0)
    elif categoria == "sicurezza-del-territorio" and seme % 4 == 1:
        sottopasso(d, orizzonte, r)
    else:
        edifici(d, r, orizzonte, notte); strada(d, orizzonte)
        albero(d, r.randint(80, 320), orizzonte + 70, r, 1.0, sec=seme % 3 == 1); albero(d, r.randint(760, 1120), orizzonte + 70, r, .9)
        if categoria == "ambiente":
            for k in range(3): cassonetto(d, 200 + k * 140 + r.randint(-20, 20), orizzonte + 120, r.choice([(52, 120, 70), (60, 98, 150), (200, 180, 60)]), pieno=True, r=r)
            for _ in range(22):
                sx, sy = r.randint(80, 1100), r.randint(orizzonte + 100, A - 30); d.ellipse([sx, sy, sx + r.randint(10, 28), sy + r.randint(8, 18)], fill=r.choice([(220, 220, 214), (60, 64, 70), (200, 80, 60)]))
        elif categoria == "mobilita-urbana":
            if seme % 2: bici_pista(d, orizzonte, r)
            else: strisce(d, orizzonte, r)
            semaforo(d, r.randint(120, 1080), orizzonte + 68, r, spento=seme % 3 == 0)
        elif categoria == "decoro-urbano":
            panchina(d, r.randint(120, 800), orizzonte + 130, rotta=True)
            for _ in range(14): x = r.randint(60, 1140); d.rectangle([x, orizzonte + 70, x + 18, orizzonte + 82], fill=(130, 140, 90))
        elif categoria == "sicurezza-del-territorio":
            strisce(d, orizzonte, r)
            for k in range(3): lampione(d, 160 + k * 380 + r.randint(-30, 30), orizzonte + 70, acceso=(k != 1), notte=notte)
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    if notte:
        for x in (200, 960): img = luce_notte(img, x + 50, orizzonte - 120, 190)
    # grana e vignettatura per un aspetto fotografico
    rumore = Image.effect_noise((L, A), 14).convert("RGB"); img = Image.blend(img, ImageChops.overlay(img, rumore), .22)
    v = Image.new("L", (L, A), 0); ImageDraw.Draw(v).ellipse([-260, -200, L + 260, A + 200], fill=255); v = v.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(img, Image.new("RGB", (L, A), (20, 22, 26)), v)


def main():
    for c in CATEGORIE:
        cartella = USCITA / c; cartella.mkdir(parents=True, exist_ok=True)
        for i in range(PER_CATEGORIA):
            scena(c, i).save(cartella / f"{i:02d}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
    cartella_v = USCITA / "video"; cartella_v.mkdir(parents=True, exist_ok=True)
    for i, (c, n) in enumerate([("ambiente", 0), ("mobilita-urbana", 1), ("decoro-urbano", 2), ("sicurezza-del-territorio", 3)]):
        sorgente = USCITA / c / f"{n:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(sorgente), "-t", "4", "-vf",
                        "scale=1280:-2,zoompan=z='min(zoom+0.0015,1.25)':d=100:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x400:fps=25,format=yuv420p",
                        "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", "-movflags", "+faststart", "-an", str(cartella_v / f"{i:02d}.mp4")], check=True)
    tot = sum(f.stat().st_size for f in USCITA.rglob("*") if f.is_file())
    print(f"{PER_CATEGORIA * len(CATEGORIE)} immagini e 4 video, {tot / 1e6:.1f} MB in {USCITA}")


main()
