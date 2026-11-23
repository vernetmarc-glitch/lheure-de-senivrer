"""Planche du chantier S7 : chantiers/planches/alpes-<n>.png.

Ligne 1 : la page servie (390 × 844) à plusieurs instants. Ligne 2 : le dernier état vu
du zénith (règles de couleur seules, puis tel qu'affiché) à côté de la référence
(relief réel Copernicus ombré, drapé de la mosaïque Sentinel-2 sans nuages).
Usage : python3 app/public/labo/alpes/planche.py chantiers/planches/alpes-1.png
"""
import io, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import controles as C

INSTANTS = [(-40, "−40 Ma"), (-25, "−25 Ma"), (-12, "−12 Ma"), (-4, "−4 Ma"), (-1, "−1 Ma"), (0, "aujourd'hui")]


def police(t):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        try:
            return ImageFont.truetype(f, t)
        except OSError:
            pass
    return ImageFont.load_default()


def main(sortie):
    from playwright.sync_api import sync_playwright
    srv, base = C.servir()
    meta = json.loads(C.lire(base + "donnees/meta.json"))
    n = meta["n"]
    vues, nadir = [], []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                 args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                       "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg.goto(base)
        pg.wait_for_function("window.ALPES && window.ALPES.pret", timeout=180000)
        pg.evaluate("window.ALPES.pause()")
        for t, _ in INSTANTS:
            pg.evaluate(f"window.ALPES.aller({t})")
            pg.wait_for_timeout(1600)
            vues.append(Image.open(io.BytesIO(pg.screenshot())).convert("RGB").resize((390, 844), Image.LANCZOS))
        for mode, mos in ((3, 0), (3, "undefined")):
            px = np.array(pg.evaluate(f"Array.from(window.ALPES.couleurs(0, {mode}, {mos}))"), np.uint8).reshape(n, n, 3)
            nadir.append(Image.fromarray(px))
        nav.close()
    # référence : DEM ombré drapé de la mosaïque
    reel = np.frombuffer(C.gzip.decompress(C.lire(base + "donnees/reel_1024.bin.gz")), "<u2").astype(float)
    reel = (reel * meta["h_pas_m"] + meta["h_zero_m"]).reshape(1024, 1024)
    mos = np.asarray(Image.open(io.BytesIO(C.lire(base + "donnees/mosaique_2048.jpg"))).convert("RGB"), float)
    mos = mos.reshape(1024, 2, 1024, 2, 3).mean(axis=(1, 3))
    gy, gx = np.gradient(reel * 1.5, 200.0)
    az, el = np.radians(145), np.radians(34)
    L = np.array([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])
    sh = (-gx * L[0] + gy * L[1] + L[2]) / np.sqrt(gx ** 2 + gy ** 2 + 1)
    lin = (mos / 255) ** 2.2
    ref = lin * (1.9 * np.clip(sh, 0, 1)[..., None] * np.array([1, .95, .86]) + 0.5 * np.array([.42, .52, .68]))
    ref = Image.fromarray((np.clip(ref, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8))

    W = 390 * 6
    plan = Image.new("RGB", (W, 844 + 60 + 420 + 50), (14, 18, 26))
    d = ImageDraw.Draw(plan)
    for i, (im, (_, lab)) in enumerate(zip(vues, INSTANTS)):
        plan.paste(im, (390 * i, 40))
        d.text((390 * i + 12, 8), lab, font=police(22), fill=(243, 239, 230))
    y = 844 + 60
    titres = ["dernier état — règles de couleur seules", "dernier état — tel qu'affiché",
              "référence — Copernicus DEM + Sentinel-2"]
    for i, im in enumerate(nadir + [ref]):
        x = 60 + i * 760
        plan.paste(im.resize((420, 420), Image.LANCZOS), (x, y + 30))
        d.text((x, y), titres[i], font=police(20), fill=(243, 239, 230))
    srv.shutdown()
    plan.save(sortie)
    print("planche :", sortie)


if __name__ == "__main__":
    main(sys.argv[1])
