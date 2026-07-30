"""GENERATEUR COMPLET -- demonstrateur a resolution reduite.

Integre tous les correctifs valides :
  - normalisation ABSOLUE par sigma_8 (facteur unique, jamais par grille)
  - DALLE ANISOTROPE : fine en x,y, mince en z (corr. spectres 0,996)
  - marge de dalle depuis le Psi rms PROPRE A LA BOITE
  - chaine emboitee M -> D par raccord spectral (heritage exact sous la coupure)
  - verre = reseau + jitter 1/2 cellule
  - halos a masse CONSERVEE, prelevees dans la toile
  - SEUIL DE RESOLUTION des halos : au-dela, la lumiere retourne au champ
  - ton ponctuel, moyenne cible 68/255 (politique 2)
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
import mcpm_web as M
import norm_abs as NA

OUT_N = 320
TARGET_MEAN = 68.0
SLAB_FRAC = 0.06
PSF_PX = 0.45
JITTER = 0.5
TARGET_PROJ = 1_600_000
HALO_FRAC = 0.25
PROFILE_Q = 0.6
R_HALO_MPC = 2.2           # rayon PHYSIQUE d'un amas, absolu -- surtout pas une
                           # fraction de la boite (donnait 769 Mpc a M !).
                           # Meme defaut que celui trouve au test 7.a.
SUB_LEVELS, SUB_FRAC = 2, 0.30

# du plus GRAND au plus petit : sens de generation impose (§4.4)
CHAIN = [
    ("M", "l5", 14570.0, 2.4, 23), ("L", "l5a", 5531.46, 1.5, 19),
    ("K", "l4b", 2100.0, 1.5, 17), ("J", "l4a", 793.73, 1.5, 13),
    ("I", "l4", 300.0, 1.5, 11), ("H", "l3b", 212.13, 1.5, 7),
    ("G", "l3", 150.0, 1.5, 102), ("F", "l2b", 67.08, 1.5, 5),
    ("E", "l2", 30.0, 1.5, 2), ("D", "l1b", 8.49, 1.5, 3),
]


def grid_for(half, margin):
    """Dalle : cellule = pixel de sortie ; epaisseur = tranche + marge Psi propre."""
    box_xy = 2.0 * half * margin
    cell = 2.0 * half / OUT_N
    nxy = int(round(box_xy / cell))
    # Psi rms de CETTE boite, sur une grille grossiere suffisante
    npsi = min(96, max(nxy, 32))
    psi = NA.psi_rms((npsi,) * 3, (box_xy,) * 3, 2 * box_xy / npsi)
    T = SLAB_FRAC * 2 * half
    # seule la composante z du deplacement fait entrer/sortir de la dalle :
    # sa rms vaut psi/sqrt(3), pas psi.
    Lz = T + 4.0 * psi / np.sqrt(3.0)
    nz = max(int(round(Lz / cell)), 8)
    return nxy, nz, cell, box_xy, Lz, psi


def field(nxy, nz, box_xy, Lz, seed, parent=None, p_box=None, p_Lz=None, k_cut=None):
    """delta sur la dalle. Si `parent`, raccord spectral : modes du parent
    conserves exactement sous sa coupure, detail frais au-dessus."""
    shape = (nxy, nxy, nz)
    box = (box_xy, box_xy, Lz)
    d = NA.gen_delta_abs(shape, box, seed)
    if parent is None:
        return d
    # sous-cube du parent au champ de l'enfant, reechantillonne
    fx = box_xy / p_box
    fz = Lz / p_Lz
    pn = parent.shape
    gx = np.linspace(pn[0] * (1 - fx) / 2, pn[0] * (1 + fx) / 2, nxy, endpoint=False)
    gz = np.linspace(pn[2] * (1 - fz) / 2, pn[2] * (1 + fz) / 2, nz, endpoint=False)
    C = np.array(np.meshgrid(gx, gx, gz, indexing="ij"))
    inh = ndimage.map_coordinates(parent, C, order=1, mode="wrap").astype(np.float32)
    del C
    _, _, _, kmag = NA.k_grid_aniso(shape, box) if hasattr(NA, "k_grid_aniso") else (None,) * 4
    if kmag is None:
        import slab_test as ST
        _, _, _, kmag = ST.k_grid_aniso(shape, box)
    lo = kmag <= k_cut
    DI = np.fft.rfftn(inh)
    DF = np.fft.rfftn(d)
    del inh, d
    dk = np.where(lo, DI, DF)
    del DI, DF
    return np.fft.irfftn(dk, s=shape).astype(np.float32)


def psi_on(delta, box, lam_min):
    import slab_test as ST
    KX, KY, KZ, kmag = ST.k_grid_aniso(delta.shape, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = (kmag > 0) & (kmag <= 2 * np.pi / lam_min)
    out = np.empty(delta.shape + (3,), np.float32)
    for a, K in enumerate((KX, KY, KZ)):
        out[..., a] = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=delta.shape)
    return out


def bake_layer(code, half, margin, seed, parent=None, p_box=None, p_Lz=None, p_cell=None):
    nxy, nz, cell, box_xy, Lz, psirms = grid_for(half, margin)
    k_cut = np.pi / p_cell if p_cell else None
    d = field(nxy, nz, box_xy, Lz, seed, parent, p_box, p_Lz, k_cut)
    box = (box_xy, box_xy, Lz)

    PSI = psi_on(d, box, 2 * cell)
    rng = np.random.default_rng(seed + 7)
    gx = (np.arange(nxy) + 0.5) * cell - box_xy / 2
    gz = (np.arange(nz) + 0.5) * cell - Lz / 2
    Q = np.stack(np.meshgrid(gx, gx, gz, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
    Q += (rng.random(Q.shape).astype(np.float32) - 0.5) * cell * 2 * JITTER
    web = Q + PSI.reshape(-1, 3)
    del PSI

    # --- halos : seuil de RESOLUTION. Un halo n'est un objet distinct que s'il
    # est resolu ET rare a l'echelle du pixel ; sinon sa lumiere reste au champ.
    px = 2 * half / OUT_N
    r_typ = R_HALO_MPC
    n_halo = 0
    if r_typ > 0.6 * px:
        qL, mass = M.extract_halos(d, box_xy, 2 * cell, 0.5, 2 * cell, 40000)
        if len(qL):
            tree = cKDTree(Q)
            _, near = tree.query(qL)
            pos_e = qL + (web - Q)[near]
            budget = int(HALO_FRAC * len(Q))
            w = mass ** 0.9
            cnt = np.maximum((w / w.sum() * budget).astype(np.int64), 0)
            k = cnt > 0
            qL, mass, cnt, pos_e = qL[k], mass[k], cnt[k], pos_e[k]
            taken = np.zeros(len(Q), bool); owner = np.full(len(Q), -1, np.int32)
            for i in np.argsort(mass)[::-1]:
                c = int(cnt[i])
                if c < 1: continue
                _, idx = tree.query(qL[i], k=min(c * 3, len(Q)))
                idx = np.atleast_1d(idx); free = idx[~taken[idx]][:c]
                taken[free] = True; owner[free] = i
            hid = owner[taken]; nh = int(taken.sum()); n_halo = len(qL)
            lvl = (rng.random(nh) * (SUB_LEVELS + 1)).astype(np.int32)
            rr = r_typ * (mass[hid] / mass.max()) ** 0.28 * SUB_FRAC ** lvl
            r = rr * rng.random(nh) ** PROFILE_Q
            ct = 2 * rng.random(nh) - 1; st = np.sqrt(np.maximum(1 - ct ** 2, 0))
            ph = 2 * np.pi * rng.random(nh)
            web[taken] = (pos_e[hid] + r[:, None] *
                          np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)).astype(np.float32)
            del tree
    del Q
    return web, d, box_xy, Lz, cell, nxy, nz, psirms, n_halo, r_typ / px


def render(web, half, cell, seed):
    slab = SLAB_FRAC * 2 * half
    rng = np.random.default_rng(seed + 991)
    img = np.zeros((OUT_N, OUT_N), np.float32); tot = 0
    base = ((np.abs(web[:, 2]) < slab / 2).mean() * 1.0) or 1.0
    rep = int(np.clip(round(TARGET_PROJ / max(len(web) * base * 0.9, 1)), 1, 20))
    for k in range(rep):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32) - 0.5) * cell
        m = (np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < half) & (np.abs(p[:, 1]) < half)
        q = p[m]; tot += int(m.sum())
        ix = np.clip(((q[:, 0] + half) / (2 * half) * OUT_N).astype(np.int32), 0, OUT_N - 1)
        iy = np.clip(((q[:, 1] + half) / (2 * half) * OUT_N).astype(np.int32), 0, OUT_N - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
        del p, q
    img = ndimage.gaussian_filter(img, PSF_PX)
    a = M.solve_alpha(img, TARGET_MEAN, gamma=1.0)
    return M.tone(img, a, gamma=1.0), tot, rep
