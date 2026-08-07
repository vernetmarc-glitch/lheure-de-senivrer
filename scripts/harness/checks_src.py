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
