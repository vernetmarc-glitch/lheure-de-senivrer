"""
Génère la MATRICE CANONIQUE de paramètres zoom × temps (§11.6 du document
d'architecture) : app/public/data/spacetime_matrix.json

Ce script ne produit AUCUN visuel — il fige, en un seul document versionnable,
tous les paramètres qui pilotent la génération des frames temporelles
(scripts/generate_spacetime_frames.py) et leur composition à l'affichage
(app/public/spacetime-matrix-test.html, et à terme la production).

RÈGLE D'AJUSTEMENT FUTUR : le JSON exporté est la SOURCE DE VÉRITÉ, éditable
à la main. Ce script ne sert qu'à le (re)construire depuis zéro si besoin —
relancer ce script ÉCRASE les ajustements manuels du JSON. Le flux normal
d'ajustement est : éditer le JSON -> relancer generate_spacetime_frames.py
-> relancer scripts/dev/validate_spacetime_matrix.py.

Provenance des valeurs : cf. docs/matrice-parametres-zoom-temps.md (chaque
champ y est documenté avec sa référence de section du doc d'architecture).
"""
import json
import math

OUT_PATH = "../app/public/data/spacetime_matrix.json"

# ── a_form(s) — points de contrôle, §11.4.a (identiques à spacetime-shared.js)
A_FORM_CONTROL_POINTS = [
    (math.log10(0.01), 0.20), (math.log10(2.4), 0.20), (math.log10(8.49), 0.55),
    (math.log10(30), 0.65), (math.log10(67), 0.70), (math.log10(150), 0.92),
    (math.log10(2100), 0.95), (math.log10(14570), 1.0),
]

def smoothstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)

def a_form_for_scale(scale_mpc):
    log_s = math.log10(max(scale_mpc, 1e-6))
    cps = A_FORM_CONTROL_POINTS
    if log_s <= cps[0][0]:
        return cps[0][1]
    if log_s >= cps[-1][0]:
        return cps[-1][1]
    for i in range(len(cps) - 1):
        if cps[i][0] <= log_s <= cps[i + 1][0]:
            span = cps[i + 1][0] - cps[i][0]
            t = smoothstep((log_s - cps[i][0]) / span) if span else 0.0
            return cps[i][1] + (cps[i + 1][1] - cps[i][1]) * t
    return cps[-1][1]

def transition_window(a_form):
    """Fenêtre de dissolution [a_debut, 1] en a, cohérente avec le correctif
    de continuité du 13 juillet dans spacetime-shared.js (§11.4.b) :
    largeur w = max(-log10(a_form), 0.05), centre = min(log10(a_form), -w),
    la fenêtre se termine TOUJOURS exactement à a=1."""
    w = max(-math.log10(a_form), 0.05)
    center = min(math.log10(a_form), -w)
    return 10 ** (center - w), w, center

def log_keyframes(a_lo, a_hi, k):
    """k valeurs de a, log-uniformes de a_lo à a_hi inclus (croissant)."""
    lo, hi = math.log10(a_lo), math.log10(a_hi)
    return [round(10 ** (lo + (hi - lo) * i / (k - 1)), 6) for i in range(k)]

# ── Échelle "galaxies" pour tout ce qui suit la dissolution des galaxies
# elles-mêmes (ancrages Groupe Local, sprites, embrasement) — §11.4.b/c.
GALAXY_SCALE_MPC = 0.03
A_FORM_GAL = a_form_for_scale(GALAXY_SCALE_MPC)          # 0.20
A_START_GAL, _, _ = transition_window(A_FORM_GAL)         # 0.04

K_TRANSITION = 9   # keyframes dans la fenêtre de dissolution du layer
K_ANCHOR_TAIL = 4  # keyframes supplémentaires (queue de dissolution de l'ancrage)

# ── Layers de densité procéduraux (mêmes clés/échelles/seeds/parents que
# scripts/generate_layers.py LAYER_SPECS — NE PAS diverger) + localgroup.
GRF_SPECS = [
    ("l5", 14570.0, 42, None, 2.4),
    ("l5a", 5531.46, 48, "l5", 1.5),
    ("l4b", 2100.0, 55, "l5", 1.5),
    ("l4a", 793.73, 61, "l4b", 1.5),
    ("l4", 300.0, 101, "l4b", 1.5),
    ("l3b", 212.13, 108, "l4", 1.5),
    ("l3", 150.0, 102, "l4", 1.5),
    ("l2b", 67.08, 112, "l3", 1.5),
    ("l2", 30.0, 103, "l3", 1.5),
    ("l1b", 8.49, 117, "l2", 1.5),
]

# Paramètres d'ancrage Groupe Local à a=1 — copie EXACTE de
# generate_layers.py main() (7 juillet, itérations 3-5). La modulation
# temporelle (multiplication par A_gal(a)) est décrite champ par champ dans
# docs/matrice-parametres-zoom-temps.md.
ANCHORS_A1 = {
    "l1b": {"strength": 1.0, "global_suppression": 0.35, "size_multiplier": 1.8,
            "real_only": False, "bump_amplitude_factor": 0.50, "extra_blur_px": 0.6,
            "diffuse": False},
    "l2": {"strength": 1.6, "real_only": False, "diffuse": True,
           "size_multiplier": 5.0, "bump_amplitude_factor": 2.6},
    "l2b": {"strength": 0.85, "real_only": False, "diffuse": True,
            "size_multiplier": 5.0, "bump_amplitude_factor": 1.7},
}

layers = []
for key, max_mpc, seed, parent, margin in GRF_SPECS:
    a_form = a_form_for_scale(max_mpc)
    a_start, w_dex, center_dex = transition_window(a_form)
    anchored = key in ANCHORS_A1
    keyframes = log_keyframes(a_start, 1.0, K_TRANSITION)
    if anchored and A_START_GAL < a_start:
        # Queue : l'ancrage (échelle galaxies) se dissout PLUS TARD en
        # remontant le temps que le champ du layer lui-même (§11.4.b).
        tail = log_keyframes(A_START_GAL, a_start, K_ANCHOR_TAIL + 1)[:-1]
        keyframes = tail + keyframes
    layers.append({
        "key": key,
        "kind": "grf",
        "max_mpc": max_mpc,
        "margin_factor": margin,
        "seed": seed,
        "parent": parent,
        "a_form": round(a_form, 4),
        "dissolution_window_a": [round(a_start, 6), 1.0],
        "halfwidth_dex": round(w_dex, 4),
        "center_dex": round(center_dex, 4),
        "compression": True,   # flux de Hubble — pondéré par compressionStrength(s), §11.4.e
        "anchor_a1": ANCHORS_A1.get(key),
        "anchor_scale_mpc": GALAXY_SCALE_MPC if anchored else None,
        "keyframes_a": keyframes,
        "frame_pattern": f"data/st_{key}_k{{:02d}}.png",
        "frame_resolution": 512,
    })

# localgroup — texture procédurale (98 galaxies) + fond FFT résiduel §4.8.
lg_keyframes = log_keyframes(A_START_GAL, 1.0, 12)
layers.append({
    "key": "localgroup",
    "kind": "procedural_galaxies",
    "max_mpc": 2.4,
    "margin_factor": 1.5,
    "seed": None,
    "parent": None,
    "a_form": A_FORM_GAL,
    "dissolution_window_a": [round(A_START_GAL, 6), 1.0],
    "halfwidth_dex": round(max(-math.log10(A_FORM_GAL), 0.05), 4),
    "center_dex": round(math.log10(A_FORM_GAL), 4),
    "compression": False,  # Groupe Local lié gravitationnellement, §11.4.e
    "anchor_a1": None,
    "anchor_scale_mpc": GALAXY_SCALE_MPC,
    "residual_bg": {  # §4.8 — calibré le 10 juillet, intégré ici (§11.7)
        "amplitude_a1": 0.35,
        "seed": 31415,
        "vmax_reference": 4.074,
        "target_mean_a1": 8.95,   # /255, mesuré §4.8
    },
    # Ton uniforme de convergence : le même que l'état dissous des layers
    # GRF (field_to_log_density(0) normalisé par le vmin/vmax partagé de
    # production) — calculé et inscrit par generate_spacetime_frames.py
    # dans "computed". Cohérence de luminosité §11.1 point 3.
    "uniform_floor": "match_grf_dissolved_tone",
    "keyframes_a": lg_keyframes,
    "frame_pattern": "data/st_localgroup_k{:02d}.png",
    "frame_resolution": 512,
})

matrix = {
    "version": 1,
    "generated": "2026-07-13",
    "comment": "SOURCE DE VÉRITÉ éditable — cf. docs/matrice-parametres-zoom-temps.md. "
               "Éditer ici puis relancer scripts/generate_spacetime_frames.py "
               "et scripts/dev/validate_spacetime_matrix.py.",
    "time_axis": {
        "a_min": round(1.0 / 1101.0, 8),      # recombinaison z≈1100, §3
        "a_max": 1.0,
        "slider_log10a_range": [round(math.log10(1.0 / 1101.0), 4), 0.0],
    },
    "zoom_axis": {
        "halfwidth_min_mpc": 0.02,             # UniverseMap.tsx
        "halfwidth_max_mpc": 14570.0,
        # Frontières et largeurs de fondu entre layers — copie de
        # app/src/layerWeights.ts (LAYER_EDGES_MPC / FADE_WIDTHS_DEX).
        "layer_order": ["milkyway", "localgroup", "l1b", "l2", "l2b", "l3",
                        "l3b", "l4", "l4a", "l4b", "l5a", "l5"],
        "layer_edges_mpc": [0.1, 2.4, 8.49, 30, 67.08, 150, 212.13, 300,
                            793.73, 2100, 5531.46],
        "fade_widths_dex": [0.15, 0.52, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15,
                            0.15, 0.15, 0.15],
    },
    "galaxy_scale_mpc": GALAXY_SCALE_MPC,
    "embrasement": {   # §11.4.c — calibré le 10 juillet, inchangé
        "exp": 5, "offset_max": 18, "fade_scale_mpc": GALAXY_SCALE_MPC,
        "a_multiplier": 6,
    },
    "compression": {   # §11.4.e — fondu en S entre lié et flux de Hubble
        "lo_mpc": 2.0, "hi_mpc": 15.0,
    },
    "sprites": {       # zone sprites du prototype (Groupe Local, §11.5)
        "visible_below_halfwidth_mpc": 4.0,
        "keyframes_json": "data/dissolution_keyframes.json",
        "catalog_json": "data/local_group_catalog.json",
        "point_radius_growth": 1.2,     # 1+progress*1.2, correctif 10 juillet
        "global_amp_scale": 0.0025,     # conservation de flux, §11.4.b
    },
    "layers": layers,
    # Rempli par generate_spacetime_frames.py après cuisson (valeurs de
    # normalisation figées + tons mesurés) — cf. §13.3 "figer la
    # normalisation une fois".
    "computed": None,
}

with open(OUT_PATH, "w") as f:
    json.dump(matrix, f, indent=1, ensure_ascii=False)

n_frames = sum(len(l["keyframes_a"]) for l in layers)
print(f"Matrice écrite -> {OUT_PATH}")
print(f"{len(layers)} layers temporels, {n_frames} frames à cuire")
for l in layers:
    print(f"  {l['key']:<11} s={l['max_mpc']:<8} a_form={l['a_form']:<6} "
          f"fenêtre a=[{l['dissolution_window_a'][0]:.4f}, 1] "
          f"{len(l['keyframes_a'])} keyframes")
