"""
Port headless (Python/numpy/scipy) EXACT du pipeline de rendu de
app/public/time-axis-fullscene-test.html — pour valider par le calcul
(taux de saturation, histogramme) AVANT tout retour visuel, plutôt que de
découvrir les problèmes après coup via une capture d'écran de l'utilisateur.

node-canvas n'est pas installable dans cet environnement (dépendances
natives manquantes) — ce port Python est le moyen le plus fiable
disponible ici de "vraiment" exécuter le rendu hors-ligne.

Usage : python3 scripts/dev/validate_fullscene_render.py
"""
import json
import math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

CANVAS_N = 300  # plus petit que les 900 du navigateur, pour iterer vite ; le rendu est resolution-independant pour les stats qui nous interessent
DATA_DIR = "../../app/public/data"

# ---------------------------------------------------------------------
# Port de spacetime-shared.js
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Port du bruit de valeur (mulberry32 + value noise + multi-octave)
# ---------------------------------------------------------------------
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

def value_noise_field(n, grid_size, seed):
    rng = mulberry32(seed)
    g = max(2, round(grid_size))
    grid = np.array([rng() * 2 - 1 for _ in range((g + 1) * (g + 1))]).reshape(g + 1, g + 1)
    ys = np.linspace(0, g, n, endpoint=False)
    xs = np.linspace(0, g, n, endpoint=False)
    gy0 = np.clip(np.floor(ys).astype(int), 0, g - 1)
    gx0 = np.clip(np.floor(xs).astype(int), 0, g - 1)
    fy = ys - np.floor(ys)
    fx = xs - np.floor(xs)
    sy = fy * fy * (3 - 2 * fy)
    sx = fx * fx * (3 - 2 * fx)
    v00 = grid[gy0[:, None], gx0[None, :]]
    v10 = grid[gy0[:, None], gx0[None, :] + 1]
    v01 = grid[gy0[:, None] + 1, gx0[None, :]]
    v11 = grid[gy0[:, None] + 1, gx0[None, :] + 1]
    a = v00 + (v10 - v00) * sx[None, :]
    b = v01 + (v11 - v01) * sx[None, :]
    return a + (b - a) * sy[:, None]

def multi_octave_cloud(n, seed, base_grid):
    o1 = value_noise_field(n, base_grid, seed)
    o2 = value_noise_field(n, base_grid * 2.4, seed + 1)
    o3 = value_noise_field(n, base_grid * 5.5, seed + 2)
    return (o1 * 0.55 + o2 * 0.3 + o3 * 0.15 + 1) / 2  # 0..1

def background_raw_field(n, seed):
    o1 = value_noise_field(n, 5, seed)
    o2 = value_noise_field(n, 12, seed + 1)
    o3 = value_noise_field(n, 28, seed + 2)
    return o1 * 0.5 + o2 * 0.32 + o3 * 0.18  # ~zero-mean

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

# ---------------------------------------------------------------------
# Chargement des donnees (identiques a celles du navigateur)
# ---------------------------------------------------------------------
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

filament_noise_cache = multi_octave_cloud(CANVAS_N, 5151, 8)
bg_raw = background_raw_field(CANVAS_N, 9001)

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
        # Conservation du FLUX (pas juste une reduction cosmetique) : pour
        # un pic gaussien 2D, l'integrale totale est A*2*pi*sigma^2 — pour
        # la garder a peu pres constante quand sigma grandit (halo qui
        # s'etale), il faut diviser l'amplitude par sigma^2, pas sqrt(sigma).
        # GLOBAL_AMP_SCALE corrige en plus un probleme independant de la
        # dissolution : avec ~2500-6000 particules par galaxie, la simple
        # somme au centre du bulbe SATURE DEJA a a=1 (aujourd'hui, avant
        # toute dissolution) sans ce facteur — verifie : pic de champ brut
        # a 1605 sans lui (tone=1.0000, sature), 4.0 avec (tone=0.98).
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

    bg_late_fade = 1 - structure_amplitude(0.03, min(a * 6, 1))
    bg_amplitude = 0.55 * (1 - bg_late_fade * 0.85)
    field = field + bg_raw * bg_amplitude + bg_amplitude * 0.5

    scene_progress = 1 - structure_amplitude(0.03, a)
    blur_px = (scene_progress ** 1.5) * 14 * (CANVAS_N / 900)  # mise a l'echelle de la resolution reduite
    tone = 1 - np.exp(-np.clip(field, 0, None))
    tone = np.clip(tone, 0, 1)
    if blur_px > 0.3:
        tone = gaussian_filter(tone, sigma=blur_px)

    fil_intensity = 0.5
    v = tone * (1 + (filament_noise_cache - 0.5) * 2 * fil_intensity)
    v = np.clip(v, 0, 1)

    # Embrasement : reutilise EXACTEMENT bg_late_fade (deja une courbe
    # lisse qui monte vers 1 a l'approche de la recombinaison) au lieu
    # d'une fenetre etroite basee sur log(a) pres de a_min — cette derniere
    # creait un "creux" sombre juste avant un saut brutal vers le clair
    # (verifie : moyenne tombant a 2.2/255 juste avant le saut a 236/255).
    embrasement_mix = bg_late_fade
    target = universe_glow_color(a)

    rgb = colorize(v)
    rgb = rgb * (1 - embrasement_mix) + target * embrasement_mix
    return np.clip(rgb, 0, 255).astype(np.uint8), {
        'scene_progress': scene_progress, 'bg_amplitude': bg_amplitude,
        'embrasement_mix': embrasement_mix, 'blur_px': blur_px,
    }

if __name__ == '__main__':
    test_as = [1.0, 0.5, 0.24, 0.10, 0.03, 0.001, 3.16e-4]
    for a in test_as:
        rgb, dbg = render(a)
        gray = rgb.mean(axis=2)
        sat_frac = (gray > 240).mean()
        black_frac = (gray < 8).mean()
        print(f"a={a:.2e}  mean={gray.mean():6.1f}  std={gray.std():5.1f}  "
              f"%sat(>240)={sat_frac*100:5.1f}%  %noir(<8)={black_frac*100:5.1f}%  "
              f"progress={dbg['scene_progress']:.2f} bgAmp={dbg['bg_amplitude']:.2f} embrasement={dbg['embrasement_mix']:.2f}")
        Image.fromarray(rgb).resize((512, 512), Image.NEAREST).save(f"/home/claude/validate_a_{a:.0e}.png")
