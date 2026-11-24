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
Étape : **passage 4 terminé** (24/11 ; demande de Marc du 23/11, 22 h 19 ; N38, N39, D-50) —
`labo/humanite/`, branche `chantier/humanite`.
Contrôles : **22/22** sur la page servie (`controles-resultat.txt`) ; C18–C22 montrés d'abord
en échec sur la version publiée (`controles-echec-passage4.txt`, 0/5).
Planche : `chantiers/planches/humanite-4.png` (−2500, 100, 1279, 1900, aujourd'hui).

Passage 4 :
- **données** (workflow GitHub, `prepa/civilisations.py`) : Cliopatria v0.2.1 (14 000 enregistrements,
  1 409 entités politiques, −3400 → 2024) + 36 foyers néolithiques (`prepa/neolithique.csv`,
  disques aux contours approximatifs, en italique sur la page) ; carte « identifiant
  d'entité » à 0,25° pour 248 pas de temps (200 ans avant −3400, puis 50, 25, 10, 5 ans ;
  les 10 dates témoins sont des pas) : 2,0 Mo de cartes en paquets de 8 pas, chargés à la
  demande, 0,57 Mo de métadonnées ; noms français Wikidata (933/1 409, les autres en anglais) ;
  couleurs par coloriage des voisinages (0 paire voisine à ΔE < 30 sur 5 178) ;
- **rendu** : les points restent les points de population (un point = 2 000 humains) ;
  ils prennent la couleur de leur entité ; liseré discret de frontière ; ton qui garde la teinte
  (les foules ne virent plus au blanc) ; noms posés sur le centre intérieur de chaque zone, les
  plus grandes d'abord, sans chevauchement, en fondu, stables d'une image à l'autre ;
- **temps** : lecture × 0,06 à partir de −3000 (raccord −3600 → −3000) : 763 an/s avant,
  38 an/s après (× 20) ; bouton « Époque historique » qui saute à −3000 et lit ; −3000 → 2024
  dure environ 8 minutes ;
- C18 : 96,8 % à 100 % en surface aux 10 dates (shapely, indépendant du workflow) ; C19 : 100 %
  des points à la couleur de leur entité ; C21 : 98 % de la surface des pays de Natural Earth
  à leur entité en 2024 (4/131 grands pays partagés).

Ce qui manque : 476 noms restent en anglais (pas de libellé Wikidata français) ; en 2024 les
pays ont des couleurs vives sur les lumières de la nuit (choix de Marc), le « Black Marble »
pur n'existe plus qu'en couleur unique hors des entités ; les petits pays d'aujourd'hui ne
sont pas tous nommés (place) ; « aujourd'hui » = 2023 (HYDE), la carte 2024 sert à partir de 2024.

Prochaine étape : traduire les noms manquants (table de correspondance relue) ; zoom
automatique sur une région pendant la lecture historique ; jonction avec le globe de S3.

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
