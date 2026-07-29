"""INVARIANTS EXECUTABLES — niveau 3 de la hierarchie documentaire.

Chaque controle est ne d'un echec DATE. Une regle ecrite en prose n'empeche rien :
le document d'architecture exigeait la conservation du flux depuis le 10 juillet
et interdisait explicitement `x8,5` ; le code de production utilise 8.5 et ne
conserve pas le flux, et rien ne l'a detecte pendant trois semaines.

Usage :
    python3 invariants.py --source          # controles statiques sur le code
    python3 invariants.py --render fichier  # controles sur une texture cuite
    python3 invariants.py --constants       # code vs document d'architecture

Sortie : code 0 si tout passe, 1 sinon. A brancher en pre-cuisson bloquant.
"""
import sys, os, re, json
import numpy as np
from scipy import ndimage

REPO = os.environ.get("REPO_ROOT", os.path.expanduser("~/repo"))
FAILED = []
PASSED = []


def check(ok, ident, label, detail=""):
    (PASSED if ok else FAILED).append((ident, label, detail))
    print(f"  {'OK  ' if ok else 'ECHEC'} {ident:10s} {label}" + (f"  — {detail}" if detail else ""))
    return ok


# ===========================================================================
# GROUPE A — metriques : jamais en pixels, toujours en unites comobiles
# ===========================================================================
# Origine : 4 occurrences. `lam_min_px` (juillet), `peak_sharpness` a fenetre de
# 11 px (28/07, a fausse un diagnostic de "creux" inexistant), critere de
# couverture juge sur l'echelle du layer (28/07, 9 layers faussement en defaut),
# sigma brut melangeant structure et grenaille (28/07, dissolution jugee bloquee).
# Protege : demandes-client B5, B2.

def A1_no_pixel_windows(src_paths):
    """Aucune fenetre de mesure spatiale exprimee en pixels."""
    bad = []
    pat = re.compile(r"def\s+(peak_sharpness|aniso|elongation|punctuality|"
                     r"cloud_shape|filamentarity)\s*\([^)]*\br\s*=\s*\d")
    for p in src_paths:
        try:
            t = open(p).read()
        except OSError:
            continue
        for m in pat.finditer(t):
            bad.append(f"{os.path.basename(p)}:{m.group(1)}")
    return check(not bad, "INV-A1",
                 "aucune metrique spatiale a fenetre en pixels par defaut",
                 ", ".join(bad))


def A2_sharpness_physical(half_mpc, out_n, r_px, target_mpc=3.0):
    """La fenetre de nettete doit valoir `target_mpc` en comobile."""
    mpp = 2.0 * half_mpc / out_n
    got = 2.0 * r_px * mpp
    return check(abs(got - target_mpc) / target_mpc < 0.5, "INV-A2",
                 f"fenetre de nettete physique ~{target_mpc} Mpc",
                 f"obtenue {got:.2f} Mpc (r={r_px} px, {mpp:.3f} Mpc/px)")


def A3_structure_vs_shot(t, smooth_px=8):
    """sigma brut melange structure et grenaille : il faut le sigma LISSE."""
    raw = float(t.std())
    sm = float(ndimage.gaussian_filter(t, smooth_px).std())
    return check(sm < raw, "INV-A3",
                 "sigma de structure isole du bruit de grenaille",
                 f"brut {raw*255:.1f} / lisse {sm*255:.2f}")


# ===========================================================================
# GROUPE B — aucune grandeur ne depend d'une statistique globale
# ===========================================================================
# Origine : compte de points par halo en part d'un budget global (28/07, ajouter
# des halos changeait la luminosite de tous les autres) ; `mass.max()` dans le
# rayon (28/07, ecart de 0,78 Mpc selon le contexte) ; sigma8 recalcule par
# grille (29/07, Psi passait a 78 Mpc) ; exposition par percentile.
# Protege : demandes-client B1 (heritage a 100 %).

FORBIDDEN_GLOBAL = [
    (r"/\s*\w*mass\w*\.sum\(\)", "masse normalisee par la somme du catalogue"),
    (r"mass\w*\.max\(\)", "rayon ou masse normalise par mass.max()"),
    (r"np\.percentile\([^)]*\)\s*\)?\s*(?:#\s*exposition|.*alpha)", "exposition par percentile"),
    (r"/\s*\w*\.std\(\)\s*(?!\s*#\s*ok)", "normalisation par l'ecart-type courant"),
]


def B1_no_global_stats(src_paths):
    bad = []
    for p in src_paths:
        try:
            lines = open(p).read().splitlines()
        except OSError:
            continue
        for i, ln in enumerate(lines, 1):
            if ln.strip().startswith("#"):
                continue
            for pat, why in FORBIDDEN_GLOBAL:
                if re.search(pat, ln):
                    bad.append(f"{os.path.basename(p)}:{i} ({why})")
    return check(not bad, "INV-B1",
                 "aucune grandeur par objet issue d'une statistique globale",
                 "; ".join(bad[:4]) + (f" … +{len(bad)-4}" if len(bad) > 4 else ""))


def B2_norm_computed_once(norm_values):
    """Le facteur de normalisation doit etre INVARIANT sur toutes les grilles."""
    v = np.asarray(norm_values, float)
    spread = float(v.ptp() / max(v.mean(), 1e-30)) if v.size > 1 else 0.0
    return check(spread < 0.02, "INV-B2",
                 "facteur de normalisation invariant par grille (<2 %)",
                 f"dispersion {spread*100:.2f} %")


def B3_cloud_context_free(cloud_solo, cloud_in_context):
    """Le nuage d'un objet doit etre identique hors de tout contexte."""
    a = np.sort(np.asarray(cloud_solo), axis=0)
    b = np.sort(np.asarray(cloud_in_context), axis=0)
    ok = a.shape == b.shape and np.allclose(a, b, atol=1e-6)
    d = float(np.abs(a - b).max()) if a.shape == b.shape else float("inf")
    return check(ok, "INV-B3", "nuage d'un objet independant du contexte",
                 f"ecart max {d:.6f} Mpc")


# ===========================================================================
# GROUPE C — grandeurs physiques absolues
# ===========================================================================
# Origine : rayon de halo en fraction de boite (28 et 29/07, DEUX fois : 769 Mpc
# a M la ou un amas fait 2,2) ; densite de particules issue de la grille physique
# (28/07, 1,15 particule/px a G contre 16 a D, ANISO 0,72) ; amplitude de
# deplacement renormalisee par boite (29/07, 932 Mpc a M).
# Protege : demandes-client B5, A3, A4.

def C1_radius_absolute(radius_mpc, box_mpc, max_mpc=20.0):
    """Un rayon d'objet est une valeur physique, jamais une fraction de boite."""
    return check(radius_mpc < max_mpc, "INV-C1",
                 f"rayon d'objet physique (<{max_mpc} Mpc)",
                 f"{radius_mpc:.2f} Mpc pour une boite de {box_mpc:.0f} Mpc")


def C2_density_from_output(n_projected, out_n, lo=4.0, hi=40.0):
    """La densite projetee vient de la resolution de SORTIE."""
    per_px = n_projected / float(out_n ** 2)
    return check(lo <= per_px <= hi, "INV-C2",
                 f"densite projetee dans [{lo}, {hi}] particules/px",
                 f"{per_px:.2f}/px ({n_projected/1e3:.0f}k sur {out_n}^2)")


def C3_displacement_physical(psi_rms_mpc, lo=3.0, hi=12.0):
    """Le deplacement de Zel'dovich est une grandeur physique (~7 Mpc)."""
    return check(lo <= psi_rms_mpc <= hi, "INV-C3",
                 f"deplacement rms dans [{lo}, {hi}] Mpc",
                 f"{psi_rms_mpc:.2f} Mpc")


# ===========================================================================
# GROUPE D — operateurs interdits en aval du generateur
# ===========================================================================
# Origine : flou gaussien et bruit de valeur rejetes (§11.2) ; depot CIC non
# lineaire detruisant la coherence inter-layer (0,08-0,43 mesure).
# Protege : demandes-client E1, E2, E3, B1.

def D1_no_downstream_nonlinear(src_paths):
    """Entre generateur et ecran : operateurs lineaires + courbes ponctuelles."""
    bad = []
    pat = re.compile(r"(gaussian_filter|uniform_filter|median_filter|maximum_filter)"
                     r"\s*\(\s*(?:t|tone|img_tone|out_tone)\b")
    for p in src_paths:
        try:
            lines = open(p).read().splitlines()
        except OSError:
            continue
        for i, ln in enumerate(lines, 1):
            if ln.strip().startswith("#"):
                continue
            if pat.search(ln):
                bad.append(f"{os.path.basename(p)}:{i}")
    return check(not bad, "INV-D1",
                 "aucun filtre spatial applique APRES la courbe de ton",
                 ", ".join(bad))


def D2_flux_conserving_splat(flux_by_progress, tol=0.35):
    """Un splat qui s'elargit doit CONSERVER son flux (echec du 10 ET du 28/07)."""
    f = np.asarray(flux_by_progress, float)
    ratio = float(f.max() / max(f.min(), 1e-30))
    return check(ratio < 1.0 / tol, "INV-D2",
                 f"flux conserve pendant l'elargissement (<x{1/tol:.1f})",
                 f"x{ratio:.1f}")


# ===========================================================================
# GROUPE E — signature de rendu
# ===========================================================================
# Protege : demandes-client A1, A2, A4, A6, E4, E5, C6, C8.

def E1_mean(t, lo=65.0, hi=70.0):
    m = float(t.mean()) * 255
    return check(lo <= m <= hi, "INV-E1", f"moyenne dans [{lo}, {hi}]/255", f"{m:.1f}")


def E2_saturation(t, max_hi=0.01, max_lo=0.10):
    hi = float((t > 240 / 255).mean()); lo = float((t < 8 / 255).mean())
    return check(hi <= max_hi and lo <= max_lo, "INV-E2",
                 f"saturation <{max_hi*100:.0f} % clair, <{max_lo*100:.0f} % noir",
                 f"{hi*100:.2f} % / {lo*100:.1f} %")


def E3_unimodal(t, max_dip=0.35):
    """Une seule population de matiere : pas de creux entre deux modes."""
    h, _ = np.histogram(t, bins=48, range=(0, 1)); h = h / h.sum()
    lg = np.log10(h + 1e-9)
    dip = float(min(lg[3:8].max(), lg[34:].max()) - lg[6:34].min())
    return check(dip <= max_dip, "INV-E3",
                 f"distribution continue (creux <={max_dip})", f"{dip:.2f}")


def E4_isotropy(t, lo=0.85, hi=1.20):
    """Aucun artefact de grille : pas de direction privilegiee."""
    m = min(t.shape); u = t[:m, :m]
    a = (u - u.mean()) * np.hanning(m)[:, None] * np.hanning(m)[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    c = m // 2; y, x = np.indices(F.shape); dy, dx = y - c, x - c
    r = np.hypot(dy, dx)
    A = np.abs(np.degrees(np.arctan2(dy, dx))); ang = np.minimum(A, 180 - A)
    b = (r > 3) & (r < m * 0.45)
    v = float(F[b & ((ang < 12) | (ang > 78))].mean() / F[b & (np.abs(ang - 45) < 20)].mean())
    return check(lo <= v <= hi, "INV-E4", f"isotropie axes/diagonales [{lo}, {hi}]", f"{v:.2f}")


def E5_hf_alive(t, min_var=1e-3):
    """Le contenu haute frequence ne tombe jamais a zero, meme dissous."""
    v = float(np.var(ndimage.laplace(t)))
    return check(v >= min_var, "INV-E5", f"contenu haute frequence >={min_var:.0e}", f"{v:.2e}")


def E6_glass_not_lattice(aniso_at_zero_displacement, hi=1.5):
    """A deplacement nul, les positions initiales ne doivent pas etre un reseau."""
    return check(aniso_at_zero_displacement <= hi, "INV-E6",
                 "positions initiales en verre, pas en reseau",
                 f"anisotropie a A=0 : {aniso_at_zero_displacement:.2f}")


# ===========================================================================
# GROUPE F — coherence de la matrice zoom x temps
# ===========================================================================
# Protege : demandes-client B1, B2, C9, D2, D3.

def F1_A_at_unity(a_values_at_one, tol=1e-9):
    v = np.asarray(a_values_at_one, float)
    return check(bool(np.all(np.abs(v - 1.0) <= tol)), "INV-F1",
                 "A(lambda, a=1) = 1 exactement pour toute echelle",
                 f"min {v.min():.9f}")


def F2_cross_layer(corr, min_corr=0.85):
    return check(corr >= min_corr, "INV-F2",
                 f"correlation inter-layer >={min_corr}", f"{corr:.3f}")


def F3_object_identity(median_px, max_px=1.5):
    return check(median_px <= max_px, "INV-F3",
                 f"identite d'objet : deplacement median <={max_px} px",
                 f"{median_px:.2f} px")


def F4_mean_continuity(d_mean_255, max_d=2.0):
    return check(d_mean_255 <= max_d, "INV-F4",
                 f"ecart de moyenne inter-layer <={max_d}/255", f"{d_mean_255:.2f}")


def F5_frame_coverage(worst_out_fraction, max_out=0.05):
    return check(worst_out_fraction <= max_out, "INV-F5",
                 f"couverture du cadre : hors-cadre <={max_out*100:.0f} %",
                 f"{worst_out_fraction*100:.1f} %")


# ===========================================================================
# GROUPE G — derive du code par rapport a son architecture
# ===========================================================================
# Origine : 29/07. Le document exigeait la conservation du flux depuis le
# 10 juillet et interdisait `x8,5` ; le code utilise 8.5. Non detecte pendant
# trois semaines. C'EST LE CONTROLE LE PLUS IMPORTANT DE CE FICHIER.

DOCUMENTED = {
    "scripts/generate_dissolution_sprites.mjs": [
        ("HALO_GROWTH", 1.2, "architecture §11.4.b : `1 + progress x1.2`, pas x8,5"),
        ("POINT_SIZE", 0.5, "architecture §11.4.b : pointSize=0,5 (8 juillet)"),
        ("FILAMENT_AMOUNT", 0.8, "architecture §11.4.b : filamentAmount~0,8"),
    ],
    "scripts/generate_layers.py": [
        ("NS", 0.965, "architecture §4.3"),
    ],
}


def G1_code_matches_doc(root=REPO):
    bad = []
    for rel, consts in DOCUMENTED.items():
        p = os.path.join(root, rel)
        try:
            txt = open(p).read()
        except OSError:
            bad.append(f"{rel} introuvable")
            continue
        for name, expected, why in consts:
            m = re.search(rf"\b{name}\s*=\s*([0-9.]+)", txt)
            if not m:
                bad.append(f"{rel}:{name} absent")
            elif abs(float(m.group(1)) - expected) > 1e-6:
                bad.append(f"{rel}:{name}={m.group(1)} attendu {expected} ({why})")
    return check(not bad, "INV-G1",
                 "les constantes du code correspondent au document d'architecture",
                 " | ".join(bad))


# ===========================================================================
def report():
    print(f"\n{'='*72}\n{len(PASSED)} passes, {len(FAILED)} echecs")
    if FAILED:
        print("\nINVARIANTS VIOLES — cuisson a bloquer :")
        for i, l, d in FAILED:
            print(f"  {i}  {l}" + (f"  [{d}]" if d else ""))
    return 1 if FAILED else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--source" in args or not args:
        print("— controles statiques sur le code —")
        srcs = []
        for base in (os.path.join(REPO, "scripts"), os.path.join(REPO, "scripts", "dev")):
            if os.path.isdir(base):
                srcs += [os.path.join(base, f) for f in os.listdir(base) if f.endswith(".py")]
        A1_no_pixel_windows(srcs)
        B1_no_global_stats(srcs)
        D1_no_downstream_nonlinear(srcs)
    if "--constants" in args or not args:
        print("— code vs document d'architecture —")
        G1_code_matches_doc()
    if "--render" in args:
        f = args[args.index("--render") + 1]
        t = np.load(f) if f.endswith(".npy") else None
        if t is None:
            from PIL import Image
            t = np.array(Image.open(f).convert("L")).astype(np.float32) / 255
        print(f"— controles de rendu sur {os.path.basename(f)} —")
        E1_mean(t); E2_saturation(t); E3_unimodal(t)
        E4_isotropy(t); E5_hf_alive(t); A3_structure_vs_shot(t)
    sys.exit(report())
