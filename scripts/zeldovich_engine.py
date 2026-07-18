"""Moteur de densité v3.2 — advection de Zel'dovich (matrice, bloc `zeldovich`).

SOURCE UNIQUE partagée par :
  - generate_layers.py            (textures de production density_l*.png, a=1)
  - generate_spacetime_frames.py  (frames temporelles st_*, format identique)

Tous les paramètres sont lus dans spacetime_matrix.json (variante Z2 validée
par Marc le 16/07). Déterministe : mêmes graines -> mêmes sorties, partout.
"""
import json
import math
import os
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX_PATH = os.path.join(_HERE, "..", "app", "public", "data", "spacetime_matrix.json")

with open(MATRIX_PATH) as _f:
    _MATRIX = json.load(_f)
Z = _MATRIX["zeldovich"]

_CACHE = {}


def _kgrids(n):
    if n not in _CACHE:
        ky = np.fft.fftfreq(n)[:, None]
        kx = np.fft.rfftfreq(n)[None, :]
        k2 = ky ** 2 + kx ** 2
        _CACHE[n] = (ky, kx, k2, np.sqrt(k2))
    return _CACHE[n]


def displacement(delta, world_mpc):
    """Ψ̂ = i·k·δ̂/k², bande λ ∈ [lam_min_px, filament_max_scale_mpc comobiles],
    normalisé à déplacement rms = 1 px (l'amplitude est portée par S)."""
    n = delta.shape[0]
    ky, kx, k2, k = _kgrids(n)
    D = np.fft.rfft2(delta)
    k_cut = world_mpc / (Z["filament_max_scale_mpc"] * n)
    mask = (k >= k_cut) & (k <= 1.0 / max(Z["lam_min_px"], 2.0)) & (k2 > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        base = np.where(mask, D / k2, 0)
    px = np.fft.irfft2(1j * kx * base / (2 * np.pi), s=delta.shape)
    py = np.fft.irfft2(1j * ky * base / (2 * np.pi), s=delta.shape)
    rms = math.sqrt(px.var() + py.var())
    if rms < 1e-12:
        return np.zeros_like(delta), np.zeros_like(delta)
    return px / rms, py / rms


def _bilinear(f, y, x):
    n = f.shape[0]
    y0 = np.floor(y).astype(int) % n
    x0 = np.floor(x).astype(int) % n
    y1, x1 = (y0 + 1) % n, (x0 + 1) % n
    fy, fx = y - np.floor(y), x - np.floor(x)
    return (f[y0, x0] * (1 - fy) * (1 - fx) + f[y1, x0] * fy * (1 - fx)
            + f[y0, x1] * (1 - fy) * fx + f[y1, x1] * fy * fx)


def _blur(f, sigma_px):
    if sigma_px <= 0:
        return f
    n = f.shape[0]
    _, _, k2, _ = _kgrids(n)
    G = np.exp(-2 * (math.pi * sigma_px) ** 2 * k2)
    return np.fft.irfft2(np.fft.rfft2(f) * G, s=f.shape)


def density_from_psi(psi, s_px, out_n):
    """Dépôt CIC d'une grille de masse advectée. S=0 -> exactement uniforme."""
    if s_px <= 1e-3:
        return np.ones((out_n, out_n))
    px, py = psi
    ng = Z["mass_grid"]
    step = out_n / ng
    qy, qx = np.mgrid[0:ng, 0:ng] * step
    qy, qx = qy.ravel(), qx.ravel()
    y = qy + s_px * _bilinear(py, qy, qx)
    x = qx + s_px * _bilinear(px, qy, qx)
    rho = np.zeros((out_n, out_n))
    y0 = np.floor(y).astype(int)
    x0 = np.floor(x).astype(int)
    fy, fx = y - y0, x - x0
    for dy, wy in ((0, 1 - fy), (1, fy)):
        for dx, wx in ((0, 1 - fx), (1, fx)):
            np.add.at(rho, ((y0 + dy) % out_n, (x0 + dx) % out_n), wy * wx)
    rho /= rho.mean()
    # le flou anti-crénelage peut créer de petits négatifs -> clip (ρ^shape)
    return np.clip(_blur(rho, Z["soft_px"]), 0, None)


def density_from_delta(delta, world_mpc, s_px):
    return density_from_psi(displacement(delta, world_mpc), s_px, delta.shape[0])


def calibrate_alpha(rhos):
    """α GLOBAL : ton moyen poolé sur les densités a=1 -> 38/255 (cf. matrice)."""
    shape = Z["exposure"]["shape"]
    vg = Z["exposure"]["void_gamma"]
    alphas = np.linspace(0.02, 2.5, 120)
    means = [np.mean([np.mean((1 - np.exp(-a * r ** shape)) ** vg) for r in rhos])
             for a in alphas]
    return float(alphas[int(np.argmin(np.abs(np.array(means) - 38 / 255)))])


def tone(rho, alpha):
    return (1 - np.exp(-alpha * rho ** Z["exposure"]["shape"])) ** Z["exposure"]["void_gamma"]


def dissolved_tone(alpha):
    return float((1 - math.exp(-alpha)) ** Z["exposure"]["void_gamma"])


def store_computed(alpha):
    """Écrit α et le ton dissous dans matrix.computed.zeldovich (source de
    vérité pour les frames temporelles et les prototypes)."""
    with open(MATRIX_PATH) as f:
        m = json.load(f)
    m.setdefault("computed", {})["zeldovich"] = {
        "alpha": round(alpha, 6),
        "dissolved_tone": round(dissolved_tone(alpha), 6),
        "dissolved_tone_255": round(dissolved_tone(alpha) * 255, 2),
        "provenance": "calibré par generate_layers.py (pooling D..M à a=1)",
    }
    with open(MATRIX_PATH, "w") as f:
        json.dump(m, f, indent=1, ensure_ascii=False)
    return m["computed"]["zeldovich"]


def load_alpha():
    with open(MATRIX_PATH) as f:
        m = json.load(f)
    zc = m.get("computed", {}).get("zeldovich")
    if not zc:
        raise RuntimeError("α non calibré — lancer d'abord generate_layers.py")
    return zc["alpha"]


def export_tone_png(t, path):
    from PIL import Image
    Image.fromarray(np.clip(t * 255, 0, 255).astype(np.uint8), mode="L").save(path)
