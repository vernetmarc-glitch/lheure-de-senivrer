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

### Plancher de traceurs posé — et ce qu'il a montré

`MIN_PTS_PX2 = 36` garantit désormais que le bruit de tirage reste petit devant
le signal. À `O` le rapport signal/bruit passe de **1,58 à ~3,8**, et l'héritage
`O→N` de 0,620 à 0,661.

**Mais T-052, T-053 et T-029 n'ont pas bougé.** La grenaille n'était donc pas
leur cause, et le plancher — bien que justifié — ne les concernait pas.

### La vraie cause de T-052 et T-053 : la bande disponible à `O` fait 0,58 octave

| ligne | Mpc/px | bande du champ fin | octaves |
|---|---|---|---|
| `O` | 91,06 | **200 → 300 Mpc** | **0,58** |
| `N` | 36,14 | 80 → 300 Mpc | 1,92 |
| `M` | 14,34 | 32 → 300 Mpc | 3,25 |

La borne haute est l'échelle d'homogénéité, 300 Mpc ; la borne basse est
Nyquist, 2,2 px. À `O`, un pixel vaut 91 Mpc : il ne reste **que 0,58 octave**
entre les deux. Un champ à bande quasi monochromatique produit un motif
quasi périodique — d'où la dispersion des pics mesurée à 0,39 par T-052, plus
**régulière** qu'un tirage au hasard (0,52).

**Les deux contrôles ont la même cause, et elle n'est pas corrigeable par
réglage.** Élargir la bande demanderait `lam_hi ≥ 800 Mpc`, c'est-à-dire
peindre des structures au-delà de l'échelle d'homogénéité : inventer un univers
qui n'existe pas.

**Ce que dit la physique.** À 14 570 Mpc de demi-champ, l'univers observable
*est* homogène. Les plus grandes structures réelles — vides, superamas, pic
acoustique — plafonnent vers 200–300 Mpc, soit 2 à 3 pixels. La ligne `O` ne
peut pas montrer de toile filamenteuse, et c'est exactement ce que B8 affirme
déjà en déclarant `L`→`O` homogènes.

*B11 (« distribution amassée », « ≥ 2 octaves ») et A5 (« points le long des
filaments ») sont donc appliqués hors de leur domaine de validité sur `O`, comme
B4 l'était avant que T-039 ne soit borné à la fenêtre `D`→`J`. Le parallèle est
exact. Décision à prendre par Marc : borner la portée de ces trois contrôles aux
lignes où l'échelle d'homogénéité dépasse quelques pixels.*

### L'amortissement continu est posé — et il révèle une contradiction entre B5 et B11

`_fine_spectrum` ne coupe plus net à l'échelle d'homogénéité : au-delà, le
spectre se prolonge avec la pente primordiale `P(k) ~ k^+1`, l'amplitude
décroissant vers les grandes échelles au lieu de s'annuler d'un coup. C'est ce
que **B9** demandait depuis le début — *« il n'y a pas de coupure »* — et la
coupure franche la violait.

**Gains :** T-053 passe à `N`, T-029 à plusieurs lignes, T-014 (isotropie `L`),
T-052 à `M`, T-010 et T-011 sur `O→N`. **12 → 11 bloquants.**

Un essai intermédiaire a été écarté par la mesure : placer le genou au maximum
réel du spectre de puissance (~600 Mpc, échelle d'égalité) donnait bien 2,25
octaves à `O`, mais faisait apparaître des structures de **720 à 971 Mpc sur
cinq lignes**, et T-008 les a vues immédiatement. L'œuvre montre les structures
**formées**, pas le spectre : B5 et B8 fixent le genou à 300 Mpc et ils priment.

### La contradiction, en arithmétique

À `O`, un pixel vaut 91,06 Mpc.

| | |
|---|---|
| borne basse | Nyquist, **2,2 px** |
| borne haute | plafond de T-008 (B5), 300 × 1,6 = 480 Mpc = **5,27 px** |
| **bande maximale possible** | **1,26 octave** |
| **bande exigée par B11** | **2,00 octaves** |

**Aucune image ne peut satisfaire les deux à la fois à la ligne `O`.** Ce n'est
pas un défaut de réglage ni un générateur à améliorer : c'est une impossibilité
arithmétique, et elle est confinée à cette seule ligne — `N` autorise 2,59
octaves et `M` 3,93, donc les deux exigences y coexistent sans peine.

Mesuré après cuisson : `O` 502 Mpc pour un plafond à 480 (dépassement de 4 %),
`N` 482, `M` 510. Et T-053 reste à 1,4 octave à `O`, T-052 à 0,41, T-029 à 0 %.

*Trois issues possibles, toutes du ressort de Marc :*
1. *desserrer le facteur 1,6 de T-008 — il était déjà une tolérance pour ce même
   effet, et un spectre amorti étale un peu plus loin qu'un spectre tronqué ;*
2. *borner B11 aux lignes où la bande est physiquement disponible, comme B4 l'a
   été à la fenêtre `D`→`J` ;*
3. *accepter que `O` soit la ligne où l'univers est montré homogène — ce que B8
   affirme déjà — et n'y garder que les trois sphères, qui sont le sujet.*

### T-023 : l'ancrage marche, c'est le champ fin qui l'efface

Mesure du 08/08, sur **la sortie de `render_full`** et non sur la texture finale :
**65 %** des positions du catalogue sont au-dessus de la médiane, pour un seuil
à 70 %. Sur la texture **publiée** : **23 %**.

**Ce qui détruit le signal est donc en aval du rendu.** `apply_fine` module
l'image par un champ log-normal qui n'a aucune corrélation avec la toile, et à
la ligne `H` son amplitude domine la convergence des filaments.

Deux hypothèses écartées par la mesure, dans l'ordre où elles se présentaient :

- **le signe de l'ancrage** — `+1` donne 65 %, `−1` donne 64 %. Il n'est pas en
  cause ;
- **le gain d'ancrage** — il produit pourtant un déplacement de **12,65 Mpc rms
  à `H`, soit 90 pixels**, pour ancrer un Groupe Local étalé sur 18 Mpc. Le
  ramener à 265 (≈1,5 Mpc) améliore bien T-011 — `I→H` de 9,0 à 7,5 px — mais
  **dégrade** T-023 de 36 % à 23 % et fait échouer T-027 sur `H`. Huit bloquants
  contre sept.

*Le gain est donc remis à 2235, et il ne doit pas être retouché avant que la
modulation aval soit traitée : tant que le champ fin écrase la convergence,
régler l'ancrage revient à ajuster un signal qu'on efface ensuite.*

**Conséquence probable au-delà de T-023.** T-010 et T-011 échouent sur
exactement les lignes ancrées, avec des ampleurs qui suivent `ANCHOR_STRENGTH`
(`J` 0,12 → 4,5 px · `I` 0,45 → 7,5 px · `H` 1,00). Le chantier O-07 n'est
peut-être pas une question de recherche ouverte, mais ce même défaut.

---

## 08/08/2026 (fin de séance) — état réel, et ce qui survit à la session

**Cuisson fraîche : 378 contrôles passés, 15 en échec, 4 bloquants.**
Au démarrage de la séance : 339 / 48 / **35**.

**Attention au piège de lecture.** `bake.py --check` mesure les textures
**publiées**, et celles-ci sont antérieures à toutes les corrections du 08/08 :
le harnais a refusé **cinq publications de suite**, exactement comme la règle 0
l'exige. `--check` rapporte donc 27 bloquants, et **ce chiffre ne dit rien de
l'état du code**. Le seul chiffre valable est celui d'une cuisson fraîche.

*Ne pas « corriger » ce désaccord en publiant : c'est la règle 0 qui fonctionne,
pas un défaut.*

Les 4 bloquants restants : T-052 (`N`, dispersion 0,43) · T-027 (`I`, creux
6,60) · T-023 (`H`, densité au catalogue — cause identifiée, le champ fin efface
l'ancrage) · T-077 (`G`, fond aussi brillant que les galaxies). Plus T-035
(arête `G|H`) et le chantier O-07 (héritage `I→H`, `H→G`), non bloquants.

### Ce qui survit d'une instance à la suivante

| | où | versionné |
|---|---|---|
| algorithmes de génération | `scripts/dev/gen_chain.py`, `sprites_layer.py` | ✅ |
| **tous** les paramètres | `spacetime_matrix.json`, bloc `generation` | ✅ |
| graines, règle de dérivation | `generation.seeds`, `seed_rule` | ✅ |
| 393 contrôles | `scripts/harness/` | ✅ |
| exigences, décisions, impasses | `docs/` | ✅ |
| textures publiées | `app/public/essai-v4/data/v4` | ✅ |
| empreintes de reproductibilité | `docs/baseline-textures.json` | ✅ *(ajouté ce jour)* |

**Ce qui ne survit pas, et n'a pas à survivre :** le cache `scripts/dev/_chaine`
(1 Go de `.npz` intermédiaires, régénérable) et les cuissons en `/tmp`. La
chaîne est **déterministe** — `seed_rule` promet la reproductibilité bit à bit —
donc une cuisson de 11 minutes reconstruit tout.

*C'est cette promesse que `baseline-textures.json` rend vérifiable : si un digest
diffère alors que les trois fichiers moteur sont identiques, la chaîne a cessé
d'être déterministe, et il faut le savoir avant de chercher ailleurs. L'empreinte
manquait — le fichier n'avait jamais été écrit.*

### Un risque structurel à connaître

**Le moteur de production vit dans `scripts/dev/`**, que le workflow CI déclare
« recherche, non bloquant ». `gen_chain.py` et `sprites_layer.py` sont pourtant
la chaîne réelle, désignée comme telle par `generation.engine`. Un ajout cassant
dans ces deux fichiers ne fait pas rougir la CI. *À déplacer vers un chemin
bloquant, ou à ajouter explicitement au périmètre bloquant du workflow.*

---

# PASSATION — 08/08/2026, fin de séance

*À lire après `bake.py --check` et avant toute correction. Objectif de la
prochaine séance : **amener les 4 bloquants à zéro pour publier les 15 lignes
actuelles**. Ne pas ouvrir le chantier des 165 cellules avant.*

**Rappel du piège :** `--check` mesure les textures **publiées**, qui ont six
cuissons de retard, et rapporte ~27 bloquants. Le chiffre vrai est **4**, sur
cuisson fraîche. Lancer le workflow **Cuisson** (onglet Actions) ou
`bake.py --all` avant de conclure quoi que ce soit.

## Les 4 bloquants, par ordre conseillé

### 1. T-023 — `H`, densité aux positions du catalogue (D6) · **36 %** pour 70 %

**La cause est trouvée et mesurée, il reste à la corriger.** L'ancrage
fonctionne : sur la sortie de `render_full`, **65 %** des positions du catalogue
sont au-dessus de la médiane. Sur la texture publiée : **23 à 36 %**. Ce qui
détruit le signal est **en aval du rendu** — `apply_fine` module l'image par un
champ log-normal sans aucune corrélation avec la toile, et à la ligne `H` son
amplitude domine la convergence des filaments.

*Écarté par la mesure, ne pas y revenir :* le **signe** de l'ancrage (+1 → 65 %,
−1 → 64 %) ; le **gain** (le passer de 2235 à 265 améliore T-011 mais dégrade
T-023 à 23 % et casse T-027 sur `H` — huit bloquants au lieu de sept).

*Piste :* moduler l'amplitude du champ fin là où l'ancrage est fort, ou appliquer
le champ fin **avant** l'ancrage. Écrire le contrôle avant la correction.

### 2. T-077 — `G`, rien d'aussi brillant que les galaxies (A8) · **0,70** pour ≤ 0,60

Pic du fond 113/255 contre pic des galaxies 162/255. **Non diagnostiqué.**
Attention : `ambient_ceil` et `ambient_strength` existent déjà par ligne dans la
matrice et sont le levier évident — vérifier d'abord qu'ils sont bien lus, la
courbe à genou doux ayant été posée le 07/08.

### 3. T-052 — `N`, distribution amassée (B11) · **0,43** pour ≥ 0,50

`N` dispose de **2,59 octaves** de bande : contrairement à `O`, l'exigence y est
tenable et **la borne D-30 ne s'y applique pas**. L'amortissement continu a fait
passer `M` mais pas `N`. **Non diagnostiqué** — mesurer la bande réellement
obtenue à `N` après amortissement avant de toucher au générateur.

### 4. T-027 — `I`, signature de référence (A1) · creux **6,596**

Une seule composante de la signature hors cible. **Non diagnostiqué.** Vérifier
d'abord si c'est un effet de bord du plancher de traceurs `MIN_PTS_PX2`, ajouté
le même jour et qui a changé la grenaille à toutes les lignes.

## Non bloquants, à ne pas confondre avec les précédents

**T-035** (arête `G|H`, ton 8,0/255) et le **chantier O-07** — héritage `I→H`
0,719 et `H→G` 0,793. Ces derniers échouent sur **exactement les lignes
ancrées**, avec des ampleurs suivant `ANCHOR_STRENGTH` (`J` 0,12 → 4,5 px ·
`I` 0,45 → 7,5 px · `H` 1,00). *O-07 n'est peut-être pas une question de
recherche ouverte, mais le même défaut que T-023.* Le traiter en 1 pourrait
fermer les deux.

## Ce qui a été acquis ce jour et ne doit pas se reperdre

- **T-079**, banc de falsification : tout contrôle de paire doit rendre sa valeur
  cible sur une paire synthétique et échouer sur un témoin négatif. Il a attrapé
  deux fautes dans la réécriture de T-012 avant toute relecture humaine.
- **Sept contrôles trouvés faux** au total (T-012, T-016, et les cinq du 07/08).
  Devant un échec, mettre d'abord le contrôle au banc.
- **T-081** : la réduction des sprites perdait **100 %** du flux sous 20 px.
- **D-29** : avancer sans demander l'arbitrage à chaque étape.
- **D-31 / M1** : plus aucune distance affichée n'est comobile.
