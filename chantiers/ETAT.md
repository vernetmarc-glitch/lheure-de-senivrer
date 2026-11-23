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
Étape : **première page labo publiable** (23/11) — `labo/humanite/`, branche `chantier/humanite`.
Contrôles : **11/11** sur la page servie (`app/public/labo/humanite/controles.py`, journal
`controles-resultat.txt` ; échec initial 0/11 dans `controles-echec-initial.txt`).
Planche : `chantiers/planches/humanite-1.png` (2 Ma, 100 000 ans, 40 000 ans, 10 000 ans, aujourd'hui).

Ce qui marche :
- globe de nuit WebGL2 (relief SRTM15+ 0,2°, côtes au niveau marin de l'instant : Béringie,
  Sonde, Sahul), rotation et pincement, curseur 7 Ma / 300 000 ans / 10 000 ans, lecture
  à vitesse décroissante (âge divisé par e toutes les 7,7 s) ; compteur commun
  (`commun/compteur.js`, contrôle C6 conservé) ;
- 6 lignées (7 cartes : la première sortie de sapiens à part) : carte arrivée/disparition
  à 0,5° par croissance de proche en proche (Dijkstra sur vitesses bruitées), domaines
  d'après les habitats de Timmermann et al. 2022 (serveur IBS, OPeNDAP), ponts de terre
  et sauts de mer selon le niveau marin (Spratt & Lisiecki 2016, Bintanja & van de Wal
  2008), calée sur 85 sites et refuges datés (`prepa/sites_cles.csv`, publications citées) ;
  remplacement par sapiens avec coexistence (5–8 ka), liseré de couleur mêlée ;
- densité : un point = 2 000 humains (fixe) ; effectifs estimés de la littérature avant
  10 000 av. J.-C. (signalés), HYDE ensuite (52 498 mailles, 38 tranches, 4,0 M de points
  aujourd'hui) ; lumière par humain tirée de Black Marble 2016 (r log = 0,99 ; densité
  seule r = 0,74) ; électrification progressive 1880 → 2016 (hypothèse signalée) ;
  points renouvelés à chaque génération (25 ans) aux vitesses lentes ;
- 6,5 Mo avant la première image ; JS 0,9 ms par image.

Ce qui manque / limites :
- **HYDE 3.3** est derrière une protection anti-robots (Anubis) à Utrecht : la page
  utilise **HYDE 3.2.1** (DANS, → 2017) et l'effectif ONU 2023 réparti comme en 2017 ;
- ROAD injoignable depuis GitHub (délai dépassé) et accès complet sur inscription : sites
  clés pris dans les publications et chez Timmermann et al. 2022 (table S1 téléchargée,
  pas encore exploitée : 3 245 entrées) ;
- esthétique : traînées radiales dans les territoires (chemins du Dijkstra visibles via la
  lueur du front), points d'avant l'Holocène un peu uniformes ; pas de calottes glaciaires
  (S4) ; position des points dans la maille d'après 2017 pour toutes les tranches.

Prochaine étape : exploiter la table S1 de Timmermann (contrôle C2 sur les 3 245 entrées,
calage) ; habitats variables dans le temps (vitesse du front ∝ habitabilité) pour des
bouffées plus organiques ; lueur du front lissée ; densité intra-continentale avant
l'Holocène guidée par les habitats ; puis jonction avec le globe de S3.

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
