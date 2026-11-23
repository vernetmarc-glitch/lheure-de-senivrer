"""Scénario de collision imposé à FastScape — Alpes du Nord autour de Grenoble.

Simplification assumée (hypothèse signalée sur la page), d'après la synthèse classique
de l'histoire alpine (p. ex. Schmid et al. 2004, Eclogae 97 ; Handy et al. 2010,
Earth-Sci. Rev. 102 ; Fügenschuh & Schmid 2003 ; Bellahsen et al. 2014, Tectonics 33 ;
van der Beek et al. 2010, Basin Research 22 ; Nouibat et al. 2022 pour la structure) :

- avant 35 Ma : la Téthys alpine se referme ; ici, la marge européenne est une plaine
  basse ; à l'est, le prisme qui deviendra les zones internes commence à émerger ;
- 35–28 Ma : collision continentale ; les zones internes (à l'est du front pennique)
  montent ; raccourcissement vers l'ouest-nord-ouest ;
- 24–14 Ma : flexure de l'avant-pays, mer molassique peu profonde (Burdigalien) ;
- à partir de 22 Ma, et surtout après 12 Ma : soulèvement des massifs cristallins
  externes (Belledonne, Grandes Rousses, Écrins, Mont-Blanc) ;
- 14–4 Ma : plissement des chaînes subalpines (Chartreuse, Vercors, Bauges) et du Jura ;
- depuis 4 Ma : la convergence s'arrête presque (GPS actuel < 1 mm/an) ; le relief
  continue de se soulever (rebond) et de s'éroder ; glaciations depuis 2,6 Ma.

Les grandeurs sont physiques : km, Ma, mm/an. Aucune n'est normalisée par une
statistique de l'image.
"""
import numpy as np

LAT0, LON0 = 45.188, 5.724
KM_LON = 111.32 * np.cos(np.radians(LAT0))
KM_LAT = 111.13


def xy(lat, lon):
    """(lat, lon) -> (x est, y nord) en km depuis Grenoble."""
    return (np.asarray(lon) - LON0) * KM_LON, (np.asarray(lat) - LAT0) * KM_LAT


# Front pennique (limite zones internes / externes), lat-lon approchées
FRONT_PENNIQUE = [(44.20, 6.50), (44.60, 6.47), (44.90, 6.56), (45.10, 6.46),
                  (45.30, 6.45), (45.50, 6.55), (45.70, 6.76), (45.85, 6.97), (46.20, 7.20)]
# Front des chaînes subalpines et du Jura méridional
FRONT_SUBALPIN = [(44.20, 4.95), (44.60, 5.15), (44.90, 5.30), (45.10, 5.42),
                  (45.30, 5.62), (45.50, 5.72), (45.75, 5.55), (46.20, 5.40)]
# Massifs cristallins externes : segments (lat, lon) -> (lat, lon) et demi-largeur (km)
MCE = [((45.02, 5.80), (45.58, 6.32), 9.0),     # Belledonne (avec le Taillefer)
       ((45.08, 6.10), (45.20, 6.15), 7.0),     # Grandes Rousses
       ((44.80, 6.15), (45.00, 6.45), 18.0),    # Écrins – Pelvoux
       ((45.75, 6.72), (45.98, 7.05), 8.0),     # Mont-Blanc
       ((45.93, 6.78), (46.05, 6.92), 5.0)]     # Aiguilles Rouges


def _front_x(poly, Y):
    ys, xs = zip(*[xy(la, lo)[::-1] for la, lo in poly])
    return np.interp(Y, ys, xs)


def _sig(z):
    return 1.0 / (1.0 + np.exp(-z))


def _segment(X, Y, a, b, r):
    (xa, ya), (xb, yb) = xy(*a), xy(*b)
    dx, dy = xb - xa, yb - ya
    s = np.clip(((X - xa) * dx + (Y - ya) * dy) / (dx * dx + dy * dy), 0, 1)
    d = np.hypot(X - xa - s * dx, Y - ya - s * dy)
    return np.exp(-(d / r) ** 4)


def domaines(X, Y):
    """Fractions (somme = 1) : avant-pays, subalpin, cristallin externe, interne."""
    interne = _sig((X - _front_x(FRONT_PENNIQUE, Y)) / 3.0)
    mce = np.zeros_like(X)
    for a, b, r in MCE:
        mce = np.maximum(mce, _segment(X, Y, a, b, r))
    mce *= 1 - interne
    externe = _sig((X - _front_x(FRONT_SUBALPIN, Y)) / 3.0)
    sub = externe * (1 - interne) * (1 - mce)
    avant = 1 - interne - mce - sub
    return {"avant": avant, "subalpin": sub, "mce": mce, "interne": interne}


def _rampe(t, t0, t1, v0=0.0, v1=1.0):
    s = np.clip((t - t0) / (t1 - t0), 0, 1)
    return v0 + (v1 - v0) * s * s * (3 - 2 * s)


def progression(t):
    """Part du soulèvement « actuel » atteinte par chaque domaine à l'instant t (Ma, < 0)."""
    return {
        "interne": _rampe(t, -45, -28, 0.15, 1.0),
        "mce": _rampe(t, -22, -12, 0.0, 0.45) + _rampe(t, -12, -4, 0.0, 0.55),
        "subalpin": _rampe(t, -14, -4),
        "avant": _rampe(t, -6, -2),
    }


# Surface du bassin d'avant-pays (m) : mer priabonienne, plaine oligocène, mer molassique
# (Burdigalien), puis remplissage continental de la molasse. Hypothèse simplifiée :
# FastScape ne calcule ici que l'érosion ; le dépôt du bassin est imposé.
NIVEAU_BASSIN = [(-45, 20), (-38, 20), (-36, -40), (-31, -40), (-29, 80), (-24, 80),
                 (-22, -60), (-17, -60), (-14, 150), (-6, 380), (0, 380)]


def niveau_bassin(t):
    a, b = zip(*NIVEAU_BASSIN)
    return float(np.interp(t, a, b))


def poids_bassin(t, dom, prog):
    """Où la surface suit le bassin : avant-pays et subalpin pas encore plissé ;
    s'efface entre 7 et 5 Ma (début de l'incision plio-quaternaire)."""
    return (dom["avant"] + dom["subalpin"] * (1 - prog["subalpin"])) * (1 - _rampe(t, -7, -5))


def raccourcissement_mm_an(t):
    """Vitesse vers l'ouest-nord-ouest des zones internes par rapport à l'avant-pays."""
    if t < -35:
        return 0.6
    if t < -20:
        return 1.5
    if t < -5:
        return 1.0
    return float(1.0 * (1 - _rampe(t, -5, -3)))


DIRECTION = np.array([-np.cos(np.radians(22.5)), np.sin(np.radians(22.5))])   # vers l'ONO


def champ_raccourcissement(X, Y):
    """Fraction de la vitesse : nulle sur le front subalpin, 1 au front pennique."""
    xs = _front_x(FRONT_SUBALPIN, Y)
    xp = _front_x(FRONT_PENNIQUE, Y)
    return np.clip((X - xs) / np.maximum(xp - xs, 10.0), 0, 1)


TEXTES = None  # les textes sont dans la page
