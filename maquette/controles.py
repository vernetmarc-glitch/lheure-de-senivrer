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
    ok = bool(ok); RES.append(ok)
    print(f"{'OK ' if ok else 'ÉCHEC'}  {nom:<38} {mesure:<34} ← {retour}")


async def main(url):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        err = []; pg.on("pageerror", lambda e: err.append(str(e)))
        await pg.goto(url); await pg.wait_for_timeout(5000)
        await pg.evaluate("HDS.demarrerLibre()")

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
        # 3 bis. au-delà de la toile cosmique, la matière reste visible comme un grain jusqu'à l'univers observable
        fr = []
        for Wg in (4, 15, 50):
            im = await vue(Wg, 13.787, 1500)
            fr.append((((im.max(-1) - im.min(-1)) > 25) & (im.mean(-1) > 20)).mean())   # la matière est colorée, cercles et textes gris
        note("grain de matière aux très grandes échelles", min(fr) > 0.02, " ; ".join(f"{w} Gal {x:.1%}" for w, x in zip((4, 15, 50), fr)),
             "« au-delà de la toile cosmique, continuer à voir des structures, pas un fond noir »")
        # 3 quinquies. P1 (17/11) : de 0,1 à 1 milliard d'a.-l., la toile en points qui bougent, plus de fondu
        #    d'images entre époques (les structures n'apparaissent plus deux fois)
        cp = []
        for Wc in (0.3, 0.8):
            await vue(Wc, 9.0, 800); cp.append(await pg.evaluate("HDS.couches") or {})
        note("toile en points, sans fondu d'images (P1)", all(c.get("tuilesPetite", 1) < 0.01 and c.get("points", 0) > 0.99 for c in cp),
             " ; ".join(f"{w} Gal : points {c.get('points', 0):.2f}, tuiles {c.get('tuilesPetite', 1):.2f}" for w, c in zip((0.3, 0.8), cp)), "« galaxies fantômes, mouvements non fluides »")
        # 3 quater. époques jeunes : pas de noir (17/11, 19 h 25 : « une augmentation de contraste pour
        #    éviter le noir aux époques jeunes »), mais les vides restent sombres (sphères lisibles)
        jeunes = []
        for Wj in (0.15, 1.5):
            for tj in (0.6, 1.2, 2.2):
                im = await vue(Wj, tj, 1300); Lj = im.mean(-1)
                jeunes.append((Wj, tj, (((im.max(-1) - im.min(-1)) > 25) & (Lj > 25)).mean(), (Lj < 18).mean()))
        note("époques jeunes : la toile visible, les vides sombres", all(c >= 0.04 and d >= 0.45 for _, _, c, d in jeunes),
             " ; ".join(f"{w} Gal {t} Ga : {c:.1%} colorés, {d:.0%} sombres" for w, t, c, d in jeunes), "« éviter le noir aux époques jeunes de l'univers »")
        # 3 quinquies. pas de traits droits aux époques jeunes (17/11, données v2) : le sous-échantillon tiré
        #    pour l'écran gardait des plans entiers de la grille de départ, alignés près des bords des
        #    boîtes. Profil moyen le long de chaque bord de la case centrale contre ses voisins à 25-45 px.
        bords = []
        for Wc, tc in ((0.15, 1.2), (0.15, 3.3), (0.3, 2.0)):
            await vue(Wc, tc, 2500); ac = await pg.evaluate(f"HDS.facteur({tc})")
            Lc = np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("L")).astype(float)
            ppg = (min(390 - 44, 844 * 0.8) / 2) / Wc; cxc, cyc = (390 - 44) / 2, 844 * 0.44; dc = ac * 0.96782 * ppg / 2
            for sg in (-1, 1):
                for axe, c0, lim in ((1, cxc, 346), (0, cyc, 844)):
                    e = c0 + sg * dc
                    if not 50 < e < lim - 50: continue
                    prof = Lc[100:560, :].mean(0) if axe == 1 else Lc[:, 10:330].mean(1); i = int(round(e))
                    bande = max(prof[i + o - 2:i + o + 3].mean() for o in range(-12, 13)); vois = np.r_[prof[i - 45:i - 25], prof[i + 25:i + 45]].mean()
                    bords.append(bande / max(vois, 1))
        note("pas de traits droits aux époques jeunes", max(bords) < 2.5, f"bord/voisins max {max(bords):.2f} ({len(bords)} bords)", "image du 17/11 : traits brillants aux bords des boîtes")
        # 3 ter. pas de dallage au grand champ (univers observable), sur un écran de téléphone (densité 3)
        pg3 = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
        await pg3.goto(url); await pg3.wait_for_timeout(5000)
        await pg3.evaluate("HDS.demarrerLibre(); HDS.grille = false")   # le fond seul
        rs = []
        for Wd in (46, 90):
            await pg3.evaluate(f"(()=>{{const z=document.getElementById('zoom');z.value={u(Wd)};z.dispatchEvent(new Event('input'));HDS.aller(13.787)}})()")
            await pg3.wait_for_timeout(2000)
            L3 = np.asarray(Image.open(io.BytesIO(await pg3.screenshot())).convert("L")).astype(float)
            ppg3 = 3 * (min(390 - 44, 844 * 0.8) / 2) / Wd; T3 = 7.25866 * ppg3; n3 = int(T3)
            cx3, cy3 = 3 * (390 - 44) / 2, 3 * (844 * 0.44 - 70)
            cs = []
            for i in range(-12, 13):
                for j in range(-20, 21):
                    x0, y0 = int(round(cx3 + (i - 0.5) * T3)), int(round(cy3 + (j - 0.5) * T3))
                    if x0 >= 0 and y0 >= 3 * 60 and x0 + n3 <= 3 * 340 and y0 + n3 <= 3 * 600 and (i, j) != (0, 0):
                        cs.append(L3[y0:y0 + n3, x0:x0 + n3])
            # médiane des cases empilées : une répétition la garde contrastée, les textes et cercles
            # (présents dans quelques cases seulement) ne la faussent pas ; cases indépendantes → ≈ 1,25
            C3 = np.array(cs); rs.append(np.median(C3, 0).std() * math.sqrt(len(C3)) / C3.std(axis=(1, 2)).mean())
        await pg3.close()
        note("pas de dallage à l'échelle de l'univers observable", max(rs) < 1.6, " ; ".join(f"{w} Gal : rapport {r:.2f}" for w, r in zip((46, 90), rs)),
             "« un dallage régulier qui fait un peu moche »")
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
        await pg.evaluate("HDS.recit(\'hubble\')"); await pg.wait_for_timeout(2500)
        vis_h = await pg.evaluate("!document.getElementById('intro').hidden")
        txt_h = await pg.evaluate("document.getElementById('intro').textContent")
        el_h = await pg.evaluate("HDS.el")
        await pg.evaluate("document.getElementById('cestParti').click()"); await pg.wait_for_timeout(4000); el_h2 = await pg.evaluate("HDS.el")
        note("Hubble : explication puis départ", vis_h and "Hubble" in txt_h and "photographie" in txt_h and el_h < 0.3 and el_h2 > 2,
             f"fenêtre {vis_h}, attente el = {el_h:.1f} s, puis {el_h2:.1f} s", "« une modale qui explique ce qui se passe et ce qu'on voit »")
        await pg.wait_for_timeout(8000)
        th = await pg.evaluate("HDS.t")
        note("Hubble : temps figé", abs(th - 13.787) < 0.05, f"t = {th:.2f} Ga après 12 s", "« une photographie à l'instant t »")
        # 9 quinquies. un second appui arrête le scénario, retire ses ajouts, garde l'instant
        # (scénario du passé : l'instant est gardé ; sortir de l'horizon dans le futur ramène à
        #  aujourd'hui depuis la décision du 17/11, la frise libre s'arrêtant à aujourd'hui)
        await pg.evaluate("HDS.recit(\'observable\')"); await pg.wait_for_timeout(1500); await pg.click("#cestParti"); await pg.wait_for_timeout(9000)
        avant = await pg.evaluate("HDS.t"); await pg.evaluate("HDS.recit(\'observable\')"); await pg.wait_for_timeout(600)
        e = await pg.evaluate("HDS.etat"); apres = await pg.evaluate("HDS.t")
        note("second appui : retour à l'exploration", e["scen"] is None and e["fronts"] == 0 and abs(apres - avant) < 0.5,
             f"scénario {e['scen']}, {e['fronts']} lumière(s), t {avant:.1f} → {apres:.1f} Ga", "« je ne sais pas revenir à la vue par défaut »")
        # 9 sexies. « aujourd'hui » ramène au présent
        await vue(0.15, 5.0, 300); await pg.click("#repAuj"); await pg.wait_for_timeout(400)
        ta = await pg.evaluate("HDS.t")
        note("bouton « aujourd'hui »", abs(ta - 13.787) < 0.05, f"t = {ta:.2f} Ga", "« appuyer sur aujourd'hui pour explorer »")
        # 9 septies. Promenade : plongée jusqu'à la galaxie plein écran, retour à ~1 Ga, curseurs qui pulsent
        await vue(0.15, 13.787, 300); await pg.evaluate("HDS.recit(\'promenade\')"); await pg.wait_for_timeout(1200)
        await pg.wait_for_timeout(1500); W0 = await pg.evaluate("HDS.W")
        await pg.evaluate("HDS.el = 7"); await pg.wait_for_timeout(900)
        z_pulse = await pg.evaluate("document.getElementById('zoom').classList.contains('bouge')")
        tz = []
        for e_ in (15.5, 17.5, 19.2):
            await pg.evaluate(f"HDS.el = {e_}"); await pg.wait_for_timeout(500); tz.append(await pg.evaluate("HDS.t"))
        note("Promenade : le temps attend la fin du zoom", max(tz) >= 13.77, f"t pendant le recul : {[round(x, 2) for x in tz]}", "« ne remonte pas le temps pendant le dézoom final »")
        Ws = []
        for e_ in (13.6, 14.5, 15.4):                       # lecture deux images après, indépendante de la vitesse de la machine
            Ws.append(await pg.evaluate(f"new Promise(r => {{ HDS.el = {e_}; requestAnimationFrame(() => requestAnimationFrame(() => r(HDS.W))); }})"))
        W14 = Ws[1]
        note("Promenade : plongée et recul d'un seul mouvement", Ws[0] > 1.03 * Ws[1] and Ws[2] > 1.03 * Ws[1],
             f"champ {Ws[0]:.2e} → {Ws[1]:.2e} → {Ws[2]:.2e} Gal (à ±0,9 s du fond)", "« pas de pause entre le zoom et le dézoom »")
        await pg.evaluate("HDS.el = 22"); await pg.wait_for_timeout(1500)
        t_pulse = await pg.evaluate("document.getElementById('temps').classList.contains('bouge')")
        async def vitesse(t0):
            await pg.evaluate(f"HDS.aller({t0})"); await pg.wait_for_timeout(400)
            a, ea = await pg.evaluate("[HDS.t, HDS.el]"); await pg.wait_for_timeout(2500); b, eb = await pg.evaluate("[HDS.t, HDS.el]")
            return (a - b) / max(eb - ea, 1e-6)                 # Ga par seconde de scénario (indépendant de la machine)
        # (18/11, 9 h 33, remplace « accélérer jusqu'à 7 Ga, ralentir aux collisions ») : pendant la remontée,
        # un seul champ où la galaxie occupe l'écran, qu'on voit rapetisser sans rezoomer ; vitesse constante,
        # durée totale gardée (37,6 s de récit de 13,8 à 1,8 Ga)
        await pg.evaluate("HDS.aller(13.4)"); await pg.wait_for_timeout(2500)
        gimg = np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("L")).astype(float)[90:600, 0:340]
        cols = np.where((gimg > 45).sum(0) > 2)[0]; largeur = (cols.max() - cols.min()) / 340 if len(cols) else 0
        Wa = await pg.evaluate("HDS.W")
        v_vite, v_collision = await vitesse(11.0), await vitesse(6.0)
        Wb = await pg.evaluate("HDS.W"); v_fin = await vitesse(3.2); Wc_ = await pg.evaluate("HDS.W")
        Wrecul = Wa; fixe = max(Wa, Wb, Wc_) / min(Wa, Wb, Wc_)
        await pg.evaluate("HDS.aller(1.25)"); fin = 99
        for _ in range(10):
            await pg.wait_for_timeout(250); fin = min(fin, await pg.evaluate("HDS.t"))
        vs = (v_vite, v_collision, v_fin); duree = (13.787 - 1.8) / (sum(vs) / 3)
        note("Promenade : plongée, puis on remonte le temps", W14 <= 7e-5 and min(vs) > 0 and max(vs) / min(vs) <= 1.25 and fin <= 1.81 and fixe <= 1.02 and largeur >= 0.7 and 32 <= duree <= 43,
             f"champ {W14:.1e} Gal ; vitesses {[round(v, 2) for v in vs]} Ga/s, durée ≈ {duree:.0f} s ; champ en remontant {Wrecul:.1e} (écart ×{fixe:.3f}) ; galaxie sur {largeur:.0%} de la largeur ; arrêt à {fin:.2f} Ga",
             "« se délite petit à petit » ; 18/11 : « la galaxie prend beaucoup d'espace, puis rapetisse sans que l'on zoome ; vitesse moyenne la même tout le long, même durée totale »")
        note("Promenade : départ à l'échelle de la toile cosmique", W0 >= 1.0, f"champ de départ {W0:.2f} Gal", "« commencer à la toile cosmique, pas aux superamas »")
        note("curseurs qui bougent : pulsation", z_pulse and t_pulse, f"zoom {z_pulse}, temps {t_pulse}", "« repérer ceux qui bougent »")
        # fin de la Promenade : retour fluide à aujourd'hui, au champ Millennium, scénario désactivé
        suite = []
        # fin de la remontée : la jeune galaxie reste visible, et le retour repart vite (17/11, 18 h 59)
        await pg.evaluate("HDS.recit('promenade'); HDS.recit('promenade')"); await pg.wait_for_timeout(1500)   # une Promenade neuve
        await pg.evaluate("HDS.el = 22; HDS.aller(3.4)"); fil = []
        for _ in range(120):
            await pg.wait_for_timeout(200); fil.append(await pg.evaluate("[HDS.el, HDS.t, HDS.W]"))
            if len(fil) > 5 and fil[-1][2] > 1.6 * min(x[2] for x in fil): break
        e3 = next((x[0] for x in fil if x[1] <= 3.0), None)
        k0 = min(range(len(fil)), key=lambda k: (fil[k][1], k))         # le point le plus ancien atteint
        eR = next((x[0] for x in fil[k0:] if x[2] > 1.15 * fil[k0][2]), None)   # le champ repart (retour)
        attente = (eR - e3) if (e3 is not None and eR is not None) else 99
        # à l'arrêt, l'embryon de galaxie occupe encore une part visible de l'écran
        await pg.evaluate("HDS.recit('promenade'); HDS.recit('promenade')"); await pg.wait_for_timeout(1200)
        await pg.evaluate("HDS.el = 22; HDS.aller(1.81)"); await pg.wait_for_timeout(1200)
        img = np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("RGB")).astype(float)[100:600, 0:340]
        vu = (((img.max(-1) - img.min(-1)) > 25) & (img.mean(-1) > 25)).mean()
        note("fin de la remontée : rien d'interminable, l'embryon visible", attente <= 6 and vu >= 0.01,
             f"{attente:.1f} s de récit entre 3 milliards d'années et le départ du retour ; à l'arrêt, {vu:.1%} de l'écran éclairé", "« on reste au moins 10 s sur " + "« elle naissait », il ne se passe rien »")
        await pg.evaluate("HDS.recit('promenade'); HDS.recit('promenade')"); await pg.wait_for_timeout(800)
        await pg.evaluate("HDS.vitesse = 3")                  # le grand recul est long : scénario accéléré pour le contrôle
        for _ in range(200):                                   # jusqu'à la fin réelle du scénario (60 s au plus)
            await pg.wait_for_timeout(300); suite.append(await pg.evaluate("[HDS.t, HDS.W, HDS.etat.scen, HDS.el]"))
            if suite[-1][2] is None: break
        await pg.evaluate("HDS.vitesse = 1")
        actif = await pg.evaluate("!!document.querySelector('.scen button.actif')")
        ts = [x[0] for x in suite if x[2] == "promenade"]; Wf = suite[-1][1]
        # pas mesuré par seconde de scénario (le contrôle l'accélère) : Ga par seconde de récit
        ps = [x for x in suite if x[2] == "promenade"]
        saut = max(abs(q[0] - p_[0]) / max(q[3] - p_[3], 1e-3) for p_, q in zip(ps, ps[1:])) if len(ps) > 1 else 99
        note("Promenade : retour fluide au présent, grand recul", suite[-1][2] is None and not actif and abs(suite[-1][0] - 13.787) < 0.02 and 40 <= Wf <= 60 and saut < 4,
             f"fin t = {suite[-1][0]:.2f} Ga, champ {Wf:.1f} Gal, plus grand pas {saut:.2f} Ga par seconde de récit, scénario {suite[-1][2]}, bouton actif {actif}",
             "« revenir de manière fluide au présent, désactiver Promenade » ; 17/11 15 h 54 : fin sur le grand recul (D1), remplace la fin aux superamas")
        # 9 octies. Univers observable : d'abord l'explication, le départ au bouton « C'est parti »
        await pg.evaluate("HDS.recit(\'observable\')"); await pg.wait_for_timeout(3000)
        ta = await pg.evaluate("HDS.t"); vis = await pg.evaluate("!document.getElementById('intro').hidden")
        await pg.click("#cestParti"); await pg.wait_for_timeout(6000); tb = await pg.evaluate("HDS.t")
        note("Observable : explication puis départ", vis and ta < 0.0004 and tb > ta * 1.5, f"attente à {ta * 1e6:.0f}000 ans, puis {tb:.3f} Ga", "« un message, puis un bouton c'est parti »")
        await pg.evaluate("HDS.aller(13.7)")
        for _ in range(8):                                   # les étapes attendent « Suite »
            await pg.wait_for_timeout(1200); await pg.evaluate("HDS.suite()")
        await pg.wait_for_timeout(3000)
        fin_txt = await pg.evaluate("document.getElementById('phrase').textContent + ' ' + (document.getElementById('finObs').hidden ? '' : document.getElementById('finObs').textContent)")
        textes = " ".join(await pg.evaluate("HDS.textes"))
        note("Observable : tapis roulant annoncé, 46 Gal à la fin", "46" in fin_txt and "tapis roulant" in textes, f"fourmis {'tapis roulant' in textes}, fin « {fin_txt.strip()[:90]} »", "« fourmis sur un tapis roulant » ; « 46 milliards à la fin »")
        await pg.evaluate("HDS.recit(\'observable\')"); await pg.wait_for_timeout(300)
        # 9 octies bis. le texte arrive avec le bouton (18/11, 6 h 12) : pendant que l'animation court, pas de
        #    texte ; à chaque arrêt, une explication nouvelle et « Suite » ensemble ; univers observable :
        #    la transparence à 380 000 ans, le départ à 41 millions d'années-lumière
        SEQ = """(cle) => new Promise(res => { HDS.vitesse = 6; HDS.recit(cle); const obs = []; const t0 = performance.now(); let vu = -1, lu = -1;
          let va = -1;
          const iv = setInterval(() => { const s = document.getElementById('suite'), p = document.getElementById('phrase'), e = HDS.etat, now = performance.now() - t0;
            const sv = !!s.offsetParent, txt = +getComputedStyle(p).opacity > 0.5 && getComputedStyle(p).display !== 'none' ? p.textContent.trim() : '';
            obs.push([now, sv, txt, e.attente, e.fin]);
            if (e.attente && va < 0) va = now; if (!e.attente) va = -1;
            if (e.attente && now - va > 1500) { document.getElementById('cestParti').click(); va = -1; }
            if (sv && vu < 0) { vu = now; lu = -1; } if (!sv) vu = -1; if (sv && txt && lu < 0) lu = now;
            if (sv && ((lu >= 0 && now - lu > 1200) || now - vu > 8000)) { s.click(); vu = -1; }
            if (e.fin && obs.filter(o => o[4]).length > 12 || now > 150000) { clearInterval(iv); HDS.vitesse = 1; res(obs); } }, 200); })"""
        bilan = {}
        for cle in ("observable", "hubble", "evenements", "toile"):
            obs = await pg.evaluate(f"({SEQ})('{cle}')")
            # (navigateur sans carte graphique : une image par seconde environ ; le fondu de la légende
            #  dure 0,9 s et ne part qu'à l'image suivante : on tolère 4 s de traîne après chaque arrêt)
            # un arrêt = un texte affiché avec « Suite » ; des pages successives au même instant comptent chacune
            arrets, bavard, dern_arret, cour, vide = [], 0, -1e9, None, 0
            for k, (tm, sv, txt, att, fin) in enumerate(obs):
                if sv:
                    dern_arret = tm
                    if txt and (not arrets or arrets[-1] != txt or cour is None): arrets.append(txt)
                    cour = cour or txt or ""
                if not sv and cour is not None:
                    if not cour: vide += 1
                    cour = None
                if not sv and not att and not fin and tm - dern_arret > 4000 and txt: bavard += 1
            if vide: arrets.append("")
            bilan[cle] = (arrets, bavard, obs[-1][4])
            await pg.evaluate(f"HDS.recit('{cle}')"); await pg.wait_for_timeout(400)
        ok_seq = all(len(a) >= 2 and all(a) and len(set(a)) == len(a) and bv == 0 and f for a, bv, f in bilan.values())
        tobs = " ".join(bilan["observable"][0]) + " " + " ".join(await pg.evaluate("(HDS.recit('observable'), HDS.textes)"))
        await pg.evaluate("HDS.recit('observable')")
        # (18/11, 7 h 45) la fin en plusieurs pages : 13,8 milliards d'années de voyage, la source passée de
        # 41 millions à 45 milliards d'années-lumière, plus de mille fois plus loin
        fin_pages = all(m in tobs for m in ("13,8 milliards", "45 milliards", "mille fois")) and len(bilan["observable"][0]) >= 6
        ok_obs = "transparent" in tobs and "380 000" in tobs and "41 millions" in tobs and fin_pages
        note("récits : le texte arrive avec le bouton « Suite »", ok_seq and ok_obs,
             " ; ".join(f"{c} : {len(a)} arrêts, {bv} textes pendant le mouvement, fin {f}" for c, (a, bv, f) in bilan.items()) + f" ; observable : transparence {'transparent' in tobs}, 41 millions {'41 millions' in tobs}, fin en pages {fin_pages}",
             "« le texte en même temps que le bouton suite » ; « pourquoi 380 000 ans : l'univers devient transparent ; d'où part la lumière : 41 millions »")
        # 9 nonies. Voie lactée : basse résolution pendant le mouvement (budget de remplissage),
        #    pleine résolution reconstruite en arrière-plan à l'arrêt, identique au rendu direct
        await vue(0.0003, 13.787, 300)
        bouge = await pg.evaluate(f"""new Promise(r => {{ const z = document.getElementById('zoom'); const u0 = {u(0.0004)}, u1 = {u(0.00017)}; let k = 0, mx = 0, qs = [];
          const f = () => {{ k++; z.value = u0 + (u1 - u0) * k / 30; z.dispatchEvent(new Event('input'));
            const g = HDS.galaxie || {{ q: 1, remplissage: 99 }}; qs.push(g.q); mx = Math.max(mx, g.remplissage);
            if (k < 30) requestAnimationFrame(f); else r({{ qmax: Math.max(...qs.slice(3)), rmax: mx }}); }}; requestAnimationFrame(f); }})""")
        fin = None
        for _ in range(60):
            await pg.wait_for_timeout(250); fin = await pg.evaluate("HDS.galaxie || { pleine: false }")
            if fin["pleine"]: break
        a1 = np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("RGB")).astype(float)[70:560, 0:340]
        await pg.evaluate("HDS.galaxieDirecte = true"); await pg.wait_for_timeout(1500)
        a2 = np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("RGB")).astype(float)[70:560, 0:340]
        await pg.evaluate("HDS.galaxieDirecte = false")
        ecart = np.abs(a1 - a2).mean()
        note("Voie lactée : basse résolution en mouvement", bouge["qmax"] <= 0.5 and bouge["rmax"] <= 4,
             f"résolution ≤ {bouge['qmax']:.2f}, remplissage ≤ {bouge['rmax']:.1f} écrans par image", "« ça rame quand la Voie lactée apparaît »")
        note("Voie lactée : pleine résolution à l'arrêt", fin["pleine"] and ecart < 1.5,
             f"pleine {fin['pleine']}, écart au rendu direct {ecart:.2f}/255", "« la haute résolution s'affiche dès qu'elle est disponible »")
        # 10. pas de gel quand la Voie lactée se charge (on recharge la page, on zoome tout de suite)
        await pg.goto(url); await pg.wait_for_timeout(5000)
        await pg.evaluate("HDS.demarrerLibre()")
        gel = await pg.evaluate("""new Promise(res => { let p = performance.now(), mx = 0, t0 = p;
          const z = document.getElementById('zoom'); z.value = 40; z.dispatchEvent(new Event('input'));
          const f = () => { const n = performance.now(); mx = Math.max(mx, n - p); p = n; if (n - t0 < 9000) requestAnimationFrame(f); else res(mx); };
          requestAnimationFrame(f); })""")
        note("pas de gel au chargement de la galaxie", gel < max(600, 1.2 * d0), f"plus longue image {gel:.0f} ms", "« ça rame énormément »")
        # 10 quinquies bis. Horizon : une explication avant l'acte 1, une autre avant l'acte 2
        await pg.evaluate("HDS.recit(\'evenements\')"); await pg.wait_for_timeout(2500)
        vis1 = await pg.evaluate("!document.getElementById('intro').hidden")
        txt1 = await pg.evaluate("document.getElementById('intro').textContent"); t1 = await pg.evaluate("HDS.t")
        await pg.evaluate("document.getElementById('cestParti').click()"); await pg.wait_for_timeout(5000); t1b = await pg.evaluate("HDS.t")
        await pg.evaluate("HDS.aller(99.9)"); await pg.wait_for_timeout(5000)
        await pg.evaluate("(() => { const s = document.getElementById('suite'); if (s.offsetParent) s.click(); })()"); await pg.wait_for_timeout(3000)
        e2 = await pg.evaluate("HDS.etat"); vis2 = await pg.evaluate("!document.getElementById('intro').hidden")
        txt2 = await pg.evaluate("document.getElementById('intro').textContent"); t2 = await pg.evaluate("HDS.t")
        await pg.wait_for_timeout(2000); t2a = await pg.evaluate("HDS.t")
        await pg.evaluate("document.getElementById('cestParti').click()"); await pg.wait_for_timeout(5000); t2b = await pg.evaluate("HDS.t")
        ok = (vis1 and "acte 1" in txt1.lower() and abs(t1 - 13.787) < 0.02 and t1b > 14.5
              and e2.get("acte") == 2 and vis2 and "acte 2" in txt2.lower() and abs(t2a - 13.787) < 0.02 and t2b > 14.5)
        note("Horizon : une explication par acte", ok,
             f"acte 1 : fenêtre {vis1}, t {t1:.2f} → {t1b:.1f} Ga ; acte 2 : acte {e2.get('acte')}, fenêtre {vis2}, t {t2a:.2f} → {t2b:.1f} Ga",
             "« une modale pour l'acte 1 et une autre pour l'acte 2 »")
        await pg.evaluate("HDS.recit(\'evenements\')"); await pg.wait_for_timeout(800)
        # 10 sexies bis. P6 (17/11) : formation de la toile cosmique, champ comobile (les structures restent en place)
        await pg.evaluate("HDS.recit('toile')"); await pg.wait_for_timeout(1500)
        t6 = await pg.evaluate("HDS.t"); vis6 = await pg.evaluate("!document.getElementById('intro').hidden")
        await pg.evaluate("document.getElementById('cestParti').click()"); await pg.wait_for_timeout(1500)
        ech = []
        for _ in range(30):
            await pg.wait_for_timeout(500); x = await pg.evaluate("[HDS.t, HDS.W]"); ech.append(x)
            if await pg.evaluate("!!document.getElementById('suite') && !!document.getElementById('suite').offsetParent"): break
        await pg.evaluate("HDS.aller(5.0)"); await pg.wait_for_timeout(1500); x5 = await pg.evaluate("[HDS.t, HDS.W, HDS.etat.scen]")
        # W / a(t) doit rester constant : on le vérifie sur deux instants éloignés
        r = await pg.evaluate(f"(() => {{ const a = t => HDS.facteur(t); return [{ech[-1][1]} / a({ech[-1][0]}), {x5[1]} / a({x5[0]})]; }})()")
        note("formation de la toile cosmique : champ qui suit l'expansion (P6)", vis6 and t6 < 0.5 and abs(r[0] / r[1] - 1) < 0.03 and x5[2] == "toile",
             f"départ {t6:.2f} Ga, carte d'intro {vis6}, champ/a : {r[0]:.3f} puis {r[1]:.3f}", "« la formation de filaments cosmiques comme récit à part entière »")
        await pg.evaluate("HDS.recit('toile')"); await pg.wait_for_timeout(500)
        # 10 quater. frise du temps : jusqu'à aujourd'hui en libre, futur seulement pendant l'horizon
        libre_max = await pg.evaluate("+document.getElementById('temps').max")
        await pg.evaluate("HDS.recit(\'evenements\')"); await pg.wait_for_timeout(1200)
        hor_max = await pg.evaluate("+document.getElementById('temps').max")
        await pg.evaluate("HDS.recit(\'evenements\')"); await pg.wait_for_timeout(800)
        apres_max = await pg.evaluate("+document.getElementById('temps').max"); ta = await pg.evaluate("HDS.t")
        note("futur seulement pendant l'horizon", libre_max < 900 and hor_max == 1000 and apres_max == libre_max and ta <= 13.79,
             f"max libre {libre_max}, horizon {hor_max}, après {apres_max}, t {ta:.2f}", "« le curseur libre s'arrête à aujourd'hui »")
        # 10 ter. axes lisibles : libellés « espace » et « temps », pas de redshift z
        lec = await pg.evaluate("document.getElementById('lectureTemps').textContent")
        esp = await pg.evaluate("document.getElementById('axeEspace').textContent")
        note("axes nommés, sans « z = »", "z =" not in lec and "⏳" in lec and "espace" in esp, f"« {lec} » ; « {esp} »", "« le z ne parle à personne »")
        # 10 bis. chargement : zones prêtes affichées sur le curseur, tout prêt une fois chargé
        await pg.wait_for_timeout(6000)
        d = await pg.evaluate("HDS.dispo"); bd = await pg.evaluate("HDS.bandes")
        note("zones prêtes visibles, tout chargé", min(d) >= 1 and bd > 50, f"disponibilité {[round(x, 2) for x in d]}", "« rendre visibles les zones accessibles »")
        # 12. la découverte (décisions du 17/11, 15 h 54 : tableau « Choix à valider », tout « oui »)
        #     un visiteur neuf, du noir jusqu'à l'exploration libre
        pd = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        perr = []; pd.on("pageerror", lambda e: perr.append(str(e)))
        MOTS = """(() => { const exclus = el => el.closest('#zoomBloc, .piste, template, #chargement');
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n, mots = 0;
          while ((n = w.nextNode())) { const el = n.parentElement; if (!el || !n.textContent.trim() || exclus(el)) continue;
            const r = el.getBoundingClientRect(); let v = r.width > 0 && r.bottom > 0 && r.top < innerHeight;
            for (let a = el; a && v; a = a.parentElement) { const st = getComputedStyle(a); if (a.hidden || st.display === 'none' || st.visibility === 'hidden' || +st.opacity < 0.3) v = false; }
            if (v) mots += n.textContent.trim().split(/\\s+/).length; }
          const vis = el => { if (!el) return false; if (getComputedStyle(el).pointerEvents === 'none') return false; for (let a = el; a; a = a.parentElement) { const st = getComputedStyle(a); if (a.hidden || st.display === 'none' || st.visibility === 'hidden' || +st.opacity < 0.3) return false; } const r = el.getBoundingClientRect(); return r.width > 0 && r.bottom > 0 && r.top < innerHeight; };
          const actifs = [...document.querySelectorAll('button, input')].filter(vis);
          return { mots, commandes: actifs.map(e => e.id || e.dataset.scen || e.textContent.trim().slice(0, 12)), principales: actifs.filter(e => e.classList.contains('principal')).length }; })()"""
        async def ecran(): return np.asarray(Image.open(io.BytesIO(await pd.screenshot())).convert("RGB")).astype(float)
        budget = []
        await pd.goto(url); await pd.wait_for_timeout(700)
        # le voile noir lui-même (une capture d'écran attend une image : sur ce navigateur sans carte
        # graphique, elle arrive plusieurs secondes plus tard et ne dit rien du noir à 0,7 s)
        noir = 255 * (1 - await pd.evaluate("(() => { const v = document.querySelector('#ouverture .noir'); return v ? +getComputedStyle(v).opacity : 0; })()"))
        ligne = await pd.evaluate("(document.getElementById('ouverture') || {}).textContent || ''")
        await pd.wait_for_timeout(5500)
        im = await ecran(); toile = (((im.max(-1) - im.min(-1)) > 25) & (im.mean(-1) > 20)).mean()
        m = await pd.evaluate(MOTS); budget.append(("ouverture", m["mots"]))
        note("ouverture : le noir, puis la toile (A1)", noir < 12 and "enivrer" in ligne and toile > 0.01 and m["commandes"] == ["partir"] and m["principales"] == 1,
             f"luminance à 0,7 s {noir:.1f}, toile {toile:.1%} à 6 s, commandes {m['commandes']}, {m['mots']} mots", "« effet waouh dès l'ouverture, un seul bouton »")
        await pd.click("#partir"); await pd.wait_for_timeout(1500)
        e0 = await pd.evaluate("HDS.etat")
        ph = {}
        for e_ in (1.5, 8, 16.5, 21):
            await pd.evaluate(f"HDS.el = {e_}"); await pd.wait_for_timeout(1300)
            mm = await pd.evaluate(MOTS); lg = await pd.evaluate("(() => { const p = document.getElementById('phrase'); return { txt: getComputedStyle(p).opacity > 0.3 ? p.textContent.trim() : '', h: p.getBoundingClientRect().height, lh: parseFloat(getComputedStyle(p).lineHeight) }; })()")
            ph[e_] = (mm, lg); budget.append((f"promenade {e_} s", mm["mots"]))
            if e_ == 16.5: ici = await pd.evaluate("HDS.ici")
        cmd = [ph[k][0]["commandes"] for k in ph]
        note("Promenade plein écran, légende d'une ligne (B1)", e0["scen"] == "promenade" and all(c == ["passer"] for c in cmd) and all(ph[k][1]["h"] <= 2.2 * ph[k][1]["lh"] for k in ph) and ph[1.5][1]["txt"],
             f"commandes {cmd[0]} ; hauteurs de légende {[round(ph[k][1]['h'] / ph[k][1]['lh'], 1) for k in ph]} lignes", "« trop de choses à lire »")
        note("silence pendant la plongée (B2)", ph[8][1]["txt"] == "", f"légende à 8 s : « {ph[8][1]['txt']} »", "« le mot arrive quand l'image se pose »")
        note("repère « nous sommes ici » sur le Soleil", bool(ici), f"repère dessiné {ici}", "« qu'on comprenne bien ce qu'on voit »")
        # grand recul (D1) : les trois cercles s'allument l'un après l'autre
        await pd.evaluate("HDS.vitesse = 3; HDS.el = 22; HDS.aller(1.25)"); ordre = []
        legs, etiqs = [], set()
        for _ in range(240):
            await pd.wait_for_timeout(250); st = await pd.evaluate("[HDS.etat.scen, HDS.cercles.join(''), HDS.W, document.getElementById('phrase').textContent.trim(), (HDS.etiquettes || []).join('|')]")
            if st[1] and (not ordre or ordre[-1] != st[1]): ordre.append(st[1])
            if st[1] and st[3] and (not legs or legs[-1] != st[3]): legs.append(st[3])
            if st[4]: etiqs.update(st[4].split('|'))
            if st[0] is None: break
        await pd.evaluate("HDS.vitesse = 1")
        note("grand recul : les trois frontières une à une (D1)", st[0] is None and ordre[:3] == ["p", "ph", "phe"] and 40 <= st[2] <= 60,
             f"cercles allumés dans l'ordre {ordre}, champ final {st[2]:.0f} Gal", "« le dernier moment waouh dévoile les trois frontières »")
        noms = [l for l in legs if "milliards d'années-lumière" in l]
        definit = [l for l in legs if any(m in l for m in ("au-delà", "tout ce que", "parviendra", "plus vite"))]
        invite = [l for l in legs if "Récits" in l and "curseurs" in l]
        note("les frontières nommées, leur rayon, puis une invitation", len(noms) >= 3 and not definit and invite and etiqs and not any("Gal" in e for e in etiqs),
             f"légendes {legs} ; étiquettes {sorted(etiqs)}", "« nommer, donner le rayon ; pour comprendre, Récits ou les curseurs ; sinon on décroche »")
        # passer la main (C1) : le zoom seul, puis le temps, puis le reste
        await pd.wait_for_timeout(800)
        z1 = await pd.evaluate(MOTS); budget.append(("main : zoom", z1["mots"]))
        ind1 = await pd.evaluate("(document.getElementById('indice') || {}).textContent || ''")
        await pd.evaluate("(() => { const z = document.getElementById('zoom'); z.value = +z.value - 120; z.dispatchEvent(new Event('input')); })()"); await pd.wait_for_timeout(800)
        z2 = await pd.evaluate(MOTS); ind2 = await pd.evaluate("(document.getElementById('indice') || {}).textContent || ''")
        await pd.evaluate("(() => { const z = document.getElementById('temps'); z.value = +z.value - 80; z.dispatchEvent(new Event('input')); })()"); await pd.wait_for_timeout(800)
        z3 = await pd.evaluate(MOTS); budget.append(("libre", z3["mots"]))
        note("passer la main, un geste après l'autre (C1)", z1["commandes"] == ["zoom"] and "Glissez" in ind1 and set(z2["commandes"]) == {"zoom", "temps"} and "temps" in ind2 and "recits" in z3["commandes"],
             f"{z1['commandes']} → {z2['commandes']} → {z3['commandes']}", "« découverte graduelle »")
        # l'interface au repos (E1)
        rep = await pd.evaluate("[...document.querySelectorAll('#reperesZoom span')].filter(s => +getComputedStyle(s).opacity > 0.5).length")
        await pd.wait_for_timeout(7000); op1 = await pd.evaluate("+getComputedStyle(document.getElementById('phrase')).opacity")
        await pd.mouse.click(150, 300); await pd.wait_for_timeout(700); op2 = await pd.evaluate("+getComputedStyle(document.getElementById('phrase')).opacity")
        await pd.click("#recits"); await pd.wait_for_timeout(500)
        entrees = await pd.evaluate("[...document.querySelectorAll('#panneauRecits button[data-scen]')].filter(b => b.offsetParent).map(b => b.dataset.scen)")
        await pd.click("#panneauRecits button[data-scen=hubble]"); await pd.wait_for_timeout(1500)
        e1 = await pd.evaluate("HDS.etat"); panneau = await pd.evaluate("!!document.getElementById('panneauRecits').offsetParent")
        nomP = await pd.evaluate("document.querySelector('#panneauRecits button[data-scen=promenade]').textContent.trim()")
        note("la Promenade s'appelle « Formation de la Voie lactée »", nomP == "Formation de la Voie lactée", f"« {nomP} »", "« le bouton promenade pourrait être renommé formation de la Voie lactée »")
        note("récits derrière un bouton (E1)", entrees == ["observable", "hubble", "evenements", "promenade", "toile"] and e1["scen"] == "hubble" and not panneau,
             f"panneau {entrees}, lancé {e1['scen']}, panneau refermé {not panneau}", "« moins de choses à la fois »")
        note("un seul repère sur le curseur du zoom (E1)", rep == 1, f"{rep} repère(s) visibles", "« hiérarchie »")
        note("légende qui s'efface, rappelée au toucher (E1)", op1 < 0.2 and op2 > 0.8, f"opacité après 7 s {op1:.2f}, après un toucher {op2:.2f}", "« moins de texte à la fois »")
        # récits en étapes (F1)
        c1 = await pd.evaluate(MOTS); budget.append(("récit : introduction", c1["mots"]))
        await pd.click("#cestParti"); await pd.wait_for_timeout(1500)
        r1 = await pd.evaluate(MOTS); budget.append(("récit : étape", r1["mots"]))
        el_a = None
        for _ in range(40):
            await pd.wait_for_timeout(500)
            if await pd.evaluate("!!document.getElementById('suite') && !!document.getElementById('suite').offsetParent"): break
        el_a = await pd.evaluate("HDS.el"); await pd.wait_for_timeout(1500); el_b = await pd.evaluate("HDS.el")
        points = await pd.evaluate("document.querySelectorAll('#points i').length")
        await pd.click("#suite"); await pd.wait_for_timeout(1500); el_c = await pd.evaluate("HDS.el")
        note("récits en étapes, toucher pour continuer (F1)", abs(el_b - el_a) < 0.05 and el_c > el_b + 0.5 and points >= 3,
             f"arrêt à {el_a:.1f} s (puis {el_b:.1f}), reprise {el_c:.1f} s, {points} étapes", "« récits en étapes »")
        await pd.evaluate("HDS.recit('hubble')"); await pd.wait_for_timeout(500)
        # le « i » garde le texte complet
        await pd.click("#apropos"); await pd.wait_for_timeout(500)
        nps = await pd.evaluate("[...document.querySelectorAll('#modaleCorps p')].filter(p => p.offsetParent).length")
        note("le « i » garde le texte complet", nps >= 5, f"{nps} paragraphes", "« tout le texte disponible »")
        await pd.click("#fermer"); await pd.wait_for_timeout(300)
        # budget de mots, à chaque écran
        note("25 mots à l'écran au plus", max(n for _, n in budget) <= 25, " ; ".join(f"{k} {n}" for k, n in budget), "« minimiser la quantité de texte à la fois »")
        # visiteur qui revient : « Passer » mène droit à l'exploration libre
        await pd.goto(url); await pd.wait_for_selector("#partir", state="visible", timeout=15000); await pd.click("#partir"); await pd.wait_for_timeout(800)
        await pd.click("#passer"); await pd.wait_for_timeout(800)
        z4 = await pd.evaluate(MOTS)
        note("visiteur qui revient : tout de suite libre", "recits" in z4["commandes"] and "temps" in z4["commandes"], f"commandes {z4['commandes']}", "découverte faite une fois")
        # tailles des boutons (retour du 17 novembre 2026) : un bouton d'ouverture qui dit ce qu'il fait,
        # « Récits » action principale une fois la présentation finie, des cibles au doigt, un panneau sans sous-titres
        mot = await pd.evaluate("document.getElementById('partir').textContent.trim()")
        note("bouton d'ouverture : « Découvrir »", mot == "Découvrir", f"« {mot} »", "« le bouton partir n'est pas clair »")
        # identité visuelle (18/11, 9 h 48) : l'icône des trois horizons en favicon, dans la barre de titre,
        # à l'ouverture et dans « à propos » ; trois anneaux jamais sous 24 px (icône ≥ 32 px)
        idv = await pd.evaluate("""(async () => { const ic = [...document.querySelectorAll('link[rel~=icon]')].map(l => l.href);
          const svg = ic.find(h => h.startsWith('data:image/svg+xml')); let desc = '';
          if (svg) desc = decodeURIComponent(escape(atob(svg.split(',')[1])));
          const tl = document.querySelector('#titre img.logo'), ov = document.querySelector('#ouverture img.logo');
          document.getElementById('apropos').click(); await new Promise(r => setTimeout(r, 300));
          const md = document.querySelector('#modale img.logo'), mh = md ? md.getBoundingClientRect().height : 0; document.getElementById('fermer').click();
          return { favicon: desc.includes('Trois horizons'), titre: tl ? [tl.complete && tl.naturalWidth > 0, tl.getBoundingClientRect().height] : null,
                   ouverture: !!(ov && ov.getAttribute('src') === (tl && tl.getAttribute('src'))), modale: mh }; })()""")
        note("identité visuelle : l'icône des trois horizons", idv["favicon"] and idv["titre"] and idv["titre"][0] and idv["titre"][1] >= 32 and idv["ouverture"] and idv["modale"] >= 48,
             f"favicon {idv['favicon']}, barre de titre {idv['titre']}, ouverture {idv['ouverture']}, à propos {idv['modale']:.0f} px", "« utilise ces visuels pour l'application »")
        TAILLES = """(() => { const vis = el => { for (let a = el; a; a = a.parentElement) { const st = getComputedStyle(a); if (a.hidden || st.display === 'none' || st.visibility === 'hidden' || +st.opacity < 0.3) return false; } const r = el.getBoundingClientRect(); return r.width > 0 && r.bottom > 0 && r.top < innerHeight; };
          return [...document.querySelectorAll('button')].filter(vis).map(b => { const r = b.getBoundingClientRect(); return [b.id || b.dataset.scen || b.textContent.trim().slice(0, 10), Math.round(r.width), Math.round(r.height)]; }); })()"""
        rc = await pd.evaluate("""(() => { const b = document.getElementById('recits'), r = b.getBoundingClientRect(), br = document.getElementById('barreRecits').getBoundingClientRect(), st = getComputedStyle(b);
          return { fond: st.backgroundColor, accent: getComputedStyle(document.querySelector('button.principal') || b).backgroundColor, l: r.width, h: r.height, part: r.width / br.width, police: parseFloat(st.fontSize), bas: document.getElementById('bas').getBoundingClientRect().height }; })()""")
        acc = await pd.evaluate("(() => { const b = document.createElement('button'); b.className = 'principal'; document.body.appendChild(b); const c = getComputedStyle(b).backgroundColor; b.remove(); return c; })()")
        note("« Récits » : l'action principale, bien visible", rc["fond"] == acc and rc["h"] >= 48 and rc["part"] >= 0.6 and rc["police"] >= 16 and rc["bas"] <= 0.32 * 844,
             f"fond {rc['fond']}, {rc['l']:.0f}×{rc['h']:.0f} px ({rc['part']:.0%} de la barre), police {rc['police']:.0f} px, bas {rc['bas']:.0f} px",
             "« une fois la présentation faite, l'action principale devient récit : beaucoup plus gros »")
        # bas de l'écran centré, sur toute la largeur (18/11, 5 h 57) : « Récits » et la frise du temps
        cen = await pd.evaluate("""(() => { const W = innerWidth, r = document.getElementById('recits').getBoundingClientRect(), b = document.getElementById('bas').getBoundingClientRect(), tp = document.getElementById('temps').getBoundingClientRect();
          return { dec: (r.left + r.right) / 2 - W / 2, larg: r.width / W, bas: b.right / W, temps: tp.width / W, fin: (W - tp.right) }; })()""")
        note("bas de l'écran centré, sur toute la largeur", abs(cen["dec"]) <= 4 and cen["larg"] >= 0.88 and cen["bas"] >= 0.995 and cen["temps"] >= 0.7 and cen["fin"] <= 24,
             f"« Récits » décalé de {cen['dec']:.0f} px, {cen['larg']:.0%} de l'écran ; zone du bas jusqu'à {cen['bas']:.0%} ; frise {cen['temps']:.0%}, finit à {cen['fin']:.0f} px du bord",
             "« problème de centrage en bas : le bouton et la barre ne prennent pas l'ensemble de l'écran »")
        t_libre = await pd.evaluate(TAILLES)
        await pd.click("#recits"); await pd.wait_for_timeout(500)
        t_pan = await pd.evaluate(TAILLES)
        pan = await pd.evaluate("""(() => { const p = document.getElementById('panneauRecits'), lp = p.clientWidth - 28;
          const bs = [...p.querySelectorAll('button[data-scen]')].map(b => { const r = b.getBoundingClientRect(); return [r.width / lp, r.height, parseFloat(getComputedStyle(b).fontSize)]; });
          const sous = [...p.querySelectorAll('span')].filter(s => s.offsetParent && s.textContent.trim()).length; return { bs, sous }; })()""")
        ferme = await pd.evaluate("(() => { const f = document.getElementById('fermeRecits'); if (!f) return false; f.click(); return document.getElementById('panneauRecits').hidden; })()")
        await pd.wait_for_timeout(300)
        # pendant un récit : la croix, les étapes, « Suite » — rien de tronqué
        await pd.evaluate("HDS.recit('hubble')"); await pd.wait_for_timeout(800); await pd.click("#cestParti")
        for _ in range(60):
            await pd.wait_for_timeout(500)
            if await pd.evaluate("!!document.getElementById('suite').offsetParent"): break
        t_rec = await pd.evaluate(TAILLES)
        tronque = await pd.evaluate("[...document.querySelectorAll('#barreRecits button')].filter(b => b.offsetParent && b.scrollWidth > b.clientWidth + 1).map(b => b.id)")
        await pd.evaluate("HDS.recit('hubble')"); await pd.wait_for_timeout(500)
        t_libre += t_rec
        petits = [x for x in t_libre + t_pan if x[1] < 40 or x[2] < 40] + [[i, "tronqué"] for i in tronque]
        note("boutons à la taille du doigt (≥ 40 px)", not petits, f"trop petits : {petits}" if petits else f"{len(t_libre)} + {len(t_pan)} boutons mesurés", "« tout est aussi petit »")
        note("panneau des récits : le titre seul, gros boutons", ferme and pan["sous"] == 0 and all(l >= 0.85 and h >= 48 and f >= 16 for l, h, f in pan["bs"]),
             f"refermable {ferme} ; {pan['sous']} sous-titres visibles ; boutons {[(round(l, 2), round(h), round(f)) for l, h, f in pan['bs']]}", "« les récits peuvent n'avoir que le texte du bouton »")
        # ordre, annonce et un seul espace de récit (17/11, 22 h 43) : les trois frontières d'abord ; après
        # l'appui, on sait ce qu'on va voir (la définition courte) ; tout le texte du récit au même endroit, en bas
        ordreR = await pd.evaluate("[...document.querySelectorAll('#panneauRecits button[data-scen]')].map(b => b.dataset.scen)")
        note("récits : les trois frontières d'abord", ordreR == ["observable", "hubble", "evenements", "promenade", "toile"], f"{ordreR}",
             "« l'univers observable en premier, puis Hubble, l'horizon, la Voie lactée, la toile »")
        ESPACE = """(() => { const i = document.getElementById('intro'), p = document.getElementById('phrase'), H = innerHeight;
          const vis = el => { for (let a = el; a; a = a.parentElement) { const st = getComputedStyle(a); if (a.hidden || st.display === 'none' || st.visibility === 'hidden' || +st.opacity < 0.3) return false; } return el.getBoundingClientRect().height > 0; };
          return { intro: vis(i), txt: i.textContent.replace(/\\s+/g, ' ').trim(), haut: i.getBoundingClientRect().top / H, phrase: vis(p) && p.textContent.trim() ? p.getBoundingClientRect().top / H : null }; })()"""
        annonces, budgetR = [], []
        for cle, mot in (("observable", "transparent"), ("hubble", "vitesse de la lumière"), ("evenements", "message"), ("promenade", "galaxie"), ("toile", "filaments")):
            await pd.evaluate("HDS.demarrerLibre()"); await pd.wait_for_timeout(300)
            await pd.click("#recits"); await pd.wait_for_timeout(400)
            await pd.click(f"#panneauRecits button[data-scen={cle}]"); await pd.wait_for_timeout(1200)
            av = await pd.evaluate(ESPACE); budgetR.append((cle, (await pd.evaluate(MOTS))["mots"]))
            if av["intro"]: await pd.evaluate("document.getElementById('cestParti').click()")
            await pd.wait_for_timeout(2500); ap = await pd.evaluate(ESPACE)
            annonces.append((cle, mot, av, ap))
            await pd.evaluate(f"HDS.recit('{cle}')"); await pd.wait_for_timeout(500)
        fin = await pd.evaluate("(() => { const f = document.getElementById('finObs'); f.hidden = false; const h = f.getBoundingClientRect().top / innerHeight; f.hidden = true; return h; })()")
        mauvais = [c for c, m, av, ap in annonces if not (av["intro"] and m in av["txt"].lower() and av["haut"] > 0.5 and not ap["intro"] and (ap["phrase"] is None or ap["phrase"] > 0.5))]
        note("récit annoncé, puis raconté au même endroit (en bas)", not mauvais and fin > 0.5 and max(n for _, n in budgetR) <= 25,
             f"en défaut {mauvais} ; annonce en haut de l'écran à {[round(av['haut'], 2) for _, _, av, _ in annonces]} ; fin d'observable à {fin:.2f} ; mots {budgetR}",
             "« une idée de ce qu'on va voir » ; « un seul espace de récit, soit en haut soit en bas »")
        # couleur des photons selon leur vitesse par rapport à nous (17/11, 23 h 30) : rouges s'ils s'éloignent,
        # blancs immobiles, bleus ou violets s'ils approchent ; mesuré sur la couleur dessinée et sur l'image
        await pd.evaluate("HDS.demarrerLibre(); HDS.recit('observable')"); await pd.wait_for_timeout(1500)
        await pd.evaluate("document.getElementById('cestParti').click()"); await pd.wait_for_timeout(1500)
        await pd.evaluate("HDS.vitesse = 0")
        coul = []
        for tc in (0.05, 1.0, 6.0, 12.5):
            await pd.evaluate(f"HDS.aller({tc})"); await pd.wait_for_timeout(2500)
            ph = await pd.evaluate("HDS.photons"); Wc = await pd.evaluate("HDS.W")
            Lc = np.asarray(Image.open(io.BytesIO(await pd.screenshot())).convert("RGB")).astype(float)
            if not ph or ph[0] is None: coul.append((tc, None, None, None)); continue
            R = ph[0]["r"] * 173 / Wc; yy, xx = np.mgrid[0:844, 0:390]; d = np.hypot(xx - 173, yy - 844 * 0.44)
            zone = (yy < 560) & (xx < 340)
            def teinte(m):
                px = Lc[m & zone]; px = px[(px.max(1) > 110) & (px.max(1) - px.min(1) > 35)]
                return float((px[:, 0] - px[:, 2]).mean()) if len(px) > 20 else 0.0
            coul.append((tc, ph[0]["v"], ph[0]["rgb"], teinte((d > R - 6) & (d < R + 32)) - teinte((d > R + 60) & (d < R + 98))))
        await pd.evaluate("HDS.vitesse = 1; HDS.recit('observable')"); await pd.wait_for_timeout(400)
        def accord(v, rgb, dt):
            if v is None: return False
            if v > 0.1: return rgb[0] - rgb[2] > 60 and dt > 20
            if v < -0.1: return rgb[2] - rgb[0] > 60 and dt < -20
            return min(rgb) > 190
        note("photons : rouges s'ils s'éloignent, blancs immobiles, bleus s'ils approchent", all(accord(v, c, dt) for _, v, c, dt in coul) and any(v is not None and v > 0.1 for _, v, _, _ in coul) and any(v is not None and v < -0.1 for _, v, _, _ in coul),
             " ; ".join(f"{tc} Ga : v {v if v is None else round(v, 2)} c, {c}, image {dt if dt is None else round(dt)}" for tc, v, c, dt in coul),
             "« rouge s'ils s'éloignent, blanc statiques, bleu ou violet s'ils se rapprochent »")
        # un vrai doigt sur les curseurs (écran tactile simulé) : ils doivent avoir leur longueur et répondre
        tc = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True, is_mobile=True)
        pt = await tc.new_page(); await pt.goto(url); await pt.wait_for_selector("#partir", state="visible", timeout=20000)
        # les deux boutons d'ouverture par programme : ce contrôle-ci porte sur les curseurs, au doigt
        await pt.evaluate("document.getElementById('partir').click()"); await pt.wait_for_timeout(1000)
        await pt.evaluate("document.getElementById('passer').click()"); await pt.wait_for_timeout(1500)
        cdp = await tc.new_cdp_session(pt)
        async def glisse(sel, vertical):
            r = await pt.evaluate(f"(() => {{ const z = document.querySelector('{sel}').getBoundingClientRect(); return [z.left, z.top, z.width, z.height]; }})()")
            lg = r[3] if vertical else r[2]
            pts = [(r[0] + r[2] / 2, r[1] + r[3] * (0.6 - 0.04 * k)) if vertical else (r[0] + r[2] * (0.8 - 0.05 * k), r[1] + r[3] / 2) for k in range(9)]
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": pts[0][0], "y": pts[0][1]}]})
            for x_, y_ in pts[1:]:
                await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x_, "y": y_}]}); await pt.wait_for_timeout(30)
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); await pt.wait_for_timeout(500)
            return lg
        W0 = await pt.evaluate("HDS.W"); lz = await glisse("#zoom", True); W1 = await pt.evaluate("HDS.W")
        t0_ = await pt.evaluate("HDS.t"); lt = await glisse("#temps", False); t1_ = await pt.evaluate("HDS.t")
        await tc.close()
        rz = W0 / W1 if W1 > 0 else 0
        note("curseurs au doigt : longueur et réponse", lz > 250 and lt > 150 and 1.5 < rz < 1e4 and t1_ < t0_ - 0.5,
             f"zoom {lz:.0f} px, champ ×1/{rz:.1f} ; temps {lt:.0f} px, {t0_:.2f} → {t1_:.2f} Ga", "« le curseur de navigation dans l'espace ne fonctionne plus »")
        note("découverte sans erreur JavaScript", not perr, f"{len(perr)} erreur(s) {perr[:1]}", "—")
        await pd.close()
        # 10 septies. réseau capricieux : une tuile qui ne vient pas ne fige pas la Promenade
        pg2 = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        coups = {"n": 0}
        async def coupe(route):
            coups["n"] += 1; await route.abort()
        await pg2.route("**/tuiles/grande-a0.0909.jpg*", coupe)                 # toujours en échec
        ratee_une = {"n": 0}
        async def une_fois(route):
            ratee_une["n"] += 1
            if ratee_une["n"] == 1: await route.abort()
            else: await route.continue_()
        await pg2.route("**/tuiles/petite-a0.5000.jpg*", une_fois)              # échec passager
        await pg2.goto(url); await pg2.wait_for_selector("#partir", state="visible", timeout=20000)
        await pg2.click("#partir"); await pg2.wait_for_timeout(16000)
        e_p = await pg2.evaluate("HDS.el"); sc = await pg2.evaluate("HDS.etat"); dsp = await pg2.evaluate("HDS.dispo")
        # figée, la Promenade resterait à 0,5 s (elle attend la tuile) ; au-delà de 1 s, elle avance — ce
        # navigateur sans carte graphique dessine lentement les points : on ne mesure pas sa vitesse ici
        note("tuile manquante : la Promenade avance", sc["scen"] == "promenade" and e_p > 1 and min(dsp[3:]) >= 1,
             f"{e_p:.1f} s de scénario après 16 s ; {coups['n']} essais sur la tuile coupée, {ratee_une['n']} sur la passagère", "« la promenade ne se lance pas, écran figé à 95 % »")
        note("échec passager : la tuile est rechargée", ratee_une["n"] >= 2, f"{ratee_une['n']} requêtes", "« figé à 95 % »")
        await pg2.close()
        # 11. aucune erreur JavaScript
        note("aucune erreur JavaScript", not err, f"{len(err)} erreur(s)", "—")
        await b.close()
    print(f"\n{sum(RES)} contrôles passés, {len(RES) - sum(RES)} en échec")
    sys.exit(0 if all(RES) else 1)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/index.html"))
