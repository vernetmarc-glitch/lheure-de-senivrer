"""Civilisations et empires (N38, D-50) — tourne sur le runner GitHub.

Usage : python civilisations.py <cache> <dossier de sortie donnees/civ> <intermédiaires>

- Cliopatria (Seshat ; Bennett et al. 2025, Sci. Data 12, 247) : 3400 av. J.-C. → 2024,
  GeoJSON des entités politiques (Name, FromYear, ToYear, Area, Wikidata).
- Avant −3400 (et là où Cliopatria ne dit rien) : foyers néolithiques de prepa/neolithique.csv,
  disques aux contours flous (hypothèse).
- Carte « identifiant d'entité » à 0,25° (1440 × 720, uint16) par pas de temps ; les plus
  petites entités recouvrent les plus grandes ; paquets de 8 pas, gzip.
- Noms français : libellés Wikidata (fr), sinon le nom Cliopatria.
- Couleurs : coloriage glouton du graphe des voisinages (toutes époques), ΔE CIE76 ≥ 30
  entre voisines.
- Étiquettes : par pas et par entité, point le plus intérieur de sa plus grande composante
  (transformée de distance), aire en km².
"""
import csv, gzip, io, json, math, os, pathlib, subprocess, sys, time, urllib.request, zipfile
import numpy as np
from scipy import ndimage

CACHE = pathlib.Path(sys.argv[1]); CACHE.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
INTER = pathlib.Path(sys.argv[3])
ICI = pathlib.Path(__file__).resolve().parent
W, H, PAS = 1440, 720, 0.25


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ Cliopatria
zp = CACHE / 'cliopatria.geojson.zip'
if not zp.exists():
    d = CACHE / 'clio'
    subprocess.run(['git', 'clone', '-q', '--depth', '1', 'https://github.com/Seshat-Global-History-Databank/cliopatria', str(d)], check=True)
    (d / 'cliopatria.geojson.zip').rename(zp)
with zipfile.ZipFile(zp) as z:
    nom = [n for n in z.namelist() if n.endswith('.geojson')][0]
    gj = json.loads(z.read(nom))
feats = [f for f in gj['features'] if f.get('geometry') and f['properties'].get('Type', 'POLITY') == 'POLITY']
log('Cliopatria :', nom, len(feats), 'enregistrements')

# ------------------------------------------------------------------ entités
entites = {}      # nom -> dict
def entite(nom, **kw):
    if nom not in entites:
        entites[nom] = dict(id=len(entites) + 1, nom=nom, debut=10 ** 9, fin=-10 ** 9, **kw)
    return entites[nom]
for f in feats:
    p = f['properties']
    e = entite(p['Name'], wikidata=p.get('Wikidata') or '', source='Cliopatria (Seshat)', flou=False)
    e['debut'] = min(e['debut'], int(p['FromYear'])); e['fin'] = max(e['fin'], int(p['ToYear']))
neo = []
with open(ICI / 'neolithique.csv', encoding='utf-8') as fh:
    for r in csv.DictReader([l for l in fh if not l.startswith('#')], delimiter=';'):
        e = entite(r['nom'], wikidata='', source=r['source'], flou=True)
        e['debut'], e['fin'] = int(r['debut']), int(r['fin'])
        neo.append(dict(r, id=e['id'], lon=float(r['lon']), lat=float(r['lat']), rayon=float(r['rayon_km']),
                        debut=int(r['debut']), fin=int(r['fin'])))
log(len(entites), 'entités dont', len(neo), 'foyers néolithiques')

# ------------------------------------------------------------------ noms français (Wikidata)
qids = sorted({e['wikidata'] for e in entites.values() if e['wikidata'].startswith('Q')})
fr = {}
for k in range(0, len(qids), 50):
    u = 'https://www.wikidata.org/w/api.php?action=wbgetentities&props=labels&languages=fr&format=json&ids=' + '|'.join(qids[k:k + 50])
    for essai in range(3):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'chantier-cartographie/1.0 (python-urllib)'})
            d = json.loads(urllib.request.urlopen(req, timeout=60).read())
            for q, v in d.get('entities', {}).items():
                lab = v.get('labels', {}).get('fr', {}).get('value')
                if lab:
                    fr[q] = lab
            break
        except Exception as ex:
            log('  wikidata', ex); time.sleep(3)
for e in entites.values():
    e['nom_fr'] = fr.get(e['wikidata'], e['nom'])
log('noms français :', len(fr), '/', len(qids))

# ------------------------------------------------------------------ pas de temps
pas = list(range(-10000, -3400, 200)) + list(range(-3400, -1000, 50)) + list(range(-1000, 1500, 25)) + \
      list(range(1500, 1900, 10)) + list(range(1900, 2025, 5))
TEMOINS = [-9000, -5000, -2500, -500, 100, 800, 1279, 1500, 1900, 2024]   # dates témoins des contrôles
pas = sorted(set(pas) | set(TEMOINS))
log(len(pas), 'pas de temps')

from rasterio import features as rf
from rasterio.transform import from_origin
T = from_origin(-180, 90, PAS, PAS)
LAT = 90 - (np.arange(H) + 0.5) * PAS
LON = -180 + (np.arange(W) + 0.5) * PAS
AIRE = (111.32 * PAS) ** 2 * np.cos(np.radians(LAT))[:, None] * np.ones((1, W))
LO2, LA2 = np.meshgrid(LON, LAT)

def disque(n):
    la0, lo0 = math.radians(n['lat']), math.radians(n['lon'])
    la, lo = np.radians(LA2), np.radians(LO2)
    d = 6371 * np.arccos(np.clip(np.sin(la0) * np.sin(la) + np.cos(la0) * np.cos(la) * np.cos(lo - lo0), -1, 1))
    return d <= n['rayon']

par_annee = {}
for f in feats:
    p = f['properties']
    par_annee.setdefault((int(p['FromYear']), int(p['ToYear'])), []).append(f)

voisins = {}
etiquettes = []
cartes = []
for k, an in enumerate(pas):
    m = np.zeros((H, W), np.uint16)
    # néolithique d'abord (sous Cliopatria), du plus grand au plus petit
    for n in sorted([n for n in neo if n['debut'] <= an <= n['fin']], key=lambda n: -n['rayon']):
        m[disque(n)] = n['id']
    act = [f for (a0, a1), fs in par_annee.items() if a0 <= an <= a1 for f in fs]
    act.sort(key=lambda f: (-float(f['properties'].get('Area') or 0), f['properties']['Name']))   # ordre total : égalités départagées par le nom
    if act:
        r = rf.rasterize(((f['geometry'], entites[f['properties']['Name']]['id']) for f in act),
                         out_shape=(H, W), transform=T, fill=0, dtype='uint16')
        m = np.where(r > 0, r, m)
    cartes.append(m)
    # voisinages
    for a, b in [(m[:, :-1], m[:, 1:]), (m[:-1, :], m[1:, :])]:
        diff = (a != b) & (a > 0) & (b > 0)
        for x, y in set(zip(a[diff].tolist(), b[diff].tolist())):
            voisins.setdefault(x, set()).add(y); voisins.setdefault(y, set()).add(x)
    # étiquettes
    et = []
    for i in np.unique(m[m > 0]):
        lab, nb = ndimage.label(m == i)
        if nb == 0:
            continue
        aires = ndimage.sum(AIRE, lab, index=np.arange(1, nb + 1))
        grand = int(np.argmax(aires)) + 1
        if aires.sum() < 15000:
            continue
        dt = ndimage.distance_transform_edt(lab == grand)
        y, x = np.unravel_index(np.argmax(dt), dt.shape)
        et.append([int(i), round(float(LON[x]), 2), round(float(LAT[y]), 2), round(float(aires.sum()))])
    et.sort(key=lambda t: -t[3])
    etiquettes.append(et)
    if k % 20 == 0:
        log(f'  {an} : {len(np.unique(m)) - 1} entités')

# ------------------------------------------------------------------ couleurs
def lab(rgb):
    c = np.asarray(rgb, dtype=float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]]) / np.array([0.95047, 1, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])
import colorsys
palette = []
for L in (0.50, 0.64):          # couleurs vives (relecture : les teintes claires viraient au blanc)
    for h in range(12):
        r, g, b = colorsys.hls_to_rgb((h / 12 + (0.04 if L > 0.6 else 0)) % 1, L, 1.0)
        palette.append([int(255 * r), int(255 * g), int(255 * b)])
PL = [lab(c) for c in palette]
couleur = {}
ordre = sorted(entites.values(), key=lambda e: -len(voisins.get(e['id'], ())))
for e in ordre:
    vs = [couleur[v] for v in voisins.get(e['id'], ()) if v in couleur]
    best, bscore = 0, -1
    for ci in range(len(palette)):
        dmin = min([np.linalg.norm(PL[ci] - PL[v]) for v in vs] or [999])
        score = min(dmin, 60) + 0.001 * ((e['id'] * 7 + ci * 13) % 97)   # au-delà de 60, varier
        if score > bscore:
            best, bscore = ci, score
    couleur[e['id']] = best
mauvais = sum(1 for a, vs in voisins.items() for b in vs if np.linalg.norm(PL[couleur[a]] - PL[couleur[b]]) < 30) // 2
log('paires voisines à ΔE < 30 :', mauvais, '/', sum(len(v) for v in voisins.values()) // 2)

# ------------------------------------------------------------------ paquets
GROUPE = 8
for g in range(0, len(pas), GROUPE):
    with gzip.open(OUT / f'civ_{g // GROUPE:03d}.u16.gz', 'wb', compresslevel=9) as fz:
        for m in cartes[g:g + GROUPE]:
            fz.write(m.tobytes())
taille = sum(p.stat().st_size for p in OUT.glob('civ_*.u16.gz'))
meta = {'w': W, 'h': H, 'pas_deg': PAS, 'groupe': GROUPE, 'annees': pas, 'octets': taille,
        'entites': [{'id': e['id'], 'nom': e['nom_fr'], 'nom_en': e['nom'], 'debut': e['debut'], 'fin': e['fin'],
                     'couleur': palette[couleur[e['id']]], 'flou': e['flou'], 'source': e['source']}
                    for e in sorted(entites.values(), key=lambda e: e['id'])],
        'etiquettes': etiquettes,
        'sources': 'Cliopatria v0.2.1 (Seshat Global History Databank ; Bennett et al. 2025) ; foyers néolithiques : prepa/neolithique.csv'}
(OUT / 'civ_meta.json').write_text(json.dumps(meta, ensure_ascii=False, separators=(',', ':')))
log('paquet :', len(pas), 'pas,', taille / 1e6, 'Mo de cartes,', (OUT / 'civ_meta.json').stat().st_size / 1e6, 'Mo de méta')

# ------------------------------------------------------------------ référence des États actuels (Natural Earth)
try:
    u = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson'
    ne = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'python-urllib'}), timeout=120).read())
    shp = [(f['geometry'], k + 1) for k, f in enumerate(ne['features']) if f.get('geometry')]
    r = rf.rasterize(shp, out_shape=(H, W), transform=T, fill=0, dtype='uint16')
    np.savez_compressed(INTER / 'etats_actuels_ne50m.npz', id=r,
                        noms=np.array([f['properties'].get('NAME_FR') or f['properties'].get('NAME') for f in ne['features']]),
                        source=u)
    log('Natural Earth 50 m :', len(shp), 'pays')
except Exception as ex:
    log('Natural Earth :', ex)
