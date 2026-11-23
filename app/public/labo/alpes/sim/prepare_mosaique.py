"""Mosaïque Sentinel-2 sans nuages sur la fenêtre de 204,8 km centrée sur Grenoble.

Source : « Sentinel-2 cloudless » d'EOX IT Services GmbH (https://s2maps.eu), contient des
données Copernicus Sentinel modifiées. Service WMS public (EPSG:4326), couche la plus
récente disponible. Reprojection bilinéaire sur la grille du relief (azimutale
équidistante centrée sur Grenoble, nord en haut), 2048 × 2048 mailles de 100 m.

Sortie : donnees/mosaique_2048.jpg et sim/mosaique.json (couche, attribution).
Ne tourne que dans le workflow chantier-alpes (bac à sable : EOX non joignable).
"""
import io, json, os, urllib.request
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
from pyproj import Transformer

LAT0, LON0 = 45.188, 5.724
N, PAS = 2048, 100.0
ICI = os.path.dirname(os.path.abspath(__file__))
COUCHES = ["s2cloudless-2024", "s2cloudless-2023", "s2cloudless-2022", "s2cloudless-2021",
           "s2cloudless-2020", "s2cloudless-2019", "s2cloudless-2018", "s2cloudless"]
DEG_PX = 0.0007


def getmap(couche, lon0, lat0, lon1, lat1, w, h):
    url = ("https://tiles.maps.eox.at/wms?service=WMS&request=GetMap&version=1.1.1"
           f"&layers={couche}&styles=&srs=EPSG:4326&bbox={lon0},{lat0},{lon1},{lat1}"
           f"&width={w}&height={h}&format=image/jpeg")
    data = urllib.request.urlopen(url, timeout=180).read()
    im = Image.open(io.BytesIO(data))
    if im.format != "JPEG":
        raise RuntimeError(data[:300])
    return np.asarray(im.convert("RGB"))


def main():
    tr = Transformer.from_crs(f"+proj=aeqd +lat_0={LAT0} +lon_0={LON0} +datum=WGS84 +units=m",
                              "EPSG:4326", always_xy=True)
    demi = N * PAS / 2
    c = (np.arange(N) + 0.5) * PAS - demi
    X, Y = np.meshgrid(c, -c)
    lon, lat = tr.transform(X, Y)
    L0, L1 = lon.min() - 0.01, lon.max() + 0.01
    B0, B1 = lat.min() - 0.01, lat.max() + 0.01
    nx = ny = 3
    wt = int(np.ceil((L1 - L0) / nx / DEG_PX)); ht = int(np.ceil((B1 - B0) / ny / DEG_PX))
    for couche in COUCHES:
        try:
            getmap(couche, 5.7, 45.1, 5.8, 45.2, 64, 64)
            break
        except Exception as e:
            print("couche indisponible", couche, str(e)[:120], flush=True)
    print("couche", couche, flush=True)
    img = np.zeros((ny * ht, nx * wt, 3), np.uint8)
    dl, db = (L1 - L0) / nx, (B1 - B0) / ny
    for i in range(ny):          # i = 0 en haut (nord)
        for j in range(nx):
            t = getmap(couche, L0 + j * dl, B1 - (i + 1) * db, L0 + (j + 1) * dl, B1 - i * db, wt, ht)
            img[i * ht:(i + 1) * ht, j * wt:(j + 1) * wt] = t
            print(f"  tuile {i},{j} {t.shape}", flush=True)
    col = (lon - L0) / (L1 - L0) * img.shape[1] - 0.5
    row = (B1 - lat) / (B1 - B0) * img.shape[0] - 0.5
    out = np.stack([map_coordinates(img[..., k].astype(np.float32), [row, col], order=1, mode="nearest")
                    for k in range(3)], -1)
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    dest = os.path.join(ICI, "..", "donnees")
    os.makedirs(dest, exist_ok=True)
    Image.fromarray(out).save(os.path.join(dest, "mosaique_2048.jpg"), quality=88, optimize=True)
    annee = couche.split("-")[1] if "-" in couche else "2016"
    json.dump({"couche": couche, "attribution": f"Sentinel-2 cloudless – https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data {annee})"},
              open(os.path.join(ICI, "mosaique.json"), "w"), ensure_ascii=False)
    print("mosaïque", out.shape, out.reshape(-1, 3).mean(0), flush=True)


if __name__ == "__main__":
    main()
