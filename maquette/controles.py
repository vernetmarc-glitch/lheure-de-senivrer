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
        # 3. pas de dallage : on empile les cases de la taille d'une boîte, centrées comme
        #    les copies. Copies indépendantes → la moyenne empilée s'aplatit (rapport ≈ 1) ;
        #    copies identiques ou au même nœud central → elle garde du contraste (≈ √n).
        W = 1.5; im = await vue(W, 13.79, 1500); L = im.mean(-1)
        ppg = (min(390 - 44, 844 * 0.8) / 2) / W; T = 0.96782 * ppg
        cx, cy = (390 - 44) / 2, 844 * 0.44 - 70
        cases = []
        for i in range(-3, 4):
            for j in range(-6, 7):
                x0, y0 = int(round(cx + (i - 0.5) * T)), int(round(cy + (j - 0.5) * T)); n = int(T)
                if x0 >= 0 and y0 >= 0 and x0 + n <= L.shape[1] and y0 + n <= L.shape[0] and (i, j) != (0, 0):
                    cases.append(L[y0:y0 + n, x0:x0 + n])
        C = np.array(cases); r = C.mean(0).std() * math.sqrt(len(C)) / C.std(axis=(1, 2)).mean()
        note("pas de dallage (cases empilées)", r < 1.6, f"rapport {r:.2f} sur {len(C)} cases", "« dallage plus que toile »")
        # 4. lisibilité des sphères au plus grand champ : fond sombre
        im = await vue(55, 13.79); Lm = im.mean()
        note("sphères lisibles au grand champ", Lm < 28, f"luminance moyenne {Lm:.1f}", "lisibilité > beauté")
        # 5. le zoom va jusqu'à la Voie lactée, qui est visible et non saturée
        im = await vue(0.00009, 13.79, 7000); L = im.mean(-1)
        note("Voie lactée visible au zoom max", (L > 60).mean() > 0.05, f"{(L > 60).mean():.1%} > 60", "« on ne peut pas zoomer jusqu'à la Voie lactée »")
        note("Voie lactée non saturée", (L > 250).mean() < 0.01, f"{(L > 250).mean():.2%} blanc", "centre saturé (planche TNG)")
        # 6. la Voie lactée en tons Millennium (pas de rose ni de bleu « photo ») et vue de biais
        # chaque pixel coloré doit se trouver sur la courbe de la palette (noir → indigo → violet → corail → or → blanc)
        B_ = [0, 0.22, 0.45, 0.65, 0.82, 0.93, 1.0]
        C_ = np.array([[0, 0, 0], [0.06, 0.04, 0.26], [0.40, 0.10, 0.52], [0.90, 0.32, 0.30], [1.0, 0.70, 0.32], [1.0, 0.93, 0.70], [1, 1, 1]])
        tq = np.linspace(0, 1, 400); courbe = np.stack([np.interp(tq, B_, C_[:, c]) for c in range(3)], -1) * 255
        pix = im.reshape(-1, 3); pix = pix[(pix.max(1) - pix.min(1)) > 30]
        if len(pix) > 2000: pix = pix[np.random.default_rng(1).choice(len(pix), 2000, replace=False)]
        dist = np.sqrt(((pix[:, None, :] - courbe[None]) ** 2).sum(-1)).min(1) if len(pix) else np.zeros(1)
        hors = (dist > 40).mean()
        note("Voie lactée en tons Millennium", hors < 0.05, f"{hors:.1%} hors palette", "« rester dans les tons Millenium »")
        ys, xs = np.where(L > 50)
        allong = (np.percentile(xs, 95) - np.percentile(xs, 5)) / max(1, np.percentile(ys, 95) - np.percentile(ys, 5)) if len(xs) > 100 else 0
        note("Voie lactée vue de biais", allong > 1.4, f"largeur/hauteur {allong:.2f}", "« un peu sur sa tranche »")
        # 7. danse continue : aucun saut entre deux époques simulées
        d = []; prev = None
        for k in range(24):
            im = await vue(0.00009, 12.40 + 0.35 * k / 23, 120); a = im.mean(-1)
            if prev is not None: d.append(np.abs(a - prev).mean())
            prev = a
        d = np.array(d); r = d.max() / np.median(d)
        note("danse continue (pas de saut)", r < 1.8, f"max/médiane {r:.2f}", "« danse des particules »")
        # 8. entre 1 et 60 Mal : de la structure (halos TNG50), pas des points rouges isolés
        im = await vue(0.02, 13.79, 2500); L = im.mean(-1); br = L > 90
        note("structure visible à 20 Mal", br.mean() > 0.004, f"brillant {br.mean():.1%}", "« plus aucun aspect filamenteux »")
        im = await vue(0.015, 8.0, 2500); L8 = im.mean(-1)
        note("structure visible à 15 Mal, il y a 6 Ga", (L8 > 90).mean() > 0.003, f"brillant {(L8 > 90).mean():.1%}", "« plus de structure sous les superamas »")
        sel = L > 50
        bleu = (im[..., 2][sel] / (im[..., 0][sel] + 1)).mean() if sel.any() else 0
        note("palette non monochrome rouge", bleu > 0.35, f"bleu/rouge {bleu:.2f}", "« pourquoi cette couleur rouge ? »")
        # 9. fluidité : temps d'une image à 1 Mal comparé à celui de la toile (même machine)
        async def duree(W):
            await vue(W, 13.79, 2500)
            return await pg.evaluate("""new Promise(res => { let n = 0, t0 = performance.now();
              const pas = () => { HDS.aller(13.79 - 0.0001 * (n % 2)); if (++n < 30) requestAnimationFrame(pas); else res((performance.now() - t0) / 30); };
              requestAnimationFrame(pas); })""")
        d0, d1 = await duree(0.15), await duree(0.002)
        note("fluidité à 1 Mal (vs toile)", d1 < 2.0 * d0 + 4, f"{d1:.0f} ms contre {d0:.0f} ms", "« ça rame énormément »")
        # 9 bis. netteté à 1 Mal : des points fins, pas de grosses taches floues
        im = await vue(0.003, 13.79, 2500); L = im.mean(-1)
        lap = np.abs(4 * L[1:-1, 1:-1] - L[:-2, 1:-1] - L[2:, 1:-1] - L[1:-1, :-2] - L[1:-1, 2:])
        zone = L[1:-1, 1:-1] > 40
        net = lap[zone].mean() / (L[1:-1, 1:-1][zone].mean() + 1) if zone.any() else 0
        note("netteté à 1 Mal", net > 0.25, f"laplacien relatif {net:.2f}", "« grosses taches floues »")
        # 9 ter. futur lointain : pas de structures figées grossies (la matière n'est pas simulée)
        im = await vue(0.15, 60, 1500)
        colore = ((im.max(-1) - im.min(-1)) > 40) & (im.mean(-1) > 30)      # la matière est colorée, les textes sont gris
        note("pas de matière dans le futur lointain", colore.mean() < 0.001, f"{colore.mean():.2%} colorés", "« toile à 100 milliards d'années, peu crédible »")
        # 9 quater. scénario Hubble : une photographie, le temps ne bouge pas
        await pg.click("[data-scen=hubble]"); await pg.wait_for_timeout(12000)
        th = await pg.evaluate("HDS.t")
        note("Hubble : temps figé", abs(th - 13.787) < 0.05, f"t = {th:.2f} Ga après 12 s", "« une photographie à l'instant t »")
        await pg.click("[data-scen=hubble]"); await pg.evaluate("document.querySelector('[data-scen=hubble]').click()")
        # 10. pas de gel quand la Voie lactée se charge (on recharge la page, on zoome tout de suite)
        await pg.goto(url); await pg.wait_for_timeout(5000)
        await pg.evaluate("document.getElementById('fermer').click()")
        gel = await pg.evaluate("""new Promise(res => { let p = performance.now(), mx = 0, t0 = p;
          const z = document.getElementById('zoom'); z.value = 40; z.dispatchEvent(new Event('input'));
          const f = () => { const n = performance.now(); mx = Math.max(mx, n - p); p = n; if (n - t0 < 9000) requestAnimationFrame(f); else res(mx); };
          requestAnimationFrame(f); })""")
        note("pas de gel au chargement de la galaxie", gel < max(600, 1.2 * d0), f"plus longue image {gel:.0f} ms", "« ça rame énormément »")
        # 11. aucune erreur JavaScript
        note("aucune erreur JavaScript", not err, f"{len(err)} erreur(s)", "—")
        await b.close()
    print(f"\n{sum(RES)} contrôles passés, {len(RES) - sum(RES)} en échec")
    sys.exit(0 if all(RES) else 1)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/index.html"))
