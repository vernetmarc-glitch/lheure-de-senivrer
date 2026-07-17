"""Prévisualisation v3 — itération 2 (retours Marc du 15/07).

1. milkyway_hires : 2048², cadrage 2 rayons (disque ≈ 1024 px de large),
   apodisation des bords, splats par particule (sz), amplitude auto-calibrée.
2. filamentarity : squelettisation multi-octaves (3 bandes < 150 Mpc),
   modulation par la surdensité grande échelle, gain de crête.
Sorties : preview_v3b_filaments.png, preview_v3b_milkyway_hires.png
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
from spacetime_pipeline import MATRIX, BY_KEY

FIL = MATRIX["filamentarity"]
ASTRO = np.array([[0, 0, 0], [0x17, 0x0a, 0x05], [0x4a, 0x1f, 0x0a],
                  [0xa8, 0x48, 0x0f], [0xe8, 0xa1, 0x3a], [0xff, 0xf3, 0xd6]],
                 dtype=np.float64)


def colorize(t):
    n = len(ASTRO) - 1
    idx = np.clip((t * n).astype(int), 0, n - 1)
    fr = t * n - idx
    return np.clip(ASTRO[idx] + (ASTRO[idx + 1] - ASTRO[idx]) * fr[..., None],
                   0, 255).astype(np.uint8)


def labeled(rgb, text):
    img = Image.fromarray(rgb)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 16], fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 220, 160))
    return np.array(img)


def hstack(imgs, pad=3):
    h = max(i.shape[0] for i in imgs)
    w = sum(i.shape[1] for i in imgs) + pad * (len(imgs) - 1)
    out = np.zeros((h, w, 3), dtype=np.uint8)
    x = 0
    for i in imgs:
        out[:i.shape[0], x:x + i.shape[1]] = i
        x += i.shape[1] + pad
    return out


# ═══════════════════════════════════════════════════════════════════════
# Squelettisation v3.1 : multi-octaves + modulation grande échelle
# ═══════════════════════════════════════════════════════════════════════
def band(F, k, k_lo, k_hi, shape):
    return np.fft.irfft2(F * ((k >= k_lo) & (k < k_hi)), s=shape)


def filamentize2(field, world_mpc, ridge_mix, ridge_gain=2.6, env_mix=0.75,
                 p=None, cut_mpc=None):
    """Toile cosmique : crêtes multi-octaves (3 bandes sous cut_mpc),
    modulées par la surdensité grande échelle (connectivité : les filaments
    relient les zones denses, les vides restent vides)."""
    p = p if p is not None else FIL["ridge_exponent"]
    cut = cut_mpc if cut_mpc is not None else FIL["filament_max_scale_mpc"]
    F = np.fft.rfft2(field)
    ky = np.fft.fftfreq(field.shape[0])[:, None]
    kx = np.fft.rfftfreq(field.shape[1])[None, :]
    k = np.hypot(ky, kx)
    k_cut = world_mpc / (cut * field.shape[0])   # λ=cut en cycles/px
    k_nyq = 0.5
    low = np.fft.irfft2(F * (k < k_cut), s=field.shape)
    high = field - low
    # Octaves de crêtes FIXES en espace pixel (périodes 128/32/8 px) —
    # même caractère visuel à tous les zooms ; chaque octave est
    # intersectée avec la coupure physique k >= k_cut (< 150 Mpc), donc
    # aux grandes échelles (lignes L/M) seules les octaves fines
    # subsistent : uniformité + petits filaments, automatiquement.
    edges = [1 / 128, 1 / 32, 1 / 8, k_nyq]
    base_w = [0.45, 0.33, 0.22]
    web = np.zeros_like(field)
    tot_w = 0.0
    sig_ref = field.std() + 1e-12
    for (k_lo, k_hi), w in zip(zip(edges[:-1], edges[1:]), base_w):
        b = band(F, k, max(k_lo, k_cut), k_hi, field.shape)
        s = b.std()
        if s < 1e-4 * sig_ref:
            continue                      # octave vide (masquée par la coupure)
        n01 = np.clip(0.5 + b / (3.2 * s), 0, 1)
        web += w * (1 - np.abs(2 * n01 - 1) ** p)
        tot_w += w
    if tot_w < 1e-9:
        return field
    web = (web - web.mean()) / (web.std() + 1e-12)
    # Modulation par la surdensité grande échelle — DÉCOUPLÉE de la coupure
    # de filamentosité : l'enveloppe vient des plus grandes longueurs d'onde
    # disponibles DANS le cadre (lambda > monde/3, héritées du parent), même
    # quand la coupure 150 Mpc dépasse le cadre (cas l1b : le Vide Local
    # fait ~30 Mpc, il y a bien des vides à ces zooms). Elle sparsifie la
    # toile (crêtes dans le dense, vides vides) — c'est elle qui donne la
    # connectivité ET les crêtes hautes (kurtosis) après renormalisation.
    k_mod = max(k_cut, 3.0 / field.shape[0])
    low_mod = np.fft.irfft2(F * (k < k_mod), s=field.shape)
    ls = low_mod.std() + 1e-12
    z = np.clip(2.2 * low_mod / ls, -30, 30)
    env = 1 / (1 + np.exp(-z))                       # 0 vides, 1 dense
    mod = (1 - env_mix) + env_mix * env
    sig_h = high.std() + 1e-12
    ridge_part = web * mod * sig_h * ridge_gain
    return low + (1 - ridge_mix) * high + ridge_mix * ridge_part


# ═══════════════════════════════════════════════════════════════════════
# Cascade v3.1 (l5 -> l1b) + exports calibrés
# ═══════════════════════════════════════════════════════════════════════
print("1) Cascade v3.1…")
catalog = build_catalog()
W_COARSE, W_DETAIL = 0.74, 0.67
specs_by_key = {s["key"]: s for s in LAYER_SPECS}
v3 = {}
for spec in LAYER_SPECS:
    key, margin, parent_key = spec["key"], margin_for(spec["key"]), spec["parent"]
    world = box_mpc(spec["max_mpc"], margin)
    if parent_key is None:
        base = normalize_variance(generate_raw_field(N, world, spec["seed"]))
    else:
        pp = specs_by_key[parent_key]
        coarse = crop_and_upsample(v3[parent_key + "_raw"], pp["max_mpc"], spec["max_mpc"],
                                   N, margin_for(parent_key), margin)
        k_tr = np.pi * N / box_mpc(pp["max_mpc"], margin_for(parent_key))
        detail = generate_raw_field(N, world, spec["seed"], highpass_k=k_tr)
        base = normalize_variance(coarse) * W_COARSE + normalize_variance(detail) * W_DETAIL
    v3[key + "_raw"] = base           # héritage sur le champ NON squelettisé
    # Renormalisation à variance 1 APRÈS squelettisation : field_to_log_density
    # soustrait var/2 (log-normale à moyenne préservée calibrée pour sigma=1) —
    # sans cette étape la variance gonflée par les crêtes pénalise tout le champ.
    f = normalize_variance(filamentize2(base, world,
                                        BY_KEY[key].get("filamentarity_ridge_mix", 0)))
    anchor = BY_KEY[key].get("anchor_a1")
    if anchor:
        anchor = dict(anchor)
        # v3 : la toile est le contenu ambiant voulu — la suppression globale
        # v2 (0.35, esthétique "galaxies qui ressortent") écrasait les crêtes.
        # La dominance garantie des galaxies réelles s'adapte au niveau local.
        if anchor.get("global_suppression", 1.0) < 1.0:
            anchor["global_suppression"] = 1.0
    v3[key] = (apply_local_group_anchor(f, spec["max_mpc"], N, catalog, **anchor)
               if anchor else f)
    if key == "l1b":
        np.savez("/tmp/dbg_l1b.npz", base=base, fil=f, anchored=v3[key])
    print(f"   {key}")

log_v3 = {k: field_to_log_density(v3[k]) for k in specs_by_key}
np.savez("/tmp/dbg_norm.npz", ld_l1b=log_v3["l1b"], ld_l3=log_v3["l3"])
pooled = np.concatenate([ld.ravel() for ld in log_v3.values()])
VMIN3, VMAX3 = np.percentile(pooled, [1, 99.7])


def export_v3(key, gamma):
    t = np.clip((log_v3[key] - VMIN3) / (VMAX3 - VMIN3), 0, 1)
    return (t ** FIL["void_gamma"]) ** gamma


# calibration gamma -> ton moyen cible 38/255
target = 38 / 255
gammas = np.linspace(0.6, 3.5, 60)
mm = [np.mean([export_v3(k, g).mean() for k in ("l1b", "l3", "l5")]) for g in gammas]
GAMMA = float(gammas[int(np.argmin(np.abs(np.array(mm) - target)))])
print(f"2) gamma={GAMMA:.2f}")

panels = []
metrics = {}
for code, key in (("D10", "l1b"), ("G10", "l3"), ("M10", "l5")):
    t = export_v3(key, GAMMA)
    bright = float((t > 150 / 255).mean())
    metrics[code] = (float(t.mean()), bright)
    panels.append(labeled(colorize(t), f"{code} ({key}) v3.1 mean={t.mean()*255:.0f} "
                                       f"cretes>{150}: {bright*100:.1f}%"))
Image.fromarray(hstack(panels)).save("preview_v3b_filaments.png")

# ═══════════════════════════════════════════════════════════════════════
# milkyway_hires v2 : 2048², cadrage 2 rayons, splats sz, apodisation
# ═══════════════════════════════════════════════════════════════════════
print("3) milkyway_hires 2048²…")
mwsim = json.load(open("../../app/public/data/milkyway_dissolution_keyframes.json"))
NH = 2048
HWU = 2.0
RAD_LY = mwsim["mwRadiusLy"]
pos0 = np.array(mwsim["frames"][0]["positions"])
meta = mwsim["particleMeta"]
bvals = np.array([m["b"] for m in meta])
szvals = np.array([m["sz"] for m in meta])
ppu = NH / (2 * HWU * RAD_LY)
xs = NH / 2 + pos0[:, 0] * ppu
ys = NH / 2 + pos0[:, 1] * ppu
amps = 0.18 + bvals * 0.55
sigs = np.clip(szvals * (NH / 1024), 0.8, 6.0)
fld = np.zeros((NH, NH))
for x, y, amp, sg in zip(xs, ys, amps, sigs):
    r = int(math.ceil(sg * 3.0))
    if x < -r or x >= NH + r or y < -r or y >= NH + r:
        continue
    x0, x1 = max(0, int(x - r)), min(NH, int(x + r) + 1)
    y0, y1 = max(0, int(y - r)), min(NH, int(y + r) + 1)
    gy, gx = np.mgrid[y0:y1, x0:x1]
    fld[y0:y1, x0:x1] += amp * np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * sg * sg))
# amplitude auto-calibrée : p99.7 du champ non nul -> tone 0.95
nz = fld[fld > 1e-4]
kcal = -math.log(1 - 0.95) / np.percentile(nz, 99.7)
tone_mw = 1 - np.exp(-fld * kcal)
# apodisation des bords (fondu cosinus sur les derniers 6%)
ax = np.ones(NH)
edge = int(NH * 0.06)
ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, edge))
ax[:edge] = ramp
ax[-edge:] = ramp[::-1]
tone_mw = tone_mw * ax[None, :] * ax[:, None]

prod_mw = np.array(Image.open("../../app/public/data/density_milkyway.png")
                   .convert("L")) / 255
# corrélation à échelle équivalente (prod supposée 0.035075 Mpc de demi-champ)
MW_RAD_MPC = 0.01594329
frac = 0.035075 / (HWU * MW_RAD_MPC)   # >1 : la prod couvre PLUS large
if frac >= 1:
    c0 = int(prod_mw.shape[0] / 2 * (1 - 1 / frac))
    c1 = int(prod_mw.shape[0] / 2 * (1 + 1 / frac))
    prod_cmp = np.array(Image.fromarray((prod_mw[c0:c1, c0:c1] * 255).astype(np.uint8))
                        .resize((256, 256))) / 255
    hires_cmp = np.array(Image.fromarray((tone_mw * 255).astype(np.uint8))
                         .resize((256, 256))) / 255
corr = float(np.corrcoef(hires_cmp.ravel(), prod_cmp.ravel())[0, 1])

disp = 820
im_prod = labeled(colorize(np.array(Image.fromarray((prod_mw * 255).astype(np.uint8))
                                    .resize((disp, disp))) / 255),
                  "reference : density_milkyway.png")
im_new = labeled(colorize(np.array(Image.fromarray((tone_mw * 255).astype(np.uint8))
                                   .resize((disp, disp))) / 255),
                 "milkyway_hires v2 : 2048px, cadrage 2 rayons (disque ~1024px)")
crop = tone_mw[NH // 2 - 512:NH // 2 + 512, NH // 2 - 512:NH // 2 + 512]
im_crop = labeled(colorize(np.array(Image.fromarray((crop * 255).astype(np.uint8))
                                    .resize((disp, disp))) / 255),
                  "detail : crop central 1024px a l'echelle 1:1 telephone")
Image.fromarray(hstack([im_prod, im_new, im_crop])).save("preview_v3b_milkyway_hires.png")

# ── auto-contrôles
print("\n── Auto-contrôles ──")
ok = True
for code, (mean, bright) in metrics.items():
    band_ok = 0.07 <= mean <= 0.22
    web_ok = (0.004 <= bright <= 0.10) if code != "M10" else (bright <= 0.10)
    print(f"  {code}: mean={mean*255:.0f}/255 {'OK' if band_ok else 'HORS'} ; "
          f"crêtes brillantes {bright*100:.2f}% {'OK' if web_ok else 'HORS'}")
    ok &= band_ok and web_ok
sat = float((export_v3('l1b', GAMMA) > 245 / 255).mean())
print(f"  saturation D10 : {sat*100:.2f}% {'OK' if sat < 0.02 else 'ÉCHEC'}")
ok &= sat < 0.02
disk_px = 2 * RAD_LY * ppu
print(f"  disque VL : {disk_px:.0f}px de large {'OK' if 950 <= disk_px <= 1100 else 'ÉCHEC'}")
ok &= 950 <= disk_px <= 1100
print(f"  corrélation hires/prod (échelle équivalente) : {corr:.3f}")
edge_max = max(tone_mw[0].max(), tone_mw[-1].max(), tone_mw[:, 0].max(), tone_mw[:, -1].max())
print(f"  apodisation : ton max au bord {edge_max:.4f} {'OK' if edge_max < 0.01 else 'ÉCHEC'}")
ok &= edge_max < 0.01
print("\n" + ("AUTO-CONTRÔLES OK" if ok else "ÉCHEC — ne pas présenter"))
sys.exit(0 if ok else 1)
