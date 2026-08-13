"""PORTEES CELL et PAIR — galaxies du catalogue, morphologie, signature.

Ce module complete `checks.py`. Il regroupe les controles qui ont besoin soit du
CATALOGUE du Groupe Local, soit de la SIGNATURE de reference — deux sources
externes a l'image, qu'il vaut mieux charger en un seul endroit.

Tous ces controles etaient DECLARES au registre depuis le 03/08/2026 sans code
correspondant. Ils n'etaient donc pas executes, et six d'entre eux transcrivent
des retours de Marc du 6 juillet : ce qui n'est pas execute se reperd.
"""
import json
import os

import numpy as np
from scipy import ndimage

from checks import DATA, ROOT, Result, SPRITE_ROWS, matrix, visible

CATALOG = os.path.join(DATA, "local_group_catalog.json")
MARGIN = 1.5

# Domaine de T-094 (D6b) : les lignes ou le catalogue est dans le cadre, donc ou
# « entre les galaxies » a un sens. Au-dessus de `I` le Groupe Local tient dans
# quelques pixels et le fond n'a plus de galaxies a separer.
CONTINUITE = set("IHGFEDCBA")

# Cible mesuree sur l'image de reference, docs/reference-visuelle.md.
# Les tolerances ci-dessous sont une PREMIERE CALIBRATION du 07/08/2026 : larges
# a dessein, pour que le controle demarre en disant la verite plutot qu'en
# echouant partout. Elles se resserrent, jamais l'inverse, et tout desserrage
# s'ecrit au registre.
CIBLE = {"moyenne": (67.5, 8.0), "isotropie": (0.97, 0.25),
         "creux": (-0.01, 0.35), "concentration": (0.239, 0.09),
         "elongation": (1.78, 0.45)}


def _catalog():
    with open(CATALOG) as fh:
        gals = json.load(fh)
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))
    import sprites_layer as S
    return [dict(name="Voie lactée", distanceMpc=0.0, radiusMpc=S.MW_RADIUS_MPC,
                 angleDeg=0.0, brightness=1.0)] + gals


def _positions(code, img):
    """Position en pixels des galaxies du catalogue, dans la texture complete.

    Meme convention que `sprites_layer.build` : la texture couvre +/- half*1,5.
    Toute divergence ici ferait echouer les controles de galaxies pour une
    mauvaise raison.
    """
    rows = matrix()["zoom_axis"]["rows"]
    n = img.shape[0]
    ext = rows[code]["halfwidth_mpc"] * MARGIN
    out = []
    for g in _catalog():
        th = np.radians(g["angleDeg"])
        X, Y = g["distanceMpc"] * np.cos(th), g["distanceMpc"] * np.sin(th)
        cx = (X / ext * 0.5 + 0.5) * n
        cy = (0.5 - Y / ext * 0.5) * n
        if 0 <= cx < n and 0 <= cy < n:
            out.append((g, cx, cy))
    return out


def _local_extent(img, cy, cx, rad=12):
    """Etendue apparente d'un objet autour d'un point : rayon a 60 % du flux
    excedentaire local. Mesure l'objet LIVRE, pas le parametre qui l'a produit."""
    n = img.shape[0]
    y0, y1 = int(max(0, cy - rad)), int(min(n, cy + rad + 1))
    x0, x1 = int(max(0, cx - rad)), int(min(n, cx + rad + 1))
    if y1 - y0 < 5 or x1 - x0 < 5:
        return 0.0
    p = img[y0:y1, x0:x1] - np.median(img)
    p = np.clip(p, 0, None)
    if p.sum() <= 0:
        return 0.0
    yy, xx = np.indices(p.shape)
    r = np.hypot(yy - (cy - y0), xx - (cx - x0)).ravel()
    w = p.ravel()
    o = np.argsort(r)
    c = np.cumsum(w[o])
    return float(r[o][np.searchsorted(c, 0.6 * c[-1])])


def _signature(v):
    """Cinq des dix grandeurs de la signature de reference.

    Les cinq retenues sont celles qui ne dependent NI de la taille de l'image NI
    d'une fenetre en pixels : elles restent comparables entre l'image de
    reference (464 px) et les textures (480 px). Les cinq autres — nettete,
    structures, saturations, P(filament)/P(grenaille) — sont deja portees par
    T-003, T-004, T-005 et T-028.
    """
    m = min(v.shape)
    u = v[:m, :m]
    a = (u - u.mean()) * np.hanning(m)[:, None] * np.hanning(m)[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    c = m // 2
    y, x = np.indices(F.shape)
    dy, dx = y - c, x - c
    r = np.hypot(dy, dx)
    A = np.abs(np.degrees(np.arctan2(dy, dx)))
    ang = np.minimum(A, 180 - A)
    b = (r > 3) & (r < m * 0.45)
    iso = float(F[b & ((ang < 12) | (ang > 78))].mean()
                / F[b & (np.abs(ang - 45) < 20)].mean())
    h, _ = np.histogram(u, bins=48, range=(0, 1))
    h = h / h.sum()
    lg = np.log10(h + 1e-9)
    dip = float(min(lg[3:8].max(), lg[34:].max()) - lg[6:34].min())
    s = np.sort(u.ravel())[::-1]
    conc = float(s[:int(.1 * s.size)].sum() / s.sum())
    return {"moyenne": float(u.mean()) * 255, "isotropie": iso,
            "creux": dip, "concentration": conc,
            "elongation": _elongation(u)}


def _elongation(u):
    """Elongation mediane des structures brillantes. Reference : 1,78.

    C'est la grandeur qui separe une TOILE d'une MOUSSE. Attention : elle ne
    suffit pas seule — la mousse rejetee le 28/07 mesurait 1,87 — mais une
    valeur basse disqualifie a coup sur.
    """
    bw = u > np.percentile(u, 88)
    lbl, _ = ndimage.label(bw)
    el = []
    for sl in ndimage.find_objects(lbl):
        sub = lbl[sl] > 0
        ys, xs = np.nonzero(sub)
        if len(ys) < 6:
            continue
        cv = np.cov(np.stack([ys, xs]).astype(float))
        ev = np.sort(np.linalg.eigvalsh(cv))[::-1]
        if ev[0] > 1e-9:
            el.append(np.sqrt(max(ev[1], 0) / ev[0]))
    return float(1.0 / np.median(el)) if el else 1.0


# ===========================================================================
def image_cell_checks(code, img, m):
    out = []
    v = visible(img)
    sp = code in SPRITE_ROWS
    med = float(np.median(v))

    # ---- T-028 : toile, pas mousse. Origine 28/07, « impression de mousse ».
    # REARME sur les lignes homogenes le 07/08/2026, au soir.
    #
    # Le matin, T-028 et T-029 avaient ete EXCLUS des lignes `L` a `O` au motif
    # que B8 les declare homogenes. Cette exclusion reposait sur l'ancienne
    # lecture de B10 -- « rien ne doit s'y detacher » -- qui a ete corrigee
    # depuis : l'uniformite exigee aux grandes echelles est GEOMETRIQUE, pas
    # photometrique. La matiere y reste repartie en FILAMENTS, seulement avec des
    # contrastes plus faibles.
    #
    # Consequence de l'exclusion : le seul defaut que Marc voyait a l'oeil --
    # « ca ressemble plus a de la mousse avec des blobs de haute luminosite poses
    # les uns a cote des autres de maniere assez reguliere » -- etait porte par
    # une exigence ecrite (A2, A5), couvert par deux controles existants, et
    # pourtant indetectable, parce que ces deux controles etaient eteints
    # exactement la ou le defaut se trouvait.
    #
    # Une exclusion de portee est aussi dangereuse qu'un seuil desserre, et elle
    # est plus discrete : rien ne s'affiche en rouge.
    if not sp:
        # ATTENTION — T-028 NE DISCRIMINE PAS mousse et toile.
        # `docs/approches-ecartees.md` le dit noir sur blanc depuis le 28/07 :
        # « Elongation globale des nuages : ne discrimine pas mousse et toile
        # (1,87 contre 1,78 pour la reference) ». La metrique y figure parmi les
        # METRIQUES ECARTEES, et T-028 a pourtant ete construit dessus le 07/08.
        # Il mesure 4,26 a la ligne `O` alors que Marc y voit « de la mousse avec
        # des blobs poses les uns a cote des autres ».
        # Il est GARDE comme garde-fou minimal -- une valeur basse disqualifie a
        # coup sur -- mais il ne vaut pas preuve. Ce sont T-029, T-052 et T-078
        # qui portent le critere.
        el = _elongation(v)
        out.append(Result("T-028", "CELL", "elongation minimale, NE PROUVE RIEN (A2)",
                          el >= 1.45, "%s %.2f  (indicatif seulement)" % (code, el)))

        # ---- T-029 : les points sont SUR les filaments, pas au hasard.
        # Mesure : la fraction des pixels les plus brillants qui appartiennent a
        # une composante allongee. Un champ de points aleatoires donne des
        # composantes rondes ; une toile les donne etirees.
        bw = v > np.percentile(v, 97)
        lbl, k = ndimage.label(bw)
        good = tot = 0
        for i, sl in enumerate(ndimage.find_objects(lbl), start=1):
            sub = lbl[sl] == i
            ys, xs = np.nonzero(sub)
            if len(ys) < 6:
                continue
            tot += len(ys)
            cv = np.cov(np.stack([ys, xs]).astype(float))
            ev = np.sort(np.linalg.eigvalsh(cv))[::-1]
            if ev[0] > 1e-9 and np.sqrt(max(ev[1], 0) / ev[0]) <= 0.66:
                good += len(ys)
        fr = good / max(tot, 1)
        # DOMAINE DE VALIDITE (D-30, 08/08/2026). A5 suppose qu'il y ait des
        # filaments. La bande disponible est bornee en bas par Nyquist et en
        # haut par B5 ; a `O`, ou un pixel vaut 91 Mpc, il ne reste que 1,26
        # octave, et aucune image ne peut y porter une toile sans inventer des
        # structures au-dela de l'echelle d'homogeneite.
        #
        # PRECAUTION, apprise le 07/08 : ce jour-la, T-028 et T-029 avaient ete
        # eteints sur `L`->`O` et le defaut que Marc voyait a l'oeil etait
        # devenu indetectable, parce que les controles etaient eteints
        # exactement la ou il se trouvait. « Une exclusion de portee est aussi
        # dangereuse qu'un seuil desserre, et elle est plus discrete : rien ne
        # s'affiche en rouge. »
        #
        # Trois differences avec ce jour-la, et elles sont ce qui rend la borne
        # acceptable : elle ne retire QUE `O` et non quatre lignes ; elle est
        # calculee d'une impossibilite arithmetique, pas supposee ; et elle
        # AFFICHE une ligne dans le rapport au lieu de disparaitre. T-028 reste
        # arme partout comme garde-fou.
        rr = m["zoom_axis"]["rows"][code]
        hg = m["generation"]["champ_fin"]["homogeneity_mpc"]
        pxq = 2.0 * rr["halfwidth_mpc"] / v.shape[0]
        if np.log2(max(hg * 1.8 / pxq, 2.21) / 2.2) >= 2.0:
            out.append(Result("T-029", "CELL", "points repartis le long des filaments (A5)",
                              fr >= 0.45, "%s %.0f %% sur structures allongees"
                              % (code, 100 * fr)))
        else:
            out.append(Result("T-029b", "CELL",
                              "A5 hors domaine : pas de toile a cette echelle (B8)",
                              True, "%s bande disponible < 2 octaves ; "
                              "mesure indicative %.0f %% allonge" % (code, 100 * fr)))

    # ---- T-033 : une seule population de matiere, pas deux calques.
    # Origine 28/07 : « il n'y a pas de continuite d'aspect entre les points
    # blancs et les nuages ». Un creux dans l'histogramme = deux populations.
    h, _ = np.histogram(v, bins=48, range=(0, 1))
    h = h / max(h.sum(), 1)
    lg = np.log10(h + 1e-9)
    dip = float(min(lg[3:8].max(), lg[34:].max()) - lg[6:34].min())
    out.append(Result("T-033", "CELL", "continuite points brillants / fond (A6)",
                      dip >= -0.40, "%s creux %.2f" % (code, dip)))

    # ---- T-034 : une galaxie ne flotte pas sur du vide (A8). Le fond
    # filamentaire doit exister AUSSI sous G. Mesure hors voisinage des
    # galaxies, sinon on mesure les galaxies elles-memes.
    if sp:
        mask = np.ones(v.shape, bool)
        n = v.shape[0]
        off = (img.shape[0] - n) // 2
        rows_m = matrix()["zoom_axis"]["rows"]
        px_m = 2.0 * rows_m[code]["halfwidth_mpc"] * MARGIN / img.shape[0]
        # Rayon d'exclusion PROPORTIONNEL a la taille apparente de chaque
        # galaxie, jamais un nombre de pixels fixe.
        #
        # La premiere ecriture masquait 10 px autour de chaque objet. A la ligne
        # `A`, la Voie lactee fait 72 px de rayon : on mesurait donc la GALAXIE
        # en croyant mesurer le fond, et T-077 y rendait 0,78 pour un plafond a
        # 0,60. Un rayon en pixels represente une distance physique differente a
        # chaque ligne -- c'est le piege documente « unites comobiles, jamais en
        # pixels », septieme occurrence, et cette fois dans le harnais lui-meme.
        for g, cx, cy in _positions(code, img):
            r_px = max(3.0, 2.5 * g["radiusMpc"] / px_m)
            yy, xx = np.ogrid[0:n, 0:n]
            mask &= np.hypot(yy - (cy - off), xx - (cx - off)) > r_px
        if mask.sum() > 100:
            # A8 precisee le 07/08 par Marc. « Le fond s'efface » etait lu comme
            # un fondu vers l'uniforme ; l'intention est une attenuation
            # RELATIVE AUX GALAXIES, avec des nuages filamentaires qui
            # subsistent. Trois clauses distinctes, a satisfaire ENSEMBLE : un
            # fond lisse jusqu'a l'uniforme echoue la deuxieme, un fond conserve
            # tel quel echoue la troisieme.
            fond = float(ndimage.gaussian_filter(v, 2.0)[mask].std() * 255)
            # Clause 2 — des nuages FILAMENTAIRES, ni uniforme ni grain sans
            # forme. On mesure l'elongation du fond seul, les galaxies remplacees
            # par la mediane du fond pour ne pas peser dans le calcul.
            u = np.where(mask, v, float(np.median(v[mask])))
            el = _elongation(u)
            out.append(Result("T-034", "CELL", "nuages filamentaires subsistants (A8)",
                              fond >= 1.5 and el >= 1.45,
                              "%s %.2f /255, elongation %.2f" % (code, fond, el)))
            # Clause 3 — AUCUNE zone de haute luminosite hors galaxies. Le pic du
            # fond doit rester nettement sous celui des objets du catalogue.
            # Mesure du 07/08 : 220 contre 245 sur `G`, et 118 contre 108 sur
            # `E` -- le fond y etait PLUS BRILLANT que les galaxies.
            if (~mask).any():
                pic_gal = float(v[~mask].max())
                pic_fond = float(np.percentile(v[mask], 99.9))
                r = pic_fond / max(pic_gal, 1e-9)
                out.append(Result("T-077", "CELL",
                                  "rien d'aussi brillant que les galaxies (A8)",
                                  r <= 0.60, "%s pic fond %.0f / pic galaxies %.0f"
                                  " = %.2f" % (code, pic_fond * 255, pic_gal * 255, r)))

    # ---- T-027 : signature de reference sur les lignes K -> H.
    if code in ("K", "J", "I", "H"):
        sig = _signature(v)
        bad = ["%s %.3f" % (k, sig[k]) for k, (c, t) in CIBLE.items()
               if abs(sig[k] - c) > t]
        out.append(Result("T-027", "CELL", "signature de reference (A1)",
                          not bad, "%s %s" % (code, " ".join(bad) if bad
                                              else "5 grandeurs conformes")))

    # ---- Galaxies du catalogue -------------------------------------------
    pos = _positions(code, img)
    if sp and pos:
        # T-015 — position juste. Chaque galaxie doit produire un exces LOCAL
        # de lumiere a ses coordonnees, a 3 px pres. Origine 06/07.
        rows_ = matrix()["zoom_axis"]["rows"]
        px = 2.0 * rows_[code]["halfwidth_mpc"] * MARGIN / img.shape[0]
        # Un objet sous-pixellaire ne peut pas etre LOCALISE : l'absence d'exces
        # a ses coordonnees ne dit rien de la justesse de sa position. On ne
        # desserre pas le seuil, on retire de la mesure ce qu'elle ne sait pas
        # mesurer.
        vus = [(g, cx, cy) for g, cx, cy in pos if g["radiusMpc"] / px >= 0.5]
        rate = []
        for g, cx, cy in vus:
            y0, y1 = int(max(0, cy - 3)), int(min(img.shape[0], cy + 4))
            x0, x1 = int(max(0, cx - 3)), int(min(img.shape[0], cx + 4))
            rate.append(float(img[y0:y1, x0:x1].max()) > med * 1.15)
        fr = sum(rate) / max(len(rate), 1)
        out.append(Result("T-015", "CELL", "positions conformes au catalogue (D7)",
                          fr >= 0.90 and rate, "%s %d/%d galaxies resolues retrouvees"
                          % (code, sum(rate), len(rate))))

        # T-016 — le rapport des tailles apparentes suit celui des rayons
        # reels. Origine 06/07 : « je n'ai pas l'impression que le diametre
        # apparent des galaxies et leur distance soit coherent ».
        #
        # REECRIT le 08/08/2026, apres passage au banc. L'ancienne version
        # retenait TOUTE position du catalogue ou `_local_extent` rendait une
        # valeur non nulle -- or sur une texture reelle le fond en rend une
        # partout. Sur `G`, ou UNE SEULE galaxie du catalogue depasse le demi
        # pixel, le controle correlait donc 25 taches de FOND contre leurs
        # rayons catalogue. La correlation negative qu'il rapportait ne parlait
        # pas des galaxies. Sixieme controle trouve faux sur ce projet.
        #
        # Trois corrections, toutes de la meme famille -- ne mesurer que ce qui
        # est mesurable, plutot que desserrer un seuil :
        #   1. l'objet doit etre RESOLU (rayon >= 0,5 px), comme dans T-015 ;
        #   2. il doit produire un EXCES LOCAL, sinon il n'est pas dans l'image ;
        #   3. fenetre de mesure et rayon de garde PROPORTIONNELS a l'objet,
        #      jamais 12 et 24 px fixes -- un seuil en pixels sur une echelle
        #      geometrique ecarte tout sur une ligne et rien sur la suivante.
        # MESURE : le rapport etendue apparente / rayon vrai en pixels. Il doit
        # etre le MEME pour tous les objets, quelle que soit la ligne -- c'est
        # exactement ce que « diametre apparent coherent avec la distance »
        # veut dire. La borne est une CONSTANTE ABSOLUE, jamais une statistique
        # de l'image courante (INV-B1).
        #
        # Calibration du 08/08 sur les quinze textures cuites : le rapport vaut
        # 2,34 a 2,68 pour tout objet resolu, et il vaut cela AUSSI BIEN pour la
        # Voie lactee en vignette 2048 que pour les vignettes 512 -- preuve que
        # la compensation SPRITE_MARGIN / HIRES_REACH est juste. Bande retenue :
        # [1,8 ; 3,4].
        #
        # SEUIL DE RESOLUTION : 3,5 px, et non 0,5. Mesure du 08/08 : sous
        # ~4 px, `_local_extent` rend systematiquement 8 a 10 px, c'est-a-dire
        # la taille de sa propre fenetre et du fond qui la remplit -- rapports
        # apparents de 9, 12, 14. Ce n'etait pas la galaxie qui etait mesuree.
        # Un controle se tait plutot que de rendre un chiffre qui ne veut rien
        # dire ; les lignes ou aucun objet n'est resolu restent couvertes par
        # T-015 (positions) et T-012 (croissance d'un objet nomme).
        BANDE = (1.8, 3.4)
        mesures = []
        for g, cx, cy in pos:
            if g["radiusMpc"] <= 0:
                continue
            r_px = g["radiusMpc"] / px
            if r_px < 3.5:
                continue
            garde = max(12.0, 4.0 * r_px)
            if any(np.hypot(cy - y2, cx - x2) < garde
                   for h, x2, y2 in pos if h is not g):
                continue
            e = _local_extent(img, cy, cx, rad=max(10, int(3.0 * r_px)))
            if e > 0:
                mesures.append((g.get("name") or "proc", e / r_px))
        if mesures:
            hors = ["%s %.2f" % (n, k) for n, k in mesures
                    if not (BANDE[0] <= k <= BANDE[1])]
            out.append(Result("T-016", "CELL", "tailles apparentes ~ rayons reels (D7/A9)",
                              not hors,
                              "%s rapport %s sur %d objet(s) resolu(s)%s"
                              % (code, " ".join("%.2f" % k for _, k in mesures),
                                 len(mesures),
                                 "  HORS BANDE : " + " ".join(hors[:3]) if hors else "")))

        # T-018 — halo de raccord present autour de chaque galaxie (A10) : la
        # lumiere ne doit pas s'arreter net au bord de la vignette.
        # Fenetres proportionnelles a l'objet, jamais en pixels fixes : une
        # fenetre absolue mesure une taille physique differente a chaque ligne,
        # piege deja tombe cinq fois (voir « metriques ecartees »).
        halos = []
        for g, cx, cy in pos:
            r0 = max(g["radiusMpc"] / px, 1.5)
            # Si la couronne de mesure deborde du cadre, il n'y a pas de halo a
            # mesurer : l'objet remplit l'image. Cas de la Voie lactee sur `A`.
            if r0 * 5 > img.shape[0] / 2:
                continue
            c = _local_extent(img, cy, cx, rad=int(round(r0 * 1.5)))
            l = _local_extent(img, cy, cx, rad=int(round(r0 * 5)))
            if c > 0:
                halos.append(l / c)
        if halos:
            hm = float(np.median(halos))
            out.append(Result("T-018", "CELL", "halo de raccord present (A10)",
                              hm >= 1.5, "%s etalement median x%.2f" % (code, hm)))

        # T-019 — la Voie lactee ne recouvre aucune galaxie plus proche.
        # Origine 06/07. Elle est au centre ; son rayon apparent doit rester
        # inferieur a la distance de sa plus proche voisine visible.
        # A10 dit « la Voie lactee dessinee DESSOUS ». L'exigence n'est pas
        # qu'elle ne chevauche personne -- ses satellites sont physiquement dans
        # son halo -- mais qu'une galaxie situee dans son disque apparent reste
        # VISIBLE par-dessus. Une premiere ecriture testait le non-recouvrement
        # et echouait sur quatre lignes en signalant « voisine a 0,4 px », ce qui
        # decrit notre voisinage reel et non un defaut de rendu.
        mw = [p for p in pos if (p[0].get("name") or "").startswith("Voie")]
        others = [p for p in pos if not (p[0].get("name") or "").startswith("Voie")]
        if mw and others:
            _, mx, my = mw[0]
            rmw = max(_local_extent(img, my, mx, rad=40), 2.0)
            dedans = [(g, cx, cy) for g, cx, cy in others
                      if np.hypot(cy - my, cx - mx) <= rmw
                      and g["radiusMpc"] / px >= 0.5]
            noyees = []
            for g, cx, cy in dedans:
                y0, y1 = int(max(0, cy - 2)), int(min(img.shape[0], cy + 3))
                x0, x1 = int(max(0, cx - 2)), int(min(img.shape[0], cx + 3))
                loc = float(img[y0:y1, x0:x1].max())
                y0, y1 = int(max(0, cy - 9)), int(min(img.shape[0], cy + 10))
                x0, x1 = int(max(0, cx - 9)), int(min(img.shape[0], cx + 10))
                if loc <= float(np.median(img[y0:y1, x0:x1])) * 1.05:
                    noyees.append(g.get("name") or "naine")
            out.append(Result("T-019", "CELL", "la Voie lactee est dessinee dessous (A10)",
                              not noyees, "%s %d galaxie(s) dans son disque, %s"
                              % (code, len(dedans),
                                 "noyees : " + " ".join(noyees[:3]) if noyees
                                 else "toutes visibles")))

    # ---- T-023 : les galaxies sont des centres de gravite (D6) -------------
    # Sur la premiere ligne generee, les filaments doivent CONVERGER vers les
    # positions du catalogue. Mesure : la densite y depasse la mediane de la
    # ligne. Origine 31/07, formulee par Marc.
    if code == "H" and pos:
        # T-023 — REECRIT le 10/08/2026, D6c allegee par Marc.
        #
        # Ce que l'ancienne version pretendait, et ne mesurait pas
        # --------------------------------------------------------
        # Elle exigeait 70 % des positions au-dessus de la mediane, en
        # echantillonnant UN SEUL PIXEL par galaxie. D6 demandait que les
        # filaments CONVERGENT VERS les positions ; un pixel unique mesure la
        # COINCIDENCE, pas la convergence. Cinquieme controle trouve mesurant
        # autre chose que ce qu'il cite.
        #
        # Et surtout : le controle n'avait PAS DE TEMOIN. Le nuage du catalogue
        # translate au hasard 300 fois sur la meme texture rend 50 % +- 18
        # points. Les 36 % mesures sont donc a 0,8 sigma du hasard -- du bruit,
        # pas un signal. Le seuil de 70 % exigeait 1,1 sigma AU-DESSUS du hasard
        # sans que rien ne dise que le generateur puisse l'atteindre : mesure
        # faite, il ne le peut a aucun rayon de voisinage (a 7 px le temoin
        # atteint lui aussi 99 % et le controle ne prouve plus rien).
        #
        # Ce que la version ci-dessous affirme, et ce qu'elle n'affirme pas
        # ----------------------------------------------------------------
        # Elle GARDE contre l'anti-correlation : les galaxies ne doivent pas
        # tomber du cote rarefie de la toile. Elle NE PROUVE PAS la convergence,
        # et ne doit pas etre lue comme telle -- la charge de D6 est portee par
        # T-094 (D6b). Le seuil est relatif au temoin et non absolu : il suit
        # donc la texture au lieu de dependre d'un chiffre fige.
        rows = m["zoom_axis"]["rows"]
        n = img.shape[0]
        cx = np.array([p[1] for p in pos])
        cy = np.array([p[2] for p in pos])
        fr = float(np.mean([img[int(b), int(a)] > med for a, b in zip(cx, cy)]))
        rng = np.random.default_rng(20260810)
        t = []
        for d in rng.integers(-int(0.42 * n), int(0.42 * n), (300, 2)):
            a = np.clip(cx + d[0], 0, n - 1).astype(int)
            b = np.clip(cy + d[1], 0, n - 1).astype(int)
            t.append(float((img[b, a] > med).mean()))
        t = np.array(t)
        seuil = float(t.mean() - t.std())
        out.append(Result("T-023", "CELL",
                          "pas d'anti-correlation avec la toile (D6c)",
                          fr >= seuil,
                          "%s %.0f %% au-dessus de la mediane sur %d, temoin "
                          "%.0f %% +- %.0f, plancher %.0f %%"
                          % (code, 100 * fr, len(cx), 100 * t.mean(),
                             100 * t.std(), 100 * seuil)))
    return out


# ===========================================================================
def image_pair_checks(pc, cc, pimg, cimg, m):
    out = []
    rows = matrix()["zoom_axis"]["rows"]
    ratio = rows[pc]["halfwidth_mpc"] / rows[cc]["halfwidth_mpc"]
    vp, vc = visible(pimg), visible(cimg)

    # ---- T-035 : l'arete G|H, la charnière la plus fragile ----------------
    # C'est le SEUL endroit de l'echelle ou sprites et densite se comparent cote
    # a cote, donc le seul endroit ou D1 est verifiable. Meme ton, meme densite
    # apparente.
    if (pc, cc) == ("H", "G"):
        dt = abs(vp.mean() - vc.mean()) * 255
        dc = abs(vp.std() / max(vp.mean(), 1e-9) - vc.std() / max(vc.mean(), 1e-9))
        out.append(Result("T-035", "PAIR", "fluidite a l'arete G|H (D1)",
                          dt <= 12.0 and dc <= 0.20,
                          "ton %.1f /255, contraste %.2f" % (dt, dc)))

    # ---- T-094 : la matiere entre les galaxies ne chute pas (D6b) ----------
    # AJOUTE le 10/08/2026, sur reformulation de D6 par Marc : « il ne faut pas
    # qu'il y en ait trop entre les galaxies sur les layers superieurs, sinon on
    # aura l'impression que de la matiere disparait en zoomant sur les galaxies ».
    #
    # C'est la clause qui porte reellement D6 depuis que D6c est allegee. La
    # grandeur est le CONTRASTE DU FOND HORS VOISINAGE DES GALAXIES : la moyenne
    # seule ne voit pas le defaut (elle ne descend que de 12 % a l'arete `H|G`)
    # alors que le contraste y perd 36 % et le pic 42 %.
    #
    # Mesure du 10/08 sur cuisson fraiche : `I`->`H` 1,04 · `H`->`G` **0,64** ·
    # `G`->`F` 0,84 · `F`->`E` 0,93 · `E`->`D` 0,97 · `D`->`C` 0,88. L'arete
    # `H|G` est la seule hors bande -- c'est la charniere ou la trame change de
    # mecanisme, et c'est exactement celle que Marc decrit.
    if pc in CONTINUITE and cc in CONTINUITE:
        def fond_contraste(code, im):
            u = visible(im)
            n = u.shape[0]
            off = (im.shape[0] - n) // 2
            px_m = 2.0 * rows[code]["halfwidth_mpc"] / n
            msk = np.ones(u.shape, bool)
            yy, xx = np.ogrid[0:n, 0:n]
            for g, gx, gy in _positions(code, im):
                r_px = max(3.0, 2.5 * g["radiusMpc"] / px_m)
                msk &= np.hypot(yy - (gy - off), xx - (gx - off)) > r_px
            if msk.sum() < 100:
                return float("nan")
            w = ndimage.gaussian_filter(u, 2.0)[msk]
            return float(w.std() / max(w.mean(), 1e-9))
        ap, ac = fond_contraste(pc, pimg), fond_contraste(cc, cimg)
        rap = ac / max(ap, 1e-9)
        out.append(Result("T-094", "PAIR",
                          "la matiere entre les galaxies ne chute pas (D6b/D6)",
                          rap >= 0.75,
                          "%s->%s contraste du fond %.3f -> %.3f, rapport %.2f"
                          % (pc, cc, ap, ac, rap)))

    # ---- T-039 : effet fractal dans la fenetre D -> J ---------------------
    # B4, borne a sa fenetre de validite : hors de 0,1-150 Mpc l'univers n'est
    # pas auto-similaire, et l'exiger reviendrait a representer un univers qui
    # n'existe pas. Mesure : l'enfant doit porter autant d'energie haute
    # frequence que son parent — sinon le zoom delave au lieu de preciser.
    FENETRE = set("DEFGHIJ")
    if pc in FENETRE and cc in FENETRE:
        def hf(u):
            a = u - u.mean()
            P = np.abs(np.fft.rfft2(a)) ** 2
            n = a.shape[0]
            ky = np.fft.fftfreq(n)[:, None] * n
            kx = np.fft.rfftfreq(n)[None, :] * n
            k = np.sqrt(ky ** 2 + kx ** 2)
            return float(P[k > n / 8.0].sum() / max(P[k > 0].sum(), 1e-12))
        rp, rc = hf(vp), hf(vc)
        out.append(Result("T-039", "PAIR", "effet fractal dans la fenetre D->J (B4)",
                          rc >= 0.70 * rp, "%s->%s %.3f -> %.3f"
                          % (pc, cc, rp, rc)))

    # ---- T-017 : aucune galaxie visible ne disparait au palier suivant ----
    # Origine 06/07 : « la Voie lactee disparait completement et il n'y a plus
    # de points lumineux au centre quand on voit les galaxies peripheriques ».
    if pc in SPRITE_ROWS and cc in SPRITE_ROWS:
        medp, medc = float(np.median(pimg)), float(np.median(cimg))
        # Les 90 galaxies procedurales du catalogue n'ont pas de nom (O-05,
        # question ouverte) : on les identifie par leurs coordonnees polaires.
        def _cle(g):
            return g.get("name") or "%.4f@%.2f" % (g["distanceMpc"], g["angleDeg"])
        pp = {_cle(g): (cx, cy) for g, cx, cy in _positions(pc, pimg)}
        cp = {_cle(g): (cx, cy) for g, cx, cy in _positions(cc, cimg)}
        perdues = []
        for nom, (cx, cy) in pp.items():
            if nom not in cp:
                continue                      # sortie du cadre : legitime
            y0, y1 = int(max(0, cy - 3)), int(min(pimg.shape[0], cy + 4))
            x0, x1 = int(max(0, cx - 3)), int(min(pimg.shape[0], cx + 4))
            if float(pimg[y0:y1, x0:x1].max()) <= medp * 1.15:
                continue                      # pas visible chez le parent
            cx2, cy2 = cp[nom]
            y0, y1 = int(max(0, cy2 - 4)), int(min(cimg.shape[0], cy2 + 5))
            x0, x1 = int(max(0, cx2 - 4)), int(min(cimg.shape[0], cx2 + 5))
            if float(cimg[y0:y1, x0:x1].max()) <= medc * 1.15:
                perdues.append(nom)
        out.append(Result("T-017", "PAIR", "aucune galaxie ne disparait (D8)",
                          not perdues, "%s->%s %s" % (pc, cc,
                          " ".join(perdues[:3]) if perdues else "aucune perdue")))

        # ---- T-012 : UN OBJET NOMME grandit au rythme du zoom (D7/A9) -----
        # Reecriture du 08/08/2026. L'ancienne version mesurait une statistique
        # globale de l'image et etait AVEUGLE a une croissance parfaite de
        # x2,520 sur douze paires sur quatorze (banc de falsification T-079).
        #
        # Ce qu'on mesure ici : la MEME galaxie du catalogue, retrouvee dans les
        # deux lignes par son nom, doit voir son etendue apparente multipliee
        # par le rapport des demi-champs. C'est ce que protegeait l'exigence
        # d'origine — la Voie lactee passee de 13 % a 47 % du cadre (03/08) —
        # et c'est mesurable parce que l'objet, lui, a une identite.
        #
        # La fenetre de mesure suit l'objet : `rad` proportionnel a la taille
        # attendue, jamais 12 px fixes, sinon la fenetre ecrete l'enfant et
        # fabrique elle-meme l'echec qu'elle pretend detecter.
        pparents = _positions(pc, pimg)
        pg = {_cle(g): (g, cx, cy) for g, cx, cy in pparents}
        cg = {_cle(g): (g, cx, cy) for g, cx, cy in _positions(cc, cimg)}
        pxp = 2.0 * rows[pc]["halfwidth_mpc"] * MARGIN / pimg.shape[0]
        pxc = 2.0 * rows[cc]["halfwidth_mpc"] * MARGIN / cimg.shape[0]
        rr = []
        for nom in set(pg) & set(cg):
            g, cxp, cyp = pg[nom]
            _, cxc, cyc = cg[nom]
            if g["radiusMpc"] <= 0:
                continue
            # Un objet sous-pixellaire chez le PARENT n'a pas d'etendue
            # mesurable : son absence de croissance ne dit rien. On le retire de
            # la mesure plutot que de desserrer le seuil.
            if g["radiusMpc"] / pxp < 0.5:
                continue
            # La fenetre enfant est celle du parent MULTIPLIEE PAR LE RAPPORT,
            # jamais recalculee avec son propre plancher. Le banc T-079 a montre
            # le 08/08 que `max(12, 3*r/px)` des deux cotes donne la MEME fenetre
            # de 12 px quand l'objet est petit dans les deux lignes : la mesure
            # est alors ecretee a l'identique et ne peut plus voir aucune
            # croissance. Reponse au temoin positif : 0,64 au lieu de 1,00.
            radp = max(10, int(3.0 * g["radiusMpc"] / pxp))
            radc = int(round(radp * ratio))
            # Voisin proche : on mesurerait deux objets pour un. Le rayon de
            # garde suit la FENETRE DE MESURE, jamais 24 px fixes -- un seuil en
            # pixels sur une echelle geometrique ecarte tout sur une ligne et
            # rien sur la suivante (piege des unites).
            if any(np.hypot(cyp - y2, cxp - x2) < radp
                   for h, x2, y2 in pparents if h is not g):
                continue
            ep = _local_extent(pimg, cyp, cxp, rad=radp)
            ec = _local_extent(cimg, cyc, cxc, rad=radc)
            if ep > 0 and ec > 0:
                rr.append((nom, ec / (ep * ratio)))
        if len(rr) >= 2:
            med = float(np.median([v for _, v in rr]))
            hors = [n for n, v in rr if not (0.70 <= v <= 1.45)]
            out.append(Result("T-012", "PAIR",
                              "un objet grandit au rythme du zoom (D7/A9)",
                              not hors, "%s->%s mediane x%.2f sur %d objet(s)%s"
                              % (pc, cc, med, len(rr),
                                 "  hors : " + " ".join(hors[:3]) if hors else "")))
    return out


# ===========================================================================
# T-079 — LE BANC DE FALSIFICATION
# ===========================================================================
def _zoom_center(a, r):
    """Recadrage central x`r` + agrandissement. Purement lineaire.

    Applique a la texture d'une ligne avec `r` = rapport des demi-champs, cela
    fabrique EXACTEMENT ce qu'une ligne fille devrait etre si tous ses objets
    grandissaient au rythme du zoom et qu'aucun objet nouveau n'apparaissait.
    """
    n = a.shape[0]
    w = n / r
    c0 = (n - w) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return ndimage.map_coordinates(a, np.stack([c0 + yy * w / n, c0 + xx * w / n]),
                                   order=3, mode="nearest")


def _synth_row(code, n, sigma_code=None):
    """Image d'essai : une gaussienne par galaxie du catalogue, rien d'autre.

    `code` fixe la FENETRE (donc les positions) ; `sigma_code` fixe la TAILLE
    des objets. Les separer est tout l'interet du banc : en donnant a l'enfant
    la fenetre de sa ligne mais la taille d'objet de sa mere, on fabrique une
    image ou les objets N'ONT PAS GRANDI, sans rien changer d'autre.
    """
    rows = matrix()["zoom_axis"]["rows"]
    ext = rows[code]["halfwidth_mpc"] * MARGIN
    px_pos = 2.0 * ext / n
    px_sig = 2.0 * rows[sigma_code or code]["halfwidth_mpc"] * MARGIN / n
    img = np.full((n, n), 0.20, np.float64)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    for g in _catalog():
        if g["radiusMpc"] <= 0:
            continue
        th = np.radians(g["angleDeg"])
        X, Y = g["distanceMpc"] * np.cos(th), g["distanceMpc"] * np.sin(th)
        cx = (X / ext * 0.5 + 0.5) * n
        cy = (0.5 - Y / ext * 0.5) * n
        if not (0 <= cx < n and 0 <= cy < n):
            continue
        s = g["radiusMpc"] / px_sig
        if s < 0.6 or s > n / 4:
            continue
        y0, y1 = int(max(0, cy - 5 * s)), int(min(n, cy + 5 * s + 1))
        x0, x1 = int(max(0, cx - 5 * s)), int(min(n, cx + 5 * s + 1))
        if y1 <= y0 or x1 <= x0:
            continue
        r2 = ((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2) / (s * s)
        img[y0:y1, x0:x1] += 0.6 * np.exp(-0.5 * r2)
    return np.clip(img, 0, 1)


def falsification_checks(d):
    """T-079 — un controle de paire repond-il juste a une verite CONNUE ?

    Origine : 08/08/2026, apres le verdict porte sur T-012. Le 07/08 avait deja
    montre que quatre controles testaient autre chose que l'exigence citee, et
    que la relecture de Marc — pas le harnais — les avait vus. La lecon est au
    §7 de l'etat des lieux : « le harnais garantit qu'un critere est EXECUTE ;
    il ne garantit ni qu'il est JUSTE, ni qu'il est applique la ou il faut ».
    Ce controle est la reponse executable a cette lecon.

    Le banc n'utilise AUCUNE texture publiee : il fabrique trois images d'essai
    ne portant que des gaussiennes aux positions du catalogue. C'est ce qui
    permet de faire varier UNE SEULE chose a la fois.

      TEMOIN POSITIF  enfant = fenetre de l'enfant, objets a la taille de
                      l'enfant. Tout a grandi au rythme du zoom.
                      T-012 DOIT passer.

      TEMOIN NEGATIF  enfant = fenetre de l'enfant, objets restes a la taille
                      DU PARENT. Les positions sont justes, les tailles non.
                      T-012 DOIT echouer.

    Le second point est ce qui a valu deux corrections au banc lui-meme le
    08/08 : un temoin negatif fabrique en laissant le parent tel quel melangeait
    deux defauts — mauvaises positions ET absence de croissance — et T-012 le
    laissait passer pour une raison qui n'avait rien a voir avec ce qu'on
    voulait eprouver. Un banc qui fait varier deux choses ne prouve rien.
    """
    m = matrix()
    n = 480
    for pc, cc in (("E", "D"), ("F", "E"), ("C", "B"), ("B", "A")):
        par = _synth_row(pc, n)
        bon = _synth_row(cc, n)
        faux = _synth_row(cc, n, sigma_code=pc)
        pos = [r for r in image_pair_checks(pc, cc, par, bon, m) if r.tid == "T-012"]
        neg = [r for r in image_pair_checks(pc, cc, par, faux, m) if r.tid == "T-012"]
        if not pos or not neg:
            continue
        ok = pos[0].ok and not neg[0].ok
        return [Result("T-079", "CONF",
                       "T-012 repond juste a une verite connue (banc)", ok,
                       "%s->%s  positif %s (%s) · negatif %s (%s)"
                       % (pc, cc,
                          "passe" if pos[0].ok else "RATE",
                          pos[0].detail.split("  ")[0].split("s ")[-1],
                          "echoue" if not neg[0].ok else "RATE",
                          neg[0].detail.split("  ")[0].split("s ")[-1]))]
    return [Result("T-079", "CONF", "T-012 repond juste a une verite connue (banc)",
                   False, "aucune paire d'essai exploitable")]
