"""Relief réel des Alpes du Nord autour de Grenoble — préparation du MNT.

Source : Copernicus DEM GLO-90 (© DLR e.V. 2010-2014 et © Airbus Defence and Space
GmbH 2014-2018, fourni dans le cadre du programme Copernicus), dépôt ouvert AWS
(s3://copernicus-dem-90m). Repli : GLO-30, puis SRTM (tuiles « skadi »).

Grille : projection azimutale équidistante centrée sur Grenoble (45,188 N ; 5,724 E),
nord en haut, 204,8 km de côté, 1024 × 1024 mailles de 200 m. Chaque maille est la
moyenne de 4 × 4 échantillons bilinéaires (anticrénelage).

Sortie : sim/reel_1024.npz (altitude en m, float32, ligne 0 = nord).
Ce script ne tourne que dans le workflow chantier-alpes (le bac à sable ne joint pas
les sources).
"""
import gzip, io, os, sys, urllib.request
import numpy as np
from scipy.ndimage import map_coordinates
from pyproj import Transformer

LAT0, LON0 = 45.188, 5.724
N, PAS = 1024, 200.0          # mailles, m
SUR = 4                       # suréchantillonnage
ICI = os.path.dirname(os.path.abspath(__file__))


def tuile_cop(res, la, lo):
    code = {90: "30", 30: "10"}[res]
    nom = f"Copernicus_DSM_COG_{code}_N{la:02d}_00_E{lo:03d}_00_DEM"
    return f"https://copernicus-dem-{res}m.s3.amazonaws.com/{nom}/{nom}.tif"


def lire_tuile(la, lo):
    import rasterio
    for res in (90, 30):
        url = tuile_cop(res, la, lo)
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
            with rasterio.MemoryFile(data) as mf, mf.open() as ds:
                z = ds.read(1).astype(np.float32)
                T = ds.transform
            print(f"  {url.rsplit('/',1)[1]} {z.shape}", flush=True)
            # (col,row) bord de pixel -> lon,lat
            return z, (T.c, T.a, T.f, T.e), f"Copernicus GLO-{res}"
        except Exception as e:
            print(f"  échec {url}: {e}", flush=True)
    url = f"https://s3.amazonaws.com/elevation-tiles-prod/skadi/N{la:02d}/N{la:02d}E{lo:03d}.hgt.gz"
    raw = gzip.decompress(urllib.request.urlopen(url, timeout=120).read())
    n = int(round((len(raw) // 2) ** 0.5))
    z = np.frombuffer(raw, ">i2").reshape(n, n).astype(np.float32)
    z[z < -1000] = np.nan
    d = 1.0 / (n - 1)
    print(f"  SRTM {la} {lo} {z.shape}", flush=True)
    return z, (lo - d / 2, d, la + 1 + d / 2, -d), "SRTM"


def main():
    tr = Transformer.from_crs(
        f"+proj=aeqd +lat_0={LAT0} +lon_0={LON0} +datum=WGS84 +units=m", "EPSG:4326",
        always_xy=True)
    m = N * SUR
    demi = N * PAS / 2
    c = (np.arange(m) + 0.5) * (PAS / SUR) - demi
    X, Y = np.meshgrid(c, -c)               # ligne 0 = nord
    lon, lat = tr.transform(X, Y)
    print("emprise", lat.min(), lat.max(), lon.min(), lon.max(), flush=True)
    out = np.full(lon.shape, np.nan, np.float32)
    sources = set()
    for la in range(int(np.floor(lat.min())), int(np.floor(lat.max())) + 1):
        for lo in range(int(np.floor(lon.min())), int(np.floor(lon.max())) + 1):
            sel = (np.floor(lat) == la) & (np.floor(lon) == lo)
            if not sel.any():
                continue
            z, (x0, dx, y0, dy), src = lire_tuile(la, lo)
            sources.add(src)
            col = (lon[sel] - x0) / dx - 0.5
            row = (lat[sel] - y0) / dy - 0.5
            out[sel] = map_coordinates(z, [row, col], order=1, mode="nearest")
    if np.isnan(out).any():
        print("lacunes:", int(np.isnan(out).sum()), flush=True)
        out = np.where(np.isnan(out), np.nanmean(out), out)
    h = out.reshape(N, SUR, N, SUR).mean(axis=(1, 3)).astype(np.float32)
    print("relief", h.min(), h.max(), h.mean(), flush=True)
    np.savez_compressed(os.path.join(ICI, "reel_1024.npz"), h=h,
                        source=" + ".join(sorted(sources)), lat0=LAT0, lon0=LON0, pas=PAS)


if __name__ == "__main__":
    main()
