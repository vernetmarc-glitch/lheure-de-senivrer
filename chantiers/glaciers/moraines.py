#!/usr/bin/env python3
"""Moraines médianes du chantier S8 : là où deux flux de glace se rejoignent.

Principe physique : une moraine médiane naît à la confluence de deux glaciers (ou à
l'aval d'un éperon rocheux qui les sépare) et suit ensuite le courant. Elle marque la
frontière entre deux masses de glace venues de bassins différents.

Méthode (grille de 500 m) : on repère les pointes aval des obstacles rocheux qui ont de
la glace des deux côtés (éperon entre deux glaciers qui confluent, nunatak) ; de chaque
pointe, on suit vers l'aval la ligne de courant des vitesses de surface publiées (pas de
250 m, jusqu'à 80 km, tant que la glace coule) : c'est la moraine médiane, réunion des
deux moraines latérales internes.

Le même module sert à préparer le paquet publié (à partir des vitesses quantifiées
publiées) et aux contrôles (à partir des vitesses flottantes de référence).

Usage : python3 chantiers/glaciers/moraines.py   → app/public/labo/glaciers/donnees/moraines.bin.gz
"""
import gzip
import json
import os
import sys

import numpy as np

R = 2              # points par maille (500 m)
PAS = 0.25         # pas de suivi, en mailles (250 m)
N_PAS = 320        # 80 km au plus
V_ARRET = 1.0      # m/a : la glace ne coule plus, la moraine s'arrête
V_POINTE = 10.0    # m/a : la glace coule le long de l'éperon
AMONT = 0.75       # km : l'obstacle rocheux est juste en amont
LARGE = 1.5        # km : de la glace de part et d'autre de l'obstacle (deux flux)


def bil(ch, x, y):
    ny, nx = ch.shape
    fx = np.clip(x - 0.5, 0, nx - 1.0001)
    fy = np.clip(y - 0.5, 0, ny - 1.0001)
    i, j = fx.astype(int), fy.astype(int)
    a, b = fx - i, fy - j
    return ((1 - a) * (1 - b) * ch[j, i] + a * (1 - b) * ch[j, i + 1]
            + (1 - a) * b * ch[j + 1, i] + a * b * ch[j + 1, i + 1])


def champs_fins(thk):
    """Masque de glace sur la grille fine (même règle que l'écran : masque bilinéaire ≥ 0,5)."""
    ny, nx = thk.shape
    yy, xx = np.mgrid[0:ny * R, 0:nx * R]
    x = (xx + 0.5) / R
    y = (yy + 0.5) / R
    m = bil((thk >= 1).astype('f8'), x.ravel(), y.ravel()).reshape(x.shape) >= 0.5
    return m, x, y


def pointes(thk, u, v):
    """Pointes aval des éperons et nunataks qui séparent deux flux : points de glace juste en
    aval d'une roche (AMONT) qui a de la glace des deux côtés, perpendiculairement au courant."""
    masque = (thk >= 1).astype('f8')
    m, x, y = champs_fins(thk)
    from scipy.ndimage import binary_dilation
    bord = m & binary_dilation(~m)
    px, py = x[bord], y[bord]
    uu, vv = bil(u, px, py), bil(v, px, py)
    s = np.hypot(uu, vv)
    ok = s >= V_POINTE
    px, py, uu, vv, s = px[ok], py[ok], uu[ok], vv[ok], s[ok]
    ex, ey = uu / s, vv / s
    qx, qy = px - ex * AMONT, py - ey * AMONT
    roche = bil(masque, qx, qy) < 0.5
    g = bil(masque, qx - ey * LARGE, qy + ex * LARGE) >= 0.5
    d = bil(masque, qx + ey * LARGE, qy - ex * LARGE) >= 0.5
    sel = roche & g & d
    px, py, ex, ey = px[sel], py[sel], ex[sel], ey[sel]
    # deux flux distincts : juste en aval de la pointe, deux points de part et d'autre,
    # remontés ensemble sur 10 km, restent dans la glace et passent de part et d'autre de roche
    ax, ay = px + ex * 1.0, py + ey * 1.0
    gx, gy = ax - ey * 0.75, ay + ex * 0.75
    dx, dy = ax + ey * 0.75, ay - ex * 0.75
    separe = np.zeros(len(px), bool)
    dans = np.ones(len(px), bool)
    for _ in range(40):
        for X, Y in ((gx, gy), (dx, dy)):
            a, b = bil(u, X, Y), bil(v, X, Y)
            n = np.maximum(np.hypot(a, b), 1e-9)
            X -= a / n * PAS
            Y -= b / n * PAS
        dans &= (bil(masque, gx, gy) >= 0.5) | separe
        dans &= (bil(masque, dx, dy) >= 0.5) | separe
        for q in np.linspace(0.05, 0.95, 16):
            separe |= bil(masque, gx + q * (dx - gx), gy + q * (dy - gy)) < 0.5
    ok = separe & dans
    return px[ok], py[ok]


def suivre(u, v, masque, px, py, n_pas=N_PAS):
    """Suit le courant vers l'aval (Runge-Kutta 2) ; renvoie la liste des positions."""
    px, py = px.copy(), py.copy()
    actif = np.ones(len(px), bool)
    traces = []
    for _ in range(n_pas):
        a = np.where(actif)[0]
        if not len(a):
            break
        traces.append((px[a].copy(), py[a].copy()))
        def dirn(x, y):
            uu, vv = bil(u, x, y), bil(v, x, y)
            s = np.hypot(uu, vv)
            return uu / np.maximum(s, 1e-9), vv / np.maximum(s, 1e-9), s
        ex, ey, s = dirn(px[a], py[a])
        mx, my = px[a] + ex * PAS / 2, py[a] + ey * PAS / 2
        ex2, ey2, s2 = dirn(mx, my)
        nxp, nyp = px[a] + ex2 * PAS, py[a] + ey2 * PAS
        stop = (s < V_ARRET) | (s2 < V_ARRET) | (nxp < 0) | (nyp < 0) | (nxp > u.shape[1]) | (nyp > u.shape[0])
        ok = ~stop
        stop[ok] |= bil(masque, nxp[ok], nyp[ok]) < 0.5
        go = ~stop
        px[a[go]], py[a[go]] = nxp[go], nyp[go]
        actif[a[stop]] = False
    return traces


def deux_flux(u, v, masque, x, y, ecart=0.75, n_pas=N_PAS):
    """Vrai si, de part et d'autre du point (± ecart km, perpendiculairement au courant), les
    deux glaces remontées passent de part et d'autre de roche : deux flux qui se sont rejoints."""
    uu, vv = bil(u, x, y), bil(v, x, y)
    n = np.maximum(np.hypot(uu, vv), 1e-9)
    nx, ny = -vv / n, uu / n
    gx, gy, dx, dy = x + ecart * nx, y + ecart * ny, x - ecart * nx, y - ecart * ny
    separe = np.zeros(len(x), bool)
    for _ in range(n_pas):
        for X, Y in ((gx, gy), (dx, dy)):
            a, b = bil(u, X, Y), bil(v, X, Y)
            m = np.maximum(np.hypot(a, b), 1e-9)
            X -= a / m * PAS
            Y -= b / m * PAS
        for q in np.linspace(0.05, 0.95, 16):
            separe |= bil(masque, gx + q * (dx - gx), gy + q * (dy - gy)) < 0.5
    return separe


def moraines(thk, u, v):
    """thk, u, v : [ny][nx] aux centres des mailles (m, m/a). Renvoie un booléen [ny*R][nx*R] :
    moraines médianes, lignes de courant issues des pointes d'éperons entre deux flux."""
    ny, nx = thk.shape
    out = np.zeros((ny * R, nx * R), bool)
    px, py = pointes(thk, u, v)
    if not len(px):
        return out
    for tx, ty in suivre(u, v, (thk >= 1).astype('f8'), px, py):
        i = np.clip((tx * R).astype(int), 0, nx * R - 1)
        j = np.clip((ty * R).astype(int), 0, ny * R - 1)
        out[j, i] = True
    # on ne garde que les points où la moraine sépare bien deux flux (définition même
    # d'une moraine médiane) ; ailleurs la ligne s'est perdue dans un courant unique
    jj, ii = np.nonzero(out)
    if len(jj):
        garde = deux_flux(u, v, (thk >= 1).astype('f8'), (ii + 0.5) / R, (jj + 0.5) / R)
        out[jj[~garde], ii[~garde]] = False
    return out


def main():
    ici = os.path.dirname(os.path.abspath(__file__))
    don = os.path.join(ici, '..', '..', 'app/public/labo/glaciers/donnees')
    meta = json.load(open(os.path.join(don, 'meta.json')))
    nt, ny, nx = meta['nt'], meta['ny'], meta['nx']
    brut = gzip.open(os.path.join(don, 'glace.bin.gz')).read()
    n = nt * ny * nx
    thk = np.frombuffer(brut[:2 * n], '<u2').reshape(nt, ny, nx).astype('f8')
    u = np.frombuffer(brut[2 * n:4 * n], '<i2').reshape(nt, ny, nx) * meta['echelle_vitesse']
    v = np.frombuffer(brut[4 * n:6 * n], '<i2').reshape(nt, ny, nx) * meta['echelle_vitesse']
    sortie = np.zeros((nt, ny * R, nx * R), np.uint8)
    for k in range(nt):
        med = moraines(thk[k], u[k], v[k])
        sortie[k] = med * 255
        if k % 10 == 0:
            print(meta['ages'][k], 'ans : moraines médianes', med.sum() * 0.5, 'km', flush=True)
    with gzip.open(os.path.join(don, 'moraines.bin.gz'), 'wb', compresslevel=9) as f:
        f.write(sortie.tobytes())
    meta['moraines'] = {'fichier': 'moraines.bin.gz', 'nx': nx * R, 'ny': ny * R, 'dx': meta['dx'] / R,
                        'disposition': 'u8 (255 = moraine médiane), [nt][ny][nx], rangée 0 = sud',
                        'methode': 'chantiers/glaciers/moraines.py : lignes de courant issues des pointes '
                                   'd’éperons et de nunataks qui séparent deux flux'}
    json.dump(meta, open(os.path.join(don, 'meta.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    sys.exit(main())
