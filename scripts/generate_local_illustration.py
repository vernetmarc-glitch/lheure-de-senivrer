"""
Illustration procédurale de la Voie lactée (layer 1, "local") — pas une photo
réelle (pas d'accès internet dans cet environnement), mais une représentation
stylisée à base de fonctions spirale logarithmique, pour donner un rendu
réaliste d'une galaxie spirale vue de face.

Sortie : app/public/data/local_milkyway.png
"""

import numpy as np
from PIL import Image, ImageFilter

N = 1024
rng = np.random.default_rng(7)

y, x = np.mgrid[0:N, 0:N]
cx, cy = N / 2, N / 2
dx, dy = x - cx, y - cy
r = np.sqrt(dx ** 2 + dy ** 2) / (N / 2)  # rayon normalisé 0-1
theta = np.arctan2(dy, dx)

# --- Bras spiraux (spirale logarithmique, 2 bras) ---
n_arms = 2
pitch = 4.2  # facteur d'enroulement
arm_pattern = np.cos(n_arms * theta - pitch * np.log(r + 0.05)) 
arm_intensity = np.clip(arm_pattern, 0, 1) ** 1.5

# --- Profil radial (bulbe brillant + disque qui décroît) ---
bulge = np.exp(-r * 9) * 1.4
disk = np.exp(-r * 2.2)
radial_profile = bulge + disk * 0.8

density = radial_profile * (0.35 + 0.65 * arm_intensity)
density = np.clip(density, 0, None)

# Halo diffus autour du disque
halo = np.exp(-r * 1.1) * 0.15
density += halo

# --- Bruit fin (granularité stellaire) ---
stellar_noise = rng.normal(0, 1, size=(N, N))
noise_range = np.ptp(stellar_noise)
stellar_noise = np.array(Image.fromarray(((stellar_noise - stellar_noise.min()) / noise_range * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)))
density += (stellar_noise / 255.0 - 0.5) * 0.06 * (density > 0.05)

density = np.clip(density, 0, None)
density = density / density.max()

# --- Coloration : bulbe jaune-blanc chaud, bras bleutés, halo violet sombre ---
r_ch = np.clip(density ** 0.55 * 1.05 + bulge * 0.5, 0, 1)
g_ch = np.clip(density ** 0.65 * 0.95 + bulge * 0.35, 0, 1)
b_ch = np.clip(density ** 0.8 * 0.9 + arm_intensity * 0.25 + bulge * 0.15, 0, 1)

rgb = np.stack([r_ch, g_ch, b_ch], axis=-1)

# Fond spatial : noir avec quelques étoiles éparses
star_field = (rng.random((N, N)) > 0.9985).astype(float)
star_field = np.array(Image.fromarray((star_field * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))) / 255.0
for c in range(3):
    rgb[:, :, c] = np.clip(rgb[:, :, c] + star_field * 0.8 * (1 - density[:, :, None].squeeze() * 0.5), 0, 1)

img = (rgb * 255).astype(np.uint8)
out = Image.fromarray(img, mode="RGB")
out = out.filter(ImageFilter.GaussianBlur(0.8))  # léger flou pour un rendu moins "graphique"
out.save("../app/public/data/local_milkyway.png")
print("Illustration generee -> ../app/public/data/local_milkyway.png", out.size)
