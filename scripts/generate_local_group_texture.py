"""
Génère une texture statique pour le layer "Groupe Local" (halo+point par
galaxie), pour remplacer le calcul en direct (trop coûteux à chaque frame,
cf. retour utilisateur sur les lenteurs de zoom).

Contrairement à la version live précédente (sigma large ~0.59 Mpc, pensée
pour une seule échelle de vue), cette texture utilise un sigma BEAUCOUP plus
petit pour que chaque galaxie proche (Sagittaire, Nuages de Magellan...)
garde un halo distinct au lieu de fusionner en une seule tache.

Sortie : app/public/data/density_localgroup.png
Box : 4.8 Mpc de côté (max_mpc=2.4, cf. layerWeights.ts LAYER_EDGES_MPC[1])
"""

import numpy as np
from PIL import Image
from generate_local_group_catalog import build_catalog

N = 1024  # marge de securite supplementaire, en plus du fix DPR cote app
MAX_MPC = 2.4  # cf. layerWeights.ts : frontiere Groupe Local / L2 (frontiere LOGIQUE)
MARGIN_FACTOR = 1.5  # cf. generate_layers.py : meme marge, pour recadrage rectangulaire

SIZE_MPC = 0.02       # sigma du halo, calé sur le rayon reel de la Voie lactee (~0.016 Mpc)
AMPLITUDE = 3.5
HALO_SCALE = 0.85     # halo DE BASE (galaxies proches, ex. Sagittaire/Magellan) — inchange
CORE_SCALE = 1.1

# Le halo de base convient aux galaxies proches (Sagittaire, Nuages de
# Magellan...) : les rendre plus lumineuses les ferait "toucher" la Voie
# lactee. Les galaxies plus eloignees (Andromede, M33, la population
# procedurale...) ont en revanche besoin d'un halo plus marque pour ne pas
# laisser la vue trop vide a ce niveau de zoom. On applique donc un facteur
# qui grandit progressivement avec la distance (1x pres du centre, jusqu'a
# PERIPHERAL_BOOST x au-dela de FAR_MPC), sans toucher au point central.
NEAR_MPC = 0.15   # en-deca : halo inchange (1x)
FAR_MPC = 1.0     # au-dela : halo pleinement renforce
PERIPHERAL_BOOST = 4.0


def halo_distance_factor(distance_mpc):
    t = np.clip((distance_mpc - NEAR_MPC) / (FAR_MPC - NEAR_MPC), 0, 1)
    smooth = t * t * (3 - 2 * t)  # smoothstep, transition douce
    return 1.0 + (PERIPHERAL_BOOST - 1.0) * smooth


def build_field(catalog, max_mpc, n, margin_factor=1.0):
    box_mpc = 2 * max_mpc * margin_factor
    pixel_size_mpc = box_mpc / n
    core_sigma_mpc = pixel_size_mpc * 1.5
    yy, xx = np.indices((n, n))
    cx, cy = n / 2, n / 2
    x_mpc = (xx - cx) * pixel_size_mpc
    y_mpc = (yy - cy) * pixel_size_mpc

    field = np.zeros((n, n))
    for gal in catalog:
        if gal["distanceMpc"] > max_mpc * margin_factor * 1.05:
            continue
        angle_rad = np.radians(gal["angleDeg"])
        gx = np.cos(angle_rad) * gal["distanceMpc"]
        gy = np.sin(angle_rad) * gal["distanceMpc"]
        peak_amp = np.log(1 + gal["brightness"] * AMPLITUDE)
        halo_scale = HALO_SCALE * halo_distance_factor(gal["distanceMpc"])
        field += halo_scale * peak_amp * np.exp(-((x_mpc - gx) ** 2 + (y_mpc - gy) ** 2) / (2 * SIZE_MPC ** 2))
        field += CORE_SCALE * peak_amp * np.exp(-((x_mpc - gx) ** 2 + (y_mpc - gy) ** 2) / (2 * core_sigma_mpc ** 2))
    return field


if __name__ == "__main__":
    catalog = build_catalog()
    field = build_field(catalog, MAX_MPC, N, margin_factor=MARGIN_FACTOR)

    # Référence de normalisation FIXE (pas field.max()) : si on renormalisait
    # dynamiquement à chaque changement, renforcer le halo des galaxies
    # lointaines ferait remonter le maximum global et assombrirait par
    # ricochet les galaxies proches déjà calibrées — l'inverse de l'effet
    # recherché. Les nouveaux pics plus forts saturent simplement en blanc
    # pur, ce qui est cohérent avec "beaucoup plus lumineux".
    VMAX_REFERENCE = 4.074
    norm = np.clip(field / VMAX_REFERENCE, 0, 1)
    img_data = (norm * 255).astype(np.uint8)
    out_path = "../app/public/data/density_localgroup.png"
    Image.fromarray(img_data, mode="L").save(out_path)
    print(f"Texture Groupe Local generee -> {out_path}")
    print(f"max brut: {field.max():.3f}, pixels satures (>0.99): {(norm>0.99).sum()}")
