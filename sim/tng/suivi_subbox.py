"""Suivi des étoiles de la Voie lactée depuis les cadres denses de la Subbox0 de TNG50
(galaxie 537941, un cadre toutes les ~86 Ma, cf. subbox537.py).

Même principe et même format de sortie que suivi.py, avec deux différences :
- les cadres ne contiennent que les étoiles : une étoile pas encore née est absente
  et apparaît (en fondu, côté page) à sa naissance ;
- le suivi se fait sur tous les cadres (pas de temps court : les tours se comptent sans
  ambiguïté), puis on ne garde que EOUT époques pour la page ; les tours d'un intervalle
  de sortie sont la somme des angles déroulés sur les cadres qu'il contient.

Usage : python3 suivi_subbox.py CADRES SORTIE.bin [N] [EOUT] [GRAINE]
"""
import glob, json, sys
import numpy as np
from scipy.spatial import cKDTree

H, BOITE, RPAS = 0.6774, 35000.0, 0.005


def age_gyr(a):
    Om, H0 = 0.3089, 67.74; OL = 1 - Om
    return 2 / (3 * np.sqrt(OL)) * np.arcsinh(np.sqrt(OL / Om) * np.asarray(a) ** 1.5) * 977.8 / H0


def phys(X, a, ref):
    d = X - ref; d -= BOITE * np.round(d / BOITE); return d * a / H


def centre(x, m, c, r):
    while r > 1.0:
        s = ((x - c) ** 2).sum(1) < r * r
        if s.sum() < 50: break
        c = np.average(x[s], axis=0, weights=m[s]); r *= 0.85
    return c


def cadre(f):
    d = np.load(f); a = float(d["a"])
    ok = d["GFM_StellarFormationTime"] > 0
    return a, d["centre"], {k: d[k][ok] for k in ("Coordinates", "ParticleIDs", "GFM_StellarFormationTime", "Velocities", "Masses")}


def main():
    dos, sortie = sys.argv[1], sys.argv[2]
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 50000
    EOUT = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    rng = np.random.default_rng(int(sys.argv[5]) if len(sys.argv) > 5 else 7)
    fics = sorted(glob.glob(f"{dos}/cadre-*.npz"), key=lambda s: int(s.split("-")[-1][:-4]))
    E = len(fics); print(E, "cadres", flush=True)

    # --- aujourd'hui : tirage des étoiles et repère du disque
    a0, ref0, st0 = cadre(fics[-1])
    x0 = phys(st0["Coordinates"], a0, ref0); c0 = centre(x0, st0["Masses"], np.zeros(3), 8.0); x0 -= c0
    v0 = st0["Velocities"] * np.sqrt(a0); s = (x0 ** 2).sum(1) < 100
    v0 -= np.average(v0[s], axis=0, weights=st0["Masses"][s])
    L = (st0["Masses"][s, None] * np.cross(x0[s], v0[s])).sum(0); n = L / np.linalg.norm(L)
    u = np.cross(n, [1, 0, 0]); u /= np.linalg.norm(u); w = np.cross(n, u); R = np.stack([u, w, n])
    dans = np.where((x0 ** 2).sum(1) < 35 ** 2)[0]
    tb = age_gyr(st0["GFM_StellarFormationTime"][dans]); m = st0["Masses"][dans]
    bords = np.arange(0, 14.1, 0.25); ib = np.clip(np.digitize(tb, bords) - 1, 0, len(bords) - 2)
    Mb = np.bincount(ib, m, len(bords) - 1); Mb_eff = np.maximum(Mb, 0.3 * Mb[Mb > 0].mean())
    pr = m / Mb_eff[ib]; pr /= pr.sum()
    sel = rng.choice(len(dans), N, replace=False, p=pr)
    ids = st0["ParticleIDs"][dans[sel]].astype(np.uint64); naiss = tb[sel]
    poids = (m[sel] / m.sum()) / pr[sel]; poids /= poids.mean()
    print(f"{len(dans)} étoiles à < 35 kpc, {N} suivies", flush=True)

    r = np.full((E, N), np.nan); phi = np.zeros((E, N)); zz = np.zeros((E, N)); hh = np.ones((E, N))
    omp = np.full((E, N), np.nan); om = np.zeros((E, N)); ts = np.zeros(E); centres = np.zeros((E, 3))
    c_prec = None
    for e, f in enumerate(fics):
        a, ref, st = cadre(f); ts[e] = age_gyr(a)
        if len(st["Masses"]) < 20: continue
        xs = phys(st["Coordinates"], a, ref)
        # centre : resserré autour du centre précédent (en kpc propres, suivi pas à pas) si
        # le catalogue s'en écarte, pour ne pas sauter sur un satellite
        c = centre(xs, st["Masses"], np.zeros(3), 10.0)
        centres[e] = ref * a / H + c                                  # absolu, kpc propres
        xs = (xs - c) @ R.T
        vs = (st["Velocities"] * np.sqrt(a)) @ R.T
        s9 = (xs ** 2).sum(1) < 9
        vs -= np.average(vs[s9], axis=0, weights=st["Masses"][s9]) if s9.sum() > 20 else vs.mean(0)
        I = st["ParticleIDs"].astype(np.uint64); o = np.argsort(I); Is = I[o]
        j = np.clip(np.searchsorted(Is, ids), 0, len(Is) - 1); trouve = Is[j] == ids
        src = o[j[trouve]]; p = xs[src]; v = vs[src]
        r[e, trouve] = np.hypot(p[:, 0], p[:, 1]); phi[e, trouve] = np.arctan2(p[:, 1], p[:, 0]); zz[e, trouve] = p[:, 2]
        omp[e, trouve] = (p[:, 0] * v[:, 1] - p[:, 1] * v[:, 0]) / np.maximum(p[:, 0] ** 2 + p[:, 1] ** 2, 0.01) * 1.0227
        if trouve.sum() > 20:
            d, _ = cKDTree(p).query(p, k=min(9, trouve.sum())); hh[e, trouve] = np.maximum(d[:, -1] * 0.5, 0.05)
        rr = np.hypot(xs[:, 0], xs[:, 1]); vphi = (xs[:, 0] * vs[:, 1] - xs[:, 1] * vs[:, 0]) / np.maximum(rr, 1e-3)
        bins = np.geomspace(0.2, 200, 40); cb = np.sqrt(bins[1:] * bins[:-1])
        med = np.array([np.median(vphi[(rr >= bins[i]) & (rr < bins[i + 1])]) if ((rr >= bins[i]) & (rr < bins[i + 1])).sum() > 15 else np.nan for i in range(len(cb))])
        okm = np.isfinite(med)
        vprof = np.interp(np.log(np.maximum(np.nan_to_num(r[e], nan=1), 0.2)), np.log(cb[okm]), med[okm]) if okm.sum() > 2 else np.zeros(N)
        om[e] = np.where(np.isfinite(r[e]), vprof / np.maximum(np.nan_to_num(r[e], nan=1), 0.3) * 1.0227, 0)
        if e % 10 == 0 or e == E - 1:
            print(f"  {ts[e]:5.2f} Ga : {trouve.mean()*100:5.1f} % présentes, nées : {(naiss <= ts[e] + 0.05).mean()*100:4.0f} %", flush=True)

    # trous courts : comblés en ligne droite
    for i in range(N):
        pres = np.where(np.isfinite(r[:, i]))[0]
        for e0, e1 in zip(pres[:-1], pres[1:]):
            if 1 < e1 - e0 <= 8:
                A = np.array([r[e0, i] * np.cos(phi[e0, i]), r[e0, i] * np.sin(phi[e0, i]), zz[e0, i]])
                B = np.array([r[e1, i] * np.cos(phi[e1, i]), r[e1, i] * np.sin(phi[e1, i]), zz[e1, i]])
                for e in range(e0 + 1, e1):
                    f = (ts[e] - ts[e0]) / (ts[e1] - ts[e0]); P = A + (B - A) * f
                    r[e, i] = np.hypot(P[0], P[1]); phi[e, i] = np.arctan2(P[1], P[0]); zz[e, i] = P[2]
                    hh[e, i] = hh[e0, i] + (hh[e1, i] - hh[e0, i]) * f; omp[e, i] = np.nan; om[e, i] = 0

    # angle déroulé sur les cadres denses ; « droit » quand un pas n'est pas une rotation de disque
    dphi = np.zeros((E - 1, N)); droit = np.zeros((E - 1, N), bool)
    for e in range(E - 1):
        dt = ts[e + 1] - ts[e]
        d = phi[e + 1] - phi[e]; d -= 2 * np.pi * np.round(d / (2 * np.pi))
        o0 = np.where(np.isfinite(omp[e]), omp[e], om[e]); o1 = np.where(np.isfinite(omp[e + 1]), omp[e + 1], om[e + 1])
        kk = np.round((0.5 * (o0 + o1) * dt - d) / (2 * np.pi))
        both = np.isfinite(r[e]) & np.isfinite(r[e + 1])
        disque = both & (np.nan_to_num(r[e]) < 25) & (np.nan_to_num(r[e + 1]) < 25) & (np.abs(zz[e]) < 3) & (np.abs(zz[e + 1]) < 3)
        conf = disque & np.isfinite(omp[e]) & np.isfinite(omp[e + 1]) & (np.abs(o0 - om[e]) < 0.35 * np.abs(om[e]) + 2)
        dphi[e] = np.where(conf, d + 2 * np.pi * kk, d); droit[e] = both & ~conf

    # époques de sortie : uniformes en temps parmi les cadres où des étoiles existent
    e_deb = int(np.argmax(np.isfinite(r).sum(1) > 50))
    cible = np.linspace(ts[e_deb], ts[-1], EOUT)
    sortie_e = sorted({int(np.argmin(np.abs(ts - c))) for c in cible}); sortie_e[-1] = E - 1
    Eo = len(sortie_e)
    k = np.zeros((Eo - 1, N), np.int8)
    for q in range(Eo - 1):
        ea, eb = sortie_e[q], sortie_e[q + 1]
        both = np.isfinite(r[ea]) & np.isfinite(r[eb])
        continu = np.isfinite(r[ea:eb + 1]).all(0)
        dr = droit[ea:eb].any(0)
        tot = dphi[ea:eb].sum(0)
        d = phi[eb] - phi[ea]; d -= 2 * np.pi * np.round(d / (2 * np.pi))
        kk = np.clip(np.round((tot - d) / (2 * np.pi)), -127, 127)
        k[q] = np.where(both & continu & ~dr, kk, np.where(both, -128, 0))
    ro, po, zo, ho, to = r[sortie_e], phi[sortie_e], zz[sortie_e], hh[sortie_e], ts[sortie_e]
    print(f"{Eo} époques de sortie, de {to[0]:.2f} à {to[-1]:.2f} Ga ; tours médians {np.median(np.abs(k[k > -128])):.0f}, "
          f"lignes droites {np.mean(k == -128)*100:.1f} %", flush=True)

    hdr = json.dumps({"n": N, "t": [round(float(x), 4) for x in to], "rpas": RPAS, "subhalo": 537941, "source": "TNG50-1-Subbox0"}).encode()
    ru = np.where(np.isfinite(ro), np.clip(np.round(np.nan_to_num(ro) / RPAS), 0, 65534), 65535).astype(np.uint16)
    pu = (np.round((po % (2 * np.pi)) / (2 * np.pi) * 65536).astype(np.int64) % 65536).astype(np.uint16)
    zu = (np.clip(np.round(zo / RPAS), -32767, 32767).astype(np.int32) + 32768).astype(np.uint16)
    hu = np.clip(np.round((np.log2(ho) + 6) * 16), 0, 255).astype(np.uint8)
    tn = np.clip(np.round(naiss * 4000), 0, 65535).astype(np.uint16)
    with open(sortie, "wb") as f:
        f.write(np.uint32(len(hdr)).tobytes()); f.write(hdr)
        if (4 + len(hdr)) % 2: f.write(b"\0")
        f.write(np.stack([ru, pu, zu], -1).tobytes()); f.write(hu.tobytes()); f.write(k.tobytes()); f.write(tn.tobytes())
        f.write(np.clip(np.round(poids * 1000), 1, 65535).astype(np.uint16).tobytes())
    np.savez_compressed(sortie.replace(".bin", ".npz"), r=ro, phi=po, z=zo, h=ho, k=k, t=to, naiss=naiss, poids=poids,
                        centres=centres[sortie_e], R=R, snaps=[int(fics[e].split("-")[-1][:-4]) for e in sortie_e])
    print("écrit", sortie, flush=True)


if __name__ == "__main__":
    main()
