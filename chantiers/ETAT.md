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
Étape : **passage 2 terminé (23/11)**, branche `chantier/alpes`, page `labo/alpes/`.
Passage 1 publié sur main (0e4fe0e) ; licence s2cloudless 2024 tranchée (D-44).
Contrôles `app/public/labo/alpes/controles.py` : **29/29 verts** sur la page servie.
Planche : `chantiers/planches/alpes-2.png`.

Passage 2 (retours du maître) :
1. **Netteté.** Contrôle sur les données (part d'énergie à 1–5 km, tuiles montagneuses) :
   il passait déjà (169 %), le flou venait donc du rendu. Ajout d'un contrôle sur l'image
   rendue (ombrage d'un albédo gris, vue du zénith à 512², énergie à 1–5 km rapportée au
   relief réel rendu de la même façon) : **en échec sur la version publiée** (44 % à
   −30 Ma, 46 % à −12 Ma), puis vert : 102 à 132 % dès −30 Ma. Correction : film publié à
   pleine résolution FastScape (512², 400 m, pas de 2 m), maillage 512². Le détail vient
   de FastScape lui-même ; aucun détail réel n'est peint avant −2 Ma.
2. **Machine à laver.** 1 500 grains suivis dans une tranche de ±3 km autour de la coupe
   ONO → ESE par Grenoble (Vercors → Belledonne) : ils montent avec le soulèvement, sont
   portés par le raccourcissement et gardent leur profondeur maximale ; 652 arrivent au
   jour. Bouton « coupe » : la tranche, ses grains colorés par leur profondeur maximale,
   l'éclat quand l'un d'eux sort. Contrôle : au jour, la couleur de surface vaut la
   profondeur maximale du grain (écart médian 10 %).
3. **Glaciers.** PISM de Seguinot et al. 2018 (même fichier que S8), repris à la source
   par le workflow et reprojeté sur ma fenêtre de 204,8 km (la fenêtre S8 de 150 km ne la
   couvre pas), 256² à 800 m, 120 tranches de 1 ka. La glace s'élève au-dessus du relief
   sur les 120 derniers ka ; maximum à 24 ka (20 400 km²), Grésivaudan rempli. Contrôle :
   étendue dessinée = données à une maille près (0,1 % manquant au plus, rien d'inventé),
   rien avant 120 ka. Le froid des règles de couleur suit l'aire de glace PISM sur cette
   période. Pas de vidéo : la glace est une grandeur mesurée (binaire quantifié).

Limites, prochaine étape :
- Paquet de 32 Mo en tout (4,5 Mo avant la première image, le reste arrive pendant la
  lecture) : lourd pour un téléphone ; piste : clés tous les 500 ka avec résidus, ou
  états à 512² seulement sur les 10 derniers Ma.
- Glaciers sans traînées d'écoulement ni moraines (à reprendre de S8 : vitesses de
  surface dans le même fichier).
- Fluidité non mesurable ici (rendu logiciel : 2 images/s) ; maillage de 512² à vérifier
  sur un vrai téléphone.
- Le dépôt du bassin d'avant-pays reste imposé.

## S8 — Glaciers
Étape : données Seguinot 2018 préparées, contrôles écrits (0/8 sur page vide) ; relancé le 23/11.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
- 23/11 ≈ 7 h 30 : limite de 5 h atteinte (remise à 10 h 40). Publiés : compteur et vidéo (S0), puis glaciers (S8, 10/10). 11 h 45 : reprise de S7, S3, S1 ; S6 et S8 au réveil suivant.
