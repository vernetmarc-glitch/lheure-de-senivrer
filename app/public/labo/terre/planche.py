"""Planche du chantier S3 : la page servie, à 5 instants (aujourd'hui, 66 Ma, 250 Ma,
540 Ma, 1 Ga), vue centrée sur le barycentre des terres de chaque instant.
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
        for t in INSTANTS:
            e = await etat(pg, float(t))
            h, w = e.shape
            lat = np.radians(90 - (np.arange(h) + .5) * 180 / h)[:, None]
            lon = np.radians(-180 + (np.arange(w) + .5) * 360 / w)[None, :]
            m = (e > 0) * np.cos(lat)
            v = np.array([(m * np.cos(lat) * np.cos(lon)).sum(), (m * np.cos(lat) * np.sin(lon)).sum(),
                          (m * np.sin(lat) * np.ones_like(lon)).sum()])
            la, lo = np.degrees(np.arcsin(v[2] / np.linalg.norm(v))), np.degrees(np.arctan2(v[1], v[0]))
            la = max(la, -15.0)   # solstice de juin : l hémisphère sud est dans la nuit polaire
            await pg.evaluate("o => terre.regler(o)", {"t": t, "lat": float(np.clip(la, -60, 60)), "lon": float(lo)})
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
