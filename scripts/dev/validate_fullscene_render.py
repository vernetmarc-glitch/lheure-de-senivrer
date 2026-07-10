"""
Port headless (Python/numpy/scipy) EXACT du pipeline de rendu de
app/public/time-axis-fullscene-test.html, VERSION 3 (10 juillet) :
- Points (simulation N-corps) : croissance de rayon fortement réduite
  (1+progress*1.2, pas *6) — la dispersion spatiale vient de la vraie
  simulation, pas d'un grossissement artificiel.
- Fond filamenteux : frames CUITES hors-ligne (bg_filament_f00-09.png,
  cf. generate_bg_filament_keyframes.py) — vrai champ FFT à spectre de
  puissance réaliste, PAS une grille de bruit interpolée en douceur (qui
  restait un filtre passe-bas même sans flou explicite — vérifié : la
  variance du laplacien s'effondrait à ~0 à fort zoom, quelle que soit la
  résolution de la grille source).
- Combinaison points + fond par mélange "screen" (1-(1-a)(1-b)), pas une
  addition dans un champ brut commun — chacun garde sa propre netteté.

Cf. §13 du document d'architecture. Usage :
  python3 scripts/dev/validate_fullscene_render.py
"""
import json
import math
import numpy as np
from PIL import Image
from scipy.ndimage import laplace, zoom as ndi_zoom

CANVAS_N = 300
DATA_DIR = "../../app/public/data"

A_FORM_CONTROL_POINTS = [
    (math.log10(0.01), 0.20), (math.log10(2.4), 0.20), (math.log10(8.49), 0.55),
    (math.log10(30), 0.65), (math.log10(67), 0.70), (math.log10(150), 0.92),
    (math.log10(2100), 0.95), (math.log10(14570), 1.0),
]

def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def a_form_for_scale_mpc(scale_mpc):
    log_s = math.log10(max(scale_mpc, 1e-6))
    cps = A_FORM_CONTROL_POINTS
    if log_s <= cps[0][0]: return cps[0][1]
    if log_s >= cps[-1][0]: return cps[-1][1]
    for i in range(len(cps) - 1):
        if cps[i][0] <= log_s <= cps[i+1][0]:
            span = cps[i+1][0] - cps[i][0]
            t = smoothstep((log_s - cps[i][0]) / span) if span != 0 else 0
            return cps[i][1] + (cps[i+1][1] - cps[i][1]) * t
    return cps[-1][1]

def structure_amplitude(scale_mpc, a):
    if a >= 1: return 1.0
    a_form = a_form_for_scale_mpc(scale_mpc)
    half_width_dex = max(-math.log10(a_form), 0.05)
    x = math.log10(max(a, 1e-6)) - math.log10(a_form)
    t = (x + half_width_dex) / (2 * half_width_dex)
    return float(smoothstep(np.array(t)))

def universe_glow_color(a, exp=2.2):
    t = max(0, min(1 - a, 1)) ** exp
    bg = np.array([5, 5, 10])
    bright = np.array([255, 243, 214])
    return bg + (bright - bg) * t

with open(f"{DATA_DIR}/dissolution_keyframes.json") as f:
    all_sims = json.load(f)
with open(f"{DATA_DIR}/local_group_catalog.json") as f:
    catalog = json.load(f)

SLUG_BY_NAME = {
    'Andromède (M31)': 'andromede', 'Triangulum (M33)': 'triangulum', 'Grand Nuage de Magellan': 'lmc',
    'Petit Nuage de Magellan': 'smc', 'Naine du Sagittaire': 'sagittaire', 'NGC 6822': 'ngc6822',
    'IC 10': 'ic10', 'Leo I': 'leo1',
}
scene = [{'slug': 'milkyway', 'distanceMpc': 0, 'angleDeg': 0, 'radiusMpc': 0.01594329}]
for gal in catalog:
    if not gal.get('isReal'): continue
    slug = SLUG_BY_NAME.get(gal['name'])
    if not slug: continue
    scene.append({'slug': slug, 'distanceMpc': gal['distanceMpc'], 'angleDeg': gal['angleDeg'], 'radiusMpc': gal['radiusMpc']})

BG_FRAMES = [np.array(Image.open(f"{DATA_DIR}/bg_filament_f{i:02d}.png").convert('L')).astype(np.float64) / 255 for i in range(10)]

def interpolate_frame(sim, t):
    frames = sim['frames']
    n_f = len(frames)
    pos_t = t * (n_f - 1)
    i0 = min(int(math.floor(pos_t)), n_f - 2)
    i1 = i0 + 1
    frac = pos_t - i0
    p0 = np.array(frames[i0]['positions'])
    p1 = np.array(frames[i1]['positions'])
    return p0 + (p1 - p0) * frac

def sample_bg(progress, canvas_n):
    pos = progress * 9
    i0 = min(int(pos), 8)
    i1 = i0 + 1
    frac = pos - i0
    f0, f1 = BG_FRAMES[i0], BG_FRAMES[i1]
    if f0.shape[0] != canvas_n:
        f0 = ndi_zoom(f0, canvas_n / f0.shape[0], order=1)
        f1 = ndi_zoom(f1, canvas_n / f1.shape[0], order=1)
    return f0 + (f1 - f0) * frac

def render(a, half_width_mpc=1.0, point_size=1.3):
    px_per_mpc = CANVAS_N / (2 * half_width_mpc)
    cx = cy = CANVAS_N / 2
    field = np.zeros((CANVAS_N, CANVAS_N))

    for g in scene:
        sim = all_sims[g['slug']]
        progress = 1 - structure_amplitude(g['radiusMpc'], a)
        positions = interpolate_frame(sim, progress)
        meta = sim['particleMeta']
        rad = math.radians(g['angleDeg'])
        center_x_mpc = math.cos(rad) * g['distanceMpc']
        center_y_mpc = math.sin(rad) * g['distanceMpc']

        sigma_px = max(point_size * (1 + progress * 1.2), 0.5)
        r = math.ceil(sigma_px * 3.2)
        inv2s2 = 1 / (2 * sigma_px * sigma_px)
        amp_scale = 0.0025 / ((1 + progress * 1.2) ** 2)

        xs_mpc = center_x_mpc + positions[:, 0] * g['radiusMpc']
        ys_mpc = center_y_mpc + positions[:, 1] * g['radiusMpc']
        pxs = cx + xs_mpc * px_per_mpc
        pys = cy + ys_mpc * px_per_mpc
        bs = np.array([m['b'] for m in meta])
        amps = (0.18 + bs * 0.55) * amp_scale

        for px, py, amp in zip(pxs, pys, amps):
            if px < -r or px > CANVAS_N + r or py < -r or py > CANVAS_N + r:
                continue
            x0, x1 = max(0, int(px - r)), min(CANVAS_N - 1, int(px + r) + 1)
            y0, y1 = max(0, int(py - r)), min(CANVAS_N - 1, int(py + r) + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            d2 = (xx - px) ** 2 + (yy - py) ** 2
            field[y0:y1, x0:x1] += amp * np.exp(-d2 * inv2s2)

    scene_progress = 1 - structure_amplitude(0.03, a)
    point_tone = np.clip(1 - np.exp(-field), 0, 1)
    bg_tone = sample_bg(scene_progress, CANVAS_N)
    tone = 1 - (1 - point_tone) * (1 - bg_tone)  # melange "screen", pas une addition dans un champ commun

    bg_late_fade = 1 - structure_amplitude(0.03, min(a * 6, 1))
    embrasement_mix = bg_late_fade
    target = universe_glow_color(a)

    ASTRO_STOPS = np.array([
        [0,0,0], [0x17,0x0a,0x05], [0x4a,0x1f,0x0a], [0xa8,0x48,0x0f], [0xe8,0xa1,0x3a], [0xff,0xf3,0xd6]
    ], dtype=np.float64)
    n_stops = len(ASTRO_STOPS) - 1
    idx = np.clip((tone * n_stops).astype(int), 0, n_stops - 1)
    frac = (tone * n_stops) - idx
    rgb = ASTRO_STOPS[idx] + (ASTRO_STOPS[idx + 1] - ASTRO_STOPS[idx]) * frac[..., None]
    rgb = rgb * (1 - embrasement_mix) + target * embrasement_mix

    return np.clip(rgb, 0, 255).astype(np.uint8), {
        'scene_progress': scene_progress, 'embrasement_mix': embrasement_mix, 'tone': tone,
    }

if __name__ == '__main__':
    test_as = [1.0, 0.5, 0.24, 0.10, 0.03, 0.01, 0.003, 0.001]
    print("Saturation / continuite / piqué (laplacien = contenu haute frequence, NE DOIT JAMAIS tomber a 0)")
    for a in test_as:
        rgb, dbg = render(a)
        tone = dbg['tone']
        sat_frac = (tone > 0.98).mean()
        lap_var = laplace(tone).var()
        print(f"a={a:.2e}  mean_tone={tone.mean():.3f}  std={tone.std():.3f}  "
              f"%sat(>0.98)={sat_frac*100:5.1f}%  laplacien={lap_var:.5f}  "
              f"progress={dbg['scene_progress']:.2f}  embrasement={dbg['embrasement_mix']:.2f}")
        Image.fromarray(rgb).resize((512, 512), Image.NEAREST).save(f"/home/claude/v3_a_{a:.0e}.png")
