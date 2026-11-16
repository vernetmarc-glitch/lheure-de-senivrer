"""Rendu des découpes TNG50 : la Voie lactée vue de face à chaque époque.

Usage : python3 sim/tng/rendu.py DOSSIER_DECOUPES SORTIE.png
Unités physiques : kpc propres (Coordinates ckpc/h × a / h).
"""
import glob, sys
import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

H, BOITE = 0.6774, 35000.0
DEMI = 40.0      # demi-champ en kpc propres
NPX = 512


def charge(fic):
    with h5py.File(fic) as f:
        a = f["Header"].attrs["Time"]; z = f["Header"].attrs["Redshift"]
        e = f["PartType4"] if "PartType4" in f else None
        g = f["PartType0"] if "PartType0" in f else None
        st = {k: e[k][:] for k in e} if e is not None else {}
        ga = {k: g[k][:] for k in g} if g is not None else {}
    return a, z, st, ga


def centre(x, m):
    c = np.average(x, axis=0, weights=m)
    r = np.sqrt(((x - c) ** 2).sum(1)).max()
    while r > 2:
        s = ((x - c) ** 2).sum(1) < r * r
        if s.sum() < 50: break
        c = np.average(x[s], axis=0, weights=m[s]); r *= 0.8
    return c


def phys(X, a, ref):
    d = X - ref
    d -= BOITE * np.round(d / BOITE)
    return d * a / H


def rotation(x, v, m, r=10):
    s = (x ** 2).sum(1) < r * r
    L = (m[s, None] * np.cross(x[s], v[s])).sum(0)
    n = L / np.linalg.norm(L)
    u = np.cross(n, [1, 0, 0]); u /= np.linalg.norm(u)
    w = np.cross(n, u)
    return np.stack([u, w, n])


def image(x, poids, sig=1):
    from scipy.ndimage import gaussian_filter
    h, _, _ = np.histogram2d(x[:, 0], x[:, 1], bins=NPX, range=[[-DEMI, DEMI]] * 2,
                             weights=poids)
    return gaussian_filter(h.T, sig)


def rendu(fic):
    a, z, st, ga = charge(fic)
    ref = st["Coordinates"][np.argmax(st["Masses"])]
    xs = phys(st["Coordinates"], a, ref)
    vit = st["Velocities"] * np.sqrt(a)
    c = centre(xs, st["Masses"]); xs -= c
    R = rotation(xs, vit - np.average(vit, axis=0, weights=st["Masses"]), st["Masses"])
    xs = xs @ R.T
    age_a = st["GFM_StellarFormationTime"]
    ok = age_a > 0                                  # exclut les cellules de vent
    jeune = ok & (age_a > a * 0.85)
    I_vieux = image(xs[ok], st["Masses"][ok], 1.0)
    I_jeune = image(xs[jeune], st["Masses"][jeune], 1.2)
    I_gaz = 0
    if ga:
        xg = (phys(ga["Coordinates"], a, ref) - c) @ R.T
        I_gaz = image(xg, ga["Masses"], 2.0)
    # ton fixe (unités : 1e10 Msun/h par pixel) — constantes, pas de percentile
    t = lambda I, lo, hi: np.clip((np.log10(I + 1e-12) - lo) / (hi - lo), 0, 1)
    v, j, g = t(I_vieux, -6.5, -2.5), t(I_jeune, -7, -3.5), t(I_gaz, -6, -3) if ga else 0
    rgb = np.stack([1.0 * v + 0.35 * j + 0.55 * g,
                    0.78 * v + 0.6 * j + 0.18 * g,
                    0.55 * v + 1.0 * j + 0.12 * g], -1)
    im = Image.fromarray((np.clip(rgb, 0, 1) ** 0.9 * 255).astype(np.uint8)[::-1])
    return im, z, a


def age_gyr(a):
    # Planck 2015 (TNG) : t(a)
    Om, H0 = 0.3089, 67.74
    OL = 1 - Om
    return 2 / (3 * np.sqrt(OL)) * np.arcsinh(np.sqrt(OL / Om) * a ** 1.5) * 977.8 / H0


if __name__ == "__main__":
    fics = sorted(glob.glob(f"{sys.argv[1]}/decoupe-*.hdf5"))
    vignettes = []
    for f in fics:
        im, z, a = rendu(f)
        d = ImageDraw.Draw(im)
        d.text((10, 10), f"{age_gyr(a):.1f} Ga  (z = {z:.2f})", fill=(230, 230, 230))
        d.line([(10, NPX - 16), (10 + NPX * 10 / (2 * DEMI), NPX - 16)], fill=(200, 200, 200), width=2)
        d.text((12, NPX - 34), "10 kpc", fill=(200, 200, 200))
        im.save(f.replace(".hdf5", ".png"))
        vignettes.append((a, im))
        print(f, f"{age_gyr(a):.2f} Ga", flush=True)
    vignettes.sort(key=lambda x: x[0])
    n = len(vignettes); col = 4; lig = (n + col - 1) // col
    P = Image.new("RGB", (col * NPX, lig * NPX))
    for k, (_, im) in enumerate(vignettes):
        P.paste(im, ((k % col) * NPX, (k // col) * NPX))
    P.save(sys.argv[2])
