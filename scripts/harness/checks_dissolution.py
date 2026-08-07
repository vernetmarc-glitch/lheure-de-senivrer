"""PORTEE CONF — dissolubilite et resolution native.

Pourquoi ces controles passent AVANT les colonnes
-------------------------------------------------
T-036, T-037 et T-038 se verifient sur la ligne d'aujourd'hui, et ils decident si
les onze colonnes de l'axe du temps seront **du calcul** ou **une reprise de
conception**. Une composante sans loi temporelle bloque la colonne entiere — et
on ne s'en apercevrait qu'apres avoir tout cuit.

Ils ne mesurent pas une texture publiee : ils font tourner le generateur a
amplitude 1 puis a amplitude 0, en resolution reduite, et regardent ce qui reste.
C'est la seule facon de repondre a C15 (« l'etat d'amplitude nulle est
atteignable ») sans cuire 165 cellules pour le decouvrir.
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

from checks import MATRIX, ROOT, Result

sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))

N_TEST = 160          # resolution reduite : ces controles tournent a chaque
                      # cuisson, ils doivent couter quelques secondes.
ROW_TEST = "E"        # ligne du Groupe Local : sprites N-corps, galaxies
                      # procedurales et fond ambiant y coexistent tous les trois.
HALF_TEST = 1.4113


def _build(amp):
    """Construit la ligne d'essai a l'amplitude donnee, fond ambiant compris."""
    import gen_chain as G
    import sprites_layer as S
    old = G.OUT_N
    try:
        G.OUT_N = N_TEST
        G._calib_fine_norm()
        fine = G.fine_for(ROW_TEST, 4242 + 107, None, None, half=HALF_TEST)
        if fine.shape[0] != N_TEST:
            fine = ndimage.zoom(fine, N_TEST / fine.shape[0], order=1)
        # Fond volontairement PLAT : tout ce qui apparait dans l'image vient
        # alors des composantes, et non d'une trame heritee. On mesure ce que la
        # ligne AJOUTE, pas ce qu'elle recopie.
        base = np.full((N_TEST, N_TEST), 0.25, np.float32)
        tex, _, _ = S.build(ROW_TEST, HALF_TEST * 1.5, 107, base, fine, amp=amp)
        return np.asarray(tex, np.float64)
    finally:
        G.OUT_N = old


def _structure(a):
    """Ecart-type de la composante LISSEE : la structure, pas la grenaille.

    Le sigma brut a deja fait diagnostiquer de travers (voir
    `approches-ecartees.md`, « metriques ecartees ») : il stagnait a 41/255 meme
    dissous parce qu'il melangeait structure et bruit de tirage.
    """
    return float(ndimage.gaussian_filter(a, 3.0).std() * 255)


def dissolution_checks():
    out = []
    with open(MATRIX) as fh:
        m = json.load(fh)
    gen = m.get("generation", {})

    # ---- T-036 : chaque composante declare-t-elle une loi temporelle ? -----
    # C13. Une composante posee « en dur » ne pourra pas se dissoudre. Le
    # controle ne juge pas la loi, il exige qu'elle soit DECLAREE dans la
    # matrice — donc lisible, versionnee, et opposable.
    composantes = ["champ_fin", "halos", "ancrage", "sprites", "raccord"]
    lois = gen.get("lois_temporelles", {})
    sans = [c for c in composantes if c in gen and c not in lois]
    out.append(Result("T-036", "CONF", "chaque composante a une loi temporelle (C13)",
                      not sans,
                      "sans loi declaree : %s" % " ".join(sans) if sans
                      else "%d composantes" % len(composantes)))

    # ---- T-037 et T-038 : la dissolution se termine-t-elle vraiment ? ------
    try:
        a1, a0 = _build(1.0), _build(0.0)
    except Exception as e:
        for tid, lab in (("T-037", "l'etat d'amplitude nulle est atteignable (C15)"),
                         ("T-038", "la matiere dissoute retourne au champ (C14)")):
            out.append(Result(tid, "CONF", lab, False, str(e)[:60]))
        return out

    s1, s0 = _structure(a1), _structure(a0)
    # Diagnostic : QUELLE part de l'image bouge entre les deux amplitudes. Une
    # fraction minuscule signifie que la plupart des composantes ignorent
    # l'amplitude -- c'est-a-dire n'ont pas de loi temporelle.
    touche = float((np.abs(a1 - a0) > 0.004).mean())
    # C15 : a amplitude nulle plus AUCUNE composante ne subsiste comme
    # structure. Le grain subsiste (C8), les structures non. Le seuil est pris
    # en fraction de l'etat forme : exiger une valeur absolue reintroduirait une
    # dependance a la resolution.
    out.append(Result("T-037", "CONF", "l'etat d'amplitude nulle est atteignable (C15)",
                      s0 <= 0.15 * max(s1, 1e-9),
                      "structure %.2f -> %.2f /255 (%.0f %% restants), "
                      "%.1f %% des pixels bougent"
                      % (s1, s0, 100 * s0 / max(s1, 1e-9), 100 * touche)))

    # C14 : ce qui se defait REND sa matiere au champ, il ne s'ajoute pas
    # par-dessus. Si la luminosite totale s'effondre, la matiere a disparu ; si
    # elle explose, les composantes se sont empilees. Les deux empechent la
    # dissolution de se terminer.
    r = float(a0.mean() / max(a1.mean(), 1e-9))
    out.append(Result("T-038", "CONF", "la matiere dissoute retourne au champ (C14)",
                      0.85 <= r <= 1.15,
                      "luminosite moyenne x%.3f (%.1f -> %.1f /255)"
                      % (r, a1.mean() * 255, a0.mean() * 255)))
    return out


def resolution_checks(d):
    """T-025 et T-026 — le pique, origine 06/07/2026.

    « Recadrage de 8,5 px natifs agrandi x35 » : une texture agrandie au-dela
    d'un facteur raisonnable est floue quoi qu'on fasse en aval, et aucun reglage
    de rendu ne la rattrape.
    """
    import gen_chain as G
    import sprites_layer as S
    out = []

    # T-026 — la chaine travaille-t-elle a sa resolution native ?
    # Origine : pipeline en 512 sur des textures 1024. Ici : le champ fin, le
    # rendu et le fichier livre doivent partager la MEME grille.
    from PIL import Image
    tailles = set()
    for c in "ONMLKJIHGFEDCBA":
        p = os.path.join(d, "density_%s.png" % c)
        if os.path.exists(p):
            tailles.add(Image.open(p).size[0])
    attendu = int(round(G.OUT_N * G.RENDER_MARGIN))
    out.append(Result("T-026", "CONF", "traitement a la resolution native (A11)",
                      tailles == {attendu} and G.FINE_N == attendu,
                      "textures %s, champ fin %d, attendu %d"
                      % (sorted(tailles), G.FINE_N, attendu)))

    # T-025 — aucun sprite n'est agrandi au-dela du facteur admis.
    # La vignette source fait 512 px (2048 pour la Voie lactee en hires) ;
    # l'agrandir plus de 4 fois la rend molle, et c'est exactement ce qui s'est
    # produit le 06/07. Le calcul est purement geometrique : il n'exige aucune
    # cuisson et attrape le defaut AVANT qu'il ne soit visible.
    with open(S.CATALOG) as fh:
        gals = json.load(fh)
    gals = [dict(name="Voie lactée", distanceMpc=0.0, radiusMpc=S.MW_RADIUS_MPC)] + gals
    pire, ou = 0.0, ""
    for code, half in (("G", 8.9600), ("F", 3.5560), ("E", 1.4113),
                       ("D", 0.5601), ("C", 0.2223), ("B", 0.0882), ("A", 0.0350)):
        ext = half * 1.5
        px = 2.0 * ext / G.FINE_N
        for g in gals:
            key = S.SPRITE_FILE.get(g["name"])
            if not key:
                continue
            hires = (key == "milkyway" and ext < S.HIRES_BELOW)
            reach = S.HIRES_REACH if hires else S.SPRITE_MARGIN
            natif = 2048 if hires else 512
            d_px = 2.0 * reach * g["radiusMpc"] / px
            f = d_px / natif
            if f > pire:
                pire, ou = f, "%s / %s" % (code, g["name"])
    out.append(Result("T-025", "CONF", "agrandissement des sprites <= x4 (A11)",
                      pire <= 4.0, "pire cas x%.2f (%s)" % (pire, ou)))
    return out
