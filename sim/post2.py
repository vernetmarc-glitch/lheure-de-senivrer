"""Post-traitement, version 2 (plan « fond de carte » du 17/11/2026, P1, P2, P5).

Après pm.py lancé avec NSORTIES et FOULE : choix de l'observateur, tranche autour de lui,
et, pour CHAQUE instantané, un fichier séparé (la page charge d'abord les époques proches
de l'instant affiché) :
  - positions projetées des points suivis (int16, déroulées par rapport à aujourd'hui) ;
  - longueur de lissage h (taille du noyau, u8, échelle log) ;
  - agitation σ : dispersion des vitesses des 24 voisines en 3D (u8, échelle log) — dans
    les images de Millennium, les amas, où la matière s'agite le plus, tirent vers le blanc.
Aucune grandeur ne dépend d'une statistique de l'image : bornes constantes.

Usage : python post2.py DOSSIER_SIM SORTIE ETIQUETTE DEMI_EPAISSEUR NPOINTS [DELTA_MIN DELTA_MAX LISSAGE]
"""
import numpy as np, json, sys, os, glob
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter

SIM, OUT, ETQ = sys.argv[1], sys.argv[2], sys.argv[3]
HZ, NPTS = float(sys.argv[4]), int(sys.argv[5])
DMIN, DMAX, LISS = (float(v) for v in (sys.argv[6:9] if len(sys.argv) > 8 else (4, 8, 2.0)))
os.makedirs(OUT, exist_ok=True)
meta = json.load(open(f"{SIM}/meta.json")); L = meta["L"]; NP = meta["NP"]; FOULE = meta.get("foule", 1)
fichiers = sorted(glob.glob(f"{SIM}/snap_a*.npy")); AS = [float(f.split("_a")[1][:-4]) for f in fichiers]
lit = lambda f: np.load(f).astype(np.float32) * np.float32(L / 65535)
print("instantanés", len(AS), AS[:3], "…", flush=True)

# --- observateur : une cellule de surdensité modérée (un groupe de galaxies), proche du centre
x1 = lit(fichiers[-1])
ng = 128; idx = np.floor(x1 / L * ng).astype(np.int64) % ng
cnt = np.bincount((idx[:, 0] * ng + idx[:, 1]) * ng + idx[:, 2], minlength=ng**3).reshape(ng, ng, ng).astype(np.float32)
del idx
dens = gaussian_filter(cnt, LISS / (L / ng), mode="wrap"); dens /= dens.mean(); del cnt
ok = (dens > DMIN) & (dens < DMAX)
g = np.indices(dens.shape).reshape(3, -1).T.astype(np.float32)
dist = np.linalg.norm(g - ng / 2, axis=1).reshape(dens.shape)
c = np.unravel_index(np.argmin(np.where(ok, dist, 1e9)), dens.shape)
obs = (np.array(c) + 0.5) * L / ng
print("observateur", obs, "surdensité", float(dens[c]), flush=True)
w = lambda v: (v + L / 2) % L - L / 2
d1 = w(x1 - obs)
ids_tous = np.where(np.abs(d1[:, 2]) < HZ)[0]
rng = np.random.default_rng(1)
ids = np.sort(rng.choice(ids_tous, size=min(NPTS, len(ids_tous)), replace=False))
print("tranche", len(ids_tous), "points gardés", len(ids), flush=True)

Om = 0.315; E = lambda a: np.sqrt(Om / a**3 + 1 - Om)
from scipy.integrate import quad
Dg = lambda a: 2.5 * Om * E(a) * quad(lambda t: 1 / (t * E(t))**3, 0, a)[0] / (2.5 * Om * E(1) * quad(lambda t: 1 / (t * E(t))**3, 0, 1)[0])
pas = L / NP * FOULE ** (1 / 3)                     # écart moyen entre particules suivies
index = {"etiquette": ETQ, "n": int(len(ids)), "a": AS, "L_mpch": L, "L_gal": L / 0.674 * 3.26156e-3, "quant": 60000,
         "observateur": [float(v) for v in obs], "demi_epaisseur": HZ, "n_tranche": int(len(ids_tous)), "foule": FOULE,
         "h": "u8 = (log2(h / L) + 14) * 16", "sigma": "u8 = (log10(sigma km/s) - 1) * 80", "fichiers": []}
for k, (f, a) in enumerate(zip(fichiers, AS)):
    xa = lit(f); va = np.load(f.replace("snap_a", "vit_a")).astype(np.float32) if FOULE > 1 else None
    da = d1 + w(xa - x1)                                   # déroulé par rapport à aujourd'hui
    sel = da[ids]
    xy = np.clip(np.round(sel[:, :2] / L * 60000), -32767, 32767).astype(np.int16)
    q3 = np.column_stack([np.mod(sel[:, 0], L), np.mod(sel[:, 1], L), sel[:, 2] + 10 * L])
    dist, _ = cKDTree(q3, boxsize=[L, L, 1e9]).query(q3, k=9)
    plancher = pas * (0.25 + 0.65 * (1 - Dg(a)))          # la grille de départ ne doit pas se voir
    h = np.maximum(dist[:, -1], plancher) / L
    hh = np.clip(np.round((np.log2(h) + 14) * 16), 0, 255).astype(np.uint8)
    if va is not None:
        # agitation : dispersion 3D des vitesses des 24 voisines, parmi toutes les particules suivies
        arbre = cKDTree(np.mod(xa, L), boxsize=L)
        _, vois = arbre.query(np.mod(xa[ids], L), k=24, workers=-1)
        vv = va[vois]                                       # (n, 24, 3)
        sig = np.sqrt(((vv - vv.mean(1, keepdims=True))**2).sum(-1).mean(1) / 3)
        del arbre, vois, vv
    else:
        sig = np.full(len(ids), 10.0, np.float32)
    ss = np.clip(np.round((np.log10(np.maximum(sig, 1)) - 1) * 80), 0, 255).astype(np.uint8)
    tete = json.dumps({"a": a, "n": int(len(ids)), "k": k}).encode()
    blob = np.uint32(len(tete)).tobytes() + tete; blob += b"\0" * ((-len(blob)) % 2)
    blob += xy.tobytes() + hh.tobytes() + ss.tobytes()
    nom = f"matiere2-{ETQ}-{k:02d}.bin"; open(f"{OUT}/{nom}", "wb").write(blob); index["fichiers"].append(nom)
    print("a=%.4f h médian %.3f Mpc/h, σ médian %.0f km/s, 99e %.0f km/s" % (a, np.median(dist[:, -1]), np.median(sig), np.percentile(sig, 99)), flush=True)
    del xa, da, va
json.dump(index, open(f"{OUT}/matiere2-{ETQ}.json", "w"))
print("FIN", flush=True)
