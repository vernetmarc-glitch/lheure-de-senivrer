"""La reduction des sprites conserve-t-elle le flux ? Portee dev, mesure seule.

`_paste` reduit une vignette de 512 px a `d` pixels par `ndimage.zoom(order=3)`.
Une spline INTERPOLE : elle echantillonne la source, elle ne l'integre pas. En
reduction forte, tout ce qui tombe entre deux points d'echantillonnage est
PERDU. On mesure ici le flux conserve, et on le compare a une reduction par
moyenne d'aire, qui est l'operateur d'integration correct.
"""
import os, sys
import numpy as np
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import sprites_layer as S  # noqa

def aire(sp, d):
    """Reduction par moyenne d'aire : integrale exacte sur chaque pixel cible."""
    n = sp.shape[0]
    e = int(np.ceil(n / d)) * d           # multiple entier de d
    if e != n:
        sp = ndimage.zoom(sp, e / n, order=1)
    return sp.reshape(d, e // d, d, e // d).mean(axis=(1, 3))

print("%-12s %6s %10s %10s %10s" % ("sprite", "d px", "flux spline", "flux aire", "conserve"))
for key in ("milkyway", "andromede", "triangulum", "lmc", "sagittaire"):
    sp = S.load_sprite(key, 1.0)
    if sp is None:
        print("  %s introuvable" % key); continue
    f0 = float(sp.mean())
    for d in (4, 6, 10, 20, 60):
        z = ndimage.zoom(sp, d / sp.shape[0], order=3)
        np.clip(z, 0.0, None, out=z)
        a = aire(sp, d)
        print("%-12s %6d %10.4f %10.4f %9.0f %%"
              % (key, d, float(z.mean()), float(a.mean()),
                 100 * float(z.mean()) / max(float(a.mean()), 1e-12)))
    print("   (flux natif %.4f, vignette %d px)" % (f0, sp.shape[0]))
