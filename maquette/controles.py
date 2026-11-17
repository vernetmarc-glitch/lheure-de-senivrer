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
        await pg.evaluate("document.getElementById('modale').classList.remove('ouverte')")

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
        await pg.click("[data-scen=hubble]"); await pg.wait_for_timeout(2500)
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
        await pg.click("[data-scen=observable]"); await pg.wait_for_timeout(1500); await pg.click("#cestParti"); await pg.wait_for_timeout(9000)
        avant = await pg.evaluate("HDS.t"); await pg.click("[data-scen=observable]"); await pg.wait_for_timeout(600)
        e = await pg.evaluate("HDS.etat"); apres = await pg.evaluate("HDS.t")
        note("second appui : retour à l'exploration", e["scen"] is None and e["fronts"] == 0 and abs(apres - avant) < 0.5,
             f"scénario {e['scen']}, {e['fronts']} lumière(s), t {avant:.1f} → {apres:.1f} Ga", "« je ne sais pas revenir à la vue par défaut »")
        # 9 sexies. « aujourd'hui » ramène au présent
        await vue(0.15, 5.0, 300); await pg.click("#repAuj"); await pg.wait_for_timeout(400)
        ta = await pg.evaluate("HDS.t")
        note("bouton « aujourd'hui »", abs(ta - 13.787) < 0.05, f"t = {ta:.2f} Ga", "« appuyer sur aujourd'hui pour explorer »")
        # 9 septies. Promenade : plongée jusqu'à la galaxie plein écran, retour à ~1 Ga, curseurs qui pulsent
        await vue(0.15, 13.787, 300); await pg.click("[data-scen=promenade]"); await pg.wait_for_timeout(1200)
        await pg.wait_for_timeout(1500); W0 = await pg.evaluate("HDS.W")
        await pg.evaluate("HDS.el = 7"); await pg.wait_for_timeout(900)
        z_pulse = await pg.evaluate("document.getElementById('zoom').classList.contains('bouge')")
        tz = []
        for e_ in (15.5, 17.5, 19.2):
            await pg.evaluate(f"HDS.el = {e_}"); await pg.wait_for_timeout(500); tz.append(await pg.evaluate("HDS.t"))
        note("Promenade : le temps attend la fin du zoom", max(tz) >= 13.77, f"t pendant le recul : {[round(x, 2) for x in tz]}", "« ne remonte pas le temps pendant le dézoom final »")
        Ws = []
        for e_ in (13.6, 14.5, 15.4):
            await pg.evaluate(f"HDS.el = {e_}"); await pg.wait_for_timeout(700); Ws.append(await pg.evaluate("HDS.W"))
        W14 = Ws[1]
        note("Promenade : plongée et recul d'un seul mouvement", Ws[0] > 1.03 * Ws[1] and Ws[2] > 1.03 * Ws[1],
             f"champ {Ws[0]:.2e} → {Ws[1]:.2e} → {Ws[2]:.2e} Gal (à ±0,9 s du fond)", "« pas de pause entre le zoom et le dézoom »")
        await pg.evaluate("HDS.el = 22"); await pg.wait_for_timeout(1500)
        t_pulse = await pg.evaluate("document.getElementById('temps').classList.contains('bouge')")
        async def vitesse(t0):
            await pg.evaluate(f"HDS.aller({t0})"); await pg.wait_for_timeout(400)
            a, ea = await pg.evaluate("[HDS.t, HDS.el]"); await pg.wait_for_timeout(2500); b, eb = await pg.evaluate("[HDS.t, HDS.el]")
            return (a - b) / max(eb - ea, 1e-6)                 # Ga par seconde de scénario (indépendant de la machine)
        v_vite, v_collision = await vitesse(11.0), await vitesse(6.0)
        Wrecul = await pg.evaluate("HDS.W")
        await pg.evaluate("HDS.aller(1.25)"); fin = 99
        for _ in range(10):
            await pg.wait_for_timeout(250); fin = min(fin, await pg.evaluate("HDS.t"))
        note("Promenade : plongée, puis on remonte le temps", W14 <= 7e-5 and v_collision > 0 and v_vite >= 2.5 * v_collision and fin <= 1.21 and 1.3e-4 <= Wrecul <= 2.0e-4,
             f"champ {W14:.1e} Gal ; recul ×{v_vite / max(v_collision, 1e-9):.1f} plus vite avant les collisions ; champ en remontant {Wrecul:.1e} ; arrêt à {fin:.2f} Ga",
             "« se délite petit à petit » ; « accélérer jusqu'à 7 Ga, ralentir aux collisions » ; « dézoomer un peu moins, galaxie plus grosse » (17/11 : remplace « voir les environs », champ ≥ 2,5e-4)")
        note("Promenade : départ à l'échelle de la toile cosmique", W0 >= 1.0, f"champ de départ {W0:.2f} Gal", "« commencer à la toile cosmique, pas aux superamas »")
        note("curseurs qui bougent : pulsation", z_pulse and t_pulse, f"zoom {z_pulse}, temps {t_pulse}", "« repérer ceux qui bougent »")
        # fin de la Promenade : retour fluide à aujourd'hui, au champ Millennium, scénario désactivé
        suite = []
        for _ in range(200):                                   # jusqu'à la fin réelle du scénario (60 s au plus)
            await pg.wait_for_timeout(300); suite.append(await pg.evaluate("[HDS.t, HDS.W, HDS.etat.scen]"))
            if suite[-1][2] is None: break
        actif = await pg.evaluate("!!document.querySelector('.scen button.actif')")
        ts = [x[0] for x in suite if x[2] == "promenade"]; Wf = suite[-1][1]
        saut = max(abs(b_ - a_) for a_, b_ in zip(ts, ts[1:])) if len(ts) > 1 else 99
        note("Promenade : retour fluide au présent", suite[-1][2] is None and not actif and abs(suite[-1][0] - 13.787) < 0.02 and 0.15 <= Wf <= 0.3 and saut < 1.6,
             f"fin t = {suite[-1][0]:.2f} Ga, champ {Wf:.2f} Gal, plus grand pas {saut:.2f} Ga/0,3 s, scénario {suite[-1][2]}, bouton actif {actif}",
             "« revenir de manière fluide au temps présent, zoom superamas, désactiver Promenade »")
        # 9 octies. Univers observable : d'abord l'explication, le départ au bouton « C'est parti »
        await pg.click("[data-scen=observable]"); await pg.wait_for_timeout(3000)
        ta = await pg.evaluate("HDS.t"); vis = await pg.evaluate("!document.getElementById('intro').hidden")
        await pg.click("#cestParti"); await pg.wait_for_timeout(6000); tb = await pg.evaluate("HDS.t")
        note("Observable : explication puis départ", vis and ta < 0.0004 and tb > ta * 1.5, f"attente à {ta * 1e6:.0f}000 ans, puis {tb:.3f} Ga", "« un message, puis un bouton c'est parti »")
        await pg.evaluate("HDS.aller(13.7)"); await pg.wait_for_timeout(9000)
        fin_vis = await pg.evaluate("!document.getElementById('finObs').hidden")
        intro_txt = await pg.evaluate("document.getElementById('intro').textContent")
        note("Observable : tapis roulant annoncé, 46 Gal à la fin", fin_vis and "tapis roulant" in intro_txt, f"fourmis {'tapis roulant' in intro_txt}, fenêtre de fin {fin_vis}", "« fourmis sur un tapis roulant » ; « 46 milliards à la fin »")
        await pg.click("[data-scen=observable]"); await pg.wait_for_timeout(300)
        # 10. pas de gel quand la Voie lactée se charge (on recharge la page, on zoome tout de suite)
        await pg.goto(url); await pg.wait_for_timeout(5000)
        await pg.evaluate("document.getElementById('modale').classList.remove('ouverte')")
        gel = await pg.evaluate("""new Promise(res => { let p = performance.now(), mx = 0, t0 = p;
          const z = document.getElementById('zoom'); z.value = 40; z.dispatchEvent(new Event('input'));
          const f = () => { const n = performance.now(); mx = Math.max(mx, n - p); p = n; if (n - t0 < 9000) requestAnimationFrame(f); else res(mx); };
          requestAnimationFrame(f); })""")
        note("pas de gel au chargement de la galaxie", gel < max(600, 1.2 * d0), f"plus longue image {gel:.0f} ms", "« ça rame énormément »")
        # 10 quinquies bis. Horizon : une explication avant l'acte 1, une autre avant l'acte 2
        await pg.click("[data-scen=evenements]"); await pg.wait_for_timeout(2500)
        vis1 = await pg.evaluate("!document.getElementById('intro').hidden")
        txt1 = await pg.evaluate("document.getElementById('intro').textContent"); t1 = await pg.evaluate("HDS.t")
        await pg.evaluate("document.getElementById('cestParti').click()"); await pg.wait_for_timeout(5000); t1b = await pg.evaluate("HDS.t")
        await pg.evaluate("HDS.aller(99.9)"); await pg.wait_for_timeout(7000)
        e2 = await pg.evaluate("HDS.etat"); vis2 = await pg.evaluate("!document.getElementById('intro').hidden")
        txt2 = await pg.evaluate("document.getElementById('intro').textContent"); t2 = await pg.evaluate("HDS.t")
        await pg.wait_for_timeout(2000); t2a = await pg.evaluate("HDS.t")
        await pg.evaluate("document.getElementById('cestParti').click()"); await pg.wait_for_timeout(5000); t2b = await pg.evaluate("HDS.t")
        ok = (vis1 and "acte 1" in txt1 and abs(t1 - 13.787) < 0.02 and t1b > 14.5
              and e2.get("acte") == 2 and vis2 and "acte 2" in txt2 and abs(t2a - 13.787) < 0.02 and t2b > 14.5)
        note("Horizon : une explication par acte", ok,
             f"acte 1 : fenêtre {vis1}, t {t1:.2f} → {t1b:.1f} Ga ; acte 2 : acte {e2.get('acte')}, fenêtre {vis2}, t {t2a:.2f} → {t2b:.1f} Ga",
             "« une modale pour l'acte 1 et une autre pour l'acte 2 »")
        await pg.click("[data-scen=evenements]"); await pg.wait_for_timeout(800)
        # 10 quater. frise du temps : jusqu'à aujourd'hui en libre, futur seulement pendant l'horizon
        libre_max = await pg.evaluate("+document.getElementById('temps').max")
        await pg.click("[data-scen=evenements]"); await pg.wait_for_timeout(1200)
        hor_max = await pg.evaluate("+document.getElementById('temps').max")
        await pg.click("[data-scen=evenements]"); await pg.wait_for_timeout(800)
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
        # 10 quinquies. l'accueil propose la Promenade, qui se lance ; son bouton est le premier
        await pg.goto(url); await pg.wait_for_timeout(2500)
        lab = await pg.evaluate("document.getElementById('fermer').textContent")
        premier = await pg.evaluate("document.querySelector('.scen button').dataset.scen")
        await pg.click("#fermer"); await pg.wait_for_timeout(800)
        e = await pg.evaluate("HDS.etat")
        note("accueil → Promenade", "promenade" in lab.lower() and e["scen"] == "promenade" and premier == "promenade", f"« {lab} », scénario {e['scen']}, premier bouton {premier}", "« commençons par une promenade »")
        # 10 sexies. accueil : le premier paragraphe du texte, « plus… » pour le reste, un seul bouton pleine largeur
        await pg.goto(url); await pg.wait_for_timeout(1500)
        g = await pg.evaluate("""(() => { const f = document.getElementById('fermer').getBoundingClientRect(),
          c = document.querySelector('#modale > div').getBoundingClientRect(),
          ps = [...document.querySelectorAll('#modaleCorps p')].filter(p => p.offsetParent !== null),
          lien = document.querySelector('#modaleCorps .lirePlus');
          return { lf: f.width, lc: c.width, vus: ps.length, lien: !!lien && lien.offsetParent !== null,
                   boutons: document.querySelectorAll('#modaleBoutons button').length,
                   premier: ps.length ? ps[0].textContent : '' }; })()""")
        await pg.evaluate("document.querySelector('#modaleCorps .lirePlus') && document.querySelector('#modaleCorps .lirePlus').click()"); await pg.wait_for_timeout(300)
        tous = await pg.evaluate("[...document.querySelectorAll('#modaleCorps p')].filter(p => p.offsetParent !== null).length")
        cle = all(m in g["premier"] for m in ("univers observable", "sphère de Hubble", "horizon des événements", "temps"))
        note("accueil : premier paragraphe, « plus… », un bouton", g["lf"] > 0.8 * g["lc"] and g["vus"] == 1 and g["lien"] and g["boutons"] == 1 and tous >= 3 and cle,
             f"{g['vus']} paragraphe visible puis {tous}, lien {g['lien']}, {g['boutons']} bouton(s) de {g['lf']:.0f}/{g['lc']:.0f} px, notions clés {cle}",
             "« premier paragraphe avec l'information clé, plus… pour agrandir, plus de bouton en savoir plus »")
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
        await pg2.goto(url); await pg2.wait_for_timeout(1500)
        await pg2.click("#fermer"); await pg2.wait_for_timeout(16000)
        e_p = await pg2.evaluate("HDS.el"); sc = await pg2.evaluate("HDS.etat"); dsp = await pg2.evaluate("HDS.dispo")
        note("tuile manquante : la Promenade avance", sc["scen"] == "promenade" and e_p > 3 and min(dsp[3:]) >= 1,
             f"{e_p:.1f} s de scénario après 16 s ; {coups['n']} essais sur la tuile coupée, {ratee_une['n']} sur la passagère", "« la promenade ne se lance pas, écran figé à 95 % »")
        note("échec passager : la tuile est rechargée", ratee_une["n"] >= 2, f"{ratee_une['n']} requêtes", "« figé à 95 % »")
        await pg2.close()
        # 11. aucune erreur JavaScript
        note("aucune erreur JavaScript", not err, f"{len(err)} erreur(s)", "—")
        await b.close()
    print(f"\n{sum(RES)} contrôles passés, {len(RES) - sum(RES)} en échec")
    sys.exit(0 if all(RES) else 1)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/index.html"))
