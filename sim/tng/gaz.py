"""Couche de gaz froid de la Voie lactée (TNG50) : ce qui dessine les bras.

Pour chaque intervalle entre deux époques, on tire Ng cellules de gaz qui
forment des étoiles (SFR > 0) à la première époque, à moins de 40 kpc, et on
les retrouve à la suivante par leur identifiant. Même repère et même centre
que les étoiles (suivi.py, fichier .npz), même interpolation en rotation.
Le passage d'un intervalle au suivant se fait en fondu (voir la page).

Usage : python3 sim/tng/gaz.py DOSSIER_GAZ SUIVI.npz SORTIE.bin [Ng]

Variante (galaxie 537941, étoiles suivies dans la Subbox0) : les époques du gaz (boîte principale)
ne sont pas celles des étoiles. Le centre est alors interpolé dans le temps depuis les centres
absolus des étoiles (kpc propres), et la courbe de rotation se mesure sur le gaz froid lui-même.
Format : u32 longueur d'en-tête JSON, en-tête {n, t, rpas, w}, puis pour chaque
intervalle e (E-1 blocs consécutifs) :
  r0 r1 u16 [N] ×2 · q0 q1 u16 [N] ×2 · h0 h1 u8 [N] ×2 · k i8 [N] (−128 = ligne droite) · z0 z1 i16 [N] ×2
"""
import json, sys
import h5py
import numpy as np
from scipy.spatial import cKDTree

H, BOITE, RPAS = 0.6774, 35000.0, 0.005
H_ = H


def phys(X, a, ref):
    d = X - ref; d -= BOITE * np.round(d / BOITE); return d * a / H


def main():
    dos, npz, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    Ng = int(sys.argv[4]) if len(sys.argv) > 4 else 12000
    D = np.load(npz)
    with h5py.File(f"{dos}/mpb.hdf5") as f:
        POS = dict(zip(f["SnapNum"][:].tolist(), f["SubhaloPos"][:]))
    if "profils" in D:
        ts, R, C, prof, rprof, snaps = D["t"], D["R"], D["centres"], D["profils"], D["rprof"], list(D["snaps"])
        absolu = False
    else:
        # étoiles suivies ailleurs (Subbox0) : époques propres au gaz, centre interpolé, rotation mesurée sur le gaz
        meta = json.load(open(f"{dos}/meta.json")); snaps = sorted(e["snap"] for e in meta["epoques"])
        with h5py.File(f"{dos}/e{snaps[0]:03d}.hdf5") as f: pass
        def age(a):
            Om, H0 = 0.3089, 67.74; OL = 1 - Om
            return 2 / (3 * np.sqrt(OL)) * np.arcsinh(np.sqrt(OL / Om) * a ** 1.5) * 977.8 / H0
        aa = []
        for sn in snaps:
            with h5py.File(f"{dos}/e{sn:03d}.hdf5") as f: aa.append(float(f["Header"].attrs["Time"]))
        aa = np.array(aa); ts = age(aa)
        garde = ts >= D["t"][0] - 0.05
        snaps = [s for s, g in zip(snaps, garde) if g]; aa = aa[garde]; ts = ts[garde]
        R = D["R"]; Cs = D["centres"]; tsE = D["t"]
        C = np.stack([np.interp(ts, tsE, Cs[:, i]) for i in range(3)], 1)       # absolu, kpc propres
        absolu = True; rprof = None; prof = None
    E = len(ts)
    rng = np.random.default_rng(11)
    profils = []

    def lit(e):
        with h5py.File(f"{dos}/e{snaps[e]:03d}.hdf5") as f:
            a = float(f["Header"].attrs["Time"]); g = f["PartType0"]
            if absolu:
                Xa = g["Coordinates"][:] * a / H_; c = C[e] + BOITE * a / H_ * np.round((Xa.mean(0) - C[e]) / (BOITE * a / H_))
                X = (Xa - c) @ R.T
            else:
                X = (phys(g["Coordinates"][:], a, POS[snaps[e]]) - C[e]) @ R.T
            V = (g["Velocities"][:] * np.sqrt(a)) @ R.T
            sel = (X ** 2).sum(1) < 9
            V -= np.average(V[sel], axis=0, weights=g["Masses"][:][sel]) if sel.sum() > 20 else 0
            om = (X[:, 0] * V[:, 1] - X[:, 1] * V[:, 0]) / np.maximum(X[:, 0] ** 2 + X[:, 1] ** 2, 0.01) * 1.0227
            return X, g["Masses"][:], g["ParticleIDs"][:], g["StarFormationRate"][:], om

    def omega(e, r):
        if absolu: return om_gaz[e](r)
        ok = np.isfinite(prof[e])
        if ok.sum() < 3: return np.zeros_like(r)
        v = np.interp(np.log(np.maximum(r, 0.2)), np.log(rprof[ok]), prof[e][ok])
        return v / np.maximum(r, 0.3) * 1.0227

    om_gaz = {}
    def courbe(e, X, sf, om):
        rr = np.hypot(X[:, 0], X[:, 1]); s_ = (sf > 0) & (np.abs(X[:, 2]) < 3)
        bins = np.geomspace(0.2, 60, 30); cb = np.sqrt(bins[1:] * bins[:-1])
        med = np.array([np.median(om[s_ & (rr >= bins[i]) & (rr < bins[i + 1])] * cb[i]) if (s_ & (rr >= bins[i]) & (rr < bins[i + 1])).sum() > 15 else np.nan for i in range(len(cb))])
        ok = np.isfinite(med)
        om_gaz[e] = (lambda r, cb=cb, med=med, ok=ok: np.interp(np.log(np.maximum(r, 0.2)), np.log(cb[ok]), med[ok]) / np.maximum(r, 0.3)) if ok.sum() > 2 else (lambda r: np.zeros_like(r))
    blocs = []; poids = []
    suiv = lit(0)
    if absolu: courbe(0, suiv[0], suiv[3], suiv[4])
    for e in range(E - 1):
        X0, m0, id0, sf0, w0 = suiv
        X1, m1, id1, sf1, w1 = lit(e + 1); suiv = (X1, m1, id1, sf1, w1)
        if absolu: courbe(e + 1, X1, sf1, w1)
        cand = np.where((sf0 > 0) & ((X0 ** 2).sum(1) < 40 ** 2))[0]
        o = np.argsort(id1); s1 = id1[o]
        j = np.clip(np.searchsorted(s1, id0[cand]), 0, len(s1) - 1)
        ok = s1[j] == id0[cand]
        cand, j = cand[ok], o[j[ok]]
        n = min(Ng, len(cand))
        r0 = np.full(Ng, np.nan); r1 = np.full(Ng, np.nan); q0 = np.zeros(Ng); q1 = np.zeros(Ng)
        h0 = np.ones(Ng); h1 = np.ones(Ng); k = np.zeros(Ng, np.int8); z0 = np.zeros(Ng); z1 = np.zeros(Ng)
        if n > 20:
            pick = rng.choice(len(cand), n, replace=False, p=m0[cand] / m0[cand].sum())
            A, B = X0[cand[pick]], X1[j[pick]]
            r0[:n], r1[:n] = np.hypot(A[:, 0], A[:, 1]), np.hypot(B[:, 0], B[:, 1])
            q0[:n], q1[:n] = np.arctan2(A[:, 1], A[:, 0]), np.arctan2(B[:, 1], B[:, 0])
            z0[:n], z1[:n] = A[:, 2], B[:, 2]
            for P, hh in ((A, h0), (B, h1)):
                d, _ = cKDTree(P).query(P, k=min(9, n)); hh[:n] = np.maximum(d[:, -1] * 0.5, 0.04)
            d = q1[:n] - q0[:n]; d -= 2 * np.pi * np.round(d / (2 * np.pi))
            oa, ob = w0[cand[pick]], w1[j[pick]]
            pred = 0.5 * (oa + ob) * (ts[e + 1] - ts[e])
            kk = np.clip(np.round((pred - d) / (2 * np.pi)), -127, 127)
            # hors du disque en rotation : ligne droite (k = -128), comme pour les étoiles
            med = 0.5 * (omega(e, r0[:n]) + omega(e + 1, r1[:n]))
            disque = (r0[:n] < 25) & (r1[:n] < 25) & (np.abs(A[:, 2]) < 3) & (np.abs(B[:, 2]) < 3) & (np.abs(0.5 * (oa + ob) - med) < 0.35 * np.abs(med) + 2)
            k[:n] = np.where(disque, kk, -128)
        print(f"  {ts[e]:5.2f} Ga : {len(cand):7d} cellules froides suivies, {n} gardées", flush=True)
        blocs.append((r0, r1, q0, q1, h0, h1, k, z0, z1)); poids.append(len(cand) / max(n, 1))

    # nombre de cellules représentées par point, rapporté à sa médiane (constante écrite dans l'en-tête)
    w = np.array(poids); w = w / np.median(w[w > 1]) if (w > 1).any() else w
    hdr = json.dumps({"n": Ng, "t": [round(float(x), 4) for x in ts], "rpas": RPAS,
                      "w": [round(float(x), 4) for x in w]}).encode()
    with open(sortie, "wb") as f:
        f.write(np.uint32(len(hdr)).tobytes()); f.write(hdr)
        if (4 + len(hdr)) % 2: f.write(b"\0")
        for r0, r1, q0, q1, h0, h1, k, z0, z1 in blocs:
            for r in (r0, r1):
                f.write(np.where(np.isfinite(r), np.clip(np.round(np.nan_to_num(r) / RPAS), 0, 65534), 65535).astype(np.uint16).tobytes())
            for q in (q0, q1):
                f.write((np.round((q % (2 * np.pi)) / (2 * np.pi) * 65536).astype(np.int64) % 65536).astype(np.uint16).tobytes())
            for h in (h0, h1):
                f.write(np.clip(np.round((np.log2(h) + 6) * 16), 0, 255).astype(np.uint8).tobytes())
            f.write(k.tobytes())
            if Ng % 2: f.write(b"\0")
            for zq in (z0, z1):
                f.write(np.clip(np.round(zq / RPAS), -32767, 32767).astype(np.int16).tobytes())
    np.savez_compressed(sortie.replace(".bin", ".npz"), blocs=np.array([np.stack([b[0], b[1], b[2], b[3], b[4], b[5], b[6].astype(float), b[7], b[8]]) for b in blocs]), t=ts)
    print("écrit", sortie, flush=True)


if __name__ == "__main__":
    main()
