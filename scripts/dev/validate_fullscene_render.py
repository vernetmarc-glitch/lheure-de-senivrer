"""
Port headless (Python/numpy/scipy) EXACT du pipeline de rendu de
app/public/time-axis-fullscene-test.html, VERSION 2 (10 juillet) — plus de
flou de fusion, plus de fondu vers une couleur unie comme mécanisme de
dissolution. Le nuage filamenteux grandit d'échelle (zoom sur la même
grille de bruit) au lieu d'être flouté. Cf. §13 du document d'architecture.

Usage : python3 scripts/dev/validate_fullscene_render.py
"""
import json
import math
import numpy as np
from PIL import Image

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

def mulberry32(seed):
    state = seed & 0xffffffff
    def rng():
        nonlocal state
        state = (state + 0x6d2b79f5) & 0xffffffff
        t = state
        t = (t ^ (t >> 15)) * (1 | t) & 0xffffffff
        t = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xffffffff) ^ t) & 0xffffffff
        return ((t ^ (t >> 14)) & 0xffffffff) / 4294967296
    return rng

def make_noise_grid(grid_size, seed):
    rng = mulberry32(seed)
    g = max(2, round(grid_size))
    grid = np.array([rng() * 2 - 1 for _ in range((g + 1) * (g + 1))]).reshape(g + 1, g + 1)
    return grid, g

BG_OCTAVES = [
    (make_noise_grid(10, 9001), 0.5),
    (make_noise_grid(24, 9002), 0.32),
    (make_noise_grid(55, 9003), 0.18),
]

def sample_grid_bilinear(grid, g, u, v):
    gx, gy = u * g, v * g
    gx0 = np.clip(np.floor(gx).astype(int), 0, g - 1)
    gy0 = np.clip(np.floor(gy).astype(int), 0, g - 1)
    fx, fy = gx - np.floor(gx), gy - np.floor(gy)
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    v00 = grid[gy0, gx0]; v10 = grid[gy0, np.clip(gx0 + 1, 0, g)]
    v01 = grid[np.clip(gy0 + 1, 0, g), gx0]; v11 = grid[np.clip(gy0 + 1, 0, g), np.clip(gx0 + 1, 0, g)]
    a = v00 + (v10 - v00) * sx
    b = v01 + (v11 - v01) * sx
    return a + (b - a) * sy

def background_field(n, zoom):
    xs, ys = np.meshgrid(np.arange(n) / n, np.arange(n) / n)
    u = 0.5 + (xs - 0.5) / zoom
    v = 0.5 + (ys - 0.5) / zoom
    out = np.zeros((n, n))
    for (grid, g), w in BG_OCTAVES:
        out += sample_grid_bilinear(grid, g, u, v) * w
    return out

ASTRO_STOPS = np.array([
    [0,0,0], [0x17,0x0a,0x05], [0x4a,0x1f,0x0a], [0xa8,0x48,0x0f], [0xe8,0xa1,0x3a], [0xff,0xf3,0xd6]
], dtype=np.float64)

def colorize(norm):
    n_stops = len(ASTRO_STOPS) - 1
    idx = np.clip((norm * n_stops).astype(int), 0, n_stops - 1)
    frac = (norm * n_stops) - idx
    a = ASTRO_STOPS[idx]
    b = ASTRO_STOPS[idx + 1]
    return a + (b - a) * frac[..., None]

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

        sigma_px = max(point_size * (1 + progress * 6), 0.5)
        r = math.ceil(sigma_px * 3.2)
        inv2s2 = 1 / (2 * sigma_px * sigma_px)
        GLOBAL_AMP_SCALE = 0.0025
        amp_scale = GLOBAL_AMP_SCALE / ((1 + progress * 6) ** 2)

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
    ZOOM_MAX = 9
    noise_zoom = 1 + scene_progress * (ZOOM_MAX - 1)
    bg_amplitude = 0.5
    bg = background_field(CANVAS_N, noise_zoom)
    field = field + bg * bg_amplitude + bg_amplitude * 0.5

    tone = np.clip(1 - np.exp(-field), 0, 1)

    bg_late_fade = 1 - structure_amplitude(0.03, min(a * 6, 1))
    embrasement_mix = bg_late_fade
    target = universe_glow_color(a)

    rgb = colorize(tone)
    rgb = rgb * (1 - embrasement_mix) + target * embrasement_mix
    return np.clip(rgb, 0, 255).astype(np.uint8), {
        'scene_progress': scene_progress, 'noise_zoom': noise_zoom,
        'embrasement_mix': embrasement_mix, 'tone': tone,
    }

def dominant_feature_size(tone_2d):
    f = tone_2d - tone_2d.mean()
    fft = np.fft.fft2(f)
    acorr = np.fft.ifft2(fft * np.conj(fft)).real
    acorr = np.fft.fftshift(acorr)
    acorr /= acorr.max()
    c = CANVAS_N // 2
    profile = acorr[c, c:]
    below_half = np.where(profile < 0.5)[0]
    return int(below_half[0]) if len(below_half) else len(profile)

if __name__ == '__main__':
    test_as = [1.0, 0.5, 0.24, 0.10, 0.03, 0.01, 0.003, 0.001]
    print("Verification 1 : saturation / continuite / contraste global")
    for a in test_as:
        rgb, dbg = render(a)
        gray = rgb.mean(axis=2)
        sat_frac = (gray > 240).mean()
        black_frac = (gray < 8).mean()
        print(f"a={a:.2e}  mean={gray.mean():6.1f}  std={gray.std():5.1f}  "
              f"%sat(>240)={sat_frac*100:5.1f}%  %noir(<8)={black_frac*100:5.1f}%  "
              f"zoom_x{dbg['noise_zoom']:.1f}  embrasement={dbg['embrasement_mix']:.2f}")
        Image.fromarray(rgb).resize((512, 512), Image.NEAREST).save(f"/home/claude/v2_a_{a:.0e}.png")

    print("\nVerification 2 : les filaments GRANDISSENT-ils reellement (autocorrelation) ?")
    for a in test_as:
        rgb, dbg = render(a)
        size_px = dominant_feature_size(dbg['tone'])
        print(f"a={a:.2e}  taille caracteristique des structures ~ {size_px}px (sur {CANVAS_N}px)  zoom_x{dbg['noise_zoom']:.1f}")
