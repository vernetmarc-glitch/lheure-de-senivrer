"""
Génère UN champ de densité (démo Phase 4) et l'exporte en PNG niveaux de gris
(valeurs normalisées 0-255) — la coloration (style Sobre/Contrasté/Astro) est
appliquée côté client en temps réel, pas ici, pour permettre de changer de
style instantanément sans regénérer d'image.

Sortie : app/public/data/density_demo.png
"""

import numpy as np
from PIL import Image

OMEGA_M = 0.315
H = 0.674
NS = 0.965
GAMMA = OMEGA_M * H

N = 512
BOX_MPC = 300.0
SEED = 42


def bbks_transfer(k_h_mpc):
    q = np.maximum(k_h_mpc, 1e-8) / GAMMA
    return (np.log(1 + 2.34 * q) / (2.34 * q)) * (
        1 + 3.89 * q + (16.1 * q) ** 2 + (5.46 * q) ** 3 + (6.71 * q) ** 4
    ) ** -0.25


def power_spectrum(k_h_mpc):
    T = bbks_transfer(k_h_mpc)
    P = (k_h_mpc ** NS) * T ** 2
    P[k_h_mpc == 0] = 0
    return P


def generate_density_field(n=N, box_mpc=BOX_MPC, seed=SEED, sigma_target=1.0):
    rng = np.random.default_rng(seed)
    d = box_mpc / n
    kx = np.fft.fftfreq(n, d=d) * 2 * np.pi
    ky = np.fft.rfftfreq(n, d=d) * 2 * np.pi
    kx_grid, ky_grid = np.meshgrid(kx, ky, indexing="ij")
    k_mag = np.sqrt(kx_grid ** 2 + ky_grid ** 2)

    P = power_spectrum(k_mag)
    noise_real = rng.normal(size=k_mag.shape)
    noise_imag = rng.normal(size=k_mag.shape)
    delta_k = (noise_real + 1j * noise_imag) * np.sqrt(P / 2.0) * n

    field = np.fft.irfft2(delta_k, s=(n, n))
    field = field / field.std() * sigma_target
    density = np.exp(field - field.var() / 2.0)
    return density


if __name__ == "__main__":
    density = generate_density_field()
    log_density = np.log10(density + 0.05)
    vmin, vmax = np.percentile(log_density, [1, 99.8])
    norm = np.clip((log_density - vmin) / (vmax - vmin), 0, 1)

    img_data = (norm * 255).astype(np.uint8)
    img = Image.fromarray(img_data, mode="L")
    out_path = "../app/public/data/density_demo.png"
    img.save(out_path)
    print(f"Champ de densité exporte -> {out_path} ({img.size})")
