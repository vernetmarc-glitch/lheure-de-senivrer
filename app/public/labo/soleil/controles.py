#!/usr/bin/env python3
"""Contrôles du chantier S1 — Naissance et allumage du Soleil (labo/soleil).

Mesure ce qui est PUBLIÉ : les fichiers de `donnees/` tels qu'ils sont servis, et la
page `index.html` servie localement (Playwright + Chrome sans écran, 390 × 844).

    python3 app/public/labo/soleil/controles.py

Un seul échec bloque la publication (règle 0). Chaque contrôle porte l'exigence qu'il
protège (N4 : on voit le nuage s'agglutiner et le Soleil s'allumer ; N20 : même
esthétique qu'à toutes les échelles, fluide sur téléphone).

Seuils fixés le 19/11/2026, avant toute construction :
  D02 masse totale (gaz + étoiles) conservée à 1 % à chaque instant ;
  D03 moment cinétique total (orbital + spin des puits), sur l'axe de rotation, conservé à 5 % ;
  D05 disque : rapport d'aspect (épaisseur / rayon) < 0,3, rayon ≥ 20 UA ;
  D08 luminosité de la page = trajectoire publiée (BHAC15, 1 M☉) à 5 % ;
  P02 vides noirs ≥ 45 % des pixels, ≥ 300 pixels brillants, à trois instants.

Ajoutés le 23/11/2026 (directives de Marc, docs/references-visuelles-refonte.md, N25, N28) :
  P09 signature de la référence (disque de HL Tauri, ALMA 2014) : au stade disque, le long
      d'un rayon, au moins 3 anneaux et sillons alternés (contraste sillon/anneau ≥ 2) ;
      fond noir ≥ 60 % du cadre ;
  P10 compteur de vitesse du temps : angle de l'aiguille = vitesse réelle du curseur
      (échelle log, à 1° près après amortissement), butée à l'arrêt, cadran ≤ 150 px sur
      390 px de large (taille maximale du composant commun app/public/commun/compteur.js),
      ne masque ni l'étoile ni le cœur du nuage.
"""
import functools
import http.server
import json
import math
import os
import re
import socket
import sys
import threading
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(ICI, "donnees")
RES = []


def note(cle, exigence, ok, detail):
    RES.append((cle, exigence, bool(ok), detail))
    print(f"[{'OK ' if ok else 'ÉCHEC'}] {cle} ({exigence}) — {detail}", flush=True)


def garde(cle, exigence):
    """Un contrôle qui lève une exception est un échec, jamais un oubli."""
    def deco(f):
        @functools.wraps(f)
        def g(*a, **k):
            try:
                return f(*a, **k)
            except Exception as e:  # noqa: BLE001
                note(cle, exigence, False, f"exception : {type(e).__name__}: {e}")
        return g
    return deco


# ---------------------------------------------------------------- données publiées
def charge_meta():
    with open(os.path.join(DON, "soleil.json"), encoding="utf-8") as f:
        return json.load(f)


def decode_instant(meta, k):
    """Positions (UA, NaN si absente) et températures (K) publiées de l'instant k."""
    N = meta["n_points"]
    ins = meta["instants"][k]
    with open(os.path.join(DON, ins["fichier"]), "rb") as f:
        f.seek(ins["octet"])
        q = np.frombuffer(f.read(N * 6), dtype="<u2").reshape(N, 3).astype(np.float64)
        tb = np.frombuffer(f.read(N), dtype=np.uint8).astype(np.float64)
    vide = (q == 0).any(axis=1)
    pos = (q - 32768.0) / 32767.0 * ins["L"]
    pos[vide] = np.nan
    lt = meta["codage_T"]
    T = 10 ** (lt["log_min"] + (tb - 1) / 254.0 * (lt["log_max"] - lt["log_min"]))
    T[tb == 0] = np.nan
    return pos, T


@garde("S1-D01", "N20")
def d01_presence(meta):
    N, K = meta["n_points"], len(meta["instants"])
    tailles = {}
    for ins in meta["instants"]:
        tailles[ins["fichier"]] = max(tailles.get(ins["fichier"], 0), ins["octet"] + 7 * N)
    manque = [f for f, t in tailles.items() if not os.path.exists(os.path.join(DON, f))
              or os.path.getsize(os.path.join(DON, f)) < t]
    total = sum(os.path.getsize(os.path.join(DON, f)) for f in os.listdir(DON))
    ok = not manque and K >= 100 and N >= 20000 and total <= 40e6
    note("S1-D01", "N20", ok, f"{K} instants × {N} points, {total/1e6:.1f} Mo publiés "
         f"(≥ 100 instants, ≥ 20 000 points, ≤ 40 Mo) ; fichiers incomplets : {manque or 'aucun'}")


@garde("S1-D02", "N4")
def d02_masse(meta):
    b = meta["bilan"]
    m = np.array([x["masse"] for x in b])
    ecart = np.max(np.abs(m / m[0] - 1))
    note("S1-D02", "N4", ecart <= 0.01 and len(b) >= 10,
         f"masse gaz + étoiles sur {len(b)} sorties : écart max {100*ecart:.3f} % (≤ 1 %)")


@garde("S1-D03", "N4")
def d03_moment(meta):
    # Moment cinétique total (gaz + étoiles : orbital + spin des puits), projeté sur l'axe de
    # rotation initial. La boîte de Phantom est périodique : le milieu tiède qui entoure le
    # cœur traverse les bords, ce qui brouille les composantes transverses du vecteur sans
    # rien changer de physique ; la projection sur l'axe, elle, doit se conserver.
    b = meta["bilan"]
    L = np.array([[x["Lx"], x["Ly"], x["Lz"]] for x in b])
    axe = L[0] / np.linalg.norm(L[0])
    Lp = L @ axe
    ecart = np.max(np.abs(Lp / Lp[0] - 1))
    note("S1-D03", "N4", ecart <= 0.05 and Lp[0] > 0,
         f"moment cinétique total sur l'axe de rotation (orbital + spin des étoiles), {len(b)} sorties : "
         f"écart max {100*ecart:.2f} % (≤ 5 %)")


@garde("S1-D04", "N4")
def d04_etoile(meta):
    tn = meta.get("t_naissance")
    der = meta["instants"][-1]["puits"]
    mt = sum(p["m"] for p in der)
    mp = max((p["m"] for p in der), default=0.0)
    ok = tn is not None and mp >= 0.1 and mp >= 0.8 * mt
    note("S1-D04", "N4", ok, f"naissance à {tn and round(tn)} ans ; {len(der)} puits, le principal "
         f"pèse {mp:.3f} M☉ ({100*mp/max(mt,1e-30):.0f} % des étoiles) (≥ 0,1 M☉ et ≥ 80 %)")


def principal(ins):
    return max(ins["puits"], key=lambda p: p["m"])


@garde("S1-D05", "N4")
def d05_disque(meta):
    k = len(meta["instants"]) - 1
    pos, _ = decode_instant(meta, k)
    s = principal(meta["instants"][k])
    r = pos[~np.isnan(pos[:, 0])] - np.array([s["x"], s["y"], s["z"]])
    d = np.linalg.norm(r, axis=1)
    r = r[d < 1000.0]
    # axe du disque : moment cinétique publié du gaz proche n'existe pas (positions seules) →
    # axe de plus petite inertie du gaz à moins de 1 000 UA de l'étoile
    if len(r) < 500:
        note("S1-D05", "N4", False, f"seulement {len(r)} points à moins de 1 000 UA de l'étoile")
        return
    I = r.T @ r / len(r)
    w, v = np.linalg.eigh(I)
    z = r @ v[:, 0]
    R = np.linalg.norm(r - np.outer(z, v[:, 0]), axis=1)
    Rd = np.percentile(R, 80)
    asp = np.sqrt(np.mean(z ** 2)) / np.sqrt(np.mean(R ** 2))
    note("S1-D05", "N4", asp < 0.3 and Rd >= 20.0,
         f"dernier instant : {len(r)} points à < 1 000 UA, rapport d'aspect {asp:.3f} (< 0,3), "
         f"rayon à 80 % {Rd:.0f} UA (≥ 20 UA)")


@garde("S1-D06", "N4")
def d06_agglutine(meta):
    def r50(k):
        pos, _ = decode_instant(meta, k)
        p = pos[~np.isnan(pos[:, 0])]
        # rayon de demi-masse rapporté à TOUS les points (les absorbés par l'étoile sont au centre)
        n = meta["n_points"]
        d = np.sort(np.linalg.norm(p, axis=1))
        absorbes = n - len(d)
        i = n // 2 - absorbes
        return 0.0 if i <= 0 else d[i]
    a, b = r50(0), r50(len(meta["instants"]) - 1)
    note("S1-D06", "N4", b <= a / 10, f"rayon de demi-masse {a:.0f} UA → {b:.0f} UA (facteur ≥ 10)")


def table_bhac15():
    """Trajectoire 1,0 M☉ publiée, telle que téléchargée (fichier brut publié)."""
    ages, L, Te, R = [], [], [], []
    with open(os.path.join(DON, "bhac15_1.0Msol.txt"), encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("#") or not ligne.strip():
                continue
            c = ligne.split()
            # colonnes BHAC15 : M/Ms log t(yr) Teff L/Ls g R/Rs ...
            ages.append(10 ** float(c[1])); Te.append(float(c[2])); L.append(10 ** float(c[3]))
            R.append(float(c[5]))
    return np.array(ages), np.array(L), np.array(Te), np.array(R)


@garde("S1-D09", "N4")
def d09_hydrogene():
    a, L, Te, R = table_bhac15()
    # l'hydrogène prend le relais quand la contraction s'arrête : premier âge où R est à 2 %
    # de son minimum (séquence principale d'âge zéro)
    i = np.argmax(R <= R.min() * 1.02)
    ok = 25e6 <= a[i] <= 60e6
    note("S1-D09", "N4", ok, f"trajectoire BHAC15 1 M☉ : {len(a)} âges ; la contraction s'arrête "
         f"vers {a[i]/1e6:.0f} Ma (attendu 30–50 Ma, toléré 25–60)")


# ---------------------------------------------------------------- page servie
class Silence(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serveur():
    for port in range(8840, 8850):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                break
    else:
        raise RuntimeError("aucun port libre entre 8840 et 8849")
    # on sert app/public entier : la page importe ../../commun/compteur.js
    h = functools.partial(Silence, directory=os.path.dirname(os.path.dirname(ICI)))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def luma(img):
    a = img[..., :3].astype(np.float64) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def capture(page):
    """Image du canevas WebGL seul (ce que la page dessine), sans les textes posés dessus."""
    from PIL import Image
    import base64
    import io
    url = page.evaluate("document.getElementById('ciel').toDataURL('image/png')")
    img = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
    w = page.evaluate("document.getElementById('ciel').clientWidth")
    if img.width != w:   # écran à haute densité : on mesure à la taille CSS
        img = img.resize((w, round(img.height * w / img.width)), Image.BILINEAR)
    return np.array(img)


def controles_page():
    from playwright.sync_api import sync_playwright
    srv, port = serveur()
    erreurs = []
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                      "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1,
                              has_touch=True, is_mobile=True)
        page = ctx.new_page()
        page.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"),
                   lambda r: r.fulfill(status=200, body="", content_type="text/css"))
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.on("console", lambda m: m.type == "error" and erreurs.append(m.text))
        page.goto(f"http://127.0.0.1:{port}/labo/soleil/index.html")
        try:
            page.wait_for_function("window.__soleil && window.__soleil.pret === true", timeout=120000)
            pret = True
        except Exception as e:  # noqa: BLE001
            pret = False
            erreurs.append(f"page jamais prête : {e}")
        gl2 = page.evaluate("!!document.createElement('canvas').getContext('webgl2')")
        if not pret:
            note("S1-P01", "N20", False, f"WebGL2 {gl2} ; erreurs : {erreurs[:3]}")
            nav.close(); srv.shutdown(); return
        page.evaluate("window.__soleil.joue(false)")
        meta = page.evaluate("window.__soleil.meta")

        # P02 — vides noirs et points brillants, trois instants
        try:
            tn = meta["t_naissance"]
            t_fin = meta["instants"][-1]["t"]
            moments = [("début", 0.0), ("effondrement", 0.85 * tn), ("disque", t_fin)]
            det, ok = [], True
            for nom, t in moments:
                page.evaluate(f"window.__soleil.regle({t})")
                page.wait_for_timeout(400)
                y = luma(capture(page))
                noir = float(np.mean(y < 0.03))
                brill = int(np.sum(y >= 0.5))
                ok &= noir >= 0.45 and brill >= 300
                det.append(f"{nom} : {100*noir:.0f} % noirs, {brill} brillants")
            note("S1-P02", "N20", ok, " ; ".join(det) + " (≥ 45 % et ≥ 300)")
        except Exception as e:  # noqa: BLE001
            note("S1-P02", "N20", False, f"exception : {e}")

        # P03 — ton à bornes fixes : retirer la moitié des points assombrit l'image
        try:
            page.evaluate(f"window.__soleil.regle({0.85 * meta['t_naissance']})")
            page.wait_for_timeout(300)
            a = luma(capture(page)).mean()
            page.evaluate("window.__soleil.masque(0.5)"); page.wait_for_timeout(300)
            b = luma(capture(page)).mean()
            page.evaluate("window.__soleil.masque(1.0)"); page.wait_for_timeout(200)
            note("S1-P03", "N20", a > 0 and b / a < 0.9,
                 f"luminance moyenne {a:.4f} → {b:.4f} avec moitié des points (rapport {b/max(a,1e-9):.2f} < 0,9 : "
                 "aucune normalisation par l'image)")
        except Exception as e:  # noqa: BLE001
            note("S1-P03", "N20", False, f"exception : {e}")

        # P04 — curseur et lecture
        try:
            page.evaluate("window.__soleil.regle(0)")
            t0 = page.evaluate("window.__soleil.t")
            page.locator("#lecture").click(); page.wait_for_timeout(1500)
            t1 = page.evaluate("window.__soleil.t")
            page.locator("#lecture").click()
            bb = page.locator("#curseur").bounding_box()
            page.mouse.click(bb["x"] + bb["width"] * 0.75, bb["y"] + bb["height"] / 2)
            page.wait_for_timeout(300)
            t2 = page.evaluate("window.__soleil.t")
            txt = page.locator("#temps").inner_text()
            ok = t1 > t0 and t2 > meta["t_naissance"] and len(txt) > 3
            note("S1-P04", "N4", ok, f"lecture : {t0:.0f} → {t1:.0f} ans ; curseur aux 3/4 : {t2:.3g} ans "
                 f"(après la naissance) ; étiquette « {txt} »")
        except Exception as e:  # noqa: BLE001
            note("S1-P04", "N4", False, f"exception : {e}")

        # P05 — rotation de la vue au doigt
        try:
            page.evaluate(f"window.__soleil.regle({meta['instants'][-1]['t']})"); page.wait_for_timeout(300)
            a = capture(page).astype(float)
            bb = page.locator("#ciel").bounding_box()
            cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
            page.mouse.move(cx, cy); page.mouse.down()
            for i in range(10):
                page.mouse.move(cx + 12 * i, cy + 6 * i)
            page.mouse.up(); page.wait_for_timeout(300)
            b = capture(page).astype(float)
            dif = float(np.mean(np.abs(a - b)))
            note("S1-P05", "N20", dif > 0.5, f"glisser du doigt : écart moyen d'image {dif:.2f} niveaux (> 0,5)")
        except Exception as e:  # noqa: BLE001
            note("S1-P05", "N20", False, f"exception : {e}")

        # P06 — l'étoile s'allume et reste seule quand le disque s'est dissipé
        try:
            page.evaluate("window.__soleil.vueParDefaut()")
            res = []
            for t in [meta["t_naissance"] * 0.999, meta["t_naissance"] + 2e4, 4.6e7]:
                page.evaluate(f"window.__soleil.regle({t})"); page.wait_for_timeout(300)
                xy = page.evaluate("window.__soleil.ecranEtoile()")
                y = luma(capture(page))
                if xy is None:
                    res.append((None, float(np.mean(y < 0.03))))
                else:
                    i, j = int(round(xy[1])), int(round(xy[0]))
                    res.append((float(y[max(i-2,0):i+3, max(j-2,0):j+3].max()), float(np.mean(y < 0.03))))
            ok = (res[1][0] is not None and res[1][0] >= 0.9 and res[2][0] is not None and res[2][0] >= 0.9
                  and res[2][1] >= 0.9)
            note("S1-P06", "N4", ok, f"avant naissance {res[0][0]} ; +20 000 ans éclat {res[1][0]} ; "
                 f"46 Ma éclat {res[2][0]}, {100*res[2][1]:.0f} % de noir (étoile ≥ 0,9 ; noir ≥ 90 %)")
        except Exception as e:  # noqa: BLE001
            note("S1-P06", "N4", False, f"exception : {e}")

        # P07 — couleur par la température : au stade disque, étoile masquée, le gaz du disque
        # intérieur (plus dense, donc plus chaud) est plus rouge-or que le gaz froid du dehors
        try:
            page.evaluate("window.__soleil.vueParDefaut()")
            page.evaluate("window.__soleil.etoile(false)")
            page.evaluate(f"window.__soleil.regle({meta['instants'][-1]['t']})"); page.wait_for_timeout(300)
            img = capture(page).astype(float)
            page.evaluate("window.__soleil.etoile(true)")
            y = luma(img.astype(np.uint8))
            xy = page.evaluate("window.__soleil.ecranCentre()")
            H, W = y.shape
            jj, ii = np.meshgrid(np.arange(W), np.arange(H))
            d = np.hypot(jj - xy[0], ii - xy[1])
            def ratio(m):
                m = m & (y > 0.05)
                return float(img[m][:, 0].sum() / max(img[m][:, 2].sum(), 1.0)), int(m.sum())
            u = page.evaluate("window.__soleil.uaParPx()")
            d = d * u   # UA (projetées)
            rc, nc = ratio((d > 30) & (d < 120))
            rp, npx = ratio((d > 130) & (d < 260))
            note("S1-P07", "N20", nc > 5 and npx > 50 and rc > 1.3 * rp,
                 f"stade disque, étoile masquée : rapport rouge/bleu à 30–120 UA {rc:.2f} ({nc} px) "
                 f"contre {rp:.2f} à 130–260 UA ({npx} px) (× 1,3)")
        except Exception as e:  # noqa: BLE001
            note("S1-P07", "N20", False, f"exception : {e}")

        # P08 — fluidité : intervalle médian entre images pendant la lecture
        try:
            page.evaluate("window.__soleil.regle(0)")
            page.evaluate("window.__soleil.joue(true)")
            dts = page.evaluate("""() => new Promise(res => { const d = []; let p = performance.now();
                function f(n) { d.push(n - p); p = n; if (d.length < 90) requestAnimationFrame(f); else res(d); }
                requestAnimationFrame(f); })""")
            page.evaluate("window.__soleil.joue(false)")
            med = float(np.median(dts[5:]))
            cpu = page.evaluate("window.__soleil.dureeImage()")
            note("S1-P08", "N20", cpu <= 16.0,
                 f"temps de calcul d'une image côté page {cpu:.1f} ms (≤ 16 ms) ; intervalle médian "
                 f"{med:.1f} ms sous rendu logiciel (indicatif)")
        except Exception as e:  # noqa: BLE001
            note("S1-P08", "N20", False, f"exception : {e}")

        # P09 — signature HL Tauri : anneaux et sillons concentriques. Profil radial de la
        # luminance en ellipses déprojetées (inclinaison de la vue), moyenné en azimut : un
        # anneau est un tour complet, pas un amas de points sur un rayon. Étoile masquée.
        try:
            page.evaluate("window.__soleil.vueParDefaut()")
            page.evaluate("window.__soleil.etoile(false)")
            t_d = page.evaluate("window.__soleil.tDisque")
            page.evaluate(f"window.__soleil.regle({t_d})"); page.wait_for_timeout(400)
            y = luma(capture(page))
            page.evaluate("window.__soleil.etoile(true)")
            noir = float(np.mean(y < 0.03))
            xy = page.evaluate("window.__soleil.ecranCentre()")
            inc = page.evaluate("window.__soleil.inclinaison()")
            H, W = y.shape
            jj, ii = np.meshgrid(np.arange(W), np.arange(H))
            rr = np.hypot(jj - xy[0], (ii - xy[1]) / max(np.cos(inc), 0.2))
            nb = int(min(W / 2, 300) // 3)
            prof = np.array([y[(rr >= 3 * i) & (rr < 3 * i + 3)].mean() if np.any((rr >= 3 * i) & (rr < 3 * i + 3)) else 0.0
                             for i in range(nb)])
            prof = np.convolve(prof, np.ones(3) / 3, mode="same")
            # extrema alternés ; une paire anneau/sillon compte si anneau ≥ 2 × sillon et anneau visible
            ext = [(i, prof[i]) for i in range(2, nb - 1) if (prof[i] - prof[i-1]) * (prof[i+1] - prof[i]) < 0]
            paires = sum(1 for (i, a), (j, b) in zip(ext, ext[1:])
                         if max(a, b) > 0.04 and max(a, b) >= 2 * max(min(a, b), 1e-3) and j - i >= 2)
            n_ann = paires // 2
            note("S1-P09", "N25", n_ann >= 3 and noir >= 0.60,
                 f"stade disque ({t_d:.3g} ans), profil azimutal déprojeté : {n_ann} anneaux séparés de sillons "
                 f"de contraste ≥ 2 (≥ 3) ; fond noir {100*noir:.0f} % (≥ 60 %)")
        except Exception as e:  # noqa: BLE001
            note("S1-P09", "N25", False, f"exception : {e}")

        # P10 — compteur de vitesse du temps
        try:
            # 1) pendant la lecture, la cible de l'aiguille est la vitesse réelle du curseur
            page.evaluate("window.__soleil.regle(0)")
            page.evaluate("window.__soleil.joue(true)"); page.wait_for_timeout(1500)
            r = page.evaluate("""() => { const s = window.__soleil, c = s.compteur;
                return { cible: c.etat().cible, attendu: c.angleCible(s.vitesseCurseur()), v: s.vitesseCurseur() }; }""")
            # 2) à vitesse constante, l'aiguille amortie rejoint sa cible à 1° près
            page.evaluate("window.__soleil.joue(false)")
            page.evaluate("window.__soleil.vitesseImposee = 1e6"); page.wait_for_timeout(2500)
            r["a"] = page.evaluate("window.__soleil.compteur.angle()")
            r["a_cible"] = page.evaluate("window.__soleil.compteur.angleCible(1e6)")
            page.evaluate("window.__soleil.vitesseImposee = null"); page.wait_for_timeout(1500)
            page.evaluate("window.__soleil.joue(false)"); page.wait_for_timeout(1500)
            arret = page.evaluate("window.__soleil.compteur.angle()")
            butee = page.evaluate("window.__soleil.compteur.angleCible(0)")
            bb = page.evaluate("(() => { const b = window.__soleil.compteur.boite(); return [b.left, b.top, b.width, b.height]; })()")
            libres = []
            for t in [0.0, meta["t_naissance"] * 0.999, meta["t_naissance"] + 2e4]:
                page.evaluate(f"window.__soleil.regle({t})"); page.wait_for_timeout(100)
                for nom in ("ecranEtoile", "ecranCentre"):
                    q = page.evaluate(f"window.__soleil.{nom}()")
                    if q is not None:
                        libres.append(not (bb[0] - 8 <= q[0] <= bb[0] + bb[2] + 8 and bb[1] - 8 <= q[1] <= bb[1] + bb[3] + 8))
            ok = (abs(r["cible"] - r["attendu"]) <= 1.0 and abs(r["a"] - r["a_cible"]) <= 1.0 and r["v"] > 0 and abs(arret - butee) <= 1.0
                  and bb[2] <= 150 and bb[0] + bb[2] <= 390 and all(libres))
            note("S1-P10", "N28", ok, f"lecture : {r['v']:.3g} ans/s, cible de l'aiguille {r['cible']:.1f}° pour {r['attendu']:.1f}° ; "
                 f"à 1 Ma/s constant : aiguille {r['a']:.1f}° pour {r['a_cible']:.1f}° ; "
                 f"arrêt : {arret:.1f}° (butée {butee:.1f}°) ; cadran {bb[2]:.0f} px de large ; "
                 f"étoile et cœur hors du cadran : {all(libres)}")
        except Exception as e:  # noqa: BLE001
            note("S1-P10", "N28", False, f"exception : {e}")

        # D08 — luminosité de la page = trajectoire publiée à 5 %
        try:
            a, L, Te, R = table_bhac15()
            Lp = np.array(page.evaluate(f"{json.dumps(a.tolist())}.map(x => window.__soleil.luminosite(x))"))
            m = a <= 1e8
            ec = np.abs(Lp[m] / L[m] - 1)
            note("S1-D08", "N4", m.sum() >= 10 and ec.max() <= 0.05,
                 f"{m.sum()} âges BHAC15 ≤ 100 Ma : écart max de la page {100*ec.max():.2f} % (≤ 5 %)")
        except Exception as e:  # noqa: BLE001
            note("S1-D08", "N4", False, f"exception : {e}")

        page.wait_for_timeout(200)
        note("S1-P01", "N20", gl2 and not erreurs, f"WebGL2 {gl2} ; erreurs JavaScript : {erreurs[:3] or 'aucune'}")
        nav.close()
    srv.shutdown()


def main():
    try:
        meta = charge_meta()
    except Exception as e:  # noqa: BLE001
        meta = None
        note("S1-D01", "N20", False, f"données illisibles : {e}")
    if meta is not None:
        d01_presence(meta); d02_masse(meta); d03_moment(meta); d04_etoile(meta)
        d05_disque(meta); d06_agglutine(meta)
    d09_hydrogene()
    try:
        controles_page()
    except Exception as e:  # noqa: BLE001
        note("S1-P01", "N20", False, f"page non contrôlable : {e}")
    attendus = ["S1-D01", "S1-D02", "S1-D03", "S1-D04", "S1-D05", "S1-D06", "S1-D08", "S1-D09",
                "S1-P01", "S1-P02", "S1-P03", "S1-P04", "S1-P05", "S1-P06", "S1-P07", "S1-P08", "S1-P09", "S1-P10"]
    vus = {r[0]: r for r in RES}
    for c in attendus:
        if c not in vus:
            note(c, "—", False, "non exécuté")
    n_ok = sum(1 for c in attendus if {r[0]: r for r in RES}[c][2])
    print(f"\n{n_ok} contrôles passés, {len(attendus) - n_ok} en échec (sur {len(attendus)})")
    sys.exit(0 if n_ok == len(attendus) else 1)


if __name__ == "__main__":
    main()
