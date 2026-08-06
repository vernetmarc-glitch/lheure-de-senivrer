"""COMMANDE UNIQUE DE CUISSON — tout ou rien.

    python3 bake.py --check              controle l'etat publie, ne genere rien
    python3 bake.py --row J              regenere une ligne et ses voisines
    python3 bake.py --all                regenere les 15 lignes
    python3 bake.py --baseline           fige l'etat courant comme reference

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


def report(res):
    fails = [r for r in res if not r.ok]
    by = {}
    for r in res:
        by.setdefault(r.scope, []).append(r)
    for scope in ("CONF", "CELL", "PAIR", "TIME"):
        if scope not in by:
            continue
        bad = [r for r in by[scope] if not r.ok]
        print("\n-- %s : %d controles, %d en echec --"
              % (scope, len(by[scope]), len(bad)))
        for r in bad:
            print(r)
    print("\n" + "=" * 74)
    print("%d controles passes, %d en echec" % (len(res) - len(fails), len(fails)))
    return fails


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
        print("\nPUBLIE.")
        shutil.rmtree(tmp, ignore_errors=True)
        return 0
    except Exception:
        print("\nECHEC DE GENERATION — l'etat publie n'a pas ete touche.")
        raise


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
