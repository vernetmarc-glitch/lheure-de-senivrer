"""Empaquette les catalogues de galaxies (catalogue.py) pour la page.
Usage : python3 sim/tng/paquet_catalogue.py DOSSIER SORTIE.bin
Format : u32 longueur d'en-tête JSON {epoques:[{snap,a,n}], unite}, puis par époque :
  x, y int16 [n] (ckpc/h, relatifs à la Voie lactée) · logm u8 [n] (×20) · sf u8 [n]
"""
import glob, json, sys
import numpy as np
A = {}  # facteur d'échelle de chaque instantané (redshifts TNG)
Z = {99: 0.0, 91: 0.1, 84: 0.2, 78: 0.3, 72: 0.4, 67: 0.5, 59: 0.7, 50: 1.0, 40: 1.5, 33: 2.0, 25: 3.0, 21: 4.0, 17: 5.0, 13: 6.0}
ep, blocs = [], []
for f in sorted(glob.glob(f"{sys.argv[1]}/cat-*.npz")):
    sn = int(f[-7:-4]); d = np.load(f)
    o = np.argsort(-d["logm"])
    x = np.clip(np.round(d["x"][o]), -32767, 32767).astype(np.int16); y = np.clip(np.round(d["y"][o]), -32767, 32767).astype(np.int16)
    lm = np.clip(np.round(d["logm"][o] * 20), 0, 255).astype(np.uint8); sf = d["sf"][o].astype(np.uint8)
    ep.append({"snap": sn, "a": round(1 / (1 + Z[sn]), 5), "n": int(len(x))}); blocs.append((x, y, lm, sf))
ordre = np.argsort([e["a"] for e in ep]); ep = [ep[i] for i in ordre]; blocs = [blocs[i] for i in ordre]
h = json.dumps({"epoques": ep, "unite": "ckpc/h"}).encode()
with open(sys.argv[2], "wb") as f:
    f.write(np.uint32(len(h)).tobytes()); f.write(h)
    if (4 + len(h)) % 2: f.write(b"\0")
    for x, y, lm, sf in blocs: f.write(x.tobytes()); f.write(y.tobytes()); f.write(lm.tobytes()); f.write(sf.tobytes())
print(ep)
