"""TEST 4 -- dissolution des points lumineux en FILAMENTS.

Demande de Marc (27 juillet) : les points lumineux des layers de densite elevee
n'existaient pas dans l'ancien generateur. Ils ne doivent pas palir sur place en
remontant le temps -- ils doivent s'ETIRER le long du filament qui a alimente
le halo, puis se fondre dans la nappe.

Un profil radial isotrope pose autour de la position eulerienne ne sait pas
faire ca : le dissoudre serait un fondu isotrope, exactement le « disparaitre
sans etat intermediaire credible » que le §11.2 rejette.

Mecanisme : ANCRAGE LAGRANGIEN. Chaque point du halo est un element de masse
avec sa propre position initiale q_i, tiree dans la PATCH LAGRANGIENNE du halo
(la region d'espace initial qui s'est effondree pour le former).

    pos_i(a) = q_i + Psi(q_i, a) + C(a) · ( cible_compacte_i − [q_i + Psi(q_i, 1)] )

  - a = 1     : C = 1  -> pos = cible_compacte  (aspect valide par Marc)
  - a decroit : C -> 0  -> pos = q_i + Psi(q_i,a), pur Zel'dovich de la patch,
                qui s'etire le long du filament car Psi est ANISOTROPE
  - a -> 0    : Psi -> 0 -> retour au verre uniforme

C(a) suit l'a_form propre a l'echelle du halo (§11.4.a). Rien n'est floute,
rien ne palit : les points se DEPLACENT.
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M
import test2b_bandes as B
import test2b_identite as ID


def lagrangian_clouds(q_lag, pos_eul, mass, k_points, mass_ref,
                      R_patch_mpc=2.4, q_prof=0.6, rmax_mpc=2.2,
                      mass_slope=0.9, mass_ref_compact=None):
    """mass_ref  -> echelle de la PATCH lagrangienne (reference mediane)
    mass_ref_compact -> echelle du PROFIL COMPACT a a=1 (reference validee,
    distincte : les confondre casse la non-regression de la nettete des pics)."""
    """Retourne (q_points, cible_compacte, halo_id, R_L par halo).

    q_points  : positions LAGRANGIENNES des elements de masse (patch du halo)
    cible     : positions compactes a a=1 (profil radial pique deja calibre)
    """
    seeds = ID.halo_seed(q_lag)
    counts = np.maximum((k_points * mass ** mass_slope).astype(np.int64), 0)
    keep = counts > 0
    seeds, q_lag, pos_eul, mass, counts = (seeds[keep], q_lag[keep], pos_eul[keep],
                                           mass[keep], counts[keep])
    idx = np.concatenate([np.arange(c) for c in counts]).astype(np.int64)
    hid = np.repeat(np.arange(len(counts)), counts)
    sd = seeds[hid]

    # rayon lagrangien : M ~ R_L^3
    R_L = R_patch_mpc * (mass / mass_ref) ** (1.0 / 3.0)
    R_L = np.maximum(R_L, 0.35 * R_patch_mpc)

    def sphere(salt_u, salt_ct, salt_ph, radius, power):
        u = ID.rand_stream(sd, idx, salt_u)
        r = radius * u ** power
        ct = 2 * ID.rand_stream(sd, idx, salt_ct) - 1
        st = np.sqrt(np.maximum(1 - ct ** 2, 0))
        ph = 2 * np.pi * ID.rand_stream(sd, idx, salt_ph)
        return (r[:, None] * np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1))

    # patch lagrangienne : distribution ~uniforme en volume (power = 1/3)
    q_pts = q_lag[hid] + sphere(101, 103, 107, R_L[hid], 1.0 / 3.0)
    # cible compacte a a=1 : profil radial pique (canal RNG distinct)
    mrc = mass_ref if mass_ref_compact is None else mass_ref_compact
    r_cmp = (rmax_mpc * (mass / mrc) ** 0.28)[hid]
    cible = pos_eul[hid] + sphere(23, 37, 53, r_cmp, q_prof)
    return q_pts.astype(np.float32), cible.astype(np.float32), hid, R_L


def collapse_factor(a, R_L):
    """C(a) : achevement de la virialisation, pilote par l'echelle du halo."""
    return B.A_of(np.float64(a), 2.0 * R_L)


def cloud_shape(pts, hid, n_halo, min_pts=40):
    """Rapports d'axes principaux par halo : 1:1:1 = isotrope, allonge = filament."""
    out = []
    order = np.argsort(hid, kind="stable")
    h_s, p_s = hid[order], pts[order]
    bounds = np.searchsorted(h_s, np.arange(n_halo + 1))
    for i in range(n_halo):
        lo, hi = bounds[i], bounds[i + 1]
        if hi - lo < min_pts:
            continue
        c = np.cov((p_s[lo:hi] - p_s[lo:hi].mean(0)).T)
        ev = np.sort(np.linalg.eigvalsh(c))[::-1]
        if ev[2] > 1e-9:
            out.append((np.sqrt(ev[0] / ev[2]), np.sqrt(ev[0] / ev[1])))
    o = np.array(out)
    return (float(np.median(o[:, 0])), float(np.median(o[:, 1])), len(o)) if len(o) else (1., 1., 0)


def lagrangian_pair(q_lag, pos_eul, mass, k_points, mass_ref,
                    R_patch_mpc=2.4, q_prof=0.6, rmax_mpc=2.2, mass_slope=0.9,
                    sub_levels=2, sub_frac=0.30, R_mass_ref=None):
    """Retourne (q_lagrangien, cible_compacte, hid, R_L).

    La CIBLE est produite par la fonction deja validee (recursion de sous-halos
    incluse) : le rendu a a=1 est donc strictement inchange (non-regression).
    Les positions LAGRANGIENNES des memes points sont tirees sur un canal RNG
    distinct, dans la patch du halo. Les sous-halos ont donc tous leur origine
    lagrangienne dans la patch de leur parent -- physiquement correct.
    """
    seeds = ID.halo_seed(q_lag)
    counts = np.maximum((k_points * mass ** mass_slope).astype(np.int64), 0)
    keep = counts > 0
    seeds, q_lag, pos_eul, mass, counts = (seeds[keep], q_lag[keep], pos_eul[keep],
                                           mass[keep], counts[keep])
    cible = ID.halo_clouds_stable(q_lag, pos_eul, mass, k_points, q=q_prof,
                                  rmax_mpc=rmax_mpc, mass_slope=mass_slope,
                                  sub_levels=sub_levels, sub_frac=sub_frac,
                                  mass_ref=mass_ref)
    idx = np.concatenate([np.arange(c) for c in counts]).astype(np.int64)
    hid = np.repeat(np.arange(len(counts)), counts)
    sd = seeds[hid]
    mr = mass_ref if R_mass_ref is None else R_mass_ref
    R_L = np.maximum(R_patch_mpc * (mass / mr) ** (1.0 / 3.0), 0.35 * R_patch_mpc)
    u = ID.rand_stream(sd, idx, 201)
    r = R_L[hid] * u ** (1.0 / 3.0)
    ct = 2 * ID.rand_stream(sd, idx, 203) - 1
    st = np.sqrt(np.maximum(1 - ct ** 2, 0))
    ph = 2 * np.pi * ID.rand_stream(sd, idx, 207)
    off = r[:, None] * np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)
    return (q_lag[hid] + off).astype(np.float32), cible.astype(np.float32), hid, R_L
