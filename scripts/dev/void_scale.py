"""TAILLE DES VIDES -- metrique d'echelle des structures (B8).

Pourquoi pas le pic du spectre
------------------------------
Premiere formulation d'INV-H8, le 31/07 : le pic du spectre de puissance par
octave devait tomber sur la taille reelle de la structure. Elle est fausse.

A la ligne J, le champ visible fait 287 Mpc de large ; un vide de 140 Mpc y tient
deux fois. Exiger que 140 Mpc soit le PIC reviendrait a exiger qu'un seul vide
remplisse le cadre -- une tache, pas un reseau. Ce que montre reellement une
coupe a cette echelle, c'est une texture de filaments a 20 Mpc ORGANISEE en vides
de 140 Mpc. Deux echelles a la fois. Le pic mesure la texture ; il ne voit pas
l'organisation.

Ce que mesure ce module
-----------------------
Le diametre du plus grand disque inscriptible dans une region sombre -- la
definition usuelle du rayon d'un vide, et celle que l'oeil juge.

  1. seuil par PERCENTILE, donc sans unite et insensible au contraste global ;
  2. transformee de distance euclidienne sur le masque sombre ;
  3. maxima locaux = rayons inscrits des vides ;
  4. mediane des plus grands = taille caracteristique.

Le resultat est rendu en FRACTION DE LA LARGEUR DU CADRE, ce qui permet de le
comparer a l'image de reference sans connaitre son echelle physique, puis
converti en Mpc par ligne.
"""
import numpy as np
from scipy import ndimage

DARK_PCT = 45.0      # les 45 % de pixels les plus sombres forment les vides
N_KEEP = 24          # nombre de vides retenus pour la mediane
MIN_R_PX = 1.5       # en deca, c'est de la grenaille, pas un vide


def void_scale(img, dark_pct=DARK_PCT, n_keep=N_KEEP):
    """Diametre caracteristique des vides.

    Retourne (diametre_px, fraction_du_cadre, nombre_de_vides_retenus).
    """
    a = np.asarray(img, dtype=np.float64)
    n = a.shape[0]
    mask = a <= np.percentile(a, dark_pct)
    # distance au bord clair le plus proche, en pixels
    dist = ndimage.distance_transform_edt(mask)
    # un maximum local de la distance = centre d'un vide, sa valeur = rayon inscrit
    mx = ndimage.maximum_filter(dist, size=5)
    peaks = (dist == mx) & (dist >= MIN_R_PX)
    r = dist[peaks]
    if r.size == 0:
        return 0.0, 0.0, 0
    r = np.sort(r)[::-1][:n_keep]
    d_px = 2.0 * float(np.median(r))
    return d_px, d_px / n, int(r.size)


def void_scale_mpc(img, halfwidth_mpc, **kw):
    """Diametre caracteristique des vides, en Mpc comobiles."""
    d_px, frac, k = void_scale(img, **kw)
    return frac * 2.0 * halfwidth_mpc, frac, k


def describe(img, halfwidth_mpc=None):
    d_px, frac, k = void_scale(img)
    s = f"vides : {d_px:.1f} px, {100*frac:.1f} % du cadre, {k} retenus"
    if halfwidth_mpc:
        s += f", {frac * 2 * halfwidth_mpc:.1f} Mpc"
    return s
