"""LIGNES A SPRITES A -> G : galaxies reelles, catalogue, fond ambiant.

TOUT y est fonction de l'amplitude de structure `amp` = n/10 de la colonne
(D-22), afin que la dissolution temporelle soit possible partout -- rappel de
Marc du 02/08. Aucune valeur n'est figee a l'epoque actuelle.

Loi temporelle de chaque composante
-----------------------------------
| composante        | loi                    | exigence servie              |
|-------------------|------------------------|------------------------------|
| sprite N-corps    | frame f00 -> f13       | C1 s'etale ET palit          |
| rayon procedural  | croit en 1/amp^0.35    | C1, C2 (ne grossit pas en    |
|                   |                        | luminosite : le pic baisse)  |
| eclat procedural  | decroit en amp^1.2     | C2, C5                       |
| fond ambiant      | herite de H(amp)       | C1 sur le fond aussi         |
| champ fin         | amp^0.6, plancher 0,25 | C8 grain jusqu'au bout,      |
|                   |                        | C4 sans colonisation         |

Le plancher du champ fin est ce qui garantit **C8** -- « uniforme mais plein de
grain, jamais un aplat » -- sans violer **C4** : son amplitude DECROIT toujours,
elle ne fait que ne pas s'annuler. Une amplitude constante ferait au contraire
grandir sa part relative pendant la dissolution, et les petites structures
coloniseraient l'image. C'est l'approche `A(s,a)` par bande, deja ecartee.

Les sprites N-corps (9 galaxies x 14 frames, plus la Voie lactee en 2048) sont
cuits et valides ; ils ne dependent pas du moteur de champ.
"""
import json
import os

import numpy as np
from scipy import ndimage

import gen_chain as G
import mcpm_web as M

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "app", "public", "data")
SPRITE_DIR = os.path.normpath(os.path.join(DATA, "dissolution_sprites"))
SPRITE_HIRES = os.path.normpath(os.path.join(DATA, "dissolution_sprites_hires"))
CATALOG = os.path.normpath(os.path.join(DATA, "local_group_catalog.json"))

# Parametres lus depuis la source de verite, bloc `generation.sprites`.
def _load():
    import json
    try:
        with open(G.MATRIX_PATH) as fh:
            sp = json.load(fh)["generation"]["sprites"]
    except (OSError, KeyError):
        return {}
    return sp


_SP = _load()

N_FRAMES = _SP.get("n_frames", 14)
# f00 = galaxie formee (rayon median 12 px), f13 = dissoute (92 px).
# Mesure du 02/08 : l'ecart-type passe de 12,1 a 3,0 pendant que le rayon
# septuple -- la galaxie s'etale ET palit, C1 et C2 sont donc portees par les
# sprites eux-memes, sans traitement supplementaire.

# Rayons physiques, en Mpc. Valeurs ABSOLUES (INV-B1) : aucune ne depend du
# catalogue ni de l'image courante.
MW_RADIUS_MPC = _SP.get("mw_radius_mpc", 0.01594329)

# Etendue effective des vignettes, mesuree le 02/08 sur les frames f00 : rayon
# contenant 90 % du flux, en fraction du demi-cote.
#
# Les deux familles de sprites N'ONT PAS la meme echelle interne : 0,094 pour les
# vignettes 512, 0,344 pour la Voie lactee en 2048. Appliquer le meme facteur aux
# deux rendait la galaxie 3,7 fois trop petite sur les lignes servies par la
# vignette normale -- l'incoherence de taille signalee par Marc entre C/D et B/A.
#
# Le facteur est fige sur f00 et NE VARIE PAS avec la frame : c'est ainsi que
# l'etalement du sprite pendant la dissolution reste visible (C1).
SPRITE_EXTENT = _SP.get("extent_r90", {"normal": 0.094, "hires": 0.344})
# SPRITE_MARGIN historique : la vignette couvre 2,8 rayons galactiques. Valeur
# reprise de RealGalaxiesLayer.tsx et de generate_simulated_textures.mjs, ou elle
# est marquee « GARDER SYNCHRONISE ». Ma reconstruction par le rayon a 90 % du
# flux donnait 1,37, soit des sprites 1,4 fois trop grands et plus mous.
SPRITE_MARGIN = _SP.get("sprite_margin", 2.8)
PARTICLE_REACH = _SP.get("particle_reach", 1.37)  # etendue des particules, en unites de rayon galactique
                          # (mesure : max|x| = 71 235 ly pour mwRadius = 52 000)

# Attenuation du fond ambiant sur les lignes basses. Arbitrage de Marc du 02/08 :
# « le fond genere est beaucoup trop lumineux sur les layers A a D, on n'arrive
# pas a distinguer les galaxies du Groupe Local ». En descendant vers A, la toile
# cosmique n'a plus de sens physique -- a 0,035 Mpc on est DANS une galaxie. Le
# fond s'efface donc au profit des objets, ce qui sert aussi A8.
# Cible de ton propre aux lignes a sprites. Arbitrage de Marc du 03/08 : des que
# les galaxies du catalogue sont visibles, le fond doit s'effacer -- moyenne plus
# basse, filaments legers convergeant vers les galaxies. Les critères de fond
# (A7 a 68/255) ne s'appliquent plus tels quels sous G.
TARGET_MEAN_ROW = _SP.get("target_mean_row", {"G": 60.0, "F": 52.0, "E": 44.0,
                                              "D": 36.0, "C": 30.0, "B": 28.0,
                                              "A": 28.0})
AMBIENT_STRENGTH = _SP.get("ambient_strength", {"G": 0.55, "F": 0.42, "E": 0.32,
                                                "D": 0.22, "C": 0.14, "B": 0.09,
                                                "A": 0.06})
SPRITE_GAIN = _SP.get("gain", 30.0)
HIRES_BELOW = _SP.get("hires_below_half_mpc", 0.15)
SPRITE_FILE = {
    "Voie lactée": "milkyway", "Andromède (M31)": "andromede",
    "Triangulum (M33)": "triangulum", "Grand Nuage de Magellan": "lmc",
    "Petit Nuage de Magellan": "smc", "Naine du Sagittaire": "sagittaire",
    "NGC 6822": "ngc6822", "IC 10": "ic10", "Leo I": "leo1",
}


def frame_for(amp):
    """Indice de frame de dissolution pour une amplitude de structure.

    amp = 1 (colonne 10, aujourd'hui) -> f00, galaxie formee.
    amp = 0 (colonne 0, recombinaison) -> f13, dissoute.
    La racine donne une dissolution lente au debut puis rapide : les galaxies
    persistent le plus longtemps (C5).
    """
    a = float(np.clip(amp, 0.0, 1.0))
    return int(round((1.0 - a ** 0.5) * (N_FRAMES - 1)))


def load_sprite(name, amp, hires=False):
    from PIL import Image
    d = SPRITE_HIRES if hires else SPRITE_DIR
    f = os.path.join(d, "%s_f%02d.png" % (name, frame_for(amp)))
    if not os.path.exists(f):
        return None
    return np.asarray(Image.open(f).convert("L"), dtype=np.float32) / 255.0


def _paste(img, sp, cx, cy, diam_px, gain):
    """Depose un sprite redimensionne. Operateur purement lineaire."""
    n = img.shape[0]
    d = max(int(round(diam_px)), 2)
    if d > 4 * n:
        return 0
    # Spline cubique, et non bilineaire : c'est ce qui rend le PIQUE des sprites
    # historiques, rendus par drawImage. Le bilineaire les rendait mous.
    z = ndimage.zoom(sp, d / sp.shape[0], order=3)
    np.clip(z, 0.0, None, out=z)
    h = z.shape[0]
    x0, y0 = int(round(cx - h / 2)), int(round(cy - h / 2))
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    w = min(h - sx0, n - dx0)
    v = min(h - sy0, n - dy0)
    if w <= 0 or v <= 0:
        return 0
    img[dy0:dy0 + v, dx0:dx0 + w] += z[sy0:sy0 + v, sx0:sx0 + w] * gain
    return 1


def build(code, half, seed, base_img, fine, amp=1.0, ambient_half=None):
    """Construit une ligne a sprites a l'amplitude `amp`.

    `base_img` est la trame ambiante (texture de la premiere ligne generee,
    reechantillonnee) ; `fine` le champ fin HERITE de la ligne du dessus.
    """
    n = G.OUT_N
    px = 2.0 * half / n
    w_amb = AMBIENT_STRENGTH.get(code, 1.0)
    img, gm = G.apply_fine(np.maximum(base_img, 1e-6), code, fine)
    mean0 = float(img.mean())
    if w_amb < 1.0:
        # Le fond s'efface vers un plancher uniforme ; seules subsistent ses
        # zones les plus denses, qui entourent les galaxies. Operateur
        # PONCTUEL (aucun filtre spatial en aval du generateur).
        img = mean0 * (1.0 - w_amb) * 0.25 + img * w_amb

    with open(CATALOG) as fh:
        gals = json.load(fh)
    gals = [dict(name="Voie lactée", distanceMpc=0.0, radiusMpc=MW_RADIUS_MPC,
                 angleDeg=0.0, brightness=1.0, isReal=True)] + gals

    n_real = n_proc = 0
    for g in gals:
        th = np.radians(g["angleDeg"])
        X, Y = g["distanceMpc"] * np.cos(th), g["distanceMpc"] * np.sin(th)
        cx = (X / half * 0.5 + 0.5) * n
        cy = (0.5 - Y / half * 0.5) * n
        if not (-1.5 * n < cx < 2.5 * n and -1.5 * n < cy < 2.5 * n):
            continue
        key = SPRITE_FILE.get(g["name"])
        if key:
            # Sprite N-corps : il porte deja sa propre dissolution.
            hires = (key == "milkyway" and half < HIRES_BELOW)
            sp = load_sprite(key, amp, hires=hires)
            if sp is not None:
                frac = SPRITE_EXTENT["hires" if hires else "normal"]
                # Gain 30 calibre le 02/08 : la courbe de ton a gamma 0,45 comprime fortement
                # les hautes valeurs, un gain de 6 y disparaissait (pic local 170
                # contre 170 pour le fond seul). A 30 : 246 aujourd hui, 168 a la
                # dissolution totale, saturation 0,05 %.
                # Diametre de la vignette tel que le rayon a 90 % du flux tombe
                # sur PARTICLE_REACH rayons galactiques -- independant de la
                # famille de sprite, donc taille coherente d'une ligne a l'autre.
                d_px = 2.0 * SPRITE_MARGIN * g["radiusMpc"] / px
                if _paste(img, sp, cx, cy, d_px, mean0 * SPRITE_GAIN * g["brightness"]):
                    n_real += 1
                    continue
        # Galaxie procedurale : elle s'etale et palit avec l'amplitude, comme
        # les sprites -- C1 et C2 sans discontinuite entre les deux familles.
        spread = float(np.clip(amp, 0.05, 1.0)) ** -0.35
        r_px = max(g["radiusMpc"] / px * spread, 0.8)
        if r_px > 1.5 * n:
            continue
        y0, y1 = int(max(0, cy - 4 * r_px)), int(min(n, cy + 4 * r_px + 1))
        x0, x1 = int(max(0, cx - 4 * r_px)), int(min(n, cx + 4 * r_px + 1))
        if y1 <= y0 or x1 <= x0:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1]
        rr = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / r_px
        amp_g = g["brightness"] * float(np.clip(amp, 0.0, 1.0)) ** 1.2
        img[y0:y1, x0:x1] += (np.exp(-rr ** 1.4) * mean0 * 3.5 * amp_g).astype(np.float32)
        n_proc += 1

    # Ton cale sur la fenetre visible (cf. gen_chain.render_full).
    v = int(round(n / 1.5))
    c0 = (n - v) // 2
    a = M.solve_alpha(img[c0:c0 + v, c0:c0 + v] if c0 > 0 else img,
                      TARGET_MEAN_ROW.get(code, G.TARGET_MEAN), gamma=gm)
    return M.tone(img, a, gamma=gm), n_real, n_proc
