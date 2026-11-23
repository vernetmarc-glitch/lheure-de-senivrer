"""Préparation (runner GitHub, pyGPlates) du modèle de plaques de Cao et al. 2024.

Sorties :
  - <inter>/cao.npz :
      statiques  : indice du polygone statique couvrant chaque pixel actuel (grille de la
                   page, 1440 × 720, pixel (i, j) centré lon -180+(i+.5)/4, lat 90-(j+.5)/4),
      statiques_table : (plaque, début Ma, fin Ma) par polygone,
      continents / continents_table : idem pour les polygones de croûte continentale,
      ids, q : rotations totales (quaternions x, y, z, w) de chaque plaque, 0–1800 Ma par Ma ;
  - <inter>/topo.npz (lourd, en cache) : plaque de chaque cellule de 0,5° en coordonnées
    paléo, tous les 2 Ma de 0 à 1800 Ma, d'après les frontières topologiques résolues.

Usage : python3 preparer_cao.py <sources> <intermédiaires lourds>
"""
import sys, pathlib, time
import numpy as np
import pygplates
from PIL import Image, ImageDraw

SRC = pathlib.Path(sys.argv[1]); INTER_L = pathlib.Path(sys.argv[2]); INTER_L.mkdir(parents=True, exist_ok=True)
ICI = pathlib.Path(__file__).resolve().parent
T0 = time.time(); TMAX = 1800


def log(*a): print(f"[{time.time()-T0:7.1f} s]", *a, flush=True)


def quaternion(rot):
    if rot.represents_identity_rotation(): return (0.0, 0.0, 0.0, 1.0)
    pole, ang = rot.get_euler_pole_and_angle()
    x, y, z = pole.to_xyz(); s = np.sin(ang / 2)
    return (x * s, y * s, z * s, np.cos(ang / 2))


racine = SRC / "cao"
fichiers = [p for p in racine.rglob("*") if p.is_file() and "__MACOSX" not in str(p)]
rots = [p for p in fichiers if p.suffix.lower() == ".rot"]
gpml = [p for p in fichiers if p.suffix.lower() in (".gpml", ".gpmlz")]
log("fichiers .rot :", *[f"\n  {p.relative_to(SRC)}" for p in rots])
classes = {}
for p in gpml:
    try:
        fc = pygplates.FeatureCollection(str(p))
    except Exception as e:
        log("illisible", p.name, e); continue
    types = {}
    for f in fc:
        k = f.get_feature_type().get_name(); types[k] = types.get(k, 0) + 1
    classes[p] = (fc, types)
    log(f"{p.relative_to(SRC)} : {len(fc)} objets ; " + ", ".join(f"{k} {v}" for k, v in sorted(types.items(), key=lambda x: -x[1])[:6]))

nom = lambda p: p.name.lower()
topo = [p for p, (fc, ty) in classes.items() if any(k.startswith("Topological") for k in ty)]
statiques = [p for p in classes if "static" in nom(p)]
continents = [p for p in classes if any(m in nom(p) for m in ("continent", "cob", "craton", "shapes")) and "static" not in nom(p)
              and "coast" not in nom(p)]
log("topologies :", [p.name for p in topo]); log("statiques :", [p.name for p in statiques])
log("continents :", [p.name for p in continents])
if not rots or not topo or not statiques:
    raise SystemExit("modèle incomplet : voir l'inventaire")
rm = pygplates.RotationModel([str(r) for r in rots])

# ---------------------------------------------------------------- rastérisation (grille de la page)
W, H = 1440, 720
wrap = pygplates.DateLineWrapper()


def dessiner(dr, poly, val, W, H):
    try: parts = wrap.wrap(poly, 0.5)
    except TypeError: parts = wrap.wrap(poly)
    for q in parts:
        pts = [((u.get_longitude() + 180) / 360 * W, (90 - u.get_latitude()) / 180 * H) for u in q.get_exterior_points()]
        if len(pts) >= 3: dr.polygon(pts, fill=int(val))


def rasteriser(chemins, titre):
    img = Image.new("I", (W, H), 0); dr = ImageDraw.Draw(img); table = []; n = 0
    for c in chemins:
        for f in classes[c][0]:
            b, e = f.get_valid_time()
            b = 1e4 if pygplates.GeoTimeInstant(b).is_distant_past() else float(b)
            e = 0.0 if pygplates.GeoTimeInstant(e).is_distant_future() else float(e)
            for g in f.get_geometries():
                if not isinstance(g, pygplates.PolygonOnSphere): continue
                n += 1; table.append((f.get_reconstruction_plate_id(), b, e)); dessiner(dr, g, n, W, H)
    a = np.asarray(img, np.int64)
    log(f"{titre} : {n} polygones, couverture {(a > 0).mean()*100:.1f} % des pixels")
    return a.astype(np.int32), np.array(table, np.float64).reshape(-1, 3)


st_r, st_t = rasteriser(statiques, "polygones statiques")
if continents:
    co_r, co_t = rasteriser(continents, "croûte continentale")
else:
    co_r, co_t = np.zeros_like(st_r), np.zeros((0, 3))

# ---------------------------------------------------------------- topologies résolues, 0,5°, tous les 2 Ma
TW, TH = 720, 360
f_topo = INTER_L / "topo.npz"
pids_topo = set()
if f_topo.exists():
    d = np.load(f_topo); grilles = d["g"]; temps = d["t"]; pids_topo = set(np.unique(grilles).tolist())
    log(f"topologies en cache : {len(temps)} instants")
else:
    feats = []
    for c in classes: feats.extend(list(classes[c][0]))
    temps = np.arange(0, TMAX + 1, 2)
    grilles = np.zeros((len(temps), TH, TW), np.uint16)
    for k, t in enumerate(temps):
        snap = pygplates.TopologicalSnapshot(feats, rm, float(t))
        img = Image.new("I", (TW, TH), 0); dr = ImageDraw.Draw(img)
        rts = snap.get_resolved_topologies(resolve_topology_types=pygplates.ResolveTopologyType.boundary)
        for r in sorted(rts, key=lambda r: -r.get_resolved_boundary().get_area()):   # les petites plaques par-dessus
            pid = r.get_feature().get_reconstruction_plate_id(); pids_topo.add(pid)
            dessiner(dr, r.get_resolved_boundary(), pid, TW, TH)
        grilles[k] = np.asarray(img, np.int64).astype(np.uint16)
        if t % 100 == 0:
            log(f"topologies {t} Ma : {len(rts)} plaques, couverture {(grilles[k] > 0).mean()*100:.1f} %")
    np.savez_compressed(f_topo, g=grilles, t=temps)

# ---------------------------------------------------------------- rotations
pids = sorted(set(st_t[:, 0].astype(int)) | set(co_t[:, 0].astype(int)) | {int(p) for p in pids_topo} | {0})
Q = np.zeros((len(pids), TMAX + 1, 4), np.float32)
for i, pid in enumerate(pids):
    for t in range(TMAX + 1):
        Q[i, t] = quaternion(rm.get_rotation(float(t), pid))
log(f"rotations : {len(pids)} plaques × {TMAX+1} Ma")
np.savez_compressed(INTER_L / "cao.npz", statiques=st_r, statiques_table=st_t, continents=co_r,
                    continents_table=co_t, ids=np.array(pids, np.int32), q=Q)
log("fin")
