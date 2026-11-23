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
Étape (passage 2) : **10 contrôles sur 12 verts**, page pas encore publiable (C4, C5 :
segment Merdith seulement). Planche : `chantiers/planches/terre-2.png` (aujourd'hui,
66, 250, 540 Ma, 1 Ga, caméra automatique).

Fait au passage 2 :
- D-46 : C3 mesure le bloc continental (croûte > -200 m) : 96–100 % de 320 à 200 Ma, vert ;
  les terres émergées (71–82 %) restent affichées comme indicateur non bloquant.
- D-47 : frise à la vraie proportion (4,5 %), inchangée.
- Caméra automatique : le point subsolaire de juin, tourné d'au plus 30° vers le barycentre
  des continents (latitude bornée -20°/55°), suivi en douceur, libéré 8 s par le doigt.
  Nouveau contrôle C12 (≥ 60 % des terres visibles éclairées) : 95, 96, 97, 78, 96, 79 % à
  0, 66, 250, 540, 700 Ma et 1 Ga. (C12 a été écrit en même temps que la caméra : il n'a
  pas été montré en échec sur l'ancienne vue — il l'aurait été : 20 % à 1 Ga au premier essai.)
- Segment Merdith (1 Ga → 540 Ma) : cumul pondéré des morceaux (tampons flottants 32 bits
  quand le mélange flottant existe), poids continus (croûte qui naît, croûte qui s'enfonce
  en plateau à -200 m) : plus de bascule de visibilité ; empreinte des points corrigée près
  des pôles. C4 est rejoué 5 fois.

Ce qui reste rouge (tout dans le segment Merdith, que S3b remplacera, D-49) :
- C5 : 3,0 % de surface émergée perdue entre 540 et 540,5 Ma — le nuage Merdith, ramené
  au présent puis reporté à 540 Ma, a 2,7 % de terres de moins que le PaleoDEM de 540 Ma
  (pixels de terre qu'aucun pixel actuel n'atteint) ; vers 593 Ma ≈ 2,5 % (morceaux
  superposés qui changent de poids ensemble). Le segment PALEOMAP (540 → 0) passe.
- C4 : 4 passes sur 5 vertes (0,12–0,15 %), une à 0,47 % (vers 545 Ma) : même zone.

Question au maître : pour publier sans attendre S3b, appliquer C4 et C5 au seul segment
publié avec des reliefs (540 Ma → aujourd'hui) et afficher le segment 1 Ga → 540 Ma comme
« raccord provisoire » ? C'est restreindre un contrôle, donc à décider par Marc ;
recommandation : oui, S3b reprendra ce segment avec Cao et al. 2024.

Prochaine étape : S3b (Cao 2024, couche mince + FastScape) sur ce globe ; si l'on garde
Merdith d'ici là, combler les terres du PaleoDEM de 540 Ma non atteintes par le nuage.

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
