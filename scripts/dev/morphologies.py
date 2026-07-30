"""Morphologies parametriques pour les 98 galaxies (option C, test 7).

Objectif fixe par Marc : le realisme n'est PAS le but (a cette echelle on ne les
voit quasiment pas). Ce qui compte, c'est que la DISSOLUTION soit filamenteuse
comme dans les sprites cuits, et non une tache blanche qui grossit.

Parametre determinant : v_rot / sigma.
  - eleve  -> le systeme se delie en COURANTS de maree (filaments)
  - faible -> il gonfle isotropiquement (tache)

Chaque type fixe donc : profil de densite, aplatissement, v_rot/sigma.
"""
import numpy as np

# (nom, v_rot/sigma, aplatissement c/a, fraction de bulbe, grumeaux, exposant d'echelle)
TYPES = {
    "spirale_barree":   dict(vrs=6.0, ca=0.12, bulge=0.18, clumps=4, n_exp=1.0),
    "spirale":          dict(vrs=5.0, ca=0.14, bulge=0.14, clumps=3, n_exp=1.0),
    "lenticulaire":     dict(vrs=3.5, ca=0.25, bulge=0.35, clumps=0, n_exp=1.0),
    "elliptique":       dict(vrs=1.2, ca=0.70, bulge=1.00, clumps=0, n_exp=0.8),
    "irreguliere":      dict(vrs=2.5, ca=0.30, bulge=0.05, clumps=6, n_exp=0.9),
    "naine_irreguliere": dict(vrs=2.0, ca=0.35, bulge=0.05, clumps=4, n_exp=0.7),
    "naine_spheroidale": dict(vrs=1.4, ca=0.75, bulge=1.00, clumps=0, n_exp=0.6),
}


def assign_type(radius_mpc, brightness, rng):
    """Type a partir du catalogue : grandes et brillantes -> spirales,
    petites et faibles -> naines. Un peu d'alea pour la variete."""
    r = radius_mpc
    if r > 0.020:
        pool = ["spirale_barree", "spirale", "spirale", "lenticulaire", "elliptique"]
    elif r > 0.008:
        pool = ["spirale", "lenticulaire", "irreguliere", "irreguliere", "elliptique"]
    elif r > 0.003:
        pool = ["irreguliere", "naine_irreguliere", "naine_irreguliere", "naine_spheroidale"]
    else:
        pool = ["naine_spheroidale", "naine_spheroidale", "naine_irreguliere"]
    return pool[int(rng.integers(len(pool)))]


def make_galaxy(kind, n, radius, rng):
    """Positions + vitesses d'un modele parametrique. Unites : Mpc, et vitesse
    en unites ou G*M_tot/radius = 1 (l'echelle absolue est sans importance ici,
    seul le rapport v_rot/sigma pilote le caractere de la dissolution)."""
    p = TYPES[kind]
    n_b = int(n * p["bulge"])
    n_d = n - n_b

    # --- bulbe / spheroide : profil r^-1 tronque, aplati par ca
    def spheroid(m, ca):
        u = rng.random(m)
        r = radius * u ** 0.9
        ct = 2 * rng.random(m) - 1
        st = np.sqrt(np.maximum(1 - ct ** 2, 0))
        ph = 2 * np.pi * rng.random(m)
        x = np.stack([r * st * np.cos(ph), r * st * np.sin(ph), r * ct * ca], 1)
        return x

    # --- disque : exponentiel, mince
    def disk(m, ca, clumps):
        rr = radius * np.sqrt(rng.random(m)) ** p["n_exp"]
        ph = 2 * np.pi * rng.random(m)
        if clumps:  # bras/grumeaux : modulation azimutale
            ph = ph + 0.9 * np.sin(clumps * ph + rr / radius * 6.0)
        z = rng.normal(0, radius * ca * 0.35, m)
        return np.stack([rr * np.cos(ph), rr * np.sin(ph), z], 1)

    xb = spheroid(n_b, p["ca"]) if n_b else np.zeros((0, 3))
    xd = disk(n_d, p["ca"], p["clumps"]) if n_d else np.zeros((0, 3))
    x = np.vstack([xb, xd]).astype(np.float32)

    R = np.sqrt(x[:, 0] ** 2 + x[:, 1] ** 2) + 1e-9
    v_circ = np.sqrt(np.maximum(R / radius, 1e-6))          # courbe de rotation montante
    sigma = 1.0 / max(p["vrs"], 1e-6)
    # rotation dans le plan xy + dispersion isotrope
    v = np.stack([-x[:, 1] / R * v_circ, x[:, 0] / R * v_circ, np.zeros(len(x))], 1)
    v += rng.normal(0, sigma, v.shape)
    return x, v.astype(np.float32)


def dissolve(x, v, steps=240, g0=1.0, soft=0.02, radius=1.0):
    """Dissolution : N-corps direct, gravite decroissante (le halo n'est pas
    encore effondre quand on remonte le temps). Retourne les instantanes.

    Une rotation initiale produit des COURANTS ; sans rotation, une bouffee
    isotrope. C'est exactement le critere demande.
    """
    x = x.copy().astype(np.float64)
    v = v.copy().astype(np.float64)
    m = 1.0 / len(x)
    snaps = []
    dt = 3.0 / steps
    for s in range(steps):
        frac = 1.0 - s / steps
        g = g0 * frac ** 2                       # la gravite s'eteint
        d = x[:, None, :] - x[None, :, :]
        r2 = (d ** 2).sum(-1) + (soft * radius) ** 2
        a = -g * m * (d / r2[..., None] ** 1.5).sum(1)
        v += a * dt
        x += v * dt
        if s % (steps // 6) == 0 or s == steps - 1:
            snaps.append(x.copy())
    return snaps


def filamentarity(x):
    """Rapport des axes principaux : ~1 = tache ronde, >>1 = courants."""
    c = np.cov((x - x.mean(0)).T)
    ev = np.sort(np.linalg.eigvalsh(c))[::-1]
    return float(np.sqrt(ev[0] / max(ev[2], 1e-12))), float(np.sqrt(ev[0] / max(ev[1], 1e-12)))
