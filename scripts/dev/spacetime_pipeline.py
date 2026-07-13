"""
Pipeline headless PARTAGÉ de composition zoom × temps — port Python 1:1 du
prototype app/public/spacetime-matrix-test.html (fonction computeTone) et
des formules de app/public/spacetime-shared.js.

SOURCE UNIQUE côté validation : validate_spacetime_matrix.py et tout futur
contrôle croisé importent ce module au lieu de recopier les formules
(cf. §11.4 "une seule définition, réutilisée partout" et §13).
Toute évolution du prototype/du JS partagé doit être répercutée ici.
"""
import json
import math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

DATA_DIR = "../../app/public/data"

MATRIX = json.load(open(f"{DATA_DIR}/spacetime_matrix.json"))
LAYERS = MATRIX["layers"]
BY_KEY = {l["key"]: l for l in LAYERS}

FRAMES = {}
for _entry in LAYERS:
    FRAMES[_entry["key"]] = [
        np.array(Image.open(f"{DATA_DIR}/st_{_entry['key']}_k{i:02d}.png")).astype(np.float64) / 255
        for i in range(len(_entry["keyframes_a"]))]

with open(f"{DATA_DIR}/dissolution_keyframes.json") as f:
    SIMS = json.load(f)
with open(f"{DATA_DIR}/local_group_catalog.json") as f:
    CATALOG = json.load(f)

SLUG_BY_NAME = {
    'Andromède (M31)': 'andromede', 'Triangulum (M33)': 'triangulum',
    'Grand Nuage de Magellan': 'lmc', 'Petit Nuage de Magellan': 'smc',
    'Naine du Sagittaire': 'sagittaire', 'NGC 6822': 'ngc6822',
    'IC 10': 'ic10', 'Leo I': 'leo1',
}
SCENE = [{'slug': 'milkyway', 'distanceMpc': 0, 'angleDeg': 0, 'radiusMpc': 0.01594329}]
for gal in CATALOG:
    if gal.get('isReal') and gal['name'] in SLUG_BY_NAME:
        SCENE.append({'slug': SLUG_BY_NAME[gal['name']], 'distanceMpc': gal['distanceMpc'],
                      'angleDeg': gal['angleDeg'], 'radiusMpc': gal['radiusMpc']})


# ── A(s,a) — port exact de spacetime-shared.js (correctif continuité 13/07).
def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def structure_amplitude_scale(a_form, a):
    if a >= 1:
        return 1.0
    w = max(-math.log10(a_form), 0.05)
    center = min(math.log10(a_form), -w)
    x = math.log10(max(a, 1e-6)) - center
    return float(smoothstep((x + w) / (2 * w)))


def A_layer(entry, a):
    return structure_amplitude_scale(entry["a_form"], a)


GAL_A_FORM = BY_KEY["localgroup"]["a_form"]


def A_gal(a):
    return structure_amplitude_scale(GAL_A_FORM, a)


EMB = MATRIX["embrasement"]


def white_channel(a):
    fade = 1 - structure_amplitude_scale(GAL_A_FORM, min(a * EMB["a_multiplier"], 1))
    return 1 - math.exp(-(fade ** EMB["exp"]) * EMB["offset_max"])


COMP = MATRIX["compression"]


def compression_strength(scale_mpc):
    lo, hi = math.log10(COMP["lo_mpc"]), math.log10(COMP["hi_mpc"])
    return float(smoothstep((math.log10(max(scale_mpc, 1e-6)) - lo) / (hi - lo)))


def effective_halfwidth(hw, a):
    return hw + (hw / max(a, 1e-6) - hw) * compression_strength(hw)


# ── Poids de layers — port de app/src/layerWeights.ts (frontières lues dans
# la matrice), avec la simplification du prototype : poids "milkyway"
# reporté sur "localgroup" (la Voie lactée est rendue par son sprite).
ZA = MATRIX["zoom_axis"]
ORDER = ZA["layer_order"]
EDGES = [math.log10(e) for e in ZA["layer_edges_mpc"]]
FADES = ZA["fade_widths_dex"]


def layer_weights(hw):
    x = math.log10(max(hw, 1e-6))
    gates = [float(smoothstep((x - (e - f)) / (2 * f))) for e, f in zip(EDGES, FADES)]
    weights, remaining = {}, 1.0
    for i in range(len(ORDER) - 1):
        weights[ORDER[i]] = remaining * (1 - gates[i])
        remaining *= gates[i]
    weights[ORDER[-1]] = remaining
    weights["localgroup"] = weights.get("localgroup", 0) + weights.pop("milkyway", 0)
    return {k: v for k, v in weights.items() if v > 1e-3}


def layer_tone_map(entry, a, hw_eff, canvas_n):
    """Frame temporelle interpolée du layer, échantillonnée sur le cadre
    (fenêtre comobile ±hw_eff). Retourne (tone, fraction hors-texture par
    axe avant clamp, std de la frame)."""
    kfs = entry["keyframes_a"]
    imgs = FRAMES[entry["key"]]
    if a <= kfs[0]:
        frame = imgs[0]
    elif a >= kfs[-1]:
        frame = imgs[-1]
    else:
        i1 = int(np.searchsorted(kfs, a))
        i0 = i1 - 1
        frac = (math.log10(a) - math.log10(kfs[i0])) / (math.log10(kfs[i1]) - math.log10(kfs[i0]))
        frame = imgs[i0] * (1 - frac) + imgs[i1] * frac
    extent = entry["max_mpc"] * entry["margin_factor"]
    n_tex = frame.shape[0]
    lin = (np.arange(canvas_n) + 0.5) / canvas_n * 2 - 1
    mpc = lin * hw_eff
    tex = (mpc / (2 * extent) + 0.5) * (n_tex - 1)
    out_frac = float(((tex < 0) | (tex > n_tex - 1)).mean())
    yy, xx = np.meshgrid(tex, tex, indexing="ij")
    tone = map_coordinates(frame, [yy, xx], order=1, mode="nearest")
    return tone, out_frac, float(frame.std())


def interp_sim_positions(sim, t):
    frames = sim['frames']
    pos_t = t * (len(frames) - 1)
    i0 = min(int(pos_t), len(frames) - 2)
    frac = pos_t - i0
    p0 = np.array(frames[i0]['positions'])
    p1 = np.array(frames[i0 + 1]['positions'])
    return p0 + (p1 - p0) * frac


SPR = MATRIX["sprites"]


def splat_sprites(a, hw_eff, canvas_n):
    px_per_mpc = canvas_n / (2 * hw_eff)
    cx = cy = canvas_n / 2
    field = np.zeros((canvas_n, canvas_n))
    progress = 1 - structure_amplitude_scale(GAL_A_FORM, a)
    point_size = max(1.3 * (canvas_n / 300), 0.5)
    sigma_px = max(point_size * (1 + progress * SPR["point_radius_growth"]), 0.5)
    r = math.ceil(sigma_px * 3.2)
    inv2s2 = 1 / (2 * sigma_px ** 2)
    amp_scale = SPR["global_amp_scale"] / ((1 + progress * SPR["point_radius_growth"]) ** 2)
    for g in SCENE:
        sim = SIMS[g['slug']]
        positions = interp_sim_positions(sim, progress)
        rad = math.radians(g['angleDeg'])
        xs = cx + (math.cos(rad) * g['distanceMpc'] + positions[:, 0] * g['radiusMpc']) * px_per_mpc
        ys = cy + (math.sin(rad) * g['distanceMpc'] + positions[:, 1] * g['radiusMpc']) * px_per_mpc
        bs = np.array([m['b'] for m in sim['particleMeta']])
        amps = (0.18 + bs * 0.55) * amp_scale
        keep = (xs > -r) & (xs < canvas_n + r) & (ys > -r) & (ys < canvas_n + r)
        for px, py, amp in zip(xs[keep], ys[keep], amps[keep]):
            x0, x1 = max(0, int(px - r)), min(canvas_n - 1, int(px + r) + 1)
            y0, y1 = max(0, int(py - r)), min(canvas_n - 1, int(py + r) + 1)
            gy, gx = np.mgrid[y0:y1, x0:x1]
            field[y0:y1, x0:x1] += amp * np.exp(-((gx - px) ** 2 + (gy - py) ** 2) * inv2s2)
    return np.clip(1 - np.exp(-field), 0, 1)


def render_cell(hw, a, canvas_n=160):
    """Pipeline d'affichage complet — MÊMES formules que computeTone() du
    prototype spacetime-matrix-test.html."""
    hw_eff = effective_halfwidth(hw, a)
    weights = layer_weights(hw_eff)
    bg = np.zeros((canvas_n, canvas_n))
    clamp_defect = 0.0
    for key, w in weights.items():
        tone, out_frac, f_std = layer_tone_map(BY_KEY[key], a, hw_eff, canvas_n)
        bg += w * tone
        clamp_defect += w * out_frac * (f_std > 0.005)
    if hw_eff < SPR["visible_below_halfwidth_mpc"]:
        sprites = splat_sprites(a, hw_eff, canvas_n)
        bg = 1 - (1 - bg) * (1 - sprites)   # mélange "screen", §11.3
    white = white_channel(a)
    tone = 1 - (1 - bg) * (1 - white)       # embrasement en "screen", §11.4.c
    clamp_visible = clamp_defect * (1 - white)
    return tone, {"hw_eff": hw_eff, "white": white, "clamp": clamp_visible,
                  "weights": weights}
