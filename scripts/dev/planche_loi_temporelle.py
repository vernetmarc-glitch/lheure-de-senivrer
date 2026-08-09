"""PLANCHE DE COMPARAISON — quelle loi pour le champ fin le long du temps ?

Recherche pure. Ne publie rien, ne touche ni aux textures en ligne, ni a la
matrice, ni a `bake.py`. Sortie : une image de travail dans /tmp.

La question arbitree
--------------------
A la colonne 0 (recombinaison, `amp` = 0,001153 dans la matrice), qui porte le
grain que C8 exige, sans reintroduire la structure que C15 interdit ?

  OPTION A — plancher.  A_fine(amp) = A * max(amp^0,6 ; 0,25)
              Le champ fin ne descend jamais sous le quart de son amplitude
              d'aujourd'hui. C'est ce que documente la docstring de
              `sprites_layer` — loi jamais implementee, d'ou T-037.

  OPTION B — lineaire.  A_fine(amp) = A * amp
              Le champ fin suit le meme facteur de croissance que Psi, et
              s'annule franchement. Le grain revient alors au bruit de tirage
              des traceurs, qui ne disparait jamais.

Ce qui est commun aux deux
--------------------------
Le deplacement de Zel'dovich, x(amp) = q + amp * Psi. C'est exact et non
discute : Zel'dovich est LINEAIRE en facteur de croissance, donc rejouer une
epoque ne demande aucune recuisson -- d'ou `KEEP_LAGRANGIAN`.

Limite assumee de la planche
----------------------------
Les particules affectees a un halo ont vu leur position remplacee par celle du
halo ; les ramener vers `q` les dissout, ce qui est qualitativement juste mais
n'est PAS la loi `a_form(nu)` proposee pour les halos. La planche tranche la
question du CHAMP FIN, pas celle des halos.
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gen_chain as G  # noqa: E402
import mcpm_web as M  # noqa: E402

OUT_N = 200                    # resolution reduite : recherche, pas livraison
MARGIN = 1.5
ROW, HALF, SEED = "H", 22.5807, 107
AMPS = [0.001153, 0.2, 0.5, 1.0]      # colonnes 0, 2, 5, 10 de la matrice
LABELS = ["colonne 0", "colonne 2", "colonne 5", "colonne 10"]


def loi_A(amp):
    return max(amp ** 0.6, 0.25)


def loi_B(amp):
    return amp


def rendu(L, amp, loi):
    """Copie fidele de `gen_chain.render_full`, avec l'amplitude branchee.

    Deux seules differences, et elles sont le sujet de la planche :
      - les positions sont rejouees a l'epoque `amp` ;
      - l'amplitude du champ fin suit `loi(amp)`.
    Tout le reste -- tranche, PSF, repetitions, courbe de ton -- est identique,
    sinon on comparerait deux chaines et non deux lois.
    """
    n = int(round(OUT_N * MARGIN))
    ext = L.half * MARGIN
    slab = min(G.SLAB_FRAC * 2 * L.half, G.SLAB_MAX_MPC)
    rng = np.random.default_rng(SEED + 991)

    web = L.q0 + amp * (L.web - L.q0)

    img = np.zeros((n, n), np.float32)
    base = ((np.abs(web[:, 2]) < slab / 2).mean() * 1.0) or 1.0
    rep = int(np.clip(round(G.TARGET_PROJ * MARGIN ** 2
                            / max(len(web) * base * 0.9, 1)), 1, 20))
    for k in range(rep):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32)
                                      - 0.5) * L.cell
        m = ((np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < ext)
             & (np.abs(p[:, 1]) < ext))
        q = p[m]
        ix = np.clip(((q[:, 0] + ext) / (2 * ext) * n).astype(np.int32), 0, n - 1)
        iy = np.clip(((q[:, 1] + ext) / (2 * ext) * n).astype(np.int32), 0, n - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
    img = ndimage.gaussian_filter(img, G.PSF_PX)

    fine = L.fine
    if fine.shape[0] != n:
        fine = ndimage.zoom(fine, n / fine.shape[0], order=1)
    A = G.FINE_A * G.FINE_STRENGTH.get(L.code, 0.0) * loi(amp)
    out = img * np.exp(fine * A - A * A / 2)
    out = out + G.FINE_FLOOR * G.FINE_STRENGTH.get(L.code, 0.0) * out.mean()

    c = (n - OUT_N) // 2
    a = M.solve_alpha(out[c:c + OUT_N, c:c + OUT_N], G.TARGET_MEAN,
                      gamma=G.FINE_GAMMA)
    return np.asarray(M.tone(out, a, gamma=G.FINE_GAMMA))[c:c + OUT_N, c:c + OUT_N]


def structure(a):
    """Ecart-type de la composante LISSEE : la structure, pas la grenaille.

    Meme mesure que T-037, pour que le chiffre de la planche soit comparable a
    celui du harnais.
    """
    return float(ndimage.gaussian_filter(a, 3.0).std() * 255)


def grain(a):
    """Ce que la structure ne voit pas : l'ecart-type du RESIDU haute frequence.

    C'est la grandeur de C8 -- « uniforme mais plein de grain, jamais un aplat ».
    """
    return float((a - ndimage.gaussian_filter(a, 3.0)).std() * 255)


def main():
    G.KEEP_LAGRANGIAN = True
    old = G.OUT_N
    G.OUT_N = OUT_N
    try:
        G._calib_fine_norm()
        print("cuisson de la ligne %s ..." % ROW, flush=True)
        L = G.bake_layer(ROW, HALF, MARGIN, SEED)
        print("  %d traceurs, cellule %.3f Mpc" % (len(L.web), L.cell), flush=True)

        tuiles, mesures = {}, []
        for nom, loi in (("A", loi_A), ("B", loi_B)):
            for amp in AMPS:
                t = rendu(L, amp, loi)
                tuiles[(nom, amp)] = t
                mesures.append((nom, amp, structure(t), grain(t)))
                print("  %s amp=%.6f  structure %.2f  grain %.2f"
                      % (nom, amp, structure(t), grain(t)), flush=True)
    finally:
        G.OUT_N = old
        G.KEEP_LAGRANGIAN = False

    print()
    print("%-28s %10s %10s" % ("", "structure", "grain"))
    for nom, amp, s, gr in mesures:
        print("option %s  %-16s %10.2f %10.2f"
              % (nom, LABELS[AMPS.index(amp)], s, gr))
    s1A = [m for m in mesures if m[0] == "A" and m[1] == 1.0][0][2]
    s0A = [m for m in mesures if m[0] == "A" and m[1] == AMPS[0]][0][2]
    s1B = [m for m in mesures if m[0] == "B" and m[1] == 1.0][0][2]
    s0B = [m for m in mesures if m[0] == "B" and m[1] == AMPS[0]][0][2]
    print()
    print("T-037 exige <= 15 %% de structure restante a la colonne 0 :")
    print("  option A : %.0f %%   option B : %.0f %%"
          % (100 * s0A / max(s1A, 1e-9), 100 * s0B / max(s1B, 1e-9)))

    # ---------------------------------------------------------------- planche
    from PIL import Image, ImageDraw
    pad, top, left = 8, 34, 92
    W = left + 4 * (OUT_N + pad) + pad
    H = top + 2 * (OUT_N + pad + 18) + pad
    sheet = Image.new("L", (W, H), 16)
    dr = ImageDraw.Draw(sheet)
    for j, lab in enumerate(LABELS):
        dr.text((left + j * (OUT_N + pad) + 4, 12), lab, fill=230)
    for i, (nom, titre) in enumerate((("A", "A  plancher 0,25"),
                                      ("B", "B  lineaire"))):
        y = top + i * (OUT_N + pad + 18)
        dr.text((6, y + OUT_N // 2), titre, fill=230)
        for j, amp in enumerate(AMPS):
            t = (np.clip(tuiles[(nom, amp)], 0, 1) * 255).astype(np.uint8)
            x = left + j * (OUT_N + pad)
            sheet.paste(Image.fromarray(t), (x, y))
            s, gr = structure(tuiles[(nom, amp)]), grain(tuiles[(nom, amp)])
            dr.text((x + 2, y + OUT_N + 3),
                    "structure %.2f  grain %.2f" % (s, gr), fill=190)
    out = "/tmp/planche_loi_temporelle.png"
    sheet.save(out)
    print("\nplanche : %s" % out)


if __name__ == "__main__":
    main()
