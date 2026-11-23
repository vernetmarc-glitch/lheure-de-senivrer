"""Règles de couleur de surface apprises sur la référence (N25, D-43).

Pour chaque classe (altitude, pente) du relief réel, la couleur médiane de la mosaïque
Sentinel-2 sans nuages. La page applique cette même table à tous les états du film,
avec une altitude « climatique » décalée selon l'époque (ligne de neige et de la forêt
plus haute aux temps chauds, plus basse aux glaciations) : roche, forêt, neige suivent
les mêmes règles à toutes les époques.

Entrées : sim/reel_1024.npz, donnees/mosaique_2048.jpg.
Sortie : donnees/regles.png (largeur = altitude 0–5000 m par 50 m ; hauteur = pente
0–64° par 4°), couleurs sRGB.
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app", "public", "labo", "alpes", "donnees")
NA, DA, NP, DP = 100, 50.0, 16, 4.0


def main():
    h = np.load(os.path.join(ICI, "reel_1024.npz"))["h"].astype(np.float64)
    m = np.asarray(Image.open(os.path.join(DON, "mosaique_2048.jpg")).convert("RGB"), np.float64)
    m = m.reshape(1024, 2, 1024, 2, 3).mean(axis=(1, 3))
    gy, gx = np.gradient(h, 200.0)
    pente = np.degrees(np.arctan(np.hypot(gx, gy)))
    ia = np.clip((h / DA).astype(int), 0, NA - 1)
    ip = np.clip((pente / DP).astype(int), 0, NP - 1)
    lut = np.full((NP, NA, 3), np.nan)
    cnt = np.zeros((NP, NA), int)
    cle = ip * NA + ia
    for k in np.unique(cle):
        sel = cle == k
        cnt.flat[k] = sel.sum()
        if sel.sum() >= 8:
            lut[k // NA, k % NA] = np.median(m.reshape(-1, 3)[sel.ravel()], axis=0)
    # combler les classes vides : la plus proche en altitude, puis en pente
    for p in range(NP):
        ok = ~np.isnan(lut[p, :, 0])
        if ok.any():
            for c in range(3):
                lut[p, :, c] = np.interp(np.arange(NA), np.where(ok)[0], lut[p, ok, c])
    for a in range(NA):
        ok = ~np.isnan(lut[:, a, 0])
        for c in range(3):
            lut[:, a, c] = np.interp(np.arange(NP), np.where(ok)[0], lut[ok, a, c])
    lut = gaussian_filter1d(gaussian_filter1d(lut, 1.0, axis=1), 0.7, axis=0)
    Image.fromarray(np.clip(np.round(lut), 0, 255).astype(np.uint8)).save(os.path.join(DON, "regles.png"))
    print("règles :", lut.shape, "classes pleines", int((cnt >= 8).sum()), flush=True)


if __name__ == "__main__":
    main()
