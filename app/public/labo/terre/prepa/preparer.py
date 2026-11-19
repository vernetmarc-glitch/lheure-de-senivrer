"""Préparation, étape A (runner GitHub) : intermédiaires compacts tirés des données publiées.

  - rastérisation à 0,1° des polygones statiques PALEOMAP (modèle des PaleoDEM) et
    Merdith 2021, et des polygones de croûte continentale de Merdith 2021 :
    pour chaque pixel actuel, l'indice du polygone (-> plaque, âge d'apparition) ;
  - rotations totales (plaque -> repère absolu) de chaque plaque, à chaque Ma entier,
    en quaternions : PALEOMAP 0–750 Ma, Merdith 0–1000 Ma ;
  - cube des PaleoDEM à 1° (pour le développement local de la cuisson).

Puis, si `cuire.py` est présent, étape B : la cuisson du paquet publié (donnees/),
à partir des PaleoDEM à 0,1°.

Usage : python3 preparer.py <sources> <dossier donnees>
"""
import sys, pathlib, re, time, json, glob
import numpy as np
import pygplates
from PIL import Image, ImageDraw

SRC = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
ICI = pathlib.Path(__file__).resolve().parent
INTER = ICI / "intermediaires"; INTER.mkdir(exist_ok=True)
NX, NY = 3600, 1800                      # 0,1° : pixel (i, j) centré lon -180+(i+.5)/10, lat 90-(j+.5)/10
T0 = time.time()


def age_nc(f):
    """Âge (Ma) tiré du nom d'un PaleoDEM, ex. « Map88_PALEOMAP_6min_..._540Ma.nc »."""
    m = re.findall(r"(\d+(?:\.\d+)?)\s*Ma", pathlib.Path(f).name)
    if not m: raise ValueError(f"âge illisible : {f}")
    return int(round(float(m[-1])))


def log(*a):
    print(f"[{time.time()-T0:7.1f} s]", *a, flush=True)


def trouve(motif, racine=SRC):
    r = sorted(p for p in racine.rglob(motif) if "__MACOSX" not in str(p))
    if not r: raise SystemExit(f"introuvable : {motif}")
    return r[0]


def quaternion(rot):
    if rot.represents_identity_rotation():
        return (0.0, 0.0, 0.0, 1.0)
    pole, ang = rot.get_euler_pole_and_angle()
    x, y, z = pole.to_xyz(); s = np.sin(ang / 2)
    return (x * s, y * s, z * s, np.cos(ang / 2))


def qrot(q, v):
    """Rotation de vecteurs v (..., 3) par quaternions q (..., 4) (x, y, z, w)."""
    u, w = q[..., :3], q[..., 3:4]
    t = 2 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def rasteriser(features, nom):
    """Indice (1..n) du polygone couvrant chaque pixel actuel ; 0 = aucun."""
    img = Image.new("I", (NX, NY), 0); dr = ImageDraw.Draw(img)
    wrap = pygplates.DateLineWrapper()
    table = []   # (plate_id, begin, end)
    n = 0
    for f in features:
        geoms = f.get_geometries() if hasattr(f, "get_geometries") else [f.get_geometry()]
        pid = f.get_reconstruction_plate_id()
        b, e = f.get_valid_time()
        b = 1e4 if pygplates.GeoTimeInstant(b).is_distant_past() else float(b)
        e = float(e) if not pygplates.GeoTimeInstant(e).is_distant_future() else 0.0
        for g in geoms:
            if not isinstance(g, pygplates.PolygonOnSphere):
                continue
            n += 1; table.append((pid, b, e))
            try:
                parts = wrap.wrap(g, 0.5)
            except TypeError:
                parts = wrap.wrap(g)
            for p in parts:
                pts = [((q.get_longitude() + 180) / 360 * NX, (90 - q.get_latitude()) / 180 * NY)
                       for q in p.get_exterior_points()]
                if len(pts) >= 3:
                    dr.polygon(pts, fill=n)
    a = np.asarray(img, dtype=np.int64)
    log(f"{nom} : {n} polygones, {len(set(t[0] for t in table))} plaques, "
        f"couverture {(a > 0).mean()*100:.1f} % des pixels")
    return a.astype(np.uint16), np.array(table, dtype=np.float64).reshape(-1, 3)


def tables_rotations(rotfiles, pids, tmax, nom):
    rm = pygplates.RotationModel([str(r) for r in rotfiles])
    pids = sorted(set(int(p) for p in pids) | {0})
    Q = np.zeros((len(pids), tmax + 1, 4), np.float32)
    for i, pid in enumerate(pids):
        for t in range(tmax + 1):
            Q[i, t] = quaternion(rm.get_rotation(float(t), pid))
    # vérification de la convention : quaternion maison == pygplates
    err = 0.0
    for i, pid in list(enumerate(pids))[:: max(1, len(pids) // 20)]:
        for t in (10, 250, min(tmax, 700)):
            pt = pygplates.PointOnSphere(20.0, 40.0)
            a = np.array((rm.get_rotation(float(t), pid) * pt).to_xyz())
            b = qrot(Q[i, t][None], np.array(pt.to_xyz())[None])[0]
            err = max(err, np.abs(a - b).max())
    log(f"rotations {nom} : {len(pids)} plaques × {tmax+1} Ma ; écart maison/pygplates {err:.2e}")
    assert err < 1e-5, "convention de quaternion fausse"
    return np.array(pids, np.int32), Q


def etape_a():
    # PALEOMAP : le modèle livré avec les PaleoDEM (Scotese PaleoAtlas v3)
    pm_rot = trouve("PALEOMAP_PlateModel.rot", SRC / "paleodem")
    pm_pol = trouve("PALEOMAP_PlatePolygons.gpml", SRC / "paleodem")
    me_dir = trouve("1000_0_rotfile_Merdith_etal.rot", SRC / "merdith").parent.parent
    me_rot = me_dir / "Rotations" / "1000_0_rotfile_Merdith_etal.rot"
    me_sta = trouve("shapes_static_polygons_Merdith_etal.gpml", me_dir)
    me_con = trouve("shapes_continents.gpml", me_dir)
    log("sources :", *[f"\n  {x}" for x in (pm_rot, pm_pol, me_rot, me_sta, me_con)])

    pm_r, pm_t = rasteriser(pygplates.FeatureCollection(str(pm_pol)), "PALEOMAP polygones")
    ms_r, ms_t = rasteriser(pygplates.FeatureCollection(str(me_sta)), "Merdith polygones statiques")
    mc_r, mc_t = rasteriser(pygplates.FeatureCollection(str(me_con)), "Merdith croûte continentale")
    np.savez_compressed(INTER / "partitions.npz", paleomap=pm_r, paleomap_table=pm_t,
                        merdith=ms_r, merdith_table=ms_t, continents=mc_r, continents_table=mc_t)

    pm_ids, pm_q = tables_rotations([pm_rot], pm_t[:, 0], 750, "PALEOMAP")
    me_ids, me_q = tables_rotations([me_rot], set(ms_t[:, 0]) | set(mc_t[:, 0]), 1000, "Merdith")
    np.savez_compressed(INTER / "rotations.npz", paleomap_ids=pm_ids, paleomap_q=pm_q,
                        merdith_ids=me_ids, merdith_q=me_q)

    # cube PaleoDEM 1° (développement local)
    import netCDF4
    fs = sorted(glob.glob(str(SRC / "paleodem" / "**" / "*_1deg_*Ma.nc"), recursive=True))
    fs = [f for f in fs if "__MACOSX" not in f]
    ok = []
    for f in fs:
        try: ok.append((age_nc(f), f))
        except ValueError as e: log(e)
    ok = sorted(dict(ok).items())
    fs = [f for _, f in ok]; ts = [t for t, _ in ok]
    ordre = np.argsort(ts)
    cube = []
    for k in ordre:
        ds = netCDF4.Dataset(fs[k]); z = np.array(ds.variables["z"][:], np.float32)
        lat = np.array(ds.variables["lat"][:]); ds.close()
        if lat[0] < lat[-1]: z = z[::-1]
        cube.append(np.nan_to_num(z, nan=-4000).round().astype(np.int16))
    np.savez_compressed(INTER / "dem1deg.npz", t=np.array(ts)[ordre], z=np.stack(cube))
    log(f"cube 1° : {len(cube)} PaleoDEM, de {min(ts)} à {max(ts)} Ma")
    (INTER / "LISEZMOI.txt").write_text(
        "Intermédiaires de l'étape A (workflow chantier-terre), pour la cuisson et le\n"
        "développement local. Ne pas publier : la page ne lit que ../../donnees/.\n"
        "partitions.npz : indices de polygones à 0,1° (pixel (i,j) centré lon -180+(i+.5)/10,\n"
        "  lat 90-(j+.5)/10), tables (plate_id, début Ma, fin Ma) ;\n"
        "rotations.npz : quaternions (x,y,z,w) plaque -> repère absolu, par Ma entier ;\n"
        "dem1deg.npz : PaleoDEM Scotese & Wright 2018 à 1°, lat décroissante, lon -180..180.\n")


if __name__ == "__main__":
    if not (INTER / "dem1deg.npz").exists() or "--refaire-a" in sys.argv:
        etape_a()
    else:
        log("étape A déjà faite (intermediaires/ présents)")
    if (ICI / "cuire.py").exists():
        sys.path.insert(0, str(ICI))
        import cuire
        cuire.main(SRC, OUT, INTER)
    log("fin")
