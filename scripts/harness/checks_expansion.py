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
