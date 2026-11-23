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
Étape : **passage 3 terminé** (23/11, retour de Marc de 17 h 25) — `labo/humanite/`, branche `chantier/humanite`.
Contrôles : **17/17** sur la page servie (`controles-resultat.txt`) ; les nouveaux montrés
d'abord en échec sur la version publiée (`controles-echec-passage3.txt` : 0/4).
Planche : `chantiers/planches/humanite-3.png` (2 Ma, 100 000, 46 000, 10 000 ans, aujourd'hui).

Passage 3 (règle 0 bis) :
- **une seule représentation** (C12) : plus d'aplat de couleur (teinte des territoires nulle,
  mesurée) ; avant 10 000 av. J.-C. les points ont la taille et l'éclat de ceux de
  l'Holocène (mesurés à l'écran : identiques à 12 500 et 9 000 ans) ; un point = 2 000
  humains partout ; plus de « feux » ni de foyers ;
- **loi de densité** (C13, remplace le contrôle des foyers du passage 2) : points tirés sur
  tout le territoire de la lignée, densité ∝ habitabilité moyenne (Timmermann 2022) ×
  (1 + 3 × proximité des présences attestées : sites clés + table S1) ; indice de Clark et
  Evans 0,94–1,45 (ni groupés ni réguliers), densité ×2,4 à ×3,4 à moins de 300 km des sites ;
  sapiens glisse vers la carte HYDE de 10 000 av. J.-C. entre 20 000 et 13 000 ans ;
- **étiquettes** (C16) : le nom de chaque lignée présente, posé sur le centre de son
  territoire visible, sans chevauchement (ni entre elles ni avec le cadran) ; « arrive » dans
  les premiers 15 % de sa vie, « s'efface(nt) » dans les derniers 15 % ;
- **couleurs** (C17) : palette resserrée sur des teintes séparées (magenta, orange, bleu,
  turquoise, vert, or) ; ΔE minimal 33 mesuré sur les crêtes des points dessinés ;
- C14 (contact 60–30 ka) : 9 instants sur 16, sans plus aucun « aimant » de contact ;
  C15 (Timmermann) inchangé, 98,2 %.

Ce qui manque : avant l'Holocène, peu de points (honnête à 2 000 humains par point : 100 à
1 000 points) et donc des continents peu lisibles de loin ; le liseré mêlé n'existe plus
que par l'entremêlement des points des deux couleurs ; pas de calottes glaciaires (S4).

Prochaine étape : jonction avec le globe de S3 ; régler la lisibilité des époques anciennes
sans changer K (zoom automatique sur le territoire actif, par exemple) — arbitrage à
soumettre si cela touche à la règle « un point = nombre fixe d'humains ».

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
