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
                          < 45°), au moins 400 traînées sur la glace
  C6 erreurs            : aucune erreur JavaScript ni de console
  C7 fluidité           : téléphone 390 × 844 : temps JavaScript médian par image
                          < 8 ms ; intervalle médian entre images < 50 ms même en
                          rendu logiciel
  C8 lecture            : la page montre l'âge, les noms des lieux, et une image non vide

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
            'ref_v': z['ref_v']}


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
                ntr = int(page.evaluate('window.glaciers.nombreTrainees()'))
                med = float(np.median(ang)) if len(ang) else 180.0
                p95 = float(np.percentile(ang, 95)) if len(ang) else 180.0
                ok5 &= med < 15 and p95 < 45 and ntr >= 400
                det.append(f'{a}: {ntr} traînées, {sel.sum()} segments, écart médian {med:.1f}°, 95e c. {p95:.1f}°')
            verdict('C5', ok5, '; '.join(det))

        # C7 fluidité
        if pret:
            page.goto(url, wait_until='load')
            page.wait_for_function('window.glaciers && window.glaciers.pret === true', timeout=90000)
            page.evaluate('window.glaciers.regler({age: 40000, lecture: true})')
            page.wait_for_timeout(1500)
            page.evaluate('window.glaciers.mesureImages(true)')
            page.wait_for_timeout(5000)
            st = page.evaluate('window.glaciers.mesureImages(false)')
            js = float(np.median(st['js'])) if st['js'] else 1e9
            iv = float(np.median(st['intervalles'])) if st['intervalles'] else 1e9
            verdict('C7', js < 8 and iv < 50,
                    f'{len(st["js"])} images, JS médian {js:.2f} ms, intervalle médian {iv:.1f} ms '
                    f'(rendu logiciel SwiftShader, 2 cœurs partagés)')
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
        else:
            verdict('C7', False, 'page non prête')
            verdict('C8', False, 'page non prête')
        nav.close()
    srv.shutdown()
    if ref is None:
        for c in ['C2', 'C3', 'C4', 'C5']:
            verdict(c, False, 'références absentes (le workflow n’a pas encore déposé les données)')
    elif not any(r[0] == 'C2' for r in resultats):
        for c in ['C2', 'C3', 'C4', 'C5']:
            verdict(c, False, 'page non prête')
    verdict('C6', not erreurs, f'{len(erreurs)} erreur(s) ' + ' | '.join(erreurs[:5]))
    nb = sum(ok for _, ok, _ in resultats)
    print(f'\n{nb}/{len(resultats)} contrôles passés')
    sys.exit(0 if nb == len(resultats) else 1)


if __name__ == '__main__':
    main()
