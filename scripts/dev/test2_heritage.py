"""TEST UNITAIRE 2 -- heritage de particules entre layers adjacents (G -> F).

Enjeu : Marc demande un heritage a 100%, pas les 55% de variance de la
production. Avec un champ, "heriter" = correler des phases (partiel, et detruit
par tout operateur non lineaire en aval : 0.08-0.43 mesure historiquement).
Avec des particules, l'ensemble enfant se DEFINIT comme
   (particules du parent dans la fenetre)  U  (nouvelles particules fines)
donc l'heritage est exact par construction.

Conditions verifiees ici :
  1. delta_enfant = crop_upsample(delta_parent) + detail STRICTEMENT passe-haut
     (pas de ponderation 0.74/0.67 qui diluerait l'heritage)
  2. Psi unique decoupe en bandes de k : la particule heritee recoit un
     INCREMENT de deplacement, jamais un nouveau deplacement
  3. les particules parentes gardent leur identite (meme indice, meme origine)
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M
import zel_particles as Z

G_BOX, G_HALF = 450.0, 150.0
F_BOX, F_HALF = 201.24, 67.08
NF = 384
SLAB = 0.06
OUT = 512
AMP = 6.0


def psi_field(delta, box, n, k_lo=0.0, k_hi=None):
    """Psi = i k delta_k / k^2 restreint a la bande [k_lo, k_hi]."""
    KX, KY, KZ, kmag = M.k_grid3(n, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    hi = np.inf if k_hi is None else k_hi
    band = (kmag >= k_lo) & (kmag <= hi)
    out = np.empty((n, n, n, 3), np.float32)
    for a, K in enumerate((KX, KY, KZ)):
        out[..., a] = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=(n,) * 3)
    return out


def sample_psi(psi, box, pts):
    """Interpolation trilineaire de Psi aux positions continues pts."""
    n = psi.shape[0]
    c = ((pts + box / 2.0) / box * n).T
    return np.stack([ndimage.map_coordinates(psi[..., a], c, order=1, mode="wrap")
                     for a in range(3)], axis=1).astype(np.float32)


def glass(box, n_side, seed, zlim=None):
    """Verre : reseau + jitter d'une demi-cellule (cf. test 1)."""
    rng = np.random.default_rng(seed)
    cell = box / n_side
    g = (np.arange(n_side) + 0.5) * cell - box / 2
    gz = g if zlim is None else g[np.abs(g) < zlim]
    Q = np.stack(np.meshgrid(g, g, gz, indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    return Q + (rng.random(Q.shape).astype(np.float32) - 0.5) * cell


def peaks(img, k=200):
    mx = ndimage.maximum_filter(img, size=7)
    m = (img >= mx) & (img > np.percentile(img, 97))
    idx = np.argwhere(m)
    return idx[np.argsort(img[m])[::-1][:k]]


def compare(tG, tF, label):
    from scipy.spatial import cKDTree
    a = ndimage.gaussian_filter(tG, 2)
    b = ndimage.gaussian_filter(tF, 2)
    corr = np.corrcoef(a.ravel(), b.ravel())[0, 1]
    kA, kB = peaks(a), peaks(b)
    d, _ = cKDTree(kB).query(kA)
    print(f"{label}")
    print(f"  correlation            {corr:.3f}      [cible >= 0.85 ; depot CIC historique 0.08-0.43]")
    print(f"  appariement des pics   median {np.median(d):.2f} px | "
          f"<=1.5px {float((d<=1.5).mean()):.2f} | <=4px {float((d<=4).mean()):.2f}")
    print(f"  ecart moyenne          {abs(tG.mean()-tF.mean())*255:.2f}/255   [cible < 2]")
    print(f"  ecart ecart-type       {abs(tG.std()-tF.std())/tG.std()*100:.1f}%     [cible < 10]")
    return corr
