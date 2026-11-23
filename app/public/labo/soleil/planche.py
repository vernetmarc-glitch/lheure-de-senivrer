#!/usr/bin/env python3
"""Planche du chantier S1 : la page servie, capturée à plusieurs instants.

    python3 app/public/labo/soleil/planche.py chantiers/planches/soleil-1.png
"""
import functools
import http.server
import os
import re
import sys
import threading

from PIL import Image, ImageDraw, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))


def main():
    sortie = sys.argv[1]
    from playwright.sync_api import sync_playwright

    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    import socket
    port = next(p for p in range(8840, 8850) if socket.socket().connect_ex(("127.0.0.1", p)) != 0)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Q, directory=ICI))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    vues = []
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                      "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        pg.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"),
                 lambda r: r.fulfill(status=200, body="", content_type="text/css"))
        pg.goto(f"http://127.0.0.1:{port}/index.html")
        pg.wait_for_function("window.__soleil && window.__soleil.pret === true", timeout=180000)
        m = pg.evaluate("window.__soleil.meta")
        tc, tf = m["t_naissance"], m["instants"][-1]["t"]
        instants = [0.0, tc - 3e4, tc - 3e3, tc - 300, tc + 300, tc + 5e3, tf, tc + 1e6, tc + 4.5e7]
        for t in instants:
            pg.evaluate(f"window.__soleil.regle({t})")
            pg.wait_for_timeout(700)
            png = pg.screenshot()
            vues.append(Image.open(__import__("io").BytesIO(png)).convert("RGB"))
        nav.close()
    srv.shutdown()
    w, h = vues[0].size
    col = 5
    lignes = (len(vues) + col - 1) // col
    planche = Image.new("RGB", (col * w + (col + 1) * 8, lignes * h + (lignes + 1) * 8 + 40), (12, 14, 21))
    d = ImageDraw.Draw(planche)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except OSError:
        f = ImageFont.load_default()
    d.text((12, 8), "S1 — Naissance et allumage du Soleil (labo/soleil) : la page servie, 390 × 844", fill=(230, 232, 240), font=f)
    for i, v in enumerate(vues):
        x, y = 8 + (i % col) * (w + 8), 48 + (i // col) * (h + 8)
        planche.paste(v, (x, y))
    os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
    planche.save(sortie, optimize=True)
    print(sortie, planche.size)


if __name__ == "__main__":
    main()
