"""TEST UNITAIRE 1 -- distribution initiale et dissolution temporelle.

Enjeu (cf. analyse §4) : en remontant le temps, Psi -> 0 et les particules
reviennent sur leurs positions lagrangiennes. Si celles-ci forment un RESEAU
REGULIER, l'etat dissous est un cristal periodique -> pics de Bragg -> exactement
l'artefact de maille axiale identifie par Marc. Il faut une distribution en
VERRE (uniforme a grande echelle, sans periodicite).

Criteres (§11.2 / §11.4.b) :
  - ANISO ~ 1.0 a TOUTE epoque, y compris A=0
  - contenu haute frequence non nul jusqu'a la dissolution totale
  - A(s,a=1) = 1 exactement, sans saut
  - convergence vers "uniforme + grenaille", jamais vers un gris plat
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M
import zel_particles as Z

BOX = 450.0
HALF = 150.0
SLAB = 0.06
N_FIELD = 384
OUT = 512


def psi_slab(n_field, box, seed, half_mpc, slab_frac, amp, lam_min_mpc=1.318359):
    """Psi echantillonne aux positions du reseau, restreint au voisinage de la tranche."""
    delta = M.gen_delta3(n_field, box, seed)
    KX, KY, KZ, kmag = M.k_grid3(n_field, box)
    dk = np.fft.rfftn(delta)
    del delta
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = kmag <= 2 * np.pi / lam_min_mpc
    cell = box / n_field
    z_half = slab_frac * 2 * half_mpc / 2.0 + 4.0 * amp
    iz = np.arange(n_field)[np.abs((np.arange(n_field) + 0.5) * cell - box / 2) < z_half]
    gx = (np.arange(n_field) + 0.5) * cell - box / 2
    gz = (iz + 0.5) * cell - box / 2
    P = np.empty((n_field, n_field, len(iz), 3), np.float32)
    rms2 = 0.0
    for a, K in enumerate((KX, KY, KZ)):
        p = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=(n_field,) * 3).astype(np.float32)
        rms2 += float(np.mean(p ** 2))
        P[..., a] = p[:, :, iz]
        del p
    scale = amp / max(np.sqrt(rms2 / 3.0), 1e-9)
    Q = np.stack(np.meshgrid(gx, gx, gz, indexing="ij"), axis=-1).astype(np.float32)
    return Q.reshape(-1, 3), (P.reshape(-1, 3) * scale), cell


def initial_positions(Q, cell, mode, seed=11):
    """reseau | jitter (verre approche) | poisson"""
    rng = np.random.default_rng(seed)
    if mode == "reseau":
        return Q
    if mode == "jitter":
        return Q + (rng.random(Q.shape).astype(np.float32) - 0.5) * cell
    if mode == "poisson":
        lo = Q.min(0)
        hi = Q.max(0) + cell
        return (lo + rng.random(Q.shape).astype(np.float32) * (hi - lo)).astype(np.float32)
    raise ValueError(mode)


def render(pos, psf=0.45, target=68.0):
    img, cnt = Z.project(pos, BOX, HALF, SLAB, OUT, psf=psf)
    return M.tone(img, M.solve_alpha(img, target), gamma=1.0), cnt


def hf_content(t):
    """variance du laplacien : indicateur direct de contenu haute frequence (§11.2)"""
    return float(np.var(ndimage.laplace(t)))


def lowk_power(t, kmax=6):
    """puissance aux tres grandes echelles : doit rester faible a A=0 (uniformite)"""
    p = Z.spec(t)
    return float(p[:kmax].mean() / p[40:].mean())


def A_of_a(a, a_form):
    """Courbe A(s,a) du §11.4.b, AVEC le correctif de continuite du 13 juillet."""
    w = max(-np.log10(a_form), 0.05)
    centre = min(np.log10(a_form), -w)
    x = np.log10(a) - centre
    t = np.clip((x + w) / (2 * w), 0, 1)
    return np.where(a >= 1.0, 1.0, t * t * (3 - 2 * t))
