"""VALIDATION HEADLESS DU RACCORD SPECTRAL -- porte de cuisson.

Mesure les quatre criteres d'acceptation avant toute presentation visuelle :

  C3  rms(Psi) dans [3, 12] Mpc          -- amplitude du deplacement plausible
  B2  std(delta) conforme a la theorie   -- normalisation absolue tenue
  F2  correlation inter-lignes >= 0,85   -- HERITAGE (B1) : la matiere n'est pas
                                            redistribuee d'une ligne a l'autre
  F3  deplacement median <= 1,5 px       -- IDENTITE D'OBJET : un objet visible
                                            reste au meme endroit

F2 et F3 ne se mesurent que sur la BANDE COMMUNE aux deux lignes : l'enfant
resout plus fin que le parent, comparer les deux telles quelles mesurerait la
resolution, pas l'heritage.
"""
import numpy as np
from scipy import ndimage

import gen_chain as G
import norm_abs as NA
import mcpm_web as M

PSI_MIN, PSI_MAX = 3.0, 12.0
RHO_MIN = 0.85
DISP_MAX_PX = 1.5


def sigma_theorique(shape, box):
    """std attendu du champ sur cette grille : somme P(k) wgt / V, sans fenetre."""
    kx = np.fft.fftfreq(shape[0], d=box[0] / shape[0]) * 2 * np.pi
    ky = np.fft.fftfreq(shape[1], d=box[1] / shape[1]) * 2 * np.pi
    kz = np.fft.rfftfreq(shape[2], d=box[2] / shape[2]) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing="ij")
    k = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    P = M.power_spectrum(k) * NA.norm_factor() ** 2
    w = np.full(k.shape, 2.0)
    w[..., 0] = 1.0
    if shape[2] % 2 == 0:
        w[..., -1] = 1.0
    return float(np.sqrt((P * w).sum() / (box[0] * box[1] * box[2])))


def bande_commune(img_parent, img_child, ratio, lam_cut_px):
    """Ramene les deux images a la meme fenetre ET a la meme resolution.

    `ratio` = demi-champ parent / demi-champ enfant. On decoupe le carre central
    du parent, on le ramene a la taille de l'enfant, puis on lisse LES DEUX a la
    COUPURE DU RACCORD : au-dela, l'enfant porte un detail que le parent n'avait
    pas, et le comparer n'aurait aucun sens.

    `lam_cut_px` = longueur d'onde de coupure exprimee en pixels ENFANT. Lisser a
    la place au rapport des demi-champs (ce qui avait ete fait au premier essai)
    coupe environ 2,6 fois trop haut : la bande fraiche de l'enfant reste dans la
    comparaison et fait chuter rho de 0,96 a 0,14. On mesurait la resolution, pas
    l'heritage.
    """
    n = img_child.shape[0]
    w = n / ratio                      # cote du carre central du parent, en px
    c0 = (n - w) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    C = np.stack([c0 + yy * w / n, c0 + xx * w / n])
    par = ndimage.map_coordinates(img_parent.astype(np.float64), C, order=1, mode="nearest")
    sig = lam_cut_px / 3.0             # attenuation ~exp(-2 pi^2 sig^2 / lam^2)
    return (ndimage.gaussian_filter(par, sig),
            ndimage.gaussian_filter(img_child.astype(np.float64), sig))


def correlation(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = a.std() * b.std()
    return float((a * b).mean() / d) if d > 0 else float("nan")


def deplacement_median(a, b, n_peaks=200, search=6):
    """Deplacement median des pics les plus brillants, en pixels.

    Pour chaque maximum local de `a`, on cherche le maximum de `b` dans une
    fenetre de +-`search` px et on mesure la distance. Median, pas moyenne : un
    seul appariement rate ne doit pas emporter le verdict.
    """
    mx = ndimage.maximum_filter(a, size=5)
    peaks = np.argwhere((a == mx) & (a > np.percentile(a, 97)))
    if len(peaks) == 0:
        return float("nan"), 0
    if len(peaks) > n_peaks:
        order = np.argsort(a[peaks[:, 0], peaks[:, 1]])[::-1][:n_peaks]
        peaks = peaks[order]
    n = a.shape[0]
    d = []
    for y, x in peaks:
        y0, y1 = max(0, y - search), min(n, y + search + 1)
        x0, x1 = max(0, x - search), min(n, x + search + 1)
        w = b[y0:y1, x0:x1]
        dy, dx = np.unravel_index(int(np.argmax(w)), w.shape)
        d.append(np.hypot((y0 + dy) - y, (x0 + dx) - x))
    return float(np.median(d)), len(peaks)


def main():
    print("=" * 78)
    print("VALIDATION DU RACCORD SPECTRAL -- chaine O -> H, resolution %d" % G.OUT_N)
    print("=" * 78)
    res = G.run_chain(verbose=True)
    fails = []

    print("\n--- C3 : rms(Psi) dans [%.0f, %.0f] Mpc ---" % (PSI_MIN, PSI_MAX))
    for L, _ in res:
        ok = PSI_MIN <= L.psi_rms <= PSI_MAX
        print("  %-4s rms(Psi) = %8.3f Mpc   %s" % (L.code, L.psi_rms, "OK" if ok else "HORS BANDE"))
        if not ok:
            fails.append(f"C3 {L.code}: {L.psi_rms:.2f} Mpc")

    print("\n--- B2 : std(delta) conforme a la theorie (+-15 %) ---")
    for L, _ in res:
        th = sigma_theorique(L.shape, (L.box_xy, L.box_xy, L.Lz))
        r = L.std_delta / th if th > 0 else float("nan")
        ok = 0.85 <= r <= 1.15
        print("  %-4s mesure %8.4f   theorie %8.4f   rapport %5.3f   %s"
              % (L.code, L.std_delta, th, r, "OK" if ok else "ECART"))
        if not ok:
            fails.append(f"B2 {L.code}: rapport {r:.3f}")

    print("\n--- F2 / F3 : heritage entre lignes voisines ---")
    print("  %-9s %8s %10s %13s %8s" % ("paire", "lam_cut", "rho", "deplacement", "verdict"))
    for i in range(len(res) - 1):
        (Lp, ip), (Lc, ic) = res[i], res[i + 1]
        ratio = Lp.half / Lc.half
        lam_px = (2 * np.pi / Lp.k_cut) / (2 * Lc.half / G.OUT_N)
        pa, ch = bande_commune(ip, ic, ratio, lam_px)
        rho = correlation(pa, ch)
        disp, npk = deplacement_median(pa, ch)
        ok = (rho >= RHO_MIN) and (disp <= DISP_MAX_PX)
        print("  %-9s %6.1f px %10.3f %10.2f px %8s   (%d pics)"
              % (f"{Lp.code}->{Lc.code}", lam_px, rho, disp, "OK" if ok else "ECHEC", npk))
        if rho < RHO_MIN:
            fails.append(f"F2 {Lp.code}->{Lc.code}: rho={rho:.3f}")
        if disp > DISP_MAX_PX:
            fails.append(f"F3 {Lp.code}->{Lc.code}: {disp:.2f} px")

    print("\n" + "=" * 78)
    if fails:
        print("PORTE FERMEE -- %d critere(s) en echec :" % len(fails))
        for f in fails:
            print("   ", f)
    else:
        print("PORTE OUVERTE -- les quatre criteres passent.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
