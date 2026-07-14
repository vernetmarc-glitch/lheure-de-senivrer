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

# ── Mapping temps cosmique (table Planck déjà déployée)
_COSMO = json.load(open("../app/public/data/cosmology_table.json"))["rows"]
def _t_of_a(a_target):
    rows = _COSMO
    for i in range(len(rows) - 1):
        if rows[i]["a"] <= a_target <= rows[i + 1]["a"]:
            f = (a_target - rows[i]["a"]) / (rows[i + 1]["a"] - rows[i]["a"])
            return rows[i]["t_Gyr"] + (rows[i + 1]["t_Gyr"] - rows[i]["t_Gyr"]) * f
    return rows[0]["t_Gyr"] if a_target < rows[0]["a"] else rows[-1]["t_Gyr"]
T_MIN_GYR = round(_t_of_a(1.0 / 1101.0), 6)
T_MAX_GYR = round(_t_of_a(1.0), 4)

# ── Entrées galaxies réelles (catalogue + étendues monde des sprites cuits)
_CATALOG = json.load(open("../app/public/data/local_group_catalog.json"))
_KEYFRAMES = json.load(open("../app/public/data/dissolution_keyframes.json"))
_SLUG_BY_NAME = {
    'Andromède (M31)': 'andromede', 'Triangulum (M33)': 'triangulum',
    'Grand Nuage de Magellan': 'lmc', 'Petit Nuage de Magellan': 'smc',
    'Naine du Sagittaire': 'sagittaire', 'NGC 6822': 'ngc6822',
    'IC 10': 'ic10', 'Leo I': 'leo1',
}
def _sprite_halfwidth_units(slug):
    last = _KEYFRAMES[slug]["frames"][-1]["positions"]
    return max(max(abs(x), abs(y)) for x, y in last) * 1.15
REAL_GALAXY_ENTRIES = [{
    "slug": "milkyway", "name": "Voie lactée", "distance_mpc": 0.0,
    "angle_deg": 0.0, "radius_mpc": 0.01594329,
    "sprite_halfwidth_units": round(_sprite_halfwidth_units("milkyway"), 4),
    "sprite_halfwidth_mpc": round(_sprite_halfwidth_units("milkyway") * 0.01594329, 6),
}]
for _g in _CATALOG:
    if _g.get("isReal") and _g["name"] in _SLUG_BY_NAME:
        _slug = _SLUG_BY_NAME[_g["name"]]
        _hw = _sprite_halfwidth_units(_slug)
        REAL_GALAXY_ENTRIES.append({
            "slug": _slug, "name": _g["name"], "distance_mpc": _g["distanceMpc"],
            "angle_deg": _g["angleDeg"], "radius_mpc": _g["radiusMpc"],
            "sprite_halfwidth_units": round(_hw, 4),
            "sprite_halfwidth_mpc": round(_hw * _g["radiusMpc"], 6),
        })

# ── Effet d'expansion à l'échelle de chaque layer (nœuds validés 13/07)
EXPANSION_AT_LAYER = {"localgroup": 0.0, "l1b": 0.15, "l2": 0.65,
                      "l2b": 0.9, "l3": 1.0, "l3b": 1.0, "l4": 1.0,
                      "l4a": 1.0, "l4b": 1.0, "l5a": 1.0, "l5": 1.0}

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
        "compression": True,   # flux de Hubble — cf. bloc "expansion", §11.4.e
        "expansion_strength": EXPANSION_AT_LAYER[key],
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
    "expansion_strength": 0.0,
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

# ── Layer milkyway : la Voie lactée est rendue par son sprite N-corps
# (dissolution_sprites/milkyway_f*.png) posé sur le FOND localgroup
# (frames st_localgroup_* échantillonnées sur la fenêtre + plancher de
# convergence). Réintégré le 13 juillet (perdu dans la première version).
layers.append({
    "key": "milkyway",
    "kind": "sprite_plus_fond",
    "max_mpc": 0.1,                    # frontière layerWeights (0.1 Mpc)
    "margin_factor": None,
    "seed": None,
    "parent": None,
    "a_form": A_FORM_GAL,
    "dissolution_window_a": [round(A_START_GAL, 6), 1.0],
    "halfwidth_dex": round(max(-math.log10(A_FORM_GAL), 0.05), 4),
    "center_dex": round(math.log10(A_FORM_GAL), 4),
    "compression": False,
    "expansion_strength": 0.0,
    "anchor_a1": None,
    "anchor_scale_mpc": GALAXY_SCALE_MPC,
    "fond_layer": "localgroup",        # le poids de zoom milkyway est
                                       # reporté sur le fond localgroup
    "sprite_slug": "milkyway",
    "keyframes_a": [],                 # aucune frame propre à cuire
    "frame_pattern": None,
    "frame_resolution": None,
})

matrix = {
    "version": 2,
    "generated": "2026-07-13",
    "comment": "SOURCE DE VÉRITÉ éditable — cf. docs/matrice-parametres-zoom-temps.md. "
               "Éditer ici puis relancer scripts/generate_spacetime_frames.py "
               "et scripts/dev/validate_spacetime_matrix.py.",
    "time_axis": {
        "a_min": round(1.0 / 1101.0, 8),      # recombinaison z≈1100, §3
        "a_max": 1.0,
        # Affichage : temps cosmique LINÉAIRE en milliards d'années (décision
        # du 13 juillet — l'ancien curseur log10(a) étalait l'embrasement,
        # t<38 Myr, sur 42% de la course). Les keyframes de génération
        # restent définies en a ; le mapping a<->t vient de la table
        # cosmologique (Planck, H0=67.4). Pas d'anamorphose.
        "display": {
            "mode": "cosmic_time_gyr_linear",
            "mapping_table": "data/cosmology_table.json",
            "t_min_gyr": T_MIN_GYR,
            "t_max_gyr": T_MAX_GYR,
            "readout": ["t_gyr", "z", "a"],
        },
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
    # Effet d'expansion PAR ÉCHELLE (décision du 13 juillet, remplace
    # l'ancienne rampe globale lo=2/hi=15 qui violait le §11.4.e : force 0.66
    # à 8.5 Mpc -> "zoom" apparent sur le champ des 96 galaxies liées).
    # strength(hw) interpolé en smoothstep sur log10(s) entre les nœuds,
    # piloté par le demi-champ DEMANDÉ au curseur.
    # hw_eff = hw + (hw/a - hw) × strength(hw)
    "expansion": {
        "nodes": [[0.03, 0.0], [2.4, 0.0], [8.49, 0.15], [30.0, 0.65],
                  [67.08, 0.9], [150.0, 1.0], [14570.0, 1.0]],
        "comment": "≲2.4 Mpc lié (Groupe Local, aucun effet) ; 8.5 Mpc volume "
                   "local découplé (résiduel 0.15 validé) ; ≥150 Mpc flux de "
                   "Hubble pur — cf. §11.4.e",
    },
    "sprites": {   # rendu des galaxies par sprites N-corps CUITS (§11.5)
        # Correctif du 13 juillet : le prototype utilisait des splats de
        # particules bruts (points sans morphologie, flux conservé donc
        # jamais éteints) au lieu des 126 sprites cuits des sessions
        # précédentes. Désormais : frames pré-cuites uniquement.
        "frames_dir": "data/dissolution_sprites",
        "frame_pattern": "data/dissolution_sprites/{slug}_f{:02d}.png",
        "n_frames": 14,
        "frame_resolution": 512,
        # progress = 1 − A_gal(a), frame = progress × 13 (interpolation
        # linéaire entre les deux frames encadrantes)
        "progress": "1 - A(galaxy_scale_mpc, a)",
        # Extinction : contribution × A_gal(a)^fade_exponent — exposant 2 =>
        # les sprites se dissolvent DANS le fond AVANT que le fond (ancrages
        # à A_gal^1) ne se dissolve à son tour (séquencement validé 13/07).
        "fade_exponent": 2.0,
        "blend": "screen",              # §11.3 — jamais de fondu alpha temporel
        # Zone de visibilité : fondu en S sur le demi-champ EFFECTIF pour
        # éviter toute apparition brutale en zoomant.
        "visible_fade_band_mpc": [4.0, 6.0],
        # Plancher de lisibilité sur le CŒUR galactique (les naines sont
        # sous-pixel dès ~1 Mpc de demi-champ, et le cœur n'occupe que ~1/7
        # de la frame cadrée sur la dispersion finale -> aliasing) :
        # frame_half_px = max(physique, min_render_core_px × halfwidth_units).
        "min_render_core_px": 1.25,
        "catalog_json": "data/local_group_catalog.json",
    },
    # Génération des sprites — chaîne complète (documentée dans la matrice
    # à la demande du 13 juillet ; provenance : sessions des 9-10 juillet) :
    "real_galaxies": {
        "generation": {
            "simulation": {
                "script": "scripts/simulate_dissolution.mjs",
                "engine": "N-corps Barnes-Hut, intégrateur leapfrog",
                "n_steps": 480, "n_keyframes": 14,
                "theta": 0.75, "softening": 0.018,
                "particles_per_galaxy": 2500,
                "initial_conditions": "morphologies GalaxyModel réelles + "
                                      "composantes de vitesse rotationnelles",
                "output": "data/dissolution_keyframes.json",
            },
            "baking": {
                "script": "scripts/generate_dissolution_sprites.mjs",
                "point_size": 0.5, "halo_growth": 8.5, "blur_max_px": 6,
                "filament_amount": 0.8,
                "tone_transform": "1 - exp(-champ)  (canal saturant, §11.3)",
                "framing": "demi-largeur = maxExtent(dernière frame) × 1.15, "
                           "FIXE pour toutes les frames d'une galaxie",
                "progress_per_frame": "f / 13 (linéaire)",
            },
        },
        # sprite_halfwidth_units = maxExtent(f13)×1.15 en unités de rayon
        # galactique (calculé depuis dissolution_keyframes.json) ;
        # sprite_halfwidth_mpc = × radiusMpc — demi-étendue MONDE du sprite.
        "entries": REAL_GALAXY_ENTRIES,
    },
    "layers": layers,
    # Rempli par generate_spacetime_frames.py après cuisson (valeurs de
    # normalisation figées + tons mesurés) — cf. §13.3 "figer la
    # normalisation une fois".
    "computed": None,
}

# ── Nomenclature des cellules (demande du 14 juillet) : <lettre><chiffre>,
# lettre = ligne de zoom (A = Voie lactée ... L = l5), chiffre = colonne de
# temps (0 = recombinaison ... 10 = aujourd'hui, linéaire en Gyr comme le
# curseur). Ex : C7 = vue l1b (8.49 Mpc) à t≈9.65 Ga.
_ORDER = ['milkyway', 'localgroup', 'l1b', 'l2', 'l2b', 'l3', 'l3b',
          'l4', 'l4a', 'l4b', 'l5a', 'l5']
_BY_KEY = {l['key']: l for l in layers}
_zoom_rows = {chr(ord('A') + i): {"layer": k, "halfwidth_mpc": _BY_KEY[k]['max_mpc']}
              for i, k in enumerate(_ORDER)}
def _a_of_t(t):
    rows = _COSMO
    if t <= rows[0]["t_Gyr"]:
        return rows[0]["a"]
    for i in range(len(rows) - 1):
        if rows[i]["t_Gyr"] <= t <= rows[i + 1]["t_Gyr"]:
            f = (t - rows[i]["t_Gyr"]) / (rows[i + 1]["t_Gyr"] - rows[i]["t_Gyr"])
            return rows[i]["a"] + (rows[i + 1]["a"] - rows[i]["a"]) * f
    return rows[-1]["a"]
_time_cols = {}
for _k in range(11):
    _t = T_MIN_GYR + _k / 10 * (T_MAX_GYR - T_MIN_GYR)
    _a = min(_a_of_t(_t), 1.0)
    _time_cols[str(_k)] = {"t_gyr": round(_t, 4), "a": round(_a, 6),
                           "z": round(1 / _a - 1, 4)}
matrix["nomenclature"] = {
    "format": "<lettre><chiffre> — la lettre identifie la LIGNE de zoom (vue ancrée "
              "au demi-champ max_mpc du layer), le chiffre la COLONNE de temps "
              "(linéaire en Gyr, comme le curseur). Ex : C7 = vue l1b (8.49 Mpc) à t≈9.65 Ga.",
    "zoom_rows": _zoom_rows,
    "time_columns": _time_cols,
    "comment": "A = vue la plus rapprochée (Voie lactée), L = la plus large (l5, univers "
               "observable) ; 0 = recombinaison (t_min), 10 = aujourd'hui (t_max). Toute "
               "cellule de la matrice espace-temps × zoom se désigne par son code (ex. A10 = "
               "Voie lactée aujourd'hui, L0 = univers observable à la recombinaison). Le "
               "montage de validation est étiqueté avec ces codes.",
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
