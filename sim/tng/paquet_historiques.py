"""Empaquette les historiques des halos (historiques.py) pour la page — plan « fond de carte » P3.

Chaque halo de la tranche est suivi le long de sa branche principale : sa position (relative au
progéniteur de la Voie lactée, donc la Voie lactée reste au centre), sa masse relative à aujourd'hui
et sa masse stellaire, à chaque instantané de TNG50 depuis z = 6. La page interpole chaque halo
le long de sa trajectoire (plus de halo figé à aujourd'hui pendant que la matière bouge).

Ses points (sa matière) gardent une position fixe dans le halo, en unités de son rayon, et suivent
le halo : rayon ∝ M(t)^(1/3), éclat ∝ M(t). Profil NFW (c = 10), un point pour MP masses solaires
(la masse d'aujourd'hui) : comme avant, la répartition interne est un modèle, pas la simulation.

Usage : python3 sim/tng/paquet_historiques.py IDS.npy HISTORIQUES/ MPB_VOIE_LACTEE.hdf5 REDSHIFTS.json SORTIE.bin
Format : u32 + en-tête JSON, puis
  halos  : par instantané e (dans l'ordre de l'en-tête), pour chaque halo h :
           x, y int16 [H] (ckpc/h) · mfrac u8 [H] (M/M0 × 100) · ms u8 [H] (log10 M*/Msun × 20, 0 = rien) · sf u8 [H]
  points : idx u16 [P] (halo) · dx, dy int8 [P] (rayon d'aujourd'hui / 100) · h u8 [P] (noyau, rayon / 100)
"""
import json, os, sys
import numpy as np, h5py
from scipy.spatial import cKDTree

H_ = 0.6774; L = 35000.0; MP = 2e9; SNAP0 = 13
ids = np.load(sys.argv[1]); dos = sys.argv[2]
mw = h5py.File(sys.argv[3]); MWP = dict(zip(mw["SnapNum"][:].tolist(), mw["SubhaloPos"][:]))
Z = {int(k): v for k, v in json.load(open(sys.argv[4])).items()}
snaps = [s for s in range(SNAP0, 100) if s in MWP]
E, w = len(snaps), lambda v: (v + L / 2) % L - L / 2
garde = [i for i in ids if os.path.exists(f"{dos}/{i}.npz")]
print("halos disponibles", len(garde), "sur", len(ids), "; instantanés", E, flush=True)
Hn = len(garde)
X = np.zeros((E, Hn), np.int16); Y = np.zeros((E, Hn), np.int16); MF = np.zeros((E, Hn), np.uint8); MS = np.zeros((E, Hn), np.uint8); SF = np.zeros((E, Hn), np.uint8)
rng = np.random.default_rng(7); pts = []
for h, i in enumerate(garde):
    d = np.load(f"{dos}/{i}.npz"); sn = d["snap"].tolist(); idx = {s: k for k, s in enumerate(sn)}
    k0 = idx[99]; M0 = float(d["m"][k0]) * 1e10 / H_
    dern = None
    for e, s in enumerate(snaps):
        if s in idx:
            k = idx[s]; r = w(d["pos"][k] - MWP[s]); dern = (r, float(d["m"][k]) * 1e10 / H_, float(d["ms"][k]) * 1e10 / H_, float(d["sfr"][k]))
            X[e, h], Y[e, h] = np.clip(np.round(r[:2]), -32767, 32767)
            MF[e, h] = np.clip(round(dern[1] / M0 * 100), 0, 255)
            MS[e, h] = np.clip(round(np.log10(dern[2]) * 20), 0, 255) if dern[2] > 1e6 else 0
            SF[e, h] = 1 if dern[3] > 0 else 0
        else:                                  # pas encore formé à cet instantané : position de la première apparition, masse nulle
            X[e, h] = Y[e, h] = -32768
    # trous : positions recopiées de l'instantané valide le plus proche, masse nulle
    v = X[:, h] != -32768
    if v.any():
        js = np.where(v)[0]
        for e in np.where(~v)[0]:
            j = js[np.argmin(np.abs(js - e))]; X[e, h], Y[e, h] = X[j, h], Y[j, h]
    # points NFW du halo, en unités du rayon d'aujourd'hui (r200 ≈ 206 kpc · (M/1e12)^(1/3))
    n = int(round(M0 / MP))
    if n < 1: continue
    c = 10.0; u = rng.random(n)
    mu = lambda x: np.log(1 + x) - x / (1 + x)
    xs = np.interp(u * mu(c), mu(np.linspace(1e-4, c, 4000)), np.linspace(1e-4, c, 4000)) / c   # rayon / r200
    th = np.arccos(2 * rng.random(n) - 1); ph = 2 * np.pi * rng.random(n)
    p2 = np.stack([xs * np.sin(th) * np.cos(ph), xs * np.sin(th) * np.sin(ph)], 1)
    hh = cKDTree(p2).query(p2, k=min(7, n))[0][:, -1] if n > 7 else np.full(n, 0.5)
    pts.append((np.full(n, h, np.uint16), np.clip(np.round(p2 * 100), -127, 127).astype(np.int8), np.clip(np.round(np.maximum(hh, 0.02) * 100), 1, 255).astype(np.uint8)))
idx = np.concatenate([p[0] for p in pts]); off = np.concatenate([p[1] for p in pts]); hk = np.concatenate([p[2] for p in pts])
# rayon d'aujourd'hui de chaque halo, en ckpc/h (pour la page : rayon(t) = R0 · (M/M0)^(1/3))
R0 = np.array([206.0 * ((float(np.load(f"{dos}/{i}.npz")["m"][0]) * 1e10 / H_) / 1e12) ** (1 / 3) * H_ for i in garde], np.float32)
o = rng.permutation(len(idx)); idx, off, hk = idx[o], off[o], hk[o]
tete = json.dumps({"H": Hn, "P": int(len(idx)), "snaps": snaps, "a": [round(1 / (1 + Z[s]), 5) for s in snaps], "unite": "ckpc/h", "mp": MP}).encode()
with open(sys.argv[5], "wb") as f:
    f.write(np.uint32(len(tete)).tobytes()); f.write(tete); f.write(b"\0" * ((-(4 + len(tete))) % 4))
    f.write(R0.tobytes())
    for e in range(E): f.write(X[e].tobytes()); f.write(Y[e].tobytes()); f.write(MF[e].tobytes()); f.write(MS[e].tobytes()); f.write(SF[e].tobytes())
    f.write(b"\0" * ((-f.tell()) % 2)); f.write(idx.tobytes()); f.write(off.tobytes()); f.write(hk.tobytes())
print("halos", Hn, "points", len(idx), "taille", os.path.getsize(sys.argv[5]) / 1e6, "Mo", flush=True)
