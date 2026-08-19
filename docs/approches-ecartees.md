# Approches écartées

**Ne pas les reproposer.** Chaque entrée porte la **mesure** qui l'a écartée, pas
une impression.

**Pourquoi ce document existe.** Sept impasses ont été explorées et documentées de
façon narrative, donc introuvables. La session du 28 juillet 2026 a proposé MCPM
avec enthousiasme et l'a classé premier de neuf méthodes — avant de le rejeter
trois jours plus tard sur mesure. Une impasse non consignée se reparcourt.

**Règle.** Reproposer une approche de cette liste exige d'expliquer **ce qui a
changé** depuis la mesure qui l'a écartée.

---

## Générateurs de toile cosmique

### Transformation log-normale sur champ gaussien
*Moteur de production historique.*
**Écartée** : ne produit pas de filaments, mais des taches diffuses. La
transformation étant ponctuelle, elle ne peut pas créer de structure filamenteuse
qui n'est pas déjà dans le champ.

### Crêtes de la matrice hessienne (NEXUS+ / MMF)
**Écartée** : donne une **mousse** de cellules, pas une toile. La hessienne d'un
champ gaussien a des crêtes partout, à toutes les échelles, sans connectivité
privilégiée. *Reste utile comme **validateur*** des fractions de volume
nœuds/filaments/murs.

### Squelette de Morse (DisPerSE)
**Écartée** : grains uniformes. Le filtrage par persistance, qui aurait pu tuer la
mousse, n'avait pas été appliqué — l'approche n'est donc pas formellement
disqualifiée, mais elle reste un détecteur, non un générateur.

### Dépôt CIC d'une grille advectée par Zel'dovich
*Moteurs v3.2 et v3.3.*
**Écartée pour raison structurelle** : corrélation du **champ** entre layers
adjacents 0,79-0,95, corrélation après **dépôt** 0,08-0,43. Cause : un opérateur
spatialement non linéaire ne commute pas avec un changement de fenêtre.
`NonLin(resample(x)) ≠ resample(NonLin(x))`. **Aucun réglage ne peut corriger
cela.**

### MCPM / Physarum (Monte Carlo Physarum Machine)
**Écartée** : produit une **bulle par halo**, donc une mousse — 123 structures
distinctes contre 512 dans la référence, et anisotropie 1,44. Rien dans sa
dynamique ne reproduit l'effondrement **anisotrope**, qui est ce qui fabrique les
filaments.
⚠ *Classée premier choix le 25 juillet sur analyse théorique, rejetée le 28 sur
mesure.* L'article Elek/Burchett fait **ajuster** un réseau à des galaxies déjà
connues — un problème d'interpolation entre nœuds donnés, non de génération.

### Particle-mesh à résolution modeste
**Écartée** : netteté des pics **1,17**, pire que Zel'dovich seul (1,26), et
anisotropie remontée à 1,28. Avec 884 k particules la résolution de force vaut
2,34 Mpc, plus qu'un amas réel : les nœuds ne *peuvent pas* se compacter, et la
grille CIC des forces réimprime l'artefact axial. Exigerait 512-1024³ avec
raffinement adaptatif.

### Dépôt direct des positions d'agents
**Écartée** : résolution effective **0,992** contre 0,886 pour la référence — donc
plus floue que tout le reste — contraste 1,12 contre 0,51, bimodalité de retour.

---

## Mécanismes de dissolution

### `A(s,a)` appliqué par bande de k
**Écartée** : physiquement fausse. En théorie linéaire le facteur de croissance
s'applique **identiquement à toutes les échelles** ; la hiérarchie de formation est
une conséquence **émergente** de la non-linéarité. Imposer `a_form` par bande
faisait survivre les petites échelles artificiellement — 80 % d'amplitude à
λ=1,6 Mpc contre 0 % à λ≥53 Mpc — et elles envahissaient l'image.
Symptôme observé : nombre de structures ×3,8 pendant la dissolution.
*Remplacée par le facteur global `D(a)` — décision D-05.*

### Halos ajoutés à la toile (masse non conservée)
**Écartée** : la dissolution **ne se termine jamais**. Les patches sphériques
isolés ne pavent pas l'espace, il reste 13,96/255 de structure lissée à `a=0,01`
contre 0,65 pour le verre pur.
*Remplacée par le prélèvement dans la toile — décision D-07.*

### Croissance du rayon de splat sans conservation du flux
**Écartée deux fois** : documentée comme corrigée le 10 juillet, **violée en
production**, redécouverte le 28. Flux mesuré ×77 sur le sprite `andromede`,
correspondant exactement au ×72 prédit par σ² de 0,5 à 4,25 px. La tache grossit
sans jamais pâlir.
*Sous contrôle par l'invariant INV-D2 et INV-G1.*

### Flou gaussien comme mécanisme de transition
**Écartée** : passe-bas par construction. Effondrement mesuré de la variance du
laplacien.

### Bruit de valeur lisse comme source de structure
**Écartée** : passe-bas également. *Dérogation limitée pour la modulation des
sprites — décision D-14.*

### Mélange vers une couleur unie
**Écartée** : recrée exactement le défaut interdit par §11.3 de l'architecture.

---

## Choix de représentation

### Normalisation du champ à variance unité par boîte
**Écartée** : artefact de code (`f / f.std()`), pas une physique. Rendait
l'amplitude de déplacement proportionnelle à la boîte — **932 Mpc à `l5`** — et
faisait dépendre la cohérence inter-layer d'une normalisation arbitraire.
*Remplacée par la normalisation absolue σ₈ — décision D-08.*

### Boîtes cubiques
**Écartée** : on ne rend jamais qu'une tranche mince. À `l5`, calculer une boîte
cubique gaspille un facteur **39** de volume, et ce gaspillage se paie en
résolution : la cellule atteint 182 Mpc et la toile n'est plus résolue du tout.
*Remplacée par la dalle anisotrope — décision D-09.*

### Rayon d'objet en fraction de boîte
**Écartée deux fois**, les 28 et 29 juillet : donne **769 Mpc** à `l5` là où un
amas fait 2,2.
*Sous contrôle par l'invariant INV-C1.*

---

## Structure de la matrice

### Axes du temps privés par ligne
*`dissolution_window_a` + `keyframes_a` par layer — matrice v3.*
**Écartée le 30/07/2026** : les colonnes déclarées cessent d'être des époques.
Mesure — la matrice déclarait 11 colonnes communes, mais les fichiers cuits
portaient des axes distincts par ligne :

| Lignes | Fenêtre | Keyframes |
|---|---|---|
| `G`→`M` | a ∈ [0,794 ; 1,0] | 9 |
| `D`→`F` | a ∈ [0,303 ; 1,0] | 13 |
| `C` | a ∈ [0,040 ; 1,0] | 12 |
| `A`, `B` | — | **0** |

`st_l5_k04.png` valait `a = 0,891` quand la colonne 4 déclarée valait
`a = 0,480`. Sept lignes sur treize n'avaient **aucune image** avant `a = 0,794`,
soit avant 10,7 Ga : le rendu comblait avec le ton dissous uniforme, ce qui a
produit les aplats. 143 cellules déclarées, 114 fichiers, 11 axes du temps.
*Remplacée par la grille rigide — décisions D-22 et D-23.*

### Plancher de déplacement exprimé en pixels
*`lam_min_px = 6`, combiné à `filament_max_scale_mpc = 150`.*
**Écartée le 30/07/2026** : un plancher en pixels vaut une échelle physique
différente à chaque ligne, et croise le plafond comobile. Mesure — à `l5`,
1 px = 68,3 Mpc, donc le plancher vaut **410 Mpc** contre un plafond de 150 : la
bande de déplacement est **vide**, `Ψ = 0`, l'image est un aplat exact
(std = 0,00 sur 1024², en production comme sur les 9 frames du prototype). Le
`std` mesuré suit la largeur de bande sur toute la colonne :

| Ligne | λ min réel | Bande | std |
|---|---|---|---|
| `l5` | 410 Mpc | **vide** | **0,0** |
| `l5a` | 97 Mpc | [97 ; 150] | 21,7 |
| `l4b` | 37 Mpc | [37 ; 150] | 32,7 |
| `l2` | 1 Mpc | [1 ; 150] | 52,8 |

Quatrième occurrence du même piège, après `lam_min_px`, `peak_sharpness`, le
critère de couverture et le σ mélangeant structure et grenaille.
*Remplacé par une loi de contraste décroissant — décisions D-25 et D-26.*

### Échelle de zoom à pas irréguliers
*13 lignes, pas de ×1,41 à ×24.*
**Écartée le 30/07/2026** : un fondu ne peut pas se comporter de la même façon
sur un pas de ×1,41 et sur un pas de ×24. Le trou entre `B` (0,1 Mpc) et `C`
(2,4 Mpc) avait été rattrapé en silence par un fondu local de **0,52 dex** là où
toutes les autres arêtes valaient 0,15 — une rustine, pas une correction. À
l'autre bout, `150 → 212 → 300` subdivisait en √2, deux fois plus fin que partout
ailleurs.
*Remplacée par l'échelle géométrique ×2,520 — décision D-21.*

### Élargissement de la bande fraîche du raccord
*`K_CUT_SAFETY` porté de 1,2 à 7 puis 20 — testé le 31/07/2026, écarté le jour même.*

**Hypothèse.** Le contenu neuf de chaque ligne se situe entre 6 et 2 pixels —
`k_cut = π/(1,2 × cellule_parent)` et la cellule parent vaut 2,52 cellules
enfant. C'est le domaine du grain, pas du filament, et ce contenu est déplacé de
13,6 px, soit deux fois sa propre longueur d'onde. Abaisser `k_cut` devait
amener le neuf à des échelles visibles.

**Mesure**, ligne `I`, taille des vides en fraction du cadre (cible : 5,0 %,
valeur de l'image de référence) :

| `K_CUT_SAFETY` | Bande fraîche | Vides | rms(Ψ) |
|---|---|---|---|
| 1,2 *(production)* | 6,0 px | 10,2 % | 12,74 |
| 7,0 | 35,3 px | **8,5 %** | 12,71 |
| 20,0 | 100,8 px | 9,4 % | 12,22 |

**Écartée** : le gain plafonne à 1,7 point et **n'est pas monotone** — à 100 px la
mesure remonte. Multiplier par 17 la largeur de la bande fraîche ne rapproche pas
de la cible.

**Ce que cela démontre.** Le défaut ne vient pas de la largeur de bande. Donner
du contenu neuf à grande échelle ne produit pas de filaments fins, parce que
l'approximation de Zel'dovich ne les **fabrique** pas : après croisement de
nappes, les particules se traversent et les structures se délavent au lieu de
s'effondrer. La structure fine naît de l'effondrement gravitationnel, absent au
premier ordre.

*Constat visuel de Marc, confirmé par la mesure : « sur le layer H, il n'y a
quasiment aucune structure haute fréquence apparue en plus par rapport au layer
K », trois lignes plus haut. Cette mesure tranche **O-07** — voir
`docs/montee-en-complexite-nbody.md`.*

---

## Métriques écartées

| Métrique | Pourquoi |
|---|---|
| `peak_sharpness` à fenêtre de 11 px fixes | mesure une taille physique différente à chaque layer ; a fait diagnostiquer un « creux » inexistant |
| σ brut comme indicateur de structure | mélange structure et bruit de grenaille ; stagnait à 41/255 même dissous |
| `frac>0` de la trace | la diffusion la porte à 1,0 partout, sans information |
| Élongation globale des nuages | ne discrimine pas mousse et toile (1,87 contre 1,78 pour la référence). **07/08 : T-028 a été écrit sur cette métrique malgré cette ligne, et rend 4,26 à `O` là où Marc voit de la mousse. Conservé comme garde-fou, retiré du rôle de preuve.** |
| Pic spectral à la fréquence de maille | mauvaise signature ; l'artefact de grille est une **anisotropie directionnelle**, pas une périodicité |

---

## 10/08/2026 — quatre impasses mesurées, à ne pas reparcourir

**Gain d'ancrage, pour T-023 (D6).** `ANCHOR_GAIN` ×3 → 36 % devient 37 %. La
baisse à 265 avait déjà été écartée le 08/08 : **les deux sens sont morts**. Coût
de la mesure : deux cuissons de `H`, environ 9 minutes chacune.

**`apply_fine` comme destructeur du signal d'ancrage.** Hypothèse de la passation
du 08/08. Champ fin **entièrement annulé** à `H` → 41 % au lieu de 36 %. Il coûte
cinq points, pas trente. *Écarté.*

**Défaut de repère dans `anchor_psi`.** Les **huit** conventions (transposée,
miroir X, miroir Y et combinaisons) testées sur la texture livrée : maximum
47 %, toutes au niveau du hasard. *Écarté sans cuisson.*

**Gain de toile pour T-052 à `N`.** 2,7 → 3,5 → 4,5 → 6,0 donne 0,43 → 0,41 →
0,40 → 0,40, et casse T-078 à 6,0. Une loi de puissance ponctuelle amplifie les
pics **sans déplacer leurs positions** : elle ne peut pas amasser. *Contre-
productif, à ne pas réessayer.*

**Champ fin propre à `G`, pour T-094 (D6b).** 1,0 → 1,4 → 1,8 → 2,4 donne 0,71 →
0,47 → 0,28 → **0,13**. La modulation log-normale relève la moyenne plus vite que
l'écart-type lissé, donc le contraste chute. La valeur nominale est optimale.
*Effondrement, pas amélioration.*

**Plafond ambiant seul, pour T-094.** Il comprime les hauts **et** le contraste
ensemble : T-094 monte de 0,64 à 0,78 pendant que T-077 se dégrade de 0,56 à
0,79. Ils se croisent avant de se rejoindre. Le levier juste est le gain de
toile, qui creuse les vides **avant** le champ fin pendant que le plafond coiffe
les pics ensuite.

---

## 11/08/2026 — cinq mesures écartées sur les galaxies

Toutes butent sur le même fait : **à ces échelles la fenêtre de mesure contient
plus de fond que de galaxie.** Ne pas les réessayer sans changer de méthode.

**Richesse de structure — trois tentatives.**
1. Écart-type du profil azimutal → mesurait le **bruit de grenaille** : le nuage
   appauvri à 2 500 traceurs « gagnait », 0,134 contre 0,037 pour 82 000 étoiles.
2. Modes azimutaux bas / modes hauts → mesurait l'**élongation** : un disque
   incliné est une ellipse, donc du m=2 pur. 338 pour la tache plate d'Andromède
   contre 11 pour le modèle à quatre bras.
3. Cohérence de phase log-spirale → mesurait le **flou** et la **concentration** :
   le dénominateur s'effondre sur une image lisse, et la couronne de mesure tombe
   sur le bord d'une petite tache.

**Taille apparente — deux tentatives.**
4. `_local_extent` sur médiane globale, bande (1,8 · 3,4) → mesurait le **fond** :
   2,61 à 2,70 à des positions sans aucune galaxie.
5. Dispersion des rapports taille/rayon sur anneau local → **ne réagit pas** à un
   grossissement ×2 (0,197 dans les trois cas).

**Enveloppe stellaire étendue (route écartée avant implémentation).** Amener le
rapport de T-016 à 1,8 imposait que la galaxie cesse de dominer sa fenêtre —
c'est-à-dire exactement ce qu'A8/T-077 interdit. Réfutée par le témoin au hasard,
sans écrire une ligne.

**Halo de transition à forte amplitude.** ×2 puis ×5 : 5 puis 7 bloquants, T-018
et T-012 cassés au passage. L'étendue apparente venait du halo dans l'ancien
générateur, et le rapporter au flux de 80 000 étoiles au lieu d'une amplitude
absolue change complètement son poids relatif.
