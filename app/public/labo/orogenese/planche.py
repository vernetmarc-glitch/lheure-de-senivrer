"""Planche du chantier S7b : chantiers/planches/orogenese-<n>.png.

La page servie (390 × 844) à six instants, puis la coupe Grenoble–Turin à trois instants.
Usage : python3 app/public/labo/orogenese/planche.py chantiers/planches/orogenese-1.png
"""
import io, sys
from PIL import Image, ImageDraw, ImageFont
import controles as C

INSTANTS = [-84, -60, -42, -30, -15, 0]
COUPES = [-60, -35, -15]


def police(t):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", t)
    except OSError:
        return ImageFont.load_default()


def main(sortie):
    from playwright.sync_api import sync_playwright
    srv, base = C.servir()
    vues, coupes = [], []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg.goto(base + "?essai")
        pg.wait_for_function("window.OROGENESE && window.OROGENESE.pret", timeout=120000)
        for t in INSTANTS:
            pg.evaluate(f"window.OROGENESE.aller({t})")
            pg.wait_for_timeout(700)
            vues.append(Image.open(io.BytesIO(pg.screenshot())).convert("RGB").resize((390, 844), Image.LANCZOS))
        pg.click("#bcoupe")
        for t in COUPES:
            pg.evaluate(f"window.OROGENESE.aller({t})")
            pg.wait_for_timeout(400)
            im = Image.open(io.BytesIO(pg.locator("#panneau").screenshot())).convert("RGB")
            coupes.append(im.resize((780, int(780 * im.height / im.width)), Image.LANCZOS))
        nav.close()
    srv.shutdown()
    hc = max(c.height for c in coupes)
    W, H = 6 * 400 + 20, 30 + 844 + 40 + hc + 40
    P = Image.new("RGB", (W, H), (4, 5, 10))
    d = ImageDraw.Draw(P)
    d.text((14, 6), "S7b — orogenèse géodynamique : page servie (390 × 844) et coupe Grenoble–Turin", fill=(230, 230, 220), font=police(18))
    for k, (v, t) in enumerate(zip(vues, INSTANTS)):
        P.paste(v, (10 + 400 * k, 30))
    for k, (c, t) in enumerate(zip(coupes, COUPES)):
        x = 10 + 800 * k
        d.text((x, 30 + 844 + 12), f"coupe à {-t} Ma", fill=(200, 200, 190), font=police(16))
        P.paste(c, (x, 30 + 844 + 36))
    P.save(sortie)
    print("planche :", sortie, P.size)


if __name__ == "__main__":
    main(sys.argv[1])
