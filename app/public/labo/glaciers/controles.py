#!/usr/bin/env python3
"""Contrôles de la page labo « glaciers » (chantier S8, exigence N22, décision D-42).

Mesure la page SERVIE (serveur local, Chrome sans tête, WebGL2 logiciel), pas un
aperçu. Les références viennent directement des champs flottants de la simulation
(chantiers/glaciers/reference/reference.npz, écrit par le workflow à partir de
Seguinot et al. 2018), jamais de la page elle-même.

  C1 données publiées   : le paquet publié redonne exactement les masques de glace
                          de la simulation, et les vitesses à 0,1 m/a près
  C2 étendue affichée   : à six instants de la simulation, la glace dessinée (vue de
                          plan, même shader que la vue d'avion) est celle des données
                          à une maille près (≥ 99,5 % dans les deux sens)
  C3 entre deux pas     : entre deux pas de 1 000 ans, aucune glace inventée hors des
                          deux états voisins, aucune disparue de leur partie commune
  C4 maximum            : l'aire dessinée suit celle des données (3 %) ; son maximum
                          tombe entre 20 000 et 30 000 ans, avec de la glace dans le
                          Grésivaudan
  C5 écoulement         : les traînées dessinées vont dans le sens des vitesses de
                          surface publiées (écart angulaire médian < 15°, 95e centile
                          < 45°), au moins 400 traînées, aucune hors de la glace (< 1 %,
                          y compris juste après un saut dans le temps)
  C6 erreurs            : aucune erreur JavaScript ni de console
  C7 fluidité           : téléphone 390 × 844 : temps JavaScript médian par image
                          < 8 ms ; intervalle médian entre images < 50 ms même en
                          rendu logiciel
  C8 lecture            : la page montre l'âge, les noms des lieux, et une image non vide
  C9 moraines médianes  : signature de la référence visuelle (Aletsch, Mer de Glace) :
                          les moraines dessinées sont celles que donnent les vitesses
                          publiées (≥ 85 % dans les deux sens, à 1 km près) et elles sont
                          là où deux flux se rejoignent : de part et d'autre d'une moraine,
                          en remontant le courant, les deux glaces viennent de part et
                          d'autre d'un éperon ou d'un nunatak (points à ± 750 m, remontés
                          sur 80 km ; ≥ 70 % des points)
  C11 aspect de près     : référence Aletsch vu d'avion. Gros plan du Grésivaudan au maximum
                          (24 000 ans) : contraste local de la glace ≥ 0,035 (écart-type de la
                          luminance moins son flou à 4 px) ; sous la ligne d'équilibre (tirée
                          des données), ≥ 25 % de glace nue bleutée (B − R ≥ 0,06, luminance < 0,85) et ≤ 20 %
                          de blanc pur ; au-dessus, le névé est plus clair (≥ + 0,08) ; gros
                          plan de la Combe de Savoie (20 000 ans) : moraines plus sombres que
                          la glace voisine (≥ 0,15)
  C10 compteur          : cadran commun de vitesse du temps (N28, commun/compteur.js) dans un coin, lisible sur
                          390 px, ne masquant ni relief ni texte ; angle de l'aiguille =
                          vitesse réelle du curseur en échelle log, à 1° près après
                          amortissement ; butée à l'arrêt ; flèche quand le temps remonte

Usage : python3 app/public/labo/glaciers/controles.py [--port 8810]
Code de sortie 0 si tout passe.
"""
import argparse
import functools
import gzip
import http.server
import json
import os
import socket
import sys
import threading
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.abspath(os.path.join(ICI, '..', '..'))
RACINE = os.path.abspath(os.path.join(PUBLIC, '..', '..'))
REF = os.path.join(RACINE, 'chantiers/glaciers/reference/reference.npz')
sys.path.insert(0, os.path.join(RACINE, 'chantiers/glaciers'))
DONNEES = os.path.join(ICI, 'donnees')

resultats = []


def verdict(code, ok, detail):
    resultats.append((code, bool(ok), detail))
    print(f"{'PASSE' if ok else 'ÉCHEC'}  {code}  {detail}", flush=True)


def port_libre(prefere):
    for p in [prefere] + list(range(8810, 8820)):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    raise SystemExit('aucun port libre entre 8810 et 8819')


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serveur(port):
    h = functools.partial(Silencieux, directory=PUBLIC)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            s = np.zeros_like(m)
            ys = slice(max(dy, 0), m.shape[0] + min(dy, 0))
            yd = slice(max(-dy, 0), m.shape[0] + min(-dy, 0))
            xs = slice(max(dx, 0), m.shape[1] + min(dx, 0))
            xd = slice(max(-dx, 0), m.shape[1] + min(-dx, 0))
            s[yd, xd] = m[ys, xs]
            out |= s
    return out


def erode(m, r):
    return ~dilate(~m, r)


def charger_reference():
    if not os.path.exists(REF):
        return None
    z = np.load(REF)
    nt, ny, nx = [int(v) for v in z['forme']]
    masques = np.unpackbits(z['masques'], axis=1)[:, :ny * nx].reshape(nt, ny, nx).astype(bool)
    return {'nt': nt, 'ny': ny, 'nx': nx, 'masques': masques, 'ages': z['ages'],
            'aires': z['aires_km2'], 'ref_ages': list(z['ref_ages']), 'ref_u': z['ref_u'],
            'ref_v': z['ref_v'], 'ref_thk': z['ref_thk']}


def agrandir(m, f):
    return np.repeat(np.repeat(m, f, axis=0), f, axis=1)


def bilineaire(champ, x, y):
    """champ[ny][nx] aux centres de mailles ; x, y en mailles depuis le coin sud-ouest."""
    ny, nx = champ.shape
    fx = np.clip(x - 0.5, 0, nx - 1.0001)
    fy = np.clip(y - 0.5, 0, ny - 1.0001)
    i, j = np.floor(fx).astype(int), np.floor(fy).astype(int)
    a, b = fx - i, fy - j
    return ((1 - a) * (1 - b) * champ[j, i] + a * (1 - b) * champ[j, i + 1]
            + (1 - a) * b * champ[j + 1, i] + a * b * champ[j + 1, i + 1])


def controle_donnees(ref):
    chemin = os.path.join(DONNEES, 'glace.bin.gz')
    if ref is None or not os.path.exists(chemin):
        verdict('C1', False, 'données absentes (glace.bin.gz ou reference.npz)')
        return
    meta = json.load(open(os.path.join(DONNEES, 'meta.json')))
    nt, ny, nx = meta['nt'], meta['ny'], meta['nx']
    brut = gzip.open(chemin).read()
    n = nt * ny * nx
    thk = np.frombuffer(brut[:2 * n], '<u2').reshape(nt, ny, nx)
    u = np.frombuffer(brut[2 * n:4 * n], '<i2').reshape(nt, ny, nx) * meta['echelle_vitesse']
    v = np.frombuffer(brut[4 * n:6 * n], '<i2').reshape(nt, ny, nx) * meta['echelle_vitesse']
    ages = np.array(meta['ages'])
    ok_masques = np.array_equal(thk >= 1, ref['masques'])
    pas = np.diff(ages)
    ecart_v = 0.0
    for k, a in enumerate(ref['ref_ages']):
        t = int(np.where(ages == a)[0][0])
        ecart_v = max(ecart_v, float(np.abs(u[t] - ref['ref_u'][k]).max()),
                      float(np.abs(v[t] - ref['ref_v'][k]).max()))
    couvre = ages.max() >= 115000 and ages.min() == 0 and np.all(-pas <= 1000)
    verdict('C1', ok_masques and ecart_v <= 0.051 and couvre,
            f'{nt} pas de {ages.max()} à {ages.min()} ans, masques identiques={ok_masques}, '
            f'écart vitesses max {ecart_v:.3f} m/a, fenêtre {nx}×{ny} mailles de {meta["dx"]:.0f} m')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8810)
    ap.add_argument('--capture', default='')
    args = ap.parse_args()
    ref = charger_reference()
    controle_donnees(ref)

    from playwright.sync_api import sync_playwright
    port = port_libre(args.port)
    srv = serveur(port)
    url = f'http://127.0.0.1:{port}/labo/glaciers/index.html'
    erreurs = []
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
                                args=['--no-sandbox', '--use-angle=swiftshader',
                                      '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = nav.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1,
                              has_touch=True, is_mobile=True)
        page = ctx.new_page()
        page.on('pageerror', lambda e: erreurs.append('pageerror: ' + str(e)))
        page.on('console', lambda m: erreurs.append('console: ' + m.text) if m.type == 'error' else None)
        page.goto(url + '?controle=1', wait_until='load', timeout=60000)
        try:
            page.wait_for_function('window.glaciers && window.glaciers.pret === true', timeout=90000)
            pret = True
        except Exception as e:  # noqa
            pret = False
            erreurs.append('page jamais prête : ' + str(e).splitlines()[0])

        if pret and ref is not None:
            meta = page.evaluate('window.glaciers.meta')
            F = 4                                  # pixels par maille dans la vue de plan
            N = ref['nx'] * F

            def plan(age):
                b = page.evaluate(f'Array.from(window.glaciers.masquePlan({age}, {N}))')
                return np.array(b, bool).reshape(N, N)

            # C2
            ages = list(ref['ages'])
            instants = [a for a in [110000, 60000, 25000, 20000, 15000, 5000] if a in ages]
            pires = []
            for a in instants:
                m_ref = agrandir(ref['masques'][ages.index(a)], F)
                m = plan(a)
                dedans = (m & dilate(m_ref, F)).sum() / max(1, m.sum())
                couvert = (m_ref & dilate(m, F)).sum() / max(1, m_ref.sum())
                pires.append((a, round(100 * dedans, 2), round(100 * couvert, 2), int(m_ref.sum() / F / F)))
            ok = all(d >= 99.5 and c >= 99.5 for _, d, c, _ in pires) and len(pires) == 6
            verdict('C2', ok, 'âge, % dessiné dans les données, % des données dessiné, mailles : '
                    + '; '.join(f'{a}: {d}/{c} ({n})' for a, d, c, n in pires))

            # C3
            det = []
            ok3 = True
            for a in [60500, 24500, 15500]:
                i0 = ages.index(a + 500)
                i1 = ages.index(a - 500)
                ua = agrandir(ref['masques'][i0] | ref['masques'][i1], F)
                ia = agrandir(ref['masques'][i0] & ref['masques'][i1], F)
                m = plan(a)
                hors = (m & ~dilate(ua, F)).sum() / max(1, m.sum())
                perdu = (erode(ia, F) & ~m).sum() / max(1, erode(ia, F).sum())
                det.append(f'{a}: inventé {100 * hors:.2f} %, perdu {100 * perdu:.2f} %')
                ok3 &= hors <= 0.005 and perdu <= 0.005
            verdict('C3', ok3, '; '.join(det))

            # C4
            aires = np.array(page.evaluate(
                f'window.glaciers.airesPlan({json.dumps([int(a) for a in ages])}, {ref["nx"] * 2})'))
            aires_ref = ref['aires']
            grand = aires_ref > 500
            err = np.abs(aires - aires_ref)[grand] / aires_ref[grand]
            kmax = int(np.argmax(aires))
            age_max = ages[kmax]
            g = meta['gresivaudan']
            mmax = plan(age_max)
            gi, gj = int(g['x'] / meta['dx'] * F), int(g['y'] / meta['dy'] * F)
            ok4 = 20000 <= age_max <= 30000 and bool(mmax[gj, gi]) and err.max() <= 0.03
            verdict('C4', ok4, f'maximum dessiné à {age_max} ans ({aires[kmax]:.0f} km² ; données '
                    f'{aires_ref.max():.0f} km² à {ages[int(np.argmax(aires_ref))]} ans), Grésivaudan '
                    f'englacé={bool(mmax[gj, gi])}, écart d’aire max {100 * err.max():.2f} %')

            # C5
            ok5 = True
            det = []
            for a in [25000, 60000]:
                if a not in ref['ref_ages']:
                    ok5 = False
                    det.append(f'{a}: pas de vitesses de référence')
                    continue
                k = ref['ref_ages'].index(a)
                page.evaluate(f'window.glaciers.regler({{age: {a}, lecture: false}})')
                page.wait_for_timeout(3000)
                seg = np.array(page.evaluate('window.glaciers.traineesDessinees()'), 'f8').reshape(-1, 4)
                if len(seg) == 0:
                    ok5 = False
                    det.append(f'{a}: aucune traînée')
                    continue
                d = meta['dx']
                mx, my = (seg[:, 0] + seg[:, 2]) / 2 / d, (seg[:, 1] + seg[:, 3]) / 2 / d
                ur = bilineaire(ref['ref_u'][k], mx, my)
                vr = bilineaire(ref['ref_v'][k], mx, my)
                rapide = np.hypot(ur, vr) >= 1.0
                ds = seg[:, 2:] - seg[:, :2]
                bouge = np.hypot(ds[:, 0], ds[:, 1]) > 1e-6
                sel = rapide & bouge
                ang = np.degrees(np.abs(np.angle(np.exp(1j * (np.arctan2(ds[sel, 1], ds[sel, 0])
                                                              - np.arctan2(vr[sel], ur[sel]))))))
                # aucune traînée hors de la glace (ex. traînées périmées après un saut dans le temps)
                mref = dilate(ref['masques'][list(ref['ages']).index(a)], 1)
                ci = np.clip(mx.astype(int), 0, ref['nx'] - 1)
                cj = np.clip(my.astype(int), 0, ref['ny'] - 1)
                hors = float((~mref[cj, ci]).mean())
                ok5 &= hors < 0.01
                det.append(f'{a}: hors glace {100 * hors:.2f} %')
                ntr = int(page.evaluate('window.glaciers.nombreTrainees()'))
                med = float(np.median(ang)) if len(ang) else 180.0
                p95 = float(np.percentile(ang, 95)) if len(ang) else 180.0
                ok5 &= med < 15 and p95 < 45 and ntr >= 400
                det.append(f'{a}: {ntr} traînées, {sel.sum()} segments, écart médian {med:.1f}°, 95e c. {p95:.1f}°')
            verdict('C5', ok5, '; '.join(det))

            # C9 moraines médianes
            import moraines as MOR
            ok9, det = True, []
            total_ref = 0.0
            for a in [60000, 15000, 110000, 20000]:
                k = ref['ref_ages'].index(a)
                t = ref['ref_thk'][k].astype('f8')
                u, v = ref['ref_u'][k].astype('f8'), ref['ref_v'][k].astype('f8')
                r_fin = MOR.moraines(t, u, v)                        # grille de 500 m
                fr = F // MOR.R
                r_px = agrandir(r_fin, fr)
                d_px = np.array(page.evaluate(f'Array.from(window.glaciers.masquePlan({a}, {N}, "moraine"))'),
                                bool).reshape(N, N)
                km_ref = r_fin.sum() / MOR.R
                total_ref += km_ref
                if r_fin.sum() == 0 and d_px.sum() == 0:
                    det.append(f'{a}: aucune (données) / aucune (dessin)')
                    continue
                prec = (d_px & dilate(r_px, F)).sum() / max(1, d_px.sum())
                rapp = (r_px & dilate(d_px, F)).sum() / max(1, r_px.sum())
                # deux flux : de part et d'autre de la moraine dessinée, on remonte le courant
                masque = (t >= 1).astype('f8')
                jj, ii = np.nonzero(d_px)
                rng = np.random.default_rng(1)
                pick = rng.choice(len(jj), size=min(300, len(jj)), replace=False) if len(jj) else []
                x = (ii[pick] + 0.5) / F
                y = (jj[pick] + 0.5) / F
                uu, vv = MOR.bil(u, x, y), MOR.bil(v, x, y)
                sp = np.maximum(np.hypot(uu, vv), 1e-9)
                nxv, nyv = -vv / sp, uu / sp
                gx, gy, dx_, dy_ = x + 0.75 * nxv, y + 0.75 * nyv, x - 0.75 * nxv, y - 0.75 * nyv
                surg = (MOR.bil(masque, gx, gy) >= 0.5) & (MOR.bil(masque, dx_, dy_) >= 0.5)
                separe = np.zeros(len(x), bool)
                for _ in range(320):
                    for P in ('g', 'd'):
                        X, Y = (gx, gy) if P == 'g' else (dx_, dy_)
                        a_u, a_v = MOR.bil(u, X, Y), MOR.bil(v, X, Y)
                        s_ = np.maximum(np.hypot(a_u, a_v), 1e-9)
                        X -= a_u / s_ * 0.25
                        Y -= a_v / s_ * 0.25
                    for q in np.linspace(0.05, 0.95, 16):
                        mx, my = gx + q * (dx_ - gx), gy + q * (dy_ - gy)
                        separe |= MOR.bil(masque, mx, my) < 0.5
                frac = separe[surg].mean() if surg.any() else 0.0
                ok9 &= prec >= 0.85 and rapp >= 0.85 and frac >= 0.70
                det.append(f'{a}: {km_ref:.0f} km (données), dessinées dans les données {100 * prec:.1f} %, '
                           f'données dessinées {100 * rapp:.1f} %, deux flux {100 * frac:.0f} % ({surg.sum()} pts)')
            ok9 &= total_ref >= 100
            verdict('C9', ok9, '; '.join(det))

            # C11 aspect de près (Aletsch)
            import base64
            from scipy.ndimage import gaussian_filter, binary_erosion

            def vue(mode):
                r = page.evaluate(f'window.glaciers.vueControle({mode}, false)')
                im = np.frombuffer(base64.b64decode(r['b64']), np.uint8).reshape(r['h'], r['w'], 4)[::-1]
                return im.astype('f8') / 255.0

            def gros_plan(age, cam):
                page.goto(url + f'?controle=1&cam={cam}', wait_until='load')
                page.wait_for_function('window.glaciers && window.glaciers.pret === true', timeout=90000)
                page.evaluate(f'window.glaciers.regler({{age: {age}, lecture: false}})')
                page.wait_for_timeout(600)
                return vue(0), vue(1)[..., 0] > 0.5, vue(2)[..., 0] > 0.5, (lambda a: a[..., 0] * 255 * 256 + a[..., 1] * 255)(vue(3))

            det, ok11 = [], True
            col, glace, mor, alt = gros_plan(24000, '82,86,24,15,38')
            ela = meta['ligne_equilibre_m'][list(ref['ages']).index(24000)] if 'ligne_equilibre_m' in meta else 1e9
            Lum = col[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
            g = binary_erosion(glace, iterations=3)
            hp = Lum - gaussian_filter(Lum, 4)
            contraste = float(hp[g].std()) if g.any() else 0.0
            bas, haut = g & (alt < ela - 100), g & (alt > ela + 100)
            bleu = float((((col[..., 2] - col[..., 0]) >= 0.06) & (Lum < 0.85))[bas].mean()) if bas.any() else 0.0
            sat = col[..., :3].max(-1) - col[..., :3].min(-1)
            blanc = float(((Lum >= 0.88) & (sat < 0.06))[bas].mean()) if bas.any() else 1.0
            ok11 &= contraste >= 0.035 and bleu >= 0.25 and blanc <= 0.20
            det.append(f'Grésivaudan 24 000 ans : contraste local {contraste:.3f}, glace nue bleutée {100 * bleu:.0f} %, '
                       f'blanc pur {100 * blanc:.0f} % sous la ligne d’équilibre ({ela:.0f} m)')
            col, glace, mor, alt = gros_plan(20000, '108,108,38,10,35')
            ela = meta['ligne_equilibre_m'][list(ref['ages']).index(20000)] if 'ligne_equilibre_m' in meta else 1e9
            Lum = col[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
            g = binary_erosion(glace, iterations=3)
            bas, haut = g & (alt < ela - 100), g & (alt > ela + 100)
            if haut.sum() > 500 and bas.sum() > 500:
                ecart = float(Lum[haut].mean() - Lum[bas & ~mor].mean())
                ok11 &= ecart >= 0.08
                det.append(f'névé plus clair que la glace nue de {ecart:+.3f}')
            else:
                ok11 = False
                det.append('pas assez de glace des deux côtés de la ligne d’équilibre')
            voisin = g & ~mor & (gaussian_filter(mor.astype('f8'), 3) > 0.02)
            m_in = g & mor
            if m_in.sum() > 50 and voisin.sum() > 50:
                dm = float(Lum[voisin].mean() - Lum[m_in].mean())
                ok11 &= dm >= 0.15
                det.append(f'moraines plus sombres de {dm:.3f} ({m_in.sum()} px)')
            else:
                ok11 = False
                det.append('moraines non visibles dans le gros plan')
            verdict('C11', ok11, '; '.join(det))

        # C7 fluidité
        if pret:
            page.goto(url, wait_until='load')
            page.wait_for_function('window.glaciers && window.glaciers.pret === true', timeout=90000)
            page.evaluate('window.glaciers.regler({age: 40000, lecture: true})')
            page.wait_for_timeout(9000)          # la page adapte sa qualité (netteté, maillage, filets)
            page.evaluate('window.glaciers.mesureImages(true)')
            page.wait_for_timeout(6000)
            st = page.evaluate('window.glaciers.mesureImages(false)')
            qual = page.evaluate('window.glaciers.qualite()')
            js = float(np.median(st['js'])) if st['js'] else 1e9
            iv = float(np.median(st['intervalles'])) if st['intervalles'] else 1e9
            verdict('C7', js < 8 and iv < 50,
                    f'{len(st["js"])} images, JS médian {js:.2f} ms, intervalle médian {iv:.1f} ms '
                    f'(rendu logiciel SwiftShader, 2 cœurs partagés ; qualité atteinte {qual})')
            # C8
            page.evaluate('window.glaciers.regler({age: 25000, lecture: false})')
            page.wait_for_timeout(1500)
            txt = page.inner_text('body')
            img = page.screenshot()
            if args.capture:
                open(args.capture, 'wb').write(img)
            from PIL import Image
            import io
            im = np.asarray(Image.open(io.BytesIO(img)).convert('L'), 'f4')
            lieux = [n for n in ['Grenoble', 'Chartreuse', 'Vercors', 'Belledonne'] if n in txt]
            ok8 = ('25 000' in txt) and len(lieux) == 4 and im.std() > 20
            verdict('C8', ok8, f'âge lisible={"25 000" in txt}, lieux {lieux}, contraste {im.std():.1f}')

            # C10 compteur de vitesse du temps
            det, ok10 = [], True
            existe = page.evaluate('!!(window.glaciers.compteur && document.getElementById("compteur"))')
            if not existe:
                ok10 = False
                det.append('cadran absent')
            else:
                # échelle de la spécification N28 ; butée lue dans le composant commun
                import re as _re
                src = open(os.path.join(PUBLIC, 'commun/compteur.js')).read()
                butee = float(_re.search(r'ANGLE_BUTEE = (-?[\d.]+)', src).group(1))

                def angle_attendu(vit):
                    if vit <= 0:
                        return butee
                    return -135 + min(10, max(0, np.log10(vit))) / 10 * 270
                for vit, sens in [(1500, 1), (400, 1), (5000, 1), (5000, -1), (0, 0)]:
                    page.evaluate(f'window.glaciers.regler({{age: {90000 if sens >= 0 else 30000}, '
                                  f'lecture: {"true" if vit else "false"}, vitesse: {vit or 1500}, sens: {sens or 1}}})')
                    page.wait_for_timeout(1500)
                    t0, a0 = page.evaluate('[performance.now(), window.glaciers.age()]')
                    page.wait_for_timeout(1500)
                    t1, a1, ang, fl = page.evaluate('[performance.now(), window.glaciers.age(), '
                                                   'parseFloat(/rotate\\(([-\\d.e]+)/.exec(document.querySelector("#compteur .aiguille").getAttribute("transform"))[1]), '
                                                   '(+getComputedStyle(document.querySelector("#compteur .fleche-sens")).opacity > 0.5) ? "visible" : "hidden"]')
                    reelle = abs(a1 - a0) / ((t1 - t0) / 1000)
                    att = angle_attendu(reelle)
                    ecart = abs(ang - att)
                    fl_ok = (fl == 'visible') == (sens < 0 and vit > 0)
                    ok10 &= ecart <= 1.0 and fl_ok
                    det.append(f'{reelle:.0f} a/s → {ang:.1f}° (attendu {att:.1f}°){" flèche" if fl == "visible" else ""}')
                page.evaluate('window.glaciers.regler({age: 25000, lecture: false})')
                page.wait_for_timeout(800)
                boite = page.evaluate('''(() => { const r = document.querySelector("#compteur .compteur-temps").getBoundingClientRect();
                    const autres = [...document.querySelectorAll(".lieu, #titre, #bas, #info-btn")]
                      .filter(e => getComputedStyle(e).visibility !== "hidden")
                      .map(e => e.getBoundingClientRect()).filter(b => b.width > 0 &&
                        b.left < r.right && b.right > r.left && b.top < r.bottom && b.bottom > r.top).length;
                    return {l: r.left, t: r.top, w: r.width, h: r.height, autres,
                            sous: window.glaciers.couvertureSous(r.left, r.top, r.width, r.height)}; })()''')
                coin = min(boite['l'], 390 - boite['l'] - boite['w']) <= 16
                ok_b = boite['w'] >= 64 and boite['l'] >= 0 and boite['l'] + boite['w'] <= 390 and coin \
                    and boite['autres'] == 0 and boite['sous'] <= 0.05
                ok10 &= ok_b
                det.append(f"cadran {boite['w']:.0f} px, coin={coin}, recouvre {boite['autres']} texte(s), "
                           f"relief sous le cadran {100 * boite['sous']:.1f} %")
            verdict('C10', ok10, '; '.join(det))
        else:
            verdict('C7', False, 'page non prête')
            verdict('C8', False, 'page non prête')
            verdict('C10', False, 'page non prête')
        nav.close()
    srv.shutdown()
    if ref is None:
        for c in ['C2', 'C3', 'C4', 'C5', 'C9', 'C11']:
            verdict(c, False, 'références absentes (le workflow n’a pas encore déposé les données)')
    elif not any(r[0] == 'C2' for r in resultats):
        for c in ['C2', 'C3', 'C4', 'C5', 'C9', 'C11']:
            verdict(c, False, 'page non prête')
    verdict('C6', not erreurs, f'{len(erreurs)} erreur(s) ' + ' | '.join(erreurs[:5]))
    nb = sum(ok for _, ok, _ in resultats)
    print(f'\n{nb}/{len(resultats)} contrôles passés')
    sys.exit(0 if nb == len(resultats) else 1)


if __name__ == '__main__':
    main()
