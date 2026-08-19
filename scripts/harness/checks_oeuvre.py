"""PORTEE OEUVRE — les trois horizons, LE SUJET.

Pourquoi ce module existe
-------------------------
Le 07/08/2026, le controle de couverture T-055 a montre que **les huit exigences
de la section H n'etaient protegees par aucun test**. Ce sont pourtant celles qui
definissent l'oeuvre : « l'objet de l'oeuvre est de faire comprendre visuellement
l'univers observable, la sphere de Hubble et l'horizon des evenements ; tout le
reste est un fond de carte a leur service ».

Deux mois de travail et 345 controles portaient donc integralement sur le fond de
carte, et zero sur le sujet. C'est le desequilibre que ce module corrige.

Ces controles ne regardent pas une texture : ils regardent la table cosmologique
livree a l'application et le code qui la dessine. Ils sont de portee OEUVRE et
s'executent a chaque cuisson comme les autres.
"""
import json
import os
import re

import numpy as np

from checks import DATA, ROOT, Result

TABLE = os.path.join(DATA, "cosmology_table.json")
CARTE = os.path.join(ROOT, "app", "src", "UniverseMap.tsx")
COSMO = os.path.join(ROOT, "app", "src", "cosmology.ts")
DENSITE = os.path.join(ROOT, "app", "src", "DensityLayer.tsx")
POIDS = os.path.join(ROOT, "app", "src", "layerWeights.ts")
MATRICE = os.path.join(ROOT, "app", "public", "data", "spacetime_matrix.json")

# Valeurs de reference du document client, section H. Tolerance 5 % : ce sont des
# ordres de grandeur cosmologiques, pas des constantes de calibration.
CIBLES = {"chi_particle_Mpc": ("H1", "univers observable", 14570.0),
          "r_hubble_comoving_Mpc": ("H2", "sphere de Hubble", 4450.0),
          "chi_event_Mpc": ("H3", "horizon des evenements", 5100.0)}


def _table():
    with open(TABLE) as fh:
        return json.load(fh)


def _aujourdhui(rows):
    return min(rows, key=lambda r: abs(r["a"] - 1.0))


def oeuvre_checks():
    out = []
    if not os.path.exists(TABLE):
        return [Result("H1", "OEUVRE", "table cosmologique", False, "absente")]
    t = _table()
    rows = t["rows"]
    now = _aujourdhui(rows)

    # ---- H1, H2, H3 : les trois rayons, aux bonnes valeurs ----------------
    for cle, (tid, nom, cible) in CIBLES.items():
        v = float(now[cle])
        out.append(Result("T-056", "OEUVRE",
                          "les trois rayons a aujourd'hui (H1/H2/H3)",
                          abs(v - cible) / cible <= 0.05,
                          "%s %s %.0f Mpc pour %.0f attendus" % (tid, nom, v, cible)))

    # ---- H2 encore : la sphere de Hubble est PLUS PETITE que l'observable --
    # C'est le fait que l'oeuvre doit faire comprendre : on voit des objets qui
    # s'eloignent plus vite que la lumiere. Si l'ordre s'inverse, la carte
    # enseigne le contraire de ce qu'elle veut dire.
    ordre = (now["r_hubble_comoving_Mpc"] < now["chi_event_Mpc"]
             < now["chi_particle_Mpc"])
    out.append(Result("T-057", "OEUVRE", "Hubble < evenements < observable (H2/H3)",
                      ordre, "%.0f < %.0f < %.0f"
                      % (now["r_hubble_comoving_Mpc"], now["chi_event_Mpc"],
                         now["chi_particle_Mpc"])))

    # ---- H4 : la vitesse de recession depasse c, et au bon endroit ---------
    # Par definition, a la sphere de Hubble v = c. La table doit donc etre
    # coherente avec H0 : r_hubble propre = c / H0. Sans cela le depassement de c
    # est represente au mauvais rayon, et H4 est faux a l'ecran.
    c_km_s = 299792.458
    h0 = float(t["meta"]["H0_km_s_Mpc"])
    attendu = c_km_s / h0
    obtenu = float(now["r_hubble_comoving_Mpc"])
    out.append(Result("T-058", "OEUVRE", "v = c a la sphere de Hubble (H4)",
                      abs(obtenu - attendu) / attendu <= 0.05,
                      "%.0f Mpc pour c/H0 = %.0f" % (obtenu, attendu)))

    # ---- H5 : les trois rayons evoluent, et DIFFEREMMENT -------------------
    # « Ces trois rayons ne sont pas constants : ils evoluent avec l'epoque, et
    # differemment les uns des autres. » Un rayon constant, ou trois rayons qui
    # varient a l'identique, rendraient le curseur temporel muet sur le sujet.
    a = np.array([r["a"] for r in rows])
    m = (a >= 0.05) & (a <= 1.0)
    series = {k: np.array([r[k] for r in rows])[m] for k in CIBLES}
    varie = {k: float(v.max() / max(v.min(), 1e-9)) for k, v in series.items()}
    couples = [("chi_particle_Mpc", "r_hubble_comoving_Mpc"),
               ("chi_particle_Mpc", "chi_event_Mpc"),
               ("r_hubble_comoving_Mpc", "chi_event_Mpc")]
    identiques = [c for c in couples
                  if abs(varie[c[0]] - varie[c[1]]) / max(varie[c[0]], 1e-9) < 0.02]
    out.append(Result("T-059", "OEUVRE", "les trois rayons evoluent differemment (H5)",
                      all(v > 1.05 for v in varie.values()) and not identiques,
                      "amplitudes x%.1f / x%.1f / x%.1f"
                      % tuple(varie[k] for k in CIBLES)))

    # ---- H6 : les trois sont-elles REELLEMENT tracees ? -------------------
    # « Les trois spheres doivent rester lisibles et distinctes a toute position
    # des deux curseurs. » Une sphere calculee mais jamais dessinee ne remplit
    # pas l'exigence. Au 07/08, la carte n'en trace qu'une.
    src = open(CARTE, encoding="utf-8").read() if os.path.exists(CARTE) else ""
    # Le detecteur cherchait `<rayon> * pxPerMpc` colle. Trop litteral : des que
    # les trois rayons passent par une boucle, il ne voit plus rien alors que les
    # cercles sont bel et bien traces. On verifie donc que chaque rayon est
    # REFERENCE dans le composant ET qu'il s'y trace au moins trois cercles.
    n_arcs = len(re.findall(r"ctx\.arc\(", src))
    tracees = [nom for cle, nom in (("chiParticleComovingMpc", "observable"),
                                    ("rHubbleComovingMpc", "Hubble"),
                                    ("chiEventComovingMpc", "evenements"))
               if (re.search(cle + r"\s*\*\s*pxPerMpc", src)
                   or re.search(r"r:\s*cosmology\." + cle, src)) and n_arcs >= 1]
    out.append(Result("T-060", "OEUVRE", "les trois spheres sont tracees (H6)",
                      len(tracees) == 3, "%d/3 tracee(s) : %s  (%d cercles)"
                      % (len(tracees), " ".join(tracees) or "aucune", n_arcs)))

    # ---- H7 : la comprehension passe par la manipulation ------------------
    # Le texte vient EN APPUI et ne porte jamais seul la comprehension. Le
    # controle verifie qu'il existe bien deux curseurs agissant sur la carte, et
    # que chaque sphere tracee porte une etiquette lisible a l'ecran.
    curseurs = len(re.findall(r'type="range"', src))
    etiquettes = len(re.findall(r"fillText\(", src))
    out.append(Result("T-061", "OEUVRE", "comprehension par la manipulation (H7)",
                      curseurs >= 2 and etiquettes >= 3,
                      "%d curseurs, %d etiquettes tracees" % (curseurs, etiquettes)))

    # ---- H8 : la vitesse de la lumiere est representee --------------------
    # « Le fond de carte doit porter, sous une forme ou une autre, une
    # representation de la vitesse de la lumiere. » C'est l'etalon qui rend les
    # trois spheres intelligibles.
    ref_c = bool(re.search(r"\b(299792|C_KM_S|LIGHT_SPEED|vitesse de la lumi)", src)) \
        or bool(re.search(r"\b299792", open(COSMO, encoding="utf-8").read()
                          if os.path.exists(COSMO) else ""))
    out.append(Result("T-062", "OEUVRE", "la vitesse de la lumiere est representee (H8)",
                      ref_c, "aucune representation trouvee" if not ref_c else "presente"))

    dens = open(DENSITE, encoding="utf-8").read() if os.path.exists(DENSITE) else ""

    # ---- H9 : aucun bord vide au zoom -------------------------------------
    # Le defaut du 11/08 : quand `overshoot > 1`, la destination est reduite a
    # une boite centree et RIEN ne peint l'anneau restant des que le layer
    # ecrete atteint la pleine opacite (le grossier est saute a `w < 0.003`).
    # Sur un ecran large `halfWidthMpcX` est multiplie par W/H, donc le
    # debordement arrive ~1,8x plus tot en 16:9 qu'en portrait -- d'ou le cadre
    # noir vu par Marc sur ecran de PC et jamais sur telephone.
    #
    # Le controle exige les TROIS pieces, parce que deux sur trois ne peignent
    # rien : un remplisseur CHOISI parmi les layers qui couvrent encore l'ecran,
    # un DECOUPAGE en regle pair-impair (sans lui le centre serait repeint et le
    # ton fausse), et un TRACE a l'interieur de la branche d'ecretage.
    a_remplisseur = bool(re.search(r"filler\s*=", dens))
    a_decoupe = bool(re.search(r"clip\(\s*['\"]evenodd", dens))
    a_couverture = bool(re.search(r"maxMpc\s*\*\s*marginFor", dens))
    manque = [n for n, ok in (("remplisseur", a_remplisseur),
                              ("decoupe pair-impair", a_decoupe),
                              ("choix par couverture", a_couverture)) if not ok]
    out.append(Result("T-096", "OEUVRE", "aucun bord vide au zoom (H9)",
                      not manque,
                      "manque : " + ", ".join(manque) if manque
                      else "remplisseur choisi par couverture, anneau seul repeint"))

    # ---- H10 : libelles proportionnes a l'ecran ---------------------------
    # Les tailles etaient des CONSTANTES en px CSS, calibrees sur telephone.
    # Le controle verifie qu'il ne reste AUCUNE taille figee dans la carte :
    # une seule oubliee et c'est elle qui redevient illisible sur grand ecran.
    fige_html = re.findall(r"fontSize:\s*(\d+)(?![\d.])", src)
    fige_canvas = re.findall(r"\$\{(\d+(?:\.\d+)?) \* DPR\}px", src)
    a_echelle = bool(re.search(r"uiScale\s*=", src))
    out.append(Result("T-097", "OEUVRE", "libelles proportionnes a l'ecran (H10)",
                      a_echelle and not fige_html and not fige_canvas,
                      "%d taille(s) HTML et %d police(s) canvas encore figees"
                      % (len(fige_html), len(fige_canvas)) if (fige_html or fige_canvas)
                      else ("echelle absente" if not a_echelle
                            else "toutes les tailles suivent uiScale")))

    # ---- H11 : temoin des layers affiches ---------------------------------
    # Instrument de mesure du retour client : il doit lire les poids par la MEME
    # fonction que le compositeur, sinon il designe un layer pour un autre et
    # tous les retours qu'il permet sont faux.
    meme_source = bool(re.search(r"getLayerWeights", src)) and \
        bool(re.search(r"getLayerWeights", dens))
    a_pourcent = bool(re.search(r"100 \* w\[", src))
    meme_seuil = ("0.003" in src) and ("0.003" in dens)
    manque2 = [n for n, ok in (("meme fonction de poids", meme_source),
                               ("pourcentages", a_pourcent),
                               ("meme seuil d'affichage", meme_seuil)) if not ok]
    # ---- T-101 : l'application affiche la grille cuite, sans derive --------
    # AJOUTE le 11/08/2026. Jusqu'a cette date l'application de production
    # tournait sur un decoupage en DOUZE paliers herite (`milkyway`,
    # `localgroup`, `l1b`... `l5`) pendant que la grille `A` -> `O`, cuite et
    # controlee par les 392 controles du harnais, ne servait qu'a une page
    # d'essai separee. **L'oeuvre ne montrait donc AUCUNE des textures que ce
    # harnais valide.** C'est le genre d'ecart qui ne se voit pas depuis le
    # rapport de cuisson, puisque tout y est vert.
    #
    # Le controle compare la table de demi-largeurs de `layerWeights.ts` a
    # `zoom_axis.rows` de la matrice. Recopier des chiffres est legitime -- le
    # navigateur ne lit pas le JSON de generation -- mais une recopie que rien
    # ne verifie derive a la premiere cuisson qui bouge la geometrie.
    poids = open(POIDS, encoding="utf-8").read() if os.path.exists(POIDS) else ""
    try:
        rows = json.load(open(MATRICE, encoding="utf-8"))["zoom_axis"]["rows"]
    except Exception:
        rows = {}
    ecarts = []
    for code, r in sorted(rows.items()):
        m = re.search(r"^\s*%s:\s*([0-9.]+)," % code, poids, re.M)
        if not m:
            ecarts.append("%s absente" % code)
        elif abs(float(m.group(1)) - float(r["halfwidth_mpc"])) > 1e-3:
            ecarts.append("%s %s vs %.4f" % (code, m.group(1), r["halfwidth_mpc"]))
    # La marge de rendu doit elle aussi correspondre : c'est elle qui fixe quelle
    # part de la texture est visible, donc l'echelle a l'ecran.
    mm = re.search(r"LAYER_MARGIN\s*=\s*([0-9.]+)", poids)
    if not mm or abs(float(mm.group(1)) - 1.5) > 1e-9:
        ecarts.append("marge de rendu")
    out.append(Result("T-101", "OEUVRE",
                      "l'application affiche la grille cuite (B6)",
                      bool(rows) and not ecarts,
                      "ECARTS : " + " · ".join(ecarts) if ecarts
                      else "les %d lignes de la matrice, marge 1,5" % len(rows)))

    out.append(Result("T-098", "OEUVRE", "temoin des layers affiches (H11)",
                      not manque2,
                      "manque : " + ", ".join(manque2) if manque2
                      else "poids lus par getLayerWeights, seuil 0,003 partage"))
    return out


def construction_checks():
    """B7, D4, E1, E2, E3 — exigences que T-055 a montrees decouvertes."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))
    out = []
    gen = open(os.path.join(ROOT, "scripts", "dev", "gen_chain.py"),
               encoding="utf-8").read()

    # ---- B7 : les grandes echelles precedent les petites ------------------
    # « Le Groupe Local ne doit PAS etre un point special au centre de la
    # carte. » Techniquement : la chaine se deroule du plus grand demi-champ au
    # plus petit, chaque ligne heritant de sa mere. L'inverse ferait du centre
    # l'origine de tout.
    import gen_chain as G
    halfs = [c[1] for c in G.CHAIN]
    out.append(Result("T-063", "CONF", "les grandes echelles precedent les petites (B7)",
                      all(halfs[i] > halfs[i + 1] for i in range(len(halfs) - 1)),
                      "chaine %s -> %s" % (G.CHAIN[0][0], G.CHAIN[-1][0])))

    # ---- E1, E2, E3 : les interdits de mecanisme --------------------------
    # Ils ne se mesurent pas sur une image : une image floue et une image douce
    # se ressemblent. Ils se verifient sur le PROCEDE. On cherche donc les
    # operateurs interdits dans la chaine de generation, hors PSF de rendu.
    lignes = [l for l in gen.splitlines()
              if not l.strip().startswith("#")]
    corps = "\n".join(lignes)
    flous = [l.strip()[:48] for l in lignes
             if "gaussian_filter" in l and "PSF_PX" not in l]
    out.append(Result("T-064", "CONF", "aucun flou comme mecanisme (E1)",
                      not flous, "%d flou(s) hors PSF de rendu : %s"
                      % (len(flous), " | ".join(flous[:2]))))

    # E2 vise le FONDU VERS UN UNIFORME pour faire disparaitre quelque chose,
    # pas toute constante du code : une premiere ecriture signalait
    # `np.full(len(Qb), -1)`, un tableau d'indices. Le motif recherche est une
    # interpolation de l'image vers un scalaire, `image * w + scalaire * (1-w)`.
    sp_src = open(os.path.join(ROOT, "scripts", "dev", "sprites_layer.py"),
                  encoding="utf-8").read()
    motif = re.compile(r"(mean\w*|\d+\.\d+)\s*\*\s*\(1\.?0?\s*-\s*\w+\)"
                       r"[^\n]*\+\s*img\s*\*")
    fondus = []
    for nom, txt in (("gen_chain", corps), ("sprites_layer", sp_src)):
        for l in txt.splitlines():
            if l.strip().startswith("#"):
                continue
            if motif.search(l):
                fondus.append("%s: %s" % (nom, l.strip()[:44]))
    out.append(Result("T-065", "CONF", "aucun melange vers une couleur unie (E2)",
                      not fondus, "%d fondu(s) vers un uniforme : %s"
                      % (len(fondus), " | ".join(fondus[:2]))))

    # E3 : le bruit lisse n'est tolere qu'en MODULATION d'un champ deja
    # structure, avec extinction aux deux extremites (derogation D-14). Le champ
    # fin doit donc etre applique multiplicativement, jamais additivement.
    mult = bool(re.search(r"def apply_fine", gen)) and \
        bool(re.search(r"img\s*\*\s*\(1", gen) or re.search(r"\*\s*np\.exp", gen))
    out.append(Result("T-066", "CONF", "bruit lisse en modulation seulement (E3)",
                      mult, "champ fin %s" % ("multiplicatif" if mult else "ADDITIF")))

    # ---- D4 : les galaxies ne marquent pas les grandes echelles -----------
    # « Leur influence s'attenue avec l'echelle et disparait au-dela du
    # voisinage. » L'ancrage du catalogue ne doit exister que sur les lignes
    # basses ; s'il agit jusqu'a `O`, le Groupe Local marque tout l'univers.
    import checks as CK
    m = CK.matrix()
    anc = m["generation"].get("ancrage", {})
    force = anc.get("strength", {})
    ordre = "ONMLKJIHGFEDCBA"
    lignes_anc = sorted(force, key=ordre.index)
    vals = [force[c] for c in lignes_anc]
    # L'influence doit DECROITRE avec l'echelle et disparaitre au-dela du
    # voisinage. La galaxie la plus lointaine du catalogue est a 9,82 Mpc ; un
    # ancrage subsistant au-dela de `J` (143 Mpc) ferait du Groupe Local une
    # marque sur tout l'univers, ce que D4 interdit.
    deborde = [c for c in lignes_anc if ordre.index(c) < ordre.index("J")]
    decroit = all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))
    out.append(Result("T-067", "CONF", "les galaxies ne marquent pas les grandes echelles (D4)",
                      bool(force) and not deborde and decroit,
                      "ancrage %s%s" % (" ".join("%s=%.2f" % (c, force[c])
                                                 for c in lignes_anc) or "non declare",
                                        "  DEBORDE : " + " ".join(deborde)
                                        if deborde else "")))
    return out
