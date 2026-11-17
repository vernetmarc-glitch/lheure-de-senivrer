"""Re-tonalise les tuiles : la densité moyenne devient noire (vides noirs,
seules les surdensités brillent, comme Millennium). On inverse la palette feu
pour retrouver dl, puis on applique la nouvelle borne basse (constante).
Usage : python3 sim/reton.py ENTREE_DIR SORTIE_DIR [LO] [HI_SORTIE]
HI_SORTIE (facultatif) : borne haute propre au jeu de tuiles. La grande boîte (cellules
de 14 Mal) a des contrastes bien plus faibles que la petite : avec les bornes de la
petite, elle sortait presque noire (max 12/255). Bornes constantes, mêmes pour toutes
les époques : jamais de percentile de l'image courante."""
import glob, os, sys
import numpy as np
from PIL import Image
LO0, HI = 0.14, 2.0
LO = float(sys.argv[3]) if len(sys.argv) > 3 else 0.42
HO = float(sys.argv[4]) if len(sys.argv) > 4 else None     # borne haute de sortie (sinon HI)
# époques jeunes (17/11/2026, « éviter le noir ») : écart à la densité moyenne multiplié par
# R(a) = min(3, D(a)^-0,6), D le facteur de croissance — la même fonction que la page
def croissance(a):
    g = lambda x: (lambda om: 2.5 * om / (om ** (4 / 7) - (1 - om) + (1 + om / 2) * (1 + (1 - om) / 70)))(0.315 / (0.315 + 0.685 * x ** 3))
    return a * g(a) / g(1.0)
REHAUSSE = os.environ.get("REHAUSSE", "1") == "1"
PIVOT = 0.376                                              # ton de la densité moyenne (post.py : 1,25·log10 2)
os.makedirs(sys.argv[2], exist_ok=True)
# palette inspirée de Millennium (identique au shader de la page)
BORNES = [0, 0.22, 0.45, 0.65, 0.82, 0.93, 1.0]
COUL = np.array([[0, 0, 0], [0.06, 0.04, 0.26], [0.40, 0.10, 0.52], [0.90, 0.32, 0.30], [1.0, 0.70, 0.32], [1.0, 0.93, 0.70], [1, 1, 1]])
def palette(t):
    return np.stack([np.interp(t, BORNES, COUL[:, k]) for k in range(3)], -1)
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
    if HO is None:
        poids = np.clip((lisse - 0.45) / 0.35, 0, 1)      # 0 dans les vides, 1 dans les structures
    else:
        poids = np.clip((lisse - LO) / (0.25 * (HO - LO)), 0, 1)
    dl = lisse + (dl - lisse) * poids
    if REHAUSSE:
        # plafond 2 et léger adoucissement proportionnel : au-delà, des anneaux autour des grumeaux
        # (grande boîte, REHAUSSE_MAX=3 ADOUCIR=0 : à cette échelle, un grain sans anneaux)
        a = float(os.path.basename(f).split("-a")[1][:6]); R = min(float(os.environ.get("REHAUSSE_MAX", "2")), croissance(a) ** -0.6)
        if R > 1.01 and os.environ.get("ADOUCIR", "1") == "1": dl = gaussian_filter(dl, 1.2 * (R - 1), mode="wrap")
        dl = PIVOT + (dl - PIVOT) * R
    t2 = np.clip((dl - LO) / ((HO or HI) - LO), 0, 1)
    rgb = palette(t2)
    Image.fromarray((rgb * 255).astype(np.uint8)).save(f"{sys.argv[2]}/{os.path.basename(f)}", quality=88)
print("ok")
