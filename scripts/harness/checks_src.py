"""PORTEE SRC — les SPRITES SOURCES, pas les textures publiees.

Pourquoi une portee a part
--------------------------
T-040 a T-048 protegent le procede N-corps des galaxies. Ils ne portent pas sur
ce qui est cuit mais sur ce qui alimente la cuisson : les 126 frames de
dissolution. Ils doivent donc s'executer **meme quand aucune cuisson n'a lieu**,
sinon une degradation des sources reste invisible jusqu'a la prochaine cuisson.

Ce qu'ils empechent, precisement
--------------------------------
Entre le 8 juillet et le 3 aout 2026, le moteur N-corps (Barnes-Hut, 6 000
particules, 480 pas, 14 frames) a ete remplace par des gaussiennes dessinees a la
main, sans que rien ne le signale. Les sprites du 6 juillet etaient « plus jolis,
avec un meilleur pique » parce que c'etait de la physique. La regression a tenu
cinq mois faute d'etre ecrite quelque part.

T-042 et T-044 sont les deux verrous :
  - T-042 attrape le retour de `HALO_GROWTH`. Un flux x77 au lieu de x2,18
    signifie que la galaxie grossit en LUMINOSITE au lieu de s'etaler.
  - T-044 attrape le remplacement du moteur par un flou. Un lissage fait
    DIMINUER les pics locaux ; une vraie dissolution gravitationnelle les fait
    augmenter, parce que la galaxie se fragmente.

Toutes les valeurs de reference ont ete mesurees le 03/08/2026 et re-mesurees le
07/08 a l'ecriture de ces controles ; les deux jeux coincident.
"""
import os

import numpy as np
from scipy import ndimage

from checks import ROOT, Result

DATA = os.path.join(ROOT, "app", "public", "data")
SPRITE_DIR = os.path.join(DATA, "dissolution_sprites")
HIRES_DIR = os.path.join(DATA, "dissolution_sprites_hires")
NAMES = ["andromede", "ic10", "leo1", "lmc", "milkyway", "ngc6822",
         "sagittaire", "smc", "triangulum"]
N_FRAMES = 14


def _load(name, f, hires=False):
    from PIL import Image
    d = HIRES_DIR if hires else SPRITE_DIR
    p = os.path.join(d, "%s_f%02d.png" % (name, f))
    if not os.path.exists(p):
        return None
    return np.asarray(Image.open(p).convert("L"), np.float64) / 255.0


def _r50(a):
    """Rayon contenant la moitie du flux, autour du barycentre lumineux."""
    y, x = np.indices(a.shape)
    t = a.sum()
    if t <= 0:
        return 0.0
    cy, cx = (a * y).sum() / t, (a * x).sum() / t
    r = np.hypot(y - cy, x - cx).ravel()
    w = a.ravel()
    o = np.argsort(r)
    c = np.cumsum(w[o])
    return float(r[o][np.searchsorted(c, 0.5 * c[-1])])


def _peaks(a):
    m = ndimage.maximum_filter(a, 3)
    return int(((a == m) & (a > 0.05 * max(a.max(), 1e-9))).sum())


def _moments(a, mask):
    """Aplatissement ET orientation, ponderes par le flux.

    Retourne (sqrt(petit axe / grand axe), angle du grand axe en degres).
    """
    y, x = np.indices(a.shape)
    w = np.where(mask, a, 0.0)
    t = w.sum()
    if t <= 0:
        return 1.0, 0.0
    cy, cx = (w * y).sum() / t, (w * x).sum() / t
    vyy = (w * (y - cy) ** 2).sum() / t
    vxx = (w * (x - cx) ** 2).sum() / t
    vxy = (w * (y - cy) * (x - cx)).sum() / t
    C = np.array([[vyy, vxy], [vxy, vxx]])
    w_, V = np.linalg.eigh(C)
    o = np.argsort(w_)[::-1]
    ev = w_[o]
    v0 = V[:, o[0]]
    ang = float(np.degrees(np.arctan2(v0[0], v0[1])) % 180.0)
    return float(np.sqrt(max(ev[1], 0.0) / max(ev[0], 1e-12))), ang


def src_checks():
    out = []

    # ---- T-048 : les sprites viennent bien du moteur, et sont tous la -------
    present = [(n, f) for n in NAMES for f in range(N_FRAMES)
               if os.path.exists(os.path.join(SPRITE_DIR, "%s_f%02d.png" % (n, f)))]
    hires = [f for f in range(N_FRAMES)
             if os.path.exists(os.path.join(HIRES_DIR, "milkyway_f%02d.png" % f))]
    moteur = os.path.join(ROOT, "scripts", "simulate_dissolution.mjs")
    nbody = False
    if os.path.exists(moteur):
        s = open(moteur, encoding="utf-8", errors="ignore").read().lower()
        nbody = ("barnes" in s or "quadtree" in s or "quadTree".lower() in s)
    out.append(Result("T-048", "SRC", "les sprites proviennent du moteur N-corps (A12)",
                      len(present) == 126 and len(hires) == 14 and nbody,
                      "%d/126 frames, %d/14 hires, moteur %s"
                      % (len(present), len(hires), "present" if nbody else "ABSENT")))

    pics0, pics13, ell_core, sigs = [], [], [], {}
    for n in NAMES:
        a, b = _load(n, 0), _load(n, N_FRAMES - 1)
        if a is None or b is None:
            out.append(Result("T-040", "SRC", "pic de la frame formee (A12)", False,
                              "%s : frames manquantes" % n))
            continue

        # T-040 — la frame formee est normalisee a 1. Un pic qui derive signale
        # une renormalisation glissee dans la chaine.
        out.append(Result("T-040", "SRC", "pic de la frame formee = 1,000 (A12)",
                          a.max() >= 0.975, "%s %.3f" % (n, a.max())))
        # T-041 — le pic doit s'effondrer. Mesure 03/08 : 0,067 a 0,082.
        out.append(Result("T-041", "SRC", "pic a la dissolution <= 0,12 (C17)",
                          b.max() <= 0.12, "%s %.3f" % (n, b.max())))
        # T-042 — VERROU. Flux quasi conserve : la galaxie s'etale et palit.
        # x77 = HALO_GROWTH revenu, la tache grossit sans jamais palir.
        fr = b.sum() / max(a.sum(), 1e-9)
        out.append(Result("T-042", "SRC", "rapport de flux f13/f00 dans [1,5 ; 3,0] (C17)",
                          1.5 <= fr <= 3.0, "%s x%.2f" % (n, fr)))
        # T-043 — l'etalement est reel, pas cosmetique.
        rr = _r50(b) / max(_r50(a), 1e-9)
        out.append(Result("T-043", "SRC", "etalement r50 f13/f00 >= 5 (C1/C16)",
                          rr >= 5.0, "%s x%.1f" % (n, rr)))
        # T-044 — VERROU. Un flou fait DIMINUER les pics locaux ; une vraie
        # dissolution gravitationnelle les fait augmenter (fragmentation).
        p0, p13 = _peaks(a), _peaks(b)
        out.append(Result("T-044", "SRC", "pics locaux : f13 > f00 (C16)",
                          p13 > p0, "%s %d -> %d" % (n, p0, p13)))
        # T-046 — structure interne riche, pas une gaussienne.
        out.append(Result("T-046", "SRC", "structure interne >= 50 pics locaux (A13)",
                          p0 >= 50, "%s %d pics" % (n, p0)))
        # T-047 — le halo suit l'aplatissement du disque, il n'est pas rond.
        r50a = max(_r50(a), 1.0)
        y, x = np.indices(a.shape)
        t = a.sum()
        cy, cx = (a * y).sum() / t, (a * x).sum() / t
        r = np.hypot(y - cy, x - cx)
        # A14 demande deux choses distinctes, et c'est la seconde qui compte :
        #   1. le halo est ELLIPTIQUE, donc pas rond ;
        #   2. son aplatissement est CONFORME AU DISQUE, donc son grand axe
        #      pointe dans la meme direction que celui du disque.
        # Une premiere ecriture comparait les deux aplatissements et echouait sur
        # les neuf sprites : le coeur mesure 0,79 a 0,93 et le halo 0,30 a 0,65.
        # C'est le comportement ATTENDU -- bulbe rond, disque aplati -- et non un
        # defaut. Le seuil n'a pas ete desserre : le critere etait faux.
        e_core, a_core = _moments(a, r <= r50a)
        e_halo, a_halo = _moments(a, (r > r50a) & (r <= 3 * r50a))
        d_ang = abs(a_halo - a_core)
        d_ang = min(d_ang, 180.0 - d_ang)
        out.append(Result("T-047", "SRC", "halo elliptique, axe conforme au disque (A14)",
                          e_halo <= 0.90 and d_ang <= 20.0,
                          "%s halo %.2f, ecart d'axe %.0f deg" % (n, e_halo, d_ang)))

        # T-045 — monotonie sur les 14 frames : pic decroissant, rayon croissant.
        pk, ra = [], []
        for f in range(N_FRAMES):
            fr_ = _load(n, f)
            if fr_ is None:
                break
            pk.append(fr_.max())
            ra.append(_r50(fr_))
        bad_pk = sum(1 for i in range(len(pk) - 1) if pk[i + 1] > pk[i] * 1.02)
        bad_ra = sum(1 for i in range(len(ra) - 1) if ra[i + 1] < ra[i] * 0.98)
        out.append(Result("T-045", "SRC", "monotonie sur les 14 frames (C1/C2)",
                          bad_pk == 0 and bad_ra == 0,
                          "%s %d remontee(s) de pic, %d recul(s) de rayon"
                          % (n, bad_pk, bad_ra)))

        pics0.append(p0)
        pics13.append(p13)
        ell_core.append(e_halo)
        sigs[n] = (round(float(a.sum()), 3), p0)

    # ---- T-024 : les morphologies sont-elles vraiment variees ? -------------
    # Origine 28/07, exigence D5. Mesure du 07/08 : `ic10` et `leo1` sont
    # OCTET POUR OCTET le meme fichier. Deux galaxies nommees partagent une
    # morphologie ; rien ne le signalait.
    doublons = {}
    for n, s in sigs.items():
        doublons.setdefault(s, []).append(n)
    paires = [v for v in doublons.values() if len(v) > 1]
    disp = float(np.std(ell_core)) if ell_core else 0.0
    out.append(Result("T-024", "SRC", "dispersion des morphologies (D5)",
                      not paires and disp >= 0.05,
                      "dispersion %.3f%s" % (disp, "  DOUBLONS : "
                      + " / ".join("=".join(p) for p in paires) if paires else "")))
    return out


def paste_flux_checks():
    """T-081 — reduire un sprite conserve-t-il son flux ? (A12/C17/D8)

    Origine : 08/08/2026. T-015, T-016, T-017, T-012 et T-019 echouaient
    ENSEMBLE sur les lignes a sprites, et le diagnostic
    `scripts/dev/diag_paste.py` leur a trouve une cause unique.

    `sprites_layer._paste` reduisait la vignette de 512 px par
    `ndimage.zoom(order=3)`. Une spline INTERPOLE : elle echantillonne la
    source, elle ne l'integre pas. En reduction forte, tout ce qui tombe entre
    deux points d'echantillonnage est simplement perdu -- et une galaxie est
    surtout du vide avec un noyau brillant, donc c'est le noyau qu'on rate.

    Mesure du 08/08, sur les cinq vignettes, flux conserve par rapport a une
    moyenne d'aire :

        diametre    4 px    6 px   10 px   20 px   60 px
        conserve      0 %     0 %     0 %  15-80 %  78-110 %

    **En dessous de vingt pixels, la galaxie n'etait pas dessinee du tout.**
    C'est pourquoi la Voie lactee etait introuvable sur `F` et `E` (0,7 et
    1,8 px de rayon) mais retrouvee sur `D` (4,6 px), et pourquoi le Grand
    Nuage disparaissait sous le disque au lieu d'y etre noye.

    Le controle mesure l'operateur LIVRE, pas le principe : il appelle `_paste`
    sur une vignette reelle a plusieurs diametres et compare le flux depose a
    l'integrale exacte de la source. Une tolerance de 15 % couvre l'erreur de
    quadrature aux tres petits diametres.
    """
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))
    import sprites_layer as S

    out = []
    pires = []
    for key in ("milkyway", "andromede", "triangulum", "lmc", "sagittaire"):
        sp = S.load_sprite(key, 1.0)
        if sp is None:
            continue
        f_src = float(np.asarray(sp, np.float64).mean())
        for d in (4, 6, 10, 20, 60):
            img = np.zeros((4 * d + 8, 4 * d + 8), np.float32)
            c = img.shape[0] / 2.0
            S._paste(img, sp, c, c, d, 1.0)
            # Flux depose rapporte a l'aire cible : c'est la moyenne de la
            # source si et seulement si l'operateur integre.
            f_out = float(img.sum()) / (d * d)
            pires.append((f_out / max(f_src, 1e-12), key, d))
    if not pires:
        return [Result("T-081", "SRC", "la reduction des sprites conserve le flux (A12)",
                       False, "aucune vignette lisible")]
    pires.sort()
    r, key, d = pires[0]
    out.append(Result("T-081", "SRC",
                      "la reduction des sprites conserve le flux (A12/D8)",
                      r >= 0.85,
                      "pire cas %.0f %% du flux (%s a %d px) sur %d mesures"
                      % (100 * r, key, d, len(pires))))
    return out


def expansion_checks():
    """T-082 a T-084 — la carte est-elle coherente avec l'expansion reelle ?

    Exigences E1 a E4, ecrites le 08/08/2026 a la demande de Marc.

    Le point de depart est E1, et il commande le reste : LA CARTE EST EN
    COORDONNEES COMOBILES. En comobile une structure ne se comprime pas avec le
    temps, elle reste ou elle est ; ce qui varie avec l'epoque, ce sont les
    RAYONS DES HORIZONS. Confondre les deux est la faute que ces controles
    empechent.
    """
    import json
    from scipy.integrate import quad

    out = []
    m = json.load(open(os.path.join(ROOT, "app", "public", "data", "spacetime_matrix.json")))
    ta = m["time_axis"]
    co = ta["cosmology"]
    Om = co["Omega_m"]
    Ol = co["Omega_L"]
    Or = co.get("Omega_r", 0.0)
    H0 = co["H0_km_s_Mpc"]
    C = 299792.458

    def E(a):
        return np.sqrt(Or / a ** 4 + Om / a ** 3 + Ol)

    def particules(a):
        """Horizon des particules, rayon COMOBILE : c/H0 x int_0^a da/(a^2 E)."""
        return quad(lambda x: 1.0 / (x * x * E(x)), 1e-10, a, limit=300)[0] * C / H0

    def hubble(a):
        """Rayon de Hubble comobile : c / (a H(a))."""
        return C / (H0 * E(a) * a)

    # ---- T-082 : les horizons decoulent de la cosmologie, jamais d'un reglage.
    #
    # Recalcul INDEPENDANT depuis Omega_m, Omega_L, Omega_r et H0. Une valeur
    # saisie a la main, ou un parametre manquant dans le bloc declare, se voit
    # immediatement. C'est E2, et c'est le sujet meme de l'oeuvre : les trois
    # limites doivent etre justes, le fond de carte les sert.
    #
    # Ce controle a trouve son defaut des sa premiere execution : le bloc
    # `cosmology` ne declarait que Omega_m et Omega_L. Sans le rayonnement, le
    # rayon de l'horizon des particules a la recombinaison se recalcule a
    # 477,6 Mpc au lieu des 278,6 declares -- 71 % d'ecart. Les valeurs de la
    # matrice etaient JUSTES ; c'est la cosmologie declaree qui ne permettait
    # pas de les retrouver, donc rien ne garantissait qu'elles le restent.
    pires = []
    for col in ta["columns"]:
        a = col["a"]
        h = col.get("horizons", {})
        for nom, calc in (("particules", particules), ("hubble", hubble)):
            if nom not in h:
                continue
            ref = float(h[nom])
            got = calc(a)
            pires.append((abs(got - ref) / max(ref, 1e-9), col["col"], nom, ref, got))
    if not pires:
        out.append(Result("T-082", "CONF", "les horizons decoulent de la cosmologie (E2)",
                          False, "aucun horizon declare dans time_axis"))
    else:
        pires.sort(reverse=True)
        e, c0, nom, ref, got = pires[0]
        out.append(Result("T-082", "CONF", "les horizons decoulent de la cosmologie (E2)",
                          e <= 0.02,
                          "pire ecart %.1f %% (colonne %d, %s : %.1f declare, "
                          "%.1f recalcule) sur %d valeurs"
                          % (100 * e, c0, nom, ref, got, len(pires))))

    # ---- T-083 : le grille comobile ne se redimensionne PAS avec le temps.
    #
    # E1. Une ligne porte un demi-champ en Mpc COMOBILES ; il doit etre le meme
    # a toutes les colonnes. Si un jour quelqu'un fait varier le demi-champ avec
    # l'epoque -- pour « comprimer les structures comme l'univers se comprime »
    # -- il aura confondu comobile et propre, et la carte ne voudra plus rien
    # dire : les trois horizons ne seraient plus comparables d'une colonne a
    # l'autre, alors que c'est precisement ce que l'oeuvre montre.
    rows = m["zoom_axis"]["rows"]
    mauvais = [k for k, v in rows.items()
               if any(x in v for x in ("halfwidth_mpc_par_colonne", "scale_by_a",
                                       "halfwidth_proper_mpc"))]
    unite = ta["columns"][0].get("horizons", {}).get("unite", "")
    out.append(Result("T-083", "CONF", "la grille est comobile et fixe dans le temps (E1)",
                      not mauvais and "comobile" in unite.lower(),
                      "%d ligne(s) a demi-champ dependant de l'epoque ; unite des "
                      "horizons : %r" % (len(mauvais), unite)))

    # ---- T-084 : le franchissement de l'horizon est ATTENDU, et chiffre.
    #
    # E3, et c'est un controle qui protege contre une CORRECTION, pas contre un
    # defaut. Le rayon comobile de l'horizon des particules se contracte d'un
    # facteur ~50 de la colonne 10 a la colonne 0, pendant que les structures
    # restent a leur place comobile : elles sortent du cercle, et c'est
    # exactement ce que signifie « l'univers observable grandit ».
    #
    # Si ce rapport tombait vers 1, cela voudrait dire que l'horizon a ete fait
    # pour suivre l'espace -- donc que la notion d'horizon des particules a ete
    # supprimee, et avec elle le sujet de l'oeuvre. Le controle echoue alors,
    # meme si tout le reste semble plus « coherent ».
    cols = {c["col"]: c for c in ta["columns"] if "horizons" in c}
    if 0 in cols and 10 in cols:
        r0 = cols[0]["horizons"]["particules"]
        r10 = cols[10]["horizons"]["particules"]
        rap = r10 / max(r0, 1e-9)
        out.append(Result("T-084", "CONF",
                          "l'horizon des particules se contracte vers le Big Bang (E3)",
                          rap >= 20.0,
                          "rayon comobile x%.1f de la colonne 0 a la colonne 10 "
                          "(%.1f -> %.1f Mpc)" % (rap, r0, r10)))

    # ---- T-085 : les lignes liees sont exemptes de dilatation.
    #
    # E4. Sous le rayon de retournement (GM/OmegaL H0^2)^(1/3) -- 1,9 Mpc pour le
    # Groupe Local, 11 Mpc pour les amas les plus massifs -- la gravite l'emporte
    # et les structures ne suivent pas le flot de Hubble. Sur ces lignes la seule
    # evolution admise est la DISSOLUTION : les objets se defont parce qu'ils ne
    # sont pas encore formes, jamais parce que l'espace les aurait etires.
    #
    # Le controle verifie que la loi temporelle declaree pour les sprites est
    # bien une dissolution, et qu'aucune loi d'etirement spatial n'a ete ajoutee
    # pour ces lignes.
    lois = m["generation"].get("lois_temporelles", {})
    liees = [k for k, v in rows.items() if v["halfwidth_mpc"] <= 3.6]
    interdits = [k for k in lois
                 if isinstance(lois[k], dict)
                 and any(t in json.dumps(lois[k]).lower()
                         for t in ("facteur d'echelle a(", "etirement spatial",
                                   "scale_by_a"))]
    out.append(Result("T-085", "CONF",
                      "aux echelles liees, aucune dilatation apparente (E4)",
                      not interdits and "sprites" in lois,
                      "%d ligne(s) liees (<= 3,6 Mpc) : %s ; %d loi(s) d'etirement "
                      "spatial declaree(s)" % (len(liees), " ".join(sorted(liees)),
                                               len(interdits))))
    return out
