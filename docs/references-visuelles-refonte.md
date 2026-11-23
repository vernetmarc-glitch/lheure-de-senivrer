# Références visuelles de la refonte (23/11/2026)

Demande de Marc (23/11, 5 h 48) : comme la simulation Millennium pour la toile cosmique,
chaque chantier a **un visuel de référence**, objectif esthétique du rendu, et une
**signature chiffrée** tirée de cette référence, qui devient un contrôle (règle 0 ter).
Le style de rendu (photoréaliste, simulation 3D, animation) est fixé par chantier.

Principe de partage : **ce qui est matière se dessine en points lumineux** (nuage,
disque, planètes, humanité), **ce qui est surface se dessine en photographie** (Terre,
Alpes, glaciers). Les deux registres se rejoignent à la Terre de nuit, où l'humanité
redevient une myriade de points.

| Chantier | Référence visuelle | Style | Signature chiffrée (→ contrôle) |
|---|---|---|---|
| Toile, galaxie (existant) | simulation Millennium | simulation, points | vides = 5,0 % de la largeur du cadre |
| S1 Soleil | disque de HL Tauri vu par ALMA (2014) : anneaux concentriques séparés de sillons, autour d'une étoile d'un million d'années ; films SPH de formation d'étoiles | simulation 3D en points | au stade disque : au moins 3 anneaux et sillons alternés le long d'un rayon (contraste sillon/anneau ≥ 2) ; fond noir ≥ 60 % du cadre |
| S2 Planètes, Théia | visualisations des simulations SPH de Durham (Kegerreis et al.) | simulation 3D en points, colorés par la matière (noyau, manteau, Théia) | bras de débris et satellite visibles en quelques heures simulées ; deux matières distinguables |
| S3–S5 Terre | NASA Blue Marble Next Generation, composite de **juin**, sans nuages, 500 m | photoréaliste, globe 3D | aujourd'hui : couleur médiane des terres et des mers à ΔE ≤ 10 du composite de juin ; mers plus sombres que les terres |
| S6 Humanité | NASA **Black Marble** (la Terre la nuit, lumières des villes) pour la densité d'aujourd'hui ; densités historiques HYDE 3.3 (10 000 av. J.-C. → 2023, maille de 5′) | Terre de nuit, humanité en points lumineux, une couleur par lignée humaine | un point = un nombre **fixe** d'humains (jamais normalisé par l'image) ; aujourd'hui, carte des points corrélée à Black Marble (log) ≥ 0,8 ; nombre de points croît comme la population HYDE |
| S7 Alpes | relief réel (Copernicus DEM 30 m) drapé de la mosaïque Sentinel-2 sans nuages ; vues aériennes obliques des Alpes du Nord | photoréaliste, relief 3D vu d'avion | dernier état : relief à < 50 m du DEM, couleurs à ΔE ≤ 12 de la mosaïque ; ombres portées cohérentes avec un Soleil fixe |
| S8 Glaciers | vidéo des simulations de Seguinot et al. 2018 pour la dynamique ; vues aériennes de grands glaciers de vallée (Aletsch, Mer de Glace) pour l'aspect : glace blanche, moraines médianes sombres, crevasses | photoréaliste 3D + traînées d'écoulement | étendue = données à une maille près ; moraines médianes là où deux flux se rejoignent ; traînées dans le sens des vitesses (écart médian < 15°) |

## Humanité : lignées et densité

« Générations humaines » est lu comme **les lignées successives** (hominines, *Homo
erectus*, Néandertaliens, Dénisoviens, petits hommes insulaires, *Homo sapiens*), chacune
d'une couleur. La **densité** se lit par le nombre de points : une poignée de points
pendant deux millions d'années, puis l'embrasement de l'agriculture, puis la nuit
des villes d'aujourd'hui. Aux vitesses lentes, les points se renouvellent au rythme
d'une génération (≈ 25 ans), comme un scintillement de vies.

## Le compteur de vitesse du temps (N28)

Dans un coin de chaque scène, un cadran de voiture : aiguille sur une échelle
logarithmique de **1 an à 10 milliards d'années par seconde**, graduée 1 an · 100 ans ·
10 000 ans · 1 Ma · 100 Ma · 10 Ga, avec lecture chiffrée en clair (« 10 000 ans par
seconde »). Temps à l'arrêt : l'aiguille tombe sur la butée. Temps remonté : une flèche
indique le sens. Aiguille amortie, comme un vrai compteur. Composant commun à toutes les
scènes et pages labo (`app/public/commun/compteur.js`, chantier S0).

Contrôle : l'angle de l'aiguille vaut la vitesse réelle du curseur (échelle log, à 1°
près, après amortissement) ; le cadran reste lisible sur 390 px de large et ne masque
aucun objet de la scène.

## Format vidéo (N27)

- **Pour les couleurs qui changent dans le temps à projection fixe** (texture du globe en
  projection équirectangulaire, couleurs de surface des Alpes) : vidéo, décodée image par
  image avec WebCodecs et posée en texture WebGL. Le globe reste tournable : c'est sa
  texture qui est une vidéo.
  - H.264 en MP4 pour tous (décodage matériel partout), AV1 quand le téléphone le décode
    (fichiers ≈ 30 % plus légers), choisi à l'exécution par `isConfigSupported`.
  - Image clé toutes les 8 images, pas d'images B : on peut aller et venir dans le temps
    sans tout redécoder.
  - Repli sans WebCodecs : élément `<video>` et recherche par horodatage (moins précise).
- **Pas de vidéo pour les grandeurs mesurées** (relief, épaisseur et vitesse de la glace,
  densité humaine) : la compression avec perte fausserait les contrôles. Elles restent
  des binaires quantifiés (16 bits) aux instants clés, interpolés à l'écran.
- **Pas de vidéo pour le zoom** : il se fait en direct (points et maillages), sur une
  pyramide de textures.
- Contrôle : poids d'un récit ≤ 10 Mo avant la première image, fluidité ≥ 50 images/s au
  défilement sur le téléphone de référence (émulé), erreur de couleur vidéo ≤ ΔE 3 sur
  une image témoin.
