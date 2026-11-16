"""Données de matière pour la page : tranche fine autour de l'observateur,
5 instantanés (positions comobiles déroulées), longueur de lissage 2D par instantané.
Sortie : matiere.txt = base64( en-tête JSON | Int16 xy par instantané | Uint8 h par instantané )."""
import numpy as np, json, base64, sys
from scipy.spatial import cKDTree
L = 210.0; AS = ["0.15", "0.25", "0.40", "0.60", "1.00"]
X = {a: np.load(f"out/x_a{a}.npy").astype(np.float64) for a in AS}
x1 = X["1.00"]
# observateur : une cellule de surdensité modérée (groupe de galaxies) près du centre
ng = 64; idx = np.floor(x1 / L * ng).astype(int) % ng
cnt = np.bincount((idx[:, 0] * ng + idx[:, 1]) * ng + idx[:, 2], minlength=ng**3).reshape(ng, ng, ng)
from scipy.ndimage import gaussian_filter
d = gaussian_filter(cnt.astype(float), 1.0, mode="wrap"); d /= d.mean()
c = np.array(np.unravel_index(np.argmin(np.where((d > 4) & (d < 8), np.linalg.norm(np.indices(d.shape).reshape(3, -1).T.reshape(ng, ng, ng, 3) - ng / 2, axis=-1), 1e9)), d.shape))
obs = (c + 0.5) * L / ng
print("observateur", obs, "surdensité", d[tuple(c)])
w = lambda v: (v + L / 2) % L - L / 2
d1 = w(x1 - obs)
sel = np.abs(d1[:, 2]) < 8.0
rng = np.random.default_rng(1)
ids = np.where(sel)[0]; N = int(sys.argv[1]) if len(sys.argv) > 1 else 320000
ids = rng.choice(ids, size=min(N, len(ids)), replace=False)
print("tranche", sel.sum(), "gardés", len(ids))
xy = []; hh = []
for a in AS:
    ds = d1[ids] + w(X[a][ids] - x1[ids])          # déroulé par rapport à aujourd'hui
    u = ds[:, :2] / L
    xy.append(np.clip(np.round(u * 60000), -32767, 32767).astype(np.int16))
    # voisins en 3D (et non en projection) : en projection, les colonnes de la grille
    # de départ s'empilent et donnent des noyaux minuscules alignés en quadrillage
    q3 = np.column_stack([np.mod(ds[:, 0], L), np.mod(ds[:, 1], L), ds[:, 2] + 50.0])
    t = cKDTree(q3, boxsize=[L, L, 1e6])
    dist, _ = t.query(q3, k=9)
    # plancher : la grille de départ (pas 1,01 Mpc/h) ne doit pas se voir aux premières époques
    plancher = {"0.15": 0.9, "0.25": 0.8, "0.40": 0.6, "0.60": 0.4, "1.00": 0.25}[a]
    h = np.maximum(dist[:, -1], plancher) / L
    hh.append(np.clip(np.round((np.log2(h) + 14) * 16), 0, 255).astype(np.uint8))
    print(a, "h médian (Mpc/h)", np.median(dist[:, -1]))
head = json.dumps({"n": len(ids), "a": [float(a) for a in AS], "L_gal": 1.0163, "quant": 60000,
                   "frac_tranche": len(ids) / sel.sum(), "n_tranche": int(sel.sum())}).encode()
blob = np.uint32(len(head)).tobytes() + head
pad = (-len(blob)) % 2; blob += b"\0" * pad
for v in xy: blob += v.tobytes()
for v in hh: blob += v.tobytes()
open("lumiere/matiere.txt", "w").write(base64.b64encode(blob).decode())
print("taille", len(blob) / 1e6, "Mo brut")
