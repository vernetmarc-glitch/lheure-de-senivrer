"""CHAINE EMBOITEE -- raccord spectral dans l'espace de Psi.

CE QUI ETAIT FAUX (gen_full.py, `field()`)
------------------------------------------
Le sous-volume du parent etait reechantillonne sur la dalle de l'enfant, PUIS
passe a `rfftn`. Or ce sous-volume n'est pas periodique dans la boite enfant :
il a une moyenne non nulle, un gradient lent, et une discontinuite de bord.
Toute cette puissance tombe dans les modes les plus BAS, que `Psi = i k d / k^2`
amplifie ensuite en 1/k.

Signature mesuree du defaut : std(delta) 6,28 -> 85,8 et rms(Psi) 10 -> 2253 Mpc.

LE PRINCIPE DE LA CORRECTION
----------------------------
Chaque boite ne subit de FFT que la ou elle EST periodique.

  1. sur la boite PARENT   : delta_lo = passe-bas(delta_parent, k_cut)
                             Psi_lo   = Psi(delta_parent) restreint a k <= k_cut
  2. INTERPOLATION de delta_lo et Psi_lo aux coordonnees de l'enfant.
     Operateur purement lineaire, aucune FFT en aval -- c'est tout le point.
  3. sur la boite ENFANT   : delta_hi = passe-haut(delta_frais, k_cut)
                             Psi_hi   = Psi(delta_hi) sur (k_cut, k_max]
  4. delta = delta_lo + delta_hi        Psi = Psi_lo + Psi_hi

La coupure est FRANCHE : chaque mode est porte par une boite et une seule, donc
la puissance totale est conservee exactement, sans double comptage.

`k_cut = pi / (2 * cellule_parent)`, soit la MOITIE de la Nyquist du parent. Le
champ passe-bas varie alors sur ~4 cellules parent : l'interpolation trilineaire
y est precise. Prendre la Nyquist entiere ferait de l'interpolation la nouvelle
source d'erreur.

Les modes plus grands que la boite enfant ne disparaissent pas : ils arrivent par
l'interpolation sous forme de gradient lent (translation d'ensemble + champ de
maree). C'est physiquement ce qu'il faut, et c'est impossible a obtenir en
re-FFT-ant l'enfant.
"""
import json
import os

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

import mcpm_web as M
import norm_abs as NA
import slab_test as ST

# ---------------------------------------------------------------------------
# LES PARAMETRES CI-DESSOUS SONT LUS DEPUIS LA SOURCE DE VERITE.
#
# `app/public/data/spacetime_matrix.json`, bloc `generation`, est la reference :
# editer ici ne sert a rien, le chargement ci-dessous ecrase les valeurs. Les
# constantes restent ecrites en clair pour que le module soit lisible seul et
# qu'un defaut de chargement ne passe pas inapercu -- elles doivent rester
# identiques au JSON, ce que INV-G2 verifie.
# ---------------------------------------------------------------------------
OUT_N = 320
TARGET_MEAN = 68.0
SLAB_MAX_MPC = 300.0
# Plafond PHYSIQUE de l'epaisseur de tranche, ajoute le 07/08/2026.
#
# `SLAB_FRAC` est une FRACTION DE BOITE -- exactement le piege documente
# (« rayons et masses en valeurs physiques absolues, jamais en fraction de la
# boite »), sixieme occurrence. A la ligne O elle empilait 1 748 Mpc de
# profondeur, soit une demi-douzaine de structures independantes moyennees les
# unes sur les autres : le contraste de la toile y tombait a 0,0013.
#
# Une tranche plus epaisse que l'echelle d'homogeneite ne peut RIEN ajouter --
# au-dela, les structures sont decorrelees et leur superposition ne fait que
# diluer. Mesure du 07/08 a la ligne O : plafonner a 300 Mpc porte la structure
# de 0,0013 a 0,0075, soit x5,8.
SLAB_FRAC = 0.06
# Essai du 31/07, REVENU EN ARRIERE. Porter la dalle de 0,06 a 0,15 fait passer
# le pic du spectre de 20,5 a 47,8 Mpc a la ligne J, puis il SATURE : a 0,30,
# 0,60 et 1,00 il revient a 20,5. La dalle n'est donc pas le levier de B8.
# Le cout etait de surcroit prohibitif : l'epaisseur fixe nz, donc le volume de
# grille -- nz passait de 19 a 48 a la ligne O, soit 2,5x sur toute la chaine.
# La puissance manquante entre 140 et 400 Mpc n'est pas coupee par la
# projection : elle n'est pas dans le champ.
PSF_PX = 0.45
JITTER = 0.5
# ---------------------------------------------------------------- champ fin
# Retabli le 02/08 apres constat de Marc : « je ne vois plus de structure
# filamentaire apparaitre a petite echelle ». Mesure a l'appui -- la puissance a
# 10 px valait 0,099 contre 0,834 sur l'image de reference.
#
# CAUSE. Le contenu frais de chaque ligne occupe la bande 6->2 px et subit un
# deplacement de 13,6 px, soit deux fois sa propre longueur d'onde : il est
# disperse avant d'etre visible. Elargir la bande ne suffit pas (teste, ecarte),
# le PM non plus a cette resolution (teste, pic invariant a 40 px).
#
# MECANISME. Un champ 2D frais, a bande LARGE et amplitude IMPOSEE, module la
# densite APRES le depot -- il n'est donc pas deplace, donc pas delave. C'est
# l'ingredient de la toute premiere iteration (commit e0d5336, 05/07), que la
# refonte des 30-31/07 avait supprime.
#
# La modulation est LOG-NORMALE : positive par construction, moyenne preservee,
# et c'est la forme physique d'un champ de densite cosmologique. La variante
# additive (1 + A*f) devenait negative, le clip a zero fabriquait une seconde
# population -- creux bimodal 0,54, INV-E3 en echec.
#
# Le fond diffus evite des vides absolument noirs (21,6 % -> 0 %) : les vides
# reels contiennent de la matiere diffuse, et l'image de reference n'a que 4,7 %
# de noir.
FINE_A = 1.7                # amplitude de la modulation log-normale
FINE_FLOOR = 0.12           # fond diffus, en fraction de la moyenne
FINE_GAMMA = 0.45           # compression du ton (sinon 4,3 % de blanc pur)
FINE_LAM_HI_PX = 40.0       # bande du champ fin : 40 px -> Nyquist
HOMOGENEITY_MPC = 300.0
# Borne PHYSIQUE de la plus grande structure representable (B8 : le passage a
# l'homogeneite se situe entre 100 et 300 Mpc). Ajoutee le 02/08 sur constat de
# Marc : « sur le layer O je vois encore beaucoup de structures de grande
# echelle ».
#
# Le champ fin etait defini en PIXELS : ses 40 px valaient 3 642 Mpc a la ligne
# O, soit douze fois l'echelle d'homogeneite. On fabriquait des structures qui
# n'existent pas.
#
# La bande est desormais bornee par la physique. Propriete utile : l'heritage
# suffit ensuite a propager la loi. La ligne O porte [300 Mpc, sa resolution] ;
# l'enfant herite de cette bande AGRANDIE de x2,520 et n'ajoute que sous sa
# propre limite -- il porte donc lui aussi [300 Mpc, sa resolution]. Chaque
# ligne montre exactement les echelles ou l'univers a des structures, et rien
# au-dela.
FINE_LAM_LO_PX = 2.2
FINE_NORM = 0.0             # calibre au premier appel pour var(champ complet)=1

# B4 borne l'auto-similarite a 0,1-150 Mpc, B8 declare L->O homogenes. Le champ
# fin est defini en PIXELS : a la ligne O, 40 px valent 3 642 Mpc, l'appliquer y
# fabriquerait des structures inexistantes. Son amplitude suit donc la fenetre
# de validite de B4.
# Revise le 02/08 sur arbitrage de Marc : « les layers L M N et O sont tres
# fades [...] on perd completement les points lumineux au noeud de la toile ».
# Mesure a l'appui : a la ligne O l'ecart-type valait 1,9/255, l'image allait de
# 58 a 78 -- il n'y avait aucun pic a preserver.
#
# TENSION ASSUMEE avec B8, qui declare L->O homogenes. Le champ fin est defini en
# pixels : a la ligne O, 40 px valent 3 642 Mpc, echelle a laquelle l'univers est
# reellement homogene. Ce grain n'est donc PAS de la structure cosmologique -- il
# rend lisible un fond de carte qui, sinon, ne montre rien. L'intention de
# l'oeuvre prime ici : les trois spheres sont le sujet, le fond les sert.
# L'amplitude reste decroissante vers le haut, ce qui preserve B3.
FINE_STRENGTH = {"A":1.0,"B":1.0,"C":1.0,"D":1.0,"E":1.0,"F":1.0,"G":1.0,
                 "H":1.0,"I":1.0,"J":1.0,"K":0.85,"L":0.34,
                 "M":0.24,"N":0.14,"O":0.08}

WEB_GAIN = {"A":1.0,"B":1.0,"C":1.0,"D":1.0,"E":1.0,"F":1.0,"G":1.0,
            "H":1.0,"I":1.0,"J":1.0,"K":1.0,"L":1.7,
            "M":2.2,"N":2.7,"O":3.0}
# GAIN PONCTUEL SUR LA TOILE, valide par Marc le 07/08/2026 sur planche visuelle.
#
# Le probleme qu'il resout, et pourquoi le champ fin baisse en meme temps
# ----------------------------------------------------------------------
# Aux lignes L a O, la dynamique visible venait presque entierement du CHAMP FIN,
# statistiquement INDEPENDANT de la toile : mesure a la ligne O, 405 pics dont
# 10 % seulement sur les 10 % les plus denses de la toile -- exactement le
# hasard. Diagnostic de Marc : « une toile fade, et des points tres lumineux
# poses aleatoirement par-dessus ». Ce n'est ni Millennium ni physique.
#
# La correction fait DEUX choses ensemble, et les deux sont necessaires :
#   - un gain ponctuel rend sa dynamique a la toile elle-meme, de sorte que les
#     points brillants SOIENT ses noeuds (B10) ;
#   - le champ fin redescend au rang de grain (C8) et cesse de la dominer.
# Baisser le champ fin seul rendrait les lignes fades -- ce que Marc avait deja
# refuse le 02/08. Monter le gain seul laisserait les faux points en place.
#
# La progression est GRADUEE de K a O, jamais brutale : une marche a la charniere
# K|L casserait l'heritage (B1, T-010). Le gain reste un operateur PONCTUEL,
# donc conforme a l'interdit sur les operateurs spatialement non lineaires.
#
# Mesure du 07/08 a la ligne O, toile seule : contraste 0,107 sans gain, 0,315
# avec gain x3 -- soit la dynamique de l'etat actuel, mais portee par la toile.

FRESH_PSI_GAIN = 1.0
# Troncature du deplacement frais (02/08). Mesure : le deplacement engendre par
# la bande fraiche vaut 24 % de sa longueur d'onde a la ligne K et 33 % a J,
# alors que le croisement de nappes commence vers 16 %. Cette bande ne
# s'effondre donc pas : elle BRASSE la matiere heritee au lieu de la structurer,
# ce qui decorrele l'enfant du parent aux petites echelles (F2 = 0,64 a 0,7 px
# de lissage contre 0,92 a 24 px).
# Le contenu fin n'est pas perdu pour autant : il est porte par le champ fin,
# qui n'est pas deplace.

RENDER_MARGIN = 1.5
FINE_N = 480                # = OUT_N * RENDER_MARGIN
# Le champ fin est calcule sur la BOITE COMPLETE, marge comprise, et non sur la
# seule fenetre visible. Motif (02/08) : la texture de production couvre
# +/- half*marge ; regenerer le champ fin a ce moment-la le privait de son
# heritage et cassait la coherence entre lignes -- defaut constate par Marc sur
# le portage. Un seul champ fin, herite une fois, sert les deux rendus.
# L'echelle Mpc/px est identique (2*half*marge/FINE_N = 2*half/OUT_N).

SUB_Z = 2                   # raffinement du reseau lagrangien selon z.
# Calibre le 30/07 : rho_auto du rendu ne depend QUE du nombre de particules par
# pixel, n/(n+6,8), quel que soit l'axe raffine -- verifie sur (1,1), (2,1),
# (1,2), (2,2). Raffiner en z coute donc x2 la ou raffiner en x,y coute x4 pour
# le meme gain. Contre-intuitif : on attendait des echantillons correles en z.
#   sub_z=1 -> 2,99 part/px dans la fenetre magnifiee (SOUS le plancher INV-C2)
#   sub_z=2 -> 5,98 part/px                            <- retenu

TARGET_PROJ = 1_600_000
HALO_FRAC = 0.25
PROFILE_Q = 0.6
R_HALO_MPC = 2.2
SUB_LEVELS, SUB_FRAC = 2, 0.30
K_CUT_SAFETY = 1.2          # k_cut = pi / (K_CUT_SAFETY * cellule_parent)
# Calibre le 30/07 par balayage, sur la paire M->L :
#   safety 2,0 -> rho 0,919, variance heritee  5,2 %
#   safety 1,2 -> rho 0,960, variance heritee 12,3 %   <- retenu
#   safety 1,0 -> rho 0,958, variance heritee 15,1 %
# A 1,0 (Nyquist du parent exactement) la fidelite redescend : l'interpolation
# devient la source d'erreur dominante. 1,2 est le maximum utile.

# Echelle du 30/07 : 15 lignes geometriques A->O, raison x2,520 (D-21).
# Seules les lignes generees (H->O) passent par cette chaine ; A->G sont a
# sprites. La chaine va du PLUS GRAND au plus petit (sens impose, §4.4).
CHAIN = [
    ("O", 14570.0000, 1.5, 23), ("N", 5781.9515, 1.5, 19),
    ("M", 2294.5067, 1.5, 17), ("L", 910.5509, 1.5, 13),
    ("K", 361.3426, 1.5, 11), ("J", 143.3950, 1.5, 7),
    ("I", 56.9048, 1.5, 5), ("H", 22.5821, 1.5, 3),
]


# ------------------------------------------------------------------ ancrage
# D6 (31/07) : « les galaxies reelles sont des centres de gravite ». Les
# filaments doivent CONVERGER vers les positions du catalogue, pas s'illuminer a
# leur endroit.
#
# Le mecanisme de la §4.7 ajoutait un halo doux + un pic au champ de DENSITE : il
# peignait des taches brillantes aux bonnes coordonnees. Une tache posee sur un
# filament qui passe ailleurs n'est pas un centre de gravite, c'est un decalque.
# Et ces bosses traversaient ensuite un exp() qui les amplifiait.
#
# On ancre donc dans Psi, le champ qui DEPLACE la matiere. Le catalogue est
# depose comme des masses ponctuelles, puis on lui applique le meme operateur de
# deplacement que le reste : l'ecoulement de Zel'dovich transporte reellement les
# particules vers ces points. Trois consequences :
#   - purement lineaire et additif -> conforme a l'interdit sur les operateurs
#     spatialement non lineaires en aval du generateur ;
#   - herite gratuitement, le raccord transmettant deja Psi ;
#   - aucune contribution ajoutee avant la transformation non lineaire, donc le
#     piege de l'exp() signale en §0 ne s'applique pas.
CATALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "app", "public", "data", "local_group_catalog.json")
R_REF_MPC = 0.01          # rayon de reference, ABSOLU (INV-B1 : jamais w.sum())
ANCHOR_GAIN = 2.235e3
# Calibre le 31/07 sur la geometrie reelle de la ligne H (grille 480x480x107,
# cellule 0,1411 Mpc) pour rms(Psi_ancrage) = 1,0 Mpc, soit environ l@echelle de
# convergence d@un filament a cette ligne, contre rms(Psi) ~ 10 Mpc pour le champ.
# Reste A CONFIRMER VISUELLEMENT : c@est un point d@equilibre, pas une mesure.

# D4 : l'influence s'attenue avec l'echelle et disparait au-dela du voisinage.
# La §4.7 s'arretait a 67 Mpc, ce qui tombe sur la ligne I dans l'echelle du 30/07.
ANCHOR_STRENGTH = {"H": 1.00, "I": 0.45, "J": 0.12}


def anchor_psi(code, shape, box, cell):
    """Deplacement attractif vers les positions reelles du catalogue.

    Retourne None si la ligne n'est pas ancree (D4 : au-dela du voisinage, le
    Groupe Local redevient statistiquement invisible, comme n'importe quelle
    autre region -- c'est le comportement correct, pas une limitation).
    """
    w0 = ANCHOR_STRENGTH.get(code, 0.0)
    if w0 <= 0.0:
        return None
    with open(os.path.normpath(CATALOG)) as fh:
        gals = json.load(fh)
    d = np.array([g["distanceMpc"] for g in gals], np.float64)
    th = np.radians([g["angleDeg"] for g in gals])
    # poids ABSOLU, proportionnel au volume ; jamais normalise par le catalogue,
    # sinon ajouter une galaxie modifierait toutes les autres (INV-B1).
    w = (np.array([g["radiusMpc"] for g in gals], np.float64) / R_REF_MPC) ** 3
    pos = np.stack([d * np.cos(th), d * np.sin(th), np.zeros_like(d)], 1)

    nx, ny, nz = shape
    bx, _, Lz = box
    ix = np.round((pos[:, 0] / bx + 0.5) * nx - 0.5).astype(np.int64)
    iy = np.round((pos[:, 1] / bx + 0.5) * ny - 0.5).astype(np.int64)
    iz = np.round((pos[:, 2] / Lz + 0.5) * nz - 0.5).astype(np.int64)
    keep = ((ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz))
    if not keep.any():
        return None
    rho = np.zeros(shape, np.float32)
    np.add.at(rho, (ix[keep], iy[keep], iz[keep]), (w[keep] * ANCHOR_GAIN).astype(np.float32))
    return psi_band(rho, box, 0.0, 2 * np.pi / (2 * cell)) * np.float32(w0), int(keep.sum())


# ------------------------------------------------- chargement des parametres
MATRIX_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "app", "public", "data", "spacetime_matrix.json"))


def load_params(path=None):
    """Charge le bloc `generation` de la matrice dans les globales du module.

    Appele a l'import. Sans cela le JSON serait de la documentation morte : le
    code garderait ses propres valeurs et la source de verite mentirait.
    """
    g = globals()
    try:
        with open(path or MATRIX_PATH) as fh:
            gen = json.load(fh)["generation"]
    except (OSError, KeyError):
        return False
    r, ra, cf = gen["render"], gen["raccord"], gen["champ_fin"]
    g.update(
        OUT_N=r["out_n"], TARGET_MEAN=r["target_mean_255"],
        SLAB_FRAC=r["slab_frac"], PSF_PX=r["psf_px"], JITTER=r["jitter"],
        TARGET_PROJ=r["target_proj"],
        K_CUT_SAFETY=ra["k_cut_safety"], SUB_Z=ra["sub_z"],
        FRESH_PSI_GAIN=ra["fresh_psi_gain"], CHUNK=ra["chunk"],
        FINE_A=cf["a"], FINE_FLOOR=cf["floor"], FINE_GAMMA=cf["gamma"],
        FINE_LAM_HI_PX=cf["lam_hi_px"], FINE_LAM_LO_PX=cf["lam_lo_px"],
        HOMOGENEITY_MPC=cf["homogeneity_mpc"], FINE_STRENGTH=cf["strength"],
        HALO_FRAC=gen["halos"]["frac"], PROFILE_Q=gen["halos"]["profile_q"],
        R_HALO_MPC=gen["halos"]["r_mpc"], SUB_LEVELS=gen["halos"]["sub_levels"],
        SUB_FRAC=gen["halos"]["sub_frac"],
        ANCHOR_GAIN=gen["ancrage"]["gain"], R_REF_MPC=gen["ancrage"]["r_ref_mpc"],
        ANCHOR_STRENGTH=gen["ancrage"]["strength"],
    )
    rows = json.load(open(path or MATRIX_PATH))["zoom_axis"]["rows"]
    seeds = gen["seeds"]
    g["CHAIN"] = [(c, rows[c]["halfwidth_mpc"], rows[c]["margin_factor"], seeds[c])
                  for c in sorted(seeds, reverse=True) if c in rows]
    return True


PARAMS_LOADED = load_params()


# ---------------------------------------------------------------- geometrie
def grid_for(half, margin):
    """Dalle anisotrope : cellule = pixel de sortie, epaisseur = tranche + marge
    Psi PROPRE A LA BOITE."""
    box_xy = 2.0 * half * margin
    cell = 2.0 * half / OUT_N
    nxy = int(round(box_xy / cell))
    npsi = min(96, max(nxy, 32))
    psi = NA.psi_rms((npsi,) * 3, (box_xy,) * 3, 2 * box_xy / npsi)
    T = min(SLAB_FRAC * 2 * half, SLAB_MAX_MPC)
    # seule la composante z fait entrer/sortir de la dalle : rms = psi/sqrt(3)
    Lz = T + 4.0 * psi / np.sqrt(3.0)
    nz = max(int(round(Lz / cell)), 8)
    return nxy, nz, cell, box_xy, Lz, psi


# ------------------------------------------------- operateurs de bande (lineaires)
def _bandpass(delta, box, kmin, kmax):
    """delta restreint a (kmin, kmax]. FFT dans la boite ou delta est periodique."""
    _, _, _, kmag = ST.k_grid_aniso(delta.shape, box)
    band = (kmag > kmin) & (kmag <= kmax)
    dk = np.fft.rfftn(delta)
    return np.fft.irfftn(np.where(band, dk, 0), s=delta.shape).astype(np.float32)


def psi_band(delta, box, kmin, kmax):
    """Deplacement de Zel'dovich Psi = i k delta / k^2, restreint a (kmin, kmax].

    Meme remarque : la FFT n'est legitime que parce que `delta` est periodique
    dans `box`. Ne jamais appeler cette fonction sur un champ interpole.
    """
    KX, KY, KZ, kmag = ST.k_grid_aniso(delta.shape, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = (kmag > kmin) & (kmag <= kmax)
    out = np.empty(delta.shape + (3,), np.float32)
    for a, K in enumerate((KX, KY, KZ)):
        out[..., a] = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=delta.shape)
    return out


# --------------------------------------------------------------- interpolation
def _idx_from_mpc(pts, p_box_xy, p_Lz, p_shape):
    """Coordonnees comobiles (boite centree en 0) -> indices de grille parent."""
    nx, ny, nz = p_shape
    return np.stack([
        (pts[:, 0] / p_box_xy + 0.5) * nx - 0.5,
        (pts[:, 1] / p_box_xy + 0.5) * ny - 0.5,
        (pts[:, 2] / p_Lz + 0.5) * nz - 0.5,
    ])


CHUNK = 4_000_000           # points par bloc d'interpolation.
# A la ligne H, le nuage compte 49 M de points : construire le tableau de
# coordonnees d'un coup demande 592 Mo de plus que le nuage lui-meme, et la
# chaine se fait tuer. Par blocs, le temporaire reste sous 100 Mo, quelle que
# soit la resolution -- c'est ce qui rendra la cuisson 1024 tenable.


def sample_parent(fieldp, pts, p_box_xy, p_Lz):
    """Echantillonne un champ parent (scalaire ou vectoriel) en des points Mpc.

    Spline cubique (order=3) et non trilineaire : pres de k_cut, l'interpolation
    lineaire attenue, et cette attenuation se lit directement dans std(delta).
    `mode="nearest"` en bord : les points de l'enfant sont tres a l'interieur du
    parent, le mode ne joue que sur l'arrondi du dernier demi-pixel.
    """
    # map_coordinates(order=3) refiltre le tableau d'entree A CHAQUE APPEL. Avec
    # 8 blocs x 3 composantes, c'etait 24 prefiltrages d'une grille de 14 M de
    # cellules -- la ligne I n'arrivait jamais au bout. On prefiltre UNE fois par
    # composante, puis prefilter=False.
    n = pts.shape[0]
    scal = fieldp.ndim == 3
    ncomp = 1 if scal else fieldp.shape[3]
    out = np.empty(n if scal else (n, ncomp), np.float32)
    for a in range(ncomp):
        src = fieldp if scal else fieldp[..., a]
        pref = ndimage.spline_filter(src, order=3, output=np.float32)
        for s0 in range(0, n, CHUNK):
            s1 = min(s0 + CHUNK, n)
            C = _idx_from_mpc(pts[s0:s1], p_box_xy, p_Lz, fieldp.shape[:3])
            v = ndimage.map_coordinates(pref, C, order=3, mode="nearest",
                                        prefilter=False)
            if scal:
                out[s0:s1] = v
            else:
                out[s0:s1, a] = v
            del C, v
        del pref
    return out


def sample_parent_grid(fieldp, shape, box_xy, Lz, p_box_xy, p_Lz):
    """Echantillonne un champ parent SCALAIRE sur toute la grille de l'enfant."""
    nx, ny, nz = shape
    gx = ((np.arange(nx) + 0.5) * (box_xy / nx) - box_xy / 2).astype(np.float32)
    gy = ((np.arange(ny) + 0.5) * (box_xy / ny) - box_xy / 2).astype(np.float32)
    gz = ((np.arange(nz) + 0.5) * (Lz / nz) - Lz / 2).astype(np.float32)
    # Par tranches de x : le maillage complet en float64 pesait 592 Mo a la
    # ligne H, plus que le champ lui-meme. Une tranche en pese 1,2.
    out = np.empty(shape, np.float32)
    Y, Z = np.meshgrid(gy, gz, indexing="ij")
    Y, Z = Y.ravel(), Z.ravel()
    P = np.empty((Y.size, 3), np.float32)
    P[:, 1], P[:, 2] = Y, Z
    pref = ndimage.spline_filter(fieldp, order=3, output=np.float32)
    for i in range(nx):
        P[:, 0] = gx[i]
        C = _idx_from_mpc(P, p_box_xy, p_Lz, fieldp.shape[:3])
        out[i] = ndimage.map_coordinates(pref, C, order=3, mode="nearest",
                                         prefilter=False).reshape(ny, nz)
    return out


# --------------------------------------------------------------------- couche
class Layer:
    """Ce qu'une ligne transmet a la suivante.

    N'y garder QUE le necessaire : `delta_lo`, `psi_lo` et la geometrie. Le champ
    complet et le nuage de points sont liberes des que la ligne est rendue --
    sinon la chaine retient huit grilles de 480x480xnz et se fait tuer avant la
    derniere ligne (mesure du 30/07 : Killed a la ligne H).
    """
    __slots__ = ("code", "half", "cell", "box_xy", "Lz", "shape",
                 "delta", "delta_lo", "psi_lo", "k_cut", "psi_rms", "web", "n_halo",
                 "std_delta", "n_anchor", "fine")

    def drop_heavy(self):
        """Libere ce dont l'enfant n'a pas besoin."""
        self.delta = None
        self.web = None


def bake_layer(code, half, margin, seed, parent=None):
    nxy, nz, cell, box_xy, Lz, psirms = grid_for(half, margin)
    shape, box = (nxy, nxy, nz), (box_xy, box_xy, Lz)
    k_max = 2 * np.pi / (2 * cell)          # bande de deplacement de CETTE ligne

    d_fresh = NA.gen_delta_abs(shape, box, seed)

    if parent is None:
        delta = d_fresh
        PSI = psi_band(delta, box, 0.0, k_max)
    else:
        kc = parent.k_cut
        # --- (3) part fraiche de l'enfant, au-dessus de la coupure
        d_hi = _bandpass(d_fresh, box, kc, k_max)
        psi_hi = psi_band(d_hi, box, kc, k_max) * np.float32(FRESH_PSI_GAIN)
        # --- (2) part heritee : INTERPOLATION, aucune FFT en aval
        d_lo = sample_parent_grid(parent.delta_lo, shape, box_xy, Lz,
                                  parent.box_xy, parent.Lz)
        # --- (4) somme
        delta = (d_lo + d_hi).astype(np.float32)
        PSI = psi_hi                         # Psi_lo s'ajoute aux positions, plus bas
        del d_hi, d_lo
    del d_fresh

    # --- ancrage du catalogue (D6), ajoute a Psi AVANT la propagation ---
    L_anchor = anchor_psi(code, shape, box, cell)
    if L_anchor is not None:
        PSI += L_anchor[0]
        n_anchor = L_anchor[1]
        del L_anchor
    else:
        n_anchor = 0

    # ce que CETTE ligne transmettra : sa coupure vaut la moitie de sa Nyquist
    k_cut = np.pi / (K_CUT_SAFETY * cell)
    delta_lo = _bandpass(delta, box, 0.0, k_cut)

    # Psi transmis = le deplacement REELLEMENT APPLIQUE a cette ligne, filtre --
    # et non un Psi recalcule depuis delta. Corrige le 02/08.
    #
    # Le code recalculait psi_band(delta, 0, k_cut). Or delta = d_lo + d_hi ou
    # d_lo est le champ du parent INTERPOLE : recalculer Psi dessus ne redonne
    # pas le psi_lo que le parent avait transmis, a cause de l'interpolation et
    # des bords. La ligne etait donc deplacee par une quantite et en transmettait
    # une autre -- d'ou une matiere heritee decalee de plusieurs pixels, sans que
    # ni les halos, ni l'ancrage, ni la densite de particules, ni le deplacement
    # frais en soient responsables (les quatre ont ete testes et disculpes).
    PSI_full = PSI.copy()
    if parent is not None:
        for a in range(3):
            PSI_full[..., a] += sample_parent_grid(parent.psi_lo[..., a], shape,
                                                   box_xy, Lz, parent.box_xy, parent.Lz)
    psi_lo = np.empty_like(PSI_full)
    for a in range(3):
        psi_lo[..., a] = _bandpass(PSI_full[..., a], box, 0.0, k_cut)
    del PSI_full

    # --------------------------------------------------- positions lagrangiennes
    rng = np.random.default_rng(seed + 7)
    cz = cell / SUB_Z
    gx = (np.arange(nxy) + 0.5) * cell - box_xy / 2
    gz = (np.arange(nz * SUB_Z) + 0.5) * cz - Lz / 2
    Q = np.stack(np.meshgrid(gx, gx, gz, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
    J = rng.random(Q.shape).astype(np.float32) - 0.5
    Q[:, :2] += J[:, :2] * cell * 2 * JITTER
    Q[:, 2] += J[:, 2] * cz * 2 * JITTER
    del J

    # Psi est INTERPOLE aux positions lagrangiennes reelles, pas lu au noeud de
    # grille : le reseau est raffine en z, les noeuds ne coincident plus.
    # Le deplacement est applique PAR BLOCS, directement dans le nuage : garder
    # un tableau `disp` complet coutait 592 Mo de plus a la ligne H, ce qui
    # suffisait a faire tuer le processus. On n'en conserve que la trace utile --
    # la somme des carres, et le sous-reseau de base pour les halos.
    nQ = Q.shape[0]
    nb = (nQ + SUB_Z - 1) // SUB_Z
    disp_b = np.empty((nb, 3), np.float32)
    ss, nb_done = 0.0, 0
    for s0 in range(0, nQ, CHUNK):
        s1 = min(s0 + CHUNK, nQ)
        C = np.stack([(Q[s0:s1, 0] / box_xy + 0.5) * nxy - 0.5,
                      (Q[s0:s1, 1] / box_xy + 0.5) * nxy - 0.5,
                      (Q[s0:s1, 2] / Lz + 0.5) * nz - 0.5])
        d = np.empty((s1 - s0, 3), np.float32)
        for a in range(3):
            d[:, a] = ndimage.map_coordinates(PSI[..., a], C, order=1, mode="nearest")
        del C
        if parent is not None:
            d += sample_parent(parent.psi_lo, Q[s0:s1], parent.box_xy, parent.Lz)
        ss += float((d.astype(np.float64) ** 2).sum())
        k0 = (s0 + SUB_Z - 1) // SUB_Z
        sel = d[(-s0) % SUB_Z::SUB_Z]
        disp_b[k0:k0 + len(sel)] = sel
        nb_done += len(sel)
        Q[s0:s1] += d
        del d, sel
    del PSI
    disp_b = disp_b[:nb_done]
    web = Q

    L = Layer()
    L.code, L.half, L.cell, L.box_xy, L.Lz, L.shape = code, half, cell, box_xy, Lz, shape
    L.n_anchor = n_anchor
    _calib_fine_norm()
    L.fine = fine_for(code, seed + 4242,
                      None if parent is None else getattr(parent, "fine", None),
                      None if parent is None else parent.half / half, half=half)
    L.delta, L.delta_lo, L.psi_lo, L.k_cut = delta, delta_lo, psi_lo, k_cut
    L.psi_rms = float(np.sqrt(ss / nQ))
    L.std_delta = float(delta.std())

    # ------------------------------------------------------------------ halos
    px = 2 * half / OUT_N
    L.n_halo = 0
    if R_HALO_MPC > 0.6 * px:
        qL, mass = M.extract_halos(delta, box_xy, 2 * cell, 0.5, 2 * cell, 40000)
        if len(qL):
            # L'appariement des halos se fait sur le RESEAU DE BASE, pas sur le
            # nuage raffine : un cKDTree sur 49 M de points demande plus d'un Go
            # et tue la chaine. Les halos sont des objets compacts -- les peupler
            # depuis le reseau de base preserve exactement le comportement
            # d'avant SUB_Z, et le raffinement en z ne sert qu'a echantillonner
            # le champ plus finement.
            # Q a ete deplace EN PLACE : il faut remonter aux positions
            # lagrangiennes pour apparier les centres de halos, qui sont
            # lagrangiens eux aussi. Bug introduit le 30/07 par le passage au
            # deplacement en place, corrige le 31/07.
            base = np.arange(0, len(Q), SUB_Z)
            Qb = Q[base] - disp_b
            tree = cKDTree(Qb)
            _, near = tree.query(qL)
            pos_e = qL + disp_b[near]
            budget = int(HALO_FRAC * len(Qb))
            w = mass ** 0.9
            cnt = np.maximum((w / w.sum() * budget).astype(np.int64), 0)
            k = cnt > 0
            qL, mass, cnt, pos_e = qL[k], mass[k], cnt[k], pos_e[k]
            taken = np.zeros(len(Qb), bool)
            owner = np.full(len(Qb), -1, np.int32)
            for i in np.argsort(mass)[::-1]:
                c = int(cnt[i])
                if c < 1:
                    continue
                _, idx = tree.query(qL[i], k=min(c * 3, len(Qb)))
                idx = np.atleast_1d(idx)
                free = idx[~taken[idx]][:c]
                taken[free] = True
                owner[free] = i
            hid = owner[taken]
            nh = int(taken.sum())
            L.n_halo = len(qL)
            lvl = (rng.random(nh) * (SUB_LEVELS + 1)).astype(np.int32)
            # masse de reference ABSOLUE : jamais mass.max(), qui est une
            # statistique globale du catalogue (INV-B1).
            m_ref = M.HALO_MASS_REF if hasattr(M, "HALO_MASS_REF") else 1.0
            rr = R_HALO_MPC * (mass[hid] / m_ref) ** 0.28 * SUB_FRAC ** lvl
            r = rr * rng.random(nh) ** PROFILE_Q
            ct = 2 * rng.random(nh) - 1
            st = np.sqrt(np.maximum(1 - ct ** 2, 0))
            ph = 2 * np.pi * rng.random(nh)
            web[base[taken]] = (pos_e[hid] + r[:, None] *
                                np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)).astype(np.float32)
            del tree, Qb
    del Q
    L.web = web
    return L


def field_projection(L, delta):
    """Projection du champ dans la dalle visible, sans particules.

    Sert de reference a F2 : B1 porte sur la MATIERE, pas sur la finesse du
    tirage. Comparer deux rendus particulaires mesure aussi la grenaille du
    parent magnifie, qui n'a rien a voir avec l'heritage.
    """
    nz = delta.shape[2]
    k = int(max(1, round(SLAB_FRAC * 2 * L.half / (L.Lz / nz))))
    z0 = (nz - k) // 2
    im = delta[:, :, z0:z0 + k].sum(2)
    w = int(round(im.shape[0] * L.half / (L.box_xy / 2)))
    c = (im.shape[0] - w) // 2
    yy, xx = np.mgrid[0:OUT_N, 0:OUT_N] * (w / OUT_N) + c
    return ndimage.map_coordinates(im.astype(np.float64), np.stack([yy, xx]),
                                   order=1, mode="nearest")


def _fine_spectrum(k, n, lam_hi, lam_lo):
    return np.where((k >= n / lam_hi) & (k <= n / lam_lo),
                    np.maximum(k, 1e-9) ** -2.2, 0.0)


def fine_fresh(seed, lam_hi, lam_lo, n=None):
    """Bande fraiche du champ fin, amplitude ABSOLUE (jamais f/f.std()).

    La normalisation par l'ecart-type mesure est une statistique globale : elle
    ferait dependre l'amplitude de chaque ligne du contenu de cette ligne, et
    l'heritage se casserait silencieusement (INV-B1). C'est le defaut de
    `normalize_variance` de la premiere iteration, que Marc avait vu comme des
    « deplacements de matiere ».
    """
    n = n or FINE_N
    rng = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[:, None] * n
    ky = np.fft.rfftfreq(n)[None, :] * n
    k = np.sqrt(kx ** 2 + ky ** 2)
    P = _fine_spectrum(k, n, lam_hi, lam_lo)
    z = (rng.normal(size=k.shape) + 1j * rng.normal(size=k.shape)) * np.sqrt(P / 2)
    return (np.fft.irfft2(z, s=(n, n)) * FINE_NORM).astype(np.float32)


def fine_inherit(fine_parent, ratio, n=None):
    """Part du champ fin heritee du parent : recadrage central + agrandissement.

    C'est le mecanisme `crop_and_upsample` de la premiere iteration (e0d5336),
    applique au CHAMP FIN et non au champ de densite. Purement lineaire.
    """
    n = n or FINE_N
    w = n / ratio
    c = (n - w) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    C = np.stack([c + yy * w / n, c + xx * w / n])
    return ndimage.map_coordinates(fine_parent.astype(np.float64), C,
                                   order=3, mode="nearest").astype(np.float32)


def _fine_band_var(lam_hi, lam_lo):
    """Variance THEORIQUE d'une bande du champ fin, par integration du spectre.

    Pour P(k) ~ k^-2.2 en 2D, var ~ integrale de P(k) k dk ~ [k^-0.2]/(-0.2).
    Grandeur ANALYTIQUE : elle ne depend d'aucune image, donc elle ne peut pas
    faire dependre une ligne du contenu d'une autre (INV-B1).
    """
    k1, k2 = OUT_N / lam_hi, OUT_N / lam_lo
    return (k1 ** -0.2 - k2 ** -0.2) / 0.2


def fine_weights(ratio):
    """Poids de l'heritage et de la bande fraiche, pour variance totale = 1.

    Sans cela le champ fin ACCUMULE sa variance a chaque cran d'heritage et son
    amplitude effective croit en descendant l'echelle -- mesure le 02/08 :
    saturation claire 1,1-1,4 %, creux bimodal 6,8, isotropie 0,75.
    """
    vh = _fine_band_var(FINE_LAM_HI_PX, ratio * FINE_LAM_LO_PX)
    vf = _fine_band_var(ratio * FINE_LAM_LO_PX, FINE_LAM_LO_PX)
    t = vh + vf
    return np.sqrt(vh / t), np.sqrt(vf / t)


def fine_lam_hi(half):
    """Plus grande longueur d'onde du champ fin, en pixels, bornee par B8."""
    px = 2.0 * half / OUT_N          # half = fenetre VISIBLE, hors marge
    return float(min(FINE_LAM_HI_PX, max(HOMOGENEITY_MPC / px, 2.6)))


def fine_for(code, seed, fine_parent=None, ratio=None, half=None):
    """Champ fin d'une ligne : part heritee + bande fraiche a SA resolution.

    Le parent resout jusqu'a FINE_LAM_LO_PX de SA grille ; agrandi d'un facteur
    `ratio`, cela devient ratio x FINE_LAM_LO_PX sur l'enfant. L'enfant n'ajoute
    donc du neuf QUE sous cette limite -- ce qu'il est seul a pouvoir resoudre.
    Aucun double comptage, et la bande commune est heritee a l'identique.
    """
    if fine_parent is None:
        # La bande de la ligne racine est bornee par l'homogeneite, donc plus
        # etroite que la bande nominale : sans compensation elle porte moins de
        # variance et la ligne parait fade (std 7,1 contre 21,3 mesures le
        # 02/08). On renormalise par le rapport des variances THEORIQUES des deux
        # bandes -- grandeur analytique, aucune statistique mesuree.
        lam = fine_lam_hi(half)
        f = fine_fresh(seed, lam, FINE_LAM_LO_PX)
        k = np.sqrt(_fine_band_var(FINE_LAM_HI_PX, FINE_LAM_LO_PX)
                    / max(_fine_band_var(lam, FINE_LAM_LO_PX), 1e-12))
        return (f * np.float32(k)).astype(np.float32)
    wh, wf = fine_weights(ratio)
    fresh = fine_fresh(seed, ratio * FINE_LAM_LO_PX, FINE_LAM_LO_PX)
    fresh = fresh / np.sqrt(_fine_band_var(ratio * FINE_LAM_LO_PX, FINE_LAM_LO_PX)
                            / _fine_band_var(FINE_LAM_HI_PX, FINE_LAM_LO_PX))
    return (wh * fine_inherit(fine_parent, ratio) + wf * fresh).astype(np.float32)


def fine_field(seed, n=None):
    """Champ 2D frais, bande large, variance normalisee a 1.

    Amplitude IMPOSEE et non issue de sigma_8 : le spectre LCDM ne donne presque
    aucune puissance aux petites echelles, c'est precisement pourquoi le contenu
    fin restait invisible.
    """
    n = n or FINE_N
    rng = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[:, None] * n
    ky = np.fft.rfftfreq(n)[None, :] * n
    k = np.sqrt(kx ** 2 + ky ** 2)
    P = np.where((k >= n / FINE_LAM_HI_PX) & (k <= n / FINE_LAM_LO_PX),
                 np.maximum(k, 1e-9) ** -2.2, 0.0)
    z = (rng.normal(size=k.shape) + 1j * rng.normal(size=k.shape)) * np.sqrt(P / 2)
    f = np.fft.irfft2(z, s=(n, n))
    return (f / f.std()).astype(np.float32)


def apply_fine(img, code, fine):
    """Module la densite deposee par le champ fin, puis ajoute le fond diffus.

    Le gain de toile s'applique AVANT le champ fin : il agit sur la densite
    projetee, donc sur la structure, et non sur le grain qui la module.
    """
    g = WEB_GAIN.get(code, 1.0)
    if g != 1.0:
        mu = float(img.mean()) or 1.0
        img = mu * (img / mu) ** g
    w = FINE_STRENGTH.get(code, 0.0)
    if w <= 0.0 or fine is None:
        return img, 1.0
    A = FINE_A * w
    out = img * np.exp(fine * A - A * A / 2)
    return out + FINE_FLOOR * w * out.mean(), FINE_GAMMA


def _calib_fine_norm():
    """Constante d'amplitude ABSOLUE, calculee une fois, jamais mesuree."""
    global FINE_NORM
    if FINE_NORM:
        return
    FINE_NORM = 1.0
    f = fine_fresh(0, FINE_LAM_HI_PX, FINE_LAM_LO_PX)
    FINE_NORM = 1.0 / float(f.std())


def render_full(L, seed, margin=1.5):
    """Texture de PRODUCTION : couvre +/- half*margin, pas seulement +/- half.

    L'application recadre rectangulairement pour remplir l'ecran sans
    deformation (DensityLayer.tsx, MARGIN_FACTOR) : une texture limitee au champ
    nominal produirait des bandes noires sur les ecrans allonges.

    La taille de sortie suit la marge, `OUT_N * margin`, de sorte que l'echelle
    Mpc/pixel soit INCHANGEE. C'est ce qui permet de reutiliser tel quel le champ
    fin, dont les longueurs d'onde sont en pixels : elles gardent exactement la
    meme signification physique.
    """
    n = int(round(OUT_N * margin))
    ext = L.half * margin
    slab = min(SLAB_FRAC * 2 * L.half, SLAB_MAX_MPC)
    rng = np.random.default_rng(seed + 991)
    img = np.zeros((n, n), np.float32)
    web = L.web
    base = ((np.abs(web[:, 2]) < slab / 2).mean() * 1.0) or 1.0
    rep = int(np.clip(round(TARGET_PROJ * margin ** 2 / max(len(web) * base * 0.9, 1)), 1, 20))
    for k in range(rep):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32) - 0.5) * L.cell
        m = ((np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < ext) & (np.abs(p[:, 1]) < ext))
        q = p[m]
        ix = np.clip(((q[:, 0] + ext) / (2 * ext) * n).astype(np.int32), 0, n - 1)
        iy = np.clip(((q[:, 1] + ext) / (2 * ext) * n).astype(np.int32), 0, n - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
        del p, q
    img = ndimage.gaussian_filter(img, PSF_PX)
    fine = getattr(L, "fine", None)
    if fine is not None and fine.shape[0] != n:
        fine = ndimage.zoom(fine, n / fine.shape[0], order=1)
    img, gm = apply_fine(img, L.code, fine)
    # Le ton se cale sur la FENETRE VISIBLE, pas sur la texture entiere : la
    # marge n'est jamais montree telle quelle, et sur les lignes ou le centre est
    # plus dense que les bords (une galaxie au milieu) viser la moyenne globale
    # rendait la zone vue trop claire -- ligne A mesuree a 81,9/255 pour une
    # cible de 68 (03/08).
    c = (n - OUT_N) // 2
    a = M.solve_alpha(img[c:c + OUT_N, c:c + OUT_N], TARGET_MEAN, gamma=gm)
    return M.tone(img, a, gamma=gm)


def render(L, seed):
    slab = min(SLAB_FRAC * 2 * L.half, SLAB_MAX_MPC)
    rng = np.random.default_rng(seed + 991)
    img = np.zeros((OUT_N, OUT_N), np.float32)
    web = L.web
    base = ((np.abs(web[:, 2]) < slab / 2).mean() * 1.0) or 1.0
    rep = int(np.clip(round(TARGET_PROJ / max(len(web) * base * 0.9, 1)), 1, 20))
    for k in range(rep):
        p = web if k == 0 else web + (rng.random(web.shape).astype(np.float32) - 0.5) * L.cell
        m = ((np.abs(p[:, 2]) < slab / 2) & (np.abs(p[:, 0]) < L.half)
             & (np.abs(p[:, 1]) < L.half))
        q = p[m]
        ix = np.clip(((q[:, 0] + L.half) / (2 * L.half) * OUT_N).astype(np.int32), 0, OUT_N - 1)
        iy = np.clip(((q[:, 1] + L.half) / (2 * L.half) * OUT_N).astype(np.int32), 0, OUT_N - 1)
        np.add.at(img, (ix, iy), np.float32(1.0))
        del p, q
    img = ndimage.gaussian_filter(img, PSF_PX)
    f = getattr(L, "fine", None)
    if f is not None and f.shape[0] != OUT_N:
        c = (f.shape[0] - OUT_N) // 2          # fenetre visible = centre
        f = f[c:c + OUT_N, c:c + OUT_N]
    img, gm = apply_fine(img, L.code, f)
    a = M.solve_alpha(img, TARGET_MEAN, gamma=gm)
    return M.tone(img, a, gamma=gm)


# ---------------------------------------------------------- relais sur disque
# La chaine entiere ne tient pas en memoire : a la ligne H le nuage compte 49 M
# de points et le processus se fait tuer (mesure du 30/07, 4 Go). Chaque ligne
# s'execute donc dans son propre processus et ne transmet a la suivante que sa
# charge utile passe-bas, via un .npz. C'est aussi l'architecture qu'il faudra
# pour la cuisson en 1024 : jamais deux lignes vivantes a la fois.
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_chaine")


def save_payload(L, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, delta_lo=L.delta_lo, psi_lo=L.psi_lo, fine=L.fine,
             meta=np.array([L.half, L.cell, L.box_xy, L.Lz, L.k_cut,
                            L.psi_rms, L.std_delta, L.n_halo]))


def load_payload(path):
    z = np.load(path)
    L = Layer()
    (L.half, L.cell, L.box_xy, L.Lz, L.k_cut,
     L.psi_rms, L.std_delta, L.n_halo) = z["meta"]
    L.n_halo = int(L.n_halo)
    L.delta_lo, L.psi_lo = z["delta_lo"], z["psi_lo"]
    L.fine = z["fine"] if "fine" in z.files else None
    L.shape = L.delta_lo.shape
    return L


def bake_one(code, out_dir=None):
    """Cuit UNE ligne, en repartant de la charge utile de son parent sur disque.

    La charge utile passe-bas est ecrite sur disque AVANT le placement des
    particules, puis liberee : a la ligne H elle pese 395 Mo, et les garder
    pendant que le nuage de 49 M de points existe suffisait a tuer le processus.
    """
    out_dir = out_dir or CACHE
    idx = [c[0] for c in CHAIN].index(code)
    _, half, margin, seed = CHAIN[idx]
    parent = None
    if idx > 0:
        pp = os.path.join(out_dir, CHAIN[idx - 1][0] + ".npz")
        if not os.path.exists(pp):
            pp = os.path.join(CACHE, CHAIN[idx - 1][0] + ".npz")
        parent = load_payload(pp)
    L = bake_layer(code, half, margin, seed, parent)
    del parent
    save_payload(L, os.path.join(out_dir, code + ".npz"))
    L.delta_lo = None
    L.psi_lo = None
    np.save(os.path.join(out_dir, code + "_rendu.npy"), render(L, seed))
    np.save(os.path.join(out_dir, code + "_champ.npy"), field_projection(L, L.delta))
    print(f"  {code:4s}{half:11.2f} {L.cell:9.4f} {str(L.shape):>16s}"
          f" {L.std_delta:8.3f} {L.psi_rms:10.3f} {L.n_halo:7d}"
          f" {getattr(L, 'n_anchor', 0):7d}", flush=True)
    return L


def run_chain(codes=None, verbose=True, keep_images=True):
    """Deroule la chaine du plus grand au plus petit.

    Ne retient qu'un parent a la fois, et seulement ses champs passe-bas. Les
    images (320x320) sont conservees : elles servent aux controles de continuite
    inter-lignes, et pesent 0,4 Mo chacune.
    """
    todo = [c for c in CHAIN if codes is None or c[0] in codes]
    parent, out = None, []
    if verbose:
        print(f"  {'':4s}{'demi-champ':>11s} {'cellule':>9s} {'grille':>16s}"
              f" {'std(d)':>8s} {'rms(Psi)':>10s} {'halos':>7s}")
    for code, half, margin, seed in todo:
        L = bake_layer(code, half, margin, seed, parent)
        img = render(L, seed) if keep_images else None
        champ = field_projection(L, L.delta) if keep_images else None
        if verbose:
            print(f"  {L.code:4s}{half:11.2f} {L.cell:9.4f} {str(L.shape):>16s}"
                  f" {L.std_delta:8.3f} {L.psi_rms:10.3f} {L.n_halo:7d}")
        L.drop_heavy()
        out.append((L, img, champ))
        if parent is not None:
            parent.delta_lo = None
            parent.psi_lo = None
        parent = L
    return out
