"""Contrôles de la page labo « La Terre vue de l'espace : continents » (chantier S3).

Mesure la page SERVIE (app/public/labo/terre/index.html, données publiées comprises),
pas un aperçu. Chaque mesure passe par le même shader que le globe : l'état du relief
à l'instant t est lu dans la texture d'état que le globe échantillonne.

  C1  aucune erreur JavaScript ; WebGL2 disponible
  C2  aujourd'hui : terres et mers coïncident à 95 % (en aire) avec le relief actuel
      (référence indépendante : Natural Earth 1:50 m, controles/terres-actuelles-ne50m.png)
  C3  Pangée : entre 320 et 200 Ma, au moins 80 % du bloc continental (croûte au-dessus de
      -200 m) d'un seul tenant (D-46, 23/11) ; la part des terres émergées d'un seul tenant
      reste affichée, indicateur non bloquant
  Plage : les contrôles portent sur toute la plage que la page affiche (terre.plage(),
  [T_PUB, 0]) ; la page ne doit permettre d'atteindre aucun instant hors de cette plage
  (vérifié en C6). Décision du maître, 23/11 : on publie moins, on ne restreint aucun contrôle.
  C4  pas de fantôme : pendant une dérive, aucun pixel du globe plus sombre que ses deux
      états voisins (tolérance : 0,2 % des pixels du disque, écart de luminance > 0,05) ;
      rejoué 5 fois, aucun échec toléré (demande du maître, 23/11)
  C5  pas de saut : la surface émergée varie continûment (aucun saut > 1 % des terres
      entre deux instants distants de 0,5 Ma), raccord des deux modèles à 540 Ma compris
  C6  frise : la plage publiée T_PUB -> 0 occupe T_PUB/4540 de la frise (à 1 % près) ;
      avant, segment hachuré « à venir » ou « hypothèse » ; curseur et glissière bornés à
      T_PUB ; bande Pangée + chaîne hercynienne à sa proportion ;
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
  C12 caméra : la vue par défaut montre des continents éclairés à toutes les époques — au
      moins 60 % des terres visibles du côté jour (Soleil de juin), à 0, 66, 250, 540, 700
      et 1000 Ma (relecture du maître, 23/11)

  C13 réunions continentales (S3b, N36) : à chaque réunion du modèle, au moins 70 % du bloc
      continental (> -200 m) d'un seul tenant à un instant de sa fenêtre : Nuna 1650–1450 Ma,
      Rodinia 950–750 Ma, Gondwana 540–460 Ma, Pangée 320–200 Ma
  C14 montagnes (S3b, N35) : à chaque collision majeure, la croûte qui est aujourd'hui dans la
      chaîne porte un relief ≥ 2 000 m (point le plus haut à moins de 400 km, au plus haut des
      instants à ±40 Ma de l'âge nominal) ; 150 Ma après ce pic, ce relief s'est abaissé d'au
      moins 800 m (90e centile) : Nuna (1,6 Ga, n'importe où : chaînes de l'assemblage),
      Grenville (1,05 Ga), panafricain (600 Ma), calédonien (420 Ma), hercynien (300 Ma) ;
      aujourd'hui Himalaya, Andes, Alpes
  C15 couleur de la vie (S3b, N37) : terres éclairées vertes (a* < -4) ≤ 1 % jusqu'à 470 Ma ;
      verdissement net entre 420 et 300 Ma (+15 points au moins de la surface éclairée)
  C16 frise des réunions et ruban de la vie : Vaalbara, Ur, Kenorland (« hypothèse »), Nuna,
      Rodinia, Pannotia (« débattue »), Pangée, chacune à son âge (à 1 % de la frise) ; sous la
      frise, le ruban de la vie (genres d'animaux marins, Paleobiology Database), à la même
      échelle de temps, explosion cambrienne visible (≥ 5 fois plus de genres à 520 qu'à 545 Ma)
  C17 Archéen (Zhou et al. 2026) : terres émergées < 15 % de la surface du globe à 3,5, 3,0
      et 2,7 Ga

  Option --visee <Ma> : mesure la page comme si elle devait couvrir <Ma> -> aujourd'hui
  (pour montrer en échec les contrôles d'une plage pas encore publiée).

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


async def actuel(pg):
    """Position actuelle (lat, lon en degrés) du morceau de croûte de chaque pixel de l'état."""
    r = await pg.evaluate("terre.actuelEquirect()")
    brut = np.frombuffer(base64.b64decode(r["rgba"]), np.uint8).reshape(r["h"], r["w"], 4).astype(np.float64)
    lon = (brut[..., 0] * 256 + brut[..., 1]) / 65535 * 360 - 180
    lat = (brut[..., 2] * 256 + brut[..., 3]) / 65535 * 180 - 90
    a = np.stack([lat, lon], -1)
    return a[::-1] if r.get("basEnHaut") else a


def dist_km(act, lat, lon):
    la1, lo1 = np.radians(act[..., 0]), np.radians(act[..., 1]); la2, lo2 = np.radians(lat), np.radians(lon)
    c = np.sin(la1) * np.sin(la2) + np.cos(la1) * np.cos(la2) * np.cos(lo1 - lo2)
    return 6371 * np.arccos(np.clip(c, -1, 1))


async def part_verte(pg):
    """Part des terres éclairées (μ > 0,3) du globe rendu dont la couleur est verte (a* < -4)."""
    rgb = await ecran(pg); geo = await pg.evaluate("terre.disque()"); v = await pg.evaluate("terre.etat()")
    s0 = await pg.evaluate("terre.soleil()"); e = await etat(pg, v["t"])
    H, W = rgb.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
    x = (xx + .5 - geo["cx"]) / geo["r"]; y = -(yy + .5 - geo["cy"]) / geo["r"]; r2 = x * x + y * y
    z = np.sqrt(np.clip(1 - r2, 0, 1)); la, lo = np.radians(v["lat"]), np.radians(v["lon"])
    ee = np.array([-np.sin(lo), np.cos(lo), 0]); nn = np.array([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)])
    cc = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    P = x[..., None] * ee + y[..., None] * nn + z[..., None] * cc
    sl, so = np.radians(s0["lat"]), np.radians(s0["lon"])
    S = np.array([np.cos(sl) * np.cos(so), np.cos(sl) * np.sin(so), np.sin(sl)])
    lat = np.degrees(np.arcsin(np.clip(P[..., 2], -1, 1))); lon = np.degrees(np.arctan2(P[..., 1], P[..., 0]))
    he, we = e.shape
    terre_ = e[np.clip(((90 - lat) / 180 * he).astype(int), 0, he - 1), np.clip(((lon + 180) / 360 * we).astype(int), 0, we - 1)] > 50
    sel = (r2 < 0.9) & terre_ & (P @ S > 0.3)
    if sel.sum() < 200: return float("nan")
    L = lab(rgb[sel])
    return float((L[:, 1] < -4).mean())


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
            for c in ("C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17"):
                note(c, False, "page non chargée")
            await b.close(); srv.shutdown(); return 1

        SEUL = sys.argv[sys.argv.index("--seulement") + 1].split(",") if "--seulement" in sys.argv else None
        veut = lambda c: SEUL is None or c in SEUL
        TPUB = float((await pg.evaluate("terre.plage ? terre.plage() : [1000, 0]"))[0])
        if "--visee" in sys.argv: TPUB = float(sys.argv[sys.argv.index("--visee") + 1])
        print(f"plage publiée : {TPUB:g} Ma -> aujourd'hui", flush=True)
        dans = lambda t: t <= TPUB + 1e-9

        # ---- C2 aujourd'hui
        if veut("C2"):
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
        if veut("C3"):
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
            mini = min(q for _, _, q in pires)
            note("C3", mini >= 0.80, "bloc continental (> -200 m) d'un seul tenant : " +
                 ", ".join(f"{t} Ma {q*100:.0f} %" for t, _, q in pires) + " (seuil 80 %) ; indicateur, "
                 "terres émergées : " + ", ".join(f"{t} Ma {p*100:.0f} %" for t, p, _ in pires))

        # ---- C4 pas de fantôme (sur l'écran, globe tel que vu), rejoué 5 fois
        if veut("C4"):
            await pg.evaluate("terre.regler({lon: 10, lat: 15})")
            pires4 = []
            for passe in range(5):
                pire = (0, None)
                for t in [x for x in (2.5, 52.5, 252.5, 302.5, 537.5, 541.0, 545.0, 552.0, 575.0, 755.0, 995.0, TPUB - 0.5) if dans(x + 0.5)]:
                    ims = []
                    for tt in (t - 0.5, t, t + 0.5):
                        await pg.evaluate("t => terre.regler({t})", tt)
                        ims.append(lum(await ecran(pg)))
                    a_, m_, c_ = ims
                    disque = (a_ > 0.02) | (c_ > 0.02)
                    sombre = (m_ < np.minimum(a_, c_) - 0.05) & disque
                    frac = sombre.sum() / max(disque.sum(), 1)
                    if frac >= pire[0]: pire = (frac, t)
                pires4.append(pire)
            pp4 = max(pires4, key=lambda x: x[0])
            note("C4", all(p[0] < 0.002 for p in pires4), "pixels plus sombres que leurs deux voisins, 5 passes : " +
                 ", ".join(f"{p[0]*100:.3f} %" for p in pires4) + f" (pire à {pp4[1]} Ma ; seuil 0,2 %)")

        # ---- C5 pas de saut
        if veut("C5"):
            r = await pg.evaluate("""async T => {
                const out = [];
                for (let [a, b] of [[0, 12], [245, 257], [528, 562], [985, 1000], [T - 12, T]]) {
                  b = Math.min(b, T); if (a >= b) continue;
                  const s = [];
                  for (let t = a; t <= b + 1e-9; t += 0.5) { await terre.regler({t}); s.push([t, terre.aireTerres()]); }
                  out.push(s); }
                return out; }""", TPUB)
            sauts = [(s[i][0], abs(s[i][1] - s[i-1][1]) / max(s[i][1], s[i-1][1], 1e-9))
                     for s in r for i in range(1, len(s))]
            smax = max(sauts, key=lambda x: x[1])
            note("C5", smax[1] < 0.01, f"plus grand saut de surface émergée : {smax[1]*100:.2f} % "
                 f"(vers {smax[0]} Ma ; seuil 1 %)")

        # ---- C6 frise
        if veut("C6"):
            fr = await pg.evaluate("""async T => {
                const box = s => { const e = document.querySelector(s); if (!e) return null;
                                   const r = e.getBoundingClientRect(); return [r.left, r.width]; };
                const res = {frise: box('#frise'), publie: box('#frise .publie'),
                             avant: [...document.querySelectorAll('#frise .hypothese, #frise .avenir')].map(e => {
                                const r = e.getBoundingClientRect();
                                return [r.left, r.width, e.textContent, getComputedStyle(e).backgroundImage]; }),
                             pangee: box('#frise .pangee'),
                             glissiere: (() => { const e = document.querySelector('#temps');
                                         return e ? [Number(e.min), Number(e.max)] : null; })(),
                             curseurs: [], bornes: terre.bornesPangee ? terre.bornesPangee() : null};
                await terre.regler({t: 4540}); res.auDela = terre.etat().t;
                for (const t of [0, 250, 540, 1000].filter(t => t <= T)) { await terre.regler({t});
                  const c = document.querySelector('#frise .curseur'); const r = c ? c.getBoundingClientRect() : null;
                  res.curseurs.push([t, r ? r.left + r.width / 2 : null]); }
                return res; }""", TPUB)
            ok6, det = True, []
            if not fr["frise"] or not fr["publie"] or not fr["avant"]:
                ok6 = False; det.append("frise incomplète")
            else:
                L0, LW = fr["frise"]
                rp = fr["publie"][1] / LW; ok = abs(rp - TPUB / 4540) <= 0.01 * (TPUB / 4540)
                ok6 &= ok; det.append(f"{TPUB:g} Ma→0 = {rp*100:.2f} % (attendu {TPUB/4540*100:.2f} %)")
                rh = sum(a[1] for a in fr["avant"]) / LW; att = (4540 - TPUB) / 4540
                ok = abs(rh - att) <= 0.01 * att and all(
                    ("hypoth" in a[2].lower() or "à venir" in a[2].lower()) and "gradient" in a[3] for a in fr["avant"])
                ok6 &= ok; det.append(f"avant {TPUB:g} Ma hachuré = {rh*100:.2f} % (attendu {att*100:.2f} %), "
                                      "« " + " / ".join(a[2].strip() for a in fr["avant"]) + " »")
                ok = abs(fr["auDela"] - TPUB) < 1e-6 and fr["glissiere"] is not None and fr["glissiere"][1] - fr["glissiere"][0] == TPUB
                ok6 &= ok; det.append(f"borne : t demandé 4540 -> {fr['auDela']:g} Ma, glissière {fr['glissiere']}")
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
        if veut("C7"):
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
        if veut("C8"):
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
        if veut("C9"):
            v0 = await pg.evaluate("terre.etat()")
            bb = await pg.locator("#globe").bounding_box()
            x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] * 0.35
            await pg.mouse.move(x, y); await pg.mouse.down()
            for k in range(1, 11): await pg.mouse.move(x + 8 * k, y)
            await pg.mouse.up()
            v1 = await pg.evaluate("terre.etat()")
            t9 = min(600.0, TPUB)
            await pg.evaluate("t => terre.regler({t})", t9)
            await pg.click("#lecture"); await pg.wait_for_timeout(1500)
            v2 = await pg.evaluate("terre.etat()")
            await pg.click("#lecture")
            ok9 = abs(v1["lon"] - v0["lon"]) > 5 and v2["t"] < t9 - 1
            note("C9", ok9, f"glisser : lon {v0['lon']:.1f}→{v1['lon']:.1f} ; lecture : {t9:g}→{v2['t']:.1f} Ma")

        # ---- C10 signature Blue Marble de juin
        if veut("C10"):
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
        if veut("C11"):
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

        # ---- C12 caméra automatique : terres visibles éclairées
        if veut("C12"):
            res12, ok12 = [], True
            for t in [x for x in (0, 66, 250, 540, 700, 1000, 1600, 2700) if dans(x)]:
                await pg.evaluate("t => terre.regler({t, auto: true})", float(t))
                e = await etat(pg, float(t)); v = await pg.evaluate("terre.etat()"); s0 = await pg.evaluate("terre.soleil()")
                geo = await pg.evaluate("terre.disque()")
                n = 160; yy, xx = np.mgrid[0:n, 0:n]
                x = (xx + .5) / n * 2 - 1; y = 1 - (yy + .5) / n * 2; r2 = x * x + y * y; d = r2 < 1
                z = np.sqrt(np.clip(1 - r2, 0, 1))
                la, lo = np.radians(v["lat"]), np.radians(v["lon"])
                ee = np.array([-np.sin(lo), np.cos(lo), 0]); nn = np.array([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)])
                cc = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
                P = x[..., None] * ee + y[..., None] * nn + z[..., None] * cc
                lat = np.degrees(np.arcsin(np.clip(P[..., 2], -1, 1))); lon = np.degrees(np.arctan2(P[..., 1], P[..., 0]))
                H, W = e.shape
                terre_ = e[np.clip(((90 - lat) / 180 * H).astype(int), 0, H - 1), np.clip(((lon + 180) / 360 * W).astype(int), 0, W - 1)] > 0
                sl, so = np.radians(s0["lat"]), np.radians(s0["lon"])
                S = np.array([np.cos(sl) * np.cos(so), np.cos(sl) * np.sin(so), np.sin(sl)])
                w = z                                                    # poids : aire apparente
                vis = d & terre_
                frac = (w * (vis & (P @ S > 0.05))).sum() / max((w * vis).sum(), 1e-9)
                ok12 &= frac >= 0.60; res12.append(f"{t} Ma {frac*100:.0f} %")
            note("C12", ok12, "terres visibles éclairées : " + ", ".join(res12) + " (seuil 60 %)")

        # ---- C13 réunions continentales
        if veut("C13"):
            det13, ok13 = [], True
            for nom, a_, b_ in (("Nuna", 1650, 1450), ("Rodinia", 950, 750), ("Gondwana", 540, 460), ("Pangée", 320, 200)):
                ts = [t for t in np.arange(a_, b_ - 1, -20.0) if dans(t)]
                if not ts: continue
                best = (0, None)
                for t in ts:
                    e = await etat(pg, float(t)); m = e > -200
                    labc, _ = composantes(m); ww = poids_aire(*m.shape)
                    ac = np.bincount(labc[m].ravel(), weights=ww[m].ravel())
                    q = ac.max() / ac.sum() if ac.sum() > 0 else 0
                    if q > best[0]: best = (q, t)
                ok13 &= best[0] >= 0.70; det13.append(f"{nom} {best[0]*100:.0f} % (à {best[1]:g} Ma)")
            note("C13", ok13, "plus grand bloc continental : " + ", ".join(det13) + " (seuil 70 %)")

        # ---- C14 montagnes aux collisions
        if veut("C14"):
            det14, ok14 = [], True
            for nom, lat_, lon_, tp in (("Nuna", None, None, 1600), ("Grenville", 46, -76, 1050),
                                        ("panafricain", -5, 37, 600), ("calédonien", 62, 8, 420),
                                        ("hercynien", 37, -81, 300), ("Himalaya", 30, 85, 0),
                                        ("Andes", -20, -68, 0), ("Alpes", 46.5, 10, 0)):
                if not dans(tp): continue
                if not await pg.evaluate("!!terre.actuelEquirect"):
                    ok14 = False; det14.append("la page ne donne pas la position actuelle de la croûte (terre.actuelEquirect)"); break
                res = []
                # pic : le plus haut des instants à ±40 Ma de l'âge nominal (une collision dure des
                # dizaines de Ma, et son âge varie d'un modèle à l'autre) ; puis 150 Ma après le pic
                pics = [x for x in ((tp - 40, tp - 20, tp, tp + 20, tp + 40) if tp >= 40 else (tp,)) if dans(x)]
                for t in pics:
                    e = await etat(pg, float(t))
                    if lat_ is None: zone = e.ravel()               # Nuna : n'importe où sur le globe
                    else: zone = e[dist_km(await actuel(pg), lat_, lon_) < 400]
                    r_ = (t, float(zone.max()) if zone.size else -1e4, float(np.percentile(zone, 90)) if zone.size else -1e4)
                    if not res or r_[1] > res[0][1]: res = [r_]
                if res[0][0] >= 150 and lat_ is not None:
                    t = res[0][0] - 150; e = await etat(pg, float(t))
                    zone = e[dist_km(await actuel(pg), lat_, lon_) < 400]
                    res.append((t, float(zone.max()) if zone.size else -1e4, float(np.percentile(zone, 90)) if zone.size else -1e4))
                ok = res[0][1] >= 2000 and (len(res) == 1 or res[0][2] - res[1][2] >= 800)
                ok14 &= ok
                det14.append(f"{nom} {res[0][0]:g} Ma max {res[0][1]:.0f} m" +
                             (f", 90e c. {res[0][2]:.0f} -> {res[1][2]:.0f} m à {res[1][0]:g} Ma" if len(res) > 1 else "") +
                             ("" if ok else " ✗"))
            note("C14", ok14, " ; ".join(det14))

        # ---- C15 couleur de la vie
        if veut("C15"):
            verts = {}
            for t in [x for x in (540, 500, 470, 420, 380, 340, 300) if dans(x)]:
                await pg.evaluate("t => terre.regler({t, auto: true})", float(t))
                verts[t] = await part_verte(pg)
            nus = [t for t in verts if t >= 470]
            ok15 = all(verts[t] <= 0.01 for t in nus)
            if 420 in verts and 300 in verts: ok15 &= verts[300] - verts[420] >= 0.15
            note("C15", ok15, "terres éclairées vertes : " + ", ".join(f"{t} Ma {v*100:.1f} %" for t, v in verts.items()) +
                 " (≤ 1 % jusqu'à 470 Ma ; +15 points de 420 à 300 Ma)")

        # ---- C16 frise des réunions et ruban de la vie
        if veut("C16"):
            fr16 = await pg.evaluate("""() => {
                const f = document.querySelector('#frise'); if (!f) return null; const R = f.getBoundingClientRect();
                const reu = [...document.querySelectorAll('[data-reunion]')].map(e => { const r = e.getBoundingClientRect();
                  return [e.dataset.reunion, Number(e.dataset.t), r.left + r.width / 2, e.dataset.statut || '', e.textContent]; });
                const rb = document.querySelector('#ruban-vie'); const rr = rb ? rb.getBoundingClientRect() : null;
                const vie = window.terre.rubanVie ? window.terre.rubanVie() : null;
                return {L: R.left, W: R.width, bas: R.bottom, reu, ruban: rr ? [rr.left, rr.width, rr.top] : null, vie,
                        source: rb ? (rb.getAttribute('title') || '') + ' ' + rb.textContent : ''}; }""")
            ok16, det16 = True, []
            attendu = {"Vaalbara": (3300, "hypoth"), "Ur": (3000, "hypoth"), "Kenorland": (2500, "hypoth"),
                       "Nuna": (1600, ""), "Rodinia": (900, ""), "Pannotia": (600, "débattu"), "Pangée": (300, "")}
            if not fr16:
                ok16 = False; det16.append("frise absente")
            else:
                vus = {r[0]: r for r in fr16["reu"]}
                for n_, (age, statut) in attendu.items():
                    r = vus.get(n_)
                    if not r: ok16 = False; det16.append(f"{n_} absente"); continue
                    x_att = fr16["L"] + fr16["W"] * (4540 - r[1]) / 4540
                    ok = abs(r[2] - x_att) <= 0.01 * fr16["W"] and abs(r[1] - age) <= 0.25 * age and statut in r[3].lower()
                    ok16 &= ok
                    if not ok: det16.append(f"{n_} mal placée ou mal signalée ({r[1]} Ma, « {r[3]} »)")
                if not fr16["ruban"] or not fr16["vie"]:
                    ok16 = False; det16.append("ruban de la vie absent")
                else:
                    L_, W_, top = fr16["ruban"]
                    ok = abs(L_ - fr16["L"]) < 2 and abs(W_ - fr16["W"]) < 2 and top >= fr16["bas"] - 1
                    vie = np.array(fr16["vie"], float)
                    g = lambda t: float(np.interp(t, vie[::-1, 0], vie[::-1, 1]))
                    ok &= g(520) >= 5 * max(g(545), 1) and "paleobiology" in fr16["source"].lower()
                    ok16 &= ok
                    det16.append(f"ruban : {len(vie)} étages, genres à 545 Ma {g(545):.0f}, à 520 Ma {g(520):.0f}" + ("" if ok else " ✗"))
                if ok16: det16.insert(0, "7 réunions à leur âge, statuts signalés")
            note("C16", ok16, " ; ".join(det16))

        # ---- C17 Archéen : continents surtout immergés
        if veut("C17"):
            det17, ok17 = [], True
            for t in [x for x in (3500, 3000, 2700) if dans(x)]:
                e = await etat(pg, float(t)); ww = poids_aire(*e.shape)
                f_ = (ww * (e > 0)).sum() / ww.sum(); ok17 &= f_ < 0.15; det17.append(f"{t} Ma {f_*100:.1f} %")
            note("C17", ok17, ("terres émergées : " + ", ".join(det17) + " (seuil 15 %)") if det17 else "hors de la plage affichée")

        # ---- C1 (en dernier : couvre toute la session)
        gl2 = await pg.evaluate("!!document.createElement('canvas').getContext('webgl2')")
        note("C1", gl2 and not erreurs, f"WebGL2 {gl2} ; {len(erreurs)} erreur(s) " + " | ".join(erreurs[:3]))
        await b.close()
    srv.shutdown()
    n_ok = sum(ok for _, ok, _ in RES)
    print(f"\n{n_ok}/{len(RES)} contrôles passés")
    if "--seulement" not in sys.argv and "--visee" not in sys.argv: (ICI / "controles" / "dernier-resultat.json").write_text(
        json.dumps([{"code": c, "ok": o, "detail": d} for c, o, d in RES], ensure_ascii=False, indent=1))
    return 0 if n_ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
