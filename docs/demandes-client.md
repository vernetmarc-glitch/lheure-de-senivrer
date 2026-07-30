# L'Heure de s'enivrer — Demandes client

**Nature du document.** Ce que l'œuvre doit **montrer**. Aucune méthode, aucun
paramètre, aucune implémentation. Chaque exigence est formulée de façon
**observable à l'œil** et doit pouvoir être jugée sans connaître le code.

**Statut.** Version 1.1, arrêtée le 30 juillet 2026. Reconstitution à partir du document
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
**A8.** Les layers bas montrant des galaxies doivent porter, eux aussi, un
**fond généré de matière filamentaire subtil**, afin de rester visuellement
cohérents avec les layers supérieurs. Une galaxie ne flotte pas sur du vide.
*(Origine : 29/07.)*


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

**B4. Effet fractal.** En descendant dans les niveaux de zoom, on doit retrouver
**une même structure à une échelle très inférieure**. La sous-structure doit
exister à tous les étages.

**B5. Taille des structures fidèle à l'échelle.** Une structure d'une taille
physique donnée doit occuper la place qui lui revient à chaque échelle
d'observation.

**B6. Aucune zone vide.** Sur toute la grille zoom × temps, aucune partie du
cadre affiché ne doit être noire, neutre ou par défaut.

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

**D5. Morphologies variées.** Les galaxies doivent présenter des formes
**variées**. Le réalisme n'est pas l'objectif — à ces échelles on ne les voit
quasiment pas — mais leur **dissolution** doit être juste (cf. C1 à C3).
*(Origine : 28/07.)*

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
pu nous parvenir depuis le Big Bang. Rayon comobile ≈ **14 570 Mpc**, soit
~46,5 milliards d'années-lumière, ~95 milliards de diamètre. C'est l'étendue du
layer `M`.

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

## Traçabilité

Toute exigence ajoutée porte sa **date** et son **origine**. Une exigence n'est
retirée que sur décision explicite de Marc, jamais par omission.

### Historique

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
