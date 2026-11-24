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

## S3b — Terre en mécanique des roches (branche `chantier/terre-mecanique`)
**Étape 1 publiable, commit 5cadbeb** : page `labo/terre` bornée à 540 Ma → aujourd'hui
(curseur, lecture, `terre.regler` ; frise : 4,54 Ga → 540 Ma hachuré « à venir »), 12/12
contrôles verts sur toute la plage affichée (C4, C5, C6, C9, C12 lisent `terre.plage()`).
Corrigé en route : C5 échouait aussi dans le segment PALEOMAP (2,2 % vers 6,5 Ma : plaines
codées sur 8 bits à une seule altitude, noyées d'un coup) -> micro-relief de ±25 m attaché à
la croûte, éteint au-delà de 80 m ; lecture à 15 Ma/s (C11 n'avait plus le temps de mesurer).

**Publiable aussi, commit 57fa02e** (meilleur que 5cadbeb, même plage 540 Ma → aujourd'hui) :
17/17 contrôles verts — les 12 de S3 et les 5 de S3b sur cette plage : C13 Gondwana 72 %,
Pangée 100 % ; C14 calédonien, hercynien (s'abaissent ensuite), Himalaya, Andes, Alpes ;
C15 roche nue jusqu'à 470 Ma, 22 % des terres éclairées vertes à 300 Ma (couvert zonal :
forêts équatoriales et tempérées, steppes subtropicales ; photo d'aujourd'hui au Cénozoïque) ;
C16 frise des 7 réunions (Vaalbara, Ur, Kenorland « hypothèse », Pannotia « débattue ») et
ruban de la vie (genres marins, PBDB : 161 à l'Édiacarien, 833 à 520 Ma) ; C17 hors plage.
Les 5 contrôles S3b ont été montrés en échec d'abord (`controles/echec-s3b-avant.txt`).

Étape 2 (1,8 Ga → 540 Ma, mécanique des roches) : construite, **pas encore publiable**.
- Workflow `chantier-terre-mecanique.yml` : Cao et al. 2024 (Zenodo 13628813) lu par
  pyGPlates, topologies résolues tous les 2 Ma (19 min, en cache) ; mécanique (2 min) :
  couche mince pondérée par la croûte (couplage 0,05 des marges actives), isostasie d'Airy,
  érosion FastScape réécrite sur HEALPix (la roue pip de fastscapelib n'a pas HEALPix),
  racines relaxées en 80 Ma (hypothèse), épaisseur 20–75 km. Diagnostic :
  `donnees/diagnostic-mecanique.json` (> 2 000 m : 1,9 Mkm² à 1,6 Ga, 10,5 à 1 Ga, 18,8 à 600 Ma).
- Page : segment C (nuage de points, relief mécanique interpolé par morceau de croûte,
  raccord Cao → PALEOMAP de 620 à 540 Ma). Activé par `"publie": 1800` dans le manifeste.
- Essai à 1,8 Ga (`controles/essai-plage-1800.txt`) : 13/17. Rouges : C4 fantômes 0,15–0,48 %
  vers 575 Ma (raccord des rotations) ; C5 saut de 7,4 % vers 1 788,5 Ma (naissance de
  croûte au début du modèle) ; C13 Rodinia 58 % (Nuna 80 % : vert) ; C14 Grenville monte à
  4 749 m mais ne s'abaisse que de 615 m en 150 Ma (seuil 800).
- Avant 1,8 Ga (Vaalbara, Ur, Kenorland, Archéen immergé) : pas commencé ; frise « à venir ».
- Planche `chantiers/planches/terre-3.png` : page en essai à 1,8 Ga (2,7 Ga montre la borne
  1,8 Ga) ; les continents protérozoïques, au limbe et sans relief lisible, ne sont pas
  encore beaux.

Prochaine étape : C5 (naissance de croûte à 1,8 Ga), C4 (raccord 620–540 Ma), Rodinia
(croûte immergée qui coupe le bloc : épaisseur initiale, croûte juvénile), relaxation un
peu plus rapide pour Grenville ; puis la caméra et le relief lisible ; puis l'avant-1,8 Ga.

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
