"""Aperçu hors navigateur de la danse (même interpolation que le shader).

Usage : python3 sim/tng/apercu.py SUIVI.npz SORTIE_DOSSIER [DEMI_KPC] [NB_IMAGES]
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

NPX = 540
# ton : bornes FIXES en points par kpc² (pas de statistique de l'image)
LO, HI = 0.6, 4.2


def etat(D, t):
    ts, r, phi, k, h, tn = D["t"], D["r"], D["phi"], D["k"], D["h"], D["naiss"]
    E = len(ts)
    if t >= ts[-1]:
        i, j, f = E - 2, E - 1, 1 + (t - ts[-1]) / (ts[-1] - ts[-2])
    else:
        j = int(np.searchsorted(ts, t)); j = max(j, 1); i = j - 1
        f = (t - ts[i]) / (ts[j] - ts[i])
    r0, r1 = r[i], r[j]
    d = phi[j] - phi[i]; d -= 2 * np.pi * np.round(d / (2 * np.pi)); d += 2 * np.pi * k[i]
    p0, p1 = np.isfinite(r0), np.isfinite(r1)
    fc = min(f, 1.0)
    rr = np.where(p0 & p1, r0 + (np.nan_to_num(r1) - np.nan_to_num(r0)) * fc, np.where(p1, r1, r0))
    ph = np.where(p0 & p1, phi[i] + d * f, np.where(p1, phi[j], phi[i]))
    al = np.where(p0 & p1, 1.0, np.where(p1, fc, np.where(p0, 1 - fc, 0.0)))
    hh = h[i] + (h[j] - h[i]) * fc
    age = t - tn
    al = al * (age > -0.02)
    return rr * np.cos(ph), rr * np.sin(ph), al * D.get("poids", 1), hh, age


def image(D, t, demi):
    x, y, al, hh, age = etat(D, t)
    ok = al > 0.002
    x, y, al, hh, age = x[ok], y[ok], al[ok], hh[ok], age[ok]
    jeune = np.exp(-np.maximum(age, 0) / 0.35)
    col = np.stack([0.95 - 0.35 * jeune, 0.78 - 0.05 * jeune, 0.52 + 0.48 * jeune], -1)
    col *= (1 + 7 * jeune)[:, None]               # lumière : les jeunes étoiles brillent
    ppk = NPX / (2 * demi)
    N = len(D["naiss"])
    # chaque point pèse 1 (point/kpc² ensuite) ; noyau gaussien σ = h/2 (≥ 0,6 px)
    sig = np.maximum(0.5 * hh * ppk, 0.6)
    acc = np.zeros((NPX, NPX, 3))
    classes = np.geomspace(0.6, 60, 14)
    cl = np.clip(np.searchsorted(classes, sig), 0, len(classes) - 1)
    for c in np.unique(cl):
        s = cl == c
        for ch in range(3):
            hgr, _, _ = np.histogram2d(y[s], x[s], bins=NPX, range=[[-demi, demi]] * 2, weights=al[s] * col[s, ch])
            acc[..., ch] += gaussian_filter(hgr, classes[c])
    lum = acc.sum(-1) / 2.25 * ppk ** 2          # points/kpc² environ
    tt = np.clip((np.log10(lum + 1e-9) - LO) / (HI - LO), 0, 1)
    tt = 1 - np.exp(-2.6 * tt)                    # épaule douce : pas de saturation brutale
    chrom = acc / np.maximum(acc.max(-1, keepdims=True), 1e-12)
    rgb = chrom * tt[..., None] / (1 - np.exp(-2.6))
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)[::-1])


if __name__ == "__main__":
    D = dict(np.load(sys.argv[1]))
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    demi = float(sys.argv[3]) if len(sys.argv) > 3 else 35
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    ts = np.linspace(1.2, 13.8, n)
    ims = []
    for t in ts:
        im = image(D, t, demi)
        ImageDraw.Draw(im).text((10, 10), f"{t:.1f} Ga", fill=(220, 220, 220))
        ims.append(im)
    col = 4; lig = (n + col - 1) // col
    P = Image.new("RGB", (col * NPX, lig * NPX))
    for k, im in enumerate(ims):
        P.paste(im, ((k % col) * NPX, (k // col) * NPX))
    P.save(f"{out}/planche.png")
    print("ok")
