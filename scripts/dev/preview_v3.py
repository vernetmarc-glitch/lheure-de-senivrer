"""Prévisualisation v3 (14/07) — échantillons AVANT recuisson complète.

Quatre panneaux indépendants, chacun rendu avec les algorithmes spécifiés
dans la matrice v3 (blocs filamentarity / tone_mapping / field_evolution /
real_galaxies.milkyway_hires), sur quelques cellules seulement :
  1. preview_v3_A_milkyway_hires.png — ligne A (actuel vs hires 1024²)
  2. preview_v3_filaments.png       — D10 et M10 avant/après squelettisation
  3. preview_v3_H_dissolution.png   — ligne H (l3b), 6 pas de temps
  4. preview_v3_tons_moyens.png     — bande C..M à a=1, tons moyens affichés

AUCUNE frame st_* ni texture de production n'est modifiée.
Auto-contrôles §13 avant présentation : saturation, cible de ton, continuité.
"""
import json
import math
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "..")
from generate_layers import (
    N, LAYER_SPECS, margin_for, box_mpc, generate_raw_field,
    normalize_variance, crop_and_upsample, field_to_log_density,
    apply_local_group_anchor,
)
from generate_local_group_catalog import build_catalog
from spacetime_pipeline import MATRIX, BY_KEY, A_layer, A_gal, t_gyr_of_a

FIL = MATRIX["filamentarity"]
TM = MATRIX["tone_mapping"]
FE = MATRIX["field_evolution"]
HIRES = MATRIX["real_galaxies"]["milkyway_hires"]

ASTRO = np.array([[0, 0, 0], [0x17, 0x0a, 0x05], [0x4a, 0x1f, 0x0a],
                  [0xa8, 0x48, 0x0f], [0xe8, 0xa1, 0x3a], [0xff, 0xf3, 0xd6]],
                 dtype=np.float64)


def colorize(tone):
    n = len(ASTRO) - 1
    idx = np.clip((tone * n).astype(int), 0, n - 1)
    frac = tone * n - idx
    return np.clip(ASTRO[idx] + (ASTRO[idx + 1] - ASTRO[idx]) * frac[..., None],
                   0, 255).astype(np.uint8)


def labeled(rgb, text):
    img = Image.fromarray(rgb)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 16], fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 220, 160))
    return np.array(img)


def hstack(imgs, pad=3):
    h = max(i.shape[0] for i in imgs)
    total = sum(i.shape[1] for i in imgs) + pad * (len(imgs) - 1)
    out = np.zeros((h, total, 3), dtype=np.uint8)
    x = 0
    for i in imgs:
        out[:i.shape[0], x:x + i.shape[1]] = i
        x += i.shape[1] + pad
    return out


# ═══════════════════════════════════════════════════════════════════════
# Squelettisation v3 (bloc filamentarity) — passe-bande < 150 Mpc
# ═══════════════════════════════════════════════════════════════════════
def filamentize(field, world_mpc, ridge_mix, a_env=1.0):
    """Transformée ridged appliquée à la composante < filament_max_scale_mpc.
    a_env : enveloppe temporelle (field_evolution : mix_eff = mix × A^q)."""
    if ridge_mix <= 0:
        return field
    p = FIL["ridge_exponent"]
    cut = FIL["filament_max_scale_mpc"]
    q = FE["schedules"]["q"]
    mix = ridge_mix * (a_env ** q)
    if mix <= 1e-4:
        return field
    F = np.fft.rfft2(field)
    ky = np.fft.fftfreq(field.shape[0])[:, None]
    kx = np.fft.rfftfreq(field.shape[1])[None, :]
    k = np.hypot(ky, kx)                       # cycles / pixel
    k_cut = world_mpc / (cut * field.shape[0])  # λ = cut Mpc en cycles/px
    hi = k >= k_cut
    # hf_boost : renforcement de l'octave la plus fine (λ < 8 px)
    boost = 1.0 + FIL["hf_boost"] * (a_env ** 1.0)
    Fb = F.copy()
    Fb[k >= 1 / 8] *= boost
    low = np.fft.irfft2(Fb * (~hi), s=field.shape)
    high = np.fft.irfft2(Fb * hi, s=field.shape)
    sig = high.std() + 1e-12
    n01 = np.clip(0.5 + high / (4 * sig), 0, 1)
    ridge = 1 - np.abs(2 * n01 - 1) ** p        # crêtes sur les zéros du champ
    ridgec = (ridge - ridge.mean()) / (ridge.std() + 1e-12) * sig
    return low + (1 - mix) * high + mix * ridgec * 1.6


# ═══════════════════════════════════════════════════════════════════════
# Reconstruction des champs de production (cascade exacte) + version v3
# ═══════════════════════════════════════════════════════════════════════
print("1) Cascade des champs de production (v2) et squelettisés (v3)…")
catalog = build_catalog()
W_COARSE, W_DETAIL = 0.74, 0.67
specs_by_key = {s["key"]: s for s in LAYER_SPECS}
prod_v2 = {}   # champs post-ancrage, chaîne actuelle
prod_v3 = {}   # champs post-ancrage, squelettisés (l'héritage parent est v3)

for spec in LAYER_SPECS:
    key, margin, parent_key = spec["key"], margin_for(spec["key"]), spec["parent"]
    world = box_mpc(spec["max_mpc"], margin)
    for tag, store in (("v2", prod_v2), ("v3", prod_v3)):
        if parent_key is None:
            base = normalize_variance(generate_raw_field(N, world, spec["seed"]))
        else:
            p = specs_by_key[parent_key]
            coarse = crop_and_upsample(store[parent_key], p["max_mpc"], spec["max_mpc"],
                                       N, margin_for(parent_key), margin)
            k_tr = np.pi * N / box_mpc(p["max_mpc"], margin_for(parent_key))
            detail = generate_raw_field(N, world, spec["seed"], highpass_k=k_tr)
            base = normalize_variance(coarse) * W_COARSE + normalize_variance(detail) * W_DETAIL
        if tag == "v3":
            base = filamentize(base, world, BY_KEY[key].get("filamentarity_ridge_mix", 0))
        anchor = BY_KEY[key].get("anchor_a1")
        store[key] = (apply_local_group_anchor(base, spec["max_mpc"], N, catalog, **anchor)
                      if anchor else base)
    print(f"   {key} ok")

# Normalisation partagée figée, recalculée comme la production le ferait (v3)
log_v3 = {k: field_to_log_density(f) for k, f in prod_v3.items()}
pooled = np.concatenate([ld.ravel() for ld in log_v3.values()])
VMIN3, VMAX3 = np.percentile(pooled, [1, 99.7])
print(f"2) Normalisation v3 : vmin={VMIN3:.4f} vmax={VMAX3:.4f}")


def export_v3(field, gamma):
    ld = field_to_log_density(field)
    t = np.clip((ld - VMIN3) / (VMAX3 - VMIN3), 0, 1)
    t = t ** FIL["void_gamma"]          # assombrissement des vides
    return t ** gamma                    # mapping de ton global


# ── Calibration du gamma global : ton moyen cible (30-45)/255 sur D..M
lo255, hi255 = TM["target_mean_tone_255"]
target = (lo255 + hi255) / 2 / 255
gammas = np.linspace(0.8, 4.0, 60)
means = []
for g in gammas:
    mm = np.mean([export_v3(prod_v3[k], g).mean() for k in ("l1b", "l3", "l5")])
    means.append(mm)
GAMMA = float(gammas[int(np.argmin(np.abs(np.array(means) - target)))])
print(f"3) Gamma de ton calibré : {GAMMA:.2f} (cible {target*255:.0f}/255)")

# Ton dissous rescalé par le même mapping (cascade obligatoire)
DISS_LOGD = math.log10(math.exp(0.0) + 0.05)
DISS_T = float(np.clip((DISS_LOGD - VMIN3) / (VMAX3 - VMIN3), 0, 1))
DISS_T = (DISS_T ** FIL["void_gamma"]) ** GAMMA
print(f"   ton dissous v3 : {DISS_T*255:.1f}/255 (v2 : 129.4)")


# ═══════════════════════════════════════════════════════════════════════
# Panneau 2 — filaments D10 (l1b) et M10 (l5), avant/après
# ═══════════════════════════════════════════════════════════════════════
print("4) Panneau filaments…")
panels = []
for code, key in (("D10", "l1b"), ("M10", "l5")):
    ld = field_to_log_density(prod_v2[key])
    # référence v2 : normalisation v2 approx = percentiles sur v2 seuls
    t2 = np.clip((ld - np.percentile(ld, 1)) /
                 (np.percentile(ld, 99.7) - np.percentile(ld, 1)), 0, 1)
    t3 = export_v3(prod_v3[key], GAMMA)
    panels.append(labeled(colorize(t2), f"{code} v2 (actuel) mean={t2.mean()*255:.0f}"))
    panels.append(labeled(colorize(t3), f"{code} v3 filaments mean={t3.mean()*255:.0f}"))
img_fil = hstack([panels[0], panels[1]])
img_fil2 = hstack([panels[2], panels[3]])
Image.fromarray(np.vstack([img_fil, np.zeros((4, img_fil.shape[1], 3), np.uint8), img_fil2])) \
    .save("preview_v3_filaments.png")

# ═══════════════════════════════════════════════════════════════════════
# Panneau 3 — dissolution ligne H (l3b) : field_evolution complet
# ═══════════════════════════════════════════════════════════════════════
print("5) Panneau dissolution H…")
from scipy.ndimage import gaussian_filter
spec_h = specs_by_key["l3b"]
world_h = box_mpc(spec_h["max_mpc"], margin_for("l3b"))
base_h_raw = {}  # champ v3 AVANT ridge, reconstruit une fois (parent v3)
p = specs_by_key[spec_h["parent"]]
coarse = crop_and_upsample(prod_v3[spec_h["parent"]], p["max_mpc"], spec_h["max_mpc"],
                           N, margin_for(spec_h["parent"]), margin_for("l3b"))
k_tr = np.pi * N / box_mpc(p["max_mpc"], margin_for(spec_h["parent"]))
detail = generate_raw_field(N, world_h, spec_h["seed"], highpass_k=k_tr)
base_h = normalize_variance(coarse) * W_COARSE + normalize_variance(detail) * W_DETAIL

thumbs, stats = [], []
A_VALUES = [1.0, 0.96, 0.92, 0.88, 0.84, 0.80]
for a in A_VALUES:
    A = A_layer(BY_KEY["l3b"], a)
    sig_mpc = (1 - A) * FE["schedules"]["sigma_max_frac"] * spec_h["max_mpc"]
    sig_px = sig_mpc * N / world_h
    f = gaussian_filter(base_h, sig_px) if sig_px > 0.1 else base_h
    f = filamentize(f, world_h, BY_KEY["l3b"]["filamentarity_ridge_mix"], a_env=A)
    f = f * A                                          # enveloppe v2 conservée
    t = export_v3(f, GAMMA)
    thumbs.append(labeled(colorize(t)[::2, ::2],
                          f"a={a} A={A:.2f} s={sig_mpc:.1f}Mpc m={t.mean()*255:.0f}"))
    stats.append((a, A, float(t.mean()), float(t.std())))
Image.fromarray(hstack(thumbs)).save("preview_v3_H_dissolution.png")

# ═══════════════════════════════════════════════════════════════════════
# Panneau 4 — tons moyens C..M à a=1
# ═══════════════════════════════════════════════════════════════════════
print("6) Panneau tons moyens…")
lg = np.array(Image.open("../../app/public/data/st_localgroup_k11.png").convert("L")) / 255
row = [labeled(colorize(lg)[::2, ::2], f"C (localgroup) mean={lg.mean()*255:.0f}")]
order = ["l1b", "l2", "l2b", "l3", "l3b", "l4", "l4a", "l4b", "l5a", "l5"]
codes = "DEFGHIJKLM"
tone_means = {}
for code, key in zip(codes, order):
    t3 = export_v3(prod_v3[key], GAMMA)
    tone_means[code] = float(t3.mean())
    row.append(labeled(colorize(t3)[::2, ::2], f"{code} ({key}) mean={t3.mean()*255:.0f}"))
Image.fromarray(hstack(row)).save("preview_v3_tons_moyens.png")

# ═══════════════════════════════════════════════════════════════════════
# Panneau 1 — milkyway_hires (ligne A)
# ═══════════════════════════════════════════════════════════════════════
print("7) Panneau Voie lactée hires…")
mwsim = json.load(open("../../app/public/data/milkyway_dissolution_keyframes.json"))
NH = HIRES["resolution"]
HWU = HIRES["framing_halfwidth_units"]
pos0 = np.array(mwsim["frames"][0]["positions"])   # en ANNÉES-LUMIÈRE
bvals = np.array([m["b"] for m in mwsim["particleMeta"]])
RAD_LY = mwsim["mwRadiusLy"]                        # 52000 ly = 1 rayon
px_per_unit = NH / (2 * HWU * RAD_LY)               # HWU exprimé en rayons
sig = 0.5 * (NH / 512)   # POINT_SIZE 0.5 à l'échelle 1024
fld = np.zeros((NH, NH))
xs = NH / 2 + pos0[:, 0] * px_per_unit
ys = NH / 2 + pos0[:, 1] * px_per_unit
amps = 0.18 + bvals * 0.55
r = int(math.ceil(sig * 3.2))
inv2s2 = 1 / (2 * sig * sig)
for x, y, amp in zip(xs, ys, amps):
    if x < -r or x > NH + r or y < -r or y > NH + r:
        continue
    x0, x1 = max(0, int(x - r)), min(NH, int(x + r) + 1)
    y0, y1 = max(0, int(y - r)), min(NH, int(y + r) + 1)
    gy, gx = np.mgrid[y0:y1, x0:x1]
    fld[y0:y1, x0:x1] += amp * np.exp(-((gx - x) ** 2 + (gy - y) ** 2) * inv2s2)
hires_f00 = 1 - np.exp(-fld)

# vue actuelle équivalente : crop central ±4 unités du sprite 512² cadrage 7.72
cur = np.array(Image.open("../../app/public/data/dissolution_sprites/milkyway_f00.png")
               .convert("L")) / 255
units_cur = MATRIX["real_galaxies"]["entries"][0]["sprite_halfwidth_units"]
frac = HWU / units_cur
c0 = int(256 - 256 * frac)
c1 = int(256 + 256 * frac)
cur_crop = np.array(Image.fromarray((cur[c0:c1, c0:c1] * 255).astype(np.uint8))
                    .resize((1024, 1024), Image.BILINEAR)) / 255
disp = 640
im_cur = labeled(colorize(np.array(Image.fromarray((cur_crop * 255).astype(np.uint8))
                                   .resize((disp, disp), Image.BILINEAR)) / 255),
                 "A10 actuel : sprite 512 cadrage large, recadre +-4 rayons")
im_new = labeled(colorize(np.array(Image.fromarray((hires_f00 * 255).astype(np.uint8))
                                   .resize((disp, disp), Image.BILINEAR)) / 255),
                 "A10 v3 : milkyway_hires 1024, cadrage 4 rayons")

# corrélation avec la texture de production, à échelle monde équivalente
# (halfwidth hires = 4 rayons = 4×0.01594 = 0.0638 Mpc ; texture prod
# supposée au max_mpc nominal 0.035075 Mpc — corrélation INDICATIVE)
MW_RAD_MPC = 0.01594329
HIRES_HW_MPC = HWU * MW_RAD_MPC
PROD_HW_MPC = 0.035075
prod_mw = np.array(Image.open("../../app/public/data/density_milkyway.png")
                   .convert("L")) / 255
frac_h = PROD_HW_MPC / HIRES_HW_MPC
h0 = int(NH / 2 - NH / 2 * frac_h)
h1 = int(NH / 2 + NH / 2 * frac_h)
hires_crop = np.array(Image.fromarray((hires_f00[h0:h1, h0:h1] * 255).astype(np.uint8))
                      .resize((256, 256), Image.BILINEAR)) / 255
prod_small = np.array(Image.fromarray((prod_mw * 255).astype(np.uint8))
                      .resize((256, 256), Image.BILINEAR)) / 255
corr = float(np.corrcoef(hires_crop.ravel(), prod_small.ravel())[0, 1])
im_prod = labeled(colorize(np.array(Image.fromarray((prod_mw * 255).astype(np.uint8))
                                    .resize((disp, disp), Image.BILINEAR)) / 255),
                  "reference : density_milkyway.png (production)")
Image.fromarray(hstack([im_prod, im_cur, im_new])).save("preview_v3_A_milkyway_hires.png")


# ═══════════════════════════════════════════════════════════════════════
# AUTO-CONTRÔLES §13 avant présentation
# ═══════════════════════════════════════════════════════════════════════
print("\n── Auto-contrôles §13 ──")
ok = True
for code, mean in tone_means.items():
    inband = lo255 / 255 * 0.75 <= mean <= hi255 / 255 * 1.35
    print(f"  ton moyen {code} = {mean*255:.1f}/255 {'OK' if inband else 'HORS BANDE'}")
    ok &= inband
sat = float((export_v3(prod_v3['l3'], GAMMA) > 240 / 255).mean())
print(f"  saturation G (l3) >240 : {sat*100:.2f}% {'OK' if sat < 0.02 else 'ÉCHEC'}")
ok &= sat < 0.02
gap = max(abs(stats[i][2] - stats[i + 1][2]) for i in range(len(stats) - 1))
conv = abs(stats[-1][2] - DISS_T)
print(f"  dissolution H : saut max entre pas {gap*255:.1f}/255 "
      f"{'OK (lisse)' if gap < 0.06 else 'ÉCHEC'} ; convergence vers ton dissous "
      f"|{stats[-1][2]*255:.1f}−{DISS_T*255:.1f}|={conv*255:.1f}/255 "
      f"{'OK' if conv < 0.05 else 'ÉCHEC'}")
print(f"  (note : la moyenne remonte vers le ton dissous {DISS_T*255:.0f}/255 — "
      f"mécanique du mapping v3, à montrer à Marc)")
ok &= gap < 0.06 and conv < 0.05
std_end = stats[-1][3]
print(f"  dissolution H : contraste résiduel à a=0.80 std={std_end*255:.1f} "
      f"{'OK (quasi dissous)' if std_end < 0.05 else 'attention'}")
print(f"  hires f00 vs density_milkyway : corrélation {corr:.3f} (info)")
print(f"  ton dissous rescalé : {DISS_T*255:.1f}/255")
print("\n" + ("AUTO-CONTRÔLES OK — panneaux présentables" if ok
              else "ÉCHEC AUTO-CONTRÔLES — ne pas présenter"))
sys.exit(0 if ok else 1)
