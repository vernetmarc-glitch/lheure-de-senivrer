"""Re-tonalise les tuiles : la densité moyenne devient noire (vides noirs,
seules les surdensités brillent, comme Millennium). On inverse la palette feu
pour retrouver dl, puis on applique la nouvelle borne basse (constante).
Usage : python3 sim/reton.py ENTREE_DIR SORTIE_DIR [LO]"""
import glob, os, sys
import numpy as np
from PIL import Image
LO0, HI = 0.14, 2.0
LO = float(sys.argv[3]) if len(sys.argv) > 3 else 0.42
os.makedirs(sys.argv[2], exist_ok=True)
for f in sorted(glob.glob(f"{sys.argv[1]}/*.jpg")):
    c = np.asarray(Image.open(f).convert("RGB")).astype(float) / 255
    R, G, B = c[..., 0], c[..., 1], c[..., 2]
    t = np.where(R < 0.97, R / 1.75, np.where(G < 0.97, 0.4 + np.clip(G, 0, 1) ** (1 / 1.1) / 1.75, 0.8 + B / 3.5))
    dl = LO0 + t * (HI - LO0)
    # la grille de départ de la simulation (période N/128 px, mesurée) : coupe-bandes
    # sur les lignes de Fourier kx, ky = 128·m (et leurs harmoniques)
    N = dl.shape[0]; k = np.abs(np.fft.fftfreq(N) * N); w = 3.0
    filt = np.ones(N)
    for m in range(1, int(N / 2 / 128) + 1):
        filt *= 1 - np.exp(-0.5 * ((k - 128 * m) / w) ** 2)
    dl = np.real(np.fft.ifft2(np.fft.fft2(dl) * filt[:, None] * filt[None, :]))
    # résidu de grille déformée dans les zones peu denses : lissage là seulement
    from scipy.ndimage import gaussian_filter
    lisse = gaussian_filter(dl, 4.0, mode="wrap")
    poids = np.clip((lisse - 0.45) / 0.35, 0, 1)          # 0 dans les vides, 1 dans les structures
    dl = lisse + (dl - lisse) * poids
    t2 = np.clip((dl - LO) / (HI - LO), 0, 1)
    rgb = np.stack([np.clip(t2 * 1.75, 0, 1), np.clip((t2 - 0.4) * 1.75, 0, 1) ** 1.1, np.clip((t2 - 0.8) * 3.5, 0, 1)], -1)
    Image.fromarray((rgb * 255).astype(np.uint8)).save(f"{sys.argv[2]}/{os.path.basename(f)}", quality=88)
print("ok")
