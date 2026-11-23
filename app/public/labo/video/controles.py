#!/usr/bin/env python3
"""Contrôles du lecteur de texture vidéo (N27), mesurés sur la page servie.

Lance : python3 app/public/labo/video/controles.py
Sert app/public sur un port libre entre 8850 et 8859 et ouvre labo/video/ dans Chrome
sans écran. Pour chacun des trois chemins (WebCodecs H.264, WebCodecs AV1, repli
<video>) : l'image affichée (vue « carte », sans ombrage) est lue sur la capture
d'écran ; son horodatage binaire doit être l'image demandée par le curseur ; les
témoins de couleur ColorChecker doivent être à ΔE2000 ≤ 3 de leur valeur sRGB.
"""
import functools
import http.server
import io
import json
import random
import socket
import sys
import threading
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]  # app/public
CHROME = "/usr/bin/google-chrome"
META = json.loads((ICI / "essai.json").read_text())
L, H, N = META["largeur"], META["hauteur"], META["images"]
DE_MAX = 3.0
POIDS_MAX = 10e6

resultats = []


def note(nom, ok, detail=""):
    resultats.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ÉCHEC ") + nom + (f" — {detail}" if detail else ""), flush=True)


# ---------- couleur ----------
def srgb_vers_lab(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = m @ c / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hpm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hpm = (h1p + h2p) / 2
    else:
        hpm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dTh = 30 * np.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dTh)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


# ---------- serveur ----------
def port_libre():
    for p in range(8850, 8860):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("aucun port libre entre 8850 et 8859")


def servir():
    class Discret(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    port = port_libre()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Discret, directory=str(RACINE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


# ---------- lecture de l'image affichée ----------
def capture_plan(page):
    r = page.evaluate("() => window.demo.rectPlan()")
    png = page.screenshot(clip={"x": r["x"], "y": r["y"], "width": r["w"], "height": r["h"]})
    im = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), float)
    return im, im.shape[1] / L, im.shape[0] / H


def moyenne(im, sx, sy, rect, frac=0.5):
    x0, y0, x1, y1 = rect
    cx, cy, dx, dy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * frac / 2, (y1 - y0) * frac / 2
    return im[int((cy - dy) * sy):int((cy + dy) * sy), int((cx - dx) * sx):int((cx + dx) * sx)].reshape(-1, 3).mean(0)


def lit_horodatage(im, sx, sy):
    cases = META["horodatage"]["cases"]
    lum = [moyenne(im, sx, sy, c, 0.4).mean() for c in cases]
    if not (lum[0] > 200 and lum[1] < 55):
        return None
    n = 0
    for k in META["horodatage"]["bits"]:
        n = 2 * n + (1 if lum[k] > 128 else 0)
    return n


def aller(page, n):
    """Déplace le curseur de temps comme un doigt (valeur + évènement input), attend l'image dessinée."""
    page.evaluate(f"""() => {{ const c = document.querySelector('#curseur'); c.value = {n};
        c.dispatchEvent(new Event('input', {{bubbles: true}})); }}""")
    page.wait_for_function(f"() => window.demo.dessinee === {n}", timeout=8000)


def chemin(nav, base, cle, mode_attendu, tol_image, erreurs):
    print(f"\n— chemin {cle} —", flush=True)
    page = nav.new_page(viewport={"width": 1024, "height": 640}, device_scale_factor=1)
    page.on("pageerror", lambda e: erreurs.append(f"[{cle}] pageerror: {e}"))
    page.on("console", lambda m: erreurs.append(f"[{cle}] console.{m.type}: {m.text}") if m.type == "error" else None)
    q = {"h264": "codec=h264", "av1": "codec=av1", "repli": "repli=1"}[cle]
    page.goto(f"{base}?vue=plan&{q}")
    page.wait_for_function("() => window.demo && window.demo.dessinee !== null", timeout=15000)
    mode = page.evaluate("() => window.demo.mode")
    note(f"[{cle}] chemin de décodage « {mode} »", mode == mode_attendu, f"attendu « {mode_attendu} »")
    if mode != mode_attendu:
        page.close()
        return
    poids = page.evaluate("() => performance.getEntriesByType('resource').reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0) + (performance.getEntriesByType('navigation')[0]?.transferSize || 0)")
    note(f"[{cle}] poids avant la première image ≤ 10 Mo", poids <= POIDS_MAX, f"{poids / 1e6:.2f} Mo")

    # L'image affichée est celle de l'instant demandé
    seq = [0, 1, 7, 8, 9, 63, 64, 100, N - 1, 150, 3, 120, 119, 118, 56]
    lus = []
    for n in seq:
        aller(page, n)
        im, sx, sy = capture_plan(page)
        lus.append(lit_horodatage(im, sx, sy))
    bons = sum(l is not None and abs(l - n) <= tol_image for l, n in zip(lus, seq))
    note(f"[{cle}] image affichée = image demandée ({'exacte' if tol_image == 0 else f'à {tol_image} image près'}), {len(seq)} instants",
         bons == len(seq), f"demandé {seq} lu {lus}")

    # Aller-retour rapide au doigt : 40 positions sans attendre, puis une dernière
    r = random.Random(7)
    vals = [r.randrange(N) for _ in range(40)]
    page.evaluate(f"""async () => {{ const c = document.querySelector('#curseur');
        for (const v of {vals}) {{ c.value = v; c.dispatchEvent(new Event('input', {{bubbles: true}}));
          await new Promise(r => setTimeout(r, 8)); }} }}""")
    aller(page, 77)
    im, sx, sy = capture_plan(page)
    lu = lit_horodatage(im, sx, sy)
    note(f"[{cle}] aller-retour rapide (40 positions) puis arrêt sur l'image 77", lu is not None and abs(lu - 77) <= tol_image, f"lu {lu}")

    # Efficacité : avancer d'une image = un décodage en régime établi (le premier pas après
    # un atterrissage dans le cache peut repartir de l'image clé : ≤ 8) ; reculer dans le
    # cache = aucun décodage ; saut lointain ≤ 8.
    if mode.startswith("webcodecs"):
        st = lambda: page.evaluate("() => ({...window.demo.lecteur.stats})")
        aller(page, 100)
        sa = st()
        aller(page, 101)
        s0 = st()
        note(f"[{cle}] premier pas après un saut : ≤ 8 décodages", s0["decodes"] - sa["decodes"] <= 8, f"{s0['decodes'] - sa['decodes']}")
        for n in range(102, 110):
            aller(page, n)
        s1 = st()
        for n in range(108, 100, -1):
            aller(page, n)
        s2 = page.evaluate("() => ({...window.demo.lecteur.stats})")
        aller(page, 13)
        s3 = page.evaluate("() => ({...window.demo.lecteur.stats})")
        av = (s1["decodes"] - s0["decodes"]) / 8
        note(f"[{cle}] en avançant image par image (8 pas) : ≤ 1 décodage par image", av <= 1.0, f"{av:.2f}")
        note(f"[{cle}] en reculant de 8 images : tout vient du cache", s2["decodes"] == s1["decodes"], f"{s2['decodes'] - s1['decodes']} décodages")
        note(f"[{cle}] saut lointain : ≤ 8 décodages (une image clé toutes les 8)", s3["decodes"] - s2["decodes"] <= 8, f"{s3['decodes'] - s2['decodes']}")

    # Rien de l'interface ne recouvre la bande de contrôle (horodatage et témoins)
    r = page.evaluate("() => window.demo.rectPlan()")
    rects = META["horodatage"]["cases"] + [t["rect"] for t in META["temoins"]]
    pts = [(r["x"] + (x0 + x1) / 2 * r["w"] / L, r["y"] + (y0 + y1) / 2 * r["h"] / H) for x0, y0, x1, y1 in rects]
    dessus = page.evaluate(f"() => {json.dumps([list(p) for p in pts])}.map(([x, y]) => document.elementFromPoint(x, y)?.id || '?')")
    note(f"[{cle}] bande de contrôle visible, rien ne la recouvre", all(d == "vue" for d in dessus), str(sorted(set(dessus))))

    # Couleur sur l'image témoin
    aller(page, 120)
    im, sx, sy = capture_plan(page)
    des = []
    for t in META["temoins"]:
        m = moyenne(im, sx, sy, t["rect"], 0.5)
        des.append(de2000(srgb_vers_lab(t["rgb"]), srgb_vers_lab(m)))
    note(f"[{cle}] couleurs des 12 témoins à ΔE2000 ≤ {DE_MAX:g} (image 120)", max(des) <= DE_MAX,
         f"max {max(des):.2f}, médiane {float(np.median(des)):.2f}")

    # Globe : la texture vidéo est posée sur un globe qui tourne au doigt
    page.click("#bascule")
    page.wait_for_function("() => window.demo.vue === 'globe'")
    page.wait_for_timeout(300)
    avant = np.asarray(Image.open(io.BytesIO(page.screenshot())).convert("L"), float)
    cx, cy = 512, 300
    page.mouse.move(cx, cy)
    page.mouse.down()
    for k in range(1, 11):
        page.mouse.move(cx + 14 * k, cy + 2 * k)
        page.wait_for_timeout(16)
    page.mouse.up()
    page.wait_for_timeout(400)
    apres = np.asarray(Image.open(io.BytesIO(page.screenshot())).convert("L"), float)
    centre = apres[cy - 60:cy + 60, cx - 60:cx + 60]
    note(f"[{cle}] globe éclairé au centre", centre.mean() > 25, f"luminance {centre.mean():.0f}")
    diff = np.abs(apres - avant)[cy - 150:cy + 150, cx - 150:cx + 150].mean()
    note(f"[{cle}] le globe tourne au doigt", diff > 4, f"écart moyen {diff:.1f}")
    page.close()


def telephone(nav, base, erreurs):
    print("\n— téléphone 390 × 844 —", flush=True)
    tel = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    tel.on("pageerror", lambda e: erreurs.append(f"[tél.] pageerror: {e}"))
    tel.on("console", lambda m: erreurs.append(f"[tél.] console.{m.type}: {m.text}") if m.type == "error" else None)
    tel.goto(base)
    tel.wait_for_function("() => window.demo && window.demo.dessinee !== null", timeout=15000)
    tel.wait_for_timeout(500)
    g = tel.evaluate("""() => { const b = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
        return {curseur: b('#curseur'), compteur: b('.compteur-temps'), titre: b('header'), commandes: b('#commandes'), vw: innerWidth, vh: innerHeight}; }""")
    c = g["curseur"]
    note("[tél.] curseur de temps dans l'écran et large pour le doigt",
         c and c[0] >= 0 and c[2] <= g["vw"] and c[3] <= g["vh"] and (c[2] - c[0]) >= 0.6 * g["vw"] and (c[3] - c[1]) >= 28, str(c))
    k = g["compteur"]
    note("[tél.] compteur de vitesse présent et dans l'écran", k and k[0] >= 0 and k[2] <= g["vw"] and k[1] >= 0 and k[3] <= g["vh"], str(k))

    def inter(a, b):
        return a and b and not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
    note("[tél.] le compteur ne chevauche ni le titre ni les commandes", not inter(k, g["titre"]) and not inter(k, g["commandes"]))
    # glisser le curseur au doigt
    x0, y = c[0] + 10, (c[1] + c[3]) / 2
    tel.touchscreen.tap(x0 + 0.5 * (c[2] - c[0]), y)
    tel.wait_for_timeout(800)
    d = tel.evaluate("() => window.demo.dessinee")
    note("[tél.] un toucher au milieu du curseur affiche le milieu de la vidéo", d is not None and abs(d - (N - 1) / 2) <= N * 0.06, f"image {d}")
    tel.close()


def main():
    srv, port = servir()
    base = f"http://127.0.0.1:{port}/labo/video/"
    erreurs = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"], headless=True)
        p = nav.new_page()
        p.goto(base + "essai.json")
        dispo = p.evaluate("""async () => { const o = {webcodecs: typeof VideoDecoder === 'function'};
            if (o.webcodecs) for (const [k, c] of [['h264', 'avc1.640020'], ['av1', 'av01.0.04M.08']])
              o[k] = (await VideoDecoder.isConfigSupported({codec: c, codedWidth: 1024, codedHeight: 512})).supported;
            return o; }""")
        p.close()
        print("décodeurs du Chrome du banc :", dispo)
        if dispo.get("h264"):
            chemin(nav, base, "h264", "webcodecs-h264", 0, erreurs)
        else:
            note("WebCodecs H.264 disponible dans ce Chrome", False, "chemin non contrôlable ici")
        if dispo.get("av1"):
            chemin(nav, base, "av1", "webcodecs-av1", 0, erreurs)
        chemin(nav, base, "repli", "video", 1, erreurs)
        telephone(nav, base, erreurs)
        nav.close()
    srv.shutdown()
    note("aucune erreur JavaScript", not erreurs, "; ".join(erreurs[:5]))
    n_ok = sum(ok for _, ok, _ in resultats)
    print(f"\n{n_ok}/{len(resultats)} contrôles passés")
    return 0 if n_ok == len(resultats) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # page absente ou cassée : c'est un échec, pas un plantage
        note("page de démonstration chargée et mesurable", False, str(e).splitlines()[0])
        print(f"\n{sum(ok for _, ok, _ in resultats)}/{len(resultats)} contrôles passés")
        sys.exit(1)
