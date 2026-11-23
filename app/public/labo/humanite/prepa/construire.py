#!/usr/bin/env python3
"""Construit le paquet de la page labo « humanité » à partir des intermédiaires publiés.

Usage : python3 construire.py            (écrit ../donnees/)

1. Relief 0,2° (8 bits, codage non linéaire, précis à 2 m entre −200 et +50 m) pour le
   globe ; niveau marin 7 Ma → 0 (Spratt & Lisiecki 2016 jusqu'à 798 ka, Bintanja & van de
   Wal 2008 jusqu'à 3 Ma, constant avant ; 0 m depuis 5 000 ans).
2. Pour chaque lignée (et la première sortie de sapiens), carte « date d'arrivée / date de
   disparition » sur une grille de 0,5° : croissance aléatoire de proche en proche
   (Dijkstra sur des vitesses bruitées à plusieurs échelles, fronts découpés comme du
   lichen), dans les terres émergées à l'instant considéré et le domaine de la lignée,
   ponts de terre et sauts de mer selon le niveau marin, calée par renforcement des
   chemins pour atteindre chaque site daté au plus tard à 90 % de son âge.
   Disparition : remplacement (arrivée de la lignée suivante moins le temps de
   coexistence), repli vers le dernier refuge, date finale.
3. Effectifs : littérature (estimations) puis HYDE ; table par maille habitée pour HYDE.
"""
import csv
import gzip
import heapq
import json
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage

ICI = os.path.dirname(os.path.abspath(__file__))
INTER = os.path.join(ICI, 'intermediaires')
SORTIE = os.path.abspath(os.path.join(ICI, '..', 'donnees'))
os.makedirs(SORTIE, exist_ok=True)

W, H = 720, 360          # grille des lignées : 0,5°
LOGMAX = 7.0             # âges codés log10(âge) / 7 sur 16 bits
AUJOURDHUI = 2023
ONU_2023 = 8.09e9        # Nations unies, World Population Prospects 2024 (1er juillet 2023)
K = 2000                 # humains par point : constante fixe

CARTES = ['hominines', 'erectus', 'neandertal', 'denisova', 'insulaires', 'sapiens', 'sapiens1']

journal = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    journal.append(s)


def lire_csv(nom):
    with open(os.path.join(ICI, nom), encoding='utf-8') as f:
        lignes = [l for l in f if l.strip() and not l.startswith('#')]
    return list(csv.DictReader(lignes, delimiter=';'))


def ecrire_gz(nom, tableau):
    with gzip.open(os.path.join(SORTIE, nom), 'wb', compresslevel=9) as f:
        f.write(np.ascontiguousarray(tableau).tobytes())
    return os.path.getsize(os.path.join(SORTIE, nom))


# ------------------------------------------------------------------ niveau marin

def niveau_marin():
    ages, sl = [], []
    for l in open(os.path.join(INTER, 'spratt2016.txt'), encoding='latin-1'):
        p = l.split()
        if l.startswith('#') or len(p) < 6:
            continue
        try:
            a, s = float(p[0]), float(p[5])
        except ValueError:
            continue
        ages.append(a * 1000)
        sl.append(s)
    a_sp, s_sp = np.array(ages), np.array(sl)
    ab, sb = [], []
    lecture = False
    for l in open(os.path.join(INTER, 'bintanja2008.txt'), encoding='latin-1'):
        p = l.split()
        if p[:1] == ['Time'] and 'RSL' in p:
            col = p.index('RSL')
            lecture = True
            continue
        if lecture and len(p) > col:
            try:
                ab.append(abs(float(p[0])) * 1000)
                sb.append(float(p[col]))
            except ValueError:
                pass
    ab, sb = np.array(ab), np.array(sb)
    o = np.argsort(ab)
    ab, sb = ab[o], sb[o]
    t = np.arange(0, 7_000_001, 1000.0)       # un pas de 1 000 ans
    s = np.interp(t, ab, sb)
    lim = a_sp.max()
    m = t <= lim
    s[m] = np.interp(t[m], a_sp, s_sp)
    # raccord doux Spratt -> Bintanja sur 20 ka
    r = (t > lim) & (t < lim + 20000)
    w = (t[r] - lim) / 20000
    s[r] = (1 - w) * np.interp(lim, a_sp, s_sp) + w * s[r]
    s[t > ab.max()] = sb[-50:].mean() if len(sb) else 0
    s[t <= 5000] = 0.0     # le stack donne +8 m à 0 ka (artefact d'échelle) : 0 m depuis 5 ka
    log(f'niveau marin : {len(a_sp)} pts Spratt (→ {lim/1e3:.0f} ka), {len(ab)} pts Bintanja (→ {ab.max()/1e6:.1f} Ma) ;'
        f' min {s.min():.0f} m, max {s.max():.0f} m')
    return t, s.astype(np.float32)


# ------------------------------------------------------------------ relief

def relief():
    z = np.load(os.path.join(INTER, 'relief_0p1.npz'))['z'].astype(np.float32)   # 1800 × 3600
    # texture du globe : 0,2°
    z2 = z.reshape(900, 2, 1800, 2).mean(axis=(1, 3))
    code = np.empty(z2.shape, np.uint8)
    b = z2 < -200
    code[b] = np.clip(np.round(39 * (z2[b] + 11000) / 10800), 0, 39)
    m = (~b) & (z2 < 50)
    code[m] = np.clip(np.round(40 + (z2[m] + 200) / 2), 40, 165)
    h = z2 >= 50
    code[h] = np.clip(np.round(166 + 89 * np.log1p((z2[h] - 50) / 50) / np.log1p(8800 / 50)), 166, 255)
    n = ecrire_gz('relief.u8.gz', code)
    log(f'relief 0,2° : {code.shape}, {n/1e6:.2f} Mo')
    # seuil de submersion d'une maille de 0,5° : 60e centile des 25 mailles de 0,1°
    # (une maille est émergée si au moins 40 % de sa surface l'est)
    blocs = z.reshape(H, 5, W, 5).transpose(0, 2, 1, 3).reshape(H, W, 25)
    seuil = np.quantile(blocs, 0.6, axis=2).astype(np.float32)
    return code, seuil


def decode_relief(code):
    c = code.astype(np.float32)
    z = np.where(c <= 39, c / 39 * 10800 - 11000,
                 np.where(c <= 165, (c - 40) * 2 - 200,
                          50 + 50 * np.expm1((c - 166) / 89 * np.log1p(8800 / 50))))
    return z


# ------------------------------------------------------------------ géographie

LAT = 90 - (np.arange(H) + 0.5) * 0.5
LON = -180 + (np.arange(W) + 0.5) * 0.5
LON2, LAT2 = np.meshgrid(LON, LAT)


def afrique():
    a = (LAT2 < 37.6) & (LAT2 > -36) & (LON2 > -19) & (LON2 < 52)
    # mer Rouge et Sinaï : ligne de (32,3°E ; 30°N) à (43,3°E ; 12,6°N)
    ligne = 32.3 + (30 - LAT2) * (11.0 / 17.4)
    arabie = (LAT2 > 12.3) & (LON2 > ligne)
    a &= ~arabie
    a &= ~((LAT2 > 30) & (LON2 > 32.3))
    a &= ~((LAT2 > 35.5) & (LON2 > 10))       # Sicile, Grèce, Anatolie
    a &= ~((LAT2 > 36.0) & (LON2 < -5.6))     # Espagne (le détroit de Gibraltar sépare)
    a &= ~((LON2 > 41.5) & (LAT2 < -11) & (LON2 < 52))  # Madagascar
    return a


def boite(lon0, lon1, lat0, lat1):
    return (LON2 >= lon0) & (LON2 <= lon1) & (LAT2 >= lat0) & (LAT2 <= lat1)


AFR = afrique()
AMER = (LON2 < -25) | ((LON2 > 172) & (LAT2 > 50))  # Amériques (et pointe ouest de la Béringie)
AMER &= ~((LON2 > 172) & (LAT2 > 50) & (LAT2 < 64.5) & (LON2 < 180) & False)
SAHUL = (LON2 > 129) & (LAT2 < -1) & (LON2 < 160) | boite(140, 160, -12, 0)
WALLACEA = boite(116.5, 129, -11, 2) & ~boite(116.5, 119, -4.5, 2)   # Sulawesi, Florès, Timor…
GROENLAND = boite(-75, -10, 59.5, 84)
ANTARCTIQUE = LAT2 < -60
MADAGASCAR = boite(42.5, 51, -26.5, -11.5)
OCEANIE_LOINTAINE = (LON2 > 160) & (LAT2 < 30) | (LON2 < -120) & (LAT2 < 25) & (LON2 > -180) & ~boite(-118, -60, -60, 25)
EURASIE = ~AFR & ~AMER & ~SAHUL & ~GROENLAND & ~ANTARCTIQUE
FLORES = boite(118.5, 123.8, -9.6, -7.8)
LUZON = boite(119.4, 124.6, 12.3, 19.2)


def domaine(carte):
    """Domaine géographique d'une lignée et dates d'ouverture (âge BP à partir duquel la
    lignée peut y entrer) : tableau H × W d'âges ; 0 = jamais."""
    o = np.zeros((H, W), np.float64)
    if carte == 'hominines':
        o[AFR & (LAT2 < 22) & (LAT2 > -35)] = 7.1e6
    elif carte == 'erectus':
        o[AFR] = 2.9e6
        eur = EURASIE & (LAT2 < 54) & ~((LON2 > 60) & (LAT2 > 46)) & ~boite(125, 150, 30, 46)
        o[eur] = 2.4e6
        o[WALLACEA & ~FLORES] = 1.1e6
        o[FLORES] = 1.1e6
        o[LUZON] = 0.75e6
    elif carte == 'neandertal':
        o[EURASIE & boite(-10, 90, 30, 56) & ~boite(48, 90, 30, 37)] = 4.5e5
    elif carte == 'denisova':
        o[EURASIE & boite(75, 135, 8, 54) & ~boite(75, 92, 8, 26)] = 3.0e5
    elif carte == 'insulaires':
        o[FLORES | LUZON] = 7.2e5
    elif carte == 'sapiens1':
        o[EURASIE & boite(20, 60, 12, 42)] = 2.2e5
    elif carte == 'sapiens':
        o[AFR] = 3.2e5
        o[EURASIE & ~WALLACEA] = 7.2e4
        o[EURASIE & (LAT2 > 62)] = 4.6e4             # Arctique : après 46 ka (Yana 32 ka)
        o[WALLACEA] = 6.5e4
        o[SAHUL] = 6.0e4
        o[AMER & ~GROENLAND] = 3.0e4
        o[MADAGASCAR] = 0       # Madagascar, Océanie lointaine, Islande : Holocène (HYDE)
        o[OCEANIE_LOINTAINE & ~AMER] = 0
        o[boite(-25, -12, 62, 67)] = 0
        o[boite(165, 180, -50, -33)] = 0                # Nouvelle-Zélande
    o[GROENLAND | ANTARCTIQUE] = 0
    return o


SAUTS = {  # (distance maximale d'un saut de mer en mailles de 0,5°, âge BP d'ouverture)
    'hominines': (0, 0), 'erectus': (1.5, 1.1e6), 'neandertal': (1.0, 4.5e5),
    'denisova': (1.0, 3e5), 'insulaires': (1.0, 7.2e5), 'sapiens1': (1.0, 2.2e5),
    'sapiens': (2.3, 6.5e4)}

VITESSE = {  # km par millier d'années, vitesse de base du front (avant calage)
    'hominines': 3.0, 'erectus': 15.0, 'neandertal': 20.0, 'denisova': 25.0,
    'insulaires': 10.0, 'sapiens1': 40.0, 'sapiens': 250.0}

COEXISTENCE = {'neandertal': 5000, 'denisova': 5000, 'insulaires': 3000, 'erectus': 20000,
               'hominines': 50000, 'sapiens1': 3000}
REMPLACANTS = {'erectus': ['neandertal', 'denisova', 'sapiens', 'insulaires'],
               'neandertal': ['sapiens'], 'denisova': ['sapiens'], 'insulaires': ['sapiens'],
               'hominines': [], 'sapiens1': []}


def bruit(graine, echelles=((24, 0.55), (8, 0.45), (2.5, 0.35), (0, 0.3))):
    rng = np.random.default_rng(graine)
    n = np.zeros((H, W))
    for s, a in echelles:
        b = rng.standard_normal((H, W))
        if s:
            b = ndimage.gaussian_filter(b, s, mode='wrap')
        b /= b.std() + 1e-12
        n += a * b
    return n


# ------------------------------------------------------------------ croissance

def prochaine_emersion(t_sl, sl):
    """table[z_idx, t_idx] = plus grand indice de temps ≤ t_idx (âge ≤) où le niveau marin
    est sous z : la maille est émergée. z de −260 à +40 m par pas de 1 m."""
    zs = np.arange(-260, 41)
    nt = len(t_sl)
    tab = np.full((len(zs), nt), -1, np.int32)
    for i, z in enumerate(zs):
        em = sl < z
        idx = np.where(em, np.arange(nt), -1)
        # pour chaque t, le plus grand indice ≤ t qui est émergé : accumulation max
        tab[i] = np.maximum.accumulate(idx)
    return zs, tab


class Croissance:
    def __init__(self, seuil, t_sl, sl):
        self.seuil = seuil
        self.t_sl, self.sl = t_sl, sl
        self.zs, self.tab = prochaine_emersion(t_sl, sl)
        self.lat_rad = np.radians(LAT)
        # longueur des pas (km) : est-ouest dépend de la latitude
        self.dx = 55.6 * np.cos(self.lat_rad)
        self.dy = 55.6

    def emerge_au_plus_tot(self, i, j, age):
        """Âge (≤ age) le plus ancien auquel la maille est émergée, ou −1."""
        z = self.seuil[i, j]
        if z > 40:
            return age
        if z < -260:
            return -1.0
        zi = int(z) + 260
        ti = min(len(self.t_sl) - 1, int(age // 1000))
        k = self.tab[zi, ti]
        if k < 0:
            return -1.0
        return float(self.t_sl[k]) if k < ti else age

    def lancer(self, carte, origines, ouverture, mult, graine):
        """Dijkstra en âges décroissants. Renvoie (A, parent)."""
        A = np.zeros((H, W))
        parent = np.full((H, W), -1, np.int64)
        v0 = VITESSE[carte]
        vit = v0 * np.exp(0.9 * bruit(graine)) * mult    # km / ka
        saut, saut_age = SAUTS[carte]
        r = int(math.ceil(saut))
        voisins = [(di, dj) for di in range(-max(1, r), max(1, r) + 1) for dj in range(-max(1, r), max(1, r) + 1)
                   if (di or dj)]
        tas = []
        for (i, j, age) in origines:
            A[i, j] = age
            heapq.heappush(tas, (-age, i, j))
        fait = np.zeros((H, W), bool)
        while tas:
            na, i, j = heapq.heappop(tas)
            a = -na
            if fait[i, j]:
                continue
            fait[i, j] = True
            for di, dj in voisins:
                ii = i + di
                if ii < 0 or ii >= H:
                    continue
                jj = (j + dj) % W
                if fait[ii, jj] or ouverture[ii, jj] <= 0:
                    continue
                pas = math.hypot(di * self.dy, dj * 0.5 * (self.dx[i] + self.dx[ii]))
                est_voisin = abs(di) <= 1 and abs(dj) <= 1
                if not est_voisin:
                    if a > saut_age or math.hypot(di, dj) > saut + 1e-6:
                        continue
                cout = pas / (0.5 * (vit[i, j] + vit[ii, jj])) * 1000.0   # années
                t = min(a, ouverture[ii, jj]) - cout
                if t <= 0:
                    continue
                if est_voisin is False or self.seuil[ii, jj] <= 40:
                    # la maille d'arrivée doit être émergée à l'instant d'arrivée ; sinon on
                    # attend la prochaine émersion (en âges : plus petit)
                    te = self.emerge_au_plus_tot(ii, jj, t)
                    if te <= 0:
                        continue
                    if not est_voisin:
                        # saut de mer : la maille de départ doit aussi être côtière et émergée
                        pass
                    t = te
                if t > A[ii, jj]:
                    A[ii, jj] = t
                    parent[ii, jj] = i * W + j
                    heapq.heappush(tas, (-t, ii, jj))
        return A, parent


def maille(lat, lon):
    i = int(min(H - 1, max(0, math.floor((90 - lat) / 0.5))))
    j = int(min(W - 1, max(0, math.floor((lon + 180) / 0.5))))
    return i, j


def maille_valide(lat, lon, ouverture, seuil, age):
    """Maille de la grille la plus proche du site, dans le domaine et émergée (≤ 1 maille)."""
    i0, j0 = maille(lat, lon)
    best = None
    for di in (0, -1, 1):
        for dj in (0, -1, 1):
            i, j = i0 + di, (j0 + dj) % W
            if 0 <= i < H and ouverture[i, j] > 0:
                d = abs(di) + abs(dj)
                if best is None or d < best[0]:
                    best = (d, i, j)
    return None if best is None else (best[1], best[2])


def caler(cro, carte, sites, ouverture, graine, iterations=40):
    origines = []
    contraintes = []
    for s in sites:
        ij = maille_valide(s['lat'], s['lon'], ouverture, cro.seuil, s['age'])
        if ij is None:
            log(f'  !! {carte} : site hors domaine : {s["nom"]}')
            continue
        if s['role'] == 'origine':
            origines.append((ij[0], ij[1], s['age']))
            ouverture[ij] = max(ouverture[ij], s['age'])
        elif s['role'] == 'site':
            contraintes.append((ij, 0.9 * s['age'] * 1.02, s))   # marge de 2 % sur le seuil
    mult = np.ones((H, W))
    for it in range(iterations):
        A, parent = cro.lancer(carte, origines, ouverture, mult, graine)
        retards = [(c, need, s) for (c, need, s) in contraintes if A[c] < need]
        if not retards:
            log(f'  {carte} : calé en {it + 1} passe(s), {int((A > 0).sum())} mailles atteintes')
            return A, origines, contraintes
        for (c, need, s) in retards:
            if A[c] <= 0:
                facteur = 2.0
            else:
                # temps disponible / temps pris le long du chemin
                facteur = 1.35
            k = c[0] * W + c[1]
            chemin = []
            while k >= 0 and len(chemin) < 100000:
                chemin.append(k)
                k = parent.flat[k]
            masque = np.zeros((H, W), bool)
            masque.flat[chemin] = True
            masque = ndimage.binary_dilation(masque, iterations=2)
            mult[masque] *= facteur
        if it % 5 == 4:
            log(f'  {carte} : passe {it + 1}, {len(retards)} sites en retard : '
                + ', '.join(f'{s["nom"]} ({A[c]:.0f} < {need:.0f})' for c, need, s in retards[:4]))
    log(f'  !! {carte} : non calé, {len(retards)} sites en retard')
    return A, origines, contraintes


def distances_refuge(cro, ij, masque, graine):
    """Distance de proche en proche (km, bruitée) depuis le refuge, dans le masque."""
    D = np.full((H, W), np.inf)
    vit = np.exp(0.6 * bruit(graine + 7))
    D[ij] = 0
    tas = [(0.0, ij[0], ij[1])]
    while tas:
        d, i, j = heapq.heappop(tas)
        if d > D[i, j]:
            continue
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if not (di or dj):
                    continue
                ii, jj = i + di, (j + dj) % W
                if ii < 0 or ii >= H or not masque[ii, jj]:
                    continue
                nd = d + math.hypot(di * cro.dy, dj * cro.dx[i]) / vit[ii, jj]
                if nd < D[ii, jj]:
                    D[ii, jj] = nd
                    heapq.heappush(tas, (nd, ii, jj))
    # mailles non reliées au refuge (îles) : distance à vol d'oiseau
    m = masque & ~np.isfinite(D)
    if m.any():
        la0, lo0 = LAT[ij[0]], LON[ij[1]]
        D[m] = 111.0 * np.hypot(LAT2[m] - la0, (LON2[m] - lo0) * np.cos(np.radians(LAT2[m])))
    return D


def main():
    t0 = time.time()
    code, seuil = relief()
    t_sl, sl = niveau_marin()
    sites = [dict(r, lat=float(r['lat']), lon=float(r['lon']), age=float(r['age_ans']))
             for r in lire_csv('sites_cles.csv')]
    cro = Croissance(seuil, t_sl, sl)
    A, D, info = {}, {}, {}
    ordre = ['hominines', 'sapiens', 'sapiens1', 'neandertal', 'denisova', 'insulaires', 'erectus']
    for n, carte in enumerate(ordre):
        ouv = domaine(carte)
        ss = [s for s in sites if s['lignee'] == carte]
        A[carte], origines, contraintes = caler(cro, carte, ss, ouv, graine=11 + n)
        info[carte] = {'origines': len(origines), 'contraintes': len(contraintes)}
    # disparitions
    for carte in ordre:
        a = A[carte]
        pres = a > 0
        refuges = [s for s in sites if s['lignee'] == carte and s['role'] == 'refuge']
        d = np.zeros((H, W))
        if refuges:
            r = refuges[0]
            F = r['age']
            ij = maille_valide(r['lat'], r['lon'], (pres * 1.0), seuil, F)
            if ij is None:
                ij = maille(r['lat'], r['lon'])
            dist = distances_refuge(cro, ij, pres, 5 + len(carte))
            # le repli doit vider chaque site avant 90 % de son âge (le site n'est plus
            # exigé ensuite) mais sans vider le domaine avant la fin de la lignée : vitesse
            # de repli choisie pour que le domaine se vide en 15 % de la durée de vie restante
            dmax = np.nanmax(np.where(np.isfinite(dist) & pres, dist, 0))
            duree = 0.25 * F if carte != 'hominines' else 3.0e5
            d = np.where(pres, F + dist / max(dmax, 1) * duree, 0)
            for rc in REMPLACANTS.get(carte, []):
                ar = A[rc]
                tau = COEXISTENCE.get(carte, 5000)
                d = np.where(pres & (ar > 0), np.maximum(d, ar - tau), d)
            d = np.where(pres, np.maximum(d, F), 0)
            # chaque site doit rester habité à 90 % de son âge
            for s in sites:
                if s['lignee'] == carte and s['role'] in ('site', 'origine'):
                    ij2 = maille_valide(s['lat'], s['lon'], pres * 1.0, seuil, s['age'])
                    if ij2 and d[ij2] >= 0.9 * s['age']:
                        log(f'  !! {carte} : {s["nom"]} vidé trop tôt ({d[ij2]:.0f} ≥ {0.9 * s["age"]:.0f})')
        D[carte] = d
        n_pres = int(pres.sum())
        log(f'{carte} : {n_pres} mailles ; arrivée {a[pres].max():.0f} → {a[pres].min():.0f} ans ; '
            f'disparition {d[pres].max() if d.any() else 0:.0f} → {d[pres].min() if d.any() else 0:.0f} ans')
    # codage 16 bits log10
    def q(x):
        return np.where(x > 0, np.clip(np.round(np.log10(np.maximum(x, 1.0)) / LOGMAX * 65535), 1, 65535), 0).astype(np.uint16)
    pile = np.stack([np.stack([q(A[c]), q(D[c])], axis=-1) for c in CARTES])   # 7 × H × W × 2
    n = ecrire_gz('lignees.u16.gz', pile)
    log(f'cartes des lignées : {pile.shape}, {n/1e6:.2f} Mo')
    np.savez_compressed(os.path.join(ICI, 'intermediaires', 'lignees_0p5.npz'),
                        **{f'A_{c}': A[c].astype(np.float32) for c in CARTES},
                        **{f'D_{c}': D[c].astype(np.float32) for c in CARTES})
    # niveau marin : pas de 1 000 ans
    n = ecrire_gz('niveau_marin.f32.gz', sl)
    # seuils de submersion de la grille de 0,5° (pour les points)
    ecrire_gz('seuil_0p5.i16.gz', np.clip(np.round(seuil), -32000, 32000).astype(np.int16))
    meta = {'grille': {'w': W, 'h': H, 'pas_deg': 0.5, 'ligne0': 'nord', 'colonne0': '180°W'},
            'relief': {'w': 1800, 'h': 900, 'codage': 'u8 : 0-39 = −11 000…−200 m ; 40-165 = −200…+50 m (2 m) ; 166-255 = log'},
            'cartes': CARTES, 'codage_age': f'u16 = 65535 · log10(âge) / {LOGMAX} ; 0 = jamais',
            'niveau_marin': {'pas_ans': 1000, 'n': int(len(sl)),
                             'sources': 'Spratt & Lisiecki 2016 (0–798 ka) ; Bintanja & van de Wal 2008 (→ 3 Ma)'},
            'K': K, 'aujourdhui': AUJOURDHUI, 'info': info}
    json.dump(meta, open(os.path.join(SORTIE, 'meta.json'), 'w'), ensure_ascii=False, indent=1)
    json.dump([{'lignee': s['lignee'], 'role': s['role'], 'nom': s['nom'], 'lat': s['lat'], 'lon': s['lon'],
                'age': s['age'], 'source': s['source']} for s in sites],
              open(os.path.join(SORTIE, 'sites.json'), 'w'), ensure_ascii=False, indent=0)
    log(f'fini en {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
