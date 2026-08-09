# État des lieux — 7 août 2026, fin de session

**À lire en premier, avant `registre-tests.md`.** Instantané **courant**,
réécrit à chaque session. Les autres registres sont chronologiques et
contiennent, par construction, des affirmations **périmées** que ce document
tranche.

Commit de référence : `65b07d7`. Dépôt propre, poussé, intégration continue au
vert.

> **La version précédente de ce document datait du 30 juillet** et portait un
> bandeau « ⛔ LA CUISSON EST INTERDITE EN L'ÉTAT ». Cette interdiction **est
> levée** : `bake.py` cuit, mesure et refuse tout seul. L'ancienne version est
> conservée sous `archive-etat-des-lieux-30-07.md` pour la traçabilité — elle ne
> décrit plus rien d'actuel.

---

## 1. Le piège à connaître avant de lire quoi que ce soit

`registre-tests.md` s'écrit **par ajout**, en ordre chronologique. Plusieurs
sections décrivent des seuils **inversés le jour même**. En cas de contradiction,
**ce document et le code font foi**, jamais une section antérieure du registre.

| Contrôle | Version périmée (matin du 07/08) | En vigueur |
|---|---|---|
| **T-050** | contraste ≤ 0,08 | **contraste ≥ 0,10** |
| **T-051** | pic/médiane ≤ 1,8 | **pic/médiane ≥ 1,5** |
| **T-047** | halo et disque de même aplatissement | **grand axe du halo aligné sur le disque** |
| **T-019** | la Voie lactée ne chevauche personne | **elle est dessinée dessous** |
| **T-028** | preuve « toile et non mousse » | **indicatif seulement, ne prouve rien** |
| **B10** | « rien ne doit s'y détacher » | **uniformité géométrique, pas photométrique** |

---

## 2. Ce qui est en ligne, et ce qui ne l'est pas

| | État |
|---|---|
| **Application** | ✅ à jour. Les **trois sphères** sont tracées et déployées depuis `db3d508` (API Pages : `built`) |
| **Textures publiées** | ⚠️ **périmées** — celles des 4 et 5 août, issues de **trois cuissons différentes** (`adc3dba`, `db11e1e`, `c9bc464`) |
| **Générateur** | ✅ à jour, contient toutes les corrections du 07/08 |

L'écart est **intentionnel** : le harnais refuse de publier tant qu'un contrôle
bloquant échoue. Une cuisson complète (`bake.py --all`, ≈ 25 min) reproduit
l'état corrigé.

### Les deux chiffres à ne pas confondre

| Mesure | Passés | Échecs | Bloquants |
|---|---|---|---|
| `bake.py --check` — **textures publiées, périmées** | 339 | **48** | **35** |
| Cuisson corrigée du 07/08 — **non publiée** | 346 | **41** | **26** |

Un `--check` au démarrage donne **48**, pas 41 : il mesure l'ancien état. Ce
n'est pas une régression.

---

## 3. Le harnais

| | |
|---|---|
| **T-000** plan de test complet | ✅ **77 / 77** |
| **T-055** couverture des exigences | ✅ **64 / 64** |
| Portées | CONF · OEUVRE · SRC · CELL · PAIR · TIME |

| Fichier | Contenu |
|---|---|
| `bake.py` | commande unique, rapport, décision de publication, liste `CHANTIERS` |
| `bake_impl.py` | **génération des 15 lignes** — chaîne `O`→`H`, puis sprites `G`→`A` |
| `checks.py` | CELL, PAIR, TIME, CONF, T-000, T-055 |
| `checks_image.py` | galaxies du catalogue, morphologie, signature, A8 |
| `checks_src.py` | portée SRC — les 126 frames de dissolution, hors cuisson |
| `checks_oeuvre.py` | portée OEUVRE — les trois horizons, section H |
| `checks_dissolution.py` | dissolubilité (C13–C15) et résolution native |

---

## 4. Les 26 échecs bloquants, par cause

| Cause | Contrôles | Nombre |
|---|---|---|
| **Bruit de Poisson à `O` et `N`** | T-029, T-052, T-053, T-078 | 7 |
| **T-012, métrique suspecte** | T-012 | 8 |
| **Galaxies** | T-015, T-016, T-019, T-023, T-077 | 7 |
| Divers marginaux | T-014, T-033, T-035, T-049 | 4 |

### La cause principale, mesurée

À `O`, la projection dépose ses points dans une tranche de 300 Mpc : le **bruit
de comptage domine la structure**. Lissé par la PSF, un semis de Poisson donne
des blobs ronds de taille comparable et d'espacement quasi régulier — ce que
Marc décrit comme « de la mousse avec des blobs posés les uns à côté des autres
de manière assez régulière ».

Mesures à `O` : T-029 **0 %** de structures allongées · T-052 dispersion **0,40**
pour 0,50 · T-053 **0,6 octave** pour 2 · T-078 **47 %**.

**Un gain d'amplitude ne corrige pas cela** — il amplifie le bruit dans la même
proportion que la structure. Essayé et mesuré : contraste 0,318 → 0,353, aucune
différence visible.

**Les deux leviers restants**, identifiés et non traités :

1. **Le nombre de traceurs**, plafonné à 20 répétitions dans `render_full`.
2. **La largeur de bande** : `_fine_spectrum` est un filtre **rectangulaire**
   qui met à zéro hors bande ; à `O` la bande utile fait 0,58 octave. B9 demande
   un **amortissement continu**, ce qui élargirait la bande et supprimerait la
   quasi-périodicité décrite par B11.

---

## 5. Questions ouvertes à trancher par Marc

**T-012 — la métrique mesure-t-elle ce qu'elle prétend ?** Elle rend **0,40 sur
huit paires**, soit exactement 1/2,520, la raison de l'échelle : l'étendue
apparente mesurée **ne change pas d'une ligne à l'autre**. La métrique retient
les composantes au-dessus du 99,5ᵉ centile, donc le grain, qui suit le pixel et
non le mégaparsec. Quatre contrôles ont déjà été trouvés faux ce jour ; celui-ci
en a la signature, mais rien n'est décidé.

**`O` et `N` peuvent-elles montrer de vrais nœuds ?** À 91 Mpc par pixel la
structure réelle est ténue. Si lever le plafond de traceurs ne suffit pas, il
faudra décider si ces deux lignes portent un **grain honnête** plutôt que des
nœuds fabriqués — et l'écrire comme tel.

---

## 6. Chantiers ouverts — rouges, comptés, non bloquants

D�clarés dans `bake.py:CHANTIERS`, chacun avec sa raison. Aucune cuisson ne peut
les résoudre.

| Contrôles | Chantier |
|---|---|
| T-036, T-037 | **axe du temps** : aucune loi temporelle déclarée ; 99 % de la structure subsiste à amplitude nulle. **Bloque les onze colonnes** |
| T-010, T-011 | **O-07** : Zel'dovich ne fabrique pas la structure fine. Mesuré le 31/07 |
| T-024, T-045, T-047 | **sprites sources** : `ic10` et `leo1` sont le même fichier, octet pour octet |

---

## 7. La leçon de méthode de la session

Quatre contrôles écrits ce jour **testaient autre chose que l'exigence citée**, et
les quatre fois c'est la relecture de Marc qui l'a vu, pas le harnais. T-028 a
été bâti sur une métrique figurant **explicitement dans les métriques écartées**
depuis le 28/07 — « ne discrimine pas mousse et toile » — et il donne un bon
score là où le rendu est mauvais.

Et un contrôle peut être neutralisé **sans qu'aucun voyant ne s'allume** : T-028
et T-029 avaient été *exclus de portée* sur `L`→`O`, exactement là où le défaut
se trouvait.

> Le harnais garantit qu'un critère est **exécuté**. Il ne garantit ni qu'il est
> **juste**, ni qu'il est **appliqué là où il faut**. Une exclusion de portée est
> aussi dangereuse qu'un seuil desserré, et plus discrète.

---

## 8. Séquence de démarrage recommandée

1. `python3 scripts/harness/bake.py --check` — attendre **48 échecs, 35
   bloquants**. Tout autre chiffre demande une explication avant de continuer.
2. **Ce document**, puis `registre-tests.md` en gardant §1 à l'esprit.
3. `demandes-client.md` **v1.9** en entier · `decisions.md` (D-27 clôt O-08) ·
   `approches-ecartees.md`.
4. §0 de `architecture-univers-observable.md`.

**Ne pas commencer par cuire.** La cause principale est identifiée et aucune
cuisson ne la corrige : le travail utile est dans `_fine_spectrum` et dans le
plafond de traceurs de `render_full`.

---

## 08/08/2026 (soir) — la cause de la mousse à `O` n'est aucune des deux supposées

Les deux leviers documentés le 07/08 — le plafond de 20 répétitions dans
`render_full` et le filtre rectangulaire de `_fine_spectrum` — sont **tous les
deux hors de cause**. Mesure (`scripts/dev/diag_poisson.py`) :

| ligne | Mpc/px | cellule | **Ψ/cellule** | pts/px² |
|---|---|---|---|---|
| `O` | 91,06 | 91,06 | **0,01** | 15,9 |
| `N` | 36,14 | 36,14 | **0,06** | 15,7 |
| `M` | 14,34 | 14,34 | 0,28 | 38,7 |
| `L` | 5,69 | 5,69 | 0,99 | 37,5 |
| `K` | 2,26 | 2,26 | 2,92 | 38,5 |

Deux faits, et le second explique tout :

1. **L'échantillonnage est suffisant** — 16 à 39 traceurs par pixel, et
   `rep = 1` partout : le plafond de 20 n'est jamais atteint. Il n'a donc jamais
   rien limité.
2. **Le déplacement de Zel'dovich vaut 1 % d'un pixel à `O`.** Les traceurs sont
   restés là où on les a posés : un point par cellule, uniformément gigué.
   C'est un **verre** — la distribution la plus régulière qui soit, plus
   régulière qu'un tirage de Poisson. D'où la dispersion mesurée par T-052 à
   0,40 quand un hasard pur donnerait 0,52.

**Toute la structure est portée par le déplacement, et le déplacement est
sous-pixellaire.** L'image ne montre donc pas la toile : elle montre la grille
d'échantillonnage. Augmenter les répétitions ou élargir la bande du champ fin ne
peut rien y changer — ni l'un ni l'autre ne touche à ce qui manque.

*Et physiquement, Ψ ≈ 7 Mpc à ces échelles est JUSTE : au-delà de 300 Mpc
l'univers est presque homogène. Le défaut n'est pas dans la cosmologie, il est
dans le fait qu'un rendu par advection de traceurs ne sait rien montrer quand
l'advection est plus petite que le pixel.*

**Piste à arbitrer** (non implémentée) : pondérer chaque traceur par `1 + δ` à sa
position lagrangienne, au lieu de compter les traceurs. L'opérateur reste
linéaire, la masse est conservée, `δ` est déjà hérité de la ligne mère donc la
cohérence inter-lignes est préservée — et la structure cesse de dépendre de
l'amplitude du déplacement. Ne pas confondre avec le dépôt CIC, écarté le 29/07
pour une autre raison (il détruisait la cohérence inter-lignes, mesurée à
0,08–0,43).
