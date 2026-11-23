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
Étape (23/11) : première page labo `app/public/labo/terre/` complète, **8 contrôles sur 11
verts** au dernier passage — pas encore publiable (C3, C5, et C4 instable). Planche : `chantiers/planches/terre-1.png`.

Ce qui marche :
- Données publiées, préparées par `.github/workflows/chantier-terre.yml` (pyGPlates sur le
  runner) : PaleoDEM Scotese & Wright 2018 à 0,1° (109 états, 540 Ma → 0), modèle de plaques
  PALEOMAP livré avec eux (PaleoAtlas v3, Zenodo 5460860), Merdith et al. 2021 v1.2.4
  (Zenodo 13635864), Blue Marble NG juin 2004. Paquet `donnees/` : 35 Mo (≈ 5 Mo avant la
  première image).
- 540 Ma → 0 : rotations **PALEOMAP** (les PaleoDEM ont été dessinés sur ces plaques ; avec
  Merdith ils glisseraient hors de leurs propres reconstructions). États clés tous les 5 Ma
  (élévation + plaque par pixel) ; entre deux, chaque pixel est **transporté** par sa
  plaque (points WebGL2, rééchantillonnage au plus proche) et l'on interpole l'élévation
  de deux champs co-localisés : aucun fondu d'images.
- 1 Ga → 540 Ma : un seul nuage de points en coordonnées actuelles transporté par Merdith ;
  relief de 540 Ma qui s'efface (540 → 640 Ma) vers un relief générique signalé comme
  hypothèse ; raccord Merdith → PALEOMAP par rotation par morceau, étalé de 620 à 540 Ma.
  Sauts de rotation non physiques de Merdith (> 15°/Ma, ex. 610 Ma) lissés sur ± 5 Ma.
- Rendu : globe photoréaliste, Soleil fixe au solstice de juin, aujourd'hui = Blue Marble
  portée par les plaques et s'effaçant en remontant le temps (e-folding 10 Ma) vers des
  couleurs minérales (place laissée à S4/S5) ; liseré d'atmosphère ; frise 4,54 Ga avec
  segment hachuré « hypothèse » ; compteur commun (`commun/compteur.js`).
- Contrôles verts : C1 erreurs JS, C2 aujourd'hui 98,5 % (Natural Earth),
  C6 frise, C7 Soleil de juin, C8 atmosphère, C9 interaction, C10 Blue Marble (terres
  ΔE 1,7, mers ΔE 3,0), C11 compteur.

Ce qui manque :
- **C5** (aucun saut > 1 % de surface émergée en 0,5 Ma) échoue dans le segment Merdith :
  5,8 % vers 557 Ma, 2,6 % à 620 Ma, ≈ 1–2 % ailleurs. Cause : morceaux de croûte qui se
  chevauchent pendant le raccord des deux modèles et les mouvements très rapides de Merdith
  à l'Édiacarien (jusqu'à 8°/Ma) ; la règle de visibilité entre morceaux superposés bascule.
  Le segment PALEOMAP (540 → 0) passe.
- **C4** (pas de fantôme) est instable d'un passage à l'autre près du raccord : 0,12 à
  0,17 % (vert) sur trois passages, 0,77 % à 541 Ma (rouge) au dernier ; même cause que C5
  (morceaux superposés, égalités de profondeur entre points).
- **C3** (Pangée : 80 % des terres émergées en un bloc entre 320 et 200 Ma) échoue sur les
  données publiées elles-mêmes : 71 % à 220 Ma, 76 % à 260 Ma, 78 % à 300 Ma (mers
  épicontinentales et détroits des PaleoDEM, Chine du Nord et du Sud encore séparées). Le
  bloc continental (au-dessus de -200 m) fait 96–100 % à toutes ces dates.
- Vidéo de texture : non utilisée (la couleur vient de Blue Marble + relief calculé ; rien
  à décoder) ; à reconsidérer quand S5 apportera des couleurs changeantes.
- Proportion N8 : la Pangée et la chaîne hercynienne (380 → 175 Ma) couvrent 4,5 % de
  l'histoire de la Terre, pas « environ un dixième » ; la frise montre la vraie proportion.

Question au maître : C3 mesure-t-il les terres émergées (le texte du plan) ou le bloc
continental (croûte au-dessus de -200 m, la « Pangée » des géologues) ? Recommandation :
mesurer le bloc continental — les PaleoDEM publiés ne donnent jamais 80 % d'émergé d'un
seul tenant entre 300 et 220 Ma. C'est un changement de définition (à Marc s'il juge que
cela desserre l'exigence) ; en attendant, C3 reste strict et en échec.

Prochaine étape : C5 dans le segment Merdith (visibilité continue entre morceaux superposés,
raccord plus lent), puis publication ; ensuite S4 (glaces, climat) sur ce globe.

## S4 — Climat et glaces
Étape : attend S3.

## S5 — Vie
Étape : attend S4.

## S6 — Humanité
Étape : lancé le 23/11 (globe de nuit autonome, HYDE 3.3, Black Marble).

## S7 — Alpes
Étape : relief réel et simulation recalculés par workflow (19/11) ; relancé le 23/11.

## S8 — Glaciers
Étape : données Seguinot 2018 préparées, contrôles écrits (0/8 sur page vide) ; relancé le 23/11.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
- 23/11 ≈ 7 h 30 : limite de 5 h atteinte (remise à 10 h 40). Publiés : compteur et vidéo (S0), puis glaciers (S8, 10/10). 11 h 45 : reprise de S7, S3, S1 ; S6 et S8 au réveil suivant.
