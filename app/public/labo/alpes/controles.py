"""Contrôles de la page labo S7 — L'orogenèse alpine, vue d'avion.

Usage : python3 app/public/labo/alpes/controles.py
Sert app/public sur un port libre (8820–8829), mesure le paquet PUBLIÉ (donnees/)
tel que la page le lit, puis la page elle-même dans Chrome (Playwright, 390 × 844).

Exigences servies : N16 (compression et érosion simultanées), N17 (relief réaliste),
N20 (fluide sur téléphone), N23 / D-41 (fin sur le relief réel, barre qui ralentit).
"""
import gzip, http.server, json, os, socket, sys, threading, time, urllib.request
from scipy.ndimage import binary_dilation
from functools import partial
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", ".."))   # app/public
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
CHANTIER = os.path.abspath(os.path.join(ICI, "..", "..", "..", "..", "chantiers", "alpes"))


def agrandir(a, n):
    """Bilinéaire aux centres de mailles, bords répétés (identique à alpes.js et simuler.py)."""
    m = a.shape[0]
    c = np.clip((np.arange(n) + 0.5) * m / n - 0.5, 0, m - 1)
    i0 = np.floor(c).astype(int); i1 = np.minimum(i0 + 1, m - 1); w = c - i0
    a = a[i0] * (1 - w)[:, None] + a[i1] * w[:, None]
    return a[:, i0] * (1 - w)[None, :] + a[:, i1] * w[None, :]


def decoder_paquet(base, meta):
    """Décode le paquet v3 exactement comme la page (alpes.js, classe Film) : relief de chaque
    état (m), soulèvement et érosion (octets), roches (octets, interpolées entre clés)."""
    n, nr, nx, nu = meta["n"], meta["n_res"], meta["n_x"], meta["n_ue"]
    nn, K = n * n, len(meta["temps_Ma"])
    Q, QR = meta["q_cle_m"], meta["q_res_m"]
    qk, xk, res, U, E = {}, {}, {}, [None] * K, [None] * K
    qprev = xprev = None; kprev = -1
    for p in meta["paquets"]:
        b = np.frombuffer(gzip.decompress(lire(base + "donnees/" + p["fichier"])), np.uint8)
        o = 0
        for k in p["cles"]:
            d = (b[o:o + nn].astype(np.uint16) | (b[o + nn:o + 2 * nn].astype(np.uint16) << 8)).view(np.int16).astype(np.int64)
            o += 2 * nn
            q = d if qprev is None else qprev + d
            for j in range(kprev + 1, k):
                res[j] = b[o:o + nr * nr].view(np.int8).reshape(nr, nr).astype(np.float64); o += nr * nr
            x = b[o:o + nx * nx].astype(np.int64); o += nx * nx
            x = x if xprev is None else (xprev + x) % 256
            for j in (range(0, 1) if kprev < 0 else range(kprev + 1, k + 1)):
                U[j] = b[o:o + nu * nu]; E[j] = b[o + nu * nu:o + 2 * nu * nu]; o += 2 * nu * nu
            qk[k], xk[k] = q, x; qprev, xprev, kprev = q, x, k
    cles = sorted(qk)
    H = np.zeros((K, nn), np.float32); X = np.zeros((K, nx * nx), np.uint8)
    for a_, b_ in zip(cles[:-1], cles[1:]):
        H[a_] = qk[a_] * Q; X[a_] = xk[a_]
        for j in range(a_ + 1, b_):
            f = (j - a_) / (b_ - a_)
            H[j] = (qk[a_] * (1 - f) + qk[b_] * f) * Q + agrandir(res[j] * QR, n).ravel()
            X[j] = np.round(xk[a_] * (1 - f) + xk[b_] * f)
    H[cles[-1]] = qk[cles[-1]] * Q; X[cles[-1]] = xk[cles[-1]]
    return H, np.array(U), np.array(E), X


def glaciers(base):
    gm = json.loads(lire(base + "donnees/glace.json"))
    nt, N, nv, nm = len(gm["ages_ans"]), gm["n"], gm["n_v"], gm["n_moraines"]
    cum = lambda b, nn, o=0: np.cumsum(b[o:o + nt * nn].reshape(nt, nn).astype(np.int64), axis=0) % 256
    e = cum(np.frombuffer(gzip.decompress(lire(base + "donnees/glace.bin.gz")), np.uint8), N * N).reshape(nt, N, N)
    vb = np.frombuffer(gzip.decompress(lire(base + "donnees/vitesses.bin.gz")), np.uint8)
    ve = cum(vb, nv * nv).astype(np.uint8).view(np.int8).reshape(nt, nv, nv)
    vn = cum(vb, nv * nv, nt * nv * nv).astype(np.uint8).view(np.int8).reshape(nt, nv, nv)
    mo = cum(np.frombuffer(gzip.decompress(lire(base + "donnees/moraines.bin.gz")), np.uint8), nm * nm).reshape(nt, nm, nm)
    return gm, e.astype(np.uint8), ve, vn, mo


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


def nettete(h, n, pas_m, tuile_km=25.6, bande_km=(1.0, 5.0)):
    """Part de l'énergie spectrale du relief aux longueurs d'onde 1–5 km, moyenne sur les
    tuiles montagneuses (écart-type > 150 m), après retrait du plan moyen (fenêtre de Hann).
    Grandeur sans dimension : ne dépend ni de la quantité de montagnes ni d'une statistique
    globale de l'image."""
    h = np.asarray(h, np.float64).reshape(n, n)
    m = int(round(tuile_km * 1000 / pas_m))
    f = np.fft.fftfreq(m, d=pas_m / 1000)
    FX, FY = np.meshgrid(f, f)
    fr = np.hypot(FX, FY)
    bande = (fr >= 1 / bande_km[1]) & (fr <= 1 / bande_km[0])
    tout = fr > 0
    w = np.outer(np.hanning(m), np.hanning(m))
    yy, xx = np.mgrid[0:m, 0:m]
    A = np.c_[xx.ravel(), yy.ravel(), np.ones(m * m)]
    parts = []
    for i in range(0, n - m + 1, m):
        for j in range(0, n - m + 1, m):
            t = h[i:i + m, j:j + m]
            if t.std() < 150:
                continue
            c, *_ = np.linalg.lstsq(A, t.ravel(), rcond=None)
            r = (t.ravel() - A @ c).reshape(m, m) * w
            P = np.abs(np.fft.fft2(r)) ** 2
            parts.append(P[bande].sum() / P[tout].sum())
    return float(np.mean(parts)) if parts else 0.0


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
    taille = sum(int(urllib.request.urlopen(urllib.request.Request(base + "donnees/" + p["fichier"], method="HEAD")).headers["Content-Length"])
                 for p in meta["paquets"])
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(ICI) for f in fs)
    ok("D4 poids de tout le dossier publié (film, glaciers, page) ≤ 15 Mo", total <= 15e6, f"{total/1e6:.1f} Mo")

    H, U8, E8, X8 = decoder_paquet(base, meta)
    n = meta["n"]
    reel = np.frombuffer(gzip.decompress(lire(base + "donnees/" + meta.get("reel", "reel_256.bin.gz"))), "<u2").astype(np.float32)
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

    # Netteté du relief à toutes les époques (retour du maître, 23/11)
    ref = nettete(reel, n, meta["pas_m"])
    pires = []
    for k in range(len(t)):
        if t[k] >= -30:
            pires.append((nettete(H[k], n, meta["pas_m"]) / ref, t[k]))
    pire = min(pires)
    ok("S7 netteté : énergie 1–5 km ≥ 50 % de celle du relief réel dès −30 Ma",
       pire[0] >= 0.5, f"pire {100*pire[0]:.0f} % à {pire[1]} Ma (réel : {100*ref:.1f} % de l'énergie)")

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

    # N17 : grains suivis — au jour, la surface porte la couleur de leur profondeur maximale
    G = meta["grains"]["nombre"]
    gb = gzip.decompress(lire(base + "donnees/" + meta["grains"]["fichier"]))
    tex = np.frombuffer(gb[:4 * G], "<f4"); gq = np.frombuffer(gb[4 * G:8 * G], "<f4")
    K = len(t)
    def plan16(o):
        lo = np.frombuffer(gb[o:o + K * G], np.uint8).astype(np.uint16); hi = np.frombuffer(gb[o + K * G:o + 2 * K * G], np.uint8).astype(np.uint16)
        d = (lo | (hi << 8)).view(np.int16).astype(np.int64).reshape(K, G)
        return np.cumsum(d, axis=0).astype(np.int16)
    GS = plan16(8 * G) / 100.0; GZ = plan16(8 * G + 2 * K * G)
    od = 8 * G + 4 * K * G
    GD = (np.cumsum(np.frombuffer(gb[od:od + K * G], np.uint8).reshape(K, G).astype(np.int64), axis=0) % 256) * 100.0
    ax = np.array(meta["grains"]["axe_est"]); nr = np.array([-ax[1], ax[0]])
    nx_ = meta["n_x"]; ecarts = []
    xm = lambda v: (np.exp(v / 255 * np.log1p(meta["x_max_m"] / 200)) - 1) * 200
    for g in np.where(tex <= 0)[0]:
        k = int(np.searchsorted(t, tex[g]))
        k = min(k, len(t) - 1)
        dmax = GD[k][g]
        if dmax < 1000:
            continue
        x_, y_ = GS[k][g] * ax + gq[g] * nr
        j = int((x_ + meta["taille_km"] / 2) / meta["taille_km"] * nx_); i = int((meta["taille_km"] / 2 - y_) / meta["taille_km"] * nx_)
        if 0 <= i < nx_ and 0 <= j < nx_:
            ecarts.append(abs(xm(float(X8[k].reshape(nx_, nx_)[i, j])) - dmax) / dmax)
    ok("N17 grains arrivés au jour : couleur de surface = leur profondeur maximale (écart médian < 35 %)",
       len(ecarts) >= 50 and np.median(ecarts) < 0.35, f"{len(ecarts)} grains, écart médian {100*np.median(ecarts) if ecarts else 0:.0f} %")

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
        pp = page.evaluate("window.ALPES && window.ALPES.poidsPremiereImage")
        ok("N27 poids téléchargé avant la première image ≤ 4 Mo (mesuré par le navigateur)",
           pp is not None and pp <= 4e6, f"{pp/1e6:.2f} Mo" if pp is not None else "non mesuré")
        if pret:
            meta_ = json.loads(lire(base + "donnees/meta.json"))
            controles_nettete_rendu(page, base, meta_, decoder_paquet(base, meta_)[0])
            controles_couleurs(page, base)
            # Vitesse réelle de la barre : temps géologique écoulé par seconde de lecture
            mesures, angles, inst = {}, {}, {}
            for t0 in (-20, -1.9, -1.2, -0.6, -0.2):
                v = page.evaluate("""async (t0) => {
                    const A = window.ALPES; A.vitesse(1); A.aller(t0); A.lire();
                    const image = () => new Promise(r => requestAnimationFrame(ts => r([ts, A.temps(), A.compteur.etat().cible])));
                    await new Promise(r => setTimeout(r, 1200));          // amortissement de l'aiguille
                    const [ta, a, ca] = await image();
                    let tb = ta, b = a, tp = ta, bp = a, cb = ca, cp = ca;
                    while (tb - ta < 1500) { tp = tb; bp = b; cp = cb; [tb, b, cb] = await image(); }
                    const v = (b - a) / ((tb - ta) / 1000);             // vitesse moyenne
                    const vi = (b - bp) / ((tb - tp) / 1000);           // vitesse de la dernière image
                    const ang = (cp + cb) / 2; A.pause();          // cible moyenne sur la dernière image
                    return [v, ang, vi];
                }""", t0)
                mesures[t0], angles[t0], inst[t0] = v
            r = [mesures[k] for k in (-1.9, -1.2, -0.6, -0.2)]
            ok("N23 la barre ralentit : vitesse décroissante sur les 2 derniers Ma",
               all(r[i] > r[i + 1] > 0 for i in range(3)) and mesures[-20] > 3 * r[0],
               " ; ".join(f"{k} Ma : {v*1000:.0f} ka/s" for k, v in mesures.items()))

            from math import log10
            attendu = {k: -135 + 270 * min(max(log10(v * 1e6), 0), 10) / 10 for k, v in inst.items()}
            ecart_ang = max(abs(angles[k] - attendu[k]) for k in mesures)
            ra = [angles[k] for k in (-1.9, -1.2, -0.6, -0.2)]
            ok("N28 compteur : la cible de l'aiguille vaut la vitesse réelle (log, à 1° près) et redescend sur les 2 derniers Ma",
               ecart_ang <= 1.0 and all(ra[i] > ra[i + 1] for i in range(3)),
               f"écart max {ecart_ang:.2f}° ; aiguille " + ", ".join(f"{a:.1f}°" for a in ra))
            page.evaluate("window.ALPES.pause(); window.ALPES.aller(-0.5)")
            page.wait_for_function("!window.ALPES.compteur.etat().anime", timeout=60000)   # amortissement fini
            e = page.evaluate("window.ALPES.compteur.etat()")
            ok("N28 compteur : temps à l'arrêt, aiguille amortie posée sur la butée (−146°)",
               abs(e["angle"] - (-146)) <= 1 and e["sens"] == 0, f"{e['angle']:.1f}°")

            page.evaluate("window.ALPES.aller(0)")
            page.wait_for_timeout(600)
            geo = page.evaluate("""() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
                return { c: r(window.ALPES.compteur.element), bas: r(document.getElementById('bas')), date: r(document.getElementById('haut')),
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

            page.evaluate("window.ALPES.aller(-10)")
            info = page.evaluate("window.ALPES.coupe(true)")
            page.wait_for_timeout(400)
            px = page.evaluate("""() => { const c = document.getElementById('coupe'), g = c.getContext('2d');
                const d = g.getImageData(0, 0, c.width, c.height).data; let s = 0, s2 = 0, n = 0;
                for (let i = 0; i < d.length; i += 16) { const v = d[i] + d[i+1] + d[i+2]; s += v; s2 += v * v; n++; }
                const m = s / n; return Math.sqrt(s2 / n - m * m); }""")
            info = page.evaluate("window.ALPES.coupe(true)")
            page.evaluate("window.ALPES.coupe(false)")
            ok("N17 coupe : la tranche et ses grains sont dessinés", px > 20 and info["dessines"] > 100,
               f"{info['dessines']} grains dessinés sur {info['vivants']} encore enfouis, contraste {px:.0f}")
            ims = page.evaluate("""async () => { const A = window.ALPES; A.aller(-44); A.vitesse(4); A.lire();
                const t0 = performance.now(); let n = 0;
                await new Promise(r => { const f = () => { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
                A.pause(); return n / 3; }""")
            print(f"       (images par seconde en rendu logiciel : {ims:.0f})")
        ok("P4 aucune erreur JavaScript", not erreurs, "; ".join(erreurs[:3]))
        nav.close()


def controles_nettete_rendu(page, base, meta, H):
    """Netteté du relief tel qu'il est dessiné : énergie de l'ombrage (albédo gris, vue du
    zénith, 512²) aux longueurs d'onde 1–5 km, sur les tuiles où le relief publié a un
    écart-type > 150 m, rapportée à celle du relief réel dessiné de la même façon."""
    N, L = 512, meta["taille_km"]
    pas = L * 1000 / N
    def energie(tt, h):
        im = np.array(page.evaluate(f"Array.from(window.ALPES.couleurs({tt}, 5, 0, {N}))"), np.float64).reshape(N, N, 3)[..., 0]
        hh = np.repeat(np.repeat(h.reshape(meta["n"], meta["n"]), N // meta["n"], 0), N // meta["n"], 1)
        m = int(round(25.6e3 / pas)); f = np.fft.fftfreq(m, d=pas / 1000)
        fr = np.hypot(*np.meshgrid(f, f)); bande = (fr >= 0.2) & (fr <= 1.0)
        w = np.outer(np.hanning(m), np.hanning(m)); es = []
        for i in range(0, N - m + 1, m):
            for j in range(0, N - m + 1, m):
                if hh[i:i + m, j:j + m].std() < 150:
                    continue
                t_ = im[i:i + m, j:j + m]
                es.append((np.abs(np.fft.fft2((t_ - t_.mean()) * w)) ** 2)[bande].sum() / (m * m))
        return float(np.mean(es)) if es else 0.0
    T = np.array(meta["temps_Ma"])
    ref = energie(0, H[-1])
    res = []
    for tt in (-30, -29.5, -25, -18, -12.25, -6, -3):   # clés et instants entre deux clés
        k = int(np.argmin(abs(T - tt)))
        res.append((energie(T[k], H[k]) / ref, tt))
    pire = min(res)
    ok("S7 netteté du rendu : ombrage du relief à 1–5 km ≥ 50 % de celui du relief réel dès −30 Ma",
       pire[0] >= 0.5, " ; ".join(f"{t} Ma : {100*r:.0f} %" for r, t in res))


def controles_couleurs(page, base):
    """Signature chiffrée S7 (docs/references-visuelles-refonte.md)."""
    from PIL import Image
    import io
    meta = json.loads(lire(base + "donnees/meta.json"))
    n = 256                                             # mesure vue du zénith à 800 m
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
        nh = meta["n"]
        h = H[k].reshape(nh, nh).astype(np.float64)
        gy, gx = np.gradient(h, meta["pas_m"])
        pente = np.degrees(np.arctan(np.hypot(gx, gy)))
        dc = page.evaluate(f"window.ALPES.decalage({T[k]})")
        ia = np.clip((h + dc) / 5000 * lut.shape[1] - 0.5, 0, lut.shape[1] - 1).astype(int)
        ip = np.clip(pente / 64 * lut.shape[0] - 0.5, 0, lut.shape[0] - 1).astype(int)
        attendu = lut[ip, ia]
        fb = nh // n
        attendu = attendu.reshape(n, fb, n, fb, 3).mean(axis=(1, 3)); h = h.reshape(n, fb, n, fb).mean(axis=(1, 3))
        rendu = np.array(page.evaluate(f"Array.from(window.ALPES.couleurs({T[k]}, 1, 0))"), np.float64).reshape(n, n, 3)
        terre = h > 0
        pires.append(float(np.median(delta_e(rendu, attendu)[terre])))
    ok("S7 époques passées : mêmes règles (ΔE médian ≤ 6 entre rendu et table appliquée au relief publié)",
       max(pires) <= 6, " ; ".join(f"{t} Ma : {v:.1f}" for t, v in zip((-30, -10, -2.5), pires)))

    # Ombres portées cohérentes avec un Soleil fixe
    so = page.evaluate("window.ALPES.soleil")
    nh = meta["n"]; fb = nh // n
    h256 = np.maximum(H[-1].reshape(nh, nh), 0).reshape(n, fb, n, fb).mean(axis=(1, 3))
    attendu = ombre_python(h256, n, meta["pas_m"] * fb, so["azimut"], so["hauteur"], so["pas"], so["exageration"])
    rendu = np.array(page.evaluate("Array.from(window.ALPES.couleurs(0, 2))"), np.float64).reshape(n, n, 3)[..., 0] > 127
    accord = (attendu == rendu)[2:-2, 2:-2].mean()
    part = 1 - rendu.mean()
    # Glaciers du dernier cycle : l'étendue dessinée est celle des données (à une maille près)
    gm, gv, gve, gvn, gmo = glaciers(base)
    res = []
    for age in (110000, 60000, 24000, 15000):
        k = gm["ages_ans"].index(age)
        d = gv[k] >= 6
        r = np.array(page.evaluate(f"Array.from(window.ALPES.couleurs({-age/1e6}, 4))"), np.float64).reshape(n, n, 3)[..., 0] > 127
        manque = (d & ~binary_dilation(r)).sum() / max(d.sum(), 1)
        invente = (r & ~binary_dilation(d)).sum() / max(r.sum(), 1)
        res.append((age, d.sum() * 0.64, manque, invente))
    avant = np.array(page.evaluate("Array.from(window.ALPES.couleurs(-0.125, 4))")).max()
    ok("S8→S7 glace dessinée = données PISM à une maille près (≤ 2 % manquante ou inventée), rien avant 120 ka",
       all(m <= 0.02 and i <= 0.02 for _, _, m, i in res) and avant == 0,
       " ; ".join(f"{a//1000} ka : {ai:.0f} km², manque {100*m:.1f} %, inventée {100*i:.1f} %" for a, ai, m, i in res))
    gmax = gm["ages_ans"][int(np.argmax(gm["aires_km2"]))]
    ok("S8→S7 maximum glaciaire entre 30 et 18 ka, glace dans le Grésivaudan",
       18000 <= gmax <= 30000 and gv[gm["ages_ans"].index(gmax)].reshape(n, n)[int((102.4 - 15) / 0.8), int((102.4 + 12) / 0.8)] >= 6,
       f"maximum à {gmax} ans")

    # C5 (de S8) : traînées dans le sens des vitesses publiées
    sys.path.insert(0, CHANTIER)
    import moraines as MOR
    L_ = meta["taille_km"]; nv = gm["n_v"]; vmax = gm["v_max_m_a"]
    deq = lambda q: np.sign(q) * (q.astype(np.float64) / 127) ** 2 * vmax
    def bil(a, x, y):                     # x, y en km -> bilinéaire aux centres (comme vitesseAu)
        m = a.shape[0]
        c = np.clip((x + L_ / 2) / L_ * m - 0.5, 0, m - 1.001); r = np.clip((L_ / 2 - y) / L_ * m - 0.5, 0, m - 1.001)
        j, i = c.astype(int), r.astype(int); u, v = c - j, r - i
        return (a[i, j] * (1 - u) + a[i, j + 1] * u) * (1 - v) + (a[i + 1, j] * (1 - u) + a[i + 1, j + 1] * u) * v
    det, ok5 = [], True
    for age in (25000, 60000):
        k = gm["ages_ans"].index(age)
        page.evaluate(f"window.ALPES.aller({-age / 1e6}); window.ALPES.avancerTrainees(3)")
        seg = np.array(page.evaluate("window.ALPES.traineesDessinees()"), np.float64).reshape(-1, 4)
        ntr = page.evaluate("window.ALPES.nombreTrainees()")
        mx, my = (seg[:, 0] + seg[:, 2]) / 2, (seg[:, 1] + seg[:, 3]) / 2
        ur, vr = bil(deq(gve[k]), mx, my), bil(deq(gvn[k]), mx, my)
        sel = np.hypot(ur, vr) >= 1.0
        ang = np.degrees(np.abs(np.angle(np.exp(1j * (np.arctan2(seg[sel, 3] - seg[sel, 1], seg[sel, 2] - seg[sel, 0]) - np.arctan2(vr[sel], ur[sel]))))))
        masque = binary_dilation(gv[k] >= 6)
        ci = np.clip(((mx + L_ / 2) / L_ * gm["n"]).astype(int), 0, gm["n"] - 1); ri = np.clip(((L_ / 2 - my) / L_ * gm["n"]).astype(int), 0, gm["n"] - 1)
        hors = float((~masque[ri, ci]).mean()) if len(seg) else 1.0
        med = float(np.median(ang)) if len(ang) else 180.0; p95 = float(np.percentile(ang, 95)) if len(ang) else 180.0
        ok5 &= med < 15 and p95 < 45 and ntr >= 400 and hors < 0.01
        det.append(f"{age // 1000} ka : {ntr} traînées, écart médian {med:.1f}°, 95e c. {p95:.1f}°, hors glace {100 * hors:.2f} %")
    ok("C5 (S8) traînées dans le sens des vitesses publiées (médiane < 15°, 95e c. < 45°, ≥ 400, hors glace < 1 %)", ok5, " ; ".join(det))

    # C9 (de S8) : moraines médianes dessinées = celles que donnent les vitesses publiées, là où deux flux se rejoignent
    det, ok9, total = [], True, 0.0
    nm = gm["n_moraines"]; F = 3                       # tolérance ≈ 1,2 km
    for age in (60000, 15000, 110000, 20000):
        k = gm["ages_ans"].index(age)
        e_ = (gv[k].astype(np.float64) / 255) ** 2 * gm["e_max_m"] * (gv[k] >= 6)
        u_, v_ = agrandir(deq(gve[k]), gm["n"]), agrandir(deq(gvn[k]), gm["n"])
        ref = MOR.moraines(e_, u_, -v_)
        des = np.array(page.evaluate(f"Array.from(window.ALPES.couleurs({-age / 1e6}, 6, 0, {nm}))"), np.float64).reshape(nm, nm, 3)[..., 0] > 127
        km = ref.sum() / MOR.R * MOR.MAILLE_KM; total += km
        if ref.sum() == 0 and des.sum() == 0:
            det.append(f"{age // 1000} ka : aucune"); continue
        dil = lambda m_: binary_dilation(m_, iterations=F)
        prec = (des & dil(ref)).sum() / max(1, des.sum()); rapp = (ref & dil(des)).sum() / max(1, ref.sum())
        jj, ii = np.nonzero(des)
        pick = np.random.default_rng(1).choice(len(jj), size=min(300, len(jj)), replace=False) if len(jj) else np.array([], int)
        x_, y_ = (ii[pick] + 0.5) / MOR.R, (jj[pick] + 0.5) / MOR.R
        deux = MOR.deux_flux(u_, -v_, (e_ >= 1).astype(np.float64), x_, y_)
        frac = float(np.mean(deux)) if len(pick) else 0.0
        ok9 &= prec >= 0.85 and rapp >= 0.85 and frac >= 0.70
        det.append(f"{age // 1000} ka : {km:.0f} km, dessinées ⊂ données {100 * prec:.0f} %, données ⊂ dessinées {100 * rapp:.0f} %, deux flux {100 * frac:.0f} %")
    ok9 &= total >= 100
    ok("C9 (S8) moraines médianes : celles des vitesses publiées (≥ 85 % dans les deux sens), là où deux flux se rejoignent (≥ 70 %)", ok9, " ; ".join(det))

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
