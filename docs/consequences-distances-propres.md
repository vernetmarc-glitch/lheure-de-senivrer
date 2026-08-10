# Conséquences du passage aux distances propres (M5 / D-31)

*08/08/2026. Arbitrage de Marc : « je ne veux rien voir apparaître en
coordonnées comobiles, tout doit être représenté en distance réelle ».*

Ce document mesure ce que cela change. Il ne propose rien : il chiffre.

---

## 0. Ce qui change, et ce qui ne change pas

**Ne change pas.** Le générateur continue de travailler en comobile. Le champ y
est **statique** — une structure ne bouge pas d'une époque à l'autre — et c'est
la seule coordonnée où l'héritage entre lignes voisines (B1, T-010) a un sens.
Renoncer au comobile *à l'intérieur* du moteur reviendrait à recalculer le champ
à chaque colonne, et à perdre la cohérence entre lignes.

**Change.** Tout ce qui est **montré**. `propre = comobile × a(époque)`.

*Les deux ne s'opposent pas : c'est un changement de variable à l'affichage.*

---

## 1. Le demi-champ d'une ligne dépend maintenant de la colonne

Loi retenue : `R_ref × a` tant que l'échelle suit le flot, **figée à `R_ref`**
dès qu'elle est liée. Continue au passage, et égale à `R_ref` aujourd'hui.

| ligne | a_form | col 0 | col 3 | col 6 | col 10 |
|---|---|---|---|---|---|
| `A` | 0,12 | 0,00026 | 0,0350 | 0,0350 | 0,0350 |
| `E` | 0,56 | 0,00231 | 0,604 | 1,255 | 1,411 |
| `H` | — | 0,0205 | 5,365 | 11,15 | 22,58 |
| `O` | — | **13,23** | 3 462 | 7 193 | 14 570 |

*Toutes valeurs en Mpc propres.*

**Vérification décisive :** à la colonne 0, la ligne `O` mesure 13,23 Mpc, et la
matière que nous observons aujourd'hui occupait alors une sphère de **12,84 Mpc
de rayon**. Le cadre la contient exactement. C'est précisément ce que Marc
demandait : la matière se contracte et **reste dans le cercle**.

---

## 2. L'échelle de zoom n'est plus géométrique à toute époque

| | rapport entre lignes voisines |
|---|---|
| colonne 10 | 2,52 partout |
| colonne 6 | 2,01 à 2,52 |
| colonne 0 | **1,55** à 2,52 |

Les lignes liées se figent pendant que les autres continuent de se contracter :
l'écart entre elles se referme. **D-21 — « échelle géométrique, raison
constante » — n'est vraie qu'à la colonne 10** et doit être amendée.

*Conséquence directe sur les fondus de zoom : `fade_width_dex = 0,15` est calé
sur un pas de 0,401 dex. À la colonne 0 le pas tombe à 0,19 dex par endroits, et
le fondu couvrirait alors 79 % du pas au lieu de 37 %. Les arêtes doivent
devenir dépendantes de la colonne, ou le fondu exprimé en fraction du pas
courant.*

---

## 3. La dissolution et le découplage sont le même évènement

C'est le gain conceptuel de la décision.

Une échelle cesse de participer à l'expansion **exactement quand elle
s'effondre**. Avant, elle suit le flot ; après, sa taille propre est figée.
C'est le même seuil que celui qui gouverne la dissolution (C16, C13) : une
galaxie n'est pas « formée puis liée », c'est le même fait.

**À la recombinaison, rien n'est effondré : aucune ligne n'est liée.** La table
`expansion_par_ligne` du 08/08 au matin ne décrivait donc que la colonne 10, et
elle aurait figé l'échelle de la Voie lactée à une époque où la Voie lactée
n'existe pas. Remplacée par `regime_expansion_par_cellule`, 15 × 11.

---

## 4. Les deux cercles, en distance propre

| colonne | matière observable aujourd'hui | horizon des particules |
|---|---|---|
| 0 | **12,84 Mpc** | **0,253 Mpc** |
| 3 | 3 361 | 1 769 |
| 6 | 6 983 | 5 273 |
| 10 | 14 145 | 14 145 |

Les deux coïncident aujourd'hui — par définition — et **divergent d'un facteur
51 à la recombinaison**. C'est le cœur du sujet : à la colonne 0, la matière que
nous voyons aujourd'hui remplit la ligne `O`, tandis que l'horizon des
particules de cette époque-là est **cinquante fois plus petit**, quelque part
vers la ligne `K`. Un observateur d'alors ne voyait qu'une fraction minuscule
de ce que nous voyons.

*Les deux cercles doivent être tracés, et distingués visuellement. Les
confondre est l'erreur que ce document existe pour empêcher.*

---

## 5. Ce qui reste à faire

- **`a_form(R)` est provisoire** — interpolation logarithmique calée sur deux
  repères sûrs (Groupe Local lié vers `a` ≈ 0,56, amas riche vers 0,80). À
  remplacer par le critère sphérique `σ(R)·D(a) ≥ 1,686`, où `σ(R)` se calcule
  du spectre de puissance. T-090 vérifiera alors la loi dérivée.
- **Amender D-21** (raison constante) et le calage des fondus.
- **`UniverseMap.tsx`** : graduations, barre d'échelle et barre de la vitesse de
  la lumière (H8) doivent lire `demi_champ_propre_mpc` et
  `horizons_propres_mpc`, jamais les valeurs comobiles.
- **Relire les libellés des contrôles** : ceux qui rapportent des Mpc doivent
  dire lesquels. Les seuils internes (homogénéité 300 Mpc, plafond de tranche)
  restent comobiles et le resteront — ils décrivent le champ, pas l'affichage.
