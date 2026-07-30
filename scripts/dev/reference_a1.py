"""NOUVELLE REFERENCE a=1 -- generateur canonique par particules.

Remplace la reference du §11.7 (rendu de production log-normale), dont le
changement a ete acte par Marc le 28 juillet.

Chaine, dans l'ordre, sans aucune etape spatialement non lineaire en aval :

  1. champ gaussien contraint par P(k) BBKS (ns=0.965, Gamma=0.21231) --
     repris a l'identique de scripts/generate_layers.py
  2. positions lagrangiennes en VERRE : reseau + jitter d'une demi-cellule
     (le reseau seul donne des pics de Bragg : anisotropie 2.7e9, cf. test 1)
  3. deplacement de Zel'dovich, bande unique, applique aux POSITIONS
     (jamais de depot CIC : c'est lui qui detruisait la coherence inter-layer)
  4. halos par peak-patch ; leurs points sont PRELEVES dans la toile
     (conservation de la masse : sans elle la dissolution ne se termine jamais)
  5. profil radial pique, sous-halos recursifs
  6. projection en tranche : somme lineaire en profondeur
  7. courbe de ton ponctuelle 1 - exp(-alpha.rho), alpha resolu pour la cible
     de moyenne de la cellule

Invariant : entre l'objet generateur et l'ecran, uniquement des operateurs
spatiaux LINEAIRES et des courbes de ton PONCTUELLES.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
import mcpm_web as M

# ---- parametres canoniques, figes -----------------------------------------
JITTER_CELL = 0.5          # verre : demi-cellule (le 1/4 ne casse pas Bragg)
SLAB_FRAC = 0.06           # epaisseur de tranche / largeur de champ
PSF_PX = 0.45              # PSF du point ; 0 -> quantification entiere visible
TARGET_MEAN = 68.0         # politique 2 : moyenne constante (decision 28/07)
GAMMA = 1.0
LAM_MIN_MPC = 1.318359     # calibre l3 ; inactif si sous la coupure de la grille
AMP_RMS_MPC = 6.0          # deplacement rms de reference, CALIBRE SUR l3
AMP_REF_BOX = 450.0        # ... pour cette taille de boite.
                           # delta etant normalise a variance unite par boite,
                           # Psi ~ delta/k impose rms(Psi) ∝ boite. Renormaliser
                           # a 6 Mpc dans TOUTES les boites sur-deplacerait les
                           # petits layers et casserait la coherence inter-layer
                           # (une particule partagee bougerait differemment).
HALO_SMOOTH_CELLS = 2.0    # echelle de lissage du peak-patch
HALO_THRESH_SIGMA = 0.5
HALO_FRAC_WEB = 0.25       # part de la toile prelevee par les halos
TARGET_PROJ = 2_200_000    # particules VISEES dans la projection : la densite
                           # doit etre fixee par la resolution de SORTIE, pas
                           # par la grille physique (regle etablie au test 2 :
                           # 33k contre 298k faisaient diverger sigma de 24%)
PROFILE_Q = 0.6            # exposant radial (calibre sur la reference Millennium)
PROFILE_RMAX_FRAC = 0.011  # rmax / largeur de boite pour le halo le plus massif
SUB_LEVELS = 2
SUB_FRAC = 0.30

LAYERS = [
    ("D", "l1b", 8.49, 1.5, 3), ("E", "l2", 30.0, 1.5, 2),
    ("F", "l2b", 67.08, 1.5, 5), ("G", "l3", 150.0, 1.5, 102),
    ("H", "l3b", 212.13, 1.5, 7), ("I", "l4", 300.0, 1.5, 11),
    ("J", "l4a", 793.73, 1.5, 13), ("K", "l4b", 2100.0, 1.5, 17),
    ("L", "l5a", 5531.46, 1.5, 19), ("M", "l5", 14570.0, 2.4, 23),
]


def bake(half_mpc, margin, seed, n_field=384, out_n=512, verbose=False):
    box = 2.0 * half_mpc * margin
    cell = box / n_field
    amp = AMP_RMS_MPC * box / AMP_REF_BOX
    rng = np.random.default_rng(seed)

    delta = M.gen_delta3(n_field, box, seed)

    # --- verre restreint au voisinage de la tranche
    z_half = SLAB_FRAC * 2 * half_mpc / 2.0 + 4.0 * amp
    g = (np.arange(n_field) + 0.5) * cell - box / 2
    gz = g[np.abs(g) < max(z_half, 2 * cell)]
    Q = np.stack(np.meshgrid(g, g, gz, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
    Q += (rng.random(Q.shape).astype(np.float32) - 0.5) * cell * (2 * JITTER_CELL)
    frac = min(SLAB_FRAC * 2 * half_mpc / max(2 * (gz.max() - gz.min()) + cell, 1e-9), 1.0) \
        * min((half_mpc / (box / 2)) ** 2, 1.0)
    rep = int(np.clip(round(TARGET_PROJ / max(len(Q) * frac, 1.0)), 1, 24))
    if verbose:
        print(f"    densite : {len(Q)*frac:.0f} projetees a rep=1 -> replication x{rep}")

    # --- Zel'dovich sur les positions
    KX, KY, KZ, kmag = M.k_grid3(n_field, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = kmag <= 2 * np.pi / max(LAM_MIN_MPC, 2 * cell)
    c = ((Q + box / 2) / box * n_field).T
    PS = np.empty_like(Q)
    acc = 0.0
    for a, K in enumerate((KX, KY, KZ)):
        p = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=(n_field,) * 3).astype(np.float32)
        acc += float(np.mean(p ** 2))
        PS[:, a] = ndimage.map_coordinates(p, c, order=1, mode="wrap")
        del p
    del dk, c
    import gc; gc.collect()
    PS *= np.float32(amp / max(np.sqrt(acc / 3.0), 1e-9))
    web = Q + PS

    # --- halos : peak-patch, points PRELEVES dans la toile
    import gc
    qL, mass = M.extract_halos(delta, box, HALO_SMOOTH_CELLS * cell, HALO_THRESH_SIGMA,
                               HALO_SMOOTH_CELLS * cell, 60000)
    del delta; gc.collect()
    tree = cKDTree(Q)
    # Ne garder que les halos dont le centre lagrangien est DANS la tranche
    # generee : un halo exterieur consommerait des particules de la tranche pour
    # les emporter hors du cadre (constate sur G : ANISO 0.62, struct divisees
    # par deux).
    inz = np.abs(qL[:, 2]) < (gz.max() - gz.min()) / 2 + cell
    qL, mass = qL[inz], mass[inz]
    _, near = tree.query(qL)
    pos_e = qL + PS[near]

    budget = int(HALO_FRAC_WEB * len(Q))
    w = mass ** 0.9
    counts = np.maximum((w / w.sum() * budget).astype(np.int64), 0)
    keep = counts > 0
    qL, mass, counts, pos_e = qL[keep], mass[keep], counts[keep], pos_e[keep]
    taken = np.zeros(len(Q), bool)
    owner = np.full(len(Q), -1, np.int32)
    for i in np.argsort(mass)[::-1]:
        k = int(counts[i])
        if k < 1:
            continue
        _, idx = tree.query(qL[i], k=min(k * 3, len(Q)))
        idx = np.atleast_1d(idx)
        free = idx[~taken[idx]][:k]
        taken[free] = True
        owner[free] = i
    hid = owner[taken]
    n_h = int(taken.sum())

    # --- profil radial pique + sous-halos
    rmax = PROFILE_RMAX_FRAC * box
    lvl = (rng.random(n_h) * (SUB_LEVELS + 1)).astype(np.int32)
    scale = SUB_FRAC ** lvl
    rr = rmax * (mass[hid] / mass.max()) ** 0.28 * scale
    r = rr * rng.random(n_h) ** PROFILE_Q
    ct = 2 * rng.random(n_h) - 1
    st = np.sqrt(np.maximum(1 - ct ** 2, 0))
    ph = 2 * np.pi * rng.random(n_h)
    d = np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)
    web[taken] = (pos_e[hid] + r[:, None] * d).astype(np.float32)

    if verbose:
        print(f"    cellule {cell:.3f} Mpc | amp {amp:.3f} Mpc | {len(Q)} part. | {len(qL)} halos "
              f"| {n_h} points preleves ({100*n_h/len(Q):.0f}%)")
    return web, box, rep, cell


def render(web, box, half_mpc, out_n=512, rep=1, cell=1.0, seed=0):
    """La replication (jitter sous-cellule autour de la position deplacee) porte
    la densite projetee a la cible, sans recalculer Psi : le deplacement varie
    negligeablement a l'interieur d'une cellule."""
    slab = SLAB_FRAC * 2 * half_mpc
    rng = np.random.default_rng(seed + 991)
    img = np.zeros((out_n, out_n), np.float32)
    total = 0
    for k in range(max(rep, 1)):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32) - 0.5) * cell
        m = (np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < half_mpc) & (np.abs(p[:, 1]) < half_mpc)
        q = p[m]
        total += int(m.sum())
        ix = np.clip(((q[:, 0] + half_mpc) / (2 * half_mpc) * out_n).astype(np.int32), 0, out_n - 1)
        iy = np.clip(((q[:, 1] + half_mpc) / (2 * half_mpc) * out_n).astype(np.int32), 0, out_n - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
        del p, q
    img = ndimage.gaussian_filter(img, PSF_PX)
    alpha = M.solve_alpha(img, TARGET_MEAN, gamma=GAMMA)
    return M.tone(img, alpha, gamma=GAMMA), float(alpha), total
