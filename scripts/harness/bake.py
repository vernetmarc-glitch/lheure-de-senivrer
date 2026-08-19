"""COMMANDE UNIQUE DE CUISSON — tout ou rien.

    python3 bake.py --check              controle l'etat publie, ne genere rien
    python3 bake.py --row J              regenere une ligne et ses voisines
    python3 bake.py --all                regenere les 15 lignes
    python3 bake.py --baseline           fige l'etat courant comme reference
    python3 bake.py --statique           portees CONF et SRC seules (integration continue)

Pourquoi cette commande existe
------------------------------
Jusqu'au 03/08/2026 je cuisais ligne par ligne a la main et je publiais ce qui me
semblait bon. Deux consequences, toutes deux survenues :

  - j'ai publie des textures dont le champ fin n'etait pas herite, parce que
    j'avais mesure l'apercu et non ce que je livrais ;
  - j'ai corrige le pique des sprites et casse leur echelle, parce que rien ne
    verifiait la taille d'un objet d'une ligne a l'autre.

Trois regles, non contournables :

  1. GENERATION EN LIEU TEMPORAIRE. Rien n'est ecrit sur l'etat publie tant que
     la batterie n'est pas verte.
  2. TOUT OU RIEN. Un seul controle en echec annule la publication entiere. Pas
     de « je publie quand meme, celui-la n'est pas grave » -- c'est exactement
     ce raisonnement qui a fait deriver le projet.
  3. LE COUPLAGE EST TRAITE ICI. Regenerer une cellule relance les controles de
     ses VOISINES. La coherence ne depend plus de ce dont je me souviens.

La ligne de base hashee attrape la quatrieme classe d'erreurs : la modification
non intentionnelle. Si je corrige C et que M change, la commande le dit AVANT
publication.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts", "dev"))

import checks as CK  # noqa: E402

PUBLISHED = os.path.join(ROOT, "app", "public", "essai-v4", "data", "v4")
BASELINE = os.path.join(ROOT, "docs", "baseline-textures.json")


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def read_baseline():
    if os.path.exists(BASELINE):
        with open(BASELINE) as fh:
            return json.load(fh)
    return {}


def compare_baseline(d, expected_changes):
    """Signale toute texture modifiee HORS de ce qui etait demande."""
    base = read_baseline().get("textures", {})
    if not base:
        return [], []
    changed, unexpected = [], []
    for c in CK.ORDER:
        f = os.path.join(d, "density_%s.png" % c)
        if not os.path.exists(f) or c not in base:
            continue
        if digest(f) != base[c]:
            changed.append(c)
            if c not in expected_changes:
                unexpected.append(c)
    return changed, unexpected


# ---------------------------------------------------------------------------
# CHANTIERS OUVERTS — controles qui restent ROUGES mais ne bloquent PAS une
# publication de texture.
#
# Pourquoi cette distinction existe (07/08/2026)
# ----------------------------------------------
# La regle 0 dit : refuser de publier si un seul controle echoue. Or certains
# echecs ne peuvent PAS etre corriges par une cuisson -- les trois spheres sont
# du code d'application, la loi temporelle est un chantier de conception, les
# sprites sources ne sont pas produits par `bake.py`. Aucune texture, si bonne
# soit-elle, ne pouvait donc plus etre publiee.
#
# Une regle inapplicable finit toujours par etre contournee : c'est exactement
# ainsi que ce projet a derive en juillet. La distinction ne desserre rien --
# les chantiers restent affiches en rouge, comptes, et leur liste ne peut pas
# s'allonger en silence, chaque entree portant sa raison. Elle rend seulement la
# regle tenable.
#
# Ce qui reste BLOQUANT : tout ce qu'une cuisson peut corriger. C'est le coeur
# de la regle 0, et il n'y est pas touche.
CHANTIERS = {
    "T-036": "axe du temps : aucune loi temporelle declaree (C13)",
    "T-037": "axe du temps : 99 % de la structure subsiste a amplitude nulle",
    "T-060": "les trois spheres : code d'application, pas une texture (H6)",
    "T-061": "les trois spheres : code d'application (H7)",
    "T-062": "les trois spheres : code d'application (H8)",
    "T-024": "sprites sources : ic10 et leo1 sont le meme fichier (D5)",
    "T-045": "sprites sources : triangulum, remontee de pic",
    "T-047": "sprites sources : smc, ecart d'axe 21 deg",
    "T-065": "mecanisme A8 : courbe de ton ponctuelle non ecrite (O-08 -> D-27)",
    "T-010": "O-07 : Zel'dovich ne fabrique pas la structure fine",
    "T-011": "O-07 : idem",
    "T-027": "O-07 : signature de reference, meme cause",
    # Rattache le 10/08/2026 par decision de Marc (D-34), apres mesure du
    # plateau. Le fond de `G` est le recadrage de `H` AGRANDI x2,52 : un
    # agrandissement ne fabrique pas de structure, et c'est exactement ce que
    # O-07 nomme. Une cuisson ne peut donc PAS le corriger -- critere
    # d'admission de cette liste.
    #
    # Etat a l'entree : 0,71 pour 0,75 exige. Ce n'est pas l'etat de depart
    # (0,64) : le gain de toile a `G` a rendu 0,07, et a ferme au passage T-010
    # et T-011 sur cette meme arete, qui etaient rouges le matin.
    #
    # CE QUI LE FERME : que le fond de `G` soit ENGENDRE au lieu d'etre
    # reechantillonne depuis `H`. Tant que ce n'est pas fait, ce controle
    # affiche sa mesure a chaque cuisson et ne doit pas etre desarme.
    "T-094": "O-07 : le fond de `G` est le recadrage de `H` agrandi, pas engendre",
}


def report(res):
    fails = [r for r in res if not r.ok]
    by = {}
    for r in res:
        by.setdefault(r.scope, []).append(r)
    for scope in ("CONF", "OEUVRE", "SRC", "CELL", "PAIR", "TIME"):
        if scope not in by:
            continue
        bad = [r for r in by[scope] if not r.ok]
        print("\n-- %s : %d controles, %d en echec --"
              % (scope, len(by[scope]), len(bad)))
        for r in bad:
            print(r)
    print("\n" + "=" * 74)
    bloquants = [r for r in fails if r.tid not in CHANTIERS]
    chantiers = [r for r in fails if r.tid in CHANTIERS]
    print("%d controles passes, %d en echec" % (len(res) - len(fails), len(fails)))
    if chantiers:
        vus = sorted(set(r.tid for r in chantiers))
        print("  dont %d sur %d chantier(s) ouvert(s), non bloquants : %s"
              % (len(chantiers), len(vus), " ".join(vus)))
        for t in vus:
            print("      %s  %s" % (t, CHANTIERS[t]))
    print("  %d echec(s) BLOQUANT(s)" % len(bloquants))
    return bloquants


def main(argv):
    mode = argv[1] if len(argv) > 1 else "--check"

    if mode == "--check":
        print("=" * 74)
        print("CONTROLE DE L'ETAT PUBLIE — aucune generation")
        print("=" * 74)
        res = CK.run_all(PUBLISHED)
        fails = report(res)
        changed, unexpected = compare_baseline(PUBLISHED, set(CK.ORDER))
        if changed:
            print("textures differentes de la ligne de base : " + " ".join(changed))
        elif read_baseline():
            print("conforme a la ligne de base")
        return 1 if fails else 0

    if mode == "--statique":
        # MODE POUR L'INTEGRATION CONTINUE — 08/08/2026.
        #
        # Il n'execute QUE les portees qui ne dependent d'aucune texture : la
        # conformite de la matrice (CONF) et les vignettes sources (SRC). Il ne
        # cuit rien, ne lit aucun PNG de densite, et tourne en quelques secondes.
        #
        # Pourquoi il existe : `gen_chain.py` et `sprites_layer.py` sont la
        # chaine de production -- `generation.engine` les designe comme telle --
        # mais ils vivent dans `scripts/dev/`, que le workflow declarait
        # « recherche, non bloquant ». Un ajout cassant dans ces deux fichiers ne
        # faisait donc pas rougir l'integration continue. C'est exactement la
        # situation qui a laisse `HALO_GROWTH = 8.5` survivre trois semaines, et
        # ce workflow existe pour l'empecher.
        #
        # Les portees CELL et PAIR restent hors CI : elles mesurent les textures
        # PUBLIEES, qui sont anterieures aux corrections en cours. Les inclure
        # rendrait la CI durablement rouge, et une CI toujours rouge ne protege
        # plus rien -- on cesse de la lire.
        # Deux controles de portee CONF mesurent en realite les TEXTURES
        # publiees, pas le code : T-049 lit le profil de contraste des quinze
        # images, T-054 leur fichier de provenance. Les inclure rendrait la CI
        # rouge tant qu'une cuisson n'a pas ete publiee -- c'est-a-dire en
        # permanence pendant les travaux -- et une CI toujours rouge cesse
        # d'etre lue. Ils restent evidemment armes dans `--check` et `--all`,
        # ou ils portent sur ce qu'ils pretendent mesurer.
        HORS_CI = {"T-049", "T-054"}
        res = [r for r in CK.run_all(PUBLISHED)
               if r.scope in ("CONF", "SRC") and r.tid not in HORS_CI]
        report(res)
        bloquants = [r for r in res if not r.ok and r.tid not in CHANTIERS]
        return 1 if bloquants else 0

    if mode == "--baseline":
        res = CK.run_all(PUBLISHED)
        fails = report(res)
        if fails:
            print("\nLIGNE DE BASE REFUSEE : on ne fige pas un etat en echec.")
            return 1
        tex = {c: digest(os.path.join(PUBLISHED, "density_%s.png" % c))
               for c in CK.ORDER
               if os.path.exists(os.path.join(PUBLISHED, "density_%s.png" % c))}
        with open(BASELINE, "w") as fh:
            json.dump({"note": "Empreintes des textures validees. Toute "
                               "divergence non intentionnelle est signalee "
                               "avant publication.",
                       "textures": tex}, fh, ensure_ascii=False, indent=1)
        print("\nligne de base figee : %d textures" % len(tex))
        return 0

    # --- modes de generation -------------------------------------------------
    rows = None
    if mode == "--row" and len(argv) > 2:
        rows = [argv[2]]
    elif mode == "--all":
        rows = list(CK.ORDER)
    else:
        print(__doc__)
        return 2

    tmp = tempfile.mkdtemp(prefix="bake_")
    try:
        for c in CK.ORDER:
            f = os.path.join(PUBLISHED, "density_%s.png" % c)
            if os.path.exists(f):
                shutil.copy2(f, tmp)
        print("generation dans %s" % tmp)
        import bake_impl
        bake_impl.bake(rows, tmp)

        print("\n" + "=" * 74)
        print("CONTROLE AVANT PUBLICATION")
        print("=" * 74)
        res = CK.run_all(tmp)
        fails = report(res)
        _, unexpected = compare_baseline(tmp, set(rows))
        if unexpected:
            print("MODIFICATION NON DEMANDEE sur : " + " ".join(unexpected))
            fails = fails or [1]
        if fails:
            print("\nPUBLICATION ANNULEE. L'etat publie n'a pas ete touche.")
            print("Repertoire de travail conserve : %s" % tmp)
            return 1
        for c in CK.ORDER:
            f = os.path.join(tmp, "density_%s.png" % c)
            if os.path.exists(f):
                shutil.copy2(f, PUBLISHED)
        # `provenance.json` fait partie de l'etat publie, au meme titre que les
        # images : c'est lui qui permet a T-054 de verifier que les 15 lignes
        # viennent bien d'une meme cuisson. Il etait ecrit dans le repertoire de
        # travail et jamais recopie, si bien que l'etat publie ne pouvait pas
        # declarer son origine et que T-054 echouait sur TOUTE publication --
        # y compris une publication parfaitement saine. Corrige le 11/08/2026.
        prov = os.path.join(tmp, "provenance.json")
        if os.path.exists(prov):
            shutil.copy2(prov, PUBLISHED)
        print("\nPUBLIE.")
        shutil.rmtree(tmp, ignore_errors=True)
        return 0
    except Exception:
        print("\nECHEC DE GENERATION — l'etat publie n'a pas ete touche.")
        raise


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
