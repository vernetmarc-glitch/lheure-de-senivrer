"""Cuisson des sprites milkyway_hires (matrice : real_galaxies.milkyway_hires).

14 frames 2048², cadrage FIXE 2 rayons (disque ≈ 1024 px), splats par
particule (sz), passe cœur + passe halo, halo croissant avec progress,
exposition k calibrée sur f00 et PARTAGÉE par toutes les frames (continuité
de flux pendant la dissolution), apodisation cosinus 6 %.
Sortie : app/public/data/dissolution_sprites_hires/milkyway_f00..f13.png
"""
import json
import math
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "app", "public", "data")
M = json.load(open(os.path.join(DATA, "spacetime_matrix.json")))
H = M["real_galaxies"]["milkyway_hires"]
NH = H["resolution"]
HWU = H["framing_halfwidth_units"]

sim = json.load(open(os.path.join(DATA, "milkyway_dissolution_keyframes.json")))
RAD_LY = sim["mwRadiusLy"]
meta = sim["particleMeta"]
bvals = np.array([m["b"] for m in meta])
szvals = np.array([m["sz"] for m in meta])
amps = 0.18 + bvals * 0.55
sig_core = np.clip(szvals * (NH / 1024), 0.8, 6.0)
ppu = NH / (2 * HWU * RAD_LY)
N_FRAMES = H["n_frames"]

edge = int(NH * 0.06)
ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, edge))
apod = np.ones(NH)
apod[:edge] = ramp
apod[-edge:] = ramp[::-1]
APOD = apod[None, :] * apod[:, None]


def splat(field, xs, ys, sig_arr, amp_arr):
    for x, y, amp, sg in zip(xs, ys, amp_arr, sig_arr):
        r = int(math.ceil(sg * 3.0))
        if x < -r or x >= NH + r or y < -r or y >= NH + r:
            continue
        x0, x1 = max(0, int(x - r)), min(NH, int(x + r) + 1)
        y0, y1 = max(0, int(y - r)), min(NH, int(y + r) + 1)
        gy, gx = np.mgrid[y0:y1, x0:x1]
        field[y0:y1, x0:x1] += amp * np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * sg * sg))


def field_of(frame_idx):
    progress = frame_idx / (N_FRAMES - 1)
    pos = np.array(sim["frames"][frame_idx]["positions"])
    xs = NH / 2 + pos[:, 0] * ppu
    ys = NH / 2 + pos[:, 1] * ppu
    grow = 1 + progress * 2.5          # halo croissant avec la dissolution
    fld = np.zeros((NH, NH))
    splat(fld, xs, ys, sig_core * grow, amps * 0.7)
    splat(fld, xs, ys, sig_core * 3.5 * grow, amps * 0.22)
    return fld


out_dir = os.path.join(DATA, "dissolution_sprites_hires")
os.makedirs(out_dir, exist_ok=True)

f0 = field_of(0)
nz = f0[f0 > 1e-4]
KCAL = -math.log(1 - 0.95) / np.percentile(nz, 99.7)   # calibré sur f00, PARTAGÉ
print(f"exposition k={KCAL:.4f} (f00, partagée par les 14 frames)")

for i in range(N_FRAMES):
    fld = f0 if i == 0 else field_of(i)
    tone = (1 - np.exp(-fld * KCAL)) * APOD
    Image.fromarray(np.clip(tone * 255, 0, 255).astype(np.uint8), mode="L") \
        .save(os.path.join(out_dir, f"milkyway_f{i:02d}.png"))
    print(f"  f{i:02d} : max={tone.max():.3f} mean={tone.mean()*255:.2f}")

# corrélation f00 / texture de production (contrôle exigé par la matrice)
prod = np.array(Image.open(os.path.join(DATA, "density_milkyway.png")).convert("L")) / 255
MW_RAD_MPC = 0.01594329
frac = 0.035075 / (HWU * MW_RAD_MPC)
t0 = (1 - np.exp(-f0 * KCAL)) * APOD
if frac >= 1:
    hires_cmp = np.array(Image.fromarray((t0 * 255).astype(np.uint8)).resize((256, 256))) / 255
    c0 = int(prod.shape[0] / 2 * (1 - 1 / frac))
    c1 = int(prod.shape[0] / 2 * (1 + 1 / frac))
    prod_cmp = np.array(Image.fromarray((prod[c0:c1, c0:c1] * 255).astype(np.uint8))
                        .resize((256, 256))) / 255
    corr = float(np.corrcoef(hires_cmp.ravel(), prod_cmp.ravel())[0, 1])
    print(f"corrélation f00 / density_milkyway (échelle équivalente) : {corr:.3f}")
    assert corr > 0.6, "f00 ne corrèle pas avec la production"
print("Terminé.")
