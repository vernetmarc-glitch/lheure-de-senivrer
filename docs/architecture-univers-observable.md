# Architecture — Carte interactive de l'univers observable
### Document de référence technique et scientifique
Version 1.0 — Juillet 2026

---

## 0. État actuel du projet — résumé pour reprise de contexte

*(Section mise à jour le 7 juillet 2026, pensée pour permettre à Claude de reprendre ce projet dans une nouvelle conversation sans relire tout l'historique. Décrit l'état ACTUEL et son rationnel — pas l'historique des étapes pour y arriver.)*

**Dépôt et déploiement**
- Dépôt : `vernetmarc-glitch/lheure-de-senivrer` (renommé depuis `carte-univers-observable`)
- Site en ligne : https://vernetmarc-glitch.github.io/lheure-de-senivrer/
- Outils de calibration : `glow-test.html` (style/couleur des textures de densité) et `l1b-anchor-test.html` (halo/bruit de fond de l'ancrage du Groupe Local sur `l1b`) — cf. §4.7
- Déploiement automatique via GitHub Actions (`.github/workflows/deploy.yml`) sur push vers `main`
- Projet installable en PWA (`manifest.json`, icônes générées depuis le logo fourni), nom affiché "L'Heure de s'enivrer"

**Architecture de rendu actuelle**
- App plein écran (pas d'onglets, pas de légendes texte) : titre en haut à gauche, bouton réglages (⚙) en haut à droite (style + présence du fond), curseur de zoom vertical à droite, curseur de temps horizontal en bas — tous en overlay sur la carte, avec `env(safe-area-inset-*)`.
- Zone de rendu clampée à un ratio max de 2,4:1 (bandes noires fixes au-delà) pour éviter qu'un layer ne "disparaisse" sur écrans très larges/étroits.
- Canvas dimensionnés selon `devicePixelRatio` (plafonné à 3) pour la netteté sur écrans Retina.
- Chargement des textures progressif et priorisé (le layer du zoom courant en premier, affichage dès l'arrivée de chaque texture), avec indicateur discret en bas à droite.
- **Principe général de performance retenu** : tout ce qui PEUT être pré-calculé hors-ligne (Node/Python) et livré sous forme de bitmap L'EST, plutôt que d'être recalculé à chaque frame côté client. Les seuls rendus encore "en direct" (RealGalaxiesLayer, cf. §4.6) le sont par nécessité (position/taille dépendent du zoom courant), mais restent légers : quelques `drawImage`, jamais de génération procédurale ni de boucle sur des milliers d'éléments par frame.

**Les layers, du plus proche au plus lointain**

1. **`milkyway`** (`DensityLayer.tsx`, texture `density_milkyway.png`) : disque + bulbe de la Voie lactée UNIQUEMENT (pas les galaxies voisines, cf. point 2). Généré hors-ligne en exécutant le vrai module partagé `GalaxyModel` (récupéré depuis le dépôt `le-silence-du-cosmos` au moment de la génération, jamais réimplémenté localement) — cf. `scripts/generate_simulated_textures.mjs`. N'est plus chargé côté client en JavaScript : seul le résultat pré-cuit (bitmap) est livré à l'app.

2. **`RealGalaxiesLayer`** (composant React séparé, `app/src/RealGalaxiesLayer.tsx`, PAS une entrée de `DensityLayer`) : compose au runtime 9 sprites pré-cuits individuels — la Voie lactée elle-même (pour rester visible même une fois sortie du zoom rapproché du point 1) + les 8 galaxies réelles nommées du Groupe Local (Andromède, Triangulum/M33, Grand/Petit Nuage de Magellan, Naine du Sagittaire, NGC 6822, IC 10, Leo I). Chaque sprite est généré séparément (`generateRealGalaxySprite()` / `generateMilkyWay()` dans `generate_simulated_textures.mjs`), dimensionné sur SA PROPRE taille (résolution relative identique pour toutes, quelle que soit leur distance réelle), avec un halo doux qui s'étend au-delà du nuage d'étoiles net pour amorcer une transition avec le layer de densité au-dessus (§4.6). La Voie lactée est dessinée EN PREMIER (dessous) : son halo, même réduit, ne doit jamais pouvoir recouvrir visuellement une galaxie plus proche (la Naine du Sagittaire, à seulement 0,024 Mpc, est la plus proche des 8).

3. **`localgroup`** (`DensityLayer.tsx`, texture `density_localgroup.png`) : texture procédurale pour les ~90 galaxies de champ NON nommées du Groupe Local (halo dépendant de la distance, pas de sprite individuel) — cf. `generate_local_group_texture.py`.

4. **`l1b` → `l5`** (`DensityLayer.tsx`) : 10 layers procéduraux de densité (doublé depuis 5 initialement) : `l1b`, `l2`, `l2b`, `l3`, `l3b`, `l4`, `l4a`, `l4b`, `l5a`, `l5`. Les paliers "a"/"b" sont des paliers TECHNIQUES (pas de nouveaux layers scientifiques). Champ gaussien aléatoire (GRF) généré GRAND → PETIT (`l5`, le plus grand et le plus lisse, sert de racine ; chaque layer plus fin hérite de son plus proche ancêtre scientifique et y ajoute du détail passe-haut, poids 0,74/0,67) — cf. §4.3-4.4, principe **non modifié** malgré la tentation d'inverser ce sens (cf. §4.7). En plus de ce champ hérité, `l1b`/`l2`/`l2b` reçoivent un ANCRAGE ADDITIONNEL sur les positions réelles du catalogue du Groupe Local (98 galaxies), avec une intensité décroissante à mesure qu'on s'éloigne, volontairement arrêtée à `l2b` (~67 Mpc) — cf. §4.7.

**Fichiers de génération (dans `/scripts`)**
- `generate_layers.py` (Python) : génère les 10 textures procédurales de densité (résolution 1024, marge de génération ×1,5 — ×2,4 pour L5 spécifiquement, seul layer visible pile à son bord extrême) + l'ancrage du Groupe Local sur `l1b`/`l2`/`l2b` (fonction `apply_local_group_anchor`, cf. §4.7).
- `generate_simulated_textures.mjs` (Node) : génère la texture `milkyway` (disque + bulbe, via le vrai `GalaxyModel` distant) et les 9 sprites individuels de `RealGalaxiesLayer` (Voie lactée + 8 galaxies réelles, avec halo).
- `generate_local_group_texture.py` (Python) : texture `localgroup` (galaxies procédurales non nommées).
- `generate_local_group_catalog.py` (Python) : construit le catalogue JSON de 98 galaxies (8 réelles nommées, positions/tailles réelles + ~90 galaxies de champ procédurales, distance 1-10 Mpc, `isReal: false`) — SOURCE UNIQUE consommée à la fois par `RealGalaxiesLayer.tsx`, `generate_local_group_texture.py` et `generate_layers.py`.
- `local_group_style.py` (Python) : source unique des constantes de rendu des galaxies réelles pour le champ de densité (taille de halo, suppression de bruit local...) — ne jamais redéfinir ailleurs.

**Processus de développement/validation pour tout travail génératif ou visuel** : cf. §13 — toujours valider par un calcul objectif hors-ligne (`scripts/dev/`) avant de présenter un résultat comme corrigé, jamais sur la seule base des courbes de paramètres.

**Points de vigilance connus — synchronisation manuelle requise**
- `app/public/glow-test.html` duplique manuellement la liste des layers de densité et leurs marges (pas de build partagé). Toute évolution côté production (`DensityLayer.tsx`) doit être répercutée à la main, sinon désynchronisation silencieuse (déjà arrivé une fois).
- `app/public/l1b-anchor-test.html` est un outil de calibration VISUELLE (aperçu approximatif, bruit de démonstration plutôt que le vrai champ BBKS) — les valeurs qu'il affiche sont un point de départ à reporter et affiner dans `generate_layers.py`, pas une garantie de rendu pixel-identique.
- `generateRealGalaxySprite()`/`generateMilkyWay()` (JS, `generate_simulated_textures.mjs`) et `RealGalaxiesLayer.tsx` partagent des constantes (`SPRITE_MARGIN`, le rayon de la Voie lactée) qui doivent rester synchronisées manuellement entre les deux fichiers — commentées explicitement à chaque occurrence.
- `field_to_log_density()` (dans `generate_layers.py`) applique un `exp()` avant le calcul de densité — toute valeur ajoutée en amont (ex. un ancrage) y est donc amplifiée de façon EXPONENTIELLE, pas linéaire. Une amplitude qui semble modeste dans le champ brut peut dominer complètement l'export après ce passage ; à l'inverse, un flou (`gaussian_filter`) appliqué avant ce transform peut détruire une texture fine de façon disproportionnée. Toujours vérifier le résultat exporté (histogramme, écart-type, comparaison visuelle), pas seulement les paramètres d'entrée.

**Chantiers en attente, déjà cadrés (cf. §11, qui remplace/complète §9)**
L'axe du temps (a(t)) n'est pas encore implémenté en production : actuellement la carte est en coordonnées comobiles fixes (rien ne bouge avec le temps, seule la luminosité change). La conception complète — compression spatiale, dissolution des structures par époque de formation propre à chaque échelle, couleur de convergence partagée, fond résiduel sur les layers à sprites — est documentée en détail au §11 (matrice zoom × temps), avec plusieurs prototypes déjà réalisés et listés en §11.5. Reste à intégrer en production.

---

## 1. Vision du projet

Application web dynamique représentant l'univers observable en coupe 2D ("vu du dessus"), pilotée par deux axes de navigation indépendants :

- **Axe de zoom (échelle spatiale)** : de la Voie lactée et son environnement proche jusqu'à ~95 milliards d'années-lumière de diamètre (taille actuelle de l'univers observable).
- **Axe temporel** : du découplage matière-rayonnement (~380 000 ans après le Big Bang) jusqu'à aujourd'hui (13,8 milliards d'années).

L'application doit permettre de visualiser simultanément :
1. La structure hiérarchique de la matière (galaxies → amas → filaments → toile cosmique → homogénéité).
2. L'expansion physique de l'espace (dilution de la densité + croissance de l'horizon observable).

Le choix de la 2D est délibéré : il permet d'observer clairement les irrégularités de densité et les grandes structures sans l'occlusion propre à la 3D.

---

## 2. Système de coordonnées — principe fondamental

**Décision d'architecture centrale : la carte est un référentiel en coordonnées comobiles fixes.**

- La grille de la carte (95 milliards d'années-lumière de côté à son échelle maximale) ne bouge jamais, quelle que soit la position du curseur temporel.
- Ce qui varie avec le temps, c'est :
  - le **facteur d'échelle a(t)**, qui convertit une distance comobile en distance physique réelle à cette époque,
  - le **rayon de l'horizon observable** (particle horizon), qui croît avec le temps sur cette grille fixe,
  - la **densité de matière affichée**, qui se dilue avec l'expansion.

Ce choix résout élégamment trois problèmes soulevés pendant la phase de cadrage :
1. Pas besoin de reprojeter/redessiner la grille à chaque pas de temps — seule une couche d'échelle et un cercle de rayon variable changent.
2. La confusion initiale entre "distance parcourue par la lumière" et "distance réelle actuelle" ne se pose plus : on travaille nativement en comobile.
3. La question de l'héritage entre layers de zoom devient un problème de filtrage sur un champ figé, pas de régénération.

### 2.1 Rappel des trois notions de distance (pour la documentation interne)

| Distance | Définition | Usage dans l'app |
|---|---|---|
| Comobile | Distance fixe dans le référentiel en expansion, ne change jamais pour deux points sans mouvement propre | Système de coordonnées de la carte |
| Propre (physique) | Distance réelle à un instant t = distance comobile × a(t) | Utilisée pour convertir densité, tailles physiques affichées en légende |
| Parcourue par la lumière (lookback) | c × temps de trajet du photon | Utile uniquement pour les explications pédagogiques, pas pour le rendu |

---

## 3. Modèle cosmologique (axe temporel)

### 3.1 Paramètres retenus (Planck 2018, base-ΛCDM)

```
H0  = 67.4 km/s/Mpc      (constante de Hubble)
Ωm  = 0.315              (densité de matière, baryonique + noire)
ΩΛ  = 0.685              (densité d'énergie noire)
Ωr  = 9.24e-5            (densité de radiation — négligeable après recombinaison)
Âge de l'univers : 13.797 Ga (calculé, cohérent avec la valeur Planck)
```

### 3.2 Facteur d'échelle a(t)

Pour tout t postérieur à la recombinaison (domaine couvert par le curseur), la radiation est négligeable et la solution fermée matière + énergie noire s'applique :

```
a(t) = (Ωm/ΩΛ)^(1/3) · [ sinh( (3/2)·√ΩΛ·H0·t ) ]^(2/3)
```

avec convention a(aujourd'hui) = 1. Cette formule unique couvre tout l'intervalle du curseur temporel (découplage → aujourd'hui), avec une légère approximation près du découplage (radiation non totalement nulle à z~1100, écart négligeable pour l'usage visuel).

### 3.3 Facteur de dilution de densité

```
densité_affichée(t) = densité_référence_aujourd'hui × [1 / a(t)³]
```

C'est ce facteur scalaire, appliqué uniformément à tous les layers actifs, qui traduit "l'élastique qui se resserre" quand on remonte dans le temps.

### 3.4 Rayon de l'horizon observable (comobile)

Calculé par intégration complète de l'équation de Friedmann (radiation + matière + énergie noire) :

```
χ(t) = ∫₀ᵗ c·dt' / a(t')
```

Valeurs de référence à intégrer dans le moteur de rendu (pré-calculées, interpolées à l'exécution) :

| Époque | Âge | a(t) | Rayon comobile horizon | Facteur dilution 1/a³ |
|---|---|---|---|---|
| Recombinaison (z≈1100) | 0,00038 Ga | 0,00091 | 0,28 Gpc (~0,9 Gal) | ~1,3 × 10⁹ |
| z=10 | 0,47 Ga | 0,091 | 4,51 Gpc (~14,7 Gal) | ~1 288 |
| z=1 | 5,84 Ga | 0,50 | 10,74 Gpc (~35 Gal) | ~8,3 |
| Équivalence matière/ΛCDM (z≈0,3) | 10,25 Ga | 0,77 | 12,91 Gpc (~42 Gal) | ~2,5 |
| Aujourd'hui | 13,80 Ga | 1,0 | 14,14 Gpc (~46,1 Gal) | 1 |

**Recommandation d'implémentation** : générer une table de ~200-500 points (t, a, χ) par intégration numérique offline (script Python), puis interpoler (spline) côté client — évite de faire tourner un solveur d'ODE dans le navigateur.

### 3.5 Rendu visuel de l'expansion

Deux effets superposés, tous deux pilotés par a(t) :

1. **Grille de fond visible** : lignes de repère qui se resserrent/étirent avec a(t), rendant l'expansion perceptible à l'œil (effet "élastique").
2. **Dilution de la densité de matière** : facteur 1/a³ appliqué au champ de densité (voir §4).
3. **Cercle de l'horizon observable** : rayon = χ(t) sur la grille comobile fixe, croissant du centre vers les bords de la carte à mesure que le temps avance.

### 3.6 Les trois sphères cosmologiques

Au-delà de l'horizon des particules (limite de ce qu'on peut voir, déjà traité en §3.4), deux autres sphères, distinctes et souvent confondues, sont à représenter :

**Sphère de Hubble** — distance à laquelle la vitesse de récession (due à l'expansion) égale c :
```
R_Hubble(t) = c / H(t)
```
Ce n'est pas un horizon : on peut voir au-delà. Son rayon comobile croît puis **décroît** une fois l'expansion accélérée (retournement vers z≈0,63, t≈7,7 Ga).

**Horizon des événements** — distance comobile maximale au-delà de laquelle un photon émis aujourd'hui ne nous atteindra jamais :
```
D_event(t) = a(t) · ∫ₜ^∞ c dt' / a(t')
```
Son rayon comobile décroît de façon monotone ; sa distance propre converge vers une valeur finie asymptotique (~17,5 Gal).

**Table de valeurs (paramètres Planck 2018), rayons comobiles — à utiliser directement pour le rayon des cercles sur la carte** :

| Époque | a(t) | z | Âge (Ga) | R_Hubble comobile (Mpc) | Horizon événements comobile (Mpc) | Horizon particules comobile (Mpc, réf. §3.4) |
|---|---|---|---|---|---|---|
| Recombinaison | 0,00091 | 1100 | 0,0004 | 208 | 18 974 | 278 |
| z=10 | 0,091 | 10 | 0,47 | 2 384 | 14 737 | 4 515 |
| z=3 | 0,25 | 3 | 2,14 | 3 895 | 11 613 | 7 639 |
| z=1 | 0,50 | 1 | 5,84 | 4 968 | 8 509 | 10 743 |
| **Retournement Hubble** | 0,613 | 0,63 | 7,69 | **5 064 (maximum)** | 7 485 | 11 767 |
| z=0,5 | 0,667 | 0,5 | 8,58 | 5 046 | 7 059 | 12 193 |
| **Aujourd'hui** | 1,0 | 0 | 13,79 | 4 448 | 5 108 | 14 144 |
| Futur (a=1,5) | 1,5 | -0,33 | 20,12 | 3 361 | 3 520 | 15 732 |
| Futur (a=2) | 2,0 | -0,5 | 24,95 | 2 613 | 2 663 | 16 589 |
| Futur (a=5) | 5,0 | -0,8 | 40,86 | 1 073 | 1 069 | 18 183 |

**Observation clé pour le rendu** : sur la grille comobile fixe, l'horizon des particules est le seul des trois cercles qui grandit sans cesse. La sphère de Hubble grandit puis se rétracte vers le centre après le retournement (il y a ~6 Ga). L'horizon des événements se rétracte vers le centre depuis le début de la simulation. Dans le futur lointain, Hubble et horizon des événements convergent presque vers la même taille (ils tendent asymptotiquement vers la même valeur en régime de Sitter pur).

**Ordre observé aujourd'hui** : Hubble (14,5 Gal propre) < horizon des événements (16,7 Gal propre) < horizon des particules (46,1 Gal propre). Cet ordre a varié dans le passé — utile comme repère pédagogique dans l'UI ("à cette époque, quelle sphère est la plus grande ?").

### 3.7 Contrôles UI dédiés aux trois sphères

- Trois cercles superposables indépendamment activables (cases à cocher / boutons toggle), chacun avec sa propre couleur et légende.
- Étiquette dynamique affichant le rayon propre actuel de chaque sphère active, mise à jour en continu avec le curseur temporel.
- Bouton « isoler » par sphère : ajuste automatiquement le zoom pour cadrer précisément la sphère sélectionnée à l'instant courant (voir §8, animations guidées).

---

## 4. Système de layers spatiaux (axe de zoom)

### 4.1 Découpage en 5 layers conceptuels, avec plages de validité en échelle comobile

| # | Layer | Échelle (Mpc comobile) | Échelle (années-lumière) | Nature de la structure |
|---|---|---|---|---|
| 1 | Local | 0 – 3 | 0 – 10 millions | Voie lactée, Groupe Local — positions réelles connues, pas de génération statistique |
| 2 | Amas de galaxies | 3 – 30 | 10 – 100 millions | Amas, fonction de corrélation croissante |
| 3 | Toile cosmique | 30 – 150 | 100 – 500 millions | Filaments, murs, vides ; distance caractéristique inter-superamas ~120-140 h⁻¹ Mpc |
| 4 | Transition vers l'homogénéité | 150 – 300 | 500 Ma – 1 Ga | Zone de fondu entre structure et uniformité ("End of Greatness" débattu entre 100 et 300 Mpc) |
| 5 | Univers homogène | 300 – 14 400 | 1 Ga – 47 Ga (rayon) | Densité uniforme extrapolée, conforme au principe cosmologique |

Ce découpage en 5 est conceptuel/scientifique. L'implémentation réelle compte davantage de layers techniques (cf. §0 et §4.6-4.7) : le layer 1 "Local" est en réalité 3 composants de rendu distincts (`milkyway`, `RealGalaxiesLayer`, `localgroup`), et les layers 2 à 5 comptent 10 paliers techniques (`l1b` → `l5`) plutôt que 4, pour une résolution apparente plus régulière au fondu.

### 4.2 Mécanisme de transition entre layers (zoom)

- Chaque layer/composant est un canvas indépendant, avec sa propre opacité pilotée par une fonction de poids partagée (`layerWeights.ts`) — un seul calcul, réutilisé par tous les composants de rendu, pour garantir qu'aucun ne se désynchronise des autres.
- Au passage d'une plage de validité à l'autre, un **fondu d'opacité** (crossfade) est appliqué entre le layer sortant et le layer entrant, sur une zone tampon.
- Le layer 1 (local) n'est pas généré comme un champ statistique — c'est une combinaison de positions réelles connues (Voie lactée + 8 galaxies nommées, cf. §4.6) et d'une texture procédurale légère pour le reste du Groupe Local (`localgroup`).

### 4.3 Génération de la matière — méthode retenue

**Champ gaussien aléatoire (GRF) contraint par le spectre de puissance cosmologique P(k), puis transformation log-normale.**

Pipeline :
1. Calcul de P(k) via une formule de transfert analytique (Eisenstein & Hu 1998, sans nécessiter de solveur de Boltzmann complet).
2. Tirage d'un champ gaussien 2D en espace de Fourier : amplitudes fixées par √P(k), phases aléatoires (mais **fixées une fois pour toutes** — voir §4.4).
3. Transformation inverse de Fourier (FFT2D) → champ réel.
4. Transformation log-normale pour garantir des densités positives et un bon accord avec les statistiques observées (fonction de corrélation, pic BAO ~150 Mpc) :

```
δ_lognormal(x) = exp( δ_gaussien(x) − σ²/2 ) − 1
```

**Point d'implémentation important** (cf. §0, point de vigilance) : cette transformation log-normale implique un `exp()` — toute contribution ajoutée au champ gaussien AVANT cette étape (par exemple l'ancrage du Groupe Local, §4.7) y est amplifiée exponentiellement, pas linéairement. Une amplitude modeste dans le champ brut peut dominer complètement l'export final.

### 4.4 Héritage entre layers (exigence initiale du projet)

**Principe : un seul champ gaussien de base par région, décliné en plusieurs résolutions par filtrage passe-bas successif — pas un champ indépendant par layer.**

- Layer 5 (homogène) → Layer 4 → Layer 3 → Layer 2 : chaque niveau ajoute des fréquences plus hautes (détails plus fins) au-dessus de la structure déjà présente au niveau parent, en réutilisant les mêmes phases aléatoires.
- Techniquement : filtres gaussiens/passe-bas à des coupures d'échelle croissantes (analogue aux filtres à 4, 2, 1 h⁻¹ Mpc utilisés en recherche pour visualiser la toile cosmique à plusieurs résolutions), soit encore une approche "multi-octaves" calée sur P(k) plutôt que sur un bruit arbitraire.
- Conséquence pratique : quand on zoome sur une région, le layer plus détaillé n'invente pas une nouvelle distribution — il **précise** celle déjà visible au zoom précédent.
- **Ce sens (grand → petit) est un principe physique, pas seulement un choix d'implémentation, et n'a pas vocation à être inversé** — cf. §4.7 pour la discussion complète et ce qui a été fait à la place pour intégrer les données réelles du Groupe Local.

### 4.5 Interaction zoom × temps

Le facteur de dilution 1/a³ (§3.3) s'applique **après** la génération spatiale du champ de densité — il est indépendant de l'échelle affichée. Le champ de densité de base est généré à z=0 (aujourd'hui) ; on le dilue ensuite dans le temps.

### 4.6 Rendu des galaxies réelles connues (Voie lactée + Groupe Local proche)

**Contexte** : contrairement aux layers `l1b`→`l5` (structure statistique, générée), les positions de la Voie lactée et des 8 galaxies réelles nommées du Groupe Local sont CONNUES (catalogue `generate_local_group_catalog.py`) et doivent rester identifiables visuellement (formes distinctes, pas de simple point) sur toute la plage de zoom où elles sont physiquement pertinentes.

**Méthode retenue : un sprite pré-cuit dédié par galaxie, composé au runtime.**

- Chaque galaxie (Voie lactée comprise) a sa PROPRE texture (256-320 px), générée hors-ligne à une résolution dimensionnée sur SA PROPRE taille angulaire — donc la même finesse relative pour toutes, quelle que soit leur distance réelle. Une texture partagée pour l'ensemble du Groupe Local a été essayée puis écartée : à l'échelle de 2,4-3,6 Mpc, chaque galaxie n'occupait que quelques pixels et perdait toute structure reconnaissable (bras spiraux, barre...).
- Chaque sprite combine un nuage d'étoiles net (positions générées selon la morphologie propre à la galaxie — spirale, barrée, irrégulière à aile tidale, elliptique étirée) ET un halo doux qui s'étend nettement au-delà de ce nuage, en s'estompant progressivement jusqu'au bord du sprite. Ce halo sert de transition visuelle vers le layer de densité procédural juste au-dessus (`l1b`) — sans lui, la rupture entre "une galaxie physique nette" et "un champ de densité flou" était trop brutale.
- Composés au runtime par `RealGalaxiesLayer.tsx` : position/taille recalculées à chaque zoom (`distanceMpc`/`angleDeg`/`radiusMpc` du catalogue → coordonnées écran), un `drawImage` par galaxie visible. Reste un rendu "en direct" par nécessité, mais léger (quelques appels, jamais un rendu étoile par étoile).
- La Voie lactée est un sprite parmi les autres (distance 0), avec son propre halo — délibérément plus resserré que celui des 8 galaxies réelles : la galaxie réelle la plus proche (Naine du Sagittaire, 0,024 Mpc) est trop proche pour tolérer un halo aussi large que les autres sans les recouvrir visuellement. Dessinée en premier (dessous) par précaution supplémentaire.
- Visible sur toute la plage combinée `milkyway` + `localgroup` (somme des deux poids de fondu), sauf la Voie lactée elle-même qui n'utilise que le poids `localgroup` seul (pour ne pas se superposer à la texture `milkyway`, plus détaillée, pendant le zoom rapproché).

### 4.7 Ancrage du Groupe Local sur les layers de densité proches — portée et limite volontaire

**Question posée en cours de projet** : puisque les positions réelles du Groupe Local sont connues (§4.6) et que `l1b` (le layer de densité le plus proche) est généré statistiquement, ne devrait-on pas faire remonter cette connaissance réelle VERS les layers plus grands, plutôt que de laisser `l1b` ignorer superbement les 98 galaxies visibles juste en dessous ?

**Ce qui n'a PAS été fait, et pourquoi** : inverser le sens de génération du champ aléatoire lui-même (faire de `l1b` la racine et remonter vers `l5`) contredirait le principe cosmologique (§4.1, ligne 5) : à grande échelle (300+ Mpc), l'univers est statistiquement homogène et rien ne distingue notre position — construire les grandes échelles à partir d'une région locale connue introduirait un artefact scientifiquement faux (un point spécial fixe au centre de la carte, visible même là où aucun point de l'univers n'est censé se distinguer). Le sens grand → petit du champ aléatoire (§4.4) reste donc inchangé.

**Ce qui a été fait à la place** : une contrainte LOCALE, additionnelle et bornée, superposée au champ statistique existant — sans changer son sens de génération.

- `l1b` (8,49 Mpc) : ancrage complet sur les 98 galaxies du catalogue (8 réelles + ~90 procédurales de champ, cf. `generate_local_group_catalog.py`). Fonction `apply_local_group_anchor()` dans `generate_layers.py` : chaque position reçoit un halo doux + un pic, dimensionnés pour rester visibles (jamais sub-pixel, quelle que soit la résolution du layer) et pour se fondre dans la texture plutôt que de créer des ronds nets isolés (calibré visuellement via `l1b-anchor-test.html`, §0).
- `l2` (30 Mpc) et `l2b` (67,08 Mpc) : la même contrainte, mais en TRACE fortement atténuée (paramètre `strength`, 0,4 puis 0,15) — juste assez pour que les positions ne disparaissent pas net à chaque frontière de zoom, pas pour les rendre identifiables individuellement.
- **Arrêt volontaire à `l2b`** : au-delà (`l3`, 150 Mpc, et tous les layers suivants), aucun ancrage — le Groupe Local redevient statistiquement invisible, comme n'importe quelle autre région à cette échelle. C'est le comportement scientifiquement correct, pas une limitation technique à lever plus tard.

**Paramètres de `apply_local_group_anchor()`** (cf. docstring de la fonction pour le détail) : `strength` (intensité globale de l'ancrage), `global_suppression` (atténuation du bruit ambiant existant, pour laisser ressortir les positions ancrées), `size_multiplier` (taille des pics, en multiple de la résolution du layer), `bump_amplitude_factor` (luminosité des pics), `extra_blur_px` (flou d'ensemble — à utiliser avec prudence, cf. §0 sur le piège du transform `exp()`), `diffuse` (désactive le mécanisme "pic garanti dominant + suppression locale du bruit" au profit d'un simple ajout par-dessus le champ existant, pour un rendu moins "rond et net"), `real_only` (limite le traitement complet aux 8 galaxies nommées si `True` ; `False` sur `l1b`/`l2`/`l2b` pour couvrir les 98).

---

## 5. Architecture technique (proposition initiale)

### 5.1 Séparation des responsabilités

| Composant | Rôle | Calcul |
|---|---|---|
| Générateur de champs (offline) | Pré-calcule les champs gaussiens/log-normaux pour chaque layer, à une résolution fixe, sérialisés en textures | Script Python/Node, exécuté une fois, pas en temps réel |
| Table cosmologique (offline) | Pré-calcule a(t), χ(t) sur ~200-500 points | Script Python (scipy.integrate) |
| Moteur de rendu (client) | Interpole a(t)/χ(t), applique la dilution de densité, gère le fondu entre layers, dessine la grille et le cercle d'horizon | WebGL/Canvas (ou React + shaders) |
| Contrôles UI | Deux curseurs (zoom, temps) synchronisés avec le moteur de rendu | React |

### 5.2 Format des données précalculées

- Champs de densité : textures (PNG 16 bits ou format flottant type EXR/raw), une par layer, résolution à définir selon performance cible.
- Table cosmologique : JSON `{ t, a, chi_comobile }` avec interpolation spline côté client.

### 5.3 Pourquoi précalculer plutôt que générer en temps réel

- Les FFT2D à haute résolution et l'intégration de Friedmann sont coûteuses ; elles n'ont pas besoin d'être recalculées à chaque frame.
- Seuls les paramètres dérivés du temps (opacités, facteur de dilution, rayon du cercle) doivent être recalculés en continu — ce sont des opérations légères (interpolation, multiplication scalaire).

---

## 6. Points ouverts / décisions à prendre en phase de prototypage

1. **Résolution des textures de densité** par layer (compromis qualité visuelle / poids de téléchargement).
2. **Nombre exact de points de la zone tampon de transition** entre layers (largeur du fondu).
3. **Choix du moteur de rendu** : Canvas 2D (plus simple) vs WebGL/shaders (plus performant pour les transitions temps réel et les effets de grille).
4. **Niveau de détail du Layer 1 (local)** : faut-il un vrai catalogue de positions du Groupe Local, ou une représentation stylisée ?
5. **Légendes/échelles affichées** : afficher la distance comobile, la distance propre actuelle, ou les deux simultanément à l'écran ?

---

## 7. Représentation du déplacement de la lumière et séquences d'animation

Objectif : rendre perceptibles, par le mouvement, les trois sphères et la distinction entre "vitesse de la lumière" et "vitesse d'éloignement dû à l'expansion" — une distinction qui reste abstraite tant qu'elle n'est montrée qu'à travers des formules ou des cercles statiques.

### 7.1 Traceur de rayon lumineux (cône de lumière passé)

- L'utilisateur clique un point de la carte (une galaxie, un emplacement quelconque) à une époque donnée.
- Le rayon lumineux émis vers nous à ce moment est tracé comme un point qui se déplace vers le centre, avec le temps qui avance sur le curseur.
- Le déplacement du photon suit `ds = c·dt / a(t)` en coordonnées comobiles : le photon avance plus vite en distance comobile quand a(t) est petit (univers jeune), puis ralentit en comobile à mesure que a(t) grandit.
- Effet pédagogique recherché : montrer que le trajet du photon vers nous n'est pas une ligne droite à vitesse comobile constante — il illustre concrètement l'intégrale qui définit l'horizon des particules (§3.4).
- Variante : proposer un point "aux limites de l'horizon des particules actuel" pré-sélectionné, dont le rayon retrace exactement 13,8 milliards d'années de trajet jusqu'à nous, timé sur le curseur.

### 7.2 Traceur de cône de lumière futur (horizon des événements)

- Même principe que 8.1 mais projeté vers l'avenir : on choisit un point aujourd'hui et on anime la propagation d'un photon émis maintenant vers l'extérieur.
- Si le point choisi est en-deçà de l'horizon des événements actuel, le photon continue de s'éloigner en distance comobile indéfiniment (jamais de convergence) — visuellement, on voit le point lumineux ralentir sa progression comobile sans jamais s'arrêter tout à fait, illustrant que "s'éloigner indéfiniment sans jamais atteindre une limite" correspond à "être dans notre cône de causalité futur".
- Si le point choisi est au-delà, le photon **n'avance plus du tout en coordonnées comobiles au-delà d'un certain point** — utile pour matérialiser concrètement ce que signifie "cette région ne recevra jamais notre lumière".

### 7.3 Galaxie traceur franchissant les sphères

- Placer un marqueur fixe en coordonnées comobiles (une galaxie choisie par l'utilisateur ou une galaxie repère prédéfinie, par exemple à 5 Gpc comobile).
- En faisant défiler le curseur temporel, le marqueur change d'état visuel selon sa position relative aux trois sphères à cet instant (à l'intérieur / à l'extérieur de chacune), par exemple via un code couleur ou une icône qui change.
- Effet recherché : rendre concret le fait qu'une même galaxie peut être visible mais en récession superluminale (hors sphère de Hubble, dans horizon des particules), ou destinée à ne jamais nous envoyer de nouvelle lumière (hors horizon des événements).
- Un effet de "décalage vers le rouge croissant puis quasi-figement" (analogie avec la chute dans un trou noir) peut accompagner le franchissement de l'horizon des événements par un objet qui s'en approche.

### 7.4 Time-lapse automatique (lecture continue)

- Bouton "lecture" qui anime automatiquement le curseur temporel de la recombinaison à aujourd'hui (et au-delà, en mode prospectif, si souhaité).
- Vitesse réglable, avec pause automatique aux instants clés déjà identifiés dans les tables (retournement de la sphère de Hubble, équivalence matière/énergie noire, etc.).

### 7.5 Zoom guidé — "suivre une sphère"

- Bouton "isoler"/"suivre" par sphère (mentionné en §3.7) : ajuste automatiquement le niveau de zoom en continu pendant la lecture du time-lapse, pour garder la sphère choisie visible en permanence à une taille constante à l'écran.
- Particulièrement utile pour la sphère de Hubble (dont le comportement croissant-puis-décroissant est sinon difficile à suivre visuellement si le zoom reste fixe).

### 7.6 Visualisation explicite "vitesse de la lumière vs vitesse d'expansion"

- Superposer, à un point donné de la carte, un repère mobile représentant "ce qu'un photon aurait parcouru en un temps donné à vitesse comobile constante" à côté du repère réel (qui suit `ds = c dt/a(t)`).
- Permet de visualiser directement l'écart entre les deux, et donc pourquoi certaines régions sont en récession superluminale sans que rien ne dépasse localement la vitesse de la lumière.

### 7.7 Priorisation suggérée pour un premier prototype

1. Time-lapse automatique (8.4) — base indispensable, réutilise directement les tables déjà définies (§3.4, §3.6).
2. Galaxie(s) traceur(s) franchissant les sphères (8.3) — fort impact pédagogique, complexité modérée.
3. Traceur de cône de lumière passé (8.1) — cœur scientifique du projet, complexité plus élevée (nécessite le calcul d'intégrale par point cliqué).
4. Zoom guidé (8.5) et cône futur (8.2) — raffinements à ajouter une fois le socle validé.

---

## 9. Proposition retenue — distension spatiale réelle en fonction du temps

**Statut : validé en discussion, pas encore implémenté (en attente d'un correctif de netteté au moment de la rédaction).**

### 9.1 Le problème

Le système de coordonnées comobiles fixes (§2) était un choix délibéré : un point ne bouge jamais à l'écran, seule sa luminosité change avec le temps (dilution ×1/a³, §3.3). Ce choix reste valide pour l'objectif initial, mais une demande complémentaire est apparue : **voir l'espace se comprimer visuellement** en remontant vers le Big Bang, pas seulement s'assombrir/s'illuminer sur place. Autrement dit, passer d'un rendu "en distance comobile" à un rendu "en distance physique réelle" (proper distance), qui elle se contracte authentiquement avec a(t).

Précision importante actée en discussion : cet effet est **indépendant** de la question de la croissance des structures (formation hiérarchique bottom-up, §7 — non traitée ici, mise de côté pour l'instant). Il s'agit uniquement de la distension métrique de l'espace, pas de l'évolution du contraste des structures.

### 9.2 Principe d'implémentation

Un seul point de conversion centralisé est utilisé par tous les composants de rendu (grille, textures de densité, Voie lactée, Groupe Local, cercle d'horizon) :

```
pxPerMpc_actuel  = écran / (2 × halfWidthMpc)
pxPerMpc_nouveau = écran / (2 × halfWidthMpc / a(t))
```

En divisant le champ de vue comobile par `a(t)`, on affiche mécaniquement une zone comobile plus grande dans le même espace écran quand `a(t) < 1` (passé) — ce qui fait rétrécir visuellement tout ce qui est fixe en comobile vers le centre. À `a(t) = 1` (aujourd'hui), aucune distorsion : le rendu est identique à l'existant. La distorsion n'apparaît qu'en remontant le temps.

**Pourquoi une seule formule suffit** : parce que tous les composants (DensityLayer, MilkyWayLayer, LocalGroupLayer, la grille et le cercle d'horizon dans UniverseMap) dérivent déjà leur échelle px/Mpc d'un seul et même calcul. Modifier ce calcul centralement propage l'effet partout sans toucher au reste du code de chaque composant.

### 9.3 Complémentarité avec la dilution de densité

Cet effet de compression spatiale et la dilution de densité (1/a³, déjà implémentée) sont **complémentaires, pas redondants** :
- La compression fait rétrécir l'espace visuellement (effet géométrique).
- La dilution fait que ce qui reste visible est plus dense/lumineux (effet de densité).

Combinés, ils donnent l'impression d'un univers qui se comprime ET s'embrase en remontant vers le Big Bang — cohérent avec l'intuition physique de départ du projet (cf. §1 et les tout premiers échanges de cadrage).

### 9.4 Points à vérifier à l'implémentation

- Vérifier que le cercle de l'horizon des particules (déjà dynamique, §3.4) reste cohérent visuellement avec cette compression additionnelle — les deux évoluent avec le temps mais via des mécanismes distincts (l'horizon via son propre calcul physique, ce nouvel effet via la conversion px/Mpc).
- Vérifier le comportement aux limites (a(t) très petit, proche de la recombinaison) : la formule doit rester stable numériquement.
- Décider si l'effet doit s'appliquer de façon identique à tous les layers ou si certains éléments (par ex. les étiquettes de texte, si réintroduites) doivent rester lisibles indépendamment de la compression.

---

## 11. Cohérence spatio-temporelle — matrice unifiée zoom × temps

**Statut : conception validée en discussion (8 juillet), partiellement prototypée (voir liste des prototypes en fin de section), pas encore intégrée en production.**

### 11.1 Le problème que cette section résout

Le §9 traite la distension spatiale (le "dézoom" en remontant le temps) comme un effet géométrique isolé. En pratique, remonter le temps doit faire évoluer **quatre choses à la fois**, et ces quatre choses doivent rester cohérentes entre elles ET entre layers de zoom adjacents à tout instant t — sans quoi on obtient soit une rupture visuelle en changeant de zoom à temps fixé, soit une rupture en changeant le temps à zoom fixé :

1. **La position** (compression spatiale, §9) — uniquement pertinente à partir de l'échelle où le flux de Hubble domine.
2. **La forme des structures** (nettes → filamenteuses → uniformes) — pas un flou géométrique, une réduction d'amplitude AVANT la transformation log-normale qui crée les pics (cf. §11.3).
3. **La luminosité moyenne du fond** — doit être la MÊME à tout instant t, quel que soit le layer regardé.
4. **Le moment où chaque échelle commence à se dissoudre** — pas le même pour toutes : une galaxie et un amas de galaxies ne se sont pas formés à la même époque cosmique.

### 11.2 Pourquoi le flou géométrique a été écarté (rappel)

Essayé et rejeté sur les sprites (6-8 juillet) : un flou gaussien appliqué après coup donne des taches rondes lisses, jamais des filaments, et détruit la texture fine sans repasser par un état "toile cosmique" intermédiaire crédible. Solution retenue à la place : réduire l'amplitude du champ AVANT la transformation qui crée les pics de densité :

```
field_to_log_density(champ) = log10( exp(champ − var(champ)/2) + 0.05 )
```

Cette transformation exponentielle est ce qui **crée** les pics à partir d'un champ par ailleurs plat. En réduisant l'amplitude du champ gaussien source (pas en floutant le résultat), le squelette filamenteux (déterminé par la PHASE du champ, inchangée) reste identique, mais les pics s'écrasent progressivement — un vrai état "toile cosmique diffuse" existe entre "aujourd'hui" et "uniforme", pas juste une interpolation géométrique. Vérifié numériquement sur `l2` (écart-type du champ normalisé : 0,200 à amplitude 1 → 0,004 à amplitude 0,02, moyenne stable ~0,4-0,5 tout du long — convergence vers un gris plat, pas vers du noir ou du blanc).

### 11.3 Les fonctions centrales (une seule définition, réutilisée partout)

**a) Époque de formation par échelle — `a_form(s)`**

Ancrée dans la recherche (8 juillet) : les galaxies sont des structures ANCIENNES (déjà à moitié assemblées vers z≈2,5-5), les amas de galaxies sont des structures JEUNES (se forment entre z≈1 et aujourd'hui). En remontant le temps, les grandes échelles doivent donc se dissoudre BIEN AVANT les petites, pas en même temps.

| Groupe de layers | Échelle (Mpc) | z de formation | a_form | Source |
|---|---|---|---|---|
| Sprites (Voie lactée + 8 galaxies réelles) | 0,01 – 0,05 | 2,5 – 5 | **≈ 0,20** | Demi-masse assemblée à ces z (recherche 8 juillet) |
| `localgroup` (procédurales) | jusqu'à 2,4 | 2,5 – 5 (mêmes objets, échelle galaxie) | **≈ 0,20** | idem |
| `l1b` / `l2` / `l2b` | 8,49 – 67 | 0 – 1 | **≈ 0,65** | Formation des amas (recherche 8 juillet) |
| `l3` / `l3b` / `l4` / `l4a` / `l4b` | 150 – 2100 | ~0 (encore en formation) | **≈ 0,92** | Toile cosmique, encore jeune aujourd'hui |
| `l5a` / `l5` | 5531 – 14570 | — (toujours quasi homogène) | **≈ 1,0** | Aucune dissolution significative à faire |

**b) Amplitude de structure — `A(s, a)`**

Fonction en S (smoothstep), centrée sur `a_form(s)`, dans l'espace `log10(a)` (pas `a` linéaire — cf. §9, les ordres de grandeur sont trop étalés) :

```
x(s, a)  = log10(a) − log10(a_form(s))
t(s, a)  = clamp( (x + demi_largeur) / (2 × demi_largeur), 0, 1 )
A(s, a)  = t² × (3 − 2t)                    [smoothstep]
```

`demi_largeur` (en dex) contrôle la douceur de la transition — valeur de départ proposée : 0,6 dex, à calibrer visuellement comme le reste. `A = 1` pour `a` très supérieur à `a_form(s)` (structures pleinement formées, rendu actuel inchangé) ; `A → 0` pour `a` très inférieur à `a_form(s)` (dissolution complète).

**Utilisation de `A(s,a)` selon le type de layer :**
- Layers de densité (`l1b` → `l5`) : multiplie le champ gaussien source avant `field_to_log_density` (§11.2).
- Sprites : pilote à la fois la croissance du halo par étoile, l'intensité du flou de fusion et de la texture filamenteuse (paramètres validés le 8 juillet : `pointSize=0,5`, `haloGrowth=8,5×`, `blurMax=6px`, `filamentAmount≈0,8`, cf. `scripts/generate_dissolution_sprites.mjs`) — tous mis à l'échelle par `(1 − A(s,a))`.
- Ancrage forcé du Groupe Local sur `l1b`/`l2`/`l2b` (`apply_local_group_anchor`, §4.7) : le paramètre `strength` existant doit désormais aussi être multiplié par `A(s_local, a)` où `s_local` est l'échelle DES GALAXIES (≈0,03 Mpc, donc `a_form≈0,20`) — pas celle du layer qui accueille l'ancrage. L'ancrage doit rester net tant que les galaxies elles-mêmes sont formées, et se dissoudre avec elles, pas avec l'amas qui les héberge.

**c) Couleur de convergence partagée — `universeGlowColor(a)`**

UNE seule fonction, indépendante de l'échelle, utilisée par tous les layers et tous les sprites (validée le 8 juillet) :

```
t_glow(a) = clamp(1 − a, 0, 1) ^ 2.2
couleur(a) = lerp( [5, 5, 10],        // #05050a, fond actuel de l'app (UniverseMap.tsx)
                    [255, 243, 214],   // #fff3d6, teinte la plus claire de la palette Astro (colormaps.ts)
                    t_glow(a) )
```

À `A(s,a) → 0` (structure dissoute), la couleur affichée DOIT tendre vers `universeGlowColor(a)` — c'est le point de cohérence entre tous les layers à un instant t donné : quelle que soit l'échelle regardée, une fois dissoute elle affiche la même couleur.

**d) Fond résiduel sur les layers à sprites (même à a=1, aujourd'hui)**

Point soulevé le 8 juillet : `milkyway`/`RealGalaxiesLayer` ont aujourd'hui un fond parfaitement noir autour des sprites, contrairement aux layers de densité qui ont une texture partout — risque de rupture de luminosité moyenne au moment de la convergence. Correctif à appliquer : ajouter en permanence (indépendant de `A(s,a)`) un plancher de texture filamenteuse à très faible amplitude (`residualAmplitude`, valeur à calibrer, probablement < 0,05) sur les layers à sprites, générée par le MÊME mécanisme que §11.2 — pas une texture inventée séparément.

**e) Compression spatiale (rappel §9, bornée par la physique — §4.7)**

```
effectiveHalfWidthMpc(s, a) = halfWidthMpc / a(t)     si s ≳ 15-30 Mpc (flux de Hubble dominant)
effectiveHalfWidthMpc(s, a) = halfWidthMpc            si s ≲ 2 Mpc (Groupe Local, lié gravitationnellement)
```

Zone de transition entre les deux (≈2-15 Mpc, `l1b`) : à traiter avec le même type de fondu en S que `A(s,a)`, pas une coupure nette.

### 11.4 Matrice récapitulative

| Layer | Échelle (Mpc) | a_form | Compression (§9) | Ancrage forcé (§4.7) | Sprites individuels |
|---|---|---|---|---|---|
| `milkyway` + `RealGalaxiesLayer` | 0 – 2,4 | 0,20 | Non | — | Oui (9 sprites) |
| `localgroup` (procédurales) | jusqu'à 2,4 | 0,20 | Non | — | Non (texture partagée) |
| `l1b` | 8,49 | 0,65 | Transition douce | Plein (×A(0,20,a)) | Non |
| `l2` | 30 | 0,65 | Oui | Trace (×0,4×A(0,20,a)) | Non |
| `l2b` | 67 | 0,70 | Oui | Trace atténuée (×0,15×A(0,20,a)) | Non |
| `l3` → `l4b` | 150 – 2100 | 0,92 | Oui | Aucun | Non |
| `l5a` / `l5` | 5531 – 14570 | 1,0 | Oui | Aucun | Non |

Toutes les lignes convergent vers `universeGlowColor(a)` (§11.3.c) à `A(s,a) → 0`, quelle que soit l'échelle — c'est la garantie de cohérence demandée.

### 11.5 Prototypes déjà réalisés (validation partielle de cette conception)

- `app/public/time-axis-test.html` : compression spatiale + dissolution sur 3 échelles (`l5`/`l2`/Voie lactée) — première version, remplacée par les suivantes.
- `app/public/time-axis-milkyway-test.html` puis `time-axis-milkyway-nbody-test.html` : dissolution physique de la Voie lactée (séquence ELS 1962 inversée, puis vrai moteur N-corps Barnes-Hut).
- `app/public/time-axis-sprites-test.html` : généralisation aux 9 sprites + `universeGlowColor(a)`.
- `app/public/time-axis-fullscene-test.html` : les 9 sprites composés ensemble, animation Big Bang → aujourd'hui.
- `scripts/simulate_dissolution.mjs` + `scripts/generate_dissolution_sprites.mjs` : simulation N-corps et cuisson des sprites de dissolution (126 fichiers, niveaux de gris uniquement — couleur/convergence appliquées au runtime, cf. §11.3.c).
- Aperçus comparatifs (non versionnés, livrés dans la conversation) : balayage d'amplitude sur le champ brut de `l2` avant `field_to_log_density`, validant §11.2/11.3.b.

**Pas encore fait** : `a_form(s)` et `A(s,a)` ne sont pas encore implémentés comme fonctions partagées (actuellement chaque prototype a sa propre courbe ad hoc) ; le fond résiduel (§11.3.d) n'est pas implémenté ; l'ancrage forcé (§11.3.e) n'est pas encore modulé par le temps ; aucune intégration en production (tout reste dans des prototypes `app/public/*-test.html` séparés de l'app réelle).

---

## 12. Résumé des formules clés (aide-mémoire)

```
Facteur d'échelle :        a(t) = (Ωm/ΩΛ)^(1/3) · sinh²ᐟ³( (3/2)√ΩΛ H0 t )
Dilution de densité :      ρ(t) = ρ₀ / a(t)³
Horizon des particules :   χ_part(t) = ∫₀ᵗ c dt' / a(t')
Sphère de Hubble :         R_Hubble(t) = c / H(t)
Horizon des événements :   D_event(t) = a(t) · ∫ₜ^∞ c dt' / a(t')
Distance propre à t :      d_propre(t) = a(t) · d_comobile
Champ log-normal :         δ_LN(x) = exp(δ_G(x) − σ²/2) − 1
Compression spatiale :     effectiveHalfWidthMpc = halfWidthMpc / a(t)   [si échelle ≳ 15-30 Mpc, §4.7]
Amplitude de structure :   A(s,a) = smoothstep( (log10(a) − log10(a_form(s)) + w) / 2w )   [§11.3.b]
Couleur de convergence :   universeGlowColor(a) = lerp(#05050a, #fff3d6, (1−a)^2.2)          [§11.3.c]
```

Paramètres : H0 = 67,4 km/s/Mpc, Ωm = 0,315, ΩΛ = 0,685, Ωr = 9,24×10⁻⁵ (Planck 2018).

---

## 13. Processus de développement et de validation (travail génératif/visuel)

**Contexte** : établi le 9 juillet après un bug de saturation critique (sprites de dissolution complètement cramés) qui a survécu à une "correction" présentée comme validée — la vérification ne portait que sur des courbes de paramètres d'entrée, jamais sur le rendu final réellement calculé. Le bug n'a été trouvé qu'après un second retour visuel de l'utilisateur.

### 13.1 Principe

**Ne jamais présenter un résultat visuel/génératif comme corrigé sur la seule base d'une relecture de code ou d'une vérification des courbes de paramètres.** Calculer et inspecter le résultat RÉELLEMENT rendu, avec des vérifications numériques objectives, avant de demander une confirmation visuelle. Le retour visuel de l'utilisateur doit être une confirmation finale — pas la méthode de détection de bug.

Ce n'est pas un système à agents multiples en parallèle (pas d'outil de ce type disponible) — c'est une discipline à appliquer systématiquement à chaque tâche générative, en une seule passe mais rigoureuse.

### 13.2 Méthode

Pour toute modification touchant un rendu visuel (courbe de temps, texture générée, sprite, palette de couleur...) :

1. **Construire ou réutiliser un script headless** qui réplique EXACTEMENT les calculs du code réel (pas une approximation) — Python (numpy/scipy/PIL) dans cet environnement, `node-canvas` n'étant pas installable (dépendances natives absentes). Un script par mécanisme, dans `scripts/dev/`, maintenu à jour en même temps que le code qu'il valide.
2. **Calculer le résultat sur toute la plage pertinente** (plusieurs valeurs du paramètre qui varie), pas un seul point.
3. **Vérifier objectivement, par le calcul** :
   - **Saturation** : fraction de pixels proches du minimum/maximum (ex. `>240` ou `<8` sur 255) — un taux élevé signale un possible écrasement de la texture/du signal.
   - **Continuité** : pas de saut brutal de moyenne/écart-type entre deux échantillons voisins du paramètre qui varie.
   - **Contraste interne dans les zones d'intérêt** : isoler spécifiquement une zone (ex. un sprite) et mesurer sa variation interne — une moyenne globale saine peut masquer une zone locale totalement plate ou totalement saturée (piège rencontré le 9 juillet : la saturation d'un sprite était invisible dans les statistiques globales de la scène, noyée par le reste de l'image).
   - **Conditions aux limites** : la valeur au point de référence actuel (ex. a=1, "aujourd'hui") doit être identique au rendu de production déjà calibré ; les points de convergence documentés (§11.3.c) doivent être effectivement atteints.
4. **Ne déployer et demander un retour visuel qu'après que ces vérifications passent.**

### 13.3 Défauts déjà rencontrés à vérifier systématiquement (liste vivante)

- Un facteur d'atténuation "cosmétique" (ex. `1/√x`) qui semble réduire une valeur mais reste très insuffisant face à une accumulation (ex. des milliers de particules superposées) — toujours vérifier l'ordre de grandeur RÉEL du pic, pas seulement le sens de variation.
- Une modulation multiplicative (ex. bruit filamenteux) appliquée à un signal déjà saturé : elle ne peut rien montrer une fois la valeur de base à son maximum — l'ordre des opérations compte (lever la saturation AVANT d'espérer voir une texture).
- Une fenêtre de transition étroite juste avant une borne (ex. juste avant la recombinaison) : peut créer un creux ou un saut au lieu d'un fondu — préférer réutiliser une courbe déjà lisse existante plutôt que d'en construire une nouvelle isolée.
- Une normalisation recalculée indépendamment à chaque échantillon (ex. percentiles par image) : peut annuler artificiellement l'effet qu'on cherche à observer — figer la normalisation une fois, la réutiliser pour tous les échantillons comparés.

### 13.4 Rappel — ce que Claude ne peut pas faire

Pas de mode "plusieurs agents Claude en parallèle" pour développer/tester/valider séparément. Un seul thread d'exécution, dans l'ordre. Pas de modification directe du prompt système (fixé par Anthropic/la configuration du projet) — un rappel du principe ci-dessus peut être ajouté aux instructions personnalisées du projet par l'utilisateur, et/ou à la mémoire persistante de ce projet (déjà fait le 9 juillet).
