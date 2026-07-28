# Test en cours — Générateur par particules (Zel'dovich + halos récursifs)

**Statut : EN COURS DE VALIDATION — ne pas intégrer à `architecture-univers-observable.md` ni à la production avant clôture des trois tests unitaires ci-dessous.**

Date d'ouverture : 27 juillet 2026
Périmètre : layers D→M (`l1b`→`l5`), axe de zoom et axe de temps.

---

## 1. Origine

Le moteur de production (GRF + transformation log-normale, `generate_layers.py`)
et les explorations successives (log-normale, crêtes de Hessienne, Zel'dovich+CIC
v3.2/v3.3, MCPM/Physarum) ont toutes échoué sur au moins un des deux axes :

- **Cohérence inter-layer** : corrélation de champ 0,79-0,95, mais 0,08-0,43 après
  dépôt CIC. Cause racine identifiée : *un opérateur spatialement non linéaire ne
  commute pas avec un changement de fenêtre*. Aucun réglage ne peut corriger ça.
- **Aspect** : MCPM produit une mousse de bulles (une par halo) et non une toile,
  parce qu'aucune de sa dynamique ne reproduit l'effondrement **anisotrope**.

Le générateur testé ici déplace des **particules à positions continues** par le
champ de Zel'dovich, et pose aux nœuds des **halos à profil radial piqué avec
sous-halos récursifs**. Il n'y a plus aucune grille cartésienne entre l'objet
générateur et l'écran.

### Invariant de conception

> Entre l'objet générateur et l'écran, uniquement des opérateurs spatiaux
> **linéaires** (projection, fenêtrage, moyenne de zone) et des courbes de ton
> **ponctuelles** monotones. Toute non-linéarité spatiale vit en amont, dans
> l'objet unique partagé par tous les layers.

---

## 2. Conformité aux documents existants

| Exigence | Référence | Statut |
|---|---|---|
| Sens de génération grand → petit, non inversible | §4.4, §4.7 | ✅ respecté |
| Arbre de parenté (`l5`→`l4b`→`l4`→`l3`→`l2`→`l1b`) | `LAYER_SPECS` | ✅ conservé |
| Aucun flou géométrique | §11.2 | ✅ les particules se déplacent, jamais lissées |
| Aucun mélange vers une couleur unie | §11.3 | ✅ projection de points à toute époque |
| Hautes fréquences jusqu'à dissolution totale | §11.2 | ✅ vérifié, test 1 |
| `A(s, a=1) = 1` exactement, sans saut | §11.4.b | ✅ vérifié, test 1 |
| Deux types de contenu seulement (sprites + champ) | §11.1 | ✅ inchangé |
| Composition par « screen », jamais par calque | §11.3 | ⚠️ à recâbler (sources : toile, halos, embrasement) |
| Non-régression du rendu à `a=1` | §11.7 | ❌ **rompue volontairement** — cf. §6 |

### Gain collatéral sur l'ancrage du Groupe Local

Le piège documenté au §0 et §4.3 — toute contribution ajoutée au champ **avant**
la transformation log-normale y est amplifiée exponentiellement — **disparaît** :
il n'y a plus de `exp()` en amont. Les 98 galaxies entrent comme halos du
catalogue à leur position comobile réelle, et la toile pousse autour d'elles.

---

## 3. Axe de zoom — mécanisme d'héritage à 100 %

Avec un champ, « hériter » signifie corréler des phases : partiel par nature, et
détruit par tout opérateur non linéaire en aval. Avec des particules, l'ensemble
enfant se **définit** comme :

```
particules(enfant) = { particules(parent) ∩ fenêtre(enfant) }  ∪  { nouvelles particules fines }
```

Les positions parentes sont conservées. L'héritage est exact par construction.

**Trois conditions d'implémentation, non négociables :**

1. **Ψ unique découpé en bandes de k.** L'enfant applique `ΔΨ` haute fréquence :
   une particule héritée reçoit un *incrément* de position, jamais un nouveau
   déplacement. Mesuré (test 2) : incrément médian **0,344 Mpc** contre un
   déplacement total de 6 Mpc rms, soit **5,7 %**.
2. **Graine RNG des sous-halos dérivée de l'identité du halo** (hash de sa
   position comobile), jamais d'une séquence globale — sinon ajouter des halos au
   layer fin décale le flux aléatoire et re-randomise tout le reste. Équivalent
   particulaire de la règle « phases fixées une fois pour toutes » (§4.3).
   **Non testé à ce jour.**
3. **La récursion de sous-halos EST la hiérarchie de zoom.** Le layer *n* rend les
   niveaux 0..k ; le layer *n+1* rend les mêmes halos avec un niveau de
   sous-structure de plus. L'auto-similarité devient un paramètre.

**Le nombre de particules doit être fixé par la résolution de SORTIE, pas par la
résolution physique du layer** (découvert au test 2 : un parent à 33 k particules
contre 298 k pour l'enfant fait diverger l'écart-type de 24 % ; à densité égale,
1,1 %).

---

## 4. Axe de temps — mécanisme de dissolution

Le paramètre de dissolution est l'**amplitude du déplacement de Zel'dovich**, et
ce n'est pas une analogie : Ψ est proportionnel au facteur de croissance `D(a)`.

```
position(s, a) = q_glass + A(s, a) · Ψ(s)
```

où `A(s,a)` est la courbe existante du §11.4.b (avec le correctif de continuité
du 13 juillet), réutilisée telle quelle.

**Conséquence pratique majeure** : `q` et `Ψ` se calculent **une fois par layer** ;
chaque frame temporelle est une simple reprojection. Les ~114 frames par layer
deviennent bon marché — sans ça, 10 layers × 114 frames à 90 s auraient
représenté 28 h de cuisson.

**Contrainte critique découverte** : à `A → 0` les particules reviennent sur leurs
positions lagrangiennes. Si celles-ci forment un **réseau régulier**, l'état
dissous est un cristal périodique. Mesuré : anisotropie **2,7 × 10⁹**. La
distribution initiale doit être un **verre** (réseau + jitter d'une demi-cellule).

---

## 5. Tests unitaires

### Test 1 — Distribution initiale et dissolution ✅ PASSÉ

Distribution initiale, mesures à `A = 0` :

| distribution | ANISO | P(basse k)/P(haute k) |
|---|---|---|
| Réseau régulier | **2 750 686 601** | 19,10 |
| **Verre (jitter ½ cellule)** | **1,08** | **0,09** |
| Poisson | 1,08 | 1,28 |

Le verre est retenu : même isotropie que Poisson, mais 14× plus uniforme aux
grandes échelles (Poisson laisserait des grumeaux parasites là où l'univers doit
être homogène).

Trajectoire de dissolution, layer G (`l3`, `a_form = 0,92`) :

| a | A(s,a) | ANISO | HF (var. laplacien) | moy/255 | σ | P.fil/grenaille |
|---|---|---|---|---|---|---|
| 1,000 | 1,000 | 0,99 | 1,03e-1 | 68,0 | 53,7 | 222,5 |
| 0,970 | 0,952 | 0,99 | 1,04e-1 | 68,4 | 53,4 | 215,2 |
| 0,940 | 0,822 | 1,02 | 1,07e-1 | 69,5 | 52,1 | 185,4 |
| 0,900 | 0,563 | 1,04 | 1,18e-1 | 72,7 | 47,2 | 108,7 |
| 0,860 | 0,275 | 1,12 | 1,35e-1 | 78,3 | 34,2 | 40,0 |
| 0,820 | 0,052 | 1,12 | 1,40e-1 | 81,4 | 22,9 | 2,2 |
| 0,794 | 0,000 | 1,08 | 1,33e-1 | 81,9 | 20,9 | 0,1 |

- `A(1) = 1,0` et `A(1−10⁻⁶) = 1,0` — contrainte dure §11.4.b vérifiée
- Anisotropie entre 0,99 et 1,12 sur tout le trajet
- **Le contenu haute fréquence ne s'effondre jamais** : il augmente (1,03e-1 →
  1,33e-1). C'est le mode d'échec qui avait fait rejeter le flou et le bruit
  interpolé (§11.2) ; il ne se produit pas ici par construction.
- L'état dissous est « uniforme + grenaille », jamais un gris plat — le garde-fou
  `uniform_floor = 129,4/255` de la matrice devient inutile.

**Défaut relevé** : la moyenne dérive de 68 à 82/255 à exposition figée. Les
layers ne se dissolvant pas au même `a`, cela créerait une rupture de luminosité
en changeant de zoom à date intermédiaire (§11.1 point 3). Correctif :
ajouter la courbe d'exposition à `spacetime_matrix.json`, en tant que **fonction
documentée de (s,a) calculée une fois** — jamais un percentile recalculé par
image (§13.3).

### Test 2 — Héritage de particules G → F ✅ PASSÉ

Champ enfant construit par raccord spectral : modes du parent conservés
**exactement** sous sa coupure (λ = 2,344 Mpc), détail frais au-dessus avec son
amplitude P(k), raccord de puissance dans la bande de recouvrement. Part de
variance héritée : 65,6 %.

Halos : 2 626 halos parents reportés **verbatim** dans un catalogue enfant de
23 214 (11,3 % d'héritage direct), avec rapport de masse d'échelle ×13,82
(= (2,4/1,0)³, cf. peak-patch).

#### 2.a — Stabilité du flux aléatoire ✅

Générateur **basé sur compteur** (splitmix64 vectorisé), graine dérivée du hash
spatial de la position **lagrangienne** (invariant qui traverse les layers).

Le nuage de points d'un halo donné est **strictement identique** qu'il soit
généré seul ou noyé dans le catalogue complet — écart maximal de position
**0,0 Mpc**.

**Deux couplages globaux cachés découverts et corrigés** — chacun aurait
silencieusement cassé l'héritage :

| Défaut | Effet | Correctif |
|---|---|---|
| `counts = w/w.sum() × budget_global` | ajouter des halos au layer fin change la luminosité de **tous** les autres | compte absolu `k × m^slope` |
| `rr = rmax × (m/m.max())^0.28` | `m.max()` dépend du catalogue → rayon différent selon le contexte | référence de masse **absolue** |

Règle générale à retenir : **aucune grandeur par halo ne doit dépendre d'une
statistique globale du catalogue** (somme, max, percentile). C'est l'équivalent
particulaire du piège de normalisation du §13.3.

#### 2.b — Mesures inter-layer, à densité de particules égale

| Critère | Mesuré | Cible |
|---|---|---|
| Corrélation | **0,914** | ≥ 0,85 |
| Écart de moyenne | **0,00/255** | < 2 |
| Écart d'écart-type | **1,1 %** | < 10 |
| ANISO | 0,99 / 0,99 | ~1 |
| Nombre de structures | 355 / 364 | comparables |
| Netteté des pics | 1,29 / 1,28 | identiques |
| Appariement des pics (image complète) | 17 % à ≤1,5 px | ⚠️ cf. décomposition |

Rappel de la référence historique : dépôt CIC, corrélation **0,08-0,43**.

#### 2.c — Décomposition de l'appariement des pics

| Composante | Appariement des pics |
|---|---|
| **Halos seuls** | **médiane 0,00 px — 97 % à ≤1,5 px, 100 % à ≤4 px** |
| Toile seule (caustiques de Zel'dovich) | médiane 5,39 px — 11 % à ≤1,5 px |
| Déplacement mesuré des 2 626 halos partagés | **0,0000 Mpc** |

**L'identité d'objet est exacte.** Le résidu vient entièrement des caustiques de
Zel'dovich, qui se déplacent d'environ 1,4 Mpc (≈1 % de la largeur du champ)
quand l'enfant résout des échelles plus fines. C'est le comportement physique
attendu — ajouter de la puissance à petite échelle déplace le lieu du croisement
des trajectoires — et non une redistribution aléatoire : la corrélation globale
de la toile reste à 0,913.

**Point à trancher** : ce glissement de ~1 % du champ est-il visuellement
acceptable au fondu, ou faut-il l'atténuer par un raccord spectral progressif
(taper) dans la bande de recouvrement, au prix de moins de détail neuf ?

### Test 2c — `A` appliqué par bande de k ✅ PASSÉ — **corrige un défaut de conception**

**Défaut trouvé** : `A(s,a)` étant indexé par *layer*, une particule partagée entre
deux layers recevait deux pondérations différentes, donc deux positions.

| a | D/l1b | E/l2 | F/l2b | G/l3 |
|---|---|---|---|---|
| 1,00 | 1,000 | 1,000 | 1,000 | 1,000 |
| 0,90 | 0,978 | 0,959 | 0,941 | 0,563 |
| 0,80 | 0,909 | 0,834 | **0,768** | **0,003** |

À `a = 0,80`, G est entièrement dissous pendant que F est structuré à 77 % :
écart de déplacement **4,59 Mpc = 18 px** sur le champ de F pour la même
particule. C'est la rupture annoncée au §11.1, et elle est fatale.

**Correctif validé par Marc le 27 juillet** :

```
Psi(a) = Σ_k  A(λ_k, a) · Psi_k          avec  λ_k = 2π/k
```

La position d'une particule devient une fonction **unique** de `a`, identique
quel que soit le layer qui la rend ; le layer ne décide plus que des bandes
qu'il résout. La table `a_form(s)` du §11.4.a est **conservée telle quelle** —
elle est déjà indexée par échelle, ce qui est sa lecture physique la plus
fidèle ; elle n'était appliquée par layer que parce que chaque layer était un
champ séparé.

Contrainte dure revérifiée : `A(λ, a=1) = 1` et `A(λ, 1−10⁻⁹) = 1` pour
**toutes** les bandes.

Pondération mesurée (6 bandes, λ de 1,05 à 201 Mpc) :

| a | λ=1,6 | λ=8,9 | λ=52,9 | λ=128,9 |
|---|---|---|---|---|
| 0,90 | 0,997 | 0,978 | 0,941 | 0,563 |
| 0,80 | 0,986 | 0,909 | 0,768 | 0,003 |
| 0,50 | 0,881 | 0,381 | 0,002 | 0,000 |

**Bénéfice de coût** : le coût FFT est payé une fois ; chaque époque se
recombine au niveau des particules par somme pondérée. Les ~114 frames
temporelles par layer sont donc bon marché.

### Test 3 — Cohérence zoom × temps croisée (G ↔ F à dates intermédiaires) ✅ PASSÉ

Le terme croisé du §11.1 : deux layers adjacents à une date **intermédiaire**.
Exposition `alpha` **commune aux deux layers** (pas recalculée par image, §13.3).

| a | Corrélation | Pics ≤1,5 px | Médiane | Δ moyenne | Δ écart-type | ANISO G / F |
|---|---|---|---|---|---|---|
| 1,00 | 0,996 | 67 % | 1,00 px | 0,27/255 | 0,1 % | 1,02 / 1,04 |
| 0,95 | 0,996 | 68 % | 1,00 px | 0,14/255 | 0,1 % | 1,04 / 1,05 |
| 0,90 | 0,996 | 72 % | 1,00 px | 0,15/255 | 0,1 % | 1,10 / 1,11 |
| 0,86 | 0,996 | 77 % | 1,00 px | 0,22/255 | 0,1 % | 1,10 / 1,11 |
| 0,80 | 0,995 | 83 % | 1,00 px | 0,30/255 | 0,1 % | 1,07 / 1,07 |
| 0,70 | 0,994 | 84 % | 1,00 px | 0,36/255 | 0,2 % | 1,05 / 1,05 |
| 0,50 | 0,986 | 87 % | 1,00 px | 0,40/255 | 0,4 % | 1,11 / 1,09 |

Tous les critères passent avec une large marge, à **toutes** les époques.

**Effet de bord notable** : la formulation par bande améliore aussi la cohérence
de zoom **à a=1** — corrélation 0,996 contre 0,914 au test 2, appariement des
pics 67 % contre 17 %. Le résidu du test 2 n'était donc pas seulement le
glissement physique des caustiques : il venait en grande partie d'une
normalisation d'amplitude incohérente entre parent et enfant dans mon protocole.
La décomposition par bande supprime ce degré de liberté.

**L'appariement s'améliore quand `a` diminue** (67 % → 87 %) : le déplacement de
grande échelle est supprimé en premier, les structures sont donc moins évoluées
et plus faciles à apparier.

### Test 7 — Raccord C/D (sprites → premier layer généré) ⬜ NON COMMENCÉ

Enjeu **nouveau**, absent des documents existants : jusqu'ici D était un champ
lisse sans objets, donc seule la luminosité moyenne devait raccorder (§4.8,
rupture mesurée de 550× corrigée à 8,95/255). Avec ce générateur, D contient des
objets explicites — donc **la même galaxie est rendue par deux moteurs
différents** de part et d'autre du fondu : Barnes-Hut par sprite (§11.5) d'un
côté, nuage de halo à profil radial de l'autre.

Critère à vérifier : au fondu C/D, **flux intégré et rayon apparent égaux** pour
chaque galaxie du catalogue, objet par objet — pas seulement en moyenne.

---

## 6. Décisions en attente

1. **§11.7 (non-régression à `a=1`) tombe.** Le rendu de production change
   entièrement ; la moyenne cible passe de 38 à 68/255 (validé par Marc). En
   cascade : la table évaluée de `matrice-parametres-zoom-temps.md` (moyennes
   105/129), le `uniform_floor`, et la calibration `residual_bg` du §4.8 sont
   toutes indexées sur l'ancien aspect et à refaire.
2. **Résolution du champ.** À 384³ sur 450 Mpc, la coupure de Nyquist vaut
   2,34 Mpc et `lam_min_mpc = 1,318` (calibré) reste **sous cette limite, donc
   inactif**. Il manque de ce fait les structures les plus fines (417 structures
   mesurées contre 512 dans la référence). À monter en cuisson de production.
3. **Recâblage §11.3** : toile, halos et embrasement doivent être combinés par
   l'opérateur « screen », chacun avec sa propre transformation non linéaire —
   actuellement les particules de toile et de halos sont sommées dans un buffer
   commun avant une seule courbe de ton. Acceptable selon §11.3 (« même nature de
   contenu ») mais à trancher explicitement.

---

## 7. Réserve de méthode

L'outil d'inspection d'images n'est pas disponible dans la session en cours.
**Toutes les conclusions de ce document sont mesurées, non vues.** Les métriques
couvrent : anisotropie directionnelle, contenu haute fréquence, continuité de
population (creux bimodal), concentration du flux, nombre et élongation des
structures, netteté des pics, résolution effective, corrélation et appariement
inter-layer. Un défaut d'aspect en dehors de ces axes passerait au travers — la
confirmation visuelle par Marc reste requise avant clôture (§13.1).

### Test 4 — Dissolution des points lumineux en filaments ✅ MÉCANISME VALIDÉ

Demande de Marc (27 juillet) : les points lumineux des layers de densité élevée
n'existaient pas dans l'ancien générateur. Ils ne doivent pas **pâlir sur place**
en remontant le temps — ils doivent **s'étirer le long du filament** qui a
alimenté le halo, puis se fondre dans la nappe.

**Mécanisme : ancrage lagrangien.** Chaque point du halo est un élément de masse
avec sa position initiale `q_i`, tirée dans la *patch lagrangienne* du halo :

```
pos_i(a) = q_i + Psi(q_i, a) + C(a) · ( cible_compacte_i − [q_i + Psi(q_i, 1)] )
```

`C(a)` suit l'`a_form` de l'échelle propre du halo (§11.4.a). À `a=1`, `C=1` et
la position vaut exactement la cible compacte — **le rendu validé est reproduit
au bit près** (vérifié : `cible identique = True`).

| a | C(a) | Élongation du nuage | Nettété | Structures | ANISO | HF (var. lapl.) | σ |
|---|---|---|---|---|---|---|---|
| 1,00 | 1,000 | 1,21 | 1,08 | 405 | 1,03 | 4,39e-1 | 76,5 |
| 0,90 | 0,975 | 1,42 | 1,07 | 373 | 1,10 | 4,46e-1 | 77,2 |
| 0,80 | 0,895 | 2,46 | 1,33 | 358 | 1,09 | 4,49e-1 | 77,8 |
| 0,70 | 0,757 | 3,08 | 1,27 | 370 | 1,05 | 4,70e-1 | 78,4 |
| **0,60** | 0,560 | **3,25** | 1,29 | 442 | 1,10 | 5,25e-1 | 77,4 |
| 0,50 | 0,318 | 2,90 | 1,44 | 627 | 1,10 | 6,03e-1 | 73,3 |
| 0,40 | 0,081 | 2,13 | 1,75 | 995 | 1,07 | 6,61e-1 | 69,0 |
| 0,30 | 0,000 | 1,45 | 1,79 | 1018 | 1,04 | 6,99e-1 | 65,9 |
| 0,20 | 0,000 | 1,21 | 1,82 | 937 | 1,04 | 7,36e-1 | 62,0 |

Trajectoire en trois phases : **point compact → filament étiré à 3,25:1 →
retour au verre uniforme**. Les hautes fréquences montent continûment sans
jamais s'effondrer ; l'anisotropie reste entre 1,03 et 1,10. Rien n'est flouté,
rien ne pâlit : les points se **déplacent**.

#### 4.a — Le verre ne coûte rien

Le test 1 imposait un verre en remplacement du réseau régulier. Vérifié à
paramètres égaux (layer G, demi-champ 150) :

| départ | Netteté à a=1 | ANISO à a=1 | ANISO à A=0 |
|---|---|---|---|
| Réseau régulier | 1,81 | 1,01 | **18,9** |
| Verre ¼ cellule | 1,85* | 1,01 | 7,04 |
| **Verre ½ cellule** | **1,85** | 1,00 | **1,09** |

Le verre à ½ cellule est donc gratuit en aspect et indispensable en dissolution.
Le ¼ de cellule ne suffit pas à casser les pics de Bragg.

#### 4.b — Fausse alerte de non-régression, et correctif de métrique

Une chute apparente de la netteté (1,81 → 1,25) a d'abord été attribuée au
générateur. **Reconstruction à l'identique de la configuration validée : 1,81 /
417 structures / ANISO 1,02, exactement.** Puis variation d'un seul paramètre :

| Variation | Netteté |
|---|---|
| Baseline, demi-champ 150 Mpc | 1,81 |
| Mêmes particules, demi-champ 100 | 1,57 |
| Mêmes particules, demi-champ **67,08** | **1,25** |
| Mêmes particules, demi-champ 40 | 2,10 |

Le 1,81 était mesuré sur le layer **G** (150 Mpc), le banc de test sur **F**
(67,08 Mpc) : deux scènes différentes. **Il n'y a jamais eu de régression.**

**Correctif de métrique obligatoire** : `peak_sharpness` utilisait une fenêtre de
11 pixels fixes, donc une taille *physique* différente à chaque zoom. À fenêtre
physique constante (3 Mpc) :

| demi-champ | fenêtre 5 px | fenêtre 3 Mpc |
|---|---|---|
| 150 Mpc | 1,81 | 1,49 |
| 100 Mpc | 1,57 | 1,56 |
| 67 Mpc | 1,25 | 1,36 |
| 40 Mpc | 2,10 | **2,47** |

Le creux était un artefact. La netteté est plate de 150 à 67 Mpc, et **remonte
au zoom profond** parce que la sous-structure des halos devient résolue — c'est
la récursion fractale qui tient l'exigence « zones les plus lumineuses quasi
ponctuelles à tous les étages de zoom ».

**Règle** : toute métrique spatiale de ce banc doit être exprimée en unités
**comobiles**, jamais en pixels. Même piège que `lam_min_px` (§11.9).

#### 4.c — Reste à traiter

La dérive de moyenne s'aggrave : **68 → 103/255** contre 68 → 82 au test 1.
La courbe d'exposition dans `spacetime_matrix.json` n'est plus optionnelle.

### Test 4.d — La dérive de moyenne n'est pas un défaut ✅

Alerte levée. Avec un `alpha` unique figé, la moyenne dérive bien dans le temps
(68 → 88/255 de a=1 à a=0,3), mais les **deux layers se suivent** :

| a | moy G | moy F | écart |
|---|---|---|---|
| 1,00 | 68,0 | 68,3 | 0,27 |
| 0,80 | 69,9 | 70,2 | 0,32 |
| 0,60 | 76,3 | 76,9 | 0,61 |
| 0,40 | 85,1 | 85,3 | 0,16 |
| 0,30 | 88,0 | 87,4 | 0,58 |

Écart maximal **0,61/255**, très en deçà de la cible de 2. La formulation par
bande (test 2c) avait déjà réglé la cohérence inter-layer. Il ne reste qu'une
trajectoire de luminosité partagée, indépendante du layer — à **documenter**
comme `T(a)`, pas à corriger. Elle va d'ailleurs dans le sens du
`uniform_floor = 129,4/255` déjà prévu par la matrice.

### Test 5 — Couverture du cadre (§11.4.f) ✅ PASSÉ

Critère repris **du validateur existant** (`validate_spacetime_matrix.py`,
`spacetime_pipeline.py`) plutôt que réinventé :

```
clamp_defect = Σ_layers  poids(hw_eff) · fraction_hors_texture · (f_std > 0.005)
clamp_visible = clamp_defect · (1 − embrasement)          seuil : < 5 %
```

Un recadrage ne compte que si le layer est **effectivement affiché**, que sa
frame est **encore structurée**, et que l'**embrasement** ne l'a pas noyée.

Trois conditions à réunir, et deux calculs intermédiaires faux avant d'y arriver :

1. Juger la structure sur la seule échelle du layer → E et F apparaissent en
   défaut (marges 1,72 et 1,77). **Faux** : avec `A` par bande, les petites
   échelles persistent bien plus longtemps.
2. Juger sur la plus petite bande encore structurée → neuf layers sur dix en
   défaut, jusqu'à ×10. **Faux aussi** : quand le cadre s'élargit, les **poids
   de layers changent** et un layer plus grossier prend le relais.
3. Poids réels + bande structurée **et** résolue à l'écran + embrasement :

| Layer | Extent disponible | Extent requis | a critique | Marge requise | Verdict |
|---|---|---|---|---|---|
| l1b | 12,7 | 9,9 | 0,095 | **1,16** | OK |
| l2 | 45,0 | 34,9 | 0,287 | 1,16 | OK |
| l2b | 100,6 | 78,1 | 0,081 | 1,16 | OK |
| l3 | 225,0 | 174,6 | 0,380 | 1,16 | OK |
| l3b | 318,2 | 247,0 | 0,229 | 1,16 | OK |
| l4 | 450,0 | 349,4 | 0,097 | 1,16 | OK |
| l4a | 1190,6 | 924,2 | 0,456 | 1,16 | OK |
| l4b | 3150,0 | 2445,0 | 0,469 | 1,16 | OK |
| l5a | 8297,2 | 6440,2 | 0,788 | 1,16 | OK |
| l5 | 34968,0 | 17733,7 | 0,822 | **1,22** | OK |

**Aucun layer en défaut.** Les marges de production (1,5 ; 2,4 pour M) couvrent
le besoin réel (1,16 ; 1,22) avec de la réserve. La course est gagnée par la
dissolution : la structure disparaît avant que le cadre ne dépasse la texture.

**Réserve** : dérivation géométrique à partir des poids de layers, de la règle
d'expansion par échelle, de l'embrasement et du `A` par bande — pas une mesure
sur rendus réels. Une confirmation par cuisson reste souhaitable.

---

## RÉVISION MAJEURE — 28 juillet : croissance globale et conservation de la masse

Retour visuel de Marc sur le montage de dissolution : *« on a l'impression que
des structures plus petites apparaissent lors de la dissolution et finissent par
coloniser l'espace, plutôt qu'une réelle dissolution des structures initiales.
Cela ne ressemble pas à une dissolution naturelle, comme une goutte dans un
liquide. »*

**Diagnostic — deux défauts de fond, pas des réglages.**

### R.1 — `A` par bande était physiquement faux

En théorie linéaire, le facteur de croissance s'applique **identiquement à
toutes les échelles** : `Psi_k(a) = D(a)/D(1) · Psi_k(1)` pour tout k. La
hiérarchie du §11.4.a (galaxies tôt, amas tard) n'est **pas** une différence de
vitesse de croissance : c'est une conséquence **émergente** de la non-linéarité
— les petites échelles ont plus d'amplitude au départ, donc franchissent le
seuil d'effondrement plus tôt.

En imposant `a_form` **en entrée** par bande, je faisais survivre les petites
échelles artificiellement. À `a = 0,4` : λ=1,6 Mpc à **80 %** d'amplitude, λ≥53 Mpc
à **0 %**. Les petites structures envahissaient l'image dès que l'enveloppe qui
les organisait disparaissait.

**Correctif** : un seul scalaire `D(a)` ΛCDM pour toutes les échelles. La
hiérarchie passe dans le facteur d'effondrement des halos, où elle est
**dérivée** au lieu d'être posée :

```
C(a) = smoothstep( clamp( D(a) / D_form ) )     D_form = min(delta_c / nu, 1)
```

`nu` = hauteur du pic. `C(a=1) = 1` est **exact pour tous les halos** par
construction (contrainte §11.4.b).

| a | Structures (A par bande) | Structures (D global) |
|---|---|---|
| 1,00 | 141 | 141 |
| 0,60 | 234 | 175 |
| **0,40** | **539** | **185** |
| 0,20 | 407 | 223 |

L'explosion ×3,8 devient ×1,3. `a=1` strictement inchangé.

### R.2 — Les halos ajoutaient de la masse au lieu d'en concentrer

Défaut révélé en cherchant à re-valider le test 5 : même à `a = 0,01` avec un
déplacement quasi nul, il restait **13,96/255** de structure lissée. Cause : les
points de halos étaient **ajoutés** à la toile dans des patches sphériques
isolés, qui ne pavent pas l'espace. À dissolution totale il restait donc des
grumeaux là où l'univers doit être uniforme — la dissolution ne se terminait
jamais.

**Correctif** : un halo ne crée pas de matière, il **concentre** celle qui
existe. Ses points sont désormais **prélevés** dans la toile (les particules de
verre les plus proches de son centre lagrangien, les halos massifs se servant en
premier). Conséquences :

- masse totale conservée
- à `C = 0`, les points reviennent **exactement** dans le verre → uniformité exacte
- 25 % de la toile assignée aux halos

| a | D(a) | σ structure (lissée 8 px) |
|---|---|---|
| — | — | **0,65 = verre pur (référence)** |
| 1,00 | 1,0000 | 43,01 |
| 0,40 | 0,4957 | 31,15 |
| 0,20 | 0,2531 | 19,39 |
| 0,10 | 0,1269 | 10,77 |
| 0,05 | 0,0635 | 5,68 |
| 0,02 | 0,0254 | **2,38** |

Décroissance monotone vers le verre. **Correctif de métrique associé** : σ brut
mélange structure et bruit de grenaille (il stagne à ~41/255 même dissous) ; il
faut mesurer σ **après lissage à 8 px** pour isoler la structure. Troisième
occurrence du même piège après `peak_sharpness` en pixels et le critère de
couverture — toute métrique de ce banc doit isoler explicitement l'échelle
qu'elle prétend mesurer.

### R.3 — Tests à refaire

Cette révision invalide les résultats obtenus avec `A` par bande :

| Test | Impact | À refaire |
|---|---|---|
| 1 — dissolution layer isolé | mécanisme changé | **oui** |
| 2 / 2b — héritage, identité d'objet | indépendant de `A` | non |
| 2c — `A` par bande | **remplacé par `D` global** | obsolète |
| 3 — cohérence croisée | `D` global est un scalaire partagé : plus facile à satisfaire | **oui**, par sécurité |
| 4 — points → filaments | `C(a)` redéfini | **oui** |
| 5 — couverture du cadre | dépend du moment où la structure disparaît, qui a changé | **oui** |
| 6 à 9 | non commencés | — |

---

## Re-validation apres la revision du 28 juillet

Tous les chiffres ci-dessous sont obtenus avec **croissance lineaire globale
`D(a)` + halos a masse conservee** (points preleves dans la toile).

### Test 1 (rejoue) ✅

| a | D(a) | ANISO | HF (lapl.) | σ structure | moy | Netteté |
|---|---|---|---|---|---|---|
| 1,00 | 1,0000 | 1,02 | 2,36e-1 | 43,01 | 68,0 | 1,65 |
| 0,70 | 0,7975 | 0,97 | 2,42e-1 | 39,74 | 70,7 | 1,57 |
| 0,50 | 0,6068 | 0,95 | 2,61e-1 | 34,83 | 74,7 | 1,64 |
| 0,30 | 0,3768 | 1,08 | 3,10e-1 | 26,21 | 82,8 | 1,72 |
| 0,15 | 0,1901 | 1,12 | 3,55e-1 | 15,26 | 90,2 | 1,79 |
| 0,05 | 0,0635 | 1,13 | 3,78e-1 | 5,68 | 93,8 | 2,01 |
| 0,02 | 0,0254 | 1,04 | 3,81e-1 | **2,38** | 94,2 | 2,09 |

Anisotropie 0,95-1,13, HF jamais effondré, σ structure décroissante et monotone
vers le verre pur (0,65).

### Test 3 (rejoue) ✅ — nettement meilleur qu'avec `A` par bande

| a | Corrélation | Pics ≤1,5 px | Médiane | Δ moyenne | Δ écart-type |
|---|---|---|---|---|---|
| 1,00 | 0,998 | 87 % | **0,00 px** | 0,17/255 | 0,7 % |
| 0,90 | 0,999 | 98 % | 0,00 px | 0,13/255 | 0,6 % |
| 0,80 | 0,999 | 91 % | 0,00 px | 0,06/255 | 0,4 % |
| 0,60 | 0,999 | 95 % | 0,00 px | 0,05/255 | 0,0 % |
| 0,40 | 0,999 | 94 % | 0,00 px | 0,00/255 | 0,2 % |
| 0,20 | 0,998 | 94 % | 0,00 px | 0,08/255 | 0,4 % |

(Pour mémoire, avec `A` par bande : 0,986-0,996 et 67-87 % ; avec dépôt CIC
historique : 0,08-0,43.)

Le déplacement médian des pics est **exactement nul à toutes les époques** :
un scalaire `D(a)` partagé rend le déplacement des bandes communes strictement
identique entre layers.

### Test 4 (rejoue) ✅

| a | D(a) | C médian | Élongation | Étendue rms |
|---|---|---|---|---|
| 1,00 | 1,000 | 1,000 | 1,30 | 0,41 Mpc |
| 0,80 | 0,876 | 1,000 | 1,81 | 0,67 |
| 0,60 | 0,708 | 1,000 | 2,38 | 1,26 |
| **0,50** | 0,607 | 1,000 | **2,39** | 1,60 |
| 0,30 | 0,377 | 0,999 | 2,10 | 1,89 |
| 0,10 | 0,127 | 0,257 | 1,75 | 2,06 |

Observation notable : l'élongation monte **alors que `C` vaut encore 1**. Le
moteur de l'étirement n'est donc pas la décompaction du halo mais le
**cisaillement de marée** à travers sa patch lagrangienne — la variation
anisotrope de Psi sur ~2,4 Mpc. C'est le mécanisme physique correct, et il n'est
pas imposé : il émerge.

### Test 5 (rejoue) ⚠️ PASSÉ SAUF `l5`, non vérifiable sur ce banc

La partie géométrique est inchangée : chaque layer borné n'est affiché que sur
sa bande de zoom, un layer plus grossier prenant le relais quand le cadre
s'élargit. Marge requise **1,16** contre 1,5 disponible — inchangé, ce résultat
ne dépend pas du modèle de croissance.

**`l5` est le seul cas ouvert.** Dernier de l'ordre, il n'a aucun layer plus
grossier pour prendre le relais ; son cadre est recadré dès `a < 0,417`
(hw_eff > 34 968 Mpc), et à `a = 0,3` c'est **48 %** du cadre qui sort de la
texture — très au-delà du seuil de 5 %.

Avec `A` par bande, `a_form(14570) = 1,0` faisait disparaître sa structure dès
`a = 0,82` et le recadrage devenait invisible. Avec la croissance globale, sa
structure persiste : le critère `f_std > 0,005` risque de rester vrai.

L'argument qui devrait le sauver : à l'échelle de `l5`, les structures de la
toile (~50-150 Mpc) sont **très en dessous du pixel** (68 Mpc/px à `a=1`), donc
sa texture est déjà un grain quasi uniforme — conforme d'ailleurs au « End of
Greatness » du §4.1. Mais **ce banc de test travaille dans une boîte de 201 Mpc
et ne peut pas le mesurer.** Une cuisson à l'échelle de `l5` est requise pour
trancher.

### Test 5 — `l5` : ouvert, à trancher dans le vrai validateur ⚠️

Cuisson à l'échelle de `l5` (boîte 69 936 Mpc, cellule 182 Mpc, 3,5 M particules).

**Ce qui est établi :**

- le déplacement de Zel'dovich vaut **0,105 pixel** à cette échelle (6 Mpc rms
  pour 56,9 Mpc/px) — il ne peut produire aucune structure ;
- à `a = 1`, l'indicateur de structure vaut **3,55** contre 0,53 pour le verre
  pur : `l5` est bien quasi uniforme, conforme au « End of Greatness » (§4.1) ;
- la seule structure possible y est le **regroupement des halos**.

**Ce qui reste ouvert** : le comportement au recadrage (`a < 0,417`). Trois
erreurs de protocole successives sur cette mesure, toutes détectées par des
sauts d'écart-type incohérents :

1. tranche de particules dimensionnée pour `hw = 14570` puis rendue à 34 968 —
   les bords se vidaient ;
2. `alpha` figé alors que la tranche s'épaissit avec le champ — l'image saturait
   à 235/255 ;
3. un écart-type anormal sur le rendu pleine boîte, non expliqué.

**Recommandation** : ne pas continuer à rapiécer ce banc. Le dépôt contient déjà
`scripts/dev/validate_spacetime_matrix.py` (157 contrôles, dont §11.4.f, avec
contrôle croisé JS/Python à ~1e-7). Y brancher le générateur par particules vaut
mieux que réimplémenter le contrôle — c'est d'ailleurs ce validateur qui a
détecté un vrai écart d'ordre d'embrasement le 13 juillet.

### Test 6 — Composition (§11.3) ✅ PASSÉ

**6.a — toile et halos forment UNE seule population.**

| Méthode | moy | σ | Netteté |
|---|---|---|---|
| Somme **avant** la courbe de ton | 68,0 | 67,5 | **1,65** |
| « Screen » après deux courbes séparées | 73,3 | 74,4 | 1,10 |

Écart moyen 5,28/255, maximum 244,9/255. Le « screen » **détruit la netteté des
pics** (1,65 → 1,10), chaque population étant normalisée séparément et la couche
de halos, éparse, se trouvant gonflée.

Surtout, la question ne se pose plus depuis la conservation de la masse : les
halos **sont** des particules de la toile, prélevées et déplacées. Les composer
en « screen » reviendrait à compter deux fois la même matière. La somme avant
courbe de ton est la seule option correcte, et le §11.3 est respecté — il n'y a
bien qu'**un** type de contenu ici.

**6.b — l'embrasement, lui, doit être en « screen » APRÈS la courbe de ton.**

| a | white | Screen après ton (moy / σ) | Offset avant ton (moy / σ) | Écart max |
|---|---|---|---|---|
| 0,050 | 0,0543 | 78,2 / 28,6 | 68,0 / 20,9 | 29,7/255 |
| 0,030 | 0,5926 | 178,8 / 12,1 | 68,0 / 5,1 | 130,5/255 |
| 0,020 | 0,9761 | 250,5 / 0,7 | 68,0 / 3,3 | 187,4/255 |
| 0,015 | 0,9995 | **254,9 / 0,0** | 68,0 / 3,3 | 193,2/255 |

Seul le « screen » après le ton converge vers le blanc. En offset avant le ton,
la résolution de `alpha` compense l'offset et la moyenne reste clouée à 68 —
l'embrasement n'a littéralement aucun effet. Écart jusqu'à **193/255** : c'est
exactement le type d'erreur d'ordre que le contrôle croisé du projet avait
détecté le 13 juillet. La règle du §11.4.c est confirmée par la mesure.

