"""Contrôles de la page labo « La Terre vue de l'espace : continents » (chantier S3).

Mesure la page SERVIE (app/public/labo/terre/index.html, données publiées comprises),
pas un aperçu. Chaque mesure passe par le même shader que le globe : l'état du relief
à l'instant t est lu dans la texture d'état que le globe échantillonne.

  C1  aucune erreur JavaScript ; WebGL2 disponible
  C2  aujourd'hui : terres et mers coïncident à 95 % (en aire) avec le relief actuel
      (référence indépendante : Natural Earth 1:50 m, controles/terres-actuelles-ne50m.png)
  C3  Pangée : entre 320 et 200 Ma, au moins 80 % des terres émergées en un seul bloc
  C4  pas de fantôme : pendant une dérive, aucun pixel du globe plus sombre que ses deux
      états voisins (tolérance : 0,2 % des pixels du disque, écart de luminance > 0,05)
  C5  pas de saut : la surface émergée varie continûment (aucun saut > 1 % des terres
      entre deux instants distants de 0,5 Ma), raccord des deux modèles à 540 Ma compris
  C6  frise : 1 Ga -> 0 occupe 1000/4540 de la frise (à 1 % près) ; avant 1 Ga, segment
      hachuré « hypothèse » ; bande Pangée + chaîne hercynienne à sa proportion ;
      curseur à sa place
  C7  Soleil de juin, fixe : point subsolaire à 23,44° N à tout instant ; au terminateur,
      la calotte nord est éclairée et la calotte sud dans la nuit
  C8  liseré d'atmosphère : un mince anneau bleu hors du disque, côté jour
  C9  interaction : le doigt fait tourner le globe ; lecture fait avancer le temps
  C10 signature de la référence visuelle (N25, NASA Blue Marble NG, juin 2004, sans nuages) :
      aujourd'hui, sur le globe rendu (zone éclairée à moins de 32° du point subsolaire),
      couleur médiane des terres et des mers à ΔE ≤ 10 du composite de juin aux mêmes
      lieux ; mers plus sombres que terres
  C11 compteur de vitesse du temps (N28) : présent, lisible (≥ 56 px), hors du globe ;
      aiguille sur la butée à l'arrêt ; en lecture, angle = vitesse réelle du curseur
      (échelle log, à 1° près après amortissement) ; lecture chiffrée en clair

Usage : python3 app/public/labo/terre/controles.py   (code de sortie 0 si tout passe)
"""
import asyncio, base64, functools, http.server, json, math, socket, sys, threading, pathlib
import numpy as np
from PIL import Image

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent.parent            # app/public
URL_PAGE = "/labo/terre/index.html?test=1"
RES = []


def port_libre():
    for p in range(8830, 8840):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p)); return p
            except OSError:
                pass
    raise SystemExit("aucun port libre entre 8830 et 8839")


def servir(port):
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    h = functools.partial(H, directory=str(RACINE))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def note(code, ok, detail):
    RES.append((code, bool(ok), detail))
    print(f"{'OK   ' if ok else 'ÉCHEC'} {code}  {detail}", flush=True)


def poids_aire(h, w):
    lat = 90 - (np.arange(h) + .5) * 180 / h
    return np.cos(np.radians(lat))[:, None] * np.ones((1, w))


def composantes(masque):
    """Étiquetage 8-connexe sur la sphère équirectangulaire (raccord en longitude)."""
    from scipy import ndimage
    h, w = masque.shape
    lab, n = ndimage.label(masque, structure=np.ones((3, 3)))
    # raccord du méridien 180° : union des étiquettes des colonnes 0 et w-1
    parent = list(range(n + 1))
    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for j in range(h):
        for dj in (-1, 0, 1):
            jj = j + dj
            if 0 <= jj < h and lab[j, 0] and lab[jj, w - 1]:
                a, b = f(lab[j, 0]), f(lab[jj, w - 1])
                if a != b: parent[a] = b
    # pôles : une rangée polaire entière est d'un seul tenant
    for j in (0, h - 1):
        ids = [f(x) for x in np.unique(lab[j]) if x]
        for x in ids[1:]: parent[f(x)] = f(ids[0])
    racines = np.array([f(i) for i in range(n + 1)])
    return racines[lab], n


async def etat(pg, t):
    """Élévation (m) de la texture d'état à l'instant t, telle que le globe l'échantillonne."""
    r = await pg.evaluate("async t => { await terre.regler({t}); return terre.etatEquirect(); }", t)
    brut = np.frombuffer(base64.b64decode(r["rgba"]), np.uint8).reshape(r["h"], r["w"], 4)
    code = brut[..., 0].astype(np.float64) * 256 + brut[..., 1]
    elev = code / 65535.0 * (r["hmax"] - r["hmin"]) + r["hmin"]
    return elev[::-1] if r.get("basEnHaut") else elev


async def ecran(pg):
    b = await pg.locator("#globe").screenshot()
    import io
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGB")).astype(np.float64) / 255


def lum(img):
    return img @ np.array([0.2126, 0.7152, 0.0722])


def lab(rgb):
    """sRGB (0–1) -> CIELAB D65."""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def ciel_bm(rgb, geo, sol, bm, ne):
    """Compare, pixel à pixel sur le globe rendu, aux mêmes lieux, la couleur médiane des terres
    et des mers à celle de Blue Marble (zone μ > 0,85, soit < 32° du point subsolaire)."""
    H, W = rgb.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    x = (xx + .5 - geo["cx"]) / geo["r"]; y = -(yy + .5 - geo["cy"]) / geo["r"]
    r2 = x * x + y * y; d = r2 < 0.97
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    la, lo = np.radians(sol["lat"]), np.radians(sol["lon"])
    e = np.array([-np.sin(lo), np.cos(lo), 0]); n = np.array([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)])
    c = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    P = x[..., None] * e + y[..., None] * n + z[..., None] * c
    mu = P @ c
    sel = d & (mu > 0.85)
    lat = np.degrees(np.arcsin(np.clip(P[..., 2], -1, 1)))[sel]; lon = np.degrees(np.arctan2(P[..., 1], P[..., 0]))[sel]
    def prend(img):
        h, w = img.shape[:2]
        j = np.clip(((90 - lat) / 180 * h).astype(int), 0, h - 1); i = np.clip(((lon + 180) / 360 * w).astype(int), 0, w - 1)
        return img[j, i]
    terre = prend(ne)
    Lr, Lb = lab(rgb[sel]), lab(prend(bm))
    res, ok = [], True
    for nom, m in (("terres", terre), ("mers", ~terre)):
        if m.sum() < 200: ok = False; res.append(f"{nom} : trop peu de pixels"); continue
        a, b = np.median(Lr[m], 0), np.median(Lb[m], 0)
        dE = float(np.linalg.norm(a - b)); ok &= dE <= 10
        res.append(f"{nom} ΔE {dE:.1f} (rendu L*a*b* {np.round(a, 1).tolist()}, Blue Marble {np.round(b, 1).tolist()})")
    Lt, Lm = np.median(Lr[terre][:, 0]), np.median(Lr[~terre][:, 0])
    ok &= Lm < Lt; res.append(f"L* mers {Lm:.1f} < terres {Lt:.1f}")
    return ok, " ; ".join(res)


async def main():
    from playwright.async_api import async_playwright
    port = port_libre(); srv = servir(port)
    base = f"http://127.0.0.1:{port}"
    erreurs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                    args=["--no-sandbox", "--ignore-gpu-blocklist"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1,
                                  has_touch=True)
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: erreurs.append(f"pageerror: {e}"))
        pg.on("console", lambda m: erreurs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        rep = await pg.goto(base + URL_PAGE)
        try:
            if rep is None or rep.status != 200:
                raise RuntimeError(f"page absente (HTTP {rep.status if rep else '—'})")
            await pg.wait_for_function("window.terre && window.terre.pret === true", timeout=120000)
        except Exception as e:
            note("C1", False, f"page non chargée : {e}".splitlines()[0])
            for c in ("C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11"):
                note(c, False, "page non chargée")
            await b.close(); srv.shutdown(); return 1

        # ---- C2 aujourd'hui
        e0 = await etat(pg, 0.0)
        ref = np.asarray(Image.open(ICI / "controles" / "terres-actuelles-ne50m.png")) > 127
        h, w = e0.shape
        if ref.shape != (h, w):
            ref = np.asarray(Image.open(ICI / "controles" / "terres-actuelles-ne50m.png")
                             .resize((w, h), Image.BOX)) > 127
        W = poids_aire(h, w)
        acc = (W * ((e0 > 0) == ref)).sum() / W.sum()
        note("C2", acc >= 0.95, f"accord terres/mers aujourd'hui = {acc*100:.2f} % (seuil 95 %)")

        # ---- C3 Pangée
        pires = []
        for t in (320, 300, 280, 260, 240, 220, 200):
            e = await etat(pg, float(t))
            m = e > 0
            lab, n = composantes(m)
            ww = poids_aire(*m.shape)
            aires = np.bincount(lab[m].ravel(), weights=ww[m].ravel())
            part = aires.max() / aires.sum() if aires.sum() > 0 else 0
            mc_ = e > -200
            labc, _ = composantes(mc_)
            ac = np.bincount(labc[mc_].ravel(), weights=ww[mc_].ravel())
            pires.append((t, part, ac.max() / ac.sum() if ac.sum() > 0 else 0))
        mini = min(p for _, p, _ in pires)
        note("C3", mini >= 0.80, "plus grand bloc / terres émergées : " +
             ", ".join(f"{t} Ma {p*100:.0f} %" for t, p, _ in pires) + " (seuil 80 %) ; pour information, "
             "bloc continental (> -200 m) : " + ", ".join(f"{t} Ma {q*100:.0f} %" for t, _, q in pires))

        # ---- C4 pas de fantôme (sur l'écran, globe tel que vu)
        await pg.evaluate("terre.regler({lon: 10, lat: 15})")
        pire = (0, None)
        for t in (2.5, 52.5, 252.5, 302.5, 537.5, 541.0, 545.0, 552.0, 575.0, 755.0, 995.0):
            ims = []
            for tt in (t - 0.5, t, t + 0.5):
                await pg.evaluate("t => terre.regler({t})", tt)
                ims.append(lum(await ecran(pg)))
            a, m_, c = ims
            disque = (a > 0.02) | (c > 0.02)
            sombre = (m_ < np.minimum(a, c) - 0.05) & disque
            frac = sombre.sum() / max(disque.sum(), 1)
            if frac >= pire[0]: pire = (frac, t)
        note("C4", pire[0] < 0.002, f"pixels plus sombres que leurs deux voisins : "
             f"{pire[0]*100:.3f} % au pire (à {pire[1]} Ma ; seuil 0,2 %)")

        # ---- C5 pas de saut
        r = await pg.evaluate("""async () => {
            const out = [];
            for (const [a, b] of [[0, 12], [245, 257], [528, 562], [985, 1000]]) {
              const s = [];
              for (let t = a; t <= b + 1e-9; t += 0.5) { await terre.regler({t}); s.push([t, terre.aireTerres()]); }
              out.push(s); }
            return out; }""")
        sauts = [(s[i][0], abs(s[i][1] - s[i-1][1]) / max(s[i][1], s[i-1][1], 1e-9))
                 for s in r for i in range(1, len(s))]
        smax = max(sauts, key=lambda x: x[1])
        note("C5", smax[1] < 0.01, f"plus grand saut de surface émergée : {smax[1]*100:.2f} % "
             f"(vers {smax[0]} Ma ; seuil 1 %)")

        # ---- C6 frise
        fr = await pg.evaluate("""async () => {
            const box = s => { const e = document.querySelector(s); if (!e) return null;
                               const r = e.getBoundingClientRect(); return [r.left, r.width]; };
            const res = {frise: box('#frise'), publie: box('#frise .publie'),
                         hyp: box('#frise .hypothese'), pangee: box('#frise .pangee'),
                         texteHyp: (document.querySelector('#frise .hypothese') || {}).textContent || '',
                         hachure: (() => { const e = document.querySelector('#frise .hypothese');
                                    return e ? getComputedStyle(e).backgroundImage : ''; })(),
                         curseurs: [], bornes: terre.bornesPangee ? terre.bornesPangee() : null};
            for (const t of [0, 250, 540, 1000]) { await terre.regler({t});
              const c = document.querySelector('#frise .curseur'); const r = c ? c.getBoundingClientRect() : null;
              res.curseurs.push([t, r ? r.left + r.width / 2 : null]); }
            return res; }""")
        ok6, det = True, []
        if not fr["frise"] or not fr["publie"] or not fr["hyp"]:
            ok6 = False; det.append("frise incomplète")
        else:
            L0, LW = fr["frise"]
            rp = fr["publie"][1] / LW; ok = abs(rp - 1000 / 4540) <= 0.01 * (1000 / 4540)
            ok6 &= ok; det.append(f"1 Ga→0 = {rp*100:.2f} % (attendu {1000/4540*100:.2f} %)")
            rh = fr["hyp"][1] / LW; ok = abs(rh - 3540 / 4540) <= 0.01 * (3540 / 4540)
            ok6 &= ok and "hypoth" in fr["texteHyp"].lower() and "gradient" in fr["hachure"]
            det.append(f"hypothèse hachurée = {rh*100:.2f} %")
            if fr["pangee"] and fr["bornes"]:
                a_, b_ = fr["bornes"]; att = (a_ - b_) / 4540
                rg = fr["pangee"][1] / LW; ok = abs(rg - att) <= 0.01 * att
                ok6 &= ok; det.append(f"Pangée+hercynien = {rg*100:.2f} % (attendu {att*100:.2f} %)")
            else:
                ok6 = False; det.append("bande Pangée absente")
            for t, x in fr["curseurs"]:
                if x is None: ok6 = False; det.append("curseur absent"); break
                att = L0 + LW * (4540 - t) / 4540
                if abs(x - att) > 0.01 * LW: ok6 = False; det.append(f"curseur à {t} Ma décalé de {x-att:.1f} px")
        note("C6", ok6, " ; ".join(det))

        # ---- C7 Soleil de juin, fixe
        sols = []
        for t in (0, 250, 700):
            s = await pg.evaluate("async t => { await terre.regler({t}); return terre.soleil(); }", t)
            sols.append(s["lat"])
        ok_lat = all(abs(x - 23.44) < 0.05 for x in sols)
        s = await pg.evaluate("terre.soleil()")
        await pg.evaluate("o => terre.regler(o)", {"t": 0, "lat": 0, "lon": s["lon"] + 90})
        im = lum(await ecran(pg)); geo = await pg.evaluate("terre.disque()")
        cx, cy, R = geo["cx"], geo["cy"], geo["r"]
        def zone(dy):
            y0 = int(cy + dy * R); return im[max(y0 - 3, 0):y0 + 3, int(cx - 0.25 * R):int(cx + 0.25 * R)].mean()
        nord, sud = zone(-0.9), zone(0.9)
        note("C7", ok_lat and nord > 3 * sud + 0.02,
             f"lat. subsolaire {sols} ; calotte nord {nord:.3f}, sud {sud:.3f} au terminateur")

        # ---- C8 liseré d'atmosphère côté jour
        await pg.evaluate("o => terre.regler(o)", {"t": 0, "lat": s["lat"], "lon": s["lon"] + 40})
        rgb = await ecran(pg); geo = await pg.evaluate("terre.disque()")
        cx, cy, R = geo["cx"], geo["cy"], geo["r"]
        yy, xx = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]]
        rr = np.hypot(xx - cx, yy - cy)
        anneau = (rr > R * 1.003) & (rr < R * 1.02) & (xx < cx)        # côté jour (soleil à l'ouest de la vue)
        loin = (rr > R * 1.08) & (rr < R * 1.12)
        bleu = rgb[anneau].mean(0); fond = rgb[loin].mean(0)
        ok8 = bleu[2] > bleu[0] + 0.05 and bleu[2] > fond[2] + 0.08 and lum(rgb[loin]).mean() < 0.08
        note("C8", ok8, f"anneau RVB {np.round(bleu, 3).tolist()} ; au-delà {np.round(fond, 3).tolist()}")

        # ---- C9 interaction
        v0 = await pg.evaluate("terre.etat()")
        bb = await pg.locator("#globe").bounding_box()
        x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] * 0.35
        await pg.mouse.move(x, y); await pg.mouse.down()
        for k in range(1, 11): await pg.mouse.move(x + 8 * k, y)
        await pg.mouse.up()
        v1 = await pg.evaluate("terre.etat()")
        await pg.evaluate("terre.regler({t: 600})")
        await pg.click("#lecture"); await pg.wait_for_timeout(1500)
        v2 = await pg.evaluate("terre.etat()")
        await pg.click("#lecture")
        ok9 = abs(v1["lon"] - v0["lon"]) > 5 and v2["t"] < 600 - 1
        note("C9", ok9, f"glisser : lon {v0['lon']:.1f}→{v1['lon']:.1f} ; lecture : 600→{v2['t']:.1f} Ma")

        # ---- C10 signature Blue Marble de juin
        refbm = ICI / "controles" / "blue-marble-juin-2004.png"
        if not refbm.exists():
            note("C10", False, "référence Blue Marble absente (controles/blue-marble-juin-2004.png)")
        else:
            s0 = await pg.evaluate("terre.soleil()")
            await pg.evaluate("o => terre.regler(o)", {"t": 0, "lat": s0["lat"], "lon": s0["lon"]})
            rgb = await ecran(pg); geo = await pg.evaluate("terre.disque()")
            ok10, det10 = ciel_bm(rgb, geo, s0, np.asarray(Image.open(refbm).convert("RGB")) / 255,
                                  np.asarray(Image.open(ICI / "controles" / "terres-actuelles-ne50m.png")) > 127)
            note("C10", ok10, det10)

        # ---- C11 compteur de vitesse du temps
        det11, ok11 = [], True
        # page neuve : l'aiguille n'hérite pas des centaines de rendus des contrôles précédents
        p2 = await ctx.new_page()
        p2.on("pageerror", lambda e: erreurs.append(f"pageerror: {e}"))
        await p2.goto(base + URL_PAGE)
        await p2.wait_for_function("window.terre && window.terre.pret === true", timeout=120000)
        bc = await p2.evaluate("""() => { const e = document.querySelector('.compteur-temps');
            if (!e) return null; const r = e.getBoundingClientRect();
            return {x: r.left, y: r.top, w: r.width, h: r.height, txt: e.textContent}; }""")
        if not bc:
            note("C11", False, "compteur absent")
        else:
            gb = await p2.locator("#globe").bounding_box(); geo = await p2.evaluate("terre.disque()")
            cx, cy, R = gb["x"] + geo["cx"], gb["y"] + geo["cy"], geo["r"] * 1.03
            nx = min(max(cx, bc["x"]), bc["x"] + bc["w"]); ny = min(max(cy, bc["y"]), bc["y"] + bc["h"])
            hors = np.hypot(nx - cx, ny - cy) > R
            dedans = bc["x"] >= 0 and bc["y"] >= 0 and bc["x"] + bc["w"] <= 390 and bc["y"] + bc["h"] <= 844
            ok11 &= hors and dedans and bc["w"] >= 56
            det11.append(f"{bc['w']:.0f} px, hors du globe {hors}, dans l'écran {dedans}")
            await p2.evaluate("terre.regler({t: 1000})"); await p2.wait_for_timeout(1500)
            c = await p2.evaluate("terre.compteur()")
            ok11 &= abs(c["angle"] - c["butee"]) <= 1
            det11.append(f"arrêt : aiguille {c['angle']:.1f}° (butée {c['butee']}°)")
            await p2.click("#lecture"); await p2.wait_for_timeout(1000)
            # « après amortissement » : on attend que l'aiguille soit au repos (à faible cadence
            # d'images, le ressort du compteur commun avance d'au plus 50 ms par image)
            try:
                await p2.wait_for_function("(() => { const c = terre.compteur(); return c.v > 0 && Math.abs(c.angle - c.cible) < 0.5; })()", timeout=25000, polling=200)
            except Exception:
                pass
            m = await p2.evaluate("""async () => { const a = [performance.now(), terre.etat().t];
                await new Promise(r => setTimeout(r, 600)); const b = [performance.now(), terre.etat().t];
                const c = terre.compteur(); return {v: (a[1] - b[1]) * 1e6 / ((b[0] - a[0]) / 1000), ...c,
                attendu: terre.angleVitesse((a[1] - b[1]) * 1e6 / ((b[0] - a[0]) / 1000)),
                txt: document.querySelector('.compteur-temps').textContent}; }""")
            await p2.click("#lecture")
            ok11 &= abs(m["angle"] - m["attendu"]) <= 1 and "par seconde" in m["txt"]
            det11.append(f"lecture : {m['v']:.3g} ans/s -> attendu {m['attendu']:.1f}°, aiguille {m['angle']:.1f}° ; « {m['txt'].strip()[-45:]} »")
            note("C11", ok11, " ; ".join(det11))
        await p2.close()

        # ---- C1 (en dernier : couvre toute la session)
        gl2 = await pg.evaluate("!!document.createElement('canvas').getContext('webgl2')")
        note("C1", gl2 and not erreurs, f"WebGL2 {gl2} ; {len(erreurs)} erreur(s) " + " | ".join(erreurs[:3]))
        await b.close()
    srv.shutdown()
    n_ok = sum(ok for _, ok, _ in RES)
    print(f"\n{n_ok}/{len(RES)} contrôles passés")
    (ICI / "controles" / "dernier-resultat.json").write_text(
        json.dumps([{"code": c, "ok": o, "detail": d} for c, o, d in RES], ensure_ascii=False, indent=1))
    return 0 if n_ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
