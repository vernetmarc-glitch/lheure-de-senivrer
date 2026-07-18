"""Prépare les entrées du contrôle croisé JS/Python (xcheck_prototype.mjs) :
frames brutes u8 + référence Python (spacetime_pipeline.render_cell, 300px).
Usage : cd scripts/dev && python3 xcheck_dump_ref.py && node xcheck_prototype.mjs
"""
import json, os
import numpy as np
from PIL import Image
from spacetime_pipeline import MATRIX, DATA_DIR, render_cell

os.makedirs("xcheck_tmp/frames", exist_ok=True)
for l in MATRIX["layers"]:
    for i in range(len(l["keyframes_a"])):
        arr = np.array(Image.open(f"{DATA_DIR}/st_{l['key']}_k{i:02d}.png"))
        arr.astype(np.uint8).tofile(f"xcheck_tmp/frames/{l['key']}_{i:02d}.raw")

os.makedirs("xcheck_tmp/sprites", exist_ok=True)
for g in MATRIX["real_galaxies"]["entries"]:
    for i in range(MATRIX["sprites"]["n_frames"]):
        arr = np.array(Image.open(
            f"{DATA_DIR}/dissolution_sprites/{g['slug']}_f{i:02d}.png").convert("L"))
        arr.astype(np.uint8).tofile(f"xcheck_tmp/sprites/{g['slug']}_{i:02d}.raw")

for i in range(MATRIX["real_galaxies"]["milkyway_hires"]["n_frames"]):
    arr = np.array(Image.open(
        f"{DATA_DIR}/dissolution_sprites_hires/milkyway_f{i:02d}.png").convert("L"))
    arr.astype(np.uint8).tofile(f"xcheck_tmp/sprites/milkyway_hires_{i:02d}.raw")

CELLS = [(0.03, 1.0), (0.05, 1.0), (0.05, 0.3), (1.2, 1.0), (1.2, 0.45), (1.2, 0.15),
         (1.0, 0.01), (5.0, 0.5), (300.0, 0.9), (14570.0, 0.85), (0.02, 0.001)]
PIXELS = [(10, 10), (150, 150), (80, 220), (250, 40), (299, 299)]
ref = []
for hw, a in CELLS:
    tone, dbg = render_cell(hw, a, canvas_n=300)
    ref.append({"hw": hw, "a": a, "mean": float(tone.mean()), "white": dbg["white"],
                "hw_eff": dbg["hw_eff"], "px": [float(tone[y, x]) for y, x in PIXELS]})
json.dump(ref, open("xcheck_tmp/python_ref.json", "w"), indent=1)
print(f"{sum(len(l['keyframes_a']) for l in MATRIX['layers'])} frames + référence dumpées dans xcheck_tmp/")
