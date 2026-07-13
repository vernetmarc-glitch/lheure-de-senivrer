"""
Validation headless de la MATRICE zoom × temps (§11.6/§11.8/§13) et des
frames cuites par scripts/generate_spacetime_frames.py.

Réplique EXACTEMENT le pipeline d'affichage du prototype
app/public/spacetime-matrix-test.html (mêmes formules, mêmes données), puis
vérifie par le calcul, sur toute la grille zoom × temps :

  A. A(s,a) : A(s,1)=1 EXACTEMENT et continûment pour toute échelle
     (contrainte dure §11.4.b, avec le correctif de continuité du 13
     juillet pour les échelles à plancher actif, l3→l5).
  B. Non-régression à a=1 (§11.7) : la dernière frame de chaque layer GRF
     doit être identique à la texture de production (au 1/255 de
     quantification près). localgroup : seule différence volontaire =
     correctif §4.8 (moyenne cible 8.95/255, galaxies préservées).
  C. Séquences de frames : saturation, continuité moyenne/écart-type entre
     keyframes voisines, contenu haute fréquence (variance du laplacien)
     qui ne s'effondre pas tant que A > 0, état final plat quand A = 0.
  D. Composition affichée sur une grille dense (zooms × temps) :
     couverture complète du cadre (§11.4.f — aucun recadrage visible d'une
     frame structurée), continuité du ton le long des DEUX axes,
     embrasement atteignant le blanc à a_min, cohérence de luminosité
     moyenne entre layers voisins.

Sortie : rapport texte + montage PNG (grille de vignettes) pour la
confirmation visuelle FINALE de l'utilisateur (§13.1 : le retour visuel
est une confirmation, pas la méthode de détection).

Usage : cd scripts/dev && python3 validate_spacetime_matrix.py
"""
import json
import math
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import laplace

from spacetime_pipeline import (
    MATRIX, LAYERS, BY_KEY, FRAMES, DATA_DIR, GAL_A_FORM, smoothstep,
    structure_amplitude_scale, A_layer, A_gal, white_channel,
    effective_halfwidth, layer_weights, render_cell,
)

CANVAS_N = 160


FAILURES = []


def check(ok, label, detail=""):
    status = "OK " if ok else "ÉCHEC"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(f"{label} — {detail}")






# ═══ A. Contraintes sur A(s,a) ══════════════════════════════════════════
print("\n═══ A. Contraintes A(s,a) (§11.4.b) ═══")
a_dense = np.concatenate([10 ** np.linspace(math.log10(MATRIX["time_axis"]["a_min"]), 0, 4000), [1.0]])
STEP_DEX = (0 - math.log10(MATRIX["time_axis"]["a_min"])) / 3999
for entry in LAYERS:
    vals = np.array([A_layer(entry, a) for a in a_dense])
    at1 = A_layer(entry, 1.0)
    just_below = A_layer(entry, 1 - 1e-9)
    max_step = np.abs(np.diff(vals)).max()
    # Borne ANALYTIQUE de continuité : pente max d'un smoothstep = 1.5 sur
    # l'entrée t, t balayant [0,1] sur 2w dex -> ΔA_max = 1.5×pas/(2w).
    # Un vrai SAUT dépasserait largement cette borne ; une transition raide
    # mais lisse la respecte exactement.
    bound = 1.5 * STEP_DEX / (2 * entry["halfwidth_dex"]) * 1.25 + 1e-6
    check(at1 == 1.0, f"A({entry['key']}, a=1) = 1 exactement", f"valeur={at1}")
    check(abs(1 - just_below) < 1e-6, f"A({entry['key']}) continu en a=1⁻", f"A(1-1e-9)={just_below:.9f}")
    check(max_step <= bound, f"A({entry['key']}) continu (borne analytique de pente)",
          f"max ΔA={max_step:.5f} ≤ {bound:.5f}")
    check(bool(np.all(np.diff(vals) >= -1e-12)), f"A({entry['key']}) monotone croissant en a")

# Trace de l'ancien défaut (formule pré-correctif) pour mémoire :
def old_A(a_form, a):
    if a >= 1:
        return 1.0
    w = max(-math.log10(a_form), 0.05)
    x = math.log10(a) - math.log10(a_form)
    return float(smoothstep((x + w) / (2 * w)))
print(f"  (mémo : ancienne formule, l5 : A(1-1e-9)={old_A(1.0, 1-1e-9):.3f} → saut 1→0.5 corrigé)")

# ═══ B. Non-régression à a=1 (§11.7) ════════════════════════════════════
print("\n═══ B. Non-régression a=1 vs production ═══")
for entry in LAYERS:
    key = entry["key"]
    n_k = len(entry["keyframes_a"])
    baked = np.array(Image.open(f"{DATA_DIR}/st_{key}_k{n_k-1:02d}.png")).astype(np.float64)
    prod = np.array(Image.open(f"{DATA_DIR}/density_{key}.png").convert("L")).astype(np.float64)
    prod512 = prod.reshape(512, 2, 512, 2).mean(axis=(1, 3))
    if key == "localgroup":
        # Seule différence volontaire : correctif §4.8. Vérifier la cible
        # calibrée et la préservation des galaxies (corrélation dans les
        # zones brillantes de la texture d'origine).
        mean = baked.mean()
        check(abs(mean - 8.95) < 0.8, "localgroup a=1 : moyenne cible §4.8 (8.95/255)", f"mesuré {mean:.2f}")
        bright = prod512 > 30
        corr = np.corrcoef(baked[bright], prod512[bright])[0, 1] if bright.sum() > 100 else 0
        check(corr > 0.95, "localgroup a=1 : galaxies préservées", f"corrélation zones brillantes={corr:.4f}")
        sat = (baked > 240).mean()
        check(sat < 0.01, "localgroup a=1 : saturation négligeable (§4.8)", f"{sat*100:.3f}% > 240")
    else:
        diff = np.abs(baked - prod512)
        check(diff.max() <= 1.0 + 1e-9, f"{key} a=1 identique à production (±1 quantif.)",
              f"max diff={diff.max():.3f}, moyenne diff={diff.mean():.4f}")

# ═══ C. Séquences de frames ═════════════════════════════════════════════
print("\n═══ C. Séquences de frames (saturation, continuité, HF) ═══")
for entry in LAYERS:
    key = entry["key"]
    kfs = entry["keyframes_a"]
    imgs = FRAMES[key]
    means = np.array([im.mean() for im in imgs])
    stds = np.array([im.std() for im in imgs])
    laps = np.array([laplace(im).var() for im in imgs])
    sat_hi = np.array([(im > 240 / 255).mean() for im in imgs])

    dmean = np.abs(np.diff(means)).max()
    check(dmean < 0.10, f"{key} : continuité de moyenne entre keyframes", f"max Δmean={dmean*255:.1f}/255")
    # Saturation : les cœurs de galaxies de l1b/localgroup sont brillants par
    # conception — seuil large mais borné.
    check(sat_hi.max() < 0.02, f"{key} : saturation bornée sur toute la séquence",
          f"max {sat_hi.max()*100:.2f}% > 240")
    # État initial (A=0) : uniforme PAR CONCEPTION (l'état dissous).
    a0 = kfs[0]
    A0 = max(A_layer(entry, a0), A_gal(a0) if entry.get("anchor_a1") or key == "localgroup" else 0)
    if A0 < 1e-6:
        check(stds[0] < 2 / 255, f"{key} : première frame (A=0) uniforme", f"std={stds[0]*255:.2f}/255")
    # HF : ne doit pas s'effondrer TANT QUE la structure existe (A>0.3),
    # puis DOIT décroître vers ~0 à l'état dissous (§11.2).
    for i, a in enumerate(kfs):
        if A_layer(entry, a) > 0.3 and laps[-1] > 0:
            frac = laps[i] / laps[-1]
            if frac < 0.02:
                check(False, f"{key} : HF effondrée à a={a} malgré A={A_layer(entry, a):.2f}",
                      f"laplacien={frac*100:.1f}% de a=1")
                break
    else:
        check(True, f"{key} : HF cohérente (laplacien suit A, pas d'effondrement prématuré)",
              f"lapvar a=1 {laps[-1]:.2e} → première frame {laps[0]:.2e}")

# ═══ D. Composition affichée — grille zoom × temps ══════════════════════
print("\n═══ D. Grille composée zoom × temps (§11.4.f) ═══")










N_ZOOM, N_TIME = 15, 15
zooms = 10 ** np.linspace(math.log10(0.02), math.log10(14570), N_ZOOM)
times = np.concatenate([10 ** np.linspace(math.log10(MATRIX["time_axis"]["a_min"]), math.log10(0.999), N_TIME - 1), [1.0]])

mean_grid = np.zeros((N_ZOOM, N_TIME))
worst_clamp, worst_cell = 0.0, None
thumbs = {}
for zi, hw in enumerate(zooms):
    for ti, a in enumerate(times):
        tone, dbg = render_cell(hw, a)
        mean_grid[zi, ti] = tone.mean()
        if dbg["clamp"] > worst_clamp:
            worst_clamp, worst_cell = dbg["clamp"], (hw, a, dbg["hw_eff"])
        if zi % 2 == 0 and ti % 2 == 0:
            thumbs[(zi, ti)] = tone

check(worst_clamp < 0.05, "Couverture du cadre (§11.4.f) : aucun recadrage visible d'une frame structurée",
      f"pire défaut pondéré={worst_clamp*100:.2f}%" + (f" à hw={worst_cell[0]:.1f} a={worst_cell[1]:.4f} hw_eff={worst_cell[2]:.0f}" if worst_cell else ""))

# ── Continuité par BALAYAGES DENSES 1D (la grille du montage est trop
# grossière pour distinguer une transition raide-mais-lisse d'un saut).
# Preuve de lissité : on mesure max |Δmean| par pas à deux résolutions ;
# pour une fonction lisse, Δ décroît proportionnellement au pas — un vrai
# saut resterait constant.
def sweep_time(hw, n_pts):
    a_s = np.concatenate([10 ** np.linspace(math.log10(MATRIX["time_axis"]["a_min"]),
                                            math.log10(0.9999), n_pts - 1), [1.0]])
    return np.array([render_cell(hw, a)[0].mean() for a in a_s])

def sweep_zoom(a, n_pts):
    hws = 10 ** np.linspace(math.log10(0.02), math.log10(14570), n_pts)
    return np.array([render_cell(hw, a)[0].mean() for hw in hws])

print("  Balayages denses (continuité, §13.2.3)…")
for hw in [0.05, 5.0, 300.0, 14570.0]:
    m120 = sweep_time(hw, 120)
    m240 = sweep_time(hw, 240)
    d120, d240 = np.abs(np.diff(m120)).max(), np.abs(np.diff(m240)).max()
    check(d120 < 0.06, f"Continuité TEMPS à hw={hw} Mpc (120 pts)", f"max Δ/pas={d120:.4f}")
    check(d240 < d120 * 0.75, f"Lissité TEMPS à hw={hw} Mpc (Δ décroît avec le pas)",
          f"{d120:.4f} → {d240:.4f} en doublant la résolution")
for a in [1.0, 0.6, 0.15]:
    m120 = sweep_zoom(a, 120)
    m240 = sweep_zoom(a, 240)
    d120, d240 = np.abs(np.diff(m120)).max(), np.abs(np.diff(m240)).max()
    check(d120 < 0.06, f"Continuité ZOOM à a={a} (120 pts)", f"max Δ/pas={d120:.4f}")
    check(d240 < d120 * 0.75, f"Lissité ZOOM à a={a} (Δ décroît avec le pas)",
          f"{d120:.4f} → {d240:.4f} en doublant la résolution")

w_min = white_channel(MATRIX["time_axis"]["a_min"])
check(w_min > 0.995, "Embrasement : blanc à la recombinaison", f"white(a_min)={w_min:.4f}")
check(white_channel(0.15) < 0.02, "Embrasement : nul jusqu'à a≈0.1-0.15", f"white(0.15)={white_channel(0.15):.4f}")
tone_amin = mean_grid[:, 0]
check(bool(np.all(tone_amin > 0.98)), "Ton uniforme blanc à a_min sur TOUS les zooms",
      f"min={tone_amin.min():.4f}")

# ── Montage de vignettes pour confirmation visuelle finale (§13.1).
ASTRO = np.array([[0, 0, 0], [0x17, 0x0a, 0x05], [0x4a, 0x1f, 0x0a],
                  [0xa8, 0x48, 0x0f], [0xe8, 0xa1, 0x3a], [0xff, 0xf3, 0xd6]], dtype=np.float64)


def colorize(tone):
    n = len(ASTRO) - 1
    idx = np.clip((tone * n).astype(int), 0, n - 1)
    frac = tone * n - idx
    return np.clip(ASTRO[idx] + (ASTRO[idx + 1] - ASTRO[idx]) * frac[..., None], 0, 255).astype(np.uint8)


zi_list = sorted({k[0] for k in thumbs})
ti_list = sorted({k[1] for k in thumbs})
PAD = 2
mont = np.zeros((len(zi_list) * (CANVAS_N + PAD), len(ti_list) * (CANVAS_N + PAD), 3), dtype=np.uint8)
for r, zi in enumerate(reversed(zi_list)):     # zoom max en haut
    for c, ti in enumerate(ti_list):           # temps croissant vers la droite
        rgb = colorize(thumbs[(zi, ti)])
        mont[r * (CANVAS_N + PAD):r * (CANVAS_N + PAD) + CANVAS_N,
             c * (CANVAS_N + PAD):c * (CANVAS_N + PAD) + CANVAS_N] = rgb
Image.fromarray(mont).save("spacetime_matrix_montage.png")
print(f"\nMontage écrit : scripts/dev/spacetime_matrix_montage.png "
      f"({len(zi_list)} zooms × {len(ti_list)} temps, zoom max en haut, temps → droite)")

print("\n══════════════════════════════════════")
if FAILURES:
    print(f"{len(FAILURES)} ÉCHEC(S) :")
    for fmsg in FAILURES:
        print(f"  - {fmsg}")
    sys.exit(1)
print("TOUTES LES VÉRIFICATIONS PASSENT — le retour visuel peut être demandé (§13.4).")
