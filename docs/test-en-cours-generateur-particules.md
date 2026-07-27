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

### Test 3 — Raccord C/D (sprites → premier layer généré) ⬜ NON COMMENCÉ

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
