"""Portee CONF — la compression apparente suit-elle l'expansion reelle ?

Origine : 08/08/2026, demande de Marc. C10 posait le principe depuis le 29/07
— « la dilatation de l'espace doit etre correcte a chaque niveau de zoom et a
chaque epoque » — mais **aucun controle ne le verifiait**. C'est le cas d'ecole
de la regle 0 ter : une exigence sans controle executable est une exigence
oubliee. Elle l'a ete pendant dix jours.

Ces controles ne lisent AUCUNE texture. Ils portent sur la matiere declaree
dans `spacetime_matrix.json` et sur la cosmologie, et ils sont donc valables
avant meme que l'axe du temps soit genere. C'est voulu : ils doivent bloquer la
premiere cuisson temporelle, pas la constater apres coup.
"""
import json
import os

import numpy as np
from scipy.integrate import quad

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
MATRIX = os.path.join(ROOT, "app", "public", "data", "spacetime_matrix.json")

C_KM_S = 299792.458
# Densite de rayonnement (photons + neutrinos relativistes), Planck 2018. Elle
# est negligeable aujourd'hui mais domine a la colonne 0 : l'omettre fausse
# l'horizon des particules a la recombinaison de plusieurs pour cent.
OMEGA_R = 9.15e-5
MPC_PER_MLY = 1.0 / 3.261563


def _cosmo():
    m = json.load(open(MATRIX, encoding="utf-8"))
    c = m["time_axis"]["cosmology"]
    return m, c["Omega_m"], c["Omega_L"], c["H0_km_s_Mpc"]


def _E(a, Om, OL):
    return np.sqrt(OMEGA_R / a ** 4 + Om / a ** 3 + OL)


def particle_horizon(a, Om, OL, H0):
    """Rayon COMOBILE de l'horizon des particules : c * int_0^a da'/(a'^2 H)."""
    dh = C_KM_S / H0
    return dh * quad(lambda x: 1.0 / (x * x * _E(x, Om, OL)), 1e-10, a,
                     limit=400)[0]


def event_horizon(a, Om, OL, H0):
    dh = C_KM_S / H0
    return dh * quad(lambda x: 1.0 / (x * x * _E(x, Om, OL)), a, np.inf,
                     limit=400)[0]


def hubble_radius(a, Om, OL, H0):
    """Rayon COMOBILE de la sphere de Hubble : c / (a H(a))."""
    return C_KM_S / (H0 * a * _E(a, Om, OL))


def growth(a, Om, OL):
    """Facteur de croissance lineaire D(a), non normalise. SANS rayonnement.

    La formule integrale D(a) = E(a) * int_0^a da'/(a' E(a'))^3 n'est exacte que
    pour matiere + Lambda. Y glisser OMEGA_R donnerait un resultat faux, pas plus
    precis : la suppression de croissance avant l'egalite (effet Meszaros) n'est
    pas decrite par cette integrale.

    Premiere version de ce controle, le 08/08 : le rayonnement avait ete inclus
    ici comme dans les integrales d'horizon, et T-082 declarait alors la colonne
    0 fausse de 36 %. C'etait le CONTROLE qui etait hors de son domaine, pas la
    matrice -- septieme fois sur ce projet qu'un controle accuse a tort, et la
    premiere fois qu'il est repris avant d'avoir fait corriger quoi que ce soit.
    """
    Ez = lambda x: np.sqrt(Om / x ** 3 + OL)
    return Ez(a) * quad(lambda x: 1.0 / (x * Ez(x)) ** 3, 1e-8, a, limit=400)[0]


def expansion_checks(Result):
    out = []
    m, Om, OL, H0 = _cosmo()
    cols = m["time_axis"]["columns"]
    rows = m["zoom_axis"]["rows"]

    # ---- T-082 : l'axe du temps est cosmologiquement coherent (C10 bis) ----
    # Chaque colonne declare a, z, t_gyr et amp. Ils ne sont pas independants :
    # z = 1/a - 1, et amp doit valoir D(a)/D(1). Une colonne dont l'amplitude ne
    # decoule pas de son facteur d'echelle donnerait une compression apparente
    # sans rapport avec l'epoque affichee -- exactement ce que C10 bis interdit.
    D1 = growth(1.0, Om, OL)
    pires = []
    for c in cols:
        a = c["a"]
        ez = abs((1.0 / a - 1.0) - c["z"]) / max(c["z"], 1.0)
        ea = abs(growth(a, Om, OL) / D1 - c["amp"]) / max(c["amp"], 1e-6)
        pires.append((max(ez, ea), c["col"], ez, ea))
    pires.sort(reverse=True)
    e, col, ez, ea = pires[0]
    out.append(Result("T-082", "CONF",
                      "l'axe du temps est coherent avec la cosmologie (C10 bis)",
                      e <= 0.02,
                      "pire colonne %d : z a %.1f %% pres, amp a %.1f %% pres "
                      "(sur %d colonnes)" % (col, 100 * ez, 100 * ea, len(cols))))

    # ---- T-083 : les trois horizons suivent l'epoque (H5 / C10 bis) --------
    # H5 exige que les trois rayons evoluent avec l'epoque, « et differemment
    # les uns des autres ». Le controle verifie que la matiere necessaire pour
    # les tracer EXISTE dans la matrice, colonne par colonne, et qu'elle est
    # juste. Sans elle, l'application ne peut que redessiner les rayons
    # d'aujourd'hui a toutes les epoques -- ce qui serait faux et invisible.
    manquantes, fausses = [], []
    for c in cols:
        h = c.get("horizons")
        if not h:
            manquantes.append(c["col"])
            continue
        a = c["a"]
        vrai = {"particules": particle_horizon(a, Om, OL, H0),
                "hubble": hubble_radius(a, Om, OL, H0),
                "evenements": event_horizon(a, Om, OL, H0)}
        for k, v in vrai.items():
            if k not in h or abs(h[k] - v) > 0.03 * max(v, 1.0):
                fausses.append("col %d %s" % (c["col"], k))
    out.append(Result("T-083", "CONF",
                      "les trois horizons sont declares a chaque epoque (H5)",
                      not manquantes and not fausses,
                      "%d colonne(s) sans bloc `horizons`%s"
                      % (len(manquantes),
                         "" if not fausses else " ; faux : " + " ".join(fausses[:3]))))

    # ---- T-084 : l'horizon des particules ne peut que CROITRE (C10 bis) ----
    # En remontant le temps il retrecit, d'un facteur 51 entre aujourd'hui et la
    # recombinaison. C'est ce qui distingue les DEUX cercles que C10 bis separe :
    # la sphere de matiere observable aujourd'hui est fixe en comobile et rien
    # ne la franchit ; l'horizon des particules a l'epoque t, lui, est franchi,
    # et l'oeuvre doit le montrer. Si le rapport n'etait pas monotone, l'un des
    # deux serait dessine a la place de l'autre.
    ph = [particle_horizon(c["a"], Om, OL, H0) for c in cols]
    croissant = all(ph[i] < ph[i + 1] for i in range(len(ph) - 1))
    out.append(Result("T-084", "CONF",
                      "l'horizon des particules croit avec l'epoque (C10 bis)",
                      croissant and ph[-1] / max(ph[0], 1e-9) > 10,
                      "%.0f Mpc a la colonne 0 -> %.0f Mpc aujourd'hui, "
                      "facteur %.0f%s" % (ph[0], ph[-1], ph[-1] / max(ph[0], 1e-9),
                                          "" if croissant else "  NON MONOTONE")))

    # ---- T-085 : la loi de compression par ligne est declaree (C10 ter) ----
    # C10 ter : un systeme lie ne se dilate pas. Appliquer a(t) uniformement
    # ferait retrecir la Voie lactee avec l'univers. La frontiere est la surface
    # de vitesse nulle -- ~1,0 a 1,4 Mpc pour le Groupe Local -- ce qui place la
    # transition entre `E` (1,41 Mpc) et `F` (3,56 Mpc).
    #
    # Le controle exige que la matrice declare, pour chaque ligne, laquelle des
    # trois lois s'applique. Il ne juge pas l'image : il refuse qu'une ligne
    # avance sans que la question ait ete tranchee par ecrit.
    loi = m["generation"].get("lois_temporelles", {}).get("expansion_par_ligne")
    if not loi:
        out.append(Result("T-085", "CONF",
                          "chaque ligne declare son regime d'expansion (C10 ter)",
                          False, "`expansion_par_ligne` absent de la matrice"))
    else:
        VALIDES = {"lie", "transition", "hubble"}
        sans = [c for c in rows if c not in loi]
        mauvais = [c for c, v in loi.items() if v not in VALIDES]
        # Coherence physique : une ligne sous 1,4 Mpc de demi-champ ne peut pas
        # etre declaree en flot de Hubble, ni une ligne au-dela de 10 Mpc liee.
        incoherent = []
        for c, v in loi.items():
            if c not in rows:
                continue
            hw = rows[c]["halfwidth_mpc"]
            if hw <= 1.4 and v == "hubble":
                incoherent.append("%s (%.2f Mpc declare hubble)" % (c, hw))
            if hw >= 10.0 and v == "lie":
                incoherent.append("%s (%.1f Mpc declare lie)" % (c, hw))
        ok = not sans and not mauvais and not incoherent
        out.append(Result("T-085", "CONF",
                          "chaque ligne declare son regime d'expansion (C10 ter)",
                          ok, "%d ligne(s) sans regime%s%s"
                          % (len(sans),
                             "" if not mauvais else " ; valeur inconnue : " + " ".join(mauvais[:3]),
                             "" if not incoherent else " ; INCOHERENT : " + " ".join(incoherent[:3]))))
    return out


def document_checks(Result):
    """T-086 — deux exigences ne portent jamais le meme identifiant.

    Origine : 08/08/2026. Le bloc d'expansion avait ete redige en `E1` a `E4`,
    alors que la section « E. Interdits » utilisait deja ces quatre numeros
    depuis le 29/07. Deux exigences differentes sous le meme nom dans le meme
    document : les controles citent un numero, et un numero qui designe deux
    choses ne designe plus rien.

    La meme relecture a trouve une seconde contradiction, qu'aucun controle ne
    voyait : la table des regimes d'expansion classait `F` du cote lie, quand
    C10 ter et `expansion_par_ligne` la placent en transition. D'ou le second
    volet ci-dessous, qui confronte le DOCUMENT a la MATRICE au lieu de croire
    l'un ou l'autre sur parole.

    C'est la regle 0 ter appliquee au document lui-meme : un document ne
    contraint pas, un test qui bloque, si.
    """
    import re
    out = []
    doc = os.path.join(ROOT, "docs", "demandes-client.md")
    if not os.path.exists(doc):
        return [Result("T-086", "CONF", "identifiants d'exigences uniques", False,
                       "demandes-client.md introuvable")]
    with open(doc, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    # Une exigence peut etre declaree en tete de ligne (`**B11.**`) ou en puce
    # (`- **G2.**`, section « Ce qui reste a trancher »). Ne reconnaitre que la
    # premiere forme faisait passer G2 pour une citation fantome dans T-093 :
    # c'est le LECTEUR qui etait trop etroit, pas le document qui etait faux.
    ids = re.findall(r"^(?:- )?\*\*([A-Z]{1,2}\d{1,2}(?: bis| ter)?)\.", txt, re.M)
    vus, doubles = set(), []
    for i in ids:
        if i in vus:
            doubles.append(i)
        vus.add(i)
    out.append(Result("T-086", "CONF", "identifiants d'exigences uniques",
                      not doubles, "%d exigence(s) numerotee(s)%s"
                      % (len(ids), "" if not doubles
                         else "  DOUBLON(S) : " + " ".join(sorted(set(doubles))))))

    # ---- T-087 : le document et la matrice disent la meme chose ------------
    with open(MATRIX, encoding="utf-8") as fh:
        m = json.load(fh)
    loi = m["generation"].get("lois_temporelles", {}).get("expansion_par_ligne", {})
    ecarts = []
    for code, regime in loi.items():
        mot = {"lie": "liées", "transition": "transition", "hubble": "Hubble"}[regime]
        # On cherche la ligne du tableau de M4 qui mentionne ce code.
        for ligne in txt.splitlines():
            if ligne.startswith("| `%s`" % code) and "Mpc" in ligne:
                if mot.lower() not in ligne.lower():
                    ecarts.append("%s: matrice %s" % (code, regime))
                break
    # ---- T-093 : aucun controle ne cite une exigence qui n'existe pas -----
    # Trouve le 08/08 : quatre controles citaient « M5 » alors que la section M
    # s'arretait a M4. T-086 verifie qu'un identifiant ne designe pas DEUX
    # choses ; celui-ci verifie qu'il en designe au moins UNE. Une citation
    # fantome est pire qu'une absence de citation : elle donne l'illusion que
    # l'exigence est couverte.
    import glob as _glob
    declares = set(re.findall(r"^(?:- )?\*\*([A-Z]{1,2}\d{1,2}(?: bis| ter)?)\.",
                              txt, re.M))
    cites, fantomes = set(), set()
    for f in _glob.glob(os.path.join(ROOT, "scripts", "harness", "*.py")):
        with open(f, encoding="utf-8", errors="replace") as fh:
            code = fh.read()
        # On ne lit QUE la parenthese finale du libelle : c'est la convention
        # de citation du projet -- « tailles apparentes ~ rayons reels (D7/A9) ».
        # Sans cette restriction, le controle prenait `F2` et `G2` pour des
        # exigences alors que ce sont des METRIQUES (la correlation d'heritage,
        # le gain de toile). Un controle qui invente des defauts se fait
        # desarmer par celui qui le lit : ces deux-la ont ete vus des la
        # premiere execution, ce qui est exactement le role du banc T-079.
        for bloc in re.findall(r'Result\("T-\d+",\s*"[A-Z]+",\s*"[^"]*\(([^")]*)\)"', code):
            for ident in re.findall(r"\b([A-Z]{1,2}\d{1,2}(?: bis| ter)?)\b", bloc):
                cites.add(ident)
                if ident not in declares and not any(
                        d.startswith(ident + " ") for d in declares):
                    fantomes.add(ident)
    out.append(Result("T-093", "CONF",
                      "aucun controle ne cite une exigence inexistante",
                      not fantomes, "%d exigence(s) citee(s)%s"
                      % (len(cites), "" if not fantomes
                         else "  FANTOME(S) : " + " ".join(sorted(fantomes)))))

    out.append(Result("T-087", "CONF",
                      "document et matrice s'accordent sur les regimes (C10 ter/M4)",
                      not ecarts, "%d ligne(s) declaree(s)%s"
                      % (len(loi), "" if not ecarts
                         else "  DESACCORD : " + " ".join(ecarts[:4]))))
    return out


def distances_propres_checks(Result):
    """T-088 a T-091 — M5/D-31 : rien d'affiche n'est en distance comobile.

    Origine : 08/08/2026, arbitrage de Marc, qui renverse D-26. Le comobile
    reste la coordonnee NATURELLE du generateur -- le champ y est statique et
    l'heritage entre lignes n'a de sens que la -- mais plus aucune grandeur
    MONTREE n'est comobile. Les deux ne s'opposent pas : c'est un changement de
    variable a l'affichage, `propre = comobile x a(epoque)`.

    Ce que ces quatre controles refusent :
      T-088  une cellule sans demi-champ propre declare ;
      T-089  un demi-champ propre qui ne suit pas la loi (flot puis figure) ;
      T-090  un regime declare par LIGNE seule, alors qu'il depend de l'EPOQUE ;
      T-091  des horizons publies uniquement en comobile.
    """
    import math
    with open(MATRIX, encoding="utf-8") as fh:
        m = json.load(fh)
    rows = m["zoom_axis"]["rows"]
    cols = m["time_axis"]["columns"]
    ORDER = list("ABCDEFGHIJKLMNO")
    out = []

    tab = m["zoom_axis"].get("demi_champ_propre_mpc")
    manque = [c for c in ORDER if not tab or c not in tab]
    out.append(Result("T-088", "CONF",
                      "chaque ligne declare son demi-champ PROPRE (M1)",
                      not manque, "%d ligne(s) sans valeur%s"
                      % (len(manque), "" if not manque else " : " + " ".join(manque[:5]))))

    # ---- T-089 : l'echelle NE BOUGE PAS avec le temps (M1 bis) -------------
    # REECRIT le 08/08 au soir. La premiere version verifiait la loi INVERSE --
    # un demi-champ propre valant R_ref x a, donc variable avec la colonne. Marc
    # l'a corrige : « la largeur de l'ecran fait toujours la meme distance
    # reelle ». Un cadre qui suit la matiere donne une image ou rien ne bouge et
    # ou seule l'etiquette change ; c'est l'expansion rendue invisible.
    #
    # Le controle exige donc l'exact contraire de ce qu'il exigeait : une valeur
    # UNIQUE par ligne, egale au demi-champ de reference, sans dependance a la
    # colonne. Une table 15x11 est desormais un ECHEC, pas une reussite.
    ecarts = []
    for c in ORDER:
        v = tab.get(c) if tab else None
        if isinstance(v, list):
            ecarts.append("%s: table par colonne" % c)
        elif v is None or abs(float(v) - rows[c]["halfwidth_mpc"]) > 1e-9:
            ecarts.append("%s: %s != R_ref" % (c, v))
    out.append(Result("T-089", "CONF",
                      "l'echelle de distance ne depend pas de l'epoque (M1 bis)",
                      not ecarts, "%d ecart(s)%s"
                      % (len(ecarts), "" if not ecarts else " : " + " ".join(ecarts[:4]))))

    # ---- T-092 : le debordement hors horizon est chiffre (M1 ter / M5) -----
    # A cadre propre fixe, une epoque ancienne fait entrer 1/a fois plus de
    # matiere comobile. Au-dela du sommet de l'echelle, il n'y a PAS de donnee :
    # ce qui est hors de l'horizon est inobservable. La matiere doit alors etre
    # ENGENDREE, sous le principe cosmologique, et cela doit etre ECRIT -- une
    # extrapolation qui ne se declare pas devient indiscernable d'une mesure.
    src = m["zoom_axis"].get("ligne_source_comobile")
    ext = m["zoom_axis"].get("extension_hors_horizon_lignes")
    hyp = m["generation"].get("extension_hors_horizon", {})
    pb = []
    if not src or not ext:
        pb.append("tables absentes")
    else:
        for c in ORDER:
            if len(src.get(c, [])) != len(cols) or len(ext.get(c, [])) != len(cols):
                pb.append("%s incomplet" % c)
                continue
            for j in range(len(cols)):
                # les deux tables doivent se repondre : source connue <=> pas
                # de debordement, source inconnue <=> debordement chiffre
                if (src[c][j] is None) != (ext[c][j] > 0):
                    pb.append("%s%d incoherent" % (c, j))
    for cle in ("hypothese", "autorise", "interdit", "signalisation"):
        if cle not in hyp:
            pb.append("hypothese sans `%s`" % cle)
    out.append(Result("T-092", "CONF",
                      "l'extension hors horizon est chiffree et assumee (M1 ter/M5/M6)",
                      not pb, "%d probleme(s)%s"
                      % (len(pb), "" if not pb else " : " + " ".join(pb[:4]))))

    # ---- T-090 : le regime depend de l'EPOQUE, pas seulement de la ligne ----
    # A la recombinaison rien n'est encore effondre. Une table par ligne seule
    # dirait que la Voie lactee etait deja liee a z = 1100, ce qui est faux et
    # ferait figer son echelle a une epoque ou elle n'existe pas.
    reg = m["zoom_axis"].get("regime_expansion_par_cellule")
    pb = []
    if not reg:
        pb.append("table par cellule absente")
    else:
        for c in ORDER:
            v = reg.get(c)
            if not v or len(v) != len(cols):
                pb.append("%s incomplet" % c)
                continue
            if v[0] != "hubble":
                pb.append("%s declare %s a la colonne 0" % (c, v[0]))
            # une ligne liee ne peut pas se delier en avancant dans le temps
            if "lie" in v and "hubble" in v[v.index("lie"):]:
                pb.append("%s se delie en avancant" % c)
    out.append(Result("T-090", "CONF",
                      "le regime d'expansion depend de l'epoque (M5/C10 ter)",
                      not pb, "%d probleme(s)%s"
                      % (len(pb), "" if not pb else " : " + " ".join(pb[:4]))))

    # ---- T-091 : les horizons sont publies en distance PROPRE --------------
    sans = [c["col"] for c in cols if "horizons_propres_mpc" not in c]
    faux = []
    for c in cols:
        hp = c.get("horizons_propres_mpc")
        if not hp:
            continue
        for k, v in c["horizons"].items():
            if k == "unite":
                continue
            att = v * c["a"]
            if abs(hp.get(k, -1) - att) > max(1e-4, 0.01 * att):
                faux.append("col%d/%s" % (c["col"], k))
    out.append(Result("T-091", "CONF",
                      "les horizons sont publies en distance PROPRE (M5/M2)",
                      not sans and not faux,
                      "%d colonne(s) sans bloc propre, %d valeur(s) fausse(s)%s"
                      % (len(sans), len(faux),
                         "" if not faux else " : " + " ".join(faux[:4]))))
    return out
