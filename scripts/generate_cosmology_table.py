"""
Génère la table cosmologique précalculée utilisée par le moteur frontend.

Calcule, pour une grille de facteurs d'échelle a allant de peu après la
recombinaison jusqu'à aujourd'hui (avec quelques points dans le futur en
réserve pour les phases ultérieures du projet) :
  - l'âge de l'univers t(a) en milliards d'années (Ga)
  - le rayon comobile de l'horizon des particules  chi_particle(a)  [Mpc]
  - le rayon comobile de la sphère de Hubble        R_hubble(a)     [Mpc]
  - le rayon comobile de l'horizon des événements   chi_event(a)    [Mpc]

Paramètres cosmologiques : Planck 2018, base-LambdaCDM.

Sortie : app/public/data/cosmology_table.json
"""

import json
import numpy as np
from scipy.integrate import quad

# --- Paramètres cosmologiques (Planck 2018) ---
H0 = 67.4          # km/s/Mpc
OMEGA_M = 0.315
OMEGA_L = 0.685
OMEGA_R = 9.24e-5

C_KM_S = 299792.458          # vitesse de la lumière, km/s
MPC_KM = 3.0857e19           # km par Mpc
GYR_S = 3.1557e16            # secondes par Ga
GLY_PER_MPC = 3.26156e6 / 1e9  # années-lumière par Mpc, converti en Ga-lumière

C_MPC_PER_GYR = C_KM_S * GYR_S / MPC_KM


def H(a: float) -> float:
    """Paramètre de Hubble H(a) en km/s/Mpc."""
    return H0 * np.sqrt(OMEGA_R * a**-4 + OMEGA_M * a**-3 + OMEGA_L)


def H_per_gyr(a: float) -> float:
    """H(a) converti en 1/Ga, pour les intégrations temporelles."""
    return (H(a) / MPC_KM) * GYR_S


def t_of_a(a: float) -> float:
    """Âge de l'univers (Ga) au facteur d'échelle a."""
    integrand = lambda x: 1.0 / (x * H_per_gyr(x))
    val, _ = quad(integrand, 1e-10, a, limit=200)
    return val


def chi_particle(a: float) -> float:
    """Rayon comobile de l'horizon des particules (Mpc) au facteur a."""
    integrand = lambda x: C_MPC_PER_GYR / (x**2 * H_per_gyr(x))
    val, _ = quad(integrand, 1e-10, a, limit=200)
    return val


def chi_event(a: float, a_inf: float = 1000.0) -> float:
    """Rayon comobile de l'horizon des événements (Mpc) au facteur a."""
    integrand = lambda x: C_MPC_PER_GYR / (x**2 * H_per_gyr(x))
    val, _ = quad(integrand, a, a_inf, limit=400)
    return val


def r_hubble_comoving(a: float) -> float:
    """Rayon comobile de la sphère de Hubble (Mpc) au facteur a."""
    return C_KM_S / (a * H(a))


def build_table(n_points: int = 400):
    # Grille en log(a) pour bien résoudre les débuts (a très petit)
    a_start = 1 / 1101.0   # juste après la recombinaison (z ~ 1100)
    a_end = 5.0            # extension future, pour les phases ultérieures (sphères)
    a_values = np.geomspace(a_start, a_end, n_points)

    rows = []
    for a in a_values:
        rows.append({
            "a": float(a),
            "z": float(1 / a - 1),
            "t_Gyr": float(t_of_a(a)),
            "chi_particle_Mpc": float(chi_particle(a)),
            "r_hubble_comoving_Mpc": float(r_hubble_comoving(a)),
            "chi_event_Mpc": float(chi_event(a)),
        })

    return {
        "meta": {
            "H0_km_s_Mpc": H0,
            "omega_m": OMEGA_M,
            "omega_lambda": OMEGA_L,
            "omega_r": OMEGA_R,
            "gly_per_mpc": GLY_PER_MPC,
            "note": "a=1 correspond a aujourd'hui. Rayons en Mpc comobiles.",
        },
        "rows": rows,
    }


if __name__ == "__main__":
    table = build_table()
    out_path = "../app/public/data/cosmology_table.json"
    with open(out_path, "w") as f:
        json.dump(table, f, indent=2)
    print(f"Table generee : {len(table['rows'])} points -> {out_path}")
    print("Aujourd'hui (a=1) le plus proche :",
          min(table["rows"], key=lambda r: abs(r["a"] - 1.0)))
