"""BATTERIE DE CONTROLES — organisee par PORTEE, pas par fichier.

Pourquoi ce module existe
-------------------------
Les controles etaient disperses entre invariants.py, validate_raccord.py et
validate_production.py, chacun avec son perimetre et son mode de lancement. Les
regressions sont toutes passees par les trous entre ces trois fichiers :

  02/08  le champ fin des textures de production n'etait pas herite  -> mesure
         faite sur l'apercu, jamais sur ce qui etait livre
  03/08  la Voie lactee passait de 13 % a 47 % du cadre entre deux lignes
         -> AUCUN controle ne comparait la taille d'un objet d'une ligne a
         l'autre

La regle est desormais : un critere n'existe que s'il est ici, et tout ce qui est
ici est execute a chaque cuisson. Un document qu'on doit penser a relire ne
contraint personne ; un test qui bloque la publication, si.

Quatre portees
--------------
  CELL   une image seule
  PAIR   deux lignes voisines -- c'est la portee du couplage
  TIME   deux colonnes voisines (dissolution) -- a activer avec les colonnes
  CONF   conformite du depot : code vs matrice, grille complete, reproductibilite

Chaque controle porte un identifiant T-nnn, sa date et le RETOUR qui l'a motive.
Voir docs/registre-tests.md. Desserrer un seuil oblige a ecrire pourquoi en
regard de ce retour.
"""
import json
import os

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "app", "public", "data")
MATRIX = os.path.join(DATA, "spacetime_matrix.json")
REF = os.path.join(ROOT, "docs", "reference-visuelle", "reference-toile-cosmique.jpg")

ORDER = list("ONMLKJIHGFEDCBA")
SPRITE_ROWS = set("ABCDEFG")
MARGIN = 1.5


class Result:
    __slots__ = ("tid", "scope", "label", "ok", "detail")

    def __init__(self, tid, scope, label, ok, detail=""):
        self.tid, self.scope, self.label = tid, scope, label
        self.ok, self.detail = bool(ok), detail

    def __str__(self):
        return "  %-5s %-6s %-7s %-46s %s" % (
            "OK" if self.ok else "ECHEC", self.tid, self.scope,
            self.label[:46], self.detail)


def matrix():
    with open(MATRIX) as fh:
        return json.load(fh)


def visible(a):
    """Fenetre reellement montree : le centre, hors marge de recadrage."""
    n = a.shape[0]
    v = int(round(n / MARGIN))
    c = (n - v) // 2
    return a[c:c + v, c:c + v]


def _common(par, chi, ratio, lam_px):
    """Ramene deux lignes a la meme fenetre ET a la meme resolution."""
    n = chi.shape[0]
    w = n / ratio
    c0 = (n - w) / 2.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    C = np.stack([c0 + yy * w / n, c0 + xx * w / n])
    p = ndimage.map_coordinates(par.astype(np.float64), C, order=1, mode="nearest")
    s = lam_px / 3.0
    return (ndimage.gaussian_filter(p, s),
            ndimage.gaussian_filter(chi.astype(np.float64), s))


def _corr(a, b):
    a, b = a - a.mean(), b - b.mean()
    d = a.std() * b.std()
    return float((a * b).mean() / d) if d > 0 else float("nan")


def _isotropy(t):
    """Rapport de puissance axes / diagonales. Cible [0,85 ; 1,20].

    REPRISE MOT POUR MOT de `invariants.py:E4_isotropy` (INV-E4). Ce controle
    existait, echouait sur cinq lignes, et a disparu en reorganisant le harnais :
    son echec est alors devenu invisible. Il n'est pas reecrit ici, il est
    RAPATRIE -- une reecriture aurait produit un troisieme seuil et un troisieme
    chiffre incomparables aux deux precedents.
    """
    m = min(t.shape)
    u = t[:m, :m]
    a = (u - u.mean()) * np.hanning(m)[:, None] * np.hanning(m)[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    c = m // 2
    y, x = np.indices(F.shape)
    dy, dx = y - c, x - c
    r = np.hypot(dy, dx)
    A = np.abs(np.degrees(np.arctan2(dy, dx)))
    ang = np.minimum(A, 180 - A)
    b = (r > 3) & (r < m * 0.45)
    return float(F[b & ((ang < 12) | (ang > 78))].mean()
                 / F[b & (np.abs(ang - 45) < 20)].mean())


def _peaks(v):
    """Pics locaux. Detecteur CALIBRE, pas choisi.

    `size=7`, centile 99,5 : ce couple redonne exactement les 382 pics et la
    dispersion de 0,40 mesures a la ligne `O` le 03/08 et consignes au registre.
    Toute autre fenetre donne un autre chiffre (924 pics a size=5) et rendrait
    les mesures d'aujourd'hui incomparables a celles d'hier.
    """
    mx = ndimage.maximum_filter(v, size=7)
    return np.argwhere((v == mx) & (v > np.percentile(v, 99.5)))


def _contrast(v):
    """Contraste relatif : ecart-type sur moyenne. Redonne 0,626 a `J` et
    0,318 a `O`, les deux valeurs bornant la plage consignee au registre."""
    return float(v.std() / max(v.mean(), 1e-9))


def _octaves(v):
    """Largeur de la bande spectrale, en octaves.

    Meme ponderation que T-008 (k^2 P(k), seuil a 20 % du maximum) : les deux
    controles doivent lire le meme spectre, sinon ils peuvent se contredire.
    """
    n = v.shape[0]
    a2 = v - v.mean()
    P = np.abs(np.fft.rfft2(a2)) ** 2
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.rfftfreq(n)[None, :] * n
    k = np.sqrt(ky ** 2 + kx ** 2).ravel()
    idx = np.digitize(k, np.arange(1, n // 2))
    Pk = np.array([P.ravel()[idx == i].mean() if (idx == i).any() else 0.0
                   for i in range(1, n // 2 - 1)])
    kb = np.arange(1, n // 2 - 1)
    w = kb ** 2 * Pk
    band = kb[w > 0.2 * w.max()]
    if len(band) < 2:
        return 0.0
    return float(np.log2(band.max() / band.min()))


def _bright_extent(a, q=99.5):
    """Etendue des zones brillantes, en fraction de la largeur.

    Sert a comparer la TAILLE APPARENTE d'un meme objet d'une ligne a l'autre.
    Mesure le rayon median des composantes connexes au-dessus du centile `q` --
    insensible au niveau general, donc comparable entre deux tons differents.
    """
    n = a.shape[0]
    m = a >= np.percentile(a, q)
    lab, k = ndimage.label(m)
    if k == 0:
        return 0.0
    sizes = ndimage.sum(m, lab, range(1, k + 1))
    sizes = sizes[sizes >= 4]
    if not len(sizes):
        return 0.0
    return float(np.sqrt(np.median(sizes) / np.pi) / n)


# ===========================================================================
# PORTEE CELL
# ===========================================================================
def _noeuds(v):
    """Taux de coincidence entre les pics lumineux et les noeuds de la toile.

    LE controle qui manquait, et le seul qui distingue Millennium d'un ciel
    etoile. Il pose une question que ni le contraste ni le compte de pics ne
    posent : ces points SONT-ILS la toile, ou sont-ils poses par-dessus ?

    Mesure du 07/08 a la ligne `O` : 405 pics, dont 10 % sur les 10 % les plus
    denses de la toile -- exactement le hasard. Les points brillants etaient
    statistiquement INDEPENDANTS de la structure qu'ils etaient censes eclairer.
    Diagnostic de Marc, mot pour mot : « une toile fade, et des points tres
    lumineux poses aleatoirement par-dessus ».

    La toile est approchee par l'image lissee a 4 px : a cette echelle le grain
    de comptage a disparu et la structure demeure.
    """
    fond = ndimage.gaussian_filter(v, 4.0)
    seuil = np.percentile(fond, 80)
    pk = _peaks(v)
    if len(pk) < 8:
        return float("nan"), 0
    return float(np.mean([fond[y, x] > seuil for y, x in pk])), len(pk)


def cell_checks(code, img, m):
    """Controles sur une image seule."""
    r = matrix()["zoom_axis"]["rows"][code]
    v = visible(img)
    out = []
    sp = code in SPRITE_ROWS

    out.append(Result("T-001", "CELL", "aucun aplat (C8)",
                      v.std() * 255 >= 1.0, "%s std %.2f" % (code, v.std() * 255)))
    tgt = m["generation"]["sprites"].get("target_mean_row", {}).get(code, 68.0)
    out.append(Result("T-002", "CELL", "ton conforme a la cible de la ligne (A7)",
                      abs(v.mean() * 255 - tgt) <= 6,
                      "%s %.1f vs %.0f" % (code, v.mean() * 255, tgt)))
    out.append(Result("T-003", "CELL", "saturation claire < 1 % (E4)",
                      (v >= 254 / 255).mean() <= 0.01,
                      "%s %.2f %%" % (code, 100 * (v >= 254 / 255).mean())))
    out.append(Result("T-004", "CELL", "saturation noire < 10 % (E4)",
                      (v <= 8 / 255).mean() <= 0.10,
                      "%s %.1f %%" % (code, 100 * (v <= 8 / 255).mean())))

    med = max(np.median(v), 1e-6)
    ratio = (v.max() if sp else np.percentile(v, 99)) / med
    out.append(Result("T-005", "CELL", "brillances ponctuelles (A3/A4)",
                      ratio >= (2.5 if sp else 1.8), "%s %.1f" % (code, ratio)))

    F = np.abs(np.fft.rfft2(v - v.mean()))
    n = F.shape[0]
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.rfftfreq(n)[None, :] * n
    hi = F[np.sqrt(ky ** 2 + kx ** 2) > n / 12.0]
    pk = hi.max() / np.median(hi) if hi.size and np.median(hi) > 0 else 0
    out.append(Result("T-006", "CELL", "aucun artefact de grille (E5/E6)",
                      pk <= 200 if sp else pk <= 60, "%s x%.0f" % (code, pk)))

    if not sp and not r.get("homogene"):
        import sys
        sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))
        import void_scale as VS
        _, fr, _ = VS.void_scale(v * 255)
        plaf = r.get("void_mpc", r["structure_mpc"])[1]
        vm = fr * 2 * r["halfwidth_mpc"]
        out.append(Result("T-007", "CELL", "taille des vides (B8)",
                          0.025 <= fr <= 0.12 and vm <= plaf * 2,
                          "%s %.1f %% du cadre, %.0f Mpc" % (code, 100 * fr, vm)))

    homog = m["generation"]["champ_fin"]["homogeneity_mpc"]
    a2 = v - v.mean()
    P = np.abs(np.fft.rfft2(a2)) ** 2
    k = np.sqrt(ky ** 2 + kx ** 2).ravel()
    idx = np.digitize(k, np.arange(1, n // 2))
    Pk = np.array([P.ravel()[idx == i].mean() if (idx == i).any() else 0.0
                   for i in range(1, n // 2 - 1)])
    kb = np.arange(1, n // 2 - 1)
    w = kb ** 2 * Pk
    big = n / kb[int(np.argmax(w > 0.2 * w.max()))] * (2 * r["halfwidth_mpc"] / n)
    if not sp:
        # 20 % est le hasard pur, puisque le seuil retient les 20 % les plus
        # denses. Exiger 60 % impose que la MAJORITE des pics soit portee par la
        # toile, sans interdire qu'une minorite tombe ailleurs.
        tx, npk = _noeuds(v)
        out.append(Result("T-078", "CELL", "les pics sont les noeuds de la toile (A1/A5)",
                          tx >= 0.60, "%s %.0f %% des %d pics sur la toile "
                          "(hasard : 20 %%)" % (code, 100 * tx, npk)))
    out.append(Result("T-008", "CELL", "rien au-dela de l'homogeneite (B5)",
                      big <= homog * 1.6, "%s %.0f Mpc" % (code, big)))

    # T-014 — PERTE SECHE, rapatrie le 07/08/2026. Existait sous INV-E4,
    # echouait sur cinq lignes, et a disparu en reorganisant le harnais.
    # Non applique aux lignes a sprites : A14 impose des halos ELLIPTIQUES
    # suivant l'aplatissement du disque, donc une anisotropie voulue.
    if not sp:
        iso = _isotropy(v)
        out.append(Result("T-014", "CELL", "isotropie axes/diagonales (B3)",
                          0.85 <= iso <= 1.20, "%s %.2f" % (code, iso)))

    # T-050 a T-053 — rendu au-dela de l'homogeneite (B9, B10, B11).
    # REECRITS le 07/08 sur precision de Marc. Les versions du matin mesuraient
    # la PLATITUDE PHOTOMETRIQUE -- contraste <= 0,08, pic/mediane <= 1,8.
    # C'etait un contresens : l'uniformite exigee au-dela de l'homogeneite est
    # GEOMETRIQUE et STATISTIQUE -- aucun lieu privilegie, isotropie -- et jamais
    # photometrique. « Comme sur Millennium on doit toujours voir aux noeuds de
    # la toile des points plus lumineux que le reste. »
    # Les seuils ne sont pas desserres : les criteres etaient faux, et ils sont
    # maintenant inverses.
    if r.get("homogene"):
        ct = _contrast(v)
        out.append(Result("T-050", "CELL", "la toile garde de la dynamique (B9)",
                          ct >= 0.10, "%s contraste %.3f" % (code, ct)))
        pm = float(np.percentile(v, 99.9) / max(np.median(v), 1e-9))
        out.append(Result("T-051", "CELL", "des noeuds plus lumineux subsistent (B10)",
                          pm >= 1.5, "%s pic/mediane %.2f" % (code, pm)))
        pk = _peaks(v)
        if len(pk) >= 4:
            from scipy.spatial import cKDTree
            dd, _ = cKDTree(pk).query(pk, k=2)
            disp = float(dd[:, 1].std() / max(dd[:, 1].mean(), 1e-9))
        else:
            disp = float("nan")
        out.append(Result("T-052", "CELL", "distribution amassee, non reguliere (B11)",
                          disp >= 0.50, "%s dispersion %.2f sur %d pics"
                          % (code, disp, len(pk))))
        oc = _octaves(v)
        out.append(Result("T-053", "CELL", "bande spectrale >= 2 octaves (B11)",
                          oc >= 2.0, "%s %.1f octave(s)" % (code, oc)))
    return out


# ===========================================================================
# PORTEE PAIR — la portee du couplage
# ===========================================================================
def pair_checks(pc, cc, pimg, cimg, m):
    rows = matrix()["zoom_axis"]["rows"]
    ratio = rows[pc]["halfwidth_mpc"] / rows[cc]["halfwidth_mpc"]
    a, b = _common(pimg, cimg, ratio, 27.0)
    out = [Result("T-010", "PAIR", "heritage F2 >= 0,85 (B1)",
                  _corr(a, b) >= 0.85, "%s->%s %.3f" % (pc, cc, _corr(a, b)))]

    mx = ndimage.maximum_filter(a, size=5)
    pk = np.argwhere((a == mx) & (a > np.percentile(a, 97)))
    if len(pk) > 200:
        pk = pk[np.argsort(a[pk[:, 0], pk[:, 1]])[::-1][:200]]
    d = []
    for y, x in pk:
        y0, y1 = max(0, y - 8), min(a.shape[0], y + 9)
        x0, x1 = max(0, x - 8), min(a.shape[0], x + 9)
        wn = b[y0:y1, x0:x1]
        dy, dx = np.unravel_index(int(np.argmax(wn)), wn.shape)
        d.append(np.hypot((y0 + dy) - y, (x0 + dx) - x))
    dm = float(np.median(d)) if d else 0.0
    out.append(Result("T-011", "PAIR", "deplacement median <= 3 px (B2/D2)",
                      dm <= 3.0, "%s->%s %.1f px" % (pc, cc, dm)))

    # T-012 : LE CONTROLE QUI MANQUAIT. Un meme objet doit garder une taille
    # apparente coherente d'une ligne a l'autre. Sans lui, la Voie lactee est
    # passee de 13 % a 47 % du cadre sans que rien ne le signale (03/08).
    ep, ec = _bright_extent(visible(pimg)), _bright_extent(visible(cimg))
    if ep > 0 and ec > 0:
        # l'enfant zoome d'un facteur `ratio` : l'objet doit grandir d'autant,
        # a 60 % pres pour tolerer l'arrivee de nouveaux objets plus fins.
        att = ep * ratio
        rr = ec / att if att > 0 else 0
        out.append(Result("T-012", "PAIR", "taille apparente des objets coherente",
                          0.4 <= rr <= 2.5, "%s->%s x%.2f" % (pc, cc, rr)))

    tp, tc = visible(pimg).mean() * 255, visible(cimg).mean() * 255
    out.append(Result("T-013", "PAIR", "ton sans saut (D2)",
                      abs(tp - tc) <= 12, "%s->%s %.0f -> %.0f" % (pc, cc, tp, tc)))
    return out


# ===========================================================================
# PORTEE TIME — dissolution. Actif des que les colonnes existent.
# ===========================================================================
def time_checks(code, col_hi, col_lo, img_hi, img_lo):
    """Deux colonnes voisines d'une meme ligne, `col_hi` plus recente.

    Les trois criteres qui portent la dissolution :
      C4  rien n'apparait en remontant le temps -> le contraste ne remonte pas
      C1  les structures s'etalent ET palissent  -> les objets grossissent
      C8  du grain subsiste jusqu'au bout        -> jamais d'aplat
    """
    vh, vl = visible(img_hi), visible(img_lo)
    out = [Result("T-020", "TIME", "aucune structure n'apparait (C4)",
                  vl.std() <= vh.std() * 1.05,
                  "%s c%d->c%d std %.1f -> %.1f" % (code, col_hi, col_lo,
                                                    vh.std() * 255, vl.std() * 255))]
    eh, el = _bright_extent(vh), _bright_extent(vl)
    out.append(Result("T-021", "TIME", "les objets s'etalent (C1)",
                      el >= eh * 0.95, "%s %.3f -> %.3f" % (code, eh, el)))
    # C3 — les points ne palissent pas sur place : ils s'ETIRENT le long des
    # filaments. Mesure : l'elongation des structures brillantes augmente
    # pendant la dissolution, au lieu de rester ronde.
    import checks_image as _CI
    e_hi, e_lo = _CI._elongation(img_hi), _CI._elongation(img_lo)
    out.append(Result("T-068", "TIME", "dissolution le long des filaments (C3)",
                      e_lo >= e_hi * 0.9, "%s %.2f -> %.2f" % (code, e_hi, e_lo)))
    # C5 — hierarchie : les GRANDES structures se defont en premier. Mesure :
    # l'energie basse frequence chute plus vite que la haute frequence.
    def _bande(u, bas):
        a = u - u.mean()
        P = np.abs(np.fft.rfft2(a)) ** 2
        n = a.shape[0]
        ky = np.fft.fftfreq(n)[:, None] * n
        kx = np.fft.rfftfreq(n)[None, :] * n
        k = np.sqrt(ky ** 2 + kx ** 2)
        m_ = (k > 0) & ((k < n / 16.0) if bas else (k > n / 8.0))
        return float(P[m_].sum())
    rb = _bande(img_lo, True) / max(_bande(img_hi, True), 1e-12)
    rh = _bande(img_lo, False) / max(_bande(img_hi, False), 1e-12)
    out.append(Result("T-069", "TIME", "les grandes structures se defont d'abord (C5)",
                      rb <= rh, "%s basses x%.2f, hautes x%.2f" % (code, rb, rh)))
    # C6 — jamais de fond noir, luminosite moyenne CONSTANTE jusqu'a
    # l'embrasement. La colonne 0 porte seule la montee (C7).
    dm = abs(img_hi.mean() - img_lo.mean()) * 255
    out.append(Result("T-070", "TIME", "luminosite moyenne constante (C6)",
                      dm <= 6.0 or col_lo == 0, "%s %.1f /255" % (code, dm)))
    # C7 — l'embrasement final : la colonne 0, et elle seule, monte vers le
    # blanc. C'est le seul moment ou la luminosite moyenne augmente.
    if col_lo == 0:
        out.append(Result("T-071", "TIME", "embrasement a la colonne 0 (C7)",
                          img_lo.mean() > img_hi.mean(),
                          "%s %.1f -> %.1f /255" % (code, img_hi.mean() * 255,
                                                    img_lo.mean() * 255)))
    # C12 — aux plus grandes echelles, remonter le temps CONTRACTE les
    # structures : l'image se densifie vers la haute frequence. C'est le pendant
    # temporel de B3.
    if code in ("O", "N", "M"):
        out.append(Result("T-072", "TIME", "contraction aux grandes echelles (C12)",
                          _bande(img_lo, False) / max(_bande(img_lo, True), 1e-12)
                          >= _bande(img_hi, False) / max(_bande(img_hi, True), 1e-12),
                          "%s" % code))
    out.append(Result("T-022", "TIME", "grain conserve, jamais d'aplat (C8)",
                      vl.std() * 255 >= 1.0, "%s std %.2f" % (code, vl.std() * 255)))
    return out


# ===========================================================================
# PORTEE CONF
# ===========================================================================
def plan_completeness():
    """Le plan de test est-il entierement implemente ?

    Origine : 03/08/2026, question de Marc -- « est-ce que l'ensemble des tests
    est bien implemente et leur execution forcee ? ». Elle etait fondee : 18
    controles sur 52 declares etaient ecrits, et RIEN ne le signalait. Une
    session suivante aurait lu « 153 passes, 14 en echec » et conclu que le plan
    tenait.

    Ce controle compare les identifiants declares dans docs/registre-tests.md a
    ceux reellement implementes ici. Il ECHOUE tant qu'il en manque, et nomme les
    manquants. C'est ce qui empeche le plan de test de deriver comme le reste a
    derive : un plan qui n'est pas execute n'est pas un plan.
    """
    import re
    reg = os.path.join(ROOT, "docs", "registre-tests.md")
    if not os.path.exists(reg):
        return Result("T-000", "CONF", "plan de test complet", False,
                      "registre introuvable")
    declared = set(re.findall(r"T-\d{3}", open(reg).read()))
    declared.discard("T-000")
    # Balaye TOUT le harnais, pas le seul fichier courant : la batterie est
    # repartie sur plusieurs modules depuis le 07/08, et ne regarder qu'ici
    # ferait croire a un plan incomplet alors qu'il ne l'est pas.
    impl = set()
    for f in sorted(os.listdir(HERE)):
        if f.endswith(".py"):
            impl |= set(re.findall(r'"(T-\d{3})"', open(os.path.join(HERE, f)).read()))
    missing = sorted(declared - impl)
    return Result("T-000", "CONF",
                  "plan de test complet (%d/%d)" % (len(declared) - len(missing),
                                                    len(declared)),
                  not missing,
                  "%d a ecrire : %s" % (len(missing), " ".join(missing[:8])
                                        + ("…" if len(missing) > 8 else "")))


def global_checks(img, m):
    """Controles qui portent sur TOUTE l'echelle, pas sur une image ni sur une
    paire. Une seule entree pour l'instant : la decroissance du contraste."""
    rows = [c for c in ORDER if c in img and c not in SPRITE_ROWS]
    if len(rows) < 3:
        return []
    # ORDER va du plus grand demi-champ au plus petit : en le remontant, on va
    # vers les GRANDES echelles, ou le contraste doit decroitre (B9). Sans
    # coupure : c'est une decroissance continue qui est exigee, pas un seuil.
    ct = [_contrast(visible(img[c])) for c in rows]
    # `rows[0]` est la PLUS GRANDE echelle. En allant vers les grandes echelles
    # -- donc en remontant l'indice vers 0 -- le contraste doit DECROITRE (B9).
    # Une rupture est donc un contraste qui remonte quand l'echelle grandit.
    bad = [rows[i] for i in range(len(ct) - 1) if ct[i] > ct[i + 1] + 0.02]
    return [Result("T-049", "CONF", "contraste decroissant vers les grandes echelles (B9)",
                   not bad, "%s %.3f -> %s %.3f%s"
                   % (rows[-1], ct[-1], rows[0], ct[0],
                      "  rupture : " + " ".join(bad) if bad else ""))]


def requirement_coverage():
    """T-055 — CHAQUE EXIGENCE CLIENT a-t-elle un controle ?

    T-000 verifie que le plan de test est entierement implemente. Il ne dit rien
    d'un tout autre trou : une exigence que le plan n'a jamais prevue. Les deux
    sont necessaires -- un plan complet peut rester aveugle.

    Ce controle lit les identifiants d'exigence rediges dans
    `docs/demandes-client.md` et les compare a ceux cites par les controles du
    harnais. Il ECHOUE tant qu'une exigence n'est couverte par aucun test, et les
    nomme.

    Origine : 07/08/2026, demande de Marc -- « confirme que l'ensemble de ces
    demandes ont bien chacune un ou plusieurs tests ». Une confirmation faite a
    la main est vraie le jour ou on la fait ; un controle la refait a chaque
    cuisson.

    Les sections J, K et L (parcours guides, fluidite, dispositif) portent sur
    l'APPLICATION et non sur les textures : elles sont hors du perimetre du
    harnais et listees a part plutot que comptees comme des trous.
    """
    import re
    doc = os.path.join(ROOT, "docs", "demandes-client.md")
    if not os.path.exists(doc):
        return Result("T-055", "CONF", "couverture des exigences", False,
                      "demandes-client.md introuvable")
    redigees = set(re.findall(r"^\*\*([A-EH]\d{1,2})\.", open(doc).read(), re.M))
    citees = set()
    for f in sorted(os.listdir(HERE)):
        if f.endswith(".py"):
            txt = open(os.path.join(HERE, f)).read()
            for m_ in re.findall(r'Result\(\s*"T-\d{3}"\s*,\s*"[A-Z]+"\s*,\s*"([^"]*)"', txt):
                citees |= set(re.findall(r"\b([A-EH]\d{1,2})\b", m_))
    nues = sorted(redigees - citees,
                  key=lambda x: (x[0], int(x[1:])))
    return Result("T-055", "CONF",
                  "toute exigence a un controle (%d/%d)"
                  % (len(redigees) - len(nues), len(redigees)),
                  not nues,
                  "%d sans controle : %s" % (len(nues), " ".join(nues)) if nues
                  else "%d exigences couvertes" % len(redigees))


def chronologie_checks(m):
    """C9, C10, C11, D3 — la grille du temps est-elle une vraie chronologie ?

    Ces quatre-la se verifient AVANT les colonnes, sur la matrice : si l'axe du
    temps est mal date, cuire 165 cellules ne le corrigera pas.
    """
    out = []
    cols = m["time_axis"]["colonnes"] if "colonnes" in m["time_axis"] \
        else m["time_axis"]["columns"]
    # C9 — aujourd'hui est EXACT : la derniere colonne porte a = 1 et
    # l'amplitude pleine, sans transition ni saut.
    der = cols[-1]
    out.append(Result("T-073", "CONF", "aujourd'hui est exact (C9)",
                      abs(der["a"] - 1.0) <= 1e-6 and abs(der["amp"] - 1.0) <= 1e-6,
                      "colonne %d : a=%.6f amp=%.6f" % (der["col"], der["a"], der["amp"])))
    # C11 — datation juste : chaque colonne doit retomber sur la table
    # cosmologique, a 2 % pres. Le curseur doit se lire comme une vraie
    # chronologie, pas comme un reglage esthetique.
    import json as _j
    tb = os.path.join(DATA, "cosmology_table.json")
    if os.path.exists(tb):
        rows = _j.load(open(tb))["rows"]
        aa = np.array([r["a"] for r in rows])
        tt = np.array([r["t_Gyr"] for r in rows])
        bad = []
        for c in cols:
            att = float(np.interp(c["a"], aa, tt))
            if abs(att - c["t_gyr"]) > max(0.02 * att, 0.01):
                bad.append("c%d %.3f vs %.3f Ga" % (c["col"], c["t_gyr"], att))
        out.append(Result("T-074", "CONF", "datation juste de la dissolution (C11)",
                          not bad, " ".join(bad[:3]) if bad
                          else "%d colonnes conformes a la table" % len(cols)))
        # C10 — l'expansion suit la meme cosmologie que les trois spheres. Deux
        # cosmologies differentes dans la meme oeuvre rendraient les horizons
        # faux par rapport au fond de carte.
        decl = m["time_axis"].get("cosmology", {})
        meta = _j.load(open(tb))["meta"]
        ecarts = [k for k in ("H0_km_s_Mpc", "omega_m", "omega_lambda")
                  if k in decl and abs(float(decl[k]) - float(meta[k])) > 1e-6]
        out.append(Result("T-075", "CONF", "une seule cosmologie pour tout (C10)",
                          bool(decl) and not ecarts,
                          "ecarts : %s" % " ".join(ecarts) if ecarts
                          else ("declaree" if decl else "AUCUNE cosmologie declaree "
                                "dans time_axis")))
    # D3 — coherence croisee : la grille doit etre RIGIDE. Toutes les lignes
    # portent les memes colonnes ; un axe du temps prive par ligne casse la
    # comparaison entre epoques (matrice v3, ecartee le 30/07).
    rows_ = m["zoom_axis"]["rows"]
    prives = [c for c, r in rows_.items()
              if "keyframes_a" in r or "dissolution_window_a" in r]
    out.append(Result("T-076", "CONF", "grille rigide, coherence croisee (D3)",
                      not prives and len(cols) == 11,
                      "%d colonnes communes%s" % (len(cols),
                      "  axes prives : " + " ".join(prives) if prives else "")))
    return out


def conf_checks(d, m):
    out = [plan_completeness(), requirement_coverage()]
    out += chronologie_checks(m)
    try:
        import checks_oeuvre as CO
        out += CO.oeuvre_checks()
        out += CO.construction_checks()
    except Exception as e:
        out.append(Result("T-060", "OEUVRE", "les trois spheres", False, str(e)[:60]))
    missing = [c for c in ORDER
               if not os.path.exists(os.path.join(d, "density_%s.png" % c))]
    out.append(Result("T-030", "CONF", "les 15 lignes existent (B6)",
                      not missing, " ".join(missing)))
    # T-054 — PUBLICATION PARTIELLE. Ajoute le 07/08 apres avoir constate que
    # les 15 textures en ligne provenaient de TROIS cuissons. La regle 0 dit
    # « jamais de publication partielle » ; jusqu'ici rien ne la faisait
    # respecter, et le melange etait indetectable a l'oeil comme a la mesure.
    prov = os.path.join(d, "provenance.json")
    if not os.path.exists(prov):
        out.append(Result("T-054", "CONF", "provenance homogene des 15 lignes",
                          False, "provenance.json absent : origine inconnue"))
    else:
        with open(prov) as fh:
            pv = json.load(fh)
        runs = set(v.get("run") for v in pv.values())
        manque = [c for c in ORDER if c not in pv]
        out.append(Result("T-054", "CONF", "provenance homogene des 15 lignes",
                          len(runs) == 1 and not manque,
                          "%d cuisson(s)%s" % (len(runs),
                                               "  sans trace : " + " ".join(manque)
                                               if manque else "")))
    out.append(Result("T-031", "CONF", "parametres figes dans la matrice",
                      bool(m.get("generation")), ""))
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))
    try:
        import gen_chain as GC
        loaded = getattr(GC, "PARAMS_LOADED", False)
        bad = [k for k, v in (("OUT_N", m["generation"]["render"]["out_n"]),
                              ("FINE_A", m["generation"]["champ_fin"]["a"]),
                              ("SUB_Z", m["generation"]["raccord"]["sub_z"]))
               if abs(float(getattr(GC, k)) - float(v)) > 1e-9]
        out.append(Result("T-032", "CONF", "le code lit la matrice (INV-G2)",
                          loaded and not bad, " ".join(bad)))
    except Exception as e:
        out.append(Result("T-032", "CONF", "le code lit la matrice", False, str(e)[:50]))
    return out


def run_all(d, cells=True, pairs=True, conf=True):
    """Toute la batterie sur un repertoire de textures."""
    from PIL import Image
    m = matrix()
    img = {}
    for c in ORDER:
        f = os.path.join(d, "density_%s.png" % c)
        if os.path.exists(f):
            img[c] = np.asarray(Image.open(f).convert("L"), np.float64) / 255.0
    res = []
    if conf:
        res += conf_checks(d, m)
        res += global_checks(img, m)
    if conf:
        try:
            import checks_dissolution as CD
            res += CD.dissolution_checks()
            res += CD.resolution_checks(d)
        except Exception as e:
            res.append(Result("T-036", "CONF", "dissolubilite", False, str(e)[:60]))
        try:
            import checks_src as CS
            res += CS.src_checks()
        except Exception as e:
            res.append(Result("T-048", "SRC", "sprites sources", False, str(e)[:60]))
    import checks_image as CI
    if cells:
        for c in ORDER:
            if c in img:
                res += cell_checks(c, img[c], m)
                res += CI.image_cell_checks(c, img[c], m)
    if pairs:
        for i in range(len(ORDER) - 1):
            p, c = ORDER[i], ORDER[i + 1]
            if p in img and c in img:
                res += pair_checks(p, c, img[p], img[c], m)
                res += CI.image_pair_checks(p, c, img[p], img[c], m)
    return res
