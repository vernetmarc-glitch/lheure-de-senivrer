"""Combo v2 — fusion réelle (retour du 19/07, points 1-3) :
  1. localgroup (C) régénéré : ajouté comme ENFANT de l1b dans la cascade
     hiérarchique (avant : générateur indépendant, seed 31415, aucun lien
     avec D — cause du décalage signalé).
  2. UNE SEULE topologie (rho) pilote le champ ATTÉNUÉ (léger, pas la pleine
     intensité de la Z2), le tirage des points, ET leur halo — au lieu de
     deux rendus recollés.
  3. Halo NUAGEUX : déposé depuis les POINTS eux-mêmes (flou large, faible
     amplitude), donc colle aux amas plutôt que d'être un fond plat.

A et B restent des sprites purs (inchangés) — la toile ambiante dessous
(retours 4-5) vient après correction du plancher de résolution.
"""
import math
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "..")
from generate_layers import (
    N, LAYER_SPECS, margin_for, box_mpc, generate_raw_field, normalize_variance,
    crop_and_upsample, apply_local_group_anchor,
)
from generate_local_group_catalog import build_catalog
import zeldovich_engine as ze
import spacetime_pipeline as sp

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


# ═══ A, B : sprites purs, inchangés (retours 4-5 = prochaine étape) ═══
print("A/B : sprites validés (inchangés)...")
panels = []
for code, hw in [("A", 0.025), ("B", 0.065)]:
    t, dbg = sp.render_cell(hw, 1.0, canvas_n=340)
    key = "milkyway_hires" if code == "A" else "milkyway"
    panels.append(labeled(colorize(t), f"{code} ({key}) mean={t.mean()*255:.0f}"))

# ═══ Cascade δ + Ψ hiérarchique, l5 -> l1b -> localgroup (NOUVEAU) ═══
print("Cascade δ + Ψ hiérarchique (l5 .. l1b, + localgroup en enfant)...")
W_COARSE, W_DETAIL = 0.74, 0.67
specs_by_key = {s["key"]: s for s in LAYER_SPECS}
catalog = build_catalog()
fields, psis = {}, {}

CHAIN = list(LAYER_SPECS) + [
    {"key": "localgroup", "max_mpc": 2.4, "seed": 31415, "parent": "l1b"}
]
specs_by_key["localgroup"] = CHAIN[-1]
MARGIN_LG = 1.5  # margin_factor localgroup (matrice)


def margin_of(key):
    return MARGIN_LG if key == "localgroup" else margin_for(key)


for spec in CHAIN:
    key, margin, pk = spec["key"], margin_of(spec["key"]), spec["parent"]
    world = box_mpc(spec["max_mpc"], margin)
    if pk is None:
        field = normalize_variance(generate_raw_field(N, world, spec["seed"]))
        psi = ze.displacement(field, world)
    else:
        pp = specs_by_key[pk]
        pmargin = margin_of(pk)
        coarse = crop_and_upsample(fields[pk], pp["max_mpc"], spec["max_mpc"], N, pmargin, margin)
        k_tr = np.pi * N / box_mpc(pp["max_mpc"], pmargin)
        detail = generate_raw_field(N, world, spec["seed"], highpass_k=k_tr)
        detail_n = normalize_variance(detail)
        field = normalize_variance(coarse) * W_COARSE + detail_n * W_DETAIL
        psi_c = (crop_and_upsample(psis[pk][0], pp["max_mpc"], spec["max_mpc"], N, pmargin, margin),
                 crop_and_upsample(psis[pk][1], pp["max_mpc"], spec["max_mpc"], N, pmargin, margin))
        psi_f = ze.displacement(detail_n, world)
        psi = (psi_c[0] + psi_f[0], psi_c[1] + psi_f[1])

    pre = field
    if key == "l1b":
        field = apply_local_group_anchor(field, spec["max_mpc"], N, catalog, strength=1.0,
                                         global_suppression=1.0, size_multiplier=1.8,
                                         real_only=False, bump_amplitude_factor=0.50,
                                         extra_blur_px=0.6, diffuse=False)
    elif key == "l2":
        field = apply_local_group_anchor(field, spec["max_mpc"], N, catalog, strength=1.6,
                                         real_only=False, diffuse=True, size_multiplier=5.0,
                                         bump_amplitude_factor=2.6)
    elif key == "l2b":
        field = apply_local_group_anchor(field, spec["max_mpc"], N, catalog, strength=0.85,
                                         real_only=False, diffuse=True, size_multiplier=5.0,
                                         bump_amplitude_factor=1.7)
    if pre is not field:
        psi_a = ze.displacement(field - pre, world)
        psi = (psi[0] + psi_a[0], psi[1] + psi_a[1])

    fields[key] = field
    psis[key] = psi
    print(f"   {key}")

G = 11.0 / math.sqrt(psis["l3"][0].var() + psis["l3"][1].var())
rhos = {k: ze.density_from_psi(psis[k], G, N) for k in psis}


# ═══ Rendu combo v2 : UNE topologie -> champ léger + points + halo-des-points ═══
def render_combo_v2(rho, n_points, seed, field_target, canvas_n=340):
    alpha = ze.solve_alpha(rho, target=field_target)
    field_light_full = ze.tone(rho, alpha)             # champ ATTÉNUÉ (léger)
    field_light = np.array(Image.fromarray((field_light_full * 255).astype(np.uint8))
                           .resize((canvas_n, canvas_n))) / 255

    P = np.clip(rho, 0, None) ** 2.2
    P = P / P.sum()
    rng = np.random.default_rng(seed)
    flat = rng.choice(P.size, size=n_points, p=P.ravel())
    py_idx, px_idx = np.unravel_index(flat, P.shape)
    pts_y = py_idx + rng.uniform(0, 1, n_points)
    pts_x = px_idx + rng.uniform(0, 1, n_points)
    lum = rng.power(1.6, n_points)
    amp = 0.10 + 0.9 * lum ** 1.5
    sizes = 0.6 + 1.7 * lum ** 0.5

    scale = canvas_n / N
    ys, xs = pts_y * scale, pts_x * scale
    s_core = np.clip(sizes * scale / (N / 300), 0.5, 20)

    # Passe 1 : halo NUAGEUX déposé depuis les POINTS eux-mêmes (pas le champ
    # indépendant) -> colle aux amas, effet filamenteux/nuageux localisé.
    halo = np.zeros((canvas_n, canvas_n))
    HALO_SIGMA = max(1.4, canvas_n / 260)
    for y, x, am in zip(ys, xs, amp):
        r = int(math.ceil(HALO_SIGMA * 3))
        if x < -r or x >= canvas_n + r or y < -r or y >= canvas_n + r:
            continue
        x0i, x1i = max(0, int(x - r)), min(canvas_n, int(x + r) + 1)
        y0i, y1i = max(0, int(y - r)), min(canvas_n, int(y + r) + 1)
        gyy_, gxx_ = np.mgrid[y0i:y1i, x0i:x1i]
        halo[y0i:y1i, x0i:x1i] += am * 0.30 * np.exp(
            -((gxx_ - x) ** 2 + (gyy_ - y) ** 2) / (2 * HALO_SIGMA * HALO_SIGMA))
    halo = np.clip(halo, 0, 1) * 0.55

    # Passe 2 : cœurs nets (galaxies individuelles)
    cores = np.zeros((canvas_n, canvas_n))
    for y, x, am, sg in zip(ys, xs, amp, s_core):
        r = int(math.ceil(sg * 3.2))
        if x < -r or x >= canvas_n + r or y < -r or y >= canvas_n + r:
            continue
        x0i, x1i = max(0, int(x - r)), min(canvas_n, int(x + r) + 1)
        y0i, y1i = max(0, int(y - r)), min(canvas_n, int(y + r) + 1)
        gyy_, gxx_ = np.mgrid[y0i:y1i, x0i:x1i]
        cores[y0i:y1i, x0i:x1i] += am * np.exp(-((gxx_ - x) ** 2 + (gyy_ - y) ** 2) / (2 * sg * sg))

    tone = 1 - (1 - field_light) * (1 - halo) * (1 - np.clip(cores, 0, 1.3))
    return np.clip(tone, 0, 1)


order = ["l1b", "l2", "l2b", "l3", "l3b", "l4", "l4a", "l4b", "l5a", "l5"]
codes = "DEFGHIJKLM"
n_points_by_key = {"localgroup": 3500, "l1b": 9000, "l2": 8500, "l2b": 8000, "l3": 9000,
                   "l3b": 7000, "l4": 6000, "l4a": 5000, "l4b": 4000, "l5a": 2500, "l5": 1500}

# ═══ C : nouveau fond combo (localgroup, hérité de l1b) + sprites VALIDÉS ═══
print("C : fond combo (localgroup, héritier de l1b) + sprites existants...")
bg_c = render_combo_v2(rhos["localgroup"], n_points_by_key["localgroup"], seed=31415,
                       field_target=10 / 255, canvas_n=340)
tone_c = sp.composite_sprites(bg_c.astype(np.float64), 1.0, 1.2, 340)
panels.append(labeled(colorize(tone_c), f"C (localgroup, nouveau fond) mean={tone_c.mean()*255:.0f}"))

for code, key in zip(codes, order):
    t = render_combo_v2(rhos[key], n_points_by_key[key], seed=hash(key) % 100000,
                        field_target=10 / 255)
    panels.append(labeled(colorize(t), f"{code} ({key}) mean={t.mean()*255:.0f}"))
    print(f"   {code} ({key}) : mean={t.mean()*255:.1f}/255")

grid = np.concatenate(panels, axis=1)
Image.fromarray(grid).save("preview_row_AM_v2.png")

print("\n── Auto-contrôles ──")
ok = True
for p, code in zip(panels, "ABCDEFGHIJKLM"):
    mean = p.astype(float)[16:].mean()
    v = 3 <= mean <= 100
    print(f"  {code}: mean={mean:.1f} {'OK' if v else 'HORS'}")
    ok &= v
print("\n" + ("AUTO-CONTRÔLES OK — présentable" if ok else "ÉCHEC — ne pas présenter"))
sys.exit(0 if ok else 1)
