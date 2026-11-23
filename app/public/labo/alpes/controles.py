"""Contrôles de la page labo S7 — L'orogenèse alpine, vue d'avion.

Usage : python3 app/public/labo/alpes/controles.py
Sert app/public sur un port libre (8820–8829), mesure le paquet PUBLIÉ (donnees/)
tel que la page le lit, puis la page elle-même dans Chrome (Playwright, 390 × 844).

Exigences servies : N16 (compression et érosion simultanées), N17 (relief réaliste),
N20 (fluide sur téléphone), N23 / D-41 (fin sur le relief réel, barre qui ralentit).
"""
import gzip, http.server, json, os, socket, sys, threading, time, urllib.request
from functools import partial
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", "..", ".."))   # app/public
CHEMIN = "/labo/alpes/"
resultats = []


def ok(nom, cond, detail=""):
    resultats.append((nom, bool(cond), detail))
    print(("  OK   " if cond else "  ÉCHEC ") + nom + (f" — {detail}" if detail else ""), flush=True)


def port_libre():
    for p in range(8820, 8830):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                pass
    raise SystemExit("aucun port libre entre 8820 et 8829")


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def servir():
    port = port_libre()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Silencieux, directory=RACINE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}{CHEMIN}"


def lire(url):
    return urllib.request.urlopen(url, timeout=30).read()


# ---------------------------------------------------------------- paquet publié
def decoder_paquet(base, meta):
    """Décode les états exactement comme la page (voir alpes.js, charger)."""
    nn, nx, nu = meta["n"] ** 2, meta["n_x"] ** 2, meta["n_ue"] ** 2
    H, U, E, X = [], [], [], []
    for p in meta["paquets"]:
        brut = gzip.decompress(lire(base + "donnees/" + p["fichier"]))
        k = p["nombre"]
        b = np.frombuffer(brut[: 2 * nn * k], np.uint8).reshape(2, k, nn)   # plans bas / haut
        d = (b[0].astype(np.uint16) | (b[1].astype(np.uint16) << 8)).view(np.int16).astype(np.int32)
        q = np.cumsum(d, axis=0)                       # différences sans perte dans le paquet
        o = 2 * nn * k
        x = np.cumsum(np.frombuffer(brut[o:o + nx * k], np.uint8).reshape(k, nx).astype(np.int32), axis=0) % 256
        o += nx * k
        u = np.frombuffer(brut[o:o + nu * k], np.uint8).reshape(k, nu); o += nu * k
        e = np.frombuffer(brut[o:o + nu * k], np.uint8).reshape(k, nu)
        for i in range(k):
            H.append(q[i] * meta["h_pas_m"] + meta["h_zero_m"])
            U.append(u[i]); E.append(e[i]); X.append(x[i].astype(np.uint8))
    return np.array(H, np.float32), np.array(U), np.array(E), np.array(X)


def lab(rgb):
    """sRGB 0–255 -> CIE L*a*b* (D65)."""
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def delta_e(a, b):
    return np.linalg.norm(lab(a) - lab(b), axis=-1)


def ombre_python(h, n, pas_m, az, el, nb, exa):
    """Même marche vers le Soleil que le nuanceur de sommets (alpes.js, VS)."""
    h = np.maximum(h.reshape(n, n), 0) * exa
    d = np.array([np.sin(np.radians(az)), np.cos(np.radians(az))]); d /= np.linalg.norm(d)
    tg = np.tan(np.radians(el))
    jj, ii = np.meshgrid(np.arange(n), np.arange(n))
    marge = np.full((n, n), 1e9)
    for s_ in range(1, nb + 1):
        pj = np.clip(np.floor(jj + d[0] * s_ + 0.5).astype(int), 0, n - 1)
        pi = np.clip(np.floor(ii - d[1] * s_ + 0.5).astype(int), 0, n - 1)
        marge = np.minimum(marge, (h + s_ * pas_m * tg - h[pi, pj]) / (s_ * pas_m))
    return marge > 0


def taux(v, meta):
    """octet -> mm/an (codage racine carrée)."""
    return (v.astype(np.float32) / 255.0) ** 2 * meta["taux_max_mm_an"]


def controles_donnees(base):
    print("Paquet publié", flush=True)
    try:
        meta = json.loads(lire(base + "donnees/meta.json"))
    except Exception as e:
        ok("D1 paquet présent (donnees/meta.json)", False, str(e))
        return None
    t = np.array(meta["temps_Ma"], float)
    ok("D1 paquet présent (donnees/meta.json)", True, f"{len(t)} états")
    pas = np.diff(t)
    ok("D2 états de −45 Ma à aujourd'hui, ordonnés",
       abs(t[0] + 45) < 1e-6 and abs(t[-1]) < 1e-9 and (pas > 0).all(),
       f"{t[0]} → {t[-1]} Ma")
    avant = pas[t[1:] <= -2 + 1e-9]
    apres = pas[t[1:] > -2 + 1e-9]
    ok("D3 pas réguliers ≤ 250 ka, plus serrés sur les 2 derniers Ma",
       len(avant) and avant.max() <= 0.25 + 1e-9 and len(apres) and apres.max() < avant.min(),
       f"avant {avant.max() if len(avant) else '–'} Ma, après {apres.max() if len(apres) else '–'} Ma")
    taille = sum(int(urllib.request.urlopen(base + "donnees/" + p["fichier"]).headers["Content-Length"])
                 for p in meta["paquets"])
    ok("D4 paquet léger (< 40 Mo)", taille < 40e6, f"{taille/1e6:.1f} Mo")
    premiere = sum(len(lire(base + "donnees/" + f)) for f in
                   ("meta.json", meta["paquets"][0]["fichier"], "reel_1024.bin.gz", "regles.png", "mosaique_2048.jpg"))
    ok("N27 poids avant la première image ≤ 10 Mo", premiere <= 10e6, f"{premiere/1e6:.1f} Mo")

    H, U8, E8, X8 = decoder_paquet(base, meta)
    n = meta["n"]
    reel = np.frombuffer(gzip.decompress(lire(base + "donnees/reel_256.bin.gz")), "<u2").astype(np.float32)
    reel = reel * meta["h_pas_m"] + meta["h_zero_m"]

    # N16 : soulèvement et érosion ensemble, aux mêmes endroits
    bons, details = 0, []
    for k in range(1, len(t)):
        u, e = taux(U8[k], meta), taux(E8[k], meta)
        zone = u > 0.1
        if zone.mean() < 0.01:
            details.append((t[k], "pas de soulèvement")); continue
        frac = (e[zone] > 0.05).mean()
        r = np.corrcoef(u, e)[0, 1]
        if frac >= 0.6 and r >= 0.5:
            bons += 1
        else:
            details.append((round(t[k], 3), round(float(frac), 2), round(float(r), 2)))
    part = bons / (len(t) - 1)
    ok("N16 soulèvement et érosion simultanés aux mêmes endroits sur ≥ 80 % des états",
       part >= 0.8, f"{100*part:.0f} % ; premiers écarts : {details[:3]}")

    # N16 : bilan de masse publié cohérent (états sans raccourcissement)
    adv = np.array(meta["raccourcissement_mm_an"], float)
    ecarts = []
    for k in range(1, len(t)):
        if adv[k] > 0:
            continue
        dt = (t[k] - t[k - 1]) * 1e6
        f = n // meta["n_ue"]
        dh = (H[k] - H[k - 1]).reshape(meta["n_ue"], f, meta["n_ue"], f).mean(axis=(1, 3)).ravel()
        dhdt = dh / dt * 1e3                                     # mm/an
        bilan = taux(U8[k], meta) - taux(E8[k], meta)
        ecarts.append(np.abs(dhdt - bilan).mean() / max(np.abs(bilan).mean(), 1e-3))
    ok("N16 relief publié = soulèvement − érosion publiés (écart relatif moyen < 25 %)",
       len(ecarts) > 0 and np.median(ecarts) < 0.25,
       f"médiane {np.median(ecarts):.2f} sur {len(ecarts)} états" if ecarts else "aucun état")

    # N23 : la fin est le relief réel
    ecart = np.abs(H[-1] - reel).mean()
    ok("N23 dernier état à moins de 50 m (moyenne) du relief réel",
       ecart < 50, f"{ecart:.1f} m (écart-type {np.std(H[-1]-reel):.0f} m)")

    # N23 : on reconnaît les massifs (lieux en km depuis Grenoble, est/nord)
    g = H[-1].reshape(n, n)
    def zone(x0, x1, y0, y1):
        c = (np.arange(n) + 0.5) * meta["pas_m"] / 1e3 - meta["taille_km"] / 2
        ix = (c >= x0) & (c <= x1); iy = (-c >= y0) & (-c <= y1)
        return g[np.ix_(iy, ix)]
    bel = zone(15, 30, -5, 15).max()          # Grand Pic de Belledonne ~ (21, 0)
    gres = np.percentile(zone(3, 25, 5, 30), 5)  # fond du Grésivaudan
    cha = zone(-5, 10, 10, 30).max()          # Chamechaude, Dent de Crolles
    ver = zone(-25, -5, -40, -5).max()        # Grand Veymont, Moucherotte
    ok("N23 Belledonne > 2 600 m, Chartreuse et Vercors > 1 700 m, Grésivaudan < 400 m",
       bel > 2600 and cha > 1700 and ver > 1700 and gres < 400,
       f"Belledonne {bel:.0f}, Chartreuse {cha:.0f}, Vercors {ver:.0f}, Grésivaudan {gres:.0f} m")

    # N17 : machine à laver — roches profondes au jour là où l'érosion a travaillé
    xf = X8[-1].astype(float)
    ok("N17 roches profondes affleurant dans les massifs cristallins (Belledonne)",
       np.median(zone_x(xf, meta, 15, 30, -5, 15)) > np.median(zone_x(xf, meta, -60, -40, -20, 20)) + 40,
       f"indice Belledonne {np.median(zone_x(xf, meta, 15, 30, -5, 15)):.0f}, avant-pays {np.median(zone_x(xf, meta, -60, -40, -20, 20)):.0f}")
    return meta


def zone_x(xf, meta, x0, x1, y0, y1):
    n = meta["n_x"]
    g = xf.reshape(n, n)
    c = (np.arange(n) + 0.5) * meta["taille_km"] / n - meta["taille_km"] / 2
    ix = (c >= x0) & (c <= x1); iy = (-c >= y0) & (-c <= y1)
    return g[np.ix_(iy, ix)]


# ---------------------------------------------------------------- page
def controles_page(base):
    print("Page", flush=True)
    from playwright.sync_api import sync_playwright
    erreurs = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                 args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                       "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        page = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        page.goto(base, wait_until="load")
        try:
            page.wait_for_function("window.ALPES && window.ALPES.pret", timeout=120000)
            pret = True
        except Exception:
            pret = False
        ok("P1 page prête (paquet chargé, WebGL2)", pret)
        if pret:
            controles_couleurs(page, base)
            # Vitesse réelle de la barre : temps géologique écoulé par seconde de lecture
            mesures, angles = {}, {}
            for t0 in (-20, -1.9, -1.2, -0.6, -0.2):
                v = page.evaluate("""async (t0) => {
                    const A = window.ALPES; A.vitesse(1); A.aller(t0); A.lire();
                    await new Promise(r => setTimeout(r, 200));
                    const a = A.temps(), ta = performance.now();
                    await new Promise(r => setTimeout(r, 1500));
                    const b = A.temps(), tb = performance.now();
                    const v = (b - a) / ((tb - ta) / 1000);
                    const ang = A.compteur.angle(); A.pause();
                    return [v, ang];
                }""", t0)
                mesures[t0], angles[t0] = v
            r = [mesures[k] for k in (-1.9, -1.2, -0.6, -0.2)]
            ok("N23 la barre ralentit : vitesse décroissante sur les 2 derniers Ma",
               all(r[i] > r[i + 1] > 0 for i in range(3)) and mesures[-20] > 3 * r[0],
               " ; ".join(f"{k} Ma : {v*1000:.0f} ka/s" for k, v in mesures.items()))

            from math import log10
            attendu = {k: -125 + 250 * min(max(log10(v * 1e6), 0), 10) / 10 for k, v in mesures.items()}
            ecart_ang = max(abs(angles[k] - attendu[k]) for k in mesures)
            ra = [angles[k] for k in (-1.9, -1.2, -0.6, -0.2)]
            ok("N28 compteur : l'aiguille vaut la vitesse réelle (log, à 1° près) et redescend sur les 2 derniers Ma",
               ecart_ang <= 1.0 and all(ra[i] > ra[i + 1] for i in range(3)),
               f"écart max {ecart_ang:.2f}° ; aiguille " + ", ".join(f"{a:.1f}°" for a in ra))
            page.evaluate("window.ALPES.pause(); window.ALPES.aller(-0.5)")
            page.wait_for_timeout(1500)
            butee = page.evaluate("window.ALPES.compteur.angle()")
            ok("N28 compteur : temps à l'arrêt, aiguille sur la butée", butee < -135, f"{butee:.1f}°")

            page.evaluate("window.ALPES.aller(0)")
            page.wait_for_timeout(600)
            geo = page.evaluate("""() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
                return { c: r(document.querySelector('.compteur')), bas: r(document.getElementById('bas')), date: r(document.getElementById('haut')),
                  lieux: [...document.querySelectorAll('.lieu')].filter(e => getComputedStyle(e).opacity > 0.05).map(r) }; }""")
            inter = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
            c = geo["c"]
            libre = not any(inter(c, l) for l in geo["lieux"]) and not inter(c, geo["bas"])
            ok("N28 compteur lisible sur 390 px (≥ 100 px) et ne masque ni lieu ni commande",
               (c[2] - c[0]) >= 100 and c[2] <= 390 and libre, f"{c[2]-c[0]:.0f} px, {len(geo['lieux'])} lieux visibles")
            vis = page.evaluate("""() => ['Belledonne','Chartreuse','Vercors','Grésivaudan'].map(n =>
                [...document.querySelectorAll('.lieu')].some(e => e.textContent.includes(n)
                 && getComputedStyle(e).opacity > 0.5 && e.getBoundingClientRect().width > 0))""")
            page.evaluate("window.ALPES.aller(-30)")
            page.wait_for_timeout(600)
            cache = page.evaluate("""() => [...document.querySelectorAll('.lieu')].every(e =>
                getComputedStyle(e).opacity < 0.2)""")
            ok("N23 noms des massifs visibles à la fin, absents à −30 Ma", all(vis) and cache,
               f"fin {vis}, −30 Ma masqués {cache}")

            page.evaluate("window.ALPES.aller(0)")
            page.wait_for_timeout(500)
            stats = page.evaluate("""() => {
                const c = document.querySelector('canvas'); const g = c.getContext('webgl2');
                const w = g.drawingBufferWidth, h = g.drawingBufferHeight;
                window.ALPES.dessiner(); const px = new Uint8Array(w*h*4);
                g.readPixels(0,0,w,h,g.RGBA,g.UNSIGNED_BYTE,px);
                let s=0,s2=0,n=0; for(let i=0;i<px.length;i+=16){const v=px[i]+px[i+1]+px[i+2]; s+=v; s2+=v*v; n++;}
                const m=s/n; return [m, Math.sqrt(s2/n-m*m)];
            }""")
            ok("P2 relief rendu (image non vide, contrastée)", stats[1] > 25, f"moyenne {stats[0]:.0f}, écart-type {stats[1]:.0f}")

            # glisser au doigt : la vue tourne
            avant = page.evaluate("window.ALPES.camera().azimut")
            page.mouse.move(200, 420); page.mouse.down(); page.mouse.move(300, 430, steps=8); page.mouse.up()
            apres = page.evaluate("window.ALPES.camera().azimut")
            ok("P3 glisser fait tourner la vue", abs(apres - avant) > 0.05, f"{avant:.2f} → {apres:.2f} rad")

            ims = page.evaluate("""async () => { const A = window.ALPES; A.aller(-44); A.vitesse(4); A.lire();
                const t0 = performance.now(); let n = 0;
                await new Promise(r => { const f = () => { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
                A.pause(); return n / 3; }""")
            print(f"       (images par seconde en rendu logiciel : {ims:.0f})")
        ok("P4 aucune erreur JavaScript", not erreurs, "; ".join(erreurs[:3]))
        nav.close()


def controles_couleurs(page, base):
    """Signature chiffrée S7 (docs/references-visuelles-refonte.md)."""
    from PIL import Image
    import io
    meta = json.loads(lire(base + "donnees/meta.json"))
    n = meta["n"]
    mos = np.asarray(Image.open(io.BytesIO(lire(base + "donnees/mosaique_2048.jpg"))).convert("RGB"), np.float64)
    f = mos.shape[0] // n
    mos = mos.reshape(n, f, n, f, 3).mean(axis=(1, 3))
    regle = np.array(page.evaluate("Array.from(window.ALPES.couleurs(0, 1, 0))"), np.float64).reshape(n, n, 3)
    affiche = np.array(page.evaluate("Array.from(window.ALPES.couleurs(0, 1))"), np.float64).reshape(n, n, 3)
    de_r, de_a = np.median(delta_e(regle, mos)), np.median(delta_e(affiche, mos))
    ok("S7 aujourd'hui : couleurs affichées à ΔE ≤ 12 de la mosaïque Sentinel-2 (médiane)", de_a <= 12, f"ΔE {de_a:.1f}")
    ok("S7 règles de couleur (roche, forêt, neige) à ΔE ≤ 12 de la mosaïque au dernier état", de_r <= 12, f"ΔE {de_r:.1f}")

    # Les époques passées suivent les mêmes règles : table appliquée au relief publié
    lut = np.asarray(Image.open(io.BytesIO(lire(base + "donnees/regles.png"))).convert("RGB"), np.float64)
    H, _, _, _ = decoder_paquet(base, meta)
    T = np.array(meta["temps_Ma"])
    pires = []
    for tt in (-30.0, -10.0, -2.5):
        k = int(np.argmin(abs(T - tt)))
        h = H[k].reshape(n, n).astype(np.float64)
        gy, gx = np.gradient(h, meta["pas_m"])
        pente = np.degrees(np.arctan(np.hypot(gx, gy)))
        dc = page.evaluate(f"window.ALPES.decalage({T[k]})")
        ia = np.clip((h + dc) / 5000 * lut.shape[1] - 0.5, 0, lut.shape[1] - 1).astype(int)
        ip = np.clip(pente / 64 * lut.shape[0] - 0.5, 0, lut.shape[0] - 1).astype(int)
        attendu = lut[ip, ia]
        rendu = np.array(page.evaluate(f"Array.from(window.ALPES.couleurs({T[k]}, 1, 0))"), np.float64).reshape(n, n, 3)
        terre = h > 0
        pires.append(float(np.median(delta_e(rendu, attendu)[terre])))
    ok("S7 époques passées : mêmes règles (ΔE médian ≤ 6 entre rendu et table appliquée au relief publié)",
       max(pires) <= 6, " ; ".join(f"{t} Ma : {v:.1f}" for t, v in zip((-30, -10, -2.5), pires)))

    # Ombres portées cohérentes avec un Soleil fixe
    so = page.evaluate("window.ALPES.soleil")
    attendu = ombre_python(H[-1], n, meta["pas_m"], so["azimut"], so["hauteur"], so["pas"], so["exageration"])
    rendu = np.array(page.evaluate("Array.from(window.ALPES.couleurs(0, 2))"), np.float64).reshape(n, n, 3)[..., 0] > 127
    accord = (attendu == rendu)[2:-2, 2:-2].mean()
    part = 1 - rendu.mean()
    ok("S7 ombres portées : accord ≥ 95 % avec la marche vers le Soleil fixe, 2–40 % du relief à l'ombre",
       accord >= 0.95 and 0.02 <= part <= 0.40, f"accord {100*accord:.1f} %, ombre {100*part:.1f} %")


def main():
    srv, base = servir()
    print("Servi :", base, flush=True)
    meta = controles_donnees(base)
    controles_page(base)
    srv.shutdown()
    n_ok = sum(r[1] for r in resultats)
    print(f"\n{n_ok}/{len(resultats)} contrôles passés")
    sys.exit(0 if n_ok == len(resultats) else 1)


if __name__ == "__main__":
    main()
