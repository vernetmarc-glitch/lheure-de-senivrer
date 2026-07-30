"""Options de profil radial pour les nuages de halos (question 1 du test 7).

Conflit mesure : q=0.6 reproduit la reference Millennium a l'echelle des amas
(r90/r50 = 1.42), q=1.0 reproduit le sprite d'Andromede a l'echelle galactique
(r90/r50 = 1.86, sprite 1.86). Une loi de puissance unique ne peut pas les deux.
"""
import numpy as np


def sample_power(n, rng, q):
    """r = u^q  (loi de puissance simple, parametre unique)."""
    return rng.random(n) ** q


def sample_nfw(n, rng, c=8.0):
    """Profil NFW : pente interne -1, externe -3, un parametre de concentration.

    M(<x) ∝ ln(1+x) − x/(1+x)  avec x = r/r_s, tronque a x = c.
    Inversion numerique de la CDF.
    """
    x = np.linspace(1e-4, c, 4000)
    m = np.log1p(x) - x / (1 + x)
    m = m / m[-1]
    return np.interp(rng.random(n), m, x) / c


def sample_einasto(n, rng, alpha=0.17, xmax=3.0):
    """Profil d'Einasto : pente logarithmique variable, un parametre alpha."""
    x = np.linspace(1e-4, xmax, 4000)
    rho = np.exp(-2.0 / alpha * ((x ** alpha) - 1.0))
    m = np.cumsum(rho * x ** 2)
    m /= m[-1]
    return np.interp(rng.random(n), m, x) / xmax


def profile_stats(r):
    r50 = float(np.median(r))
    r90 = float(np.percentile(r, 90))
    return r50, r90, r90 / max(r50, 1e-9)


def cloud(centre, n, rng, kind, scale, **kw):
    if kind == "power":
        u = sample_power(n, rng, kw.get("q", 0.6))
    elif kind == "nfw":
        u = sample_nfw(n, rng, kw.get("c", 8.0))
    elif kind == "einasto":
        u = sample_einasto(n, rng, kw.get("alpha", 0.17))
    else:
        raise ValueError(kind)
    r = scale * u
    ct = 2 * rng.random(n) - 1
    st = np.sqrt(np.maximum(1 - ct ** 2, 0))
    ph = 2 * np.pi * rng.random(n)
    d = np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)
    return centre + (r[:, None] * d).astype(np.float32)
