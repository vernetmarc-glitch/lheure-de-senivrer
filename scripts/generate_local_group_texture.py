"""
Génère une texture statique pour le layer "Groupe Local" — UNIQUEMENT pour
les galaxies PROCÉDURALES (non nommées, lointaines). Les galaxies réelles
nommées (Andromède, M33, Nuages de Magellan...) sont désormais rendues comme
un semis de points individuels côté JS (cf. app/src/nearbyGalaxyStars.ts),
pour un rendu cohérent avec la Voie lactée — plus une simple tache de halo.

Sortie : app/public/data/density_localgroup.png
Box : 4.8 Mpc de côté (max_mpc=2.4, cf. layerWeights.ts LAYER_EDGES_MPC[1])
"""

import numpy as np
from PIL import Image
from generate_local_group_catalog import build_catalog

N = 1024
MAX_MPC = 2.4
MARGIN_FACTOR = 1.5

AMPLITUDE = 3.5
HALO_SCALE = 0.85
CORE_SCALE = 1.1
# Taille du halo PROPORTIONNELLE au rayon assigné à chaque galaxie procédurale
# (plutôt qu'une taille unique pour toutes) — cohérent avec la correction
# apportée aux galaxies réelles. VISIBILITY_SCALE compense le fait que ces
# rayons (~0.0003-0.0015 Mpc) sont sous la taille d'un pixel à cette résolution.
VISIBILITY_SCALE = 22.0
MIN_SIZE_MPC = 0.006  # plancher pour rester visible même pour les plus petites

NEAR_MPC = 0.15
FAR_MPC = 1.0
PERIPHERAL_BOOST = 4.0


def halo_distance_factor(distance_mpc):
    t = np.clip((distance_mpc - NEAR_MPC) / (FAR_MPC - NEAR_MPC), 0, 1)
    smooth = t * t * (3 - 2 * t)
    return 1.0 + (PERIPHERAL_BOOST - 1.0) * smooth


def build_field(catalog, max_mpc, n, margin_factor=1.0):
    box_mpc = 2 * max_mpc * margin_factor
    pixel_size_mpc = box_mpc / n
    yy, xx = np.indices((n, n))
    cx, cy = n / 2, n / 2
    x_mpc = (xx - cx) * pixel_size_mpc
    y_mpc = (yy - cy) * pixel_size_mpc

    field = np.zeros((n, n))
    for gal in catalog:
        if gal["isReal"]:
            continue  # rendues en points cote JS, cf. nearbyGalaxyStars.ts
        if gal["distanceMpc"] > max_mpc * margin_factor * 1.05:
            continue
        angle_rad = np.radians(gal["angleDeg"])
        gx = np.cos(angle_rad) * gal["distanceMpc"]
        gy = np.sin(angle_rad) * gal["distanceMpc"]
        peak_amp = np.log(1 + gal["brightness"] * AMPLITUDE)
        halo_scale = HALO_SCALE * halo_distance_factor(gal["distanceMpc"])
        size_mpc = max(gal["radiusMpc"] * VISIBILITY_SCALE, MIN_SIZE_MPC)
        core_sigma_mpc = pixel_size_mpc * 1.5
        field += halo_scale * peak_amp * np.exp(-((x_mpc - gx) ** 2 + (y_mpc - gy) ** 2) / (2 * size_mpc ** 2))
        field += CORE_SCALE * peak_amp * np.exp(-((x_mpc - gx) ** 2 + (y_mpc - gy) ** 2) / (2 * core_sigma_mpc ** 2))
    return field


if __name__ == "__main__":
    catalog = build_catalog()
    field = build_field(catalog, MAX_MPC, N, margin_factor=MARGIN_FACTOR)

    VMAX_REFERENCE = 4.074
    norm = np.clip(field / VMAX_REFERENCE, 0, 1)
    img_data = (norm * 255).astype(np.uint8)
    out_path = "../app/public/data/density_localgroup.png"
    Image.fromarray(img_data, mode="L").save(out_path)
    print(f"Texture Groupe Local generee -> {out_path}")
    print(f"max brut: {field.max():.3f}, pixels satures (>0.99): {(norm>0.99).sum()}")
