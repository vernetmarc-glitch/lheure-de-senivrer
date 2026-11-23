# État des chantiers

*Tenu par le maître ; chaque agent met à jour sa propre section (étape, page, questions).*

Départ (19/11/2026, 7 h 40) : `bake.py --check` sur `main` : 399 passés, 15 en échec,
0 bloquant (anciens chantiers de la grille A→O, hors refonte). Carte en production :
81 contrôles de page sur `fond-de-carte`, tous verts au 19/11 4 h.

## S0 — Fondations
Étape : lancé le 23/11 (compteur commun, lecteur vidéo).

## S1 — Soleil
Étape : interrompu le 19/11 (limite d'usage), relancé le 23/11 avec les directives du jour.

## S2 — Planètes et Lune
Étape : à lancer (vague 2).

## S3 — Terre, continents
Étape : données préparées par workflow (19/11) ; relancé le 23/11.

## S4 — Climat et glaces
Étape : attend S3.

## S5 — Vie
Étape : attend S4.

## S6 — Humanité
Étape : lancé le 23/11 (globe de nuit autonome, HYDE 3.3, Black Marble).

## S7 — Alpes
Étape : relief réel et simulation recalculés par workflow (19/11) ; relancé le 23/11.

## S7b — Orogenèse géodynamique
Étape (23/11, fin du passage 1) : chaîne de calcul en place et qui tourne ; page labo
`labo/orogenese/` montée ; coupes à 5 km en calcul sur GitHub (run déclenché par d39e7e5).
- Code : `sim/geodyn.py`, 2D maison (proposition S7b-1 dans `docs/decisions.md` : ni
  Julia ni démon Docker dans le bac à sable, donc LaMEM et ASPECT ne seraient mis au point
  qu'à distance). Stokes visco-plastique, marqueurs, air collant + FSSA, chaleur, érosion
  FastScape (fastscapelib), sédimentation marine. Convergence de Le Breton et al. 2021
  imposée par un poinçon adriatique rigide (Europe fixe). Quatre coupes (Argentera,
  Grenoble–Turin, Valais–Ossola, Grisons) raccordées en plan par l'arc actuel (`sim/carte.py`).
- Ce qui marche : subduction de la Téthys sous l'Adria, collision, croûte épaissie à 60 km,
  relief qui monte et s'use ; page (carte de 800 km, fragments nommés qui bougent, coupe
  des couches du modèle, compteur, récit) : contrôles de page 9/10 au vert.
- Contrôles (`controles.py`, 21) sur le **jeu d'essai à 15 km** déposé dans `donnees/` :
  14/21. Échecs : D1 convergence (309 km au lieu de 420 avant 35 Ma), D2 Téthys fermée trop
  tôt (−60 Ma), D4 r = 0,38, D5 moyenne 1 872 m et sommet 10 413 m, D5b, D7 (mailles vides,
  incohérence de pas à 15 km), D8 (carte et coupes à ±1,8 km), P5 (4 couches visibles).
  15 km est trop grossier pour juger la physique : verdict attendu sur le jeu à 5 km que le
  workflow dépose sur la branche.
- Manque : raccord en plan plus fin (bandes en éventail sur la carte), rotation de l'Adria et
  fichiers GPlates de van Hinsbergen 2020, zoom vers Grenoble et raccord à la fin de S7,
  glaciers (D6 vert par absence).
- Prochaine étape : relever le run 5 km (journaux dans `sim/journaux/`), contrôles sur ce
  jeu, réglages physiques là où ils échouent (couplage de l'interface de subduction,
  largeurs d'océan), puis raccord en plan et zoom.
- Planche : `chantiers/planches/orogenese-1.png` (jeu d'essai à 15 km).
- Question au maître : aucune.

## S8 — Glaciers
Étape : données Seguinot 2018 préparées, contrôles écrits (0/8 sur page vide) ; relancé le 23/11.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
- 23/11 ≈ 7 h 30 : limite de 5 h atteinte (remise à 10 h 40). Publiés : compteur et vidéo (S0), puis glaciers (S8, 10/10). 11 h 45 : reprise de S7, S3, S1 ; S6 et S8 au réveil suivant.
