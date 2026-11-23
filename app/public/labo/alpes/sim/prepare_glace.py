"""Glaciers du dernier cycle (120 ka → 0) sur la fenêtre du film des Alpes.

Source : Seguinot et al. 2018, The Cryosphere 12, 3265–3285, simulation PISM de
référence à 1 km (forçage EPICA, précipitations paléo réduites), fichier
alpcyc.1km.epic.pp.ex.1ka.nc (Zenodo, enregistrement 7802275), comme le chantier S8.
Épaisseur de glace rééchantillonnée (bilinéaire) sur la grille du film : azimutale
équidistante centrée sur Grenoble, 204,8 km, 256² mailles de 800 m, ligne 0 = nord.
La fenêtre S8 (150 km) ne couvre pas la mienne : on repart du fichier source.

Sortie : donnees/glace.bin.gz (u8, [nt][256][256], v = 255·√(e/2500 m), glace ⇔ e ≥ 1 m ⇔ v ≥ 6)
et donnees/glace.json (âges, aires, source). Ne tourne que dans le workflow.
"""
import gzip, json, os, subprocess
import numpy as np
from scipy.ndimage import map_coordinates
from pyproj import CRS, Transformer

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(ICI, "..", "donnees")
LAT0, LON0, N, PAS = 45.188, 5.724, 256, 800.0
NOM = "alpcyc.1km.epic.pp.ex.1ka.nc"
URL = f"https://zenodo.org/records/7802275/files/{NOM}?download=1"
SEUIL, EMAX = 1.0, 2500.0


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
    if not os.path.exists(f):
        subprocess.run(["curl", "-L", "--fail", "--retry", "6", "--retry-delay", "10", "-o", f, URL], check=True)
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
    xy = vt.dimensions[-1] == "y"
    ordre = np.argsort(-ages)
    ages = [int(a) for a in ages[ordre] if 0 <= a <= 120000]
    out = np.zeros((len(ages), N, N), np.uint8); aires = []
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
        aires.append(float((m >= SEUIL).sum() * (PAS / 1000) ** 2))
    with gzip.open(os.path.join(DON, "glace.bin.gz"), "wb", 9) as g:
        g.write(out.tobytes())
    json.dump({"ages_ans": ages, "n": N, "pas_m": PAS, "aires_km2": aires, "e_max_m": EMAX, "seuil_m": SEUIL,
               "codage": "u8 [nt][n][n], ligne 0 = nord, v = 255·√(e/e_max), glace ⇔ v ≥ 6",
               "source": "Seguinot et al. 2018, The Cryosphere 12, 3265–3285 — PISM 1 km, EPICA, précipitations paléo réduites (alpcyc.1km.epic.pp.ex.1ka.nc, Zenodo 7802275)"},
              open(os.path.join(DON, "glace.json"), "w"), ensure_ascii=False)
    print("glace :", out.shape, "aire max", max(aires), "km² à", ages[int(np.argmax(aires))], "ans", flush=True)


if __name__ == "__main__":
    main()
