"""GENERATION DES QUINZE LIGNES — la piece que `bake.py` importe.

Pourquoi ce fichier existe
--------------------------
Jusqu'au 07/08/2026, `bake.py --row` et `--all` echouaient sur
`ModuleNotFoundError: No module named 'bake_impl'`. La commande qui INTERDIT de
cuire a la main ne savait pas cuire : le seul moyen de produire une texture etait
donc exactement la faute que la regle 0 proscrit, et rien ne le signalait
puisque `--check` fonctionnait parfaitement.

Le code de cuisson n'avait jamais ete perdu, il etait seulement DISPERSE :

  - `gen_chain.render_full()` et la correction du champ fin (FINE_N = 480)
    vivaient sur la branche `essai-echelle-15-layers` et pas sur `main` ;
  - l'orchestrateur des sept lignes a sprites n'a jamais ete un fichier : il
    etait ecrit dans un repertoire temporaire, execute, puis efface dans la meme
    commande.

Ce module reconstitue l'orchestrateur et le fige. A partir d'ici, les textures
publiees ont une origine reproductible.

Ce que la cuisson fait, dans l'ordre
------------------------------------
1. LIGNES GENEREES `O` -> `H`, du plus grand au plus petit. Chaque ligne herite
   de sa mere par raccord spectral dans l'espace de Psi (B1). La charge utile
   passe-bas transite par disque : a la ligne `H` elle pese 395 Mo, et la garder
   en memoire pendant que le nuage de points existe suffit a tuer le processus.
2. LIGNES A SPRITES `G` -> `A`. Le fond vient de la texture `H` recadree, le
   champ fin est celui HERITE de la chaine (`_chaine/H.npz`), jamais un champ
   neuf.

Le piege du champ fin, deux fois tombe dedans
---------------------------------------------
`fine_for(code, seed, None, None)` — `None` en position de parent — tire un
champ fin INDEPENDANT a chaque ligne. C'est le defaut que Marc a decrit comme
« enormement de deplacement de matiere entre chaque layer ». Il est passe deux
fois. Ici le champ fin n'est jamais regenere : il descend la chaine.

Le basculement de `OUT_N` n'est pas une bizarrerie
--------------------------------------------------
`fine_lam_hi()` borne la plus grande longueur d'onde du champ fin a partir de
`2*half/OUT_N`, ou `half` est la fenetre VISIBLE. Le rendu, lui, travaille sur la
boite complete marge comprise (480 px). Les deux valeurs sont donc necessaires,
et `OUT_N` bascule autour de l'appel a `fine_for`. Toute simplification de ce
passage change l'echelle physique du champ fin.
"""
import json
import os
import sys
import uuid

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DEV = os.path.join(ROOT, "scripts", "dev")
sys.path.insert(0, DEV)

import gen_chain as G          # noqa: E402
import sprites_layer as S      # noqa: E402

CACHE = os.path.join(DEV, "_chaine")

# Lignes a sprites, du plus grand demi-champ au plus petit. Le germe est celui
# de la cuisson du 06/08 : le changer change l'image.
#
# NOTE — les demi-champs ci-dessous divergent de `spacetime_matrix.json` a la
# quatrieme decimale (`G` 8,9600 contre 8,9615 ; `F` 3,5560 contre 3,5563). Ce
# sont les valeurs qui ont produit les textures en ligne, gardees telles quelles
# pour que la reproduction soit verifiable. L'alignement sur la matrice est un
# changement mesurable, a faire separement et a mesurer — pas a glisser dans une
# reconstitution.
SPRITE_CHAIN = [
    ("G", 8.9600, 101), ("F", 3.5560, 103), ("E", 1.4113, 107),
    ("D", 0.5601, 109), ("C", 0.2223, 113), ("B", 0.0882, 127),
    ("A", 0.0350, 131),
]

GEN_CODES = [c[0] for c in G.CHAIN]          # O ... H
SPRITE_CODES = [c[0] for c in SPRITE_CHAIN]  # G ... A
MARGIN = G.RENDER_MARGIN                     # 1.5
N_TEX = G.FINE_N                             # 480 = OUT_N * MARGIN
OUT_N_NOMINAL = 320                          # fenetre visible, hors marge
HALF_H = dict((c[0], c[1]) for c in G.CHAIN)["H"]


RUN_ID = None


def _provenance(code, out_dir):
    """Note QUI a produit cette ligne, et quand.

    Origine : 07/08/2026. Les quinze textures publiees venaient de TROIS
    cuissons differentes -- `A`/`B` du 05/08 avec la correction d'echelle de la
    Voie lactee, `C` a `G` du 05/08 sans elle, `H` a `O` du 04/08. Les echecs de
    T-012 sur `C->B` et `B->A` enjambaient donc une frontiere de version de code,
    et non un defaut de rendu. Sans trace de provenance, rien ne pouvait le dire.
    """
    import datetime
    import subprocess
    f = os.path.join(out_dir, "provenance.json")
    d = {}
    if os.path.exists(f):
        with open(f) as fh:
            d = json.load(fh)
    try:
        sha = subprocess.check_output(
            ["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        sha = "inconnu"
    d[code] = {"run": RUN_ID, "commit": sha,
               "date": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(f, "w") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1, sort_keys=True)


def _save(img, code, out_dir):
    a = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(a).save(os.path.join(out_dir, "density_%s.png" % code))
    _provenance(code, out_dir)


def bake_generated(codes, out_dir, verbose=True):
    """Cuit les lignes generees demandees, en descendant la chaine depuis `O`.

    L'heritage impose de repartir d'en haut : une ligne ne peut pas etre cuite
    sans la charge utile de sa mere. Les meres deja en cache sont reutilisees,
    ce qui rend `--row J` bien moins couteux que `--all` sans jamais rompre le
    chainage.
    """
    os.makedirs(CACHE, exist_ok=True)
    want = [c for c in GEN_CODES if c in codes]
    if not want:
        return
    deepest = max(GEN_CODES.index(c) for c in want)
    first = 0
    for i in range(deepest, -1, -1):
        if GEN_CODES[i] in codes:
            first = i
    # Toute mere manquante en cache doit etre recuite, meme non demandee.
    while first > 0 and not os.path.exists(
            os.path.join(CACHE, GEN_CODES[first - 1] + ".npz")):
        first -= 1

    for i in range(first, deepest + 1):
        code, half, margin, seed = G.CHAIN[i]
        # La mere transite par DISQUE, jamais par la memoire. A la ligne `H` sa
        # charge utile pese 395 Mo, et la garder vivante pendant que le nuage de
        # points existe suffit a faire tuer le processus par le systeme.
        parent = None
        if i > 0:
            parent = G.load_payload(os.path.join(CACHE, GEN_CODES[i - 1] + ".npz"))
        L = G.bake_layer(code, half, margin, seed, parent)
        del parent
        G.save_payload(L, os.path.join(CACHE, code + ".npz"))
        L.delta_lo = None          # libere APRES l'ecriture, jamais avant
        L.psi_lo = None
        _save(G.render_full(L, seed, margin=MARGIN), code, out_dir)
        if verbose:
            print("  %-3s %10.2f Mpc  cellule %8.4f  rms(Psi) %8.3f  halos %6d"
                  % (code, half, L.cell, L.psi_rms, L.n_halo), flush=True)
        L.drop_heavy()
        del L


def bake_sprites(codes, out_dir, verbose=True):
    """Cuit les lignes a sprites demandees, en descendant depuis `G`.

    Comme pour les lignes generees, le champ fin se transmet : on repart donc de
    `G` des qu'une seule ligne a sprites est demandee.
    """
    want = [c for c in SPRITE_CODES if c in codes]
    if not want:
        return
    deepest = max(SPRITE_CODES.index(c) for c in want)

    hpath = os.path.join(out_dir, "density_H.png")
    if not os.path.exists(hpath):
        raise RuntimeError(
            "density_H.png absent de %s : les lignes a sprites s'appuient sur le "
            "fond de H et ne peuvent pas etre cuites seules." % out_dir)
    H = np.array(Image.open(hpath).convert("L")).astype(np.float32) / 255.0

    fpath = os.path.join(CACHE, "H.npz")
    if not os.path.exists(fpath):
        raise RuntimeError(
            "charge utile H.npz absente : le champ fin des lignes a sprites doit "
            "etre HERITE de la chaine, jamais regenere (defaut du 02/08 et du "
            "06/08). Recuire la ligne H d'abord.")
    fine = np.load(fpath)["fine"]

    ext_H = HALF_H * MARGIN
    half_prev = ext_H
    for idx, (code, half, seed) in enumerate(SPRITE_CHAIN):
        ext = half * MARGIN
        # `fine_for` borne la longueur d'onde sur la fenetre VISIBLE : OUT_N
        # nominal. Le rendu, lui, travaille sur la boite complete.
        G.OUT_N = OUT_N_NOMINAL
        fine = G.fine_for(code, seed + 4242, fine, half_prev / ext, half=half)
        G.OUT_N = N_TEX

        f = ext / ext_H
        w = N_TEX * f
        c = (N_TEX - w) / 2
        yy, xx = np.mgrid[0:N_TEX, 0:N_TEX] * (w / N_TEX) + c
        bg = ndimage.map_coordinates(
            H, np.stack([yy, xx]), order=3, mode="nearest").astype(np.float32)

        tex, n_real, _ = S.build(code, ext, seed, bg, fine, amp=1.0)
        if idx <= deepest:
            _save(tex, code, out_dir)
        if verbose:
            v = int(round(N_TEX / MARGIN))
            c0 = (N_TEX - v) // 2
            print("  %-3s %10.4f Mpc  %3d sprites  moy visible %5.1f  std %5.1f"
                  % (code, half, n_real,
                     tex[c0:c0 + v, c0:c0 + v].mean() * 255, tex.std() * 255),
                  flush=True)
        half_prev = ext
    G.OUT_N = OUT_N_NOMINAL


def bake(rows, out_dir, verbose=True):
    """Point d'entree appele par `bake.py`. Genere en lieu temporaire."""
    global RUN_ID
    RUN_ID = uuid.uuid4().hex[:12]
    codes = set(rows)
    G._calib_fine_norm()
    if verbose:
        print("champ fin calibre (FINE_NORM = %.4f)" % G.FINE_NORM, flush=True)
    bake_generated(codes, out_dir, verbose)
    bake_sprites(codes, out_dir, verbose)


if __name__ == "__main__":
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/bake_manuel"
    os.makedirs(out, exist_ok=True)
    bake(list(sys.argv[1]) if len(sys.argv) > 1 else GEN_CODES + SPRITE_CODES, out)
