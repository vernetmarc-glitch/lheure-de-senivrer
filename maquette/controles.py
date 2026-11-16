"""Contrôles automatiques de la page (maquette « lumière »).

Chaque contrôle protège un retour de Marc ; il mesure la page servie, pas un aperçu.
Usage : python3 maquette/controles.py URL   (ex. http://localhost:8766/index.html)
Sortie : une ligne par contrôle, puis le bilan ; code de retour 1 si un échec.
"""
import asyncio, io, math, sys
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

WMIN, WMAX = 0.00006, 90
u = lambda W: 1000 * (math.log(W) - math.log(WMIN)) / (math.log(WMAX) - math.log(WMIN))
RES = []


def note(nom, ok, mesure, retour):
    RES.append(ok)
    print(f"{'OK ' if ok else 'ÉCHEC'}  {nom:<38} {mesure:<34} ← {retour}")


async def main(url):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        err = []; pg.on("pageerror", lambda e: err.append(str(e)))
        await pg.goto(url); await pg.wait_for_timeout(5000)
        await pg.evaluate("document.getElementById('fermer').click()")

        async def vue(W, t, att=900):
            await pg.evaluate(f"(()=>{{const z=document.getElementById('zoom');z.value={u(W)};z.dispatchEvent(new Event('input'));HDS.aller({t})}})()")
            await pg.wait_for_timeout(att)
            return np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("RGB")).astype(float)[70:560, 0:340]

        # 1. la toile : vides noirs et structures brillantes aujourd'hui (référence Millennium)
        im = await vue(0.15, 13.79); L = im.mean(-1)
        noir, brillant = (L < 18).mean(), (L > 120).mean()
        note("toile : vides noirs", noir > 0.45, f"noir {noir:.0%}", "« ni champ uniforme »")
        note("toile : structures brillantes", brillant > 0.004, f"brillant {brillant:.1%}", "« myriade de points brillants »")
        # 2. la matière agrégée est visible dès 3 Ga
        im = await vue(0.15, 3.3); L = im.mean(-1)
        note("matière agrégée visible à 3,3 Ga", (L > 60).mean() > 0.002, f"{(L > 60).mean():.2%} > 60", "« ne passe jamais par … matière agrégée »")
        # 3. pas de dallage : à la période de la boîte, l'image ne doit pas se ressembler
        #    davantage qu'à un décalage quelconque (la grille de la carte est commune aux deux)
        W = 1.5; im = await vue(W, 13.79, 1500); L = im.mean(-1); L -= L.mean()
        ppg = (min(390 - 44, 844 * 0.8) / 2) / W; T = int(round(0.96782 * ppg))
        cor = lambda s: ((L[:, :-s] * L[:, s:]).mean() + (L[:-s] * L[s:]).mean()) / 2 / (L.var() + 1e-9)
        exces = cor(T) - np.mean([cor(int(T * q)) for q in (0.61, 0.73, 1.37)])
        note("pas de dallage (autocorr. à 1 boîte)", exces < 0.08, f"excès {exces:.2f} à {T} px", "« dallage plus que toile »")
        # 4. lisibilité des sphères au plus grand champ : fond sombre
        im = await vue(55, 13.79); Lm = im.mean()
        note("sphères lisibles au grand champ", Lm < 28, f"luminance moyenne {Lm:.1f}", "lisibilité > beauté")
        # 5. le zoom va jusqu'à la Voie lactée, qui est visible et non saturée
        im = await vue(0.00009, 13.79, 7000); L = im.mean(-1)
        note("Voie lactée visible au zoom max", (L > 60).mean() > 0.05, f"{(L > 60).mean():.1%} > 60", "« on ne peut pas zoomer jusqu'à la Voie lactée »")
        note("Voie lactée non saturée", (L > 250).mean() < 0.01, f"{(L > 250).mean():.2%} blanc", "centre saturé (planche TNG)")
        # 6. bras spiraux : le gaz rose occupe des bras, pas un disque plein
        rose = (im[..., 0] > im[..., 1] * 1.6) & (im[..., 0] > 70)
        note("bras spiraux (gaz) présents", rose.mean() > 0.03, f"rose {rose.mean():.1%}", "« bras trop discrets »")
        # 7. danse continue : aucun saut entre deux époques simulées
        d = []; prev = None
        for k in range(24):
            im = await vue(0.00009, 12.40 + 0.35 * k / 23, 120); a = im.mean(-1)
            if prev is not None: d.append(np.abs(a - prev).mean())
            prev = a
        d = np.array(d); r = d.max() / np.median(d)
        note("danse continue (pas de saut)", r < 1.8, f"max/médiane {r:.2f}", "« danse des particules »")
        # 8. aucune erreur JavaScript
        note("aucune erreur JavaScript", not err, f"{len(err)} erreur(s)", "—")
        await b.close()
    print(f"\n{sum(RES)} contrôles passés, {len(RES) - sum(RES)} en échec")
    sys.exit(0 if all(RES) else 1)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/index.html"))
