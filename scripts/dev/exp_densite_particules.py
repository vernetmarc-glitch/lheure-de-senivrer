"""EXPERIENCE -- la densite de particules limite-t-elle F2 ?

Constat a expliquer (30/07) : la correlation inter-lignes vaut 0,875 sur la
PROJECTION DU CHAMP et 0,386 sur le RENDU PARTICULAIRE. L'ecart nait donc de
l'echantillonnage, en aval du raccord.

Deux mesures, dans cet ordre :

  1. PLANCHER DE BRUIT. On rend la meme ligne, a champ et deplacement
     STRICTEMENT identiques, avec plusieurs realisations independantes du verre.
     La correlation entre ces rendus donne la part du signal qui vient du champ :
        rho_auto = Var(champ) / (Var(champ) + Var(grenaille))
     et plafonne mecaniquement F2 a  rho_champ * sqrt(rho_auto).

  2. SUR-ECHANTILLONNAGE. On multiplie le nombre de particules lagrangiennes
     par s^3 sans toucher au champ. Si le plancher est bien de la grenaille,
     rho_auto doit monter comme  1/(1 + c/s^3).

Le couple O->N est choisi parce qu'il ne porte AUCUN halo (R_HALO < 0,6 px a ces
echelles) : la question posee est isolee de la redistribution en amas.
"""
import numpy as np
from scipy import ndimage

import gen_chain as G
import validate_raccord as V
import mcpm_web as M
import slab_test as ST


def psi_total_grid(L, parent):
    """Psi complet de la ligne, sur sa grille : part fraiche + part heritee."""
    box = (L.box_xy, L.box_xy, L.Lz)
    k_max = 2 * np.pi / (2 * L.cell)
    if parent is None:
        return G.psi_band(L.delta, box, 0.0, k_max)
    d_lo = G.sample_parent_grid(parent.delta_lo, L.shape, L.box_xy, L.Lz,
                                parent.box_xy, parent.Lz)
    d_hi = (L.delta - d_lo).astype(np.float32)
    psi = G.psi_band(d_hi, box, parent.k_cut, k_max)
    del d_lo, d_hi
    # part heritee, echantillonnee sur la grille de l'enfant
    for a in range(3):
        psi[..., a] += G.sample_parent_grid(parent.psi_lo[..., a], L.shape,
                                            L.box_xy, L.Lz, parent.box_xy, parent.Lz)
    return psi


def particules(L, PSI, verre_seed, sub=1):
    """Verre lagrangien, eventuellement sur-echantillonne d'un facteur `sub`.

    `sub` raffine UNIQUEMENT le reseau de particules : le champ et Psi sont
    inchanges, Psi est simplement interpole aux nouvelles positions. C'est bien
    la densite d'echantillonnage qu'on fait varier, pas la physique.
    """
    rng = np.random.default_rng(verre_seed)
    nx, ny, nz = L.shape
    c = L.cell / sub
    gx = (np.arange(nx * sub) + 0.5) * c - L.box_xy / 2
    gz = (np.arange(nz * sub) + 0.5) * c - L.Lz / 2
    Q = np.stack(np.meshgrid(gx, gx, gz, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
    Q += (rng.random(Q.shape).astype(np.float32) - 0.5) * c * 2 * G.JITTER
    C = np.stack([(Q[:, 0] / L.box_xy + 0.5) * nx - 0.5,
                  (Q[:, 1] / L.box_xy + 0.5) * ny - 0.5,
                  (Q[:, 2] / L.Lz + 0.5) * nz - 0.5])
    for a in range(3):
        Q[:, a] += ndimage.map_coordinates(PSI[..., a], C, order=1, mode="nearest")
    return Q


def rendu(L, web, slab, seed, rep=1):
    rng = np.random.default_rng(seed + 991)
    img = np.zeros((G.OUT_N, G.OUT_N), np.float32)
    for k in range(rep):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32) - 0.5) * L.cell
        m = ((np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < L.half)
             & (np.abs(p[:, 1]) < L.half))
        q = p[m]
        ix = np.clip(((q[:, 0] + L.half) / (2 * L.half) * G.OUT_N).astype(np.int32), 0, G.OUT_N - 1)
        iy = np.clip(((q[:, 1] + L.half) / (2 * L.half) * G.OUT_N).astype(np.int32), 0, G.OUT_N - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
        del p, q
    img = ndimage.gaussian_filter(img, G.PSF_PX)
    return M.tone(img, M.solve_alpha(img, G.TARGET_MEAN, gamma=1.0), gamma=1.0)


def projection_champ(d, L, slab):
    nz = d.shape[2]
    k = int(max(1, round(slab / (L.Lz / nz))))
    z0 = (nz - k) // 2
    im = d[:, :, z0:z0 + k].sum(2)
    n = G.OUT_N
    w = int(round(im.shape[0] * L.half / (L.box_xy / 2)))
    c = (im.shape[0] - w) // 2
    yy, xx = np.mgrid[0:n, 0:n] * (w / n) + c
    return ndimage.map_coordinates(im.astype(np.float64), np.stack([yy, xx]),
                                   order=1, mode="nearest")


def main():
    print("=" * 74)
    print("DENSITE DE PARTICULES -- couple O->N (aucun halo a ces echelles)")
    print("=" * 74)
    P = G.bake_layer("O", 14570.0, 1.5, 23, None)
    C = G.bake_layer("N", 5781.9515, 1.5, 19, P)
    ratio = P.half / C.half
    lam = (2 * np.pi / P.k_cut) / (2 * C.half / G.OUT_N)
    slab = G.SLAB_FRAC * 2 * C.half
    npx = G.OUT_N ** 2

    ref = projection_champ(C.delta, C, slab)
    par = projection_champ(P.delta, P, slab)
    a, b = V.bande_commune(par, ref, ratio, lam)
    rho_champ = V.correlation(a, b)
    print(f"\nreference : correlation des CHAMPS projetes = {rho_champ:.3f}\n")

    PSI = psi_total_grid(C, P)
    print(f"{'sub':>4} {'particules':>12} {'part/px':>9} {'rho_auto':>9} "
          f"{'plafond F2':>11} {'F2 mesure':>10}")
    for sub in (1, 2):
        webs = [particules(C, PSI, 1000 + 37 * i, sub) for i in range(2)]
        ims = [rendu(C, w, slab, 19 + 5 * i) for i, w in enumerate(webs)]
        vus = int(((np.abs(webs[0][:, 2]) < slab / 2)
                   & (np.abs(webs[0][:, 0]) < C.half)
                   & (np.abs(webs[0][:, 1]) < C.half)).sum())
        s1, s2 = [ndimage.gaussian_filter(x.astype(np.float64), lam / 3.0) for x in ims]
        rho_auto = V.correlation(s1, s2)
        plafond = rho_champ * np.sqrt(max(rho_auto, 0.0))
        aa, bb = V.bande_commune(par, ims[0], ratio, lam)
        f2 = V.correlation(aa, bb)
        print(f"{sub:>4} {len(webs[0]):>12,} {vus / npx:>9.1f} {rho_auto:>9.3f} "
              f"{plafond:>11.3f} {f2:>10.3f}")
        del webs, ims
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
