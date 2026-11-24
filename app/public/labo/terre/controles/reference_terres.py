"""Référence indépendante des terres actuelles pour le contrôle « aujourd'hui » :
Natural Earth 1:50 m (polygones de terres, domaine public), rastérisés en
équirectangulaire 1440 × 720 (0,25°), pixel (i, j) centré en
lon = -180 + (i + 0,5)·0,25°, lat = 90 - (j + 0,5)·0,25°.
Indépendante des PaleoDEM (qui sont dérivés d'ETOPO) : on compare deux sources.

Usage : python3 reference_terres.py [chemin du geojson]  (sinon téléchargé sur GitHub)
"""
import json, sys, urllib.request, pathlib
from PIL import Image, ImageDraw
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson"
W, H, SUR = 1440, 720, 4          # sur-échantillonnage 4× puis moyenne -> seuil 50 %
ici = pathlib.Path(__file__).parent
src = sys.argv[1] if len(sys.argv) > 1 else None
d = json.load(open(src)) if src else json.load(urllib.request.urlopen(URL))
img = Image.new("L", (W * SUR, H * SUR), 0); dr = ImageDraw.Draw(img)
def px(c): return [((x + 180) / 360 * W * SUR, (90 - y) / 180 * H * SUR) for x, y in c]
for f in d["features"]:
    g = f["geometry"]; polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poly in polys:
        dr.polygon(px(poly[0]), fill=255)
        for trou in poly[1:]: dr.polygon(px(trou), fill=0)
img = img.resize((W, H), Image.BOX).point(lambda v: 255 if v >= 128 else 0)
img.save(ici / "terres-actuelles-ne50m.png", optimize=True)
import numpy as np
a = np.asarray(img) > 0; lat = 90 - (np.arange(H) + .5) * 180 / H
w = np.cos(np.radians(lat))[:, None] * np.ones((1, W))
print("part des terres (aire) :", (a * w).sum() / w.sum())
