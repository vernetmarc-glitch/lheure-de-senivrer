"""D'ou vient la structure qui SUBSISTE a amplitude nulle (T-037 / C15) ?

Portee dev. On reconstruit la ligne d'essai de `checks_dissolution` en
neutralisant une composante a la fois, et on mesure ce qui reste.
"""
import os, sys
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "harness"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))
import gen_chain as G, sprites_layer as S  # noqa

N, ROW, HALF = 160, "E", 1.4113

def build(amp, sans_fine=False, sans_sprites=False):
    old = G.OUT_N
    try:
        G.OUT_N = N; G._calib_fine_norm()
        fine = G.fine_for(ROW, 4242+107, None, None, half=HALF)
        if fine.shape[0] != N: fine = ndimage.zoom(fine, N/fine.shape[0], order=1)
        if sans_fine: fine = np.zeros_like(fine)
        base = np.full((N, N), 0.25, np.float32)
        old_sf = dict(S.SPRITE_FILE)
        if sans_sprites: S.SPRITE_FILE.clear()
        try:
            tex, nr, npr = S.build(ROW, HALF*1.5, 107, base, fine, amp=amp)
        finally:
            S.SPRITE_FILE.update(old_sf)
        return np.asarray(tex, np.float64)
    finally:
        G.OUT_N = old

def struct(a): return float(ndimage.gaussian_filter(a, 3.0).std()*255)

print("%-34s %8s %8s %9s" % ("configuration", "amp=1", "amp=0", "restant"))
for lab, kw in (("complet (= T-037)", {}),
                ("champ fin neutralise", dict(sans_fine=True)),
                ("sprites N-corps retires", dict(sans_sprites=True)),
                ("les deux retires", dict(sans_fine=True, sans_sprites=True))):
    s1, s0 = struct(build(1.0, **kw)), struct(build(0.0, **kw))
    print("%-34s %8.2f %8.2f %8.0f %%" % (lab, s1, s0, 100*s0/max(s1,1e-9)))
