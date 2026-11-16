"""Rendu adaptatif « à la Millennium » : noyau dont la taille suit la densité locale
(comme un rendu SPH), ton logarithmique à bornes fixes, palette feu.
Usage : render2.py x.npy L epaisseur N sortie [demi_champ] [a]
Le demi-champ est en Mpc/h comobiles ; a sert à afficher la distance propre (échelle fixe).
"""
import numpy as np, sys
from scipy.ndimage import gaussian_filter
from PIL import Image

x = np.load(sys.argv[1]); L = float(sys.argv[2]); th = float(sys.argv[3])
N = int(sys.argv[4]); out = sys.argv[5]
half = float(sys.argv[6]) if len(sys.argv) > 6 else L / 2
a = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
c = np.array([float(v) for v in __import__('os').environ.get('CENTRE', f'{L/2},{L/2},{L/2}').split(',')])
d = (x - c + L / 2) % L - L / 2              # centré, périodique
sel = np.abs(d[:, 2]) < th / 2
# échelle fixe en distance PROPRE : à a < 1, la matière se resserre vers le centre
ds = d[sel, :2]
k = int(np.ceil(half / a / L - 0.5))           # répétitions périodiques nécessaires
if k > 0:
    off = np.array([(i * L, j * L) for i in range(-k, k + 1) for j in range(-k, k + 1)], np.float32)
    ds = (ds[None, :, :] + off[:, None, :]).reshape(-1, 2)
u = ds[:, 0] * a / half * 0.5 + 0.5
v = ds[:, 1] * a / half * 0.5 + 0.5
m = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
img, _, _ = np.histogram2d(v[m], u[m], bins=N, range=[[0, 1], [0, 1]])
img = img.astype(np.float64)
# densité moyenne attendue par pixel (constante analytique, pas une statistique de l'image)
npart_slab = x.shape[0] * th / L
px_mpc = 2 * half / N / a                    # taille d'un pixel en Mpc/h comobiles
mean = npart_slab / (L * L) * px_mpc**2  # identique à toute époque en comobile
MODE = __import__("os").environ.get("MODE", "reflect")
levels = [0.6, 1.2, 2.4, 4.8, 9.6]
S = [gaussian_filter(img, s, mode=MODE) for s in levels]
NGB = float(__import__("os").environ.get("NGB", 32))
out_img = S[-1].copy()
chosen = np.zeros(img.shape, bool)
for s, Ss in zip(levels, S):
    ok = (Ss * 2 * np.pi * s * s >= NGB) & ~chosen
    out_img[ok] = Ss[ok]
    chosen |= ok
glow = gaussian_filter(out_img, 8, mode=MODE)
dl = np.log10(1 + out_img / mean) + 0.25 * np.log10(1 + glow / mean)
lo, hi = float(__import__("os").environ.get("LO", 0.4)), float(__import__("os").environ.get("HI", 2.1))
t = np.clip((dl - lo) / (hi - lo), 0, 1)
r = np.clip(t * 1.75, 0, 1)
g = np.clip((t - 0.40) * 1.75, 0, 1) ** 1.1
b = np.clip((t - 0.80) * 3.5, 0, 1)
rgb = (np.stack([r, g, b], -1) * 255).astype(np.uint8)
Image.fromarray(rgb).save(out)
print(out, "particules :", int(m.sum()))
