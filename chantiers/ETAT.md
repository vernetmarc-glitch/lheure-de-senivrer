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
Étape : **passage 1 terminé (23/11)**, page labo `labo/alpes/` prête à publier,
branche `chantier/alpes`. Contrôles `app/public/labo/alpes/controles.py` : **23/23 verts**
sur la page servie (Playwright, 390 × 844). Planche : `chantiers/planches/alpes-1.png`.

Ce qui marche :
- Film de 45 Ma sur 204,8 km centrés sur Grenoble : FastScape (fastscapelib 0.3, 512² à
  400 m dans le workflow) avec soulèvement et raccourcissement imposés par un scénario de
  collision (`sim/scenario.py` : zones internes dès 45 Ma, massifs cristallins depuis
  22 Ma, chaînes subalpines 14–4 Ma, bassin d'avant-pays imposé : mer priabonienne, mer
  molassique, remplissage). Gabarit de soulèvement = inversion stationnaire du relief
  réel. Sur les 2 derniers Ma, ajustement vers le relief réel (écart 369 m à −2 Ma,
  0,6 m à la fin ; les 10 derniers ka sont libres). 213 états (250 ka puis 50 ka).
- Relief réel Copernicus GLO-90 et mosaïque Sentinel-2 cloudless 2024 (EOX), téléchargés
  par `.github/workflows/chantier-alpes.yml`. Paquet publié 9,8 Mo, 4,1 Mo avant la
  première image (relief 16 bits sans perte, jamais en vidéo).
- Couleurs : table couleur(altitude, pente) apprise sur la mosaïque (`sim/regles_couleurs.py`),
  appliquée à toutes les époques avec un décalage d'altitude climatique (climat chaud
  avant, cycles glaciaires schématiques depuis 2,6 Ma) ; la photographie Sentinel-2
  n'apparaît qu'à l'Holocène (12 derniers ka). ΔE médian 5,7 (règles) et 0,3 (affiché)
  avec la mosaïque. Pas de vidéo : les couleurs sont calculées en direct depuis le
  relief, rien à télécharger ; `commun/video.js` sera utile si on ajoute une texture
  qui change (ex. glaciers de S8).
- Ombres portées par un Soleil fixe, celui de la mosaïque (azimut 145°, hauteur 34°),
  calculées par état : accord 100 % avec le calcul Python. Relief exagéré 1,5×.
- Machine à laver, première forme : profondeur d'origine des roches au jour (érosion
  cumulée, advectée), bouton « roches ».
- Barre de temps non linéaire : 1,2 Ma/s jusqu'à −8 Ma, puis vitesse proportionnelle à
  l'âge (≈ 200 ka/s à −2 Ma, ≈ 20 ka/s à −0,2 Ma). Compteur commun (`commun/compteur.js`)
  en haut à droite. Noms des massifs à la fin (Belledonne, Chartreuse, Vercors,
  Grésivaudan, Grenoble, Écrins, Mont-Blanc).

Ce qui manque / limites :
- Avant −2 Ma, le relief est lisse (256², sans détail) ; le dépôt du bassin est imposé,
  pas calculé ; pas de glaciers (S8) ; machine à laver sans grains suivis ni coupe.
- Fluidité ≥ 50 images/s non mesurable ici (rendu logiciel : 3 images/s) ; les ombres
  sont calculées une fois par état pour alléger le GPU.
- Licence : s2cloudless 2024 est sous CC BY-NC-SA 4.0 (attribution affichée dans « ? ») ;
  compatible avec un site non commercial. Si le maître préfère CC BY, la couche 2016 est
  disponible (moins belle) : changer `COUCHES` dans `sim/prepare_mosaique.py`.

Prochaine étape : grains de roche suivis et coupe (N17) ; relief plus fin aux temps
anciens (détail de FastScape à 512² publié pour les derniers Ma) ; intégrer les glaciers
de S8 dans la même vue ; mesurer la fluidité sur un vrai téléphone.

## S8 — Glaciers
Étape : données Seguinot 2018 préparées, contrôles écrits (0/8 sur page vide) ; relancé le 23/11.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
