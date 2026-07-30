"""Normalisation ABSOLUE du champ de densite par sigma_8.

Defaut corrige : `gen_delta3` normalise delta a variance unite DANS CHAQUE BOITE
(`f / f.std()`). C'est un artefact de code, pas une physique. Consequences :

  - l'amplitude du deplacement de Zel'dovich devenait proportionnelle a la boite
    (932 Mpc a M !), la marge de dalle depassait la dalle elle-meme ;
  - la coherence inter-layer dependait d'une normalisation arbitraire ;
  - le « End of Greatness » devait etre impose au lieu d'emerger.

Avec une normalisation absolue (sigma_8 = 0,81 sur une sphere top-hat de
8 Mpc/h = 11,87 Mpc), les trois se resolvent d'eux-memes :

  - Psi ~ 6 Mpc a toutes les echelles, sature quand la boite depasse la longueur
    de coherence -- une petite boite ne contient que le deplacement INTERNE ;
  - les grandes boites ont naturellement une faible amplitude aux echelles
    qu'elles resolvent : l'univers y est homogene, c'est le fait physique.

La constante de calibration doit etre INDEPENDANTE de la boite et de la grille ;
c'est ce que verifie `check_invariance()`.
"""
import numpy as np
import mcpm_web as M

SIGMA8 = 0.81
H = 0.674
R8_MPC = 8.0 / H          # 8 Mpc/h en Mpc


def tophat_W(x):
    x = np.maximum(x, 1e-8)
    return 3.0 * (np.sin(x) - x * np.cos(x)) / x ** 3


def sigma_R_of_shape(shape, box, R):
    """sigma(R) que produit P(k) BRUT sur cette grille, par somme sur les modes."""
    kx = np.fft.fftfreq(shape[0], d=box[0] / shape[0]) * 2 * np.pi
    ky = np.fft.fftfreq(shape[1], d=box[1] / shape[1]) * 2 * np.pi
    kz = np.fft.rfftfreq(shape[2], d=box[2] / shape[2]) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing="ij")
    kmag = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    P = M.power_spectrum(kmag)
    W = tophat_W(kmag * R)
    # poids 2 pour les modes rfft replies (sauf plans kz=0 et Nyquist)
    wgt = np.full(kmag.shape, 2.0)
    wgt[..., 0] = 1.0
    if shape[2] % 2 == 0:
        wgt[..., -1] = 1.0
    V = box[0] * box[1] * box[2]
    return float(np.sqrt((P * W ** 2 * wgt).sum() / V))


# Grille de REFERENCE pour la normalisation : elle doit resoudre largement
# R8 = 11,87 Mpc. La calculer sur la grille courante est un piege -- a M la
# cellule vaut 219 Mpc, le top-hat de 11,87 Mpc n'est pas resolu du tout,
# sigma_8 mesure s'effondre et le facteur explose (Psi passait a 78 Mpc).
_REF_SHAPE = (256, 256, 256)
_REF_BOX = (300.0, 300.0, 300.0)
_NORM = None


def norm_factor(shape=None, box=None):
    """Facteur ABSOLU, calcule une seule fois sur la grille de reference."""
    global _NORM
    if _NORM is None:
        _NORM = SIGMA8 / max(sigma_R_of_shape(_REF_SHAPE, _REF_BOX, R8_MPC), 1e-30)
    return _NORM


def gen_delta_abs(shape, box, seed):
    """delta a normalisation ABSOLUE -- pas de division par f.std()."""
    rng = np.random.default_rng(seed)
    kx = np.fft.fftfreq(shape[0], d=box[0] / shape[0]) * 2 * np.pi
    ky = np.fft.fftfreq(shape[1], d=box[1] / shape[1]) * 2 * np.pi
    kz = np.fft.rfftfreq(shape[2], d=box[2] / shape[2]) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing="ij")
    kmag = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    P = M.power_spectrum(kmag)
    dk = (rng.normal(size=kmag.shape) + 1j * rng.normal(size=kmag.shape))
    dk *= np.sqrt(P / 2.0) * np.prod(shape) ** 0.5
    f = np.fft.irfftn(dk, s=shape)
    # amener a l'amplitude absolue : le champ brut a un sigma_8 connu
    f = f * norm_factor()
    return f.astype(np.float32)


def psi_rms(shape, box, lam_min):
    """rms du deplacement de Zel'dovich, en Mpc, pour cette boite et cette bande.

    Psi_k = i k delta_k / k^2  ->  <Psi^2> = somme P(k)/k^2 / V  (par composante).
    """
    kx = np.fft.fftfreq(shape[0], d=box[0] / shape[0]) * 2 * np.pi
    ky = np.fft.fftfreq(shape[1], d=box[1] / shape[1]) * 2 * np.pi
    kz = np.fft.rfftfreq(shape[2], d=box[2] / shape[2]) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing="ij")
    kmag = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    P = M.power_spectrum(kmag) * norm_factor() ** 2
    band = (kmag > 0) & (kmag <= 2 * np.pi / lam_min)
    wgt = np.full(kmag.shape, 2.0)
    wgt[..., 0] = 1.0
    if shape[2] % 2 == 0:
        wgt[..., -1] = 1.0
    V = box[0] * box[1] * box[2]
    s2 = (np.where(band, P / np.maximum(kmag ** 2, 1e-30), 0) * wgt).sum() / V
    return float(np.sqrt(s2 / 3.0))


def check_invariance():
    """sigma_8 doit sortir a 0.81 quelles que soient la boite et la grille."""
    out = []
    for shape, box in [((128,) * 3, (300.,) * 3), ((192,) * 3, (300.,) * 3),
                       ((192,) * 3, (900.,) * 3), ((256,) * 3, (2400.,) * 3),
                       ((192, 192, 48), (900., 900., 225.))]:
        nf = norm_factor()
        s8 = sigma_R_of_shape(shape, box, R8_MPC) * nf
        out.append((shape, box, nf, s8))
    return out
