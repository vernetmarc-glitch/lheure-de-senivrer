"""Glaciers du dernier cycle (120 ka → 0) sur la fenêtre du film des Alpes.

Source : Seguinot et al. 2018, The Cryosphere 12, 3265–3285, simulation PISM de
référence à 1 km (forçage EPICA, précipitations paléo réduites), fichier
alpcyc.1km.epic.pp.ex.1ka.nc (Zenodo, enregistrement 7802275), comme le chantier S8.
Épaisseur de glace rééchantillonnée (bilinéaire) sur la grille du film : azimutale
équidistante centrée sur Grenoble, 204,8 km, 256² mailles de 800 m, ligne 0 = nord.
La fenêtre S8 (150 km) ne couvre pas la mienne : on repart du fichier source.

Sorties (donnees/) : glace.bin.gz (épaisseur u8 256², v = 255·√(e/2500 m), glace ⇔ v ≥ 6),
vitesses.bin.gz (vitesses de surface est et nord, int8 128², v = 127·signe·√(|u|/2000 m/a)),
moraines.bin.gz (moraines médianes u8 512², 255 = moraine, méthode de S8 appliquée aux
données publiées), toutes en différences mod 256 d'une tranche à la suivante ;
glace.json (âges, aires, codage, source). Ne tourne que dans le workflow.
"""
import gzip, json, os, subprocess
import numpy as np
from scipy.ndimage import map_coordinates
from pyproj import CRS, Transformer

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app", "public", "labo", "alpes", "donnees")
LAT0, LON0, N, PAS = 45.188, 5.724, 256, 800.0
NOM = "alpcyc.1km.epic.pp.ex.1ka.nc"
URL = f"https://zenodo.org/records/7802275/files/{NOM}?download=1"
SEUIL, EMAX, VMAX, NV = 1.0, 2500.0, 2000.0, 128


def agrandir(a, n):
    m = a.shape[0]
    c = np.clip((np.arange(n) + 0.5) * m / n - 0.5, 0, m - 1)
    i0 = np.floor(c).astype(int); i1 = np.minimum(i0 + 1, m - 1); w = c - i0
    a = a[i0] * (1 - w)[:, None] + a[i1] * w[:, None]
    return a[:, i0] * (1 - w)[None, :] + a[:, i1] * w[None, :]


def publies(vg, vu, vv):
    """Champs tels que la page et les contrôles les relisent (256², m et m/a ; v vers le nord)."""
    e = (vg.astype(np.float64) / 255) ** 2 * EMAX * (vg >= 6)
    dq = lambda q: np.sign(q) * (q.astype(np.float64) / 127) ** 2 * VMAX
    return e, agrandir(dq(vu), N), agrandir(dq(vv), N)


def delta(a):
    return (np.diff(a.astype(np.int16), axis=0, prepend=0) % 256).astype(np.uint8)


def crs_de(ds):
    for v in [ds] + [ds.variables[k] for k in ds.variables]:
        for a in ("proj4", "proj4text", "crs_wkt", "spatial_ref"):
            if a in getattr(v, "ncattrs", lambda: [])():
                try:
                    return CRS.from_user_input(getattr(v, a))
                except Exception:
                    pass
    return CRS.from_epsg(32632)


def main():
    from netCDF4 import Dataset
    f = os.path.join("/tmp", NOM)
    for essai in range(10):                      # Zenodo coupe parfois : on reprend où on en était
        r = subprocess.run(["curl", "-L", "--fail", "-C", "-", "--retry", "6", "--retry-all-errors",
                            "--retry-delay", "10", "-o", f, URL])
        if r.returncode in (0, 33) and os.path.getsize(f) > 4e8:
            break
    else:
        raise SystemExit("téléchargement PISM incomplet")
    ds = Dataset(f)
    crs = crs_de(ds)
    print("projection", crs.to_string()[:80], flush=True)
    x = np.asarray(ds.variables["x"][:], "f8"); y = np.asarray(ds.variables["y"][:], "f8")
    if getattr(ds.variables["x"], "units", "m").startswith("km"):
        x, y = x * 1e3, y * 1e3
    tn = "time" if "time" in ds.variables else "age"
    tv = np.asarray(ds.variables[tn][:], "f8"); u = getattr(ds.variables[tn], "units", "")
    if "sec" in u:
        tv = tv / (365.0 * 86400)
    elif u.startswith("ka") or "kyr" in u:
        tv = tv * 1000
    ages = np.round(tv if tn == "age" else -tv).astype(int)
    print("âges", ages[:3], ages[-3:], flush=True)
    tr = Transformer.from_crs(f"+proj=aeqd +lat_0={LAT0} +lon_0={LON0} +datum=WGS84 +units=m", crs, always_xy=True)
    c = (np.arange(N) + 0.5) * PAS - N * PAS / 2
    X, Y = np.meshgrid(c, -c)
    px, py = tr.transform(X, Y)
    col = (px - x[0]) / (x[1] - x[0]); row = (py - y[0]) / (y[1] - y[0])
    i0, i1 = int(max(np.floor(row.min()) - 2, 0)), int(min(np.ceil(row.max()) + 3, len(y)))
    j0, j1 = int(max(np.floor(col.min()) - 2, 0)), int(min(np.ceil(col.max()) + 3, len(x)))
    vt = ds.variables["thk"]
    vux = next(ds.variables[k] for k in ("uvelsurf", "u_surf", "usurf_vel") if k in ds.variables)
    vvy = next(ds.variables[k] for k in ("vvelsurf", "v_surf", "vsurf_vel") if k in ds.variables)
    fv = 365.0 * 86400 if ("s-1" in getattr(vux, "units", "") or "m/s" in getattr(vux, "units", "")) else 1.0
    # composantes est / nord de la projection UTM vers ma grille (rotation locale)

    pa = tr.transform(0.0, 0.0); pb = tr.transform(1000.0, 0.0)
    rot = np.arctan2(pb[1] - pa[1], pb[0] - pa[0])          # angle de mon axe est dans l'UTM
    xy = vt.dimensions[-1] == "y"
    ordre = np.argsort(-ages)
    ages = [int(a) for a in ages[ordre] if 0 <= a <= 120000]
    out = np.zeros((len(ages), N, N), np.uint8); aires = []
    UQ = np.zeros((len(ages), NV, NV), np.int8); VQ = np.zeros_like(UQ)
    cv_ = (np.arange(NV) + 0.5) * (N * PAS / NV) - N * PAS / 2
    XV, YV = np.meshgrid(cv_, -cv_)
    pxv, pyv = tr.transform(XV, YV)
    colv = (pxv - x[0]) / (x[1] - x[0]); rowv = (pyv - y[0]) / (y[1] - y[0])
    def lire(var, t):
        a = var[t]
        a = np.ma.filled(a.astype("f8"), 0) if np.ma.isMaskedArray(a) else np.asarray(a, "f8")
        return np.nan_to_num(a.T if xy else a)
    for k, a in enumerate(ages):
        t = int(np.where(np.round(tv if tn == "age" else -tv).astype(int) == a)[0][0])
        e = vt[t]
        e = np.ma.filled(e.astype("f8"), 0) if np.ma.isMaskedArray(e) else np.asarray(e, "f8")
        if xy:
            e = e.T
        e = np.nan_to_num(e[i0:i1, j0:j1])
        m = map_coordinates(e, [row - i0, col - j0], order=1, mode="constant", cval=0.0)
        v = np.round(255 * np.sqrt(np.clip(m, 0, EMAX) / EMAX))
        v = np.where(m >= SEUIL, np.maximum(v, 6), 0)
        out[k] = v.astype(np.uint8)
        ue, vn = lire(vux, t) * fv, lire(vvy, t) * fv
        gt = map_coordinates(lire(vt, t), [rowv, colv], order=1, mode="constant", cval=0.0)
        ue = map_coordinates(ue, [rowv, colv], order=1, mode="constant", cval=0.0)
        vn = map_coordinates(vn, [rowv, colv], order=1, mode="constant", cval=0.0)
        ce, se = np.cos(rot), np.sin(rot)
        ve, vno = ue * ce + vn * se, -ue * se + vn * ce
        q = lambda w: np.round(127 * np.sign(w) * np.sqrt(np.clip(np.abs(w), 0, VMAX) / VMAX)) * (gt >= SEUIL)
        UQ[k] = q(ve).astype(np.int8); VQ[k] = q(vno).astype(np.int8)
        aires.append(float((m >= SEUIL).sum() * (PAS / 1000) ** 2))
    import sys
    sys.path.insert(0, ICI)
    import moraines as MOR
    MO = np.zeros((len(ages), 2 * N, 2 * N), np.uint8)
    for k in range(len(ages)):
        e, u_, v_ = publies(out[k], UQ[k], VQ[k])
        if (e >= SEUIL).any():
            MO[k] = MOR.moraines(e, u_, -v_) * 255          # lignes : nord en haut
    with gzip.open(os.path.join(DON, "glace.bin.gz"), "wb", 9) as g:
        g.write(delta(out).tobytes())
    with gzip.open(os.path.join(DON, "vitesses.bin.gz"), "wb", 9) as g:
        g.write(delta(UQ.view(np.uint8)).tobytes() + delta(VQ.view(np.uint8)).tobytes())
    with gzip.open(os.path.join(DON, "moraines.bin.gz"), "wb", 9) as g:
        g.write(delta(MO).tobytes())
    json.dump({"ages_ans": ages, "n": N, "pas_m": PAS, "aires_km2": aires, "e_max_m": EMAX, "seuil_m": SEUIL,
               "n_v": NV, "v_max_m_a": VMAX, "n_moraines": 2 * N,
               "codage": "tous : [nt][n][n], ligne 0 = nord, différences mod 256 d'une tranche à la suivante ; "
                         "glace u8, v = 255·√(e/e_max), glace ⇔ v ≥ 6 ; vitesses int8 n_v² (est puis nord), "
                         "w = signe·(v/127)²·v_max, agrandies en bilinéaire aux centres ; moraines u8, 255 = moraine",
               "source": "Seguinot et al. 2018, The Cryosphere 12, 3265–3285 — PISM 1 km, EPICA, précipitations paléo réduites (alpcyc.1km.epic.pp.ex.1ka.nc, Zenodo 7802275)"},
              open(os.path.join(DON, "glace.json"), "w"), ensure_ascii=False)
    print("glace :", out.shape, "aire max", max(aires), "km² à", ages[int(np.argmax(aires))], "ans", flush=True)


if __name__ == "__main__":
    main()
