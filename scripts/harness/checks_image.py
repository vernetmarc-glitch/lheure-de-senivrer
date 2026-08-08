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
        out.append(Result("T-029", "CELL", "points repartis le long des filaments (A5)",
                          fr >= 0.45, "%s %.0f %% sur structures allongees"
                          % (code, 100 * fr)))

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
        # Mesurer la taille apparente d'une galaxie collee a une autre revient a
        # mesurer les deux : on ne retient que les objets ISOLES d'au moins
        # 24 px. Sur les lignes ou il n'en reste pas assez, le controle se tait
        # plutot que de rendre un chiffre qui ne veut rien dire.
        iso = []
        for g, cx, cy in pos:
            if g["radiusMpc"] <= 0:
                continue
            if any(np.hypot(cy - y2, cx - x2) < 24 for h, x2, y2 in pos if h is not g):
                continue
            e = _local_extent(img, cy, cx)
            if e > 0:
                iso.append((g["radiusMpc"], e))
        pr = iso
        if len(pr) >= 6:
            a = np.argsort(np.argsort([p[0] for p in pr]))
            b = np.argsort(np.argsort([p[1] for p in pr]))
            rho = float(np.corrcoef(a, b)[0, 1])
            out.append(Result("T-016", "CELL", "tailles apparentes ~ rayons reels (D7/A9)",
                              rho >= 0.55, "%s correlation de rang %.2f sur %d"
                              % (code, rho, len(pr))))

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
        vals = [float(img[int(cy), int(cx)]) for _, cx, cy in pos]
        fr = float(np.mean([x > med for x in vals]))
        out.append(Result("T-023", "CELL", "densite aux positions du catalogue (D6)",
                          fr >= 0.70, "%s %.0f %% au-dessus de la mediane sur %d"
                          % (code, 100 * fr, len(vals))))
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
    return out
