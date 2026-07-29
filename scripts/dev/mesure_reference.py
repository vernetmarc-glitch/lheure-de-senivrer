"""Mesure la SIGNATURE d'une image de reference visuelle.

Une image seule ne sert a rien a une nouvelle instance : il faut la MESURER pour
pouvoir comparer un rendu candidat. Ce script produit les sept grandeurs qui font
la signature, dans la palette du projet.

    python3 mesure_reference.py docs/reference-visuelle/reference-toile-cosmique.jpg
    python3 mesure_reference.py mon_rendu.png --compare
"""
import sys
import numpy as np
from scipy import ndimage
from PIL import Image

ASTRO = np.array([[0, 0, 0], [0x17, 0x0a, 0x05], [0x4a, 0x1f, 0x0a],
                  [0xa8, 0x48, 0x0f], [0xe8, 0xa1, 0x3a], [0xff, 0xf3, 0xd6]], np.float32)


def astro_palette(t):
    t = np.clip(t, 0, 1); n = len(ASTRO) - 1
    i = np.clip((t * n).astype(np.int32), 0, n - 1)
    f = (t * n - i)[..., None]
    return ASTRO[i] * (1 - f) + ASTRO[i + 1] * f


def to_tone(path, crop=8):
    """Inverse la palette Astro : chaque pixel -> position dans la rampe."""
    a = np.array(Image.open(path).convert("RGB"))
    if crop and min(a.shape[:2]) > 4 * crop:
        a = a[crop:-crop, crop:-crop]
    lut_t = np.linspace(0, 1, 256)
    lut = astro_palette(lut_t)
    f = a.reshape(-1, 3).astype(np.float32)
    out = np.empty(len(f), np.float32)
    for i in range(0, len(f), 200000):
        ch = f[i:i + 200000]
        out[i:i + 200000] = lut_t[((ch[:, None, :] - lut[None, :, :]) ** 2).sum(2).argmin(1)]
    return out.reshape(a.shape[:2])


def spec(t):
    a = t - t.mean()
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    n = F.shape[0]; y, x = np.indices(F.shape)
    r = np.hypot(y - n // 2, x - n // 2).astype(int)
    return (np.bincount(r.ravel(), F.ravel()) / np.maximum(np.bincount(r.ravel()), 1))[1:n // 2]


def signature(t):
    m = min(t.shape); u = t[:m, :m]
    # isotropie
    a = (u - u.mean()) * np.hanning(m)[:, None] * np.hanning(m)[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    c = m // 2; y, x = np.indices(F.shape); dy, dx = y - c, x - c
    r = np.hypot(dy, dx)
    A = np.abs(np.degrees(np.arctan2(dy, dx))); ang = np.minimum(A, 180 - A)
    b = (r > 3) & (r < m * 0.45)
    aniso = float(F[b & ((ang < 12) | (ang > 78))].mean() / F[b & (np.abs(ang - 45) < 20)].mean())
    # continuite de population
    h, _ = np.histogram(u, bins=48, range=(0, 1)); h = h / h.sum(); lg = np.log10(h + 1e-9)
    dip = float(min(lg[3:8].max(), lg[34:].max()) - lg[6:34].min())
    # concentration du flux
    s = np.sort(u.ravel())[::-1]
    conc = float(s[:int(.1 * s.size)].sum() / s.sum())
    # structures brillantes
    bw = u > np.percentile(u, 88)
    lbl, nb = ndimage.label(bw)
    el = []
    for sl in ndimage.find_objects(lbl):
        sub = lbl[sl] > 0
        ys, xs = np.nonzero(sub)
        if len(ys) < 6:
            continue
        cv = np.cov(np.stack([ys, xs]).astype(float))
        ev = np.sort(np.linalg.eigvalsh(cv))[::-1]
        if ev[0] > 1e-9:
            el.append(np.sqrt(ev[1] / max(ev[0], 1e-12)))
    n_struct = len(el)
    elong = float(1.0 / np.median(el)) if el else 1.0
    # nettete des pics, fenetre a 1/40 de l'image (echelle relative constante)
    rr = max(int(round(m / 40)), 2)
    mx = ndimage.maximum_filter(u, size=2 * rr + 1)
    msk = (u >= mx) & (u > np.percentile(u, 97))
    ys, xs = np.nonzero(msk)
    sm = ndimage.uniform_filter(u, 2 * rr + 1)
    v = u[ys, xs] / np.maximum(sm[ys, xs], 1e-9)
    sharp = float(np.median(np.sort(v)[::-1][:150])) if len(v) else 0.0
    p = spec(u)
    return dict(moyenne=float(u.mean()) * 255, sat_clair=float((u > 240 / 255).mean()),
                sat_noir=float((u < 8 / 255).mean()), isotropie=aniso, creux=dip,
                concentration=conc, structures=n_struct, elongation=elong,
                nettete=sharp, p_fil_grenaille=float(p[7:40].mean() / p[80:].mean()))


CIBLE = dict(moyenne=67.5, sat_clair=0.0020, isotropie=0.97, creux=-0.01,
             concentration=0.239, structures=512, elongation=1.78, nettete=1.69,
             p_fil_grenaille=180.2)

if __name__ == "__main__":
    path = sys.argv[1]
    t = to_tone(path)
    s = signature(t)
    print(f"— signature de {path} ({t.shape[0]}x{t.shape[1]}) —")
    for k, v in s.items():
        line = f"  {k:18s} {v:10.3f}"
        if "--compare" in sys.argv and k in CIBLE:
            c = CIBLE[k]
            ecart = abs(v - c) / max(abs(c), 1e-9) * 100
            line += f"   cible {c:9.3f}   ecart {ecart:6.1f} %"
        print(line)
