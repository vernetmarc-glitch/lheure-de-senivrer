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
Étape : **passage 3 terminé**, branche `chantier/alpes`, page `labo/alpes/`. Périmètre
redéfini (D-48) : S7 garde la fin (derniers Ma, relief réel, glaciers, allègement) ; S7b
refait l'orogenèse ancienne (120 → ≈ 5 Ma) avec un modèle géodynamique.
Contrôles `app/public/labo/alpes/controles.py` : **31/31 verts**. Planche :
`chantiers/planches/alpes-3.png`.

Passage 3 :
1. **Poids.** Contrôles d'abord, en échec sur la version publiée (dossier 42,2 Mo ; poids
   avant la première image non mesuré, ≈ 4,5 Mo), puis verts : dossier publié **13,0 Mo**
   (seuil 15), **0,71 Mo** avant la première image, mesuré par le navigateur (seuil 4).
   Paquet v3 : images clés 512² tous les 4 états (1 Ma, puis 200 ka à la fin), pas de
   10 m, en différences d'une clé à l'autre ; entre deux clés, résidus 128² au pas de 8 m
   par rapport à l'interpolation des clés. Seules les clés restent en mémoire ; l'état
   affiché est reconstruit à la demande. Mosaïque et détail réel arrivent après la première
   image. Film : 9,0 Mo ; écart final au relief réel 3,0 m ; netteté du rendu conservée,
   y compris entre deux clés (84 % à −29,5 Ma, 95 % à −12,25 Ma ; seuil 50 %). Les scripts
   de simulation sont dans `chantiers/alpes/` (plus rien dans app/public).
2. **Glaciers au niveau de S8.** Vitesses de surface PISM (128², 1,6 km) et moraines
   médianes calculées par la méthode de S8 (`chantiers/alpes/moraines.py`, copie adaptée aux
   mailles de 800 m) à partir des données publiées. Rendu repris de S8 : surface de glace
   lisse (lit lissé sur 2,8 km + épaisseur, plus de bosses), foliation le long du courant,
   crevasses au-delà de 80 m/a, moraines médianes et latérales, reflet ; traînées advectées
   (1 500 au plus, 40 ans d'écoulement par seconde). C5 : écart angulaire médian 0,1°,
   95e centile ≤ 1,8°, 0 % hors glace ; C9 : moraines dessinées = moraines des données à
   100 % dans les deux sens, deux flux 100 %, 225 km au total. Étendue de la glace : celle
   des données à une maille près.

Ce qui reste (pour la fin, S7) : glace un peu trop blanche de près (foliation peu
lisible) ; fluidité à mesurer sur un vrai téléphone (rendu logiciel ici : 2 images/s) ;
raccord avec S7b quand ses états existeront (reprendre son relief à ≈ 5 Ma comme point de
départ de l'ajustement vers le relief réel).

## S8 — Glaciers
Étape : données Seguinot 2018 préparées, contrôles écrits (0/8 sur page vide) ; relancé le 23/11.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
- 23/11 ≈ 7 h 30 : limite de 5 h atteinte (remise à 10 h 40). Publiés : compteur et vidéo (S0), puis glaciers (S8, 10/10). 11 h 45 : reprise de S7, S3, S1 ; S6 et S8 au réveil suivant.
