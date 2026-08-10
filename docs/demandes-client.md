# L'Heure de s'enivrer — Demandes client

**Nature du document.** Ce que l'œuvre doit **montrer**. Aucune méthode, aucun
paramètre, aucune implémentation. Chaque exigence est formulée de façon
**observable à l'œil** et doit pouvoir être jugée sans connaître le code.

**Statut.** Version 1.9, arrêtée le 7 août 2026. Reconstitution à partir du document
d'architecture, de l'historique du projet et des échanges de session. **À
relire ligne à ligne par Marc** — l'objet même de ce document étant ce qui a été
oublié, son exhaustivité ne peut pas être garantie par celui qui a oublié.

**Règle d'usage.** Ce document est relu **en entier** au début de toute session
et **avant toute proposition de méthode**. Une méthode qui ne référence pas les
exigences qu'elle sert est incomplète.

---

## 0. L'œuvre — intention

**L'objet de l'œuvre est de faire comprendre visuellement trois limites de
l'univers : l'univers observable, la sphère de Hubble et l'horizon des
événements.** Tout le reste — la toile cosmique, les galaxies, les filaments, la
dissolution dans le temps — est un **fond de carte au service de cette
compréhension**.

Cette phrase fixe la hiérarchie de tout ce document. La **section H** en est le
sujet ; les sections A à G décrivent le support qui doit le rendre lisible, et
non l'inverse. Une décision qui améliorerait le fond de carte au détriment de la
lisibilité des trois sphères est une mauvaise décision.

*(Origine : 29/07. Ce cadrage était absent des semaines de travail précédentes,
consacrées presque entièrement au fond de carte.)*

### Ce que le fond de carte doit permettre

Le support doit donner l'**échelle** et la **profondeur de champ** nécessaires
pour situer les trois sphères : sans structure visible à toutes les échelles, un
cercle de 4 450 Mpc ne veut rien dire. Il doit aussi donner le **temps** — les
horizons évoluent, et c'est en les voyant bouger qu'on les comprend.

Il ne doit jamais **capter l'attention pour lui-même** au point de rendre les
sphères difficiles à lire.

### Les deux axes de parcours

Une carte interactive de l'univers observable, parcourue selon **deux axes** :

- **le zoom**, de la Voie lactée jusqu'au diamètre de l'univers observable
- **le temps**, d'aujourd'hui jusqu'aux premiers instants

Les deux axes forment une matrice : toute combinaison (échelle, époque) doit
produire une image juste et belle.

**La matrice compte 15 lignes et 11 colonnes**, soit 165 cellules, codées de
`A0` à `O10`. Toutes les lignes portent les **mêmes** 11 époques : une colonne
est un instant de l'univers, identique d'un bout à l'autre de l'échelle de zoom.
Les positions intermédiaires des deux curseurs sont obtenues par interpolation à
l'affichage.

*(Origine : 30/07. Auparavant chaque ligne avait son propre axe du temps — la
colonne 4 valait a = 0,891 sur une ligne et a = 0,480 sur une autre. Voir
`approches-ecartees.md`.)*

### Structure des layers

**Quinze lignes, codées A à O**, de la Voie lactée à l'horizon des particules.
Le demi-champ est le rayon du cadre en mégaparsecs comobiles.

| Code | Demi-champ (Mpc) | Ce que la ligne montre | Rendu |
|---|---|---|---|
| **A** | 0,035 | **La Voie lactée**, occupant tout le cadre | sprite |
| **B** | 0,088 | **La Voie lactée et ses voisines proches** — Sagittaire, Grand et Petit Nuage de Magellan | sprites |
| **C** | 0,222 | Le halo de la Voie lactée qui s'efface ; ses satellites deviennent petits | sprites |
| **D** | 0,560 | L'approche du Groupe Local ; NGC 6822 entre dans le cadre | sprites |
| **E** | 1,41 | **Le Groupe Local dans son ensemble** — IC 10, Andromède, Leo I, Triangulum | sprites |
| **F** | 3,56 | Le Groupe Local et ses abords — 29 galaxies du catalogue | sprites |
| **G** | 8,96 | **Le voisinage complet** — 86 des 98 galaxies du catalogue. Dernière ligne à sprites | sprites |
| **H** | 22,6 | Le catalogue est épuisé ; la matière devient statistique | généré |
| **I** | 56,9 | | généré |
| **J** | 143 | | généré |
| **K** | 361 | | généré |
| **L** | 911 | | généré |
| **M** | 2 295 | | généré |
| **N** | 5 782 | La sphère de Hubble et l'horizon des événements entrent dans le cadre | généré |
| **O** | 14 570 | **L'horizon des particules — l'univers observable entier** | généré |

`O` correspond au rayon de l'univers observable, soit ~95 milliards d'années-lumière
de diamètre.

**Le passage des sprites à la matière générée se fait entre G et H**, là où le
catalogue s'épuise : sa galaxie la plus lointaine est à 9,82 Mpc. C'est le seul
endroit de l'échelle où les deux représentations peuvent être comparées côte à
côte, et donc le seul endroit où **D1** est vérifiable.

Les lignes C et D n'apportent aucune galaxie nouvelle : entre les satellites de
la Voie lactée (0,06 Mpc) et Andromède (0,78 Mpc), notre voisinage est
physiquement vide. Elles portent l'effacement du halo et le fond filamentaire
ambiant demandé en **A8**.

*(Origine : 30/07. Cette échelle remplace une échelle à 13 lignes dont les pas
allaient de ×1,41 à ×24 — voir `decisions.md`, D-21.)*

---

## A. Caractère visuel général

**A1.** La référence esthétique est la **simulation Millennium** : une myriade de
points brillants avec une structure filamenteuse visible.
→ *Ni* filaments peints en continu, *ni* champ d'étoiles uniforme.

**A2.** L'image doit lire comme une **toile d'araignée**, jamais comme une
**mousse** de bulles rondes.
*(Origine : rejet explicite du 28/07 — « on a plus une impression de mousse ».)*

**A3.** Les zones les plus lumineuses doivent être **quasi ponctuelles à tous les
étages de zoom**, jamais des surfaces étendues.
*(Origine : 28/07 — « j'ai peur qu'en zoomant sur ces taches on ne puisse pas
obtenir l'effet fractal ».)*

**A4.** Les points lumineux doivent être d'**intensité variable**, et les amas de
**taille variable**. Pas de pois de taille égale, pas de tout-blanc.
*(Origine : 28/07 — « des pois de taille tout égale… tout est blanc ».)*

**A5.** Entre les amas, les points doivent se répartir **le long de fins
filaments** reliant des amas de tailles différentes — et non au hasard.

**A6.** Il doit y avoir **continuité d'aspect** entre les points brillants et le
fond diffus : une seule population de matière, pas deux calques superposés.
*(Origine : 28/07 — « il n'y a pas de continuité d'aspect entre les points
blancs et les nuages ».)*

**A7.** La palette est celle du projet (« Astro », du noir au blanc chaud par le
rouge sombre et l'orange). Le rendu ne doit jamais être en noir et blanc pur.
**A8. Sous `G`, le fond s'atténue sans disparaître.** Les layers montrant des
galaxies doivent porter, eux aussi, un **fond généré de matière filamentaire**,
afin de rester visuellement cohérents avec les layers supérieurs. Une galaxie ne
flotte pas sur du vide.

L'atténuation attendue est précisée ainsi *(Marc, 07/08)* :

- le fond devient **très peu perceptible par rapport aux galaxies** — il
  s'efface au regard, il ne s'efface pas de l'image ;
- il subsiste **quelques nuages filamentaires diffus** ; ce n'est **pas** un
  fond uniforme, et ce n'est pas non plus un grain sans forme ;
- **aucune zone de haute luminosité autre que les galaxies elles-mêmes** : rien
  dans le fond ne doit rivaliser en éclat avec un objet du catalogue.

Les trois clauses sont distinctes et doivent être satisfaites ensemble : un fond
lissé jusqu'à l'uniforme échoue la deuxième, et un fond conservé tel quel échoue
la troisième.
*(Origine : 29/07. Précisée le 07/08 après mesure : le fond mesurait un pic de
220/255 sur `G` contre 245 pour les galaxies — presque leur égal — et 118 contre
108 sur `E`, donc **plus brillant qu'elles** ; à l'autre bout, `C` et `B`
tombaient à 2,0 et 2,5 d'écart-type, soit quasiment uniformes.)*

**A9. Uniformité de rendu entre objets de même nature.** Deux objets du même type
— deux galaxies, deux amas — doivent être rendus par le **même procédé** et à la
**même échelle apparente** pour une taille physique donnée. Aucune famille
d'objets ne doit se distinguer par son traitement plutôt que par sa nature.
*(Origine : 06/07. Rédigée en exigence le 07/08 — elle n'existait jusque-là que
dans l'historique du document.)*

**A10. Halo de raccord, et la Voie lactée dessinée dessous.** Chaque galaxie
porte un **halo** qui la raccorde au fond : la lumière ne s'arrête pas net au
bord de l'objet. La Voie lactée, qui occupe le centre, est dessinée **sous** les
autres : une galaxie située dans son disque apparent doit rester **visible
par-dessus** elle, et non noyée.
*(Origine : 06/07. Rédigée en exigence le 07/08.)*

**A11. Piqué à tout niveau de zoom.** Aucune image affichée ne doit être un
agrandissement excessif d'une source de résolution insuffisante, et le traitement
se fait à la **résolution native** de la source, jamais sur une version
sous-échantillonnée.
*(Origine : 06/07 — un recadrage de 8,5 pixels natifs agrandi ×35, et un pipeline
travaillant en 512 sur des textures 1024. Rédigée en exigence le 07/08.)*

**A12. Les galaxies sont simulées, jamais dessinées.** Les vignettes de galaxies
proviennent d'une **simulation N-corps** — gravité mutuelle, intégration
temporelle — et non d'une forme analytique tracée à la main.
*(Origine : 08/07. Rédigée en exigence le 07/08. C'est la régression qui a duré
cinq mois : le moteur physique avait été remplacé par des gaussiennes, faute
d'être écrit quelque part.)*

**A13. Structure interne riche.** Une galaxie observée à sa taille propre doit
montrer une **structure interne** — grumeaux, bras, irrégularités — et non un
dégradé lisse.
*(Origine : 13/07. Rédigée en exigence le 07/08.)*

**A14. Halo elliptique suivant l'aplatissement du disque.** Le halo d'une galaxie
est **elliptique**, et son grand axe est **orienté comme le disque**. Un halo
circulaire posé sur un disque incliné trahit un objet dessiné plutôt que simulé.
*(Origine : 13/07. Rédigée en exigence le 07/08.)*


---

## B. Axe du zoom

**B1. Héritage à 100 %.** En changeant de layer, la matière visible ne doit
**jamais être redistribuée**. Un objet visible sur un layer se retrouve **au même
endroit** sur le layer adjacent. Le zoom **précise**, il ne réinvente pas.
*(Exigence formulée le 27/07 ; c'est la contrainte la plus forte du projet.)*

**B2. Similarité entre layers voisins.** Au-dessus de H, chaque layer doit offrir
un rendu **très similaire** au précédent : les structures du centre héritent
directement de ce qui était visible, et des structures de **plus grande échelle**
apparaissent en plus. On ne doit **pas perdre** les détails haute fréquence en
montant dans les layers.
*(Origine : 29/07, sur le démonstrateur.)*

**B3. Isotropie aux plus grandes échelles.** Les layers les plus élevés, et eux
seuls, tendent vers une plus grande **isotropie** : plus de structure à basse
fréquence. C'est le « End of Greatness ».

**B4. Effet fractal — et son domaine de validité.** En descendant dans les
niveaux de zoom, on doit retrouver **une même structure à une échelle très
inférieure**. La sous-structure doit exister à tous les étages **de la fenêtre où
l'univers est effectivement auto-similaire : d'environ 0,1 à 150 Mpc, soit les
lignes `D` à `J`.** En dessous, les objets sont liés gravitationnellement et
cessent de se subdiviser. Au-dessus, l'univers est statistiquement homogène et
rien de nouveau n'apparaît. Exiger la sous-structure hors de cette fenêtre
reviendrait à représenter un univers qui n'existe pas.
*(Domaine borné le 31/07, après recherche sur les échelles réelles. L'exigence
n'est pas retirée : elle est située.)*

**B5. Taille des structures fidèle à l'échelle.** Une structure d'une taille
physique donnée doit occuper la place qui lui revient à chaque échelle
d'observation.

**B9. L'approche de l'homogénéité est graduelle.** Il n'y a **pas de coupure** :
en montant en échelle, des structures de plus en plus grandes existent, mais
elles représentent des fluctuations de plus en plus **faibles**. L'amplitude
relative doit donc décroître continûment, jamais s'arrêter net à une échelle
seuil.
*(Littérature : au-delà de 300 h⁻¹ Mpc l'homogénéité prévaut ; Yadav 2010 donne
~370 Mpc comme limite au-delà de laquelle une distribution ne se distingue plus
d'une distribution homogène.)*

**B10. Au-delà de l'homogénéité, l'uniformité est GÉOMÉTRIQUE, jamais
photométrique.** Aux plus grandes échelles, la carte ne doit privilégier **aucun
lieu** : pas de région plus structurée qu'une autre, pas de direction privilégiée,
pas de centre. C'est cela, l'homogénéité — une propriété **statistique et
spatiale**.

Ce n'est **pas** une platitude de couleur. **Comme sur Millennium, on doit
toujours voir aux nœuds de la toile des points plus lumineux que le reste**, à
tout niveau de zoom, y compris le plus élevé. Une toile uniformément fade ne
satisfait pas B10 : elle le rate.

Deux fautes distinctes sont proscrites, et elles se ressemblent à l'œil :

- **la toile fade** — les structures sont là mais sans dynamique, l'image ne
  montre plus rien ;
- **les points posés par-dessus** — une toile fade complétée de points brillants
  **indépendants d'elle**. Ce n'est ni Millennium, ni physique : à ces échelles
  rien ne justifie un point lumineux qui ne soit pas un nœud.

Le critère qui les sépare est mesurable : **les pics doivent coïncider avec les
nœuds de la toile**.

*(Origine : 03/08 — « il reste des points lumineux à très grande échelle, cela ne
correspond pas à une réalité physique ». **Corrigée le 07/08** : la première
rédaction demandait une image « quasi uniforme », lue comme une platitude
photométrique. Mesure qui a tranché : à la ligne `O`, 405 pics dont **10 %
seulement** tombaient sur les 10 % les plus denses de la toile — soit exactement
le hasard. Les points étaient statistiquement indépendants de la structure.)*

**B10 bis. Aux très grandes échelles, la luminosité moyenne peut dériver.**
Maintenir une moyenne identique sur toutes les lignes écrase la dynamique du flux
là où les contrastes physiques sont les plus faibles, et fait **disparaître les
structures**. Une **légère dérive de la luminosité moyenne vers le haut est
acceptée** aux grandes échelles, en échange de nœuds qui restent visibles comme
aux niveaux de zoom inférieurs.

Ce qui est ancré, c'est le **fond** — il ne doit jamais noircir (B6) ; ce qui est
libre, c'est ce que les nœuds ajoutent au-dessus.
*(Origine : 07/08, arbitrage de Marc.)*

**B11 et A5 — domaine de validité.** Ces deux exigences s'appliquent **là où la
bande spectrale disponible atteint deux octaves**. Elle est bornée en bas par la
résolution (Nyquist) et en haut par B5. À la ligne `O`, un pixel vaut 91 Mpc et
il ne reste que **1,26 octave** : B5 et B11 y sont arithmétiquement
incompatibles. `N` en autorise 2,59, `M` 3,93. Les exigences ne sont pas
retirées, elles sont **situées** — comme B4 l'a été à la fenêtre `D`→`J`.
*(Borné le 08/08/2026, décision D-30, sur mesure. À `O` l'univers observable est
homogène, ce que B8 déclare déjà ; y peindre une toile reviendrait à représenter
un univers qui n'existe pas.)*

**B11. Aléatoire, jamais régulier.** La structure doit être celle d'un champ
**aléatoire amassé** — distribution de type Poisson aux grandes échelles, puis de
plus en plus groupée en descendant. Jamais un motif régulier ou quasi-périodique.
*(Origine : 03/08 — « dans les premières itérations on avait un zoom out sur une
structure relativement aléatoire, dans les dernières les structures semblent très
régulières ». Cause : une **bande spectrale trop étroite** engendre mécaniquement
une quasi-périodicité. Mesuré : dispersion des distances au plus proche voisin de
0,40 à la ligne `O`, contre 0,52 pour une distribution purement aléatoire et 1,83
à la ligne `J`.)*

**B6. Aucune zone vide.** Sur toute la grille zoom × temps, aucune partie du
cadre affiché ne doit être noire, neutre ou par défaut.

**B8. Échelle des structures conforme au réel.** À chaque ligne, la structure
dominante visible doit être **celle qui existe physiquement à cette échelle**. La
table ci-dessous fixe, ligne par ligne, la structure attendue et sa taille
caractéristique. C'est cette table — et non une auto-similarité imposée — qui
arbitre l'échelle apparente des structures. Une ligne dont la structure dominante
est deux fois trop fine ou deux fois trop large ne montre pas l'univers.

**La grandeur qui arbitre est la taille des vides** — le diamètre du plus grand
disque inscriptible dans une région sombre. C'est ce que l'œil juge, et c'est la
définition usuelle du rayon d'un vide. Le pic du spectre de puissance, essayé le
31/07, mesure la texture et non l'organisation : il ne convient pas.
Sur l'image de référence, les vides mesurent **5,0 % de la largeur du cadre** —
valeur stable de 4,4 à 5,8 % pour un seuil balayé de 35 à 55 %.
*(Origine : 31/07, sur constat visuel de Marc — « on a seulement un dézoom sur
une structure à fréquence spatiale fixe ».)*

### Table de référence des structures cosmiques

| Structure | Taille caractéristique | Ligne |
|---|---|---|
| Disque galactique | 0,01 – 0,05 Mpc | `A` |
| Satellites de la Voie lactée | 0,02 – 0,06 Mpc | `B` |
| Halo galactique | 0,1 – 0,3 Mpc | `C` |
| Abords du Groupe Local | ~0,5 Mpc | `D` |
| **Groupe de galaxies** | 1 – 3 Mpc | `E` |
| **Rayon viriel d'un amas** | ~2,3 Mpc | `F` |
| **Amas entier, largeur de filament** | 2 – 6 Mpc *(0,1–0,6 en matière noire seule, 1–3 avec baryons)* | `G` |
| **Longueur de filament, épaisseur de superamas** | 25 – 32 Mpc · 6 – 9 Mpc | `H` |
| **Superamas** | 45 Mpc de grand axe, 8 de petit *(Vierge)* ; Laniakea ~160 | `I` |
| **Vides courants** | 30 – 60 Mpc de diamètre | `I` – `K` |
| **Vides du réseau superamas-vides, BAO** | ~140 Mpc · ~150 Mpc | `J` – `K` |
| **Réseau superamas-vides, grandes murailles** | 170 – 200 Mpc · ~400 Mpc *(Sloan)* | `K` |
| **Passage à l'homogénéité** | 100 – 300 Mpc *(contesté)* | entre `J` et `L` |
| — | *rien de nouveau au-delà* | `L` → `O` |

**Conséquence assumée : les lignes `L` à `O` sont homogènes.** La toile n'y est
plus qu'une texture sous-pixellaire — à la ligne `O`, un vide de 140 Mpc mesure
1,6 pixel. Ce n'est pas une limite de l'implémentation, c'est l'univers. Ce sont
les **trois sphères** qui portent ces lignes, ce qui est cohérent puisqu'elles
sont le sujet de l'œuvre.
*(Arbitré par Marc le 31/07.)*

**B7. Sens de construction.** Les grandes échelles précèdent les petites. Le
Groupe Local ne doit **pas** être un point spécial au centre de la carte.

---

## C. Axe du temps

**C1. Dissolution continue.** En remontant le temps, **toutes** les structures —
le fond compris — se dissolvent **continûment**, comme une goutte d'encre dans
l'eau : elles **s'étalent et pâlissent** en même temps.
*(Origine : 28/07. C'est le critère central de l'axe du temps.)*

**C2. Ne pas grossir.** Une structure qui se dissout ne doit **jamais** paraître
grossir ni gagner en luminosité. Pas d'explosion, pas de tache blanche qui
s'étend.
*(Origine : 28/07 — « on a l'impression que les galaxies grossissent plutôt
qu'elles ne se dissolvent ».)*

**C3. Se dissoudre en filaments.** Les points lumineux ne doivent pas pâlir sur
place : ils doivent **s'étirer le long des filaments** qui les ont alimentés, et
ces filaments restent visibles aux étages de zoom concernés.
*(Origine : 28/07.)*

**C4. Pas d'apparition de structure.** La dissolution ne doit **pas** faire
apparaître des structures plus petites qui coloniseraient l'espace. Ce qui existe
se défait ; rien ne naît en remontant le temps.
*(Origine : 28/07 — « des structures plus petites apparaissent… plutôt qu'une
réelle dissolution ».)*

**C5. Hiérarchie de dissolution.** Les **grandes** structures se défont en
premier ; les galaxies persistent le plus longtemps.

**C6. Jamais de fond noir.** Aucune époque ne doit produire une image noire ou
sans intérêt visuel. La luminosité moyenne reste **constante** jusqu'à
l'embrasement final.
*(Décision du 28/07 : politique 2, moyenne constante.)*

**C7. Embrasement final.** Aux premiers instants, l'image converge vers le blanc.
C'est le seul moment où la luminosité moyenne monte.

**C8. Détail conservé jusqu'au bout.** L'image garde de la **variation spatiale
fine** jusqu'à la dissolution totale. L'état final est *uniforme mais plein de
grain* — jamais un aplat.

**C9. Aujourd'hui est exact.** À l'époque actuelle, l'état est exactement celui
de la carte de référence, sans transition ni saut.

**C10. Vitesse d'expansion juste à toute échelle et à toute époque.** La
dilatation de l'espace doit être correcte à **chaque niveau de zoom** et à
**chaque époque**. Elle n'est pas uniforme : aux petites échelles la **gravité
l'emporte** sur l'expansion et les systèmes liés — galaxies, groupes — ne se
dilatent pas ; aux grandes échelles l'expansion domine intégralement. La
transition entre les deux régimes doit être juste.
*(Origine : 29/07.)*

**C10 bis. L'expansion apparente doit suivre l'expansion réelle.** *(Origine :
08/08/2026. Précise C10, qui posait le principe sans le rendre mesurable.)*

La compression apparente des structures en remontant le temps doit suivre le
**facteur d'échelle** `a(t)` de la cosmologie, et rien d'autre. Il ne s'agit pas
d'un effet visuel réglé à l'œil : à la colonne `n`, la matière occupe
`a(t_n)` fois l'étendue propre qu'elle occupe aujourd'hui.

**Aucune matière ne doit franchir la frontière de la sphère qui la contient.**
La sphère de matière que nous observons aujourd'hui garde le **même contenu** à
toutes les époques : ce sont les mêmes atomes, plus serrés. Une structure qui
sortirait du cercle en remontant le temps signalerait que la compression du fond
de carte et le rayon tracé ne suivent pas la même loi.

*Distinction indispensable, sans quoi l'exigence est mal posée.* Il y a **deux
cercles différents**, et un seul est infranchissable :

- **la sphère de la matière observable aujourd'hui** — rayon comobile fixe,
  14 150 Mpc. Elle contient toujours la même matière ; **rien ne la franchit
  jamais**. C'est celle que vise cette exigence.
- **l'horizon des particules à l'époque `t`** — il **rétrécit** en remontant le
  temps : 14 150 Mpc comobiles aujourd'hui, **279 Mpc à la recombinaison**, un
  facteur **51**. De la matière en sort donc légitimement quand on remonte, et
  c'est un fait que l'œuvre doit **montrer**, pas masquer : l'univers observable
  contenait moins de matière dans le passé, et c'est précisément ce que le mot
  « observable » veut dire.

**Chiffres de référence** *(Planck 2018, rayonnement inclus)* :

| | rayon comobile | diamètre |
|---|---|---|
| horizon des particules, aujourd'hui | 14 150 Mpc | **92,3 Gal** |
| horizon des particules, recombinaison | **279 Mpc** | 1,82 Gal |
| sphère de Hubble, aujourd'hui | 4 448 Mpc | 29,0 Gal |
| horizon des événements, aujourd'hui | 5 114 Mpc | 33,4 Gal |

*Le « ~900 millions d'années-lumière juste après le Big Bang » est le **rayon**
comobile de l'horizon des particules à la recombinaison — 909 Mal — et non un
diamètre. Le diamètre vaut 1,82 milliard d'années-lumière.*

**C10 ter. Là où la gravité l'emporte, il n'y a pas de dilatation.** Un système
lié ne participe pas à l'expansion : ses composantes sont retenues par leur
propre gravité, et la dilatation de l'espace ne les écarte pas. En remontant le
temps, **ces échelles ne se compriment pas** — elles se **défont**, ce qui est
un tout autre mouvement, déjà porté par C16.

La frontière est la **surface de vitesse nulle** du système : ~1,0 à 1,4 Mpc
pour le Groupe Local, ~7 à 9 Mpc pour un amas riche. Sur l'échelle de zoom, cela
place la transition **entre `E` (1,41 Mpc) et `F` (3,56 Mpc)** :

- `A` → `E` — systèmes liés. **Aucune compression** avec le temps.
- `F` → `G` — régime de transition, à traiter explicitement et non par
  interpolation muette.
- `H` → `O` — flot de Hubble intégral. Compression en `a(t)`.

*Appliquer `a(t)` uniformément à toutes les lignes ferait rétrécir la Voie
lactée avec l'univers : c'est faux, et c'est le contresens que cette exigence
existe pour empêcher.*

**C11. Datation juste de la dissolution.** L'époque à laquelle chaque type de
structure se défait doit correspondre à l'**état des connaissances
scientifiques**, et non à un réglage esthétique. Le curseur du temps doit être
lisible comme une véritable chronologie.
*(Origine : 29/07.)*

**C12. Contraction aux plus grandes échelles.** Au zoom minimal — les layers
montrant l'univers observable dans son ensemble — remonter le temps doit
**contracter** les structures déjà fines, pour aller vers un visuel à **très
haute fréquence spatiale**. C'est le pendant temporel de B3 : là où l'espace se
dilate, les structures comobiles rapetissent à l'écran et l'image se densifie.
*(Origine : 29/07.)*

---

## D. Transitions

**D1. Fluidité sprites ↔ densité.** Le passage entre les layers de galaxies
(sprites) et les layers de densité doit être **imperceptible** : même ton, même
densité apparente, même luminosité, et une galaxie donnée doit avoir la **même
taille et le même éclat** des deux côtés du fondu.

**D2. Fondu de zoom sans saut.** En glissant d'un layer à l'autre, aucun saut de
luminosité, de contraste ou de densité.

**D3. Cohérence croisée.** À **toute époque**, deux layers de zoom voisins
doivent rester cohérents entre eux — et à **tout zoom**, deux époques voisines
doivent rester cohérentes. C'est la contrainte la plus facile à oublier.

**D4. Galaxies réelles.** Les galaxies du catalogue du Groupe Local sont à leur
**position réelle**. Leur influence s'atténue avec l'échelle et disparaît au-delà
du voisinage — elles ne doivent pas marquer les grandes échelles.

**D6. Les galaxies réelles sont des centres de gravité.** Sur les lignes générées
les plus basses, les filaments doivent **converger vers** les positions du
catalogue, et non s'illuminer à leur endroit. En descendant vers les lignes à
sprites, chaque galaxie nommée doit apparaître **au nœud d'une structure qui la
désignait déjà** avant qu'elle ne soit visible. C'est ce qui rend **D1** vrai à
l'œil, et pas seulement en moyenne.
*(Origine : 31/07, formulée par Marc.)*

**D7. Positions et tailles relatives justes.** Le diamètre apparent des galaxies
et leurs distances mutuelles doivent être **cohérents avec le catalogue**. Deux
galaxies voisines doivent apparaître à la bonne distance l'une de l'autre, et
leur rapport de taille doit être celui de leurs rayons réels.
*(Origine : 06/07 — « je n'ai pas l'impression que le diamètre apparent des
galaxies et leur distance soit cohérent ».)*

**D8. Aucune galaxie ne disparaît entre deux paliers.** Une galaxie visible à un
niveau de zoom doit rester visible au palier suivant tant qu'elle est dans le
cadre. En particulier, la Voie lactée ne doit pas s'effacer dès qu'on sort de son
propre palier.
*(Origine : 06/07 — « la Voie lactée disparaît complètement et il n'y a plus de
points lumineux au centre quand on voit les galaxies périphériques ».)*

**D5. Morphologies variées.** Les galaxies doivent présenter des formes
**variées**. Le réalisme n'est pas l'objectif — à ces échelles on ne les voit
quasiment pas — mais leur **dissolution** doit être juste (cf. C1 à C3).
*(Origine : 28/07.)*

---

**C16. Les galaxies se dissolvent par simulation, pas par effet.** La dissolution
des neuf sprites est produite par le **même moteur N-corps**, intégré vers
l'avant en temps de simulation — ce qui représente le temps qui remonte côté
application. La gravité mutuelle reste **active pendant la dispersion** : c'est
elle qui produit des amas irréguliers persistants plutôt qu'une explosion
uniforme. Aucun flou, aucun fondu vers une couleur, aucun bruit ajouté.
*(Origine : 08/07. Signature attendue : les pics locaux **augmentent** pendant la
dissolution — la galaxie se fragmente. S'ils diminuent, c'est qu'on lisse.)*

**C17. Conservation du flux pendant la dissolution.** Une galaxie qui se dissout
**s'étale et pâlit à flux quasi constant**. Son pic doit s'effondrer pendant que
son rayon croît, sans que la lumière totale explose.
*(Origine : 30/07 — `HALO_GROWTH = 8,5` violait l'architecture documentée depuis
le 10/07 ; corrigé à 1,2 avec `fluxNorm = 1/widen²`. Rapport de flux : ×77 avant,
×2,18 après. Pic : constant à 1,000 avant, 0,067 à la dissolution après.)*

**C13. Tout est dissoluble par construction.** Chaque composante visible doit
être produite par une fonction **paramétrée par l'amplitude de structure** de la
colonne. Aucune structure ne peut être posée « en dur » : ce qui n'a pas de loi
temporelle ne pourra pas se dissoudre, et bloquera la colonne entière.
*(Origine : 03/08, rappel de Marc. C'est la condition pour que les onze colonnes
soient seulement du calcul et non une reprise de conception.)*

**C14. Conservation de la matière pendant la dissolution.** Ce qui se défait doit
**rendre sa matière** au champ dont il provient, et non s'ajouter par-dessus.
Sinon la dissolution ne se termine jamais : il reste un résidu qui ne peut pas
disparaître.
*(Origine : 30/07 — les halos doivent soustraire au réseau, pas y ajouter. σ de
structure mesuré 13,96 sans conservation, 2,38 avec, pour 0,65 en verre pur.)*

**C15. L'état d'amplitude nulle est atteignable.** À la colonne 0, toute
composante doit avoir atteint son état dissous — aucune ne doit conserver une
amplitude résiduelle qui la rendrait encore visible comme structure. Le grain
subsiste (C8), les structures non.
*(Origine : 03/08. C'est ce qui rend C4 vérifiable de bout en bout plutôt que
paire par paire.)*

---

## E. Interdits

**E1.** Aucun **flou géométrique** comme mécanisme de transition ou de
dissolution.

**E2.** Aucun **mélange vers une couleur unie** pour faire disparaître quelque
chose.

**E3.** Aucun **bruit interpolé lisse** comme source de structure — il détruit les
hautes fréquences.
*(Toléré uniquement en modulation d'un champ déjà structuré, avec extinction aux
deux extrémités — dérogation du 28/07 pour les sprites.)*

**E4.** Aucune **saturation généralisée** : pas de grandes plages de blanc pur ni
de noir pur.

**E5.** Aucun **artefact de grille** : pas de maille, de damier, de pixellisation
ni de direction privilégiée horizontale ou verticale.
*(Origine : recadrage du 28/07.)*

**E6.** Aucune **structure périodique** ou motif qui se répète.

---

## F. Valeurs validées

| Grandeur | Valeur | Date |
|---|---|---|
| Luminosité moyenne d'une image | **65 à 70 / 255** | 28/07 |
| Politique de luminosité dans le temps | **constante** jusqu'à l'embrasement | 28/07 |
| Moteur des galaxies | **sprite** (rendu N-corps), pas les nuages de halos | 28/07 |
| Aspect à aujourd'hui | **change** par rapport à la production actuelle — acté | 28/07 |

---

## G. Ce qui reste à trancher

- **G1.** Forme du profil des objets brillants : une seule loi ne satisfait pas à
  la fois l'échelle des amas et celle des galaxies.
- **G2.** Traitement des 90 galaxies procédurales du catalogue sans sprite dédié.
  L'échelle du 30/07 les place toutes sur les lignes F et G, où elles sont
  visibles individuellement. Reste à trancher : sprites dédiés, ou points du
  champ généré ancrés sur leur position réelle ?
- **G3.** Faut-il forcer davantage de diversité morphologique parmi les naines,
  qui représentent ~59 % du catalogue ?
- **G4.** Les trois sphères s'affichent-elles simultanément, ou une à une ?

---

## H. Horizons cosmologiques — LE SUJET DE L'ŒUVRE

C'est la raison d'être de la carte, et non une couche d'information ajoutée par
dessus. Trois limites distinctes, souvent confondues, qu'il faut ici distinguer
nettement et rendre **compréhensibles par le regard**.

**H1. L'univers observable** — horizon des particules. Tout ce dont la lumière a
pu nous parvenir depuis le Big Bang. Rayon comobile ≈ **14 150 Mpc**, soit
~46,1 milliards d'années-lumière, **~92 milliards de diamètre**. C'est l'étendue
du layer `M`.
*(Chiffres recalculés le 08/08/2026 sur Planck 2018 — Ωm 0,315, ΩΛ 0,685,
H₀ 67,4, rayonnement inclus. Le « ~95 milliards de diamètre » précédent était
faux : la valeur communément publiée est 93, et l'intégrale du dépôt donne 92,3.
Les 14 570 Mpc étaient le demi-champ de la ligne `O`, pas l'horizon.)*

**H2. La sphère de Hubble** — la distance à laquelle la vitesse d'éloignement due
à l'expansion **égale la vitesse de la lumière**. Rayon ≈ **4 450 Mpc**, soit
~14,5 milliards d'années-lumière. Elle est **plus petite** que l'univers
observable : on voit des objets qui s'éloignent de nous plus vite que la lumière.

**H3. L'horizon des événements** — la limite au-delà de laquelle un événement qui
s'y produit aujourd'hui ne pourra **jamais** nous parvenir. Rayon ≈ **5 100 Mpc**,
soit ~16,6 milliards d'années-lumière.

**H4. Vitesses d'éloignement justes.** La vitesse de récession en fonction de la
distance doit être correcte, y compris là où elle **dépasse la vitesse de la
lumière** — ce qui n'a rien de paradoxal et fait partie de ce que l'œuvre doit
donner à comprendre.

**H5. Évolution dans le temps.** Ces trois rayons **ne sont pas constants** : ils
évoluent avec l'époque, et différemment les uns des autres. Leur représentation
doit rester juste à toute position du curseur temporel.

**H6. Lisibilité prioritaire.** Les trois sphères doivent rester **lisibles et
distinctes** à toute position des deux curseurs. En cas de conflit entre la
beauté du fond de carte et la lisibilité des sphères, la lisibilité l'emporte.

**H7. Compréhension par la manipulation d'abord.** C'est en déplaçant les
curseurs et en regardant que l'on doit comprendre pourquoi la sphère de Hubble
est plus petite que l'univers observable, et ce que cela implique. Le texte
explicatif vient **en appui** et reste optionnel — il ne porte jamais seul la
compréhension.

*(Origine : 29/07.)*
**H8. La vitesse de la lumière représentée.** Le fond de carte doit porter, sous
une forme ou une autre, une représentation de la **vitesse de la lumière** —
c'est l'étalon qui rend les trois sphères intelligibles, et notamment le fait que
certaines régions s'éloignent de nous plus vite qu'elle.
*(Origine : 29/07.)*


---

## J. Parcours guidés

**J1. Animations prédéfinies.** Les trois sphères doivent pouvoir être comprises
au moyen de **petites animations** parcourant des **trajectoires choisies** dans
la matrice zoom × temps. On ne compte pas sur le seul tâtonnement de
l'utilisateur pour faire apparaître ce qui compte.

**J2. Montrer l'évolution.** Ces parcours ont pour but de faire **voir évoluer**
les sphères — leurs tailles relatives, leurs croisements, ce qui entre et sort de
chacune — plutôt que de les décrire.

**J3. Reprise de la main.** À tout moment, l'utilisateur doit pouvoir quitter un
parcours guidé et explorer librement.

*(Origine : 29/07.)*

---

## K. Qualité et fluidité

**K1. Navigation fluide.** Le déplacement dans les deux axes doit rester fluide,
sans à-coup ni attente.

**K2. Qualité maximale au repos.** Dès que la navigation s'arrête, l'image
affichée doit être de la **meilleure qualité possible**. La fluidité ne doit pas
se payer en qualité sur l'image que l'on contemple.

**K3. Utilisable pendant le chargement.** La carte doit être exploitable avant
que tout ne soit chargé.

*(Origine : 29/07. Méthode envisagée par Marc — deux jeux de layers, basse
résolution pendant le défilement et haute résolution à l'arrêt — relevant du
document d'architecture.)*

---

## L. Dispositif

**L1.** Deux curseurs : **zoom** et **temps**.

**L2.** À l'ouverture, le curseur temporel est positionné sur **aujourd'hui**.

**L3.** Le temps s'exprime en **milliards d'années**. Conséquence **assumée** :
les époques les plus anciennes sont très brèves à l'écran, et l'évolution des
trois sphères y sera peu lisible. *(Arbitré par Marc le 29/07.)*

**L4.** L'observateur est **au centre** de la carte : c'est une carte de l'univers
*observable*, donc vu d'ici.

**L5.** Les distances doivent pouvoir se lire en **comobile** et en **propre** —
la distinction fait partie de ce qu'il y a à comprendre.

**L6.** L'interface est en **français**.

*(Origine : 29/07, relevé sur l'application en production.)*
**L7.** Le **redshift n'est pas affiché**. *(Arbitré par Marc le 29/07.)*


---

## Écarté du document client

Ces points ont été proposés puis retirés : ce sont des **méthodes**, pas des
demandes. Ils relèvent du document d'architecture.

- Anneaux concentriques gradués et grille cartésienne — *une* façon parmi
  d'autres de donner l'échelle. L'exigence est que l'échelle soit lisible, pas
  qu'elle le soit ainsi. *(Écarté par Marc le 29/07.)*
- Deux jeux de layers basse/haute résolution — méthode servant K1 et K2.

---

## Comment ce document est appliqué

**Ce document ne suffit pas.** L'expérience de juillet-août 2026 est nette : une
exigence écrite ici mais non couverte par un contrôle exécutable dérive en
silence, et se reperd au premier correctif apporté ailleurs. Quatre régressions
majeures sont passées ainsi.

Chaque exigence mesurable a donc un contrôle correspondant dans
`docs/registre-tests.md`, exécuté à **chaque** cuisson par
`scripts/harness/bake.py`, qui refuse de publier si un seul échoue.

Une exigence sans contrôle est une exigence qui sera oubliée. Quand une nouvelle
exigence apparaît, elle est **d'abord** traduite en contrôle.

---

## Traçabilité

Toute exigence ajoutée porte sa **date** et son **origine**. Une exigence n'est
retirée que sur décision explicite de Marc, jamais par omission.

### Historique

**v1.9 — 07/08/2026.** **B10 corrigée, B10 bis ajoutée.** La rédaction du 03/08
demandait une image « quasi uniforme » au-delà de l'homogénéité ; elle a été lue
comme une platitude photométrique, et les contrôles écrits le matin même
mesuraient cette platitude. L'intention est une uniformité **géométrique** : les
nœuds de la toile restent plus lumineux, comme sur Millennium. B10 bis autorise
la dérive de la luminosité moyenne qui rend cela possible. Mesure qui a tranché :
à la ligne `O`, 10 % des pics seulement tombaient sur la toile — le hasard pur.

**v1.8 — 07/08/2026.** **A8 précisée**, sur retour de Marc. L'exigence n'est ni
ajoutée ni retirée : elle est rendue **vérifiable**. « Le fond s'efface » était
lu comme un fondu vers l'uniforme ; l'intention est une atténuation *relative aux
galaxies*, avec des nuages filamentaires qui subsistent. Trois clauses
mesurables remplacent une phrase d'intention. Ferme **O-08** : E2 n'a pas besoin
de dérogation, c'est le mécanisme d'effacement qui était en cause.

**v1.7 — 07/08/2026.** Aucune exigence ajoutée ni retirée : **A9 à A14 sont
rédigées** dans la section A. Elles avaient été introduites les 03/08 (v1.4 et
v1.5) sous forme d'une ligne de résumé dans cet historique, et jamais promues en
exigence. Sept contrôles s'y référaient pourtant. C'est exactement le défaut
qu'elles documentaient elles-mêmes : une exigence qui n'est pas à sa place n'est
pas lue.

**v1.6 — 03/08/2026.** Trois exigences sur le rendu aux très grandes échelles,
appuyées sur la littérature :

- **B9** l'approche de l'homogénéité est graduelle, sans coupure
- **B10** au-delà de l'homogénéité, l'uniformité est géométrique, jamais photométrique
- **B10 bis** aux très grandes échelles, la luminosité moyenne peut dériver
- **B11** aléatoire, jamais régulier

*Elles corrigent un défaut introduit par la borne à 300 Mpc du 02/08 : en
restreignant la bande spectrale, elle a rendu les lignes hautes quasi-périodiques
et y a laissé des pics qui n'ont aucune réalité physique.*

**v1.5 — 03/08/2026.** Cinq exigences ajoutées, toutes transcrites de travaux
réussis de juillet qui n'avaient jamais été écrits comme exigences — donc non
protégés, donc dégradés depuis :

- **A12** les galaxies sont simulées par N-corps, jamais dessinées *(08/07)*
- **A13** structure interne riche *(13/07)*
- **A14** halo elliptique suivant l'aplatissement du disque *(13/07)*
- **C16** dissolution par le même moteur, gravité active *(08/07)*
- **C17** conservation du flux pendant la dissolution *(30/07)*

*Ces cinq exigences sont la raison pour laquelle les sprites du 6 juillet étaient
« plus jolis, avec un meilleur piqué ». Le procédé était un vrai moteur physique ;
il a été remplacé par des gaussiennes dessinées à la main faute d'être écrit
quelque part.*

**v1.4 — 03/08/2026.** Huit exigences ajoutées, aucune retirée. Six sont des
**transcriptions de retours anciens** de Marc, jusque-là appliqués sans être
écrits — donc non protégés par un contrôle, donc reperdus :

- **A9** uniformité de rendu entre objets de même nature *(06/07)*
- **A10** halo de raccord, et la Voie lactée dessinée dessous *(06/07)*
- **A11** piqué à tout niveau de zoom *(06/07)*
- **D7** positions et tailles relatives justes *(06/07)*
- **D8** aucune galaxie ne disparaît entre deux paliers *(06/07)*
- **C14** conservation de la matière pendant la dissolution *(30/07)*

Deux sont nouvelles, et garantissent que la ligne d'aujourd'hui pourra être
dissoute proprement :

- **C13** tout est dissoluble par construction
- **C15** l'état d'amplitude nulle est atteignable

**v1.3 — 31/07/2026.** **D6** ajoutée : les galaxies du catalogue sont des
centres de gravité pour les filaments, et non des taches brillantes posées à
leurs coordonnées. Implémentée par ancrage dans le champ de déplacement Ψ et non
dans la densité — écart assumé par rapport au mécanisme de la §4.7, acté par
Marc. Aucune exigence retirée.

**v1.2 — 31/07/2026.** Une exigence ajoutée, une bornée. Aucune retirée.

- **B8** ajoutée : l'échelle apparente des structures est arbitrée par une table
  de référence des structures cosmiques réelles, sourcée, et non par une
  auto-similarité imposée. Origine : constat visuel de Marc sur la
  planche-contact du 31/07.
- **B4** bornée à sa fenêtre de validité, 0,1 à 150 Mpc. L'exigence n'est pas
  retirée, elle est située — hors de cette fenêtre, l'auto-similarité n'existe
  pas dans l'univers.
- Acté que les lignes `L` à `O` sont homogènes et portées par les trois sphères.

**v1.1 — 30/07/2026.** Aucune exigence retirée ni ajoutée. Modifications de
structure uniquement, sur décision de Marc :

- §0, structure des layers : échelle refondue à 15 lignes géométriques `A`→`O`
  (raison ×2,520) en remplacement des 13 lignes précédentes, dont les pas
  allaient de ×1,41 à ×24. Les trois contenus définis par Marc — la Voie lactée,
  la Voie lactée et ses voisines, le Groupe Local entier — se placent en `A`,
  `B` et `E`.
- §0, deux axes : grille figée à 15 × 11, colonnes communes à toutes les lignes.
- **B2** : la référence « au-dessus de F » devient « au-dessus de H », le
  demi-champ visé (~60 Mpc) ayant changé de lettre.
- **G2** : reformulée — 90 galaxies procédurales et non 89, et la question
  restante précisée.
- **A7/A8**, **H6/H7/H8**, **L6/L7** remis dans l'ordre. Aucune n'avait changé
  de contenu ; dans un document cité par numéro, l'ordre de lecture compte.

**v1.0 — 29/07/2026.** Reconstitution initiale.

---

## E — Expansion : cohérence entre la dilatation réelle et la carte

*Ajouté le 08/08/2026, demande de Marc. Chiffres vérifiés et corrigés contre
l'état de l'art (Planck 2018 : Ωm = 0,315, ΩΛ = 0,685, Ωr = 9,2·10⁻⁵,
H₀ = 67,4 km/s/Mpc).*

**E1. La carte est en coordonnées COMOBILES, et cela décide tout le reste.**
Les quinze lignes sont graduées en Mpc comobiles, de 0,035 à 14 570. En
comobile, une structure ne se comprime pas avec le temps : elle **reste où elle
est**. Ce qui change avec l'époque, ce sont les **horizons**, dont le rayon
comobile varie. Toute la cohérence demandée se ramène donc à deux affirmations
séparées, et les confondre est la faute à éviter.

**E2. Les rayons des trois horizons doivent découler de la cosmologie, jamais
d'un réglage.** À chaque colonne, les rayons comobiles de l'horizon des
particules, de la sphère de Hubble et de l'horizon des événements doivent être
ceux qu'on recalcule depuis Ωm, ΩΛ, Ωr et H₀. Aucune valeur saisie à la main.

| | rayon comobile | diamètre |
|---|---|---|
| aujourd'hui (colonne 10) | 14 144 Mpc | **92,3 milliards d'a.l.** |
| recombinaison (colonne 0) | 278,6 Mpc | **1,82 milliard d'a.l.** |

*Correction d'un chiffre de l'énoncé : 900 millions d'années-lumière à la
recombinaison est le **rayon** comobile (0,91 Gal), pas le diamètre. Le
diamètre vaut le double. Les 90 milliards d'années-lumière d'aujourd'hui sont
justes — 92,3 exactement.*

**E3. La matière DOIT franchir l'horizon des particules en remontant le temps —
c'est le sujet, pas un défaut.** Le rayon comobile de l'horizon passe de
14 144 Mpc à 278,6 Mpc de la colonne 10 à la colonne 0, soit une contraction
d'un facteur **50,8**, pendant que les structures restent à leur place
comobile. Elles sortent donc du cercle, et c'est exactement ce que signifie
« l'univers observable grandit » : de la matière **entre** dans l'horizon au fil
du temps.

*Vouloir que rien ne franchisse la frontière reviendrait à faire grandir
l'horizon au même rythme que l'espace, c'est-à-dire à supprimer la notion même
d'horizon des particules — et donc le sujet de l'œuvre. Aucun contrôle ne doit
« corriger » ce franchissement.*

**E4. Aux échelles liées, aucune dilatation apparente.** Sous le rayon de
retournement, la gravité l'emporte sur l'expansion et les structures ne suivent
pas le flot de Hubble. Ce rayon vaut `(GM/ΩΛH₀²)^(1/3)` : **≈ 1,9 Mpc** pour le
Groupe Local (5·10¹² M☉) et **≈ 11 Mpc** pour les amas les plus massifs
(10¹⁵ M☉).

| lignes | demi-champ | régime |
|---|---|---|
| `A` → `F` | ≤ 3,56 Mpc | **liées** — aucune dilatation apparente |
| `G` | 8,96 Mpc | transition |
| `H` → `O` | ≥ 22,6 Mpc | flot de Hubble |

Sur `A`→`F`, la seule évolution temporelle admise est la **dissolution** (C13 à
C17) : les objets se défont parce qu'ils ne sont pas encore formés, jamais parce
que l'espace les aurait étirés.

