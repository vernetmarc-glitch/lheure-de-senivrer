#!/usr/bin/env python3
"""Contrôles de la page labo « humanité » (chantier S6 ; exigences N13, N14, N28, N29).

Mesure la page SERVIE (serveur local, Chrome sans tête, WebGL2 logiciel), pas un aperçu.
Les références viennent des sources, jamais de la page :
  - sites datés : prepa/sites_cles.csv (publications ; ROAD et Timmermann et al. 2022) ;
  - effectifs : prepa/effectifs_litterature.csv (avant l'Holocène, estimations publiées)
    et prepa/intermediaires/hyde_totaux.json (HYDE 3.2.1, sommes des grilles à 5′ ; 2023 : ONU) ;
  - Black Marble 2016 (NASA) : prepa/intermediaires/blackmarble_0p1.npz ;
  - relief et bathymétrie : prepa/intermediaires/relief_0p1.npz ; niveau marin : Spratt &
    Lisiecki 2016 (prepa/intermediaires/spratt2016.txt).

La page dessine, à la demande du contrôle, les mêmes points et les mêmes territoires que
le globe, mais en projection équirectangulaire (720 × 360, une maille de 0,5°), dans une
cible flottante relue par readPixels : c'est ce qui est dessiné qui est mesuré.

  C1 données     : paquet publié présent ; chaque site daté et chaque effectif sont repris
                   tels quels ; HYDE 3.3 couvre 10 000 av. J.-C. → 2023
  C2 sites       : chaque site daté est atteint par le territoire de sa lignée au plus tard
                   à sa date (à 10 % de son âge près : présent à 0,9, 0,95 ou 1 fois l'âge) ; chaque dernier refuge est encore
                   habité juste avant sa date (+10 %) et la lignée a disparu partout après
                   (−10 %)
  C3 remplacement: après 30 000 ans, plus aucune autre lignée que sapiens (territoires et
                   points)
  C4 densité     : à 30 instants de 7 Ma à aujourd'hui, nombre de points dessinés =
                   population / K (K fixe, celui de la légende), à 1 % + 1 point près,
                   lignée par lignée
  C5 Black Marble: aujourd'hui, lumière des points (1°, log) corrélée à Black Marble 2016
                   (log) : r ≥ 0,8 sur les terres
  C6 compteur    : aiguille = vitesse réelle du temps (log, 1 an → 10 Ga par seconde) à 1°
                   près après amortissement ; butée à l'arrêt ; flèche quand le temps
                   remonte ; lecture en clair ; cadran ≥ 80 px, ne masque ni le globe ni
                   les textes
  C7 erreurs     : aucune erreur JavaScript ni de console
  C8 lecture     : date, légende des 6 lignées, valeur de K, 3 fenêtres de temps,
                   lecture/pause ; globe non vide
  C9 générations : aux vitesses lentes, les points se renouvellent au rythme d'une
                   génération (≈ 25 ans) : ≥ 70 % inchangés après 5 ans, ≤ 30 % après 60 ans
  C10 ponts      : niveau marin : Béringie et plateau de la Sonde émergés il y a 20 000 ans,
                   submergés aujourd'hui (terres dessinées par la page)
  C11 fluidité   : 390 × 844 : temps JavaScript médian par image < 8 ms en lecture ;
                   poids avant la première image ≤ 10 Mo

Usage : python3 app/public/labo/humanite/controles.py [--port 8860] [--seul C4]
Code de sortie 0 si tout passe.
"""
import argparse
import csv
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
PUBLIC = os.path.abspath(os.path.join(ICI, '..', '..'))
PREPA = os.path.join(ICI, 'prepa')
INTER = os.path.join(PREPA, 'intermediaires')
URL_PAGE = 'labo/humanite/index.html'

LIGNEES = ['hominines', 'erectus', 'neandertal', 'denisova', 'insulaires', 'sapiens']
CARTES = ['hominines', 'erectus', 'neandertal', 'denisova', 'insulaires', 'sapiens', 'sapiens1']
LIGNEE_DE_CARTE = {c: ('sapiens' if c == 'sapiens1' else c) for c in CARTES}

resultats = []


def verdict(code, ok, detail):
    resultats.append((code, bool(ok), detail))
    print(f"{'PASSE' if ok else 'ÉCHEC'}  {code}  {detail}", flush=True)


def port_libre(prefere):
    for p in [prefere] + list(range(8860, 8870)):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    raise SystemExit('aucun port libre entre 8860 et 8869')


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def serveur(port):
    h = functools.partial(Silencieux, directory=PUBLIC)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ------------------------------------------------------------------ références (sources)

def lire_csv(chemin):
    with open(chemin, encoding='utf-8') as f:
        lignes = [l for l in f if l.strip() and not l.startswith('#')]
    return list(csv.DictReader(lignes, delimiter=';'))


def sites_reference():
    return [dict(r, lat=float(r['lat']), lon=float(r['lon']), age=float(r['age_ans']))
            for r in lire_csv(os.path.join(PREPA, 'sites_cles.csv'))]


def effectifs_reference():
    """{lignée: [(âge, effectif)]} : littérature avant l'Holocène, HYDE 3.3 ensuite (sapiens)."""
    p = os.path.join(PREPA, 'effectifs_litterature.csv')
    h = os.path.join(INTER, 'hyde_totaux_annees.json')
    if not (os.path.exists(p) and os.path.exists(h)):
        return None
    eff = {}
    for r in lire_csv(p):
        eff.setdefault(r['lignee'], []).append((float(r['age_ans']), float(r['effectif'])))
    # âges avant 2023 ; 2023 : Nations unies (WPP 2024), la dernière tranche HYDE 3.2.1 étant 2017
    hyde = {str(2023 - int(a)): float(v) for a, v in json.load(open(h)).items()}
    hyde['0'] = 8.09e9
    a_hyde = max(float(a) for a in hyde)
    eff['sapiens'] = [(a, e) for a, e in eff.get('sapiens', []) if a > a_hyde] + \
        [(float(a), float(v)) for a, v in hyde.items()]
    for k in eff:
        eff[k].sort(key=lambda x: -x[0])
    return eff


def interp_effectif(noeuds, age):
    """Interpolation log-linéaire en effectif, linéaire en âge ; 0 hors des noeuds."""
    if not noeuds or age > noeuds[0][0] or age < noeuds[-1][0]:
        return 0.0
    for (a0, e0), (a1, e1) in zip(noeuds, noeuds[1:]):
        if a0 >= age >= a1:
            if a0 == a1:
                return e1
            w = (a0 - age) / (a0 - a1)
            if e0 <= 0 or e1 <= 0:
                return e0 * (1 - w) + e1 * w
            return math.exp(math.log(e0) * (1 - w) + math.log(e1) * w)
    return noeuds[-1][1]


def niveau_marin():
    p = os.path.join(INTER, 'spratt2016.txt')
    if not os.path.exists(p):
        return None
    ages, sl = [], []
    for l in open(p, encoding='latin-1'):
        if l.startswith('#') or not l.strip():
            continue
        parts = l.split()
        try:
            a, s = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            continue
        ages.append(a * 1000.0)
        sl.append(s)
    return np.array(ages), np.array(sl)


# ------------------------------------------------------------------ page

def ouvrir(pw, port, largeur=390, hauteur=844):
    nav = pw.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
                             args=['--no-sandbox', '--use-angle=swiftshader',
                                   '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
                                   '--enable-webgl'])
    ctx = nav.new_context(viewport={'width': largeur, 'height': hauteur}, device_scale_factor=2,
                          is_mobile=True, has_touch=True)
    page = ctx.new_page()
    erreurs = []
    page.on('pageerror', lambda e: erreurs.append(f'pageerror: {e}'))
    page.on('console', lambda m: erreurs.append(f'console.{m.type}: {m.text}')
            if m.type == 'error' else None)
    octets = {'total': 0, 'avant': None}

    def reponse(r):
        try:
            n = r.headers.get('content-length')
            octets['total'] += int(n) if n else len(r.body())
        except Exception:
            pass
    page.on('response', reponse)
    page.goto(f'http://127.0.0.1:{port}/{URL_PAGE}?controle=1', wait_until='load')
    try:
        page.wait_for_function('window.__hum && window.__hum.pret === true', timeout=180000)
        octets['avant'] = octets['total']
    except Exception as e:
        erreurs.append(f'page non prête : {str(e)[:200]}')
    return nav, page, erreurs, octets


def plan(page, age, mode, carte=None):
    import base64
    r = page.evaluate('([a, m, c]) => window.__hum.plan(a, m, c)', [age, mode, carte])
    a = np.frombuffer(base64.b64decode(r['b64']), dtype=np.float32).astype(np.float64)
    return a.reshape(r['h'], r['w'])


def pixel(lat, lon, w=720, h=360):
    x = int(min(w - 1, max(0, math.floor((lon + 180.0) / 360.0 * w))))
    y = int(min(h - 1, max(0, math.floor((90.0 - lat) / 180.0 * h))))
    return y, x


def present(masque_bits, bit, lat, lon, r=1):
    y, x = pixel(lat, lon, masque_bits.shape[1], masque_bits.shape[0])
    b = masque_bits[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].astype(np.int64)
    return bool(np.any((b >> bit) & 1))


# ------------------------------------------------------------------ contrôles

def c1_donnees(page):
    ok = True
    det = []
    manquants = [f for f in ['donnees/meta.json', 'donnees/sites.json', 'donnees/population.json']
                 if not os.path.exists(os.path.join(ICI, f))]
    if manquants:
        verdict('C1', False, f'paquet absent : {manquants}')
        return
    ref = sites_reference()
    pub = json.load(open(os.path.join(ICI, 'donnees/sites.json')))
    cle = lambda s: (s['lignee'], s['nom'], round(float(s['lat']), 3), round(float(s['lon']), 3),
                     round(float(s['age'])))
    a, b = sorted(map(cle, ref)), sorted(map(cle, pub))
    if a != b:
        ok = False
        det.append(f'sites publiés ≠ sources ({len(b)} / {len(a)})')
    eff = effectifs_reference()
    popu = json.load(open(os.path.join(ICI, 'donnees/population.json')))
    if eff is None:
        ok = False
        det.append('effectifs de référence absents (HYDE ou littérature)')
    else:
        for lig, noeuds in eff.items():
            pubn = sorted(((float(x), float(y)) for x, y in popu['noeuds'].get(lig, [])), key=lambda t: -t[0])
            if len(pubn) != len(noeuds) or any(abs(x0 - x1) > 0.5 or abs(y0 - y1) > 1e-6 * max(1, y0)
                                               for (x0, y0), (x1, y1) in zip(noeuds, pubn)):
                ok = False
                det.append(f'effectifs {lig} publiés ≠ sources')
        hy = {str(2023 - int(a)): v for a, v in json.load(open(os.path.join(INTER, 'hyde_totaux_annees.json'))).items()}
        ages = sorted(float(x) for x in hy)
        if not (ages[0] <= 10 and ages[-1] >= 12000):
            ok = False
            det.append(f'HYDE couvre {ages[-1]:.0f} → {ages[0]:.0f} ans seulement')
        det.append(f'{len(ages)} tranches HYDE, {hy[min(hy, key=float)] / 1e9:.2f} milliards aujourd\'hui')
    det.append(f'{len(ref)} sites')
    verdict('C1', ok, ' ; '.join(det))


def c2_sites(page):
    ref = sites_reference()
    echecs, n = [], 0
    caches = {}

    def bits(age):
        k = round(age, 3)
        if k not in caches:
            caches[k] = plan(page, age, 'territoire')
        return caches[k]
    for s in ref:
        bit = CARTES.index(s['lignee'])
        if s['role'] in ('origine', 'site'):
            n += 1
            if not any(present(bits(s['age'] * f), bit, s['lat'], s['lon']) for f in (0.9, 0.95, 1.0)):
                echecs.append(f"{s['nom']} ({s['lignee']}, {s['age']:.0f} ans)")
        elif s['role'] == 'refuge':
            n += 1
            m_avant = bits(s['age'] * 1.1)
            m_apres = bits(s['age'] * 0.9)
            if not present(m_avant, bit, s['lat'], s['lon'], r=4):
                echecs.append(f"refuge {s['nom']} vide avant {s['age']:.0f} ans")
            if np.any((m_apres.astype(np.int64) >> bit) & 1):
                echecs.append(f"{s['lignee']} encore présent après {s['age']:.0f} ans")
    verdict('C2', not echecs and n > 0,
            f'{n - len(echecs)}/{n} sites et refuges conformes' + (' ; ' + ' ; '.join(echecs[:8]) if echecs else ''))


def c3_remplacement(page):
    autres = 0
    for c in CARTES:
        if c not in ('sapiens', 'sapiens1'):
            autres |= 1 << CARTES.index(c)
    fautes = []
    for age in [30000, 25000, 20000, 12000, 1000, 0]:
        m = plan(page, age, 'territoire').astype(np.int64)
        n_terr = int(np.count_nonzero(m & autres))
        n_pts = 0
        for lig in LIGNEES[:-1]:
            n_pts += int(round(plan(page, age, 'comptage', lig).sum()))
        sap = int(np.count_nonzero(m & (1 << CARTES.index('sapiens'))))
        if n_terr or n_pts or sap == 0:
            fautes.append(f'{age} ans : {n_terr} mailles et {n_pts} points d\'autres lignées, {sap} mailles sapiens')
    verdict('C3', not fautes, 'seul sapiens après 30 000 ans' if not fautes else ' ; '.join(fautes))


def k_legende(page):
    t = page.evaluate("() => (document.querySelector('#legende-k') || {}).textContent || ''")
    m = re.search(r'([\d\s  ]+)\s*humains', t)
    return (float(re.sub(r'\D', '', m.group(1))) if m else None), t


INSTANTS = [7.0e6, 5.0e6, 3.0e6, 2.0e6, 1.5e6, 1.0e6, 7.0e5, 4.0e5, 3.0e5, 2.0e5, 1.2e5, 7.0e4,
            5.0e4, 4.0e4, 3.0e4, 2.0e4, 1.3e4, 1.25e4, 1.2e4, 9.0e3, 5.0e3, 2023, 1000, 500, 300,
            200, 100, 50, 20, 0]


def c4_densite(page):
    K, txt = k_legende(page)
    eff = effectifs_reference()
    if not K or eff is None:
        verdict('C4', False, f'K illisible dans la légende ({txt!r}) ou effectifs absents')
        return
    fautes, lignes = [], []
    for age in INSTANTS:
        tot_m, tot_a = 0, 0.0
        for lig in LIGNEES:
            att = interp_effectif(eff.get(lig, []), age) / K
            if lig == 'sapiens':
                att += interp_effectif(eff.get('sapiens1', []), age) / K
            mes = plan(page, age, 'comptage', lig).sum()
            tot_m += mes
            tot_a += att
            if abs(mes - att) > 1 + 0.01 * att:
                fautes.append(f'{age:.0f} ans {lig} : {mes:.0f} points pour {att:.1f} attendus')
        lignes.append(f'{age:.0f}:{tot_m:.0f}')
    verdict('C4', not fautes, (f'K = {K:.0f} humains par point ; ' + ' '.join(lignes[::5])) if not fautes
            else ' ; '.join(fautes[:8]) + f' (+{max(0, len(fautes) - 8)})')


def bloc(a, f):
    h, w = a.shape
    return a.reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def c5_black_marble(page):
    p = os.path.join(INTER, 'blackmarble_0p1.npz')
    r = os.path.join(INTER, 'relief_0p1.npz')
    if not (os.path.exists(p) and os.path.exists(r)):
        verdict('C5', False, 'Black Marble ou relief absents des intermédiaires')
        return
    bm = bloc(np.load(p)['v'].astype(np.float64), 10)  # 1°
    terre = bloc((np.load(r)['z'] > 0).astype(np.float64), 10) > 0.5
    lum = bloc(plan(page, 0, 'lumiere'), 2)  # 0,5° -> 1°
    sel = terre & ((bm > 0) | (lum > 0))
    x, y = np.log10(1.0 + lum[sel]), np.log10(1.0 + bm[sel])
    rr = float(np.corrcoef(x, y)[0, 1]) if sel.sum() > 10 and x.std() > 0 else 0.0
    # pour information : nombre de points par maille (sans la lumière par humain) contre Black Marble
    n = bloc(plan(page, 0, 'comptage', 'sapiens'), 2)
    rn = float(np.corrcoef(np.log10(1.0 + n[sel]), y)[0, 1])
    verdict('C5', rr >= 0.8, f'r(log) = {rr:.3f} sur {int(sel.sum())} mailles de 1° (seuil 0,8) ; '
            f'densité de points seule : r = {rn:.3f}')


def angle_attendu(v):
    # spécification N28, composant commun app/public/commun/compteur.js : 27° par décade,
    # −135° à 1 an par seconde, +135° à 10 Ga par seconde, butée à −146° à l'arrêt
    if v == 0:
        return -146.0
    a = abs(v)
    return -135.0 + 27.0 * min(10.0, max(0.0, math.log10(a)))


def c6_compteur(page):
    fautes = []
    det = []
    for v in [1, 37, 1e4, 3.2e6, 1e9, 1e10, 0, -5e3]:
        page.evaluate('v => window.__hum.vitesse(v)', v)
        page.wait_for_timeout(1500)
        e = page.evaluate('() => window.__hum.compteur()')
        for _ in range(30):       # après amortissement : l'aiguille ne bouge plus
            page.wait_for_timeout(300)
            e2 = page.evaluate('() => window.__hum.compteur()')
            if abs(e2['angle'] - e['angle']) < 0.05:
                break
            e = e2
        e = e2
        att = angle_attendu(v)
        if abs(e['angle'] - att) > 1.0:
            fautes.append(f'{v:g} an/s : aiguille {e["angle"]:.1f}° pour {att:.1f}°')
        if v < 0 and not e['retour']:
            fautes.append('pas de flèche quand le temps remonte')
        if v > 0 and e['retour']:
            fautes.append('flèche de retour en marche avant')
        det.append(f'{v:g}→{e["angle"]:.1f}°')
        if v == 1e4 and '10 000 ans par seconde' not in e['texte'].replace(' ', ' ').replace(' ', ' '):
            fautes.append(f'lecture « {e["texte"]} » pour 10 000 ans par seconde')
    # en lecture réelle : l'aiguille suit la vitesse mesurée du curseur
    page.evaluate('() => { window.__hum.regler(2.0e5); window.__hum.lecture(true); }')
    page.wait_for_timeout(3000)
    a0 = page.evaluate('() => window.__hum.etat()')
    page.wait_for_timeout(300)
    a1 = page.evaluate('() => window.__hum.etat()')
    e = page.evaluate('() => window.__hum.compteur()')
    page.evaluate('() => window.__hum.lecture(false)')
    dt = (a1['horloge'] - a0['horloge']) / 1000.0
    v_mes = (a0['age'] - a1['age']) / dt if dt > 0 else 0
    if v_mes <= 0 or abs(e['angle'] - angle_attendu(v_mes)) > 1.5:
        fautes.append(f'lecture : vitesse mesurée {v_mes:.0f} an/s, aiguille {e["angle"]:.1f}° '
                      f'pour {angle_attendu(v_mes) if v_mes > 0 else float("nan"):.1f}°')
    # lisibilité et place
    g = page.evaluate('() => window.__hum.geometrie()')
    c = g['compteur']
    if min(c['w'], c['h']) < 80:
        fautes.append(f'cadran trop petit ({c["w"]:.0f} × {c["h"]:.0f} px)')
    if c['x'] < 0 or c['y'] < 0 or c['x'] + c['w'] > g['vw'] or c['y'] + c['h'] > g['vh']:
        fautes.append('cadran hors de l\'écran')
    gx, gy, gr = g['globe']['cx'], g['globe']['cy'], g['globe']['r']
    px = min(max(gx, c['x']), c['x'] + c['w'])
    py = min(max(gy, c['y']), c['y'] + c['h'])
    if math.hypot(px - gx, py - gy) < gr:
        fautes.append('le cadran masque le globe')
    for t in g['textes']:
        if not (t['x'] + t['w'] <= c['x'] or c['x'] + c['w'] <= t['x'] or
                t['y'] + t['h'] <= c['y'] or c['y'] + c['h'] <= t['y']):
            fautes.append(f'le cadran masque « {t["nom"]} »')
    verdict('C6', not fautes, ' '.join(det) if not fautes else ' ; '.join(fautes[:6]))


def c8_lecture(page):
    fautes = []
    t = page.evaluate("() => document.body.innerText")
    for mot in ['Australopithèques', 'erectus', 'Néandertal', 'Dénisov', 'Florès', 'sapiens']:
        if mot.lower() not in t.lower():
            fautes.append(f'légende sans « {mot} »')
    K, txt = k_legende(page)
    if not K:
        fautes.append('valeur de K absente')
    for f in ['7 Ma', '300 000 ans', '10 000 ans']:
        if page.locator(f'button:has-text("{f}")').count() == 0:
            fautes.append(f'fenêtre « {f} » absente')
    if page.locator('#lecture').count() == 0:
        fautes.append('bouton lecture/pause absent')
    if not page.evaluate("() => (document.querySelector('#date') || {}).textContent || ''").strip():
        fautes.append('date absente')
    page.evaluate('() => window.__hum.regler(0)')
    page.wait_for_timeout(500)
    img = page.screenshot()
    from PIL import Image
    import io
    a = np.asarray(Image.open(io.BytesIO(img)).convert('L'), dtype=np.float64)
    if (a > 40).mean() < 0.005:
        fautes.append('globe noir')
    verdict('C8', not fautes, 'textes, légende, fenêtres, image' if not fautes else ' ; '.join(fautes))


def c9_generations(page):
    def ech(age):
        r = page.evaluate('a => window.__hum.echantillon(a, "sapiens")', age)
        return set((round(p[0], 4), round(p[1], 4)) for p in r)
    a = ech(50000)
    b = ech(50000 - 5)
    c = ech(50000 - 60)
    if len(a) < 10:
        verdict('C9', False, f'trop peu de points sapiens à 50 000 ans ({len(a)})')
        return
    f5 = len(a & b) / len(a)
    f60 = len(a & c) / len(a)
    verdict('C9', f5 >= 0.7 and f60 <= 0.3,
            f'{len(a)} points ; inchangés après 5 ans : {f5:.0%} (≥ 70 %), après 60 ans : {f60:.0%} (≤ 30 %)')


def c10_ponts(page):
    fautes = []
    lieux = {'Béringie': (65.5, -169.0), 'plateau de la Sonde': (2.0, 107.0)}
    t20 = plan(page, 20000, 'terre')
    t0 = plan(page, 0, 'terre')
    for nom, (la, lo) in lieux.items():
        y, x = pixel(la, lo)
        if t20[y, x] < 0.5:
            fautes.append(f'{nom} sous la mer il y a 20 000 ans')
        if t0[y, x] > 0.5:
            fautes.append(f'{nom} émergé aujourd\'hui')
    verdict('C10', not fautes, 'Béringie et Sonde émergées à 20 000 ans, submergées aujourd\'hui'
            if not fautes else ' ; '.join(fautes))


def c11_fluidite(page, octets):
    page.evaluate('() => { window.__hum.regler(6.0e4); window.__hum.lecture(true); }')
    page.wait_for_timeout(4000)
    e = page.evaluate('() => window.__hum.etat()')
    page.evaluate('() => window.__hum.lecture(false)')
    ms = e.get('msJS')
    mo = (octets['avant'] or 0) / 1e6
    ok = ms is not None and ms < 8 and octets['avant'] is not None and mo <= 10
    verdict('C11', ok, f'JS médian {ms} ms par image ; {mo:.2f} Mo avant la première image')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8860)
    ap.add_argument('--seul', default=None)
    args = ap.parse_args()
    port = port_libre(args.port)
    srv = serveur(port)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav, page, erreurs, octets = ouvrir(pw, port)
        pret = page.evaluate('() => !!(window.__hum && window.__hum.pret === true)')
        tous = [('C1', c1_donnees), ('C2', c2_sites), ('C3', c3_remplacement), ('C4', c4_densite),
                ('C5', c5_black_marble), ('C6', c6_compteur), ('C8', c8_lecture),
                ('C9', c9_generations), ('C10', c10_ponts), ('C11', lambda p: c11_fluidite(p, octets))]
        for code, f in tous:
            if args.seul and code not in args.seul.split(','):
                continue
            if not pret and code != 'C1':
                verdict(code, False, 'page non prête (window.__hum absent)')
                continue
            try:
                f(page)
            except Exception as e:
                verdict(code, False, f'exception : {str(e)[:300]}')
        if not args.seul or 'C7' in args.seul:
            verdict('C7', not erreurs, 'aucune erreur' if not erreurs else ' | '.join(erreurs[:5]))
        nav.close()
    srv.shutdown()
    n_ok = sum(1 for _, ok, _ in resultats if ok)
    print(f'\n{n_ok}/{len(resultats)} contrôles passés')
    sys.exit(0 if n_ok == len(resultats) else 1)


if __name__ == '__main__':
    main()
