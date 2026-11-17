"""Suivi des étoiles de la Voie lactée (TNG50) d'une époque à l'autre.

On tire N étoiles de la galaxie d'aujourd'hui. À chaque époque, on retrouve
chacune par son identifiant : comme étoile si elle est née, sinon comme la
cellule de gaz qui la formera (dans TNG, l'étoile hérite de l'identifiant de
sa cellule mère). Absente de la découpe → marquée manquante (elle arrive de
plus loin et apparaîtra en fondu).

Repère : centré sur le progéniteur à chaque époque, orienté sur le disque
d'aujourd'hui (fixe), vu de face. Distances en kpc propres.

Entre deux époques, l'angle est interpolé en suivant la rotation : on choisit
le nombre de tours k qui rapproche le déplacement angulaire de celui que
prédit la courbe de rotation médiane ω(r) de l'époque (vitesses des étoiles).

Usage : python3 sim/tng/suivi.py DOSSIER SORTIE.bin [N] [GRAINE]
Format : u32 longueur d'en-tête JSON, en-tête, puis (alignés) :
  pos u16 [E][N][3] : r (pas 0,005 kpc ; 65535 = absente), φ (2π/65536),
                      z + 32768 (hauteur au-dessus du disque d'aujourd'hui, pas 0,005 kpc)
  h  u8  [E][N]  (log2(h/kpc)+6)*16, lissage SPH (8 voisins, 3D)
  k  i8  [E-1][N] tours supplémentaires ; -128 = trajet en ligne droite (hors disque)
  tn u16 [N]     date de naissance en Ga × 4000
  w  u16 [N]     poids (masse représentée / moyenne) × 1000
"""
import json, sys
import h5py
import numpy as np
from scipy.spatial import cKDTree

H, BOITE = 0.6774, 35000.0
RPAS = 0.005


def age_gyr(a):
    Om, H0 = 0.3089, 67.74; OL = 1 - Om
    return 2 / (3 * np.sqrt(OL)) * np.arcsinh(np.sqrt(OL / Om) * np.asarray(a) ** 1.5) * 977.8 / H0


def lit(fic):
    with h5py.File(fic) as f:
        a = float(f["Header"].attrs["Time"])
        st = {k: f["PartType4"][k][:] for k in f["PartType4"]} if "PartType4" in f else None
        ga = {k: f["PartType0"][k][:] for k in f["PartType0"]} if "PartType0" in f else None
    return a, st, ga


def phys(X, a, ref):
    d = X - ref; d -= BOITE * np.round(d / BOITE); return d * a / H


def centre(x, m, c=None, r=None):
    if c is None:
        c = np.average(x, axis=0, weights=m)
        r = np.sqrt(((x - c) ** 2).sum(1)).max()
    while r > 1.5:
        s = ((x - c) ** 2).sum(1) < r * r
        if s.sum() < 100: break
        c = np.average(x[s], axis=0, weights=m[s]); r *= 0.85
    return c


def main():
    dos, sortie = sys.argv[1], sys.argv[2]
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 40000
    rng = np.random.default_rng(int(sys.argv[4]) if len(sys.argv) > 4 else 7)
    meta = json.load(open(f"{dos}/meta.json"))
    eps = sorted(meta["epoques"], key=lambda e: e["snap"])
    E = len(eps)
    with h5py.File(f"{dos}/mpb.hdf5") as f:
        POS = dict(zip(f["SnapNum"][:].tolist(), f["SubhaloPos"][:]))

    # --- aujourd'hui : choix des étoiles et repère du disque
    a0, st0, _ = lit(f"{dos}/e{eps[-1]['snap']:03d}.hdf5")
    ok = st0["GFM_StellarFormationTime"] > 0
    st0 = {k: v[ok] for k, v in st0.items()}
    ref0 = POS[eps[-1]["snap"]]
    x0 = phys(st0["Coordinates"], a0, ref0); c0 = centre(x0, st0["Masses"], np.zeros(3), 8.0); x0 -= c0
    v0 = st0["Velocities"] * np.sqrt(a0)
    s = (x0 ** 2).sum(1) < 100
    v0 -= np.average(v0[s], axis=0, weights=st0["Masses"][s])
    L = (st0["Masses"][s, None] * np.cross(x0[s], v0[s])).sum(0); n = L / np.linalg.norm(L)
    u = np.cross(n, [1, 0, 0]); u /= np.linalg.norm(u); w = np.cross(n, u)
    R = np.stack([u, w, n])
    dans = np.where((x0 ** 2).sum(1) < 35 ** 2)[0]
    tb = age_gyr(st0["GFM_StellarFormationTime"][dans]); m = st0["Masses"][dans]
    bords = np.arange(0, 14.1, 0.25); ib = np.clip(np.digitize(tb, bords) - 1, 0, len(bords) - 2)
    Mb = np.bincount(ib, m, len(bords) - 1); Mb_eff = np.maximum(Mb, 0.3 * Mb[Mb > 0].mean())
    pr = m / Mb_eff[ib]; pr /= pr.sum()
    sel = rng.choice(len(dans), N, replace=False, p=pr)
    tirage = dans[sel]
    poids = (m[sel] / m.sum()) / pr[sel]; poids /= poids.mean()   # masse représentée / moyenne
    ids = st0["ParticleIDs"][tirage]
    naiss = tb[sel]
    print(f"{len(dans)} étoiles à < 35 kpc, {N} suivies", flush=True)

    r = np.full((E, N), np.nan); phi = np.zeros((E, N)); zz = np.zeros((E, N)); hh = np.full((E, N), 1.0)
    omp = np.full((E, N), np.nan)          # vitesse angulaire PROPRE de chaque étoile (rad/Ga)
    om = np.zeros((E, N)); ts = np.zeros(E); centres = np.zeros((E, 3)); profils = []
    for e, ep in enumerate(eps):
        a, st, ga = lit(f"{dos}/e{ep['snap']:03d}.hdf5")
        ts[e] = age_gyr(a)
        okk = st["GFM_StellarFormationTime"] > 0
        st = {k: v[okk] for k, v in st.items()}
        ref = POS[ep["snap"]]
        xs = phys(st["Coordinates"], a, ref); c = centre(xs, st["Masses"], np.zeros(3), 8.0); xs = (xs - c) @ R.T
        centres[e] = c
        vs = (st["Velocities"] * np.sqrt(a)) @ R.T
        sel = (xs ** 2).sum(1) < 9
        vs -= np.average(vs[sel], axis=0, weights=st["Masses"][sel]) if sel.sum() > 20 else vs.mean(0)
        xg = (phys(ga["Coordinates"], a, ref) - c) @ R.T if ga is not None else np.zeros((0, 3))
        X = np.concatenate([xs, xg]); I = np.concatenate([st["ParticleIDs"], ga["ParticleIDs"] if ga is not None else []]).astype(np.uint64)
        o = np.argsort(I); Is = I[o]
        j = np.clip(np.searchsorted(Is, ids), 0, len(Is) - 1)
        trouve = Is[j] == ids
        src = o[j[trouve]]; p = X[src]
        r[e, trouve] = np.hypot(p[:, 0], p[:, 1]); phi[e, trouve] = np.arctan2(p[:, 1], p[:, 0]); zz[e, trouve] = p[:, 2]
        etoile = src < len(xs); w = np.where(trouve)[0][etoile]; v = vs[src[etoile]]; q = p[etoile]
        omp[e, w] = (q[:, 0] * v[:, 1] - q[:, 1] * v[:, 0]) / np.maximum(q[:, 0] ** 2 + q[:, 1] ** 2, 0.01) * 1.0227
        # lissage : 8 voisins parmi les points suivis présents (3D)
        if trouve.sum() > 20:
            d, _ = cKDTree(p).query(p, k=min(9, trouve.sum()))
            hh[e, trouve] = np.maximum(d[:, -1] * 0.5, 0.05)
        # courbe de rotation médiane ω(r) en rad/Ga, depuis les étoiles
        rr = np.hypot(xs[:, 0], xs[:, 1]); vphi = (xs[:, 0] * vs[:, 1] - xs[:, 1] * vs[:, 0]) / np.maximum(rr, 1e-3)
        bins = np.geomspace(0.2, 200, 40); cb = np.sqrt(bins[1:] * bins[:-1])
        med = np.array([np.median(vphi[(rr >= bins[i]) & (rr < bins[i + 1])]) if ((rr >= bins[i]) & (rr < bins[i + 1])).sum() > 15 else np.nan for i in range(len(cb))])
        okm = np.isfinite(med); profils.append(med)
        vprof = np.interp(np.log(np.maximum(r[e], 0.2)), np.log(cb[okm]), med[okm]) if okm.sum() > 2 else np.zeros(N)
        om[e] = np.where(np.isfinite(r[e]), vprof / np.maximum(r[e], 0.3) * 1.0227, 0)
        print(f"  {ts[e]:5.2f} Ga : {trouve.mean()*100:5.1f} % retrouvées "
              f"(dont étoiles {np.isin(ids[trouve], st['ParticleIDs']).mean()*100:4.0f} %), "
              f"nées avant : {(naiss <= ts[e]).mean()*100:4.0f} %", flush=True)

    # trous : une étoile absente d'une découpe entre deux époques où elle est présente (le
    # satellite qui la porte sort un moment du groupe) ; on comble le trou en ligne droite
    # au lieu de la faire disparaître puis réapparaître
    for i in range(N):
        pres = np.where(np.isfinite(r[:, i]))[0]
        if len(pres) < 2: continue
        for e0, e1 in zip(pres[:-1], pres[1:]):
            if 1 < e1 - e0 <= 6:
                A = np.array([r[e0, i] * np.cos(phi[e0, i]), r[e0, i] * np.sin(phi[e0, i]), zz[e0, i]])
                B = np.array([r[e1, i] * np.cos(phi[e1, i]), r[e1, i] * np.sin(phi[e1, i]), zz[e1, i]])
                for e in range(e0 + 1, e1):
                    f = (ts[e] - ts[e0]) / (ts[e1] - ts[e0]); P = A + (B - A) * f
                    r[e, i] = np.hypot(P[0], P[1]); phi[e, i] = np.arctan2(P[1], P[0]); zz[e, i] = P[2]
                    hh[e, i] = hh[e0, i] + (hh[e1, i] - hh[e0, i]) * f
                    omp[e, i] = np.nan; om[e, i] = 0
    # tours supplémentaires par intervalle
    k = np.zeros((E - 1, N), np.int8)
    for e in range(E - 1):
        dt = ts[e + 1] - ts[e]
        d = phi[e + 1] - phi[e]; d -= 2 * np.pi * np.round(d / (2 * np.pi))
        # rotation prédite par la vitesse angulaire propre de l'étoile (cohérente pour un
        # satellite entier), à défaut par la courbe de rotation médiane
        o0 = np.where(np.isfinite(omp[e]), omp[e], om[e]); o1 = np.where(np.isfinite(omp[e + 1]), omp[e + 1], om[e + 1])
        pred = 0.5 * (o0 + o1) * dt
        kk = np.round((pred - d) / (2 * np.pi))
        both = np.isfinite(r[e]) & np.isfinite(r[e + 1])
        # hors du disque en rotation (satellites, gerbes de marée, halo) : trajet en ligne droite
        # entre les deux positions (k = -128), pour que les voisins restent voisins
        disque = both & (np.nan_to_num(r[e]) < 25) & (np.nan_to_num(r[e + 1]) < 25) & (np.abs(zz[e]) < 3) & (np.abs(zz[e + 1]) < 3)
        conf = disque & np.isfinite(omp[e]) & np.isfinite(omp[e + 1]) & (np.abs(o0 - om[e]) < 0.35 * np.abs(om[e]) + 2)
        k[e] = np.where(conf, np.clip(kk, -127, 127), np.where(both, -128, 0))

    hdr = json.dumps({"n": N, "t": [round(float(x), 4) for x in ts], "rpas": RPAS,
                      "subhalo": meta["subhalo"]}).encode()
    ru = np.where(np.isfinite(r), np.clip(np.round(np.nan_to_num(r) / RPAS), 0, 65534), 65535).astype(np.uint16)
    pu = np.round((phi % (2 * np.pi)) / (2 * np.pi) * 65536).astype(np.int64) % 65536
    hu = np.clip(np.round((np.log2(hh) + 6) * 16), 0, 255).astype(np.uint8)
    tn = np.clip(np.round(naiss * 4000), 0, 65535).astype(np.uint16)
    with open(sortie, "wb") as f:
        f.write(np.uint32(len(hdr)).tobytes()); f.write(hdr)
        if (4 + len(hdr)) % 2: f.write(b"\0")
        # positions entrelacées par époque : (r, φ, z + 32768) en u16, pour qu'un seul attribut
        # vec3 lise une époque (la page en lit quatre pour lisser les trajets droits)
        zu = (np.clip(np.round(zz / RPAS), -32767, 32767).astype(np.int32) + 32768).astype(np.uint16)
        f.write(np.stack([ru, pu.astype(np.uint16), zu], -1).tobytes())
        f.write(hu.tobytes()); f.write(k.tobytes()); f.write(tn.tobytes())
        f.write(np.clip(np.round(poids * 1000), 1, 65535).astype(np.uint16).tobytes())
    np.savez_compressed(sortie.replace(".bin", ".npz"), r=r, phi=phi, z=zz, omp=omp, h=hh, k=k, t=ts, naiss=naiss, om=om, poids=poids,
                        centres=centres, R=R, profils=np.array(profils), rprof=cb, snaps=[e["snap"] for e in eps])
    print("écrit", sortie, flush=True)


if __name__ == "__main__":
    main()
