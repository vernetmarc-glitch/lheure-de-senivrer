"""Planche du chantier S3 : la page servie, à 5 instants (aujourd'hui, 66 Ma, 250 Ma,
540 Ma, 1 Ga), vue donnée par la caméra automatique de la page.
Usage : python3 planche.py <sortie.png>"""
import asyncio, sys, io, pathlib
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from controles import port_libre, servir, etat, URL_PAGE

INSTANTS = [0, 66, 250, 540, 1000]


async def main(sortie):
    from playwright.async_api import async_playwright
    port = port_libre(); srv = servir(port)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                    args=["--no-sandbox", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg.on("pageerror", lambda e: print("pageerror", e))
        pg.on("console", lambda m: print("console", m.text) if m.type == "error" else None)
        await pg.goto(f"http://127.0.0.1:{port}{URL_PAGE}")
        await pg.wait_for_function("window.terre && window.terre.pret === true", timeout=120000)
        vues = []
        for t in INSTANTS:            # caméra automatique de la page (continents éclairés)
            await pg.evaluate("t => terre.regler({t, auto: true})", float(t))
            await pg.wait_for_timeout(300)
            vues.append(Image.open(io.BytesIO(await pg.screenshot())).convert("RGB"))
        await b.close()
    srv.shutdown()
    W, H = vues[0].size
    pl = Image.new("RGB", (W * len(vues) + 20 * (len(vues) - 1), H), (4, 5, 10))
    for k, im in enumerate(vues): pl.paste(im, (k * (W + 20), 0))
    pl = pl.resize((pl.width // 2, pl.height // 2), Image.LANCZOS)
    pl.save(sortie, optimize=True); print("planche :", sortie, pl.size)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "planche.png"))
