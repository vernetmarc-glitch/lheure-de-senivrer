"""Contrôles de la page labo S7b — L'orogenèse géodynamique.

Usage : python3 app/public/labo/orogenese/controles.py
Sert app/public sur un port libre (8830–8839), mesure le paquet PUBLIÉ (donnees/) tel que
la page le lit, puis la page elle-même dans Chrome (Playwright, 390 × 844).

Exigences servies : N30–N34, D-48 (fragments qui se déplacent et se heurtent, couches
réelles du modèle, érosion, altitudes confrontées aux estimations publiées), N28 (compteur).
"""
import gzip, http.server, io, json, os, re, socket, sys, threading
from functools import partial
from math import log10
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", ".."))   # app/public
CHEMIN = "/labo/orogenese/"
resultats = []

# Références publiées
CONVERGENCE = {(-84, 0): 680.0, (-84, -35): 420.0, (-35, 0): 260.0}   # Le Breton et al. 2021
MIOCENE = (-23.0, -5.3)
MOYENNE_MIOCENE = (1900.0, 2850.0)       # Krsnik et al. 2021 et réf.
SOMMETS_MIOCENE = (2500.0, 6500.0)       # « de 2 500 m à plus de 5 000 m »
LITHO = {"sédiments": 1, "croûte supérieure": 2, "croûte inférieure": 3,
         "manteau lithosphérique": 4, "croûte océanique": 6}


def ok(nom, cond, detail=""):
    resultats.append((nom, bool(cond), detail))
    print(("  OK   " if cond else "  ÉCHEC ") + nom + (f" — {detail}" if detail else ""), flush=True)


def port_libre():
    for p in range(8830, 8840):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                pass
    raise SystemExit("aucun port libre entre 8830 et 8839")


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def servir():
    port = port_libre()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Silencieux, directory=RACINE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}{CHEMIN}"


def lire(url):
    import urllib.request
    return urllib.request.urlopen(url, timeout=60).read()


# ---------------------------------------------------------------- paquet publié
def decoder(base, meta):
    """Décode la carte et les coupes exactement comme la page (orogenese.js, charger)."""
    nt = len(meta["temps_ma"])
    c = meta["carte"]
    n = c["nx"] * c["ny"]
    brut = gzip.decompress(lire(base + "donnees/" + c["fichier"]))
    h = np.frombuffer(brut[: 2 * n * nt], "<i2").reshape(nt, c["ny"], c["nx"]).astype(np.float32)
    f = np.frombuffer(brut[2 * n * nt: 3 * n * nt], np.uint8).reshape(nt, c["ny"], c["nx"])
    coupes = []
    for cp in meta["coupes"]:
        b = gzip.decompress(lire(base + "donnees/" + cp["fichier"]))
        k = nt * cp["nz"] * cp["nx"]
        coupes.append((np.frombuffer(b[:k], np.uint8).reshape(nt, cp["nz"], cp["nx"]),
                       np.frombuffer(b[k:k + 2 * nt * cp["nx"]], "<i2").reshape(nt, cp["nx"]).astype(np.float32)))
    return h, f, coupes


def surface_coupe(c, k):
    """Altitude publiée (m) et code du premier matériau rocheux de chaque colonne d'une coupe, à l'instant k."""
    m, topo = c
    i = np.argmax((m[k] % 8) != 0, axis=0)
    return topo[k], m[k][i, np.arange(m.shape[2])]


def controles_donnees(base):
    try:
        meta = json.loads(lire(base + "donnees/meta.json"))
        h, f, coupes = decoder(base, meta)
    except Exception as e:
        ok("D0 paquet publié lisible (meta.json, carte, coupes)", False, repr(e)[:160])
        return None
    T = np.array(meta["temps_ma"], float)
    ok("D0 paquet publié lisible (meta.json, carte, coupes)", True,
       f"{len(T)} instants de {T[0]:g} à {T[-1]:g} Ma, carte {meta['carte']['nx']}×{meta['carte']['ny']}, {len(coupes)} coupes")
    it = lambda t: int(np.argmin(abs(T - t)))
    frag = {d["nom"]: d["id"] for d in meta["fragments"]}

    # D1 convergence Europe–Adria imposée = reconstruction, mesurée sur les points suivis
    ecarts = []
    for nom, s in meta["suivi"].items():
        fac = meta["coupes"][[c["nom"] for c in meta["coupes"]].index(nom)].get("facteur_35", 1.0)
        for (a, b), ref in CONVERGENCE.items():
            if fac != 1.0 and b == 0:
                continue
            d = (np.array(s["Adria"], float) - np.array(s["Europe"], float))
            mesure = d[it(a)] - d[it(b)]
            ecarts.append((nom, a, b, mesure, ref))
    pire = max(ecarts, key=lambda e: abs(e[3] / e[4] - 1)) if ecarts else None
    ok("D1 convergence Europe–Adria = Le Breton et al. 2021 (680 km depuis 84 Ma ; 420 puis 260 km) à 10 %",
       ecarts and all(abs(m / r - 1) <= 0.10 for *_, m, r in ecarts),
       f"{len(ecarts)} mesures ; pire : {pire[0]} {pire[1]}→{pire[2]} Ma {pire[3]:.0f} km pour {pire[4]:.0f}" if pire else "aucun point suivi")

    # D2 Téthys alpine (océan liguro-piémontais) fermée vers 35 Ma : aire océanique à la surface de la carte
    pas = meta["carte"]["pas_km"]
    oc = [(f[k] == frag["océan liguro-piémontais"]).sum() * pas * pas for k in range(len(T))]
    oc0 = oc[0]
    ferme = next((T[k] for k in range(len(T)) if oc[k] < 0.05 * oc0), None) if oc0 > 0 else None
    ok("D2 Téthys ouverte à −84 Ma (≥ 20 000 km² d'océan) et fermée vers 35 Ma (< 5 % entre −42 et −30 Ma, et après)",
       oc0 >= 2e4 and ferme is not None and -42 <= ferme <= -30 and all(oc[k] < 0.05 * oc0 for k in range(len(T)) if T[k] >= -30),
       f"océan à −84 Ma : {oc0:.0f} km² ; < 5 % à {ferme} Ma ; à 0 Ma : {oc[-1]:.0f} km²")

    # D3 fragments suivis qui bougent les uns par rapport aux autres après −35 Ma
    rel = {}
    for nom, s in meta["suivi"].items():
        a = {k: np.array(v, float) for k, v in s.items()}
        rel[nom] = {k: abs((a[k][-1] - a["Europe"][-1]) - (a[k][it(-35)] - a["Europe"][it(-35)])) for k in a if k != "Europe"}
        rel[nom] = {k: (0.0 if not np.isfinite(v) else v) for k, v in rel[nom].items()}   # fragment perdu : ne compte pas
    ok("D3 au moins deux fragments bougent de ≥ 50 km par rapport à l'Europe après −35 Ma, sur chaque coupe",
       rel and all(sum(v >= 50 for v in r.values()) >= 2 for r in rel.values()),
       " ; ".join(f"{n} : " + ", ".join(f"{k} {v:.0f} km" for k, v in r.items()) for n, r in rel.items()))

    # D4 relief à −20 Ma décorrélé du relief final
    r = np.corrcoef(h[it(-20)].ravel(), h[-1].ravel())[0, 1]
    ok("D4 relief à −20 Ma décorrélé du relief final (corrélation < 0,3)", r < 0.3, f"r = {r:.2f}")

    # D5 altitudes : moyenne de la chaîne et sommets au Miocène, comparés aux estimations publiées
    moy, som = [], []
    for k in range(len(T)):
        if not (MIOCENE[0] <= T[k] <= MIOCENE[1]):
            continue
        for cp, m in zip(meta["coupes"], coupes):
            z, _ = surface_coupe(m, k)
            w = max(1, int(round(100 / cp["pas_km"])))           # fenêtre de 100 km sur la crête
            moy.append(np.convolve(z, np.ones(w) / w, "valid").max())
            som.append(z.max())
    mm, sm = (float(np.mean(moy)), float(np.max(som))) if moy else (np.nan, np.nan)
    ok("D5 altitudes miocènes : moyenne de la chaîne 1 900–2 850 m, sommets 2 500–6 500 m (Krsnik et al. 2021)",
       MOYENNE_MIOCENE[0] <= mm <= MOYENNE_MIOCENE[1] and SOMMETS_MIOCENE[0] <= sm <= SOMMETS_MIOCENE[1],
       f"moyenne {mm:.0f} m, sommet {sm:.0f} m")
    ok("D5b aucune altitude au-dessus de 7 000 m, à aucun instant", float(h.max()) <= 7000, f"max carte {h.max():.0f} m")

    # D6 vallées glaciaires seulement dans les 2,6 derniers Ma
    g = np.array(meta["glaciaire_m"], float)
    ok("D6 aucune érosion glaciaire avant −2,6 Ma", len(g) == len(T) and float(np.abs(g[T < -2.6]).sum()) == 0.0,
       f"érosion glaciaire avant −2,6 Ma : {np.abs(g[T < -2.6]).sum():.0f} m")

    # D7 continuité des couches : aucune maille sans matériau, toutes les couches présentes
    vides = sum(int((m == 255).sum()) for m, _ in coupes)
    manque = [n for n, c in LITHO.items() if not all(((m[0] % 8) == c).any() for m, _ in coupes)]
    ok("D7 couches continues : aucune maille vide dans les coupes, cinq couches présentes au départ",
       vides == 0 and not manque, f"{vides} mailles vides ; absentes : {manque or 'aucune'}")

    # D8 la carte est faite des coupes : altitude de la carte le long de chaque trace = coupe (± 300 m)
    c = meta["carte"]
    err = []
    for cp, m in zip(meta["coupes"], coupes):
        (xa, ya), (xb, yb) = cp["trace"]
        for k in (it(-60), it(-30), it(-10), len(T) - 1):
            z, _ = surface_coupe(m, k)
            xs = cp["x_front_km"] + np.linspace(-200, 200, 41)
            u = (xs - cp["x_front_km"] + 200) / 400
            X, Y = xa + u * (xb - xa), ya + u * (yb - ya)
            i = np.round((Y - c["y0_km"]) / c["pas_km"]).astype(int)
            j = np.round((X - c["x0_km"]) / c["pas_km"]).astype(int)
            dedans = (i >= 0) & (i < c["ny"]) & (j >= 0) & (j < c["nx"])
            zc = np.interp(xs, (np.arange(m[0].shape[2]) + 0.5) * cp["pas_km"], z)
            err += list(np.abs(h[k][i[dedans], j[dedans]] - zc[dedans]))
    e90 = float(np.percentile(err, 90)) if err else np.inf
    ok("D8 la carte est faite des coupes calculées (90 % des points de trace à ± 300 m)", e90 <= 300, f"P90 = {e90:.0f} m")

    # D9 le modèle bouge vraiment : les coupes changent et la chaîne monte puis s'use
    chg = [float(((m[it(-60)] != m[-1])).mean()) for m, _ in coupes]
    mx = [float(h[k].max()) for k in range(len(T))]
    kmax = int(np.argmax(mx))
    ok("D9 le modèle calcule : coupes qui changent (> 10 % des mailles), relief qui monte puis s'use quelque part",
       min(chg) > 0.10 and mx[kmax] > mx[0] + 1500 and any(
           (h[k] - h[k + 1] > 200).any() for k in range(len(T) - 1)),
       f"mailles changées {min(chg):.0%}–{max(chg):.0%} ; altitude max {mx[0]:.0f} → {mx[kmax]:.0f} m à {T[kmax]:g} Ma")

    taille = sum(os.path.getsize(os.path.join(ICI, "donnees", n)) for n in os.listdir(os.path.join(ICI, "donnees")))
    ok("D10 paquet ≤ 10 Mo avant la première image", taille <= 10e6, f"{taille/1e6:.1f} Mo")
    return meta, h, f, coupes


# ---------------------------------------------------------------- page servie
def controles_page(base, paquet):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    erreurs = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                 args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                       "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        page = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.goto(base + "?essai")
        try:
            page.wait_for_function("window.OROGENESE && window.OROGENESE.pret", timeout=120000)
            pret = True
        except Exception:
            pret = False
        ok("P1 page prête (paquet chargé)", pret, "; ".join(erreurs)[:200])
        if not pret or paquet is None:
            nav.close()
            return
        meta, h, f, coupes = paquet
        T = np.array(meta["temps_ma"], float)
        O = "window.OROGENESE"

        v = page.evaluate(f"{O}.vue()")
        ok("P2 vue des Alpes entières : 600–1 000 km de large à l'ouverture", 600 <= v["largeur_km"] <= 1000,
           f"{v['largeur_km']:.0f} km × {v['hauteur_km']:.0f} km")

        # P3 la page affiche le paquet publié : sondes comparées au décodage
        rng = np.random.default_rng(3)
        c = meta["carte"]
        mauvais = 0
        for t in (-80, -45, -20, 0):
            k = int(np.argmin(abs(T - t)))
            for _ in range(15):
                i, j = int(rng.integers(c["ny"])), int(rng.integers(c["nx"]))
                x, y = c["x0_km"] + j * c["pas_km"], c["y0_km"] + i * c["pas_km"]
                s = page.evaluate(f"{O}.aller({T[k]}), {O}.sonde({x}, {y})")
                if abs(s["altitude_m"] - h[k, i, j]) > 1 or s["fragment"] != int(f[k, i, j]):
                    mauvais += 1
        ok("P3 la page affiche le paquet publié (60 sondes : altitude à 1 m, fragment exact)", mauvais == 0, f"{mauvais} écarts")

        # P4 mouvement visible : images différentes d'une époque à l'autre
        imgs = []
        for t in (-80, -55, -35, -15, 0):
            page.evaluate(f"{O}.aller({t})")
            page.wait_for_timeout(300)
            imgs.append(np.asarray(Image.open(io.BytesIO(page.screenshot())).convert("L"), np.float32))
        d = [float(np.abs(imgs[i + 1] - imgs[i]).mean()) for i in range(4)]
        ok("P4 fragments et reliefs qui changent à l'écran (écart moyen ≥ 3 niveaux entre époques)", min(d) >= 3,
           ", ".join(f"{x:.1f}" for x in d))

        # P5 coupe : les couches réelles du modèle
        page.evaluate(f"{O}.aller(-20)")
        page.click("#bcoupe")
        page.wait_for_timeout(500)
        cinfo = page.evaluate(f"{O}.coupeInfo()")
        couleurs = {tuple(int(cc[i:i + 2], 16) for i in (1, 3, 5)) for cc in cinfo["couleurs_couches"]}
        px = np.asarray(Image.open(io.BytesIO(page.locator("#coupe").screenshot())).convert("RGB")).reshape(-1, 3)
        pres = sum(1 for cc in couleurs if (np.abs(px.astype(int) - cc).sum(1) <= 24).mean() > 0.002)
        ok("P5 bouton coupe : ≥ 5 couches du modèle visibles, échelle en km", cinfo["visible"] and pres >= 5 and "km" in cinfo["echelle"],
           f"{pres} couches visibles, échelle « {cinfo['echelle']} »")
        page.click("#bcoupe")

        # P6 compteur : cible de l'aiguille = vitesse réelle (log, à 1°), lisible, sans masquer les commandes
        v = page.evaluate(f"""async () => {{
            const A = {O}; A.aller(-70); A.lire();
            const image = () => new Promise(r => requestAnimationFrame(ts => r([ts, A.temps()])));
            await new Promise(r => setTimeout(r, 1200));
            let [ta, a] = await image(); let tp = ta, bp = a, tb = ta, b = a;
            while (tb - ta < 1200) {{ tp = tb; bp = b; [tb, b] = await image(); }}
            const vi = (b - bp) / ((tb - tp) / 1000); const ang = A.compteur.etat().cible; A.pause();
            return [vi, ang]; }}""")
        att = -135 + 270 * min(max(log10(max(v[0], 1e-12) * 1e6), 0), 10) / 10
        geo = page.evaluate(f"""() => {{ const r = e => {{ const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; }};
            return {{ c: r({O}.compteur.element), bas: r(document.getElementById('bas')) }}; }}""")
        cc, bas = geo["c"], geo["bas"]
        inter = cc[0] < bas[2] and bas[0] < cc[2] and cc[1] < bas[3] and bas[1] < cc[3]
        ok("P6 compteur : aiguille = vitesse réelle (à 1°), ≥ 100 px, ne masque pas les commandes",
           abs(v[1] - att) <= 1 and (cc[2] - cc[0]) >= 100 and not inter,
           f"{v[0]*1e6:.3g} ans/s → attendu {att:.1f}°, aiguille {v[1]:.1f}° ; {cc[2]-cc[0]:.0f} px")

        # P7 textes courts, sensibles, en français, qui suivent le temps
        textes = []
        for t in np.linspace(-84, 0, 29):
            page.evaluate(f"{O}.aller({t})")
            textes.append(page.inner_text("#recit").strip())
        uniques = list(dict.fromkeys(x for x in textes if x))
        anglais = [x for x in uniques if re.search(r"\b(the|and|of|is|with)\b", x)]
        ok("P7 récit : ≥ 5 textes français de ≤ 220 signes qui suivent le temps",
           len(uniques) >= 5 and all(len(x) <= 220 for x in uniques) and not anglais,
           f"{len(uniques)} textes, plus long {max(map(len, uniques), default=0)} signes")

        # P8 date affichée = temps de la page
        page.evaluate(f"{O}.aller(-47.3)")
        dt = page.inner_text("#date")
        ok("P8 date affichée en Ma = temps de la page", "47" in dt and "Ma" in dt, dt)
        ok("P9 aucune erreur dans la console", not erreurs, "; ".join(erreurs)[:200])
        nav.close()


def main():
    srv, base = servir()
    print(f"Contrôles S7b sur {base}")
    paquet = controles_donnees(base)
    try:
        controles_page(base, paquet)
    except Exception as e:
        ok("P page servie", False, repr(e)[:200])
    srv.shutdown()
    n_ok = sum(1 for _, c, _ in resultats if c)
    print(f"\n{n_ok}/{len(resultats)} contrôles verts")
    return 0 if n_ok == len(resultats) else 1


if __name__ == "__main__":
    sys.exit(main())
