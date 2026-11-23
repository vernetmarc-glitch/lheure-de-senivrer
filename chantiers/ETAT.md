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

## S8 — Glaciers
Étape (23/11) : **page labo publiable**, `app/public/labo/glaciers/` — 10/10 contrôles
verts (`python3 app/public/labo/glaciers/controles.py`, résultat dans
`chantiers/glaciers/controles-resultat.txt`). Planches : `chantiers/planches/glaciers-1.png`
(19/11), `chantiers/planches/glaciers-2.png` (23/11 : six instants + deux vues rapprochées
des moraines).

Ce qui marche :
- Données publiées : Seguinot et al. 2018, PISM 1 km EPICA « pp » (Zenodo 7802275, 1 état
  tous les 1 000 ans, 119 000 → 0 ans), fenêtre 150 × 150 km sur la grille native UTM 32
  (nord à 2,3° de l'axe y) ; relief Copernicus GLO-30 moyenné à 125 m. Workflow
  `chantier-glaciers.yml` (téléchargement, découpe, quantification, moraines) ; paquet
  publié 4,8 Mo (glace 2,7, relief 2,1, moraines 0,04).
- Rendu WebGL2 : relief éclairé, glace d'épaisseur variable (surface B-spline), foliation et
  crevasses dans le sens du courant, moraines médianes sombres et latérales, traînées
  advectées (RK2) dans le champ de vitesses interpolé dans le temps ; frise de l'aire
  englacée servant de curseur ; lecture ×400/×1 500/×5 000 ans/s ; épaisseur au-dessus de
  Grenoble en direct ; compteur de vitesse du temps (copie conforme N28 dans
  `labo/glaciers/compteur.js`, à remplacer par `commun/compteur.js` quand S0 l'aura) ;
  qualité adaptative (netteté, maillage, densité des filets) pour la fluidité.
- Contrôles : C1 paquet = données ; C2 étendue à une maille près (6 instants, 100 %) ;
  C3 rien d'inventé entre deux pas ; C4 maximum à 24 000 ans (11 726 km²), Grésivaudan
  englacé ; C5 traînées dans le sens des vitesses (écart médian 0,1–0,2°) et jamais hors
  glace ; C6 aucune erreur ; C7 fluidité (≤ 50 ms même en SwiftShader chargé) ; C8 lecture ;
  C9 signature moraines (= données à 1 km près, « deux flux » ≥ 97 %) ; C10 cadran (angle à
  < 1°, butée, flèche, coin, ne masque rien).

Constats (données) : dans ce modèle la glace n'atteint Grenoble qu'à 24 000 ans (430 m) et
le Grésivaudan qu'à 25–24 000 ans ; au maximum la glace couvre presque tout l'est de la
fenêtre (peu de moraines : calotte). Vitesses > 3 276 m/a (74 mailles sur 2,7 millions, marges
minces) écrêtées dans le paquet ; filets bornés à 600 m/a (sens conservé).

Ce qui manque : moraines médianes calculées (lignes de courant depuis les pointes
d'éperons), pas observées — signalé dans la page ; la glace est posée sur le relief actuel
(pas d'enfoncement isostatique) ; pas d'ombres portées ; couleurs de surface non issues
d'imagerie (pas de vidéo nécessaire à ce stade) ; pas de vérification sur un vrai téléphone
(le contrôle C7 est en rendu logiciel) ; sur la planche, l'aiguille n'a pas fini de revenir
en butée (images de contrôle très lentes), le contrôle C10 la mesure en conditions réelles.

Prochaine étape : pas de 100 ans (fichier `ex.100a`, 4 Go, par le workflow) pour un
écoulement plus continu ; ombres portées ; couleurs Sentinel-2 hors glace (en commun avec
S7) ; même caméra que S7 puis intégration dans `alpes`.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
