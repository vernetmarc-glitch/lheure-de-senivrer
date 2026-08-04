"""TEST DE NON-REGRESSION DES TEXTURES DE PRODUCTION.

Verifie les textures publiees contre CHAQUE exigence client mesurable, et non
contre l'idee qu'on s'en fait. Ecrit le 03/08/2026 apres une regression qui
serait passee inapercue : le champ fin des textures de production n'etait pas
herite, l'heritage etait detruit, et rien ne l'a signale parce que la mesure
n'avait ete faite que sur l'apercu, jamais sur ce qui etait livre.

    python3 validate_production.py [repertoire]

Ne teste QUE ce qui est mesurable sur des images fixes. Les exigences qui
portent sur l'interaction (H6, H7, J*, K*, L*) et sur l'axe du temps (C1 a C12)
relevent d'autres controles et sont listees a la fin comme non couvertes -- une
exigence oubliee en silence est pire qu'une exigence en echec.
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import void_scale as VS  # noqa: E402
import validate_raccord as VR  # noqa: E402

MATRIX = os.path.normpath(os.path.join(HERE, "..", "..", "app", "public",
                                       "data", "spacetime_matrix.json"))
REF_IMG = os.path.normpath(os.path.join(HERE, "..", "..", "docs",
                                        "reference-visuelle",
                                        "reference-toile-cosmique.jpg"))
ORDER = list("ONMLKJIHGFEDCBA")
SPRITE_ROWS = set("ABCDEFG")
MARGIN = 1.5

_fail, _pass = [], []


def check(ok, code, label, detail=""):
    (_pass if ok else _fail).append(code)
    print("  %-5s %-4s %-52s %s" % ("OK" if ok else "ECHEC", code, label, detail))
    return ok


def load(d):
    out = {}
    for c in ORDER:
        f = os.path.join(d, "density_%s.png" % c)
        if os.path.exists(f):
            out[c] = np.asarray(Image.open(f).convert("L"), np.float64) / 255.0
    return out


def visible(a):
    """Fenetre VISIBLE d'une texture de production : son centre, hors marge."""
    n = a.shape[0]
    v = int(round(n / MARGIN))
    c = (n - v) // 2
    return a[c:c + v, c:c + v]


def spec_octave(a):
    a = a - a.mean()
    n = a.shape[0]
    F = np.abs(np.fft.rfft2(a)) ** 2
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.rfftfreq(n)[None, :] * n
    k = np.sqrt(ky ** 2 + kx ** 2).ravel()
    idx = np.digitize(k, np.arange(1, n // 2))
    P = np.array([F.ravel()[idx == i].mean() if (idx == i).any() else 0.0
                  for i in range(1, n // 2 - 1)])
    kb = np.arange(1, n // 2 - 1)
    return kb, kb ** 2 * P, n


def main(d):
    m = json.load(open(MATRIX))
    rows = m["zoom_axis"]["rows"]
    half = {c: rows[c]["halfwidth_mpc"] for c in ORDER}
    img = load(d)
    print("=" * 78)
    print("TEXTURES DE PRODUCTION — %d/%d lignes trouvees dans %s"
          % (len(img), len(ORDER), d))
    print("=" * 78)
    if len(img) < len(ORDER):
        check(False, "B6", "aucune zone vide sur la grille",
              "manquantes : " + " ".join(c for c in ORDER if c not in img))
        return 1

    vis = {c: visible(a) for c, a in img.items()}

    # ---- A / E : aspect de chaque texture ---------------------------------
    print("\n-- aspect (A1..A7, E1..E6) --")
    bad = [c for c in ORDER if vis[c].std() * 255 < 1.0]
    check(not bad, "C8", "detail conserve : aucun aplat", " ".join(bad))
    bad = ["%s %.1f" % (c, vis[c].mean() * 255) for c in ORDER
           if not 60 <= vis[c].mean() * 255 <= 76]
    check(not bad, "A7", "ton moyen dans [60, 76]/255", " ".join(bad))
    bad = ["%s %.1f%%" % (c, 100 * (vis[c] >= 254 / 255).mean()) for c in ORDER
           if (vis[c] >= 254 / 255).mean() > 0.01]
    check(not bad, "E4a", "saturation claire < 1 %", " ".join(bad))
    bad = ["%s %.1f%%" % (c, 100 * (vis[c] <= 8 / 255).mean()) for c in ORDER
           if (vis[c] <= 8 / 255).mean() > 0.10]
    check(not bad, "E4b", "saturation noire < 10 %", " ".join(bad))
    # E5/E6 : une maille ou un motif periodique produit des pics discrets dans
    # le spectre. On compare le maximum a la mediane de son voisinage.
    bad = []
    for c in ORDER:
        F = np.abs(np.fft.rfft2(vis[c] - vis[c].mean()))
        # Ne comparer que dans les HAUTES frequences : une structure dominante
        # et centree (la Voie lactee sur A) produit legitimement un pic de basse
        # frequence, qui n'est pas un artefact de grille. Premiere version du
        # controle trop naive, corrigee le 03/08.
        n2 = F.shape[0]
        ky2 = np.fft.fftfreq(n2)[:, None] * n2
        kx2 = np.fft.rfftfreq(n2)[None, :] * n2
        hi = F[np.sqrt(ky2 ** 2 + kx2 ** 2) > n2 / 12.0]
        if hi.size and np.median(hi) > 0 and hi.max() / np.median(hi) > 60:
            bad.append("%s x%.0f" % (c, hi.max() / np.median(hi)))
    check(not bad, "E5/E6", "aucun artefact de grille ni motif periodique",
          " ".join(bad))
    # A3 : les zones brillantes sont quasi ponctuelles -> le 99e centile est
    # nettement au-dessus de la mediane.
    bad = ["%s %.1f" % (c, np.percentile(vis[c], 99) / max(np.median(vis[c]), 1e-6))
           for c in ORDER
           if np.percentile(vis[c], 99) / max(np.median(vis[c]), 1e-6) < 1.8]
    check(not bad, "A3/A4", "zones brillantes ponctuelles (p99/median > 1,8)",
          " ".join(bad))

    # ---- B : axe du zoom ---------------------------------------------------
    print("\n-- axe du zoom (B1..B8) --")
    f2, dep = [], []
    for i in range(len(ORDER) - 1):
        p, c = ORDER[i], ORDER[i + 1]
        r = half[p] / half[c]
        a, b = VR.bande_commune(img[p], img[c], r, 27.0)
        f2.append((p + "->" + c, VR.correlation(a, b)))
        dep.append((p + "->" + c, VR.deplacement_median(a, b)[0]))
    bad = ["%s %.2f" % (k, v) for k, v in f2 if v < 0.85]
    check(not bad, "B1", "heritage : F2 >= 0,85 sur les 14 paires", " ".join(bad))
    bad = ["%s %.1fpx" % (k, v) for k, v in dep if v > 3.0]
    check(not bad, "B2/D2", "fondu sans saut : deplacement median <= 3 px",
          " ".join(bad))
    # B3 : le contraste doit DECROITRE vers les grandes echelles.
    stds = [vis[c].std() for c in ORDER]
    inv = [ORDER[i] for i in range(len(stds) - 1) if stds[i] > stds[i + 1] + 0.04]
    check(not inv, "B3", "contraste croissant du grand vers le petit champ",
          " ".join(inv))
    # B8 : taille des vides conforme a la table.
    bad = []
    for c in ORDER:
        r = rows[c]
        if r.get("homogene") or c in SPRITE_ROWS:
            continue
        # Critere RELATIF AU CADRE : un vide ne peut pas etre plus grand que le
        # champ visible, et la reference visuelle donne 5,0 % de sa largeur. La
        # borne physique de la table ne vaut donc que comme PLAFOND. Premiere
        # version : fourchette absolue, qui exigeait 30 Mpc de vide dans un
        # cadre de 45 Mpc a la ligne H -- impossible et non souhaitable.
        _, fr, _ = VS.void_scale(vis[c] * 255)
        v = fr * 2 * half[c]
        plafond = r.get("void_mpc", r["structure_mpc"])[1]
        if not (0.025 <= fr <= 0.12):
            bad.append("%s %.1f %% du cadre" % (c, 100 * fr))
        elif v > plafond * 2:
            bad.append("%s %.0f Mpc (plafond %g)" % (c, v, plafond))
    check(not bad, "B8", "vides : 2,5-12 % du cadre, sous le plafond physique",
          " ".join(bad))
    # B5 : aucune structure au-dela de l'echelle d'homogeneite.
    homog = m["generation"]["champ_fin"]["homogeneity_mpc"]
    bad = []
    for c in ORDER:
        kb, w, n = spec_octave(vis[c])
        big = n / kb[int(np.argmax(w > 0.2 * w.max()))] * (2 * half[c] / n)
        if big > homog * 1.6:
            bad.append("%s %.0f Mpc" % (c, big))
    check(not bad, "B5", "aucune structure au-dela de %.0f Mpc" % homog,
          " ".join(bad))

    # ---- reference visuelle ------------------------------------------------
    print("\n-- reference visuelle --")
    ref = np.asarray(Image.open(REF_IMG).convert("L"))[8:-8, 8:-8]
    ref = np.asarray(Image.fromarray(ref).resize((320, 320), Image.LANCZOS))
    _, rf, _ = VS.void_scale(ref)
    best = min(ORDER, key=lambda c: abs(VS.void_scale(vis[c] * 255)[1] - rf))
    bf = VS.void_scale(vis[best] * 255)[1]
    check(abs(bf - rf) < 0.015, "A1",
          "une ligne approche la reference (vides %.1f %%)" % (100 * rf),
          "%s a %.1f %%" % (best, 100 * bf))

    # ---- geometrie des textures -------------------------------------------
    print("\n-- geometrie --")
    bad = [c for c in ORDER if img[c].shape[0] != img[ORDER[0]].shape[0]]
    check(not bad, "GEO1", "toutes les textures a la meme resolution", " ".join(bad))
    gen = m.get("generation", {})
    check(bool(gen), "GEO2", "parametres de generation figes dans la matrice",
          "" if gen else "bloc generation absent")

    print("\n" + "=" * 78)
    print("%d controles passes, %d en echec" % (len(_pass), len(_fail)))
    print("""
NON COUVERT par ce test, et devant l'etre ailleurs :
  C1..C12  axe du temps        -> demande une cuisson multi-epoques
  D4/D6    positions reelles   -> demande le catalogue en regard
  H1..H8   les trois spheres   -> pas encore tracees (O-03)
  J*/K*/L* interaction, perfs  -> hors du champ d'un test d'image
""")
    return 1 if _fail else 0


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(
        os.path.join(HERE, "..", "..", "app", "public", "data", "v4"))
    raise SystemExit(main(d))
