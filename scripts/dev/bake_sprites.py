"""Port Python de scripts/generate_dissolution_sprites.mjs.

Reproduit la chaine de cuisson a l'identique pour pouvoir l'appliquer aux 89
galaxies sans sprite (option C, test 7) :

  1. depot gaussien des particules, sigma_px = POINT_SIZE * (1 + p*(HALO_GROWTH-1))
     amplitude par particule = 0.18 + b*0.55
  2. flou croissant : blur_px = progress^1.5 * BLUR_MAX_PX
  3. ton saturant : 1 - exp(-champ)
  4. modulation filamenteuse par BRUIT DE VALEUR MULTI-OCTAVE :
        filIntensity = FILAMENT_AMOUNT * 4 * p * (1-p)      (cloche, nulle aux bouts)
        v = tone * (1 + (bruit - 0.5) * 2 * filIntensity)
  5. clamp [0,1]

L'aspect filamenteux vient donc du RENDU, pas de la dynamique -- constat etabli
en lisant le script de production le 28 juillet.
"""
import numpy as np
from scipy import ndimage

N = 512
POINT_SIZE = 0.5
HALO_GROWTH = 8.5
BLUR_MAX_PX = 6.0
FILAMENT_AMOUNT = 0.8


def value_noise(n, grid, seed):
    """Bruit de valeur : grille aleatoire + interpolation lisse (smoothstep)."""
    rng = np.random.default_rng(seed)
    g = max(int(round(grid)), 2)
    lat = rng.random((g + 1, g + 1)) * 2 - 1
    t = (np.arange(n) + 0.5) / n * g
    i0 = np.clip(t.astype(int), 0, g - 1)
    f = t - i0
    s = f * f * (3 - 2 * f)
    a = lat[np.ix_(i0, i0)]
    b = lat[np.ix_(i0 + 1, i0)]
    c = lat[np.ix_(i0, i0 + 1)]
    d = lat[np.ix_(i0 + 1, i0 + 1)]
    sx = s[:, None]
    sy = s[None, :]
    return (a * (1 - sx) * (1 - sy) + b * sx * (1 - sy)
            + c * (1 - sx) * sy + d * sx * sy)


def multi_octave_cloud(n, seed=5151, base=8):
    o1 = value_noise(n, base, seed)
    o2 = value_noise(n, base * 2.4, seed + 1)
    o3 = value_noise(n, base * 5.5, seed + 2)
    return (o1 * 0.55 + o2 * 0.3 + o3 * 0.15 + 1) / 2


_CLOUD = {}


def cloud_for(n):
    if n not in _CLOUD:
        _CLOUD[n] = multi_octave_cloud(n)
    return _CLOUD[n]


def bake_frame(pos_xy, bright, progress, half_width, n=N, filament=True):
    """Cuit une frame de sprite. pos_xy en unites de half_width."""
    sigma_px = max(POINT_SIZE * (1 + progress * (HALO_GROWTH - 1)), 0.5)
    px = n / 2 + pos_xy[:, 0] / half_width * (n / 2)
    py = n / 2 + pos_xy[:, 1] / half_width * (n / 2)
    amp = 0.18 + bright * 0.55
    field = np.zeros((n, n), np.float64)
    ix = np.clip(px.astype(int), 0, n - 1)
    iy = np.clip(py.astype(int), 0, n - 1)
    ok = (px > -3 * sigma_px) & (px < n + 3 * sigma_px) \
        & (py > -3 * sigma_px) & (py < n + 3 * sigma_px)
    np.add.at(field, (iy[ok], ix[ok]), amp[ok] if np.ndim(amp) else amp)
    # le depot gaussien du script est equivalent a un splat unite convolue
    field = ndimage.gaussian_filter(field, sigma_px) * (2 * np.pi * sigma_px ** 2)

    blur_px = progress ** 1.5 * BLUR_MAX_PX
    if blur_px >= 0.5:
        field = ndimage.gaussian_filter(field, blur_px)

    tone = 1 - np.exp(-field)
    if filament:
        fi = FILAMENT_AMOUNT * 4 * progress * (1 - progress)
        tone = tone * (1 + (cloud_for(n) - 0.5) * 2 * fi)
    return np.clip(tone, 0, 1)


def expand(pos, vel, progress, spread=7.7):
    """Dissolution cinematique : expansion auto-similaire le long des orbites.

    La dynamique n'a plus besoin de produire des courants -- c'est la
    modulation de rendu qui donne le caractere filamenteux.
    """
    return pos + vel * progress * spread


def bake_frame_conservative(pos_xy, bright, progress, half_width, n=N,
                            filament=True, blur_scale=1.0):
    """Variante A FLUX CONSERVE : le total depose par particule est constant.

    Le splat s'elargit avec `progress` mais son integrale reste egale a `amp`.
    La brillance de surface chute donc comme 1/s^2 quand l'objet se dilate d'un
    facteur s -- c'est le comportement d'une goutte d'encre qui se diffuse :
    elle s'etale ET palit, la matiere totale etant conservee.

    (Le script de production multiplie au contraire le flux par ~72 en dilatant
    le splat sans le renormaliser ; mesure sur andromede : 830 -> 64071.)
    """
    sigma_px = max(POINT_SIZE * (1 + progress * (HALO_GROWTH - 1)), 0.5)
    px = n / 2 + pos_xy[:, 0] / half_width * (n / 2)
    py = n / 2 + pos_xy[:, 1] / half_width * (n / 2)
    amp = 0.18 + bright * 0.55
    field = np.zeros((n, n), np.float64)
    ix = np.clip(px.astype(int), 0, n - 1)
    iy = np.clip(py.astype(int), 0, n - 1)
    ok = (px >= 0) & (px < n) & (py >= 0) & (py < n)
    np.add.at(field, (iy[ok], ix[ok]), (amp[ok] if np.ndim(amp) else amp))
    field = ndimage.gaussian_filter(field, sigma_px)   # PAS de x 2 pi sigma^2

    blur_px = progress ** 1.5 * BLUR_MAX_PX * blur_scale
    if blur_px >= 0.5:
        field = ndimage.gaussian_filter(field, blur_px)

    tone = 1 - np.exp(-field)
    if filament:
        fi = FILAMENT_AMOUNT * 4 * progress * (1 - progress)
        tone = tone * (1 + (cloud_for(n) - 0.5) * 2 * fi)
    return np.clip(tone, 0, 1)
