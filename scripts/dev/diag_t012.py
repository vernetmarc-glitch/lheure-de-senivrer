"""DIAGNOSTIC T-012 — la metrique mesure-t-elle la taille apparente des objets ?

Portee dev : ne bloque rien, ne publie rien. Repond a la question ouverte du
07/08 (etat-des-lieux, §5) avant toute correction du generateur.

Trois mesures :

  1. `_bright_extent` sur les quinze lignes publiees. Si la valeur ne bouge pas,
     la metrique suit le PIXEL et non le megaparsec.

  2. ESSAI DE FALSIFICATION. On fabrique un enfant SYNTHETIQUE a partir de son
     parent par recadrage central x2,520 + agrandissement. C'est, par
     construction, une croissance apparente EXACTE de x2,520 de tous les objets,
     sans aucun objet nouveau. Une metrique juste doit rendre rr ~ 1,00.
     Si elle rend ~0,40, elle est aveugle a ce qu'elle pretend mesurer.

  3. TEMOIN NEGATIF. Enfant = parent tel quel (aucune croissance). Une metrique
     juste doit rendre rr ~ 1/2,520 = 0,397 et donc echouer.
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "harness"))

from checks import _bright_extent, visible, matrix  # noqa: E402

DATA = os.path.join(ROOT, "app", "public", "essai-v4", "data", "v4")
ORDER = list("ONMLKJIHGFEDCBA")


def load(code):
    f = os.path.join(DATA, "density_%s.png" % code)
    if not os.path.exists(f):
        return None
    return np.asarray(Image.open(f).convert("L"), np.float64) / 255.0


def zoom_center(a, ratio):
    """Recadrage central x`ratio` + agrandissement, meme taille de sortie.

    Purement lineaire. Tout objet de rayon r pixels devient de rayon r*ratio.
    """
    n = a.shape[0]
    w = n / ratio
    c0 = (n - w) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    C = np.stack([c0 + yy * w / n, c0 + xx * w / n])
    return ndimage.map_coordinates(a, C, order=3, mode="nearest")


def t012(pimg, cimg, ratio):
    ep, ec = _bright_extent(visible(pimg)), _bright_extent(visible(cimg))
    att = ep * ratio
    return (ec / att if att > 0 else float("nan")), ep, ec


def main():
    rows = matrix()["zoom_axis"]["rows"]
    img = {c: load(c) for c in ORDER}
    img = {k: v for k, v in img.items() if v is not None}

    print("== 1. etendue brillante par ligne (fraction de la largeur) ==")
    print("%-4s %10s %12s" % ("ligne", "demi-champ", "_bright_extent"))
    ext = {}
    for c in ORDER:
        if c in img:
            ext[c] = _bright_extent(visible(img[c]))
            print("%-4s %10.4f %12.5f" % (c, rows[c]["halfwidth_mpc"], ext[c]))
    v = np.array(list(ext.values()))
    print("   -> dispersion relative sur 15 lignes : %.1f %%"
          % (100 * v.std() / v.mean()))

    print()
    print("== 2. falsification : enfant = parent zoome x2,520 (verite = x1,00) ==")
    print("%-8s %8s %8s %8s   %s" % ("paire", "ep", "ec", "rr", "verdict"))
    bad = 0
    for i in range(len(ORDER) - 1):
        p, c = ORDER[i], ORDER[i + 1]
        if p not in img or c not in img:
            continue
        ratio = rows[p]["halfwidth_mpc"] / rows[c]["halfwidth_mpc"]
        synth = zoom_center(img[p], ratio)
        rr, ep, ec = t012(img[p], synth, ratio)
        ok = 0.85 <= rr <= 1.18
        bad += 0 if ok else 1
        print("%-8s %8.5f %8.5f %8.2f   %s"
              % ("%s->%s" % (p, c), ep, ec, rr, "ok" if ok else "AVEUGLE"))
    print("   -> %d paire(s) sur 14 ou la metrique ne voit pas une croissance"
          " REELLE de x2,520" % bad)

    print()
    print("== 3. temoin negatif : enfant = parent inchange (verite = echec) ==")
    print("%-8s %8s   %s" % ("paire", "rr", "verdict"))
    for i in range(len(ORDER) - 1):
        p, c = ORDER[i], ORDER[i + 1]
        if p not in img or c not in img:
            continue
        ratio = rows[p]["halfwidth_mpc"] / rows[c]["halfwidth_mpc"]
        rr, _, _ = t012(img[p], img[p].copy(), ratio)
        print("%-8s %8.2f   %s" % ("%s->%s" % (p, c), rr,
                                   "detecte" if not (0.4 <= rr <= 2.5) else "RATE"))
        break

    print()
    print("== 4. taille des composantes retenues, en pixels ==")
    for c in ORDER:
        if c not in img:
            continue
        a = visible(img[c])
        m = a >= np.percentile(a, 99.5)
        lab, k = ndimage.label(m)
        if k == 0:
            continue
        s = ndimage.sum(m, lab, range(1, k + 1))
        s = s[s >= 4]
        if not len(s):
            continue
        r = np.sqrt(np.median(s) / np.pi)
        print("%-4s  %4d composantes >= 4 px, rayon median %.2f px"
              % (c, len(s), r))


if __name__ == "__main__":
    main()
