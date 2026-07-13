# Matrice de paramètres zoom × temps — document de référence versionnable

*Créé le 13 juillet 2026 — répond au §11.6 du document d'architecture
(`docs/architecture-univers-observable.md`) : « documenter cette matrice
avant de produire le moindre visuel ».*

## 1. Source de vérité et flux d'ajustement

La matrice canonique est **`app/public/data/spacetime_matrix.json`** —
éditable à la main, versionnée avec le reste du dépôt, et consommée telle
quelle par la génération ET l'affichage (aucun paramètre redéfini ailleurs) :

```
spacetime_matrix.json  ──lu par──▶  scripts/generate_spacetime_frames.py   (cuit les 114 frames st_*.png)
                       ──lu par──▶  scripts/dev/spacetime_pipeline.py       (pipeline headless partagé)
                       ──lu par──▶  scripts/dev/validate_spacetime_matrix.py (validation §13, 119 contrôles)
                       ──lu par──▶  app/public/spacetime-matrix-test.html    (prototype 2 curseurs)
```

**Flux d'ajustement d'un paramètre** :
1. Éditer `spacetime_matrix.json` (jamais les scripts).
2. `cd scripts && python3 generate_spacetime_frames.py` (recuit les frames,
   réécrit le champ `computed` — normalisation figée + tons mesurés).
3. `cd dev && python3 validate_spacetime_matrix.py` (doit afficher
   « TOUTES LES VÉRIFICATIONS PASSENT » avant tout retour visuel, §13).
4. Optionnel mais recommandé après toute modification du prototype :
   `python3 xcheck_dump_ref.py && node xcheck_prototype.mjs` (contrôle
   croisé : le JS du prototype doit reproduire le pipeline Python à ~1e-6).
5. Ouvrir `spacetime-matrix-test.html` pour la confirmation visuelle finale.

`scripts/generate_spacetime_matrix.py` ne sert qu'à reconstruire le JSON
depuis zéro — **le relancer écrase les ajustements manuels**.

## 2. Les deux axes

- **Temps** : `a ∈ [1/1101, 1]` (recombinaison → aujourd'hui, §3), curseur
  en `log10(a) ∈ [−3.0417, 0]`.
- **Zoom** : demi-champ demandé `∈ [0.02, 14570]` Mpc comobiles
  (bornes de `UniverseMap.tsx`). Le demi-champ EFFECTIF appliqué au rendu
  inclut la compression spatiale (§4 ci-dessous).

## 3. Colonnes de la matrice, par layer (provenance de chaque valeur)

| Champ | Sens | Provenance |
|---|---|---|
| `max_mpc`, `seed`, `parent`, `margin_factor` | Identiques à la production | `scripts/generate_layers.py` LAYER_SPECS — ne jamais diverger |
| `a_form` | Époque de formation de l'échelle | Points de contrôle §11.4.a (recherche du 8 juillet), interpolés en log(s) |
| `halfwidth_dex`, `center_dex` | Fenêtre de dissolution de `A(s,a)` | §11.4.b + **correctif de continuité du 13 juillet** (cf. §6 ci-dessous) |
| `dissolution_window_a` | `[a_form_effectif², 1]` — bornes où `A` passe de 0 à 1 | Dérivé des deux champs précédents |
| `keyframes_a` | Valeurs de `a` des frames cuites (log-uniformes dans la fenêtre ; queue étendue jusqu'à a=0.04 pour les layers ancrés) | Ce document |
| `anchor_a1` | Paramètres d'ancrage Groupe Local à a=1 | Copie exacte de `generate_layers.py` (itérations des 6-7 juillet) |
| `anchor_scale_mpc` | Échelle pilotant la dissolution de l'ancrage (0.03 Mpc = galaxies) | §11.4.b : « l'ancrage se dissout avec elles » |
| `compression` | Compression 1/a active (flux de Hubble) ou non (système lié) | §11.4.e |
| `residual_bg` (localgroup) | Fond FFT résiduel : amplitude 0.35, seed 31415, VMAX 4.074, cible 8.95/255 | §4.8 (calibré le 10 juillet) — intégré ici, seule différence volontaire à a=1 (§11.7) |
| `uniform_floor` (localgroup) | Convergence vers le ton dissous des layers GRF (129.4/255) | §11.1 point 3 (cohérence de luminosité moyenne) — cf. §7 ci-dessous |

Paramètres globaux : `embrasement` (exp 5, offset 18, ×6, échelle 0.03 —
§11.4.c, calibré le 10 juillet, inchangé), `compression` (fondu en S entre
2 et 15 Mpc — §4.7/§11.4.e), `sprites` (croissance 1.2, amplitude 0.0025 —
correctifs du 10 juillet), `zoom_axis` (frontières/fondus copiés de
`app/src/layerWeights.ts`).

## 4. Modulations temporelles appliquées à la génération

Pour un layer GRF à l'instant `a` (cf. `generate_spacetime_frames.py`) :

```
champ(a) = ancrage_modulé( champ_base_production × A(s_layer, a),  A_gal(a) )
log_d    = field_to_log_density(champ(a))                      [§11.2 — amplitude AVANT la transformation]
export   = clip((log_d − vmin) / (vmax − vmin))                [vmin/vmax FIGÉS, partagés, §13.3]
```

où `ancrage_modulé` multiplie par `A_gal(a)` : `strength` (donc toutes les
bosses additives ET la profondeur de suppression locale, qui en dépendent
linéairement) et relâche `global_suppression` vers 1
(`gs(a) = 1 − (1−0.35)·A_gal`). À `a=1` : appel strictement identique à la
production (vérifié frame par frame, diff max 0.75/255 = quantification).

Nuance assumée : la « trace » d'ancrage héritée par `l1b` À TRAVERS le champ
parent `l2` (héritage passe-bas de production) est modulée par `A(s_l1b,a)`
et non `A_gal(a)` — effet de second ordre (composante lissée, faible
amplitude), documenté ici pour ne pas être redécouvert.

La compression spatiale n'est PAS cuite : la grille comobile est figée (§2),
la fenêtre d'échantillonnage à l'affichage s'élargit en `hw/a` (pondérée par
`compressionStrength`), et la sélection de layers se fait sur ce demi-champ
effectif — les fondus de zoom existants absorbent naturellement le
changement d'échelle.

## 5. Table évaluée (générée depuis les frames cuites — à régénérer après tout ajustement)

Chaque cellule : `A(s_layer, a)` · moyenne exportée de la frame (/255).
`A_gal` pilote ancrages, sprites et embrasement.

| Layer (s Mpc) | a=1 | a=0.9 | a=0.7 | a=0.5 | a=0.3 | a=0.15 | a=0.05 | a=0.01 | a=0.000908 |
|---|---|---|---|---|---|---|---|---|---|
| **l5** (14570) | A=1.00 · 105 | A=0.56 · 121 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l5a** (5531.46) | A=1.00 · 105 | A=0.56 · 121 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l4b** (2100) | A=1.00 · 105 | A=0.56 · 121 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l4a** (793.73) | A=1.00 · 105 | A=0.56 · 121 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l4** (300) | A=1.00 · 103 | A=0.56 · 120 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l3b** (212.13) | A=1.00 · 102 | A=0.56 · 120 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l3** (150) | A=1.00 · 108 | A=0.56 · 123 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l2b** (67.08) | A=1.00 · 112 | A=0.94 · 115 | A=0.50 · 127 | A=0.00 · 130 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l2** (30) | A=1.00 · 105 | A=0.96 · 107 | A=0.63 · 120 | A=0.10 · 129 | A=0.00 · 130 | A=0.00 · 130 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **l1b** (8.49) | A=1.00 · 127 | A=0.98 · 127 | A=0.79 · 128 | A=0.38 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 | A=0.00 · 129 |
| **localgroup** (2.4) | A=1.00 · 9 | A=1.00 · 9 | A=0.97 · 11 | A=0.88 · 19 | A=0.68 · 41 | A=0.37 · 82 | A=0.01 · 127 | A=0.00 · 129 | A=0.00 · 129 |
| *embrasement (white %)* | 0% | 0% | 0% | 0% | 0% | 0% | 5% | 100% | 100% |
| *A_gal (ancrages/sprites)* | 1.00 | 1.00 | 0.97 | 0.88 | 0.68 | 0.37 | 0.01 | 0.00 | 0.00 |
Lecture : à `a=1`, tous les layers GRF sont à leur rendu de production
(moyennes 104-127) sauf `localgroup` (8.7/255, correctif §4.8) — plus sombre
par design. En remontant le temps, chaque layer converge vers le ton
uniforme partagé **129.4/255** (état dissous, `field_to_log_density(0)` sous
la normalisation figée `vmin=−0.9498, vmax=0.9642`) — y compris
`localgroup` via son plancher (§7). L'embrasement prend ensuite le relais
(nul jusqu'à a≈0.1, 100% à la recombinaison).

## 6. Correctif de continuité de A(s,a) — 13 juillet

La formule §11.4.b avec plancher `w = max(−log10(a_form), 0.05)` centrait la
fenêtre sur `log10(a_form)` : pour les échelles à plancher ACTIF
(`a_form > 10^−0.05 ≈ 0.891`, soit l3 → l5), la fenêtre débordait au-delà de
`a=1` et `A` sautait de 1 à ~0.5 juste sous `a=1` (mesuré : `A(l5, 1−ε) =
0.4995` avec l'ancienne formule) — violation de la contrainte dure « A(s,1)=1
continûment ». Correctif (appliqué dans `spacetime-shared.js`,
`spacetime_pipeline.py`, `validate_fullscene_render.py`) :

```
centre = min(log10(a_form), −w)      [la fenêtre se termine TOUJOURS à a=1]
```

Sans effet pour les échelles où le plancher est inactif (galaxies, l1b, l2,
l2b — rendus déjà calibrés). Conséquence assumée : les fenêtres de l3 → l5
coïncident toutes sur `a ∈ [0.794, 1]` (leurs `a_form` 0.92-1.0 sont plus
proches de 1 que la demi-largeur plancher) — l'échelonnement fin de la toile
cosmique est absorbé par le plancher. Si on veut le restaurer un jour :
réduire le plancher dans la matrice ET revalider la continuité.

## 7. Plancher de convergence de `localgroup`

`localgroup` est exporté LINÉAIREMENT (`clip(champ/4.074)`), pas en
log-densité : sans correction, sa dissolution convergerait vers le noir
(0/255) alors que les layers GRF convergent vers 129.4/255 — exactement la
rupture de luminosité moyenne que §11.1 point 3 interdit. Le plancher
`(1−A_gal(a)) × ton_dissous × 4.074` est un décalage du CHAMP avant export
(même famille de mécanisme que l'embrasement §11.4.c — un paramètre de
génération, pas un calque) : nul à `a=1`, il amène la texture au même état
uniforme que les autres layers quand les galaxies sont dissoutes.
Physiquement : la matière ne disparaît pas, elle s'uniformise.

## 8. Simplifications propres au prototype (à traiter à l'intégration production)

- Le poids du layer `milkyway` est reporté sur `localgroup` : la Voie lactée
  y est rendue par son sprite N-corps (`dissolution_keyframes.json`), pas par
  `density_milkyway.png`. L'intégration production devra décider du
  traitement temporel de la texture `milkyway` elle-même (probablement le
  même trio sprite + fond ancré + plancher).
- Le fondu entre layers de zoom reste le fondu alpha de production
  (`layerWeights.ts`) — mécanisme d'AXE DE ZOOM existant, distinct de
  l'interdiction §11.3 qui porte sur les transitions temporelles.
- Frames 512×512 (36 Mo pour 114 frames avant optimisation PNG, ~16 Mo
  réels) — résolution/nombre de keyframes réductibles via la matrice si le
  poids devient un problème.
