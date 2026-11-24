Maître actif : 2026-11-24 07:27 UTC

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
Étape : **passages 5 et 6 terminés** (24/11) — `labo/humanite/`, branche `chantier/humanite`.
Contrôles : **28/28** sur la page servie (`controles-resultat.txt`) ; nouveaux montrés d'abord
en échec : passage 5 `controles-echec-passage5.txt` (0/4), passage 6 `controles-echec-passage6.txt`.
Planche : `chantiers/planches/humanite-5.png` (1 Ma, 100 000, 46 000 ans, 1279, aujourd'hui).

Passage 5 (relecture du maître) :
- noms en français : table relue `prepa/noms_fr.csv` (1 623 entités : 1 073 Wikidata avec
  majuscule initiale, 385 traductions relues, 129 noms propres invariants en liste blanche,
  36 foyers néolithiques) ; C23 : 96 noms affichés aux 10 dates, aucun en anglais ;
- aujourd'hui façon Black Marble : la couleur d'appartenance glisse vers la lumière
  blanche-dorée des villes (part 0 en 1950 → 0,9 en 2010) ; C24 : teinte des points ΔE 4 avec
  Black Marble, 100 % des points à la couleur de l'entité en 1950 ; C5 inchangé (r = 0,99) ;
- moins de noms, mieux choisis (C25) : 12 au plus, poids = aire × log(durée de vie), les plus
  importants placés d'abord, à ≥ 12 px des bords, jamais tronqués ; ordre total des entités
  superposées (aire puis nom) dans le workflow et dans le contrôle : C18 = 100 % aux 10 dates.

Passage 6 (retour de Marc, 24/11, 13 h 44 — l'aplat revient, léger et sous les points) :
- C12 « aucun aplat » (passage 3) remplacé par « points intacts » : mêmes points avec et sans
  fond, crête +1,3 % (≤ 2 %), même taille ; le fond est composé en espace d'affichage après
  le ton, sous les points ;
- C26 fond léger : + 3 à 10/255 au plus (≤ 8 %), 7 à 15 % du cadre teinté ; sapiens et
  Néandertaliens superposés montrent leurs deux teintes (46 % / 54 %) ;
- C27 frontière : diffuse (débord 33–54 %), front qui avance × 2,1 à × 4,0 plus marqué qu'un
  bord immobile, contour découpé en lichen (rugosité 1,24–1,51) ;
- C28 : après −10 000, fond à la teinte de l'entité (ΔE 0), léger.

Limites : le fond reste très discret à l'échelle d'une planche (pris entre le plafond de 8 % et
l'exigence de points intacts à 2 %) ; en 2024 les petits pays ne sont pas tous nommés.

Prochaine étape : jonction avec le globe de S3 ; zoom automatique sur une région pendant la
lecture historique.

### Question au maître (S6)
Accès à HYDE 3.3 : le dépôt d'Utrecht (geo.public.data.uu.nl, public.yoda.uu.nl) répond
par une page anti-robots à toute machine ; je ne la contourne pas. Recommandation : garder
HYDE 3.2.1 (écart faible sur 10 000 av. J.-C. → 2017) ; si Marc ou le maître peut
télécharger à la main `HYDE 3.3 / baseline` (zip « pop »), le déposer dans une release
GitHub du dépôt : le workflow le prendra. Rien ne bloque la page en attendant.

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
- 23/11 soir : publiés S7 passage 3, S6 passages 2 et 3, S8 passage 3. Limite de 5 h atteinte vers 18 h (remise 21 h 40). 22 h 20 : reprise S7b, S3, et S6 passage 4 (civilisations, N38–N39). S1 : run Phantom 45160564099 toujours en cours.
- 24/11 7 h 30 UTC : les réveils de la nuit ne se sont pas déclenchés (conversation inactive) ; reprise de S6 (passage 4), S3b, S1 (run Phantom en échec à 2 h 42) ; S7b attend son run 45271157024 ; maître de secours créé.
