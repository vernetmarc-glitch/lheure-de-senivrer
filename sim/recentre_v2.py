"""Recentre les sorties v2 sur la matière de l'observateur : à chaque époque, on retranche le
déplacement moyen des points proches du centre aujourd'hui (rayon R, en fraction de la boîte).
Sans cela, toute la tranche glisse de plusieurs Mpc en remontant le temps et, par rapport à la
case centrale, des bandes en trop et en moins apparaissent à ses bords (retour du 17/11 : traits
droits aux époques jeunes).
Usage : python3 recentre_v2.py <dossier .bin.gz> <sortie .bin.gz> <sortie .txt base64> [R]
"""
import sys, os, gzip, json, base64, numpy as np
SRC, OUTGZ, OUTTXT = sys.argv[1:4]; R = float(sys.argv[4]) if len(sys.argv) > 4 else 0.10
os.makedirs(OUTGZ, exist_ok=True); os.makedirs(OUTTXT, exist_ok=True)
ix = json.load(open(next(f"{SRC}/{f}" for f in os.listdir(SRC) if f.endswith(".json")))); n = ix["n"]
def lit(nom):
    b = gzip.open(f"{SRC}/{nom}.gz").read(); lh = int.from_bytes(b[:4], "little"); o = 4 + lh; o += o % 2
    return b[:o], np.frombuffer(b[o:o + 4 * n], np.int16).reshape(n, 2).astype(np.int32), b[o + 4 * n:]
_, x1, _ = lit(ix["fichiers"][-1])
pres = np.hypot(*(x1 / 60000.0).T) < R
print(ix["etiquette"], "points proches :", int(pres.sum()))
for nom in ix["fichiers"]:
    tete, xy, reste = lit(nom)
    dep = np.round((xy[pres] - x1[pres]).mean(0)).astype(np.int32)
    xy = np.clip(xy - dep, -32767, 32767).astype(np.int16)
    blob = tete + xy.tobytes() + reste
    with gzip.open(f"{OUTGZ}/{nom}.gz", "wb", compresslevel=9) as f: f.write(blob)
    open(f"{OUTTXT}/{nom[:-4]}.txt", "w").write(base64.b64encode(blob).decode())
    print(nom, "déplacement retranché", dep.tolist(), "(%.1f %% de la boîte)" % (100 * np.hypot(*dep) / 60000))
json.dump(ix, open(f"{OUTGZ}/matiere2-{ix['etiquette']}.json", "w")); json.dump(ix, open(f"{OUTTXT}/matiere2-{ix['etiquette']}.json", "w"))
