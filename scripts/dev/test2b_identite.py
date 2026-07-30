"""TEST 2 (suite) -- identite d'objet a travers les layers.

Condition 2 du document de test : la graine RNG des sous-halos doit deriver de
l'IDENTITE du halo (hash de sa position lagrangienne), jamais d'une sequence
globale. Sinon, ajouter des halos au layer fin decale le flux aleatoire et
re-randomise tous les nuages deja existants.

Position LAGRANGIENNE (avant deplacement de Zel'dovich) : c'est l'invariant
qui traverse les layers, la position eulerienne changeant d'un increment.

Le generateur aleatoire est donc *base sur compteur* (splitmix64 vectorise) :
rand(graine_halo, indice_particule) -> reproductible independamment du contexte.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
import mcpm_web as M

MASK = (1 << 64) - 1


def halo_seed(q_lag, quantum=1e-3):
    """Hash spatial de la position lagrangienne -> graine stable par halo."""
    k = np.round(q_lag / quantum).astype(np.int64)
    h = ((k[:, 0] * 73856093) ^ (k[:, 1] * 19349663) ^ (k[:, 2] * 83492791))
    return (h.astype(np.uint64) & np.uint64(0x7FFFFFFFFFFF))


def _splitmix(z):
    z = (z * np.uint64(0xBF58476D1CE4E5B9)) & np.uint64(MASK)
    z = ((z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)) & np.uint64(MASK)
    z = ((z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)) & np.uint64(MASK)
    return z ^ (z >> np.uint64(31))


def rand_stream(seed, idx, salt):
    """Uniforme [0,1) deterministe pour (graine_halo, indice, canal)."""
    z = (seed * np.uint64(0x9E3779B97F4A7C15)
         + idx.astype(np.uint64) * np.uint64(0xD1342543DE82EF95)
         + np.uint64(salt)) & np.uint64(MASK)
    return (_splitmix(z) >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def halo_clouds_stable(q_lag, pos_eul, mass, k_points,
                       q=0.6, rmax_mpc=2.2, mass_slope=0.9, sub_levels=2,
                       sub_frac=0.30, mass_ref=1.0):
    """Nuages de points, chaque halo tirant sur SON PROPRE flux aleatoire."""
    seeds = halo_seed(q_lag)
    # compte ABSOLU par halo : fonction de sa seule masse, jamais d'un budget
    # global partage -- sinon ajouter des halos au layer fin change la
    # luminosite de tous les autres et l'heritage n'est plus a 100%.
    counts = np.maximum((k_points * mass ** mass_slope).astype(np.int64), 0)
    keep = counts > 0
    seeds, pos_eul, mass, counts = seeds[keep], pos_eul[keep], mass[keep], counts[keep]
    if counts.sum() == 0:
        return np.zeros((0, 3), np.float32)

    idx = np.concatenate([np.arange(c) for c in counts]).astype(np.int64)
    hid = np.repeat(np.arange(len(counts)), counts)
    sd = seeds[hid]
    # reference de masse ABSOLUE (jamais mass.max(), qui depend du catalogue)
    rr = rmax_mpc * (mass / mass_ref) ** 0.28
    rr = rr[hid]

    lvl = (rand_stream(sd, idx, 11) * (sub_levels + 1)).astype(np.int32)
    scale = sub_frac ** lvl

    u = rand_stream(sd, idx, 23)
    r = rr * scale * u ** q
    ct = 2.0 * rand_stream(sd, idx, 37) - 1.0
    st = np.sqrt(np.maximum(1 - ct ** 2, 0))
    ph = 2 * np.pi * rand_stream(sd, idx, 53)
    d = np.stack([st * np.cos(ph), st * np.sin(ph), ct], axis=1)

    off = np.zeros((len(idx), 3))
    sub = lvl > 0
    if sub.any():   # decentrage du sous-halo dans son parent
        for a, salt in enumerate((71, 89, 97)):
            off[sub, a] = (2 * rand_stream(sd[sub], idx[sub], salt) - 1) * rr[sub] * 0.5
    return (pos_eul[hid] + off + r[:, None] * d).astype(np.float32)


def extract_and_displace(delta, box, smooth_mpc, thresh, min_sep, max_n, amp):
    """Retourne (position lagrangienne, position eulerienne, masse)."""
    q_lag, mass = M.extract_halos(delta, box, smooth_mpc, thresh, min_sep, max_n)
    pos = M.zeldovich_points(q_lag, delta, box, s_rms_mpc=amp)
    return q_lag, pos, mass


def carry_over(qL_p, pos_p, m_p, qL_c, pos_c, m_c, box, excl_mpc, mass_ratio):
    """Halos parents reportes VERBATIM ; enfants en doublon exclus."""
    h = box / 2.0
    inb = np.all(np.abs(qL_p) < h, axis=1)
    qLp, pp, mp = qL_p[inb], pos_p[inb], m_p[inb] * mass_ratio
    if len(qLp) == 0:
        return qL_c, pos_c, m_c, 0
    if len(qL_c):
        d, _ = cKDTree(qLp).query(qL_c)
        k = d > excl_mpc
        qL_c, pos_c, m_c = qL_c[k], pos_c[k], m_c[k]
    return (np.vstack([qLp, qL_c]), np.vstack([pp, pos_c]),
            np.concatenate([mp, m_c]), len(qLp))


def lowpass(delta, box, k_cut):
    n = delta.shape[0]
    _, _, _, kmag = M.k_grid3(n, box)
    dk = np.fft.rfftn(delta)
    return np.fft.irfftn(np.where(kmag <= k_cut, dk, 0), s=(n,) * 3).astype(np.float32)
