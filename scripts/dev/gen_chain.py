"""CHAINE EMBOITEE -- raccord spectral dans l'espace de Psi.

CE QUI ETAIT FAUX (gen_full.py, `field()`)
------------------------------------------
Le sous-volume du parent etait reechantillonne sur la dalle de l'enfant, PUIS
passe a `rfftn`. Or ce sous-volume n'est pas periodique dans la boite enfant :
il a une moyenne non nulle, un gradient lent, et une discontinuite de bord.
Toute cette puissance tombe dans les modes les plus BAS, que `Psi = i k d / k^2`
amplifie ensuite en 1/k.

Signature mesuree du defaut : std(delta) 6,28 -> 85,8 et rms(Psi) 10 -> 2253 Mpc.

LE PRINCIPE DE LA CORRECTION
----------------------------
Chaque boite ne subit de FFT que la ou elle EST periodique.

  1. sur la boite PARENT   : delta_lo = passe-bas(delta_parent, k_cut)
                             Psi_lo   = Psi(delta_parent) restreint a k <= k_cut
  2. INTERPOLATION de delta_lo et Psi_lo aux coordonnees de l'enfant.
     Operateur purement lineaire, aucune FFT en aval -- c'est tout le point.
  3. sur la boite ENFANT   : delta_hi = passe-haut(delta_frais, k_cut)
                             Psi_hi   = Psi(delta_hi) sur (k_cut, k_max]
  4. delta = delta_lo + delta_hi        Psi = Psi_lo + Psi_hi

La coupure est FRANCHE : chaque mode est porte par une boite et une seule, donc
la puissance totale est conservee exactement, sans double comptage.

`k_cut = pi / (2 * cellule_parent)`, soit la MOITIE de la Nyquist du parent. Le
champ passe-bas varie alors sur ~4 cellules parent : l'interpolation trilineaire
y est precise. Prendre la Nyquist entiere ferait de l'interpolation la nouvelle
source d'erreur.

Les modes plus grands que la boite enfant ne disparaissent pas : ils arrivent par
l'interpolation sous forme de gradient lent (translation d'ensemble + champ de
maree). C'est physiquement ce qu'il faut, et c'est impossible a obtenir en
re-FFT-ant l'enfant.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

import mcpm_web as M
import norm_abs as NA
import slab_test as ST

OUT_N = 320
TARGET_MEAN = 68.0
SLAB_FRAC = 0.06
PSF_PX = 0.45
JITTER = 0.5
TARGET_PROJ = 1_600_000
HALO_FRAC = 0.25
PROFILE_Q = 0.6
R_HALO_MPC = 2.2
SUB_LEVELS, SUB_FRAC = 2, 0.30
K_CUT_SAFETY = 1.2          # k_cut = pi / (K_CUT_SAFETY * cellule_parent)
# Calibre le 30/07 par balayage, sur la paire M->L :
#   safety 2,0 -> rho 0,919, variance heritee  5,2 %
#   safety 1,2 -> rho 0,960, variance heritee 12,3 %   <- retenu
#   safety 1,0 -> rho 0,958, variance heritee 15,1 %
# A 1,0 (Nyquist du parent exactement) la fidelite redescend : l'interpolation
# devient la source d'erreur dominante. 1,2 est le maximum utile.

# Echelle du 30/07 : 15 lignes geometriques A->O, raison x2,520 (D-21).
# Seules les lignes generees (H->O) passent par cette chaine ; A->G sont a
# sprites. La chaine va du PLUS GRAND au plus petit (sens impose, §4.4).
CHAIN = [
    ("O", 14570.0000, 1.5, 23), ("N", 5781.9515, 1.5, 19),
    ("M", 2294.5067, 1.5, 17), ("L", 910.5509, 1.5, 13),
    ("K", 361.3426, 1.5, 11), ("J", 143.3950, 1.5, 7),
    ("I", 56.9048, 1.5, 5), ("H", 22.5821, 1.5, 3),
]


# ---------------------------------------------------------------- geometrie
def grid_for(half, margin):
    """Dalle anisotrope : cellule = pixel de sortie, epaisseur = tranche + marge
    Psi PROPRE A LA BOITE."""
    box_xy = 2.0 * half * margin
    cell = 2.0 * half / OUT_N
    nxy = int(round(box_xy / cell))
    npsi = min(96, max(nxy, 32))
    psi = NA.psi_rms((npsi,) * 3, (box_xy,) * 3, 2 * box_xy / npsi)
    T = SLAB_FRAC * 2 * half
    # seule la composante z fait entrer/sortir de la dalle : rms = psi/sqrt(3)
    Lz = T + 4.0 * psi / np.sqrt(3.0)
    nz = max(int(round(Lz / cell)), 8)
    return nxy, nz, cell, box_xy, Lz, psi


# ------------------------------------------------- operateurs de bande (lineaires)
def _bandpass(delta, box, kmin, kmax):
    """delta restreint a (kmin, kmax]. FFT dans la boite ou delta est periodique."""
    _, _, _, kmag = ST.k_grid_aniso(delta.shape, box)
    band = (kmag > kmin) & (kmag <= kmax)
    dk = np.fft.rfftn(delta)
    return np.fft.irfftn(np.where(band, dk, 0), s=delta.shape).astype(np.float32)


def psi_band(delta, box, kmin, kmax):
    """Deplacement de Zel'dovich Psi = i k delta / k^2, restreint a (kmin, kmax].

    Meme remarque : la FFT n'est legitime que parce que `delta` est periodique
    dans `box`. Ne jamais appeler cette fonction sur un champ interpole.
    """
    KX, KY, KZ, kmag = ST.k_grid_aniso(delta.shape, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = (kmag > kmin) & (kmag <= kmax)
    out = np.empty(delta.shape + (3,), np.float32)
    for a, K in enumerate((KX, KY, KZ)):
        out[..., a] = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=delta.shape)
    return out


# --------------------------------------------------------------- interpolation
def _idx_from_mpc(pts, p_box_xy, p_Lz, p_shape):
    """Coordonnees comobiles (boite centree en 0) -> indices de grille parent."""
    nx, ny, nz = p_shape
    return np.stack([
        (pts[:, 0] / p_box_xy + 0.5) * nx - 0.5,
        (pts[:, 1] / p_box_xy + 0.5) * ny - 0.5,
        (pts[:, 2] / p_Lz + 0.5) * nz - 0.5,
    ])


def sample_parent(fieldp, pts, p_box_xy, p_Lz):
    """Echantillonne un champ parent (scalaire ou vectoriel) en des points Mpc.

    Spline cubique (order=3) et non trilineaire : pres de k_cut, l'interpolation
    lineaire attenue, et cette attenuation se lit directement dans std(delta).
    `mode="nearest"` en bord : les points de l'enfant sont tres a l'interieur du
    parent, le mode ne joue que sur l'arrondi du dernier demi-pixel.
    """
    C = _idx_from_mpc(pts, p_box_xy, p_Lz, fieldp.shape[:3])
    if fieldp.ndim == 3:
        return ndimage.map_coordinates(fieldp, C, order=3, mode="nearest").astype(np.float32)
    out = np.empty((pts.shape[0], fieldp.shape[3]), np.float32)
    for a in range(fieldp.shape[3]):
        out[:, a] = ndimage.map_coordinates(fieldp[..., a], C, order=3, mode="nearest")
    return out


def sample_parent_grid(fieldp, shape, box_xy, Lz, p_box_xy, p_Lz):
    """Echantillonne un champ parent SCALAIRE sur toute la grille de l'enfant."""
    nx, ny, nz = shape
    gx = (np.arange(nx) + 0.5) * (box_xy / nx) - box_xy / 2
    gy = (np.arange(ny) + 0.5) * (box_xy / ny) - box_xy / 2
    gz = (np.arange(nz) + 0.5) * (Lz / nz) - Lz / 2
    P = np.stack(np.meshgrid(gx, gy, gz, indexing="ij"), -1).reshape(-1, 3)
    return sample_parent(fieldp, P, p_box_xy, p_Lz).reshape(shape)


# --------------------------------------------------------------------- couche
class Layer:
    """Ce qu'une ligne transmet a la suivante.

    N'y garder QUE le necessaire : `delta_lo`, `psi_lo` et la geometrie. Le champ
    complet et le nuage de points sont liberes des que la ligne est rendue --
    sinon la chaine retient huit grilles de 480x480xnz et se fait tuer avant la
    derniere ligne (mesure du 30/07 : Killed a la ligne H).
    """
    __slots__ = ("code", "half", "cell", "box_xy", "Lz", "shape",
                 "delta", "delta_lo", "psi_lo", "k_cut", "psi_rms", "web", "n_halo",
                 "std_delta")

    def drop_heavy(self):
        """Libere ce dont l'enfant n'a pas besoin."""
        self.delta = None
        self.web = None


def bake_layer(code, half, margin, seed, parent=None):
    nxy, nz, cell, box_xy, Lz, psirms = grid_for(half, margin)
    shape, box = (nxy, nxy, nz), (box_xy, box_xy, Lz)
    k_max = 2 * np.pi / (2 * cell)          # bande de deplacement de CETTE ligne

    d_fresh = NA.gen_delta_abs(shape, box, seed)

    if parent is None:
        delta = d_fresh
        PSI = psi_band(delta, box, 0.0, k_max)
    else:
        kc = parent.k_cut
        # --- (3) part fraiche de l'enfant, au-dessus de la coupure
        d_hi = _bandpass(d_fresh, box, kc, k_max)
        psi_hi = psi_band(d_hi, box, kc, k_max)
        # --- (2) part heritee : INTERPOLATION, aucune FFT en aval
        d_lo = sample_parent_grid(parent.delta_lo, shape, box_xy, Lz,
                                  parent.box_xy, parent.Lz)
        # --- (4) somme
        delta = (d_lo + d_hi).astype(np.float32)
        PSI = psi_hi                         # Psi_lo s'ajoute aux positions, plus bas
        del d_hi, d_lo
    del d_fresh

    # ce que CETTE ligne transmettra : sa coupure vaut la moitie de sa Nyquist
    k_cut = np.pi / (K_CUT_SAFETY * cell)
    delta_lo = _bandpass(delta, box, 0.0, k_cut)
    psi_lo = psi_band(delta, box, 0.0, k_cut)

    # --------------------------------------------------- positions lagrangiennes
    rng = np.random.default_rng(seed + 7)
    gx = (np.arange(nxy) + 0.5) * cell - box_xy / 2
    gz = (np.arange(nz) + 0.5) * cell - Lz / 2
    Q = np.stack(np.meshgrid(gx, gx, gz, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
    Q += (rng.random(Q.shape).astype(np.float32) - 0.5) * cell * 2 * JITTER

    disp = PSI.reshape(-1, 3).copy()
    del PSI
    if parent is not None:
        disp += sample_parent(parent.psi_lo, Q, parent.box_xy, parent.Lz)
    web = Q + disp

    L = Layer()
    L.code, L.half, L.cell, L.box_xy, L.Lz, L.shape = code, half, cell, box_xy, Lz, shape
    L.delta, L.delta_lo, L.psi_lo, L.k_cut = delta, delta_lo, psi_lo, k_cut
    L.psi_rms = float(np.sqrt((disp ** 2).sum(1).mean()))
    L.std_delta = float(delta.std())
    del disp

    # ------------------------------------------------------------------ halos
    px = 2 * half / OUT_N
    L.n_halo = 0
    if R_HALO_MPC > 0.6 * px:
        qL, mass = M.extract_halos(delta, box_xy, 2 * cell, 0.5, 2 * cell, 40000)
        if len(qL):
            tree = cKDTree(Q)
            _, near = tree.query(qL)
            pos_e = qL + (web - Q)[near]
            budget = int(HALO_FRAC * len(Q))
            w = mass ** 0.9
            cnt = np.maximum((w / w.sum() * budget).astype(np.int64), 0)
            k = cnt > 0
            qL, mass, cnt, pos_e = qL[k], mass[k], cnt[k], pos_e[k]
            taken = np.zeros(len(Q), bool)
            owner = np.full(len(Q), -1, np.int32)
            for i in np.argsort(mass)[::-1]:
                c = int(cnt[i])
                if c < 1:
                    continue
                _, idx = tree.query(qL[i], k=min(c * 3, len(Q)))
                idx = np.atleast_1d(idx)
                free = idx[~taken[idx]][:c]
                taken[free] = True
                owner[free] = i
            hid = owner[taken]
            nh = int(taken.sum())
            L.n_halo = len(qL)
            lvl = (rng.random(nh) * (SUB_LEVELS + 1)).astype(np.int32)
            # masse de reference ABSOLUE : jamais mass.max(), qui est une
            # statistique globale du catalogue (INV-B1).
            m_ref = M.HALO_MASS_REF if hasattr(M, "HALO_MASS_REF") else 1.0
            rr = R_HALO_MPC * (mass[hid] / m_ref) ** 0.28 * SUB_FRAC ** lvl
            r = rr * rng.random(nh) ** PROFILE_Q
            ct = 2 * rng.random(nh) - 1
            st = np.sqrt(np.maximum(1 - ct ** 2, 0))
            ph = 2 * np.pi * rng.random(nh)
            web[taken] = (pos_e[hid] + r[:, None] *
                          np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)).astype(np.float32)
            del tree
    del Q
    L.web = web
    return L


def render(L, seed):
    slab = SLAB_FRAC * 2 * L.half
    rng = np.random.default_rng(seed + 991)
    img = np.zeros((OUT_N, OUT_N), np.float32)
    web = L.web
    base = ((np.abs(web[:, 2]) < slab / 2).mean() * 1.0) or 1.0
    rep = int(np.clip(round(TARGET_PROJ / max(len(web) * base * 0.9, 1)), 1, 20))
    for k in range(rep):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32) - 0.5) * L.cell
        m = ((np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < L.half)
             & (np.abs(p[:, 1]) < L.half))
        q = p[m]
        ix = np.clip(((q[:, 0] + L.half) / (2 * L.half) * OUT_N).astype(np.int32), 0, OUT_N - 1)
        iy = np.clip(((q[:, 1] + L.half) / (2 * L.half) * OUT_N).astype(np.int32), 0, OUT_N - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
        del p, q
    img = ndimage.gaussian_filter(img, PSF_PX)
    a = M.solve_alpha(img, TARGET_MEAN, gamma=1.0)
    return M.tone(img, a, gamma=1.0)


def run_chain(codes=None, verbose=True, keep_images=True):
    """Deroule la chaine du plus grand au plus petit.

    Ne retient qu'un parent a la fois, et seulement ses champs passe-bas. Les
    images (320x320) sont conservees : elles servent aux controles de continuite
    inter-lignes, et pesent 0,4 Mo chacune.
    """
    todo = [c for c in CHAIN if codes is None or c[0] in codes]
    parent, out = None, []
    if verbose:
        print(f"  {'':4s}{'demi-champ':>11s} {'cellule':>9s} {'grille':>16s}"
              f" {'std(d)':>8s} {'rms(Psi)':>10s} {'halos':>7s}")
    for code, half, margin, seed in todo:
        L = bake_layer(code, half, margin, seed, parent)
        img = render(L, seed) if keep_images else None
        if verbose:
            print(f"  {L.code:4s}{half:11.2f} {L.cell:9.4f} {str(L.shape):>16s}"
                  f" {L.std_delta:8.3f} {L.psi_rms:10.3f} {L.n_halo:7d}")
        L.drop_heavy()
        out.append((L, img))
        if parent is not None:
            parent.delta_lo = None
            parent.psi_lo = None
        parent = L
    return out
