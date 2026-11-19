#!/usr/bin/env python3
"""Chantier S8 — préparation des données des glaciers des Alpes du Nord.

Tourne sur une machine GitHub (workflow `chantier-glaciers.yml`) : le bac à sable
de Claude ne joint pas Zenodo.

Source glace : Seguinot, J., Ivy-Ochs, S., Jouvet, G., Huss, M., Funk, M. et
Preusser, F. (2018), « Modelling last glacial cycle ice dynamics in the Alps »,
The Cryosphere 12, 3265–3285. Simulation PISM de référence : 1 km, forçage EPICA,
réduction des précipitations paléo (`alpcyc.1km.epic.pp.ex.1ka.nc`), variables
spatiales tous les 1 000 ans (Zenodo, doi 10.5281/zenodo.1423176, dernière
version).

Source relief : Copernicus DEM GLO-30 (AWS open data), repli GLO-90, repli ultime
le relief `topg` du fichier PISM.

Sorties (petites, commitées sur la branche) :
  app/public/labo/glaciers/donnees/meta.json      description, lieux, âges
  app/public/labo/glaciers/donnees/glace.bin.gz   thk u16 | u i16 | v i16, [nt][ny][nx]
  app/public/labo/glaciers/donnees/relief.bin.gz  i16, [nyr][nxr], mètres
  chantiers/glaciers/reference/reference.npz      masques exacts (flottants) et
                                                  vitesses flottantes, pour les contrôles
  chantiers/glaciers/journal-preparation.md       journal lisible (métadonnées, bilan)

Conventions : grille native du fichier PISM (pas de rééchantillonnage de la glace),
rangée 0 = sud, colonne 0 = ouest ; glace := épaisseur >= 1 m.
"""
import gzip
import json
import os
import subprocess
import sys
import traceback
import urllib.request

import numpy as np

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PUB = os.path.join(RACINE, 'app/public/labo/glaciers/donnees')
REF = os.path.join(RACINE, 'chantiers/glaciers/reference')
JOURNAL = os.path.join(RACINE, 'chantiers/glaciers/journal-preparation.md')
DL = os.environ.get('GLACIERS_DL', '/tmp/glaciers-dl')

CENTRE_LONLAT = (5.80, 45.20)        # Grenoble au centre de la fenêtre
DEMI = 75                             # 150 mailles de 1 km
FICHIER_GLACE = 'alpcyc.1km.epic.pp.ex.1ka.nc'
CONCEPT_CONTINU = '1423176'
REPLI_ENREGISTREMENT = '7802275'
RES_RELIEF = 125.0                    # m
SEUIL_GLACE = 1.0                     # m
ECHELLE_V = 0.1                       # m/a par unité entière
AGES_REFERENCE = [110000, 60000, 25000, 20000, 15000, 0]

LIEUX = [
    ('Grenoble', 5.7245, 45.1885, 'ville'),
    ('Chambéry', 5.9178, 45.5646, 'ville'),
    ('Grésivaudan', 5.905, 45.300, 'vallée'),
    ('Chartreuse', 5.790, 45.330, 'massif'),
    ('Vercors', 5.500, 44.980, 'massif'),
    ('Belledonne', 6.060, 45.180, 'massif'),
    ('Oisans', 6.250, 45.000, 'massif'),
    ('Bauges', 6.150, 45.680, 'massif'),
    ('Trièves', 5.700, 44.840, 'vallée'),
    ('Voironnais', 5.560, 45.360, 'vallée'),
]
# point de contrôle « glace dans le Grésivaudan » : fond de vallée près de Crolles
GRESIVAUDAN = (5.880, 45.285)

lignes = []


def note(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    lignes.append(s)


def ecrire_journal():
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, 'w') as f:
        f.write('# Journal de préparation — chantier S8 (glaciers)\n\n')
        f.write('Écrit par `chantiers/glaciers/prepare.py` sur une machine GitHub.\n\n```\n')
        f.write('\n'.join(lignes))
        f.write('\n```\n')


def lire_json(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json',
                                               'User-Agent': 'lheure-de-senivrer-chantier'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def telecharger(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        note('déjà en cache :', dest, os.path.getsize(dest), 'octets')
        return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + '.part'
    r = subprocess.run(['curl', '-L', '--fail', '--retry', '6', '--retry-delay', '10',
                        '-sS', '-o', tmp, url])
    if r.returncode != 0:
        note('échec du téléchargement', url, 'code', r.returncode)
        return False
    os.replace(tmp, dest)
    note('téléchargé', url, '->', os.path.getsize(dest), 'octets')
    return True


def fichiers_zenodo():
    essais = [f'https://zenodo.org/api/records/{CONCEPT_CONTINU}/versions/latest',
              f'https://zenodo.org/api/records/{REPLI_ENREGISTREMENT}']
    for url in essais:
        try:
            rec = lire_json(url)
            fichiers = {}
            for f in rec.get('files', []):
                cle = f.get('key') or f.get('filename')
                lien = f.get('links', {}).get('self') or f.get('links', {}).get('content')
                fichiers[cle] = lien
            note('Zenodo :', url, '-> enregistrement', rec.get('id'),
                 'version', rec.get('metadata', {}).get('version'), '|', len(fichiers), 'fichiers')
            return rec.get('id'), rec.get('metadata', {}).get('version'), fichiers
        except Exception as e:  # noqa
            note('API Zenodo indisponible', url, repr(e))
    rid = REPLI_ENREGISTREMENT
    return rid, '?', {FICHIER_GLACE: f'https://zenodo.org/records/{rid}/files/{FICHIER_GLACE}?download=1'}


def trouver_crs(ds):
    from pyproj import CRS
    cand = []
    for nom in ['proj4', 'proj', 'proj4text', 'crs_wkt', 'spatial_ref', 'projection']:
        if nom in ds.ncattrs():
            cand.append(('global:' + nom, ds.getncattr(nom)))
    for v in ds.variables.values():
        for nom in ['proj4', 'proj4text', 'proj4_params', 'crs_wkt', 'spatial_ref', 'epsg_code']:
            if nom in v.ncattrs():
                cand.append((v.name + ':' + nom, v.getncattr(nom)))
    for d, val in cand:
        note('indice de projection', d, '=', str(val)[:300])
    for d, val in cand:
        try:
            crs = CRS.from_user_input(val if not str(val).isdigit() else int(val))
            note('projection retenue :', d, '->', crs.to_string()[:200])
            return crs
        except Exception:
            pass
    note('AUCUNE projection lisible : repli EPSG:32632 (UTM 32N, celle de alpcyc)')
    return CRS.from_epsg(32632)


def en_annees(var):
    vals = np.asarray(var[:], dtype='f8')
    unites = getattr(var, 'units', '')
    note('temps :', var.name, 'unités', repr(unites), 'premiers', vals[:3], 'derniers', vals[-3:])
    if 'sec' in unites:
        vals = vals / (365.0 * 86400.0)
    elif unites.startswith('ka') or 'kyr' in unites or 'kiloyear' in unites:
        vals = vals * 1000.0
    return vals


def lire_champ(var, t, sy, sx, ordre):
    a = var[t]
    a = np.ma.filled(a.astype('f8'), np.nan) if np.ma.isMaskedArray(a) else np.asarray(a, 'f8')
    if ordre == 'xy':
        a = a.T
    return a[sy, sx]


def preparer_glace():
    from netCDF4 import Dataset
    from pyproj import Transformer
    rid, version, fichiers = fichiers_zenodo()
    url = fichiers.get(FICHIER_GLACE)
    if not url:
        note('fichier absent de l’enregistrement :', FICHIER_GLACE, 'disponibles :', sorted(fichiers))
        raise SystemExit(2)
    chemin = os.path.join(DL, FICHIER_GLACE)
    if not telecharger(url, chemin):
        alt = f'https://zenodo.org/records/{rid}/files/{FICHIER_GLACE}?download=1'
        if not telecharger(alt, chemin):
            raise SystemExit(3)

    ds = Dataset(chemin)
    note('--- attributs globaux ---')
    for a in ds.ncattrs():
        note(f'  {a} = {str(ds.getncattr(a))[:200]}')
    note('--- variables ---')
    for v in ds.variables.values():
        note(f'  {v.name} {v.dimensions} {v.shape} units={getattr(v, "units", "")!r} '
             f'long_name={getattr(v, "long_name", "")!r}')

    crs = trouver_crs(ds)
    vers = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
    x = np.asarray(ds.variables['x'][:], 'f8')
    y = np.asarray(ds.variables['y'][:], 'f8')
    if 'units' in ds.variables['x'].ncattrs() and ds.variables['x'].units.startswith('km'):
        x, y = x * 1000, y * 1000
    dx = float(np.median(np.diff(x)))
    dy = float(np.median(np.diff(y)))
    note('grille : nx', len(x), 'ny', len(y), 'dx', dx, 'dy', dy, 'x', x[0], x[-1], 'y', y[0], y[-1])
    cx, cy = vers.transform(*CENTRE_LONLAT)
    note('centre (5,80 E ; 45,20 N) dans la projection :', round(cx), round(cy))
    ic = int(np.argmin(np.abs(x - cx)))
    jc = int(np.argmin(np.abs(y - cy)))
    i0, i1 = ic - DEMI, ic + DEMI
    j0, j1 = jc - DEMI, jc + DEMI
    if i0 < 0 or j0 < 0 or i1 > len(x) or j1 > len(y):
        note('ATTENTION : la fenêtre sort du domaine, elle est rognée')
        i0, j0 = max(i0, 0), max(j0, 0)
        i1, j1 = min(i1, len(x)), min(j1, len(y))
    sx = slice(i0, i1)
    ydesc = dy < 0
    sy = slice(j0, j1)
    xs, ys = x[sx], y[sy]
    note('fenêtre : colonnes', i0, i1, 'rangées', j0, j1, 'y décroissant' if ydesc else 'y croissant')

    tnom = 'time' if 'time' in ds.variables else ('age' if 'age' in ds.variables else None)
    annees = en_annees(ds.variables[tnom])
    ages = np.round(-annees if np.nanmax(annees) <= 1 else annees).astype(int)
    if tnom == 'age':
        ages = np.round(annees).astype(int)
    note('âges (ans avant présent) :', ages[:3], '…', ages[-3:], 'n =', len(ages))

    def var(*noms):
        for n in noms:
            if n in ds.variables:
                return ds.variables[n]
        return None

    vthk = var('thk')
    vu = var('uvelsurf', 'u_surf', 'usurf_vel')
    vv = var('vvelsurf', 'v_surf', 'vsurf_vel')
    vmag = var('velsurf_mag')
    vtopg = var('topg')
    dims = vthk.dimensions
    ordre = 'xy' if dims[-1] == 'y' else 'yx'
    note('dimensions de thk', dims, 'ordre', ordre)

    def conv_v(v):
        u = getattr(v, 'units', '')
        if 'm s-1' in u or 'm/s' in u:
            return 365.0 * 86400.0
        return 1.0

    ordre_t = np.argsort(-ages)          # du plus ancien au plus récent
    nt, ny, nx = len(ages), len(ys), len(xs)
    thk_q = np.zeros((nt, ny, nx), np.uint16)
    u_q = np.zeros((nt, ny, nx), np.int16)
    v_q = np.zeros((nt, ny, nx), np.int16)
    masques = np.zeros((nt, ny, nx), bool)
    aires = np.zeros(nt)
    vmax = 0.0
    ref_u, ref_v, ref_thk, ref_ages = [], [], [], []
    for k, t in enumerate(ordre_t):
        thk = np.nan_to_num(lire_champ(vthk, t, sy, sx, ordre))
        if ydesc:
            thk = thk[::-1]
        glace = thk >= SEUIL_GLACE
        if vu is not None and vv is not None:
            u = np.nan_to_num(lire_champ(vu, t, sy, sx, ordre)) * conv_v(vu)
            v = np.nan_to_num(lire_champ(vv, t, sy, sx, ordre)) * conv_v(vv)
            if ydesc:
                u, v = u[::-1], -v[::-1]
        else:
            u = v = np.zeros_like(thk)
        u = np.where(glace, u, 0.0)
        v = np.where(glace, v, 0.0)
        # les valeurs de remplissage énormes (>1e5 m/a) ne sont pas des vitesses
        u = np.where(np.abs(u) > 1e5, 0.0, u)
        v = np.where(np.abs(v) > 1e5, 0.0, v)
        vmax = max(vmax, float(np.hypot(u, v).max()))
        q = np.where(glace, np.maximum(1, np.round(thk)), 0)
        thk_q[k] = np.clip(q, 0, 65535).astype(np.uint16)
        u_q[k] = np.clip(np.round(u / ECHELLE_V), -32767, 32767).astype(np.int16)
        v_q[k] = np.clip(np.round(v / ECHELLE_V), -32767, 32767).astype(np.int16)
        masques[k] = glace
        aires[k] = glace.sum() * abs(dx * dy) / 1e6
        if int(ages[t]) in AGES_REFERENCE:
            ref_ages.append(int(ages[t]))
            ref_u.append(u.astype('f4'))
            ref_v.append(v.astype('f4'))
            ref_thk.append(thk.astype('f4'))
    if vu is None:
        note('ATTENTION : pas de composantes de vitesse de surface (uvelsurf/vvelsurf)')
    ages_tries = ages[ordre_t]
    note('vitesse de surface maximale dans la fenêtre :', round(vmax, 1), 'm/a')
    if vmax / ECHELLE_V > 32767:
        note('ATTENTION : vitesses écrêtées à', 32767 * ECHELLE_V, 'm/a')

    # relief PISM (dernier pas) en repli
    topg = None
    if vtopg is not None:
        a = vtopg[ordre_t[-1]] if vtopg.ndim == 3 else vtopg[:]
        a = np.ma.filled(a.astype('f8'), np.nan) if np.ma.isMaskedArray(a) else np.asarray(a, 'f8')
        if ordre == 'xy':
            a = a.T
        topg = a[sy, sx]
        if ydesc:
            topg = topg[::-1]

    xs_c = xs if not ydesc else xs
    ys_c = ys[::-1] if ydesc else ys
    ouest = float(xs_c[0] - abs(dx) / 2)
    sud = float(ys_c[0] - abs(dy) / 2)

    # bilan
    kmax = int(np.argmax(aires))
    note('aire englacée de la fenêtre : max', round(aires[kmax]), 'km² à', ages_tries[kmax], 'ans')
    for a_ in [115000, 100000, 80000, 65000, 60000, 45000, 30000, 25000, 22000, 20000, 18000, 15000, 12000, 10000, 5000, 0]:
        w = np.where(ages_tries == a_)[0]
        if len(w):
            note(f'  {a_:>6} ans : {aires[w[0]]:8.0f} km²  épaisseur max {thk_q[w[0]].max()} m')
    inv = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    lieux = []
    for nom, lo, la, genre in LIEUX:
        px, py = vers.transform(lo, la)
        lieux.append({'nom': nom, 'genre': genre, 'x': round(px - ouest, 1), 'y': round(py - sud, 1),
                      'lon': lo, 'lat': la})
    gx, gy = vers.transform(*GRESIVAUDAN)
    gi, gj = int((gx - ouest) // abs(dx)), int((gy - sud) // abs(dy))
    note('Grésivaudan (Crolles) : maille', gi, gj, 'épaisseur au maximum', thk_q[kmax, gj, gi], 'm')
    # convergence du méridien au centre : angle du nord géographique dans la grille
    p0 = vers.transform(CENTRE_LONLAT[0], CENTRE_LONLAT[1])
    p1 = vers.transform(CENTRE_LONLAT[0], CENTRE_LONLAT[1] + 0.05)
    nord = float(np.degrees(np.arctan2(p1[0] - p0[0], p1[1] - p0[1])))
    note('le nord géographique fait', round(nord, 2), '° avec l’axe y de la grille')
    coins = [inv.transform(ouest, sud), inv.transform(ouest + nx * abs(dx), sud + ny * abs(dy))]
    note('coins (lon, lat) :', coins)

    os.makedirs(PUB, exist_ok=True)
    os.makedirs(REF, exist_ok=True)
    corps = thk_q.astype('<u2').tobytes() + u_q.astype('<i2').tobytes() + v_q.astype('<i2').tobytes()
    with gzip.open(os.path.join(PUB, 'glace.bin.gz'), 'wb', compresslevel=9) as f:
        f.write(corps)
    np.savez_compressed(os.path.join(REF, 'reference.npz'),
                        masques=np.packbits(masques.reshape(nt, -1), axis=1),
                        forme=np.array([nt, ny, nx]), ages=ages_tries.astype('i4'),
                        aires_km2=aires.astype('f8'),
                        ref_ages=np.array(ref_ages, 'i4'), ref_u=np.array(ref_u),
                        ref_v=np.array(ref_v), ref_thk=np.array(ref_thk),
                        topg=(topg.astype('f4') if topg is not None else np.zeros(0, 'f4')))
    meta = {
        'source': {
            'glace': 'Seguinot et al. 2018, The Cryosphere 12, 3265–3285 — PISM 1 km, EPICA, '
                     'précipitations paléo réduites (alpcyc.1km.epic.pp.ex.1ka.nc)',
            'zenodo': f'https://zenodo.org/records/{rid}', 'version': version,
        },
        'crs': crs.to_string(), 'nord_deg': round(nord, 3),
        'nx': nx, 'ny': ny, 'nt': nt, 'dx': abs(dx), 'dy': abs(dy),
        'ouest': ouest, 'sud': sud,
        'ages': [int(a) for a in ages_tries],
        'seuil_glace_m': SEUIL_GLACE, 'echelle_vitesse': ECHELLE_V,
        'glace': {'fichier': 'glace.bin.gz', 'disposition': 'thk u16 | u i16 | v i16, [nt][ny][nx], rangée 0 = sud'},
        'aires_km2': [round(float(a), 1) for a in aires],
        'lieux': lieux,
        'gresivaudan': {'x': round(gx - ouest, 1), 'y': round(gy - sud, 1), 'i': gi, 'j': gj},
        'coins_lonlat': coins,
    }
    return meta, crs, ouest, sud, nx * abs(dx), ny * abs(dy), topg


def preparer_relief(meta, crs, ouest, sud, largeur, hauteur, topg):
    nxr = int(round(largeur / RES_RELIEF))
    nyr = int(round(hauteur / RES_RELIEF))
    relief = None
    try:
        import rasterio
        from rasterio.merge import merge
        from rasterio.transform import from_origin
        from rasterio.warp import reproject, Resampling
        lo = [c[0] for c in meta['coins_lonlat']]
        la = [c[1] for c in meta['coins_lonlat']]
        lons = range(int(np.floor(min(lo) - 0.2)), int(np.floor(max(lo) + 0.2)) + 1)
        lats = range(int(np.floor(min(la) - 0.2)), int(np.floor(max(la) + 0.2)) + 1)
        for nom_jeu, seau, code in [('GLO-30', 'copernicus-dem-30m', '10'),
                                    ('GLO-90', 'copernicus-dem-90m', '30')]:
            chemins = []
            for la_ in lats:
                for lo_ in lons:
                    tuile = (f'Copernicus_DSM_COG_{code}_N{la_:02d}_00_'
                             f'E{lo_:03d}_00_DEM')
                    url = f'https://{seau}.s3.amazonaws.com/{tuile}/{tuile}.tif'
                    dest = os.path.join(DL, nom_jeu, tuile + '.tif')
                    if telecharger(url, dest):
                        chemins.append(dest)
            if not chemins:
                continue
            srcs = [rasterio.open(c) for c in chemins]
            mos, tr = merge(srcs)
            dst = np.zeros((nyr, nxr), 'f4')
            reproject(mos[0].astype('f4'), dst, src_transform=tr, src_crs=srcs[0].crs,
                      dst_transform=from_origin(ouest, sud + hauteur, RES_RELIEF, RES_RELIEF),
                      dst_crs=crs.to_wkt(), resampling=Resampling.average, src_nodata=-32767,
                      dst_nodata=np.nan)
            dst = dst[::-1]          # rangée 0 = sud
            manque = np.isnan(dst).mean()
            note('relief', nom_jeu, ':', len(chemins), 'tuiles, lacunes', round(100 * manque, 2), '%',
                 'min', np.nanmin(dst), 'max', np.nanmax(dst))
            if manque < 0.02:
                relief = np.nan_to_num(dst, nan=float(np.nanmin(dst)))
                meta['relief_source'] = f'Copernicus DEM {nom_jeu} (AWS open data), moyenné à {RES_RELIEF:.0f} m'
                break
    except Exception as e:  # noqa
        note('relief Copernicus impossible :', repr(e))
        note(traceback.format_exc())
    if relief is None and topg is not None:
        from scipy.ndimage import zoom
        relief = zoom(np.nan_to_num(topg), nxr / topg.shape[1], order=3)[:nyr, :nxr]
        meta['relief_source'] = 'relief topg du fichier PISM (1 km), interpolé — repli'
        note('relief : repli sur topg PISM')
    with gzip.open(os.path.join(PUB, 'relief.bin.gz'), 'wb', compresslevel=9) as f:
        f.write(np.clip(np.round(relief), -32768, 32767).astype('<i2').tobytes())
    meta['relief'] = {'fichier': 'relief.bin.gz', 'nx': nxr, 'ny': nyr, 'dx': RES_RELIEF,
                      'disposition': 'i16 mètres, [ny][nx], rangée 0 = sud'}


def main():
    try:
        meta, crs, ouest, sud, lx, ly, topg = preparer_glace()
        preparer_relief(meta, crs, ouest, sud, lx, ly, topg)
        with open(os.path.join(PUB, 'meta.json'), 'w') as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        for n in os.listdir(PUB):
            note('sortie', n, os.path.getsize(os.path.join(PUB, n)), 'octets')
        note('TERMINÉ')
    except SystemExit:
        note(traceback.format_exc())
        ecrire_journal()
        raise
    except Exception:
        note(traceback.format_exc())
        ecrire_journal()
        sys.exit(1)
    ecrire_journal()


if __name__ == '__main__':
    main()
