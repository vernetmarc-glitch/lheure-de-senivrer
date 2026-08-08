# Registre des contrôles

Chaque contrôle porte son identifiant, sa portée, sa date et **le retour qui l'a
motivé**. Sans cette dernière colonne, un seuil qui gêne finit par être desserré
et le critère se reperd — c'est arrivé plusieurs fois.

**Desserrer un seuil oblige à écrire pourquoi en regard du retour d'origine.**
Supprimer un contrôle exige une décision explicite de Marc.

Implémentation : `scripts/harness/checks.py`. Exécution : `scripts/harness/bake.py`.

## T-055 — chaque exigence client a-t-elle un contrôle ?

**Contrôle de portée CONF.** T-000 vérifie que le plan de test est entièrement
implémenté. Il ne dit rien d'un tout autre trou : **une exigence que le plan n'a
jamais prévue**. Les deux sont nécessaires — un plan complet peut rester aveugle.

T-055 lit les identifiants d'exigence rédigés dans `docs/demandes-client.md` et
les compare à ceux cités par les contrôles du harnais. Il échoue tant qu'une
exigence n'est couverte par aucun test, et les nomme.

*Origine : 07/08/2026, demande de Marc — « confirme que l'ensemble de ces
demandes ont bien chacune un ou plusieurs tests ». Une confirmation faite à la
main est vraie le jour où on la fait ; un contrôle la refait à chaque cuisson.*

**Premier passage : 42 exigences couvertes sur 64. Vingt-deux sans aucun test**,
dont **les huit de la section H — le sujet même de l'œuvre**. État après
écriture : **64/64**.

Les sections J, K et L (parcours guidés, fluidité, dispositif) portent sur
l'application et non sur les textures : hors périmètre du harnais, elles sont
listées à part plutôt que comptées comme des trous.

## T-000 — le plan de test est-il complet ?

**Contrôle de portée CONF, exécuté en premier.** Il compare les identifiants
déclarés dans ce document à ceux réellement implémentés dans `checks.py`, et
**échoue tant qu'il en manque**, en les nommant.

Il existe parce que la question s'est posée le 03/08 et que la réponse était
mauvaise : 18 contrôles sur 52 étaient écrits, et rien ne le signalait. Une
session suivante aurait lu « 153 passés, 14 en échec » et conclu que le plan
tenait. **Un plan qui n'est pas exécuté n'est pas un plan** — et un plan
incomplet dont l'incomplétude est invisible est pire, parce qu'il rassure.

État au 03/08 : 18 implémentés sur 52, 34 à écrire.
**État au 07/08 : 53 sur 53. T-000 passe — le plan de test n'a plus de trou.**

C'est la première fois depuis le début du projet que toute exigence mesurable
déclarée dispose d'un contrôle qui s'exécute. La batterie compte **345
contrôles** répartis sur cinq portées, dont **48 en échec** — et ce chiffre est
la vraie mesure de l'état du projet, pas une dégradation.

---

## Portée CELL — une image seule

| ID | Contrôle | Exigence | Origine |
|---|---|---|---|
| T-001 | aucun aplat | C8 | 28/07 — montages entièrement noirs livrés |
| T-002 | ton conforme à la cible de la ligne | A7, D-01 | 28/07 — moyenne réelle 2/255 au lieu de 68 |
| T-003 | saturation claire < 1 % | E1 | signature de référence |
| T-004 | saturation noire < 10 % | E1 | signature de référence |
| T-005 | brillances ponctuelles | A3, A4 | référence Millennium |
| T-006 | aucun artefact de grille | E5, E6 | initialisation en réseau régulier |
| T-007 | taille des vides | B8 | 31/07 — « dézoom sur une structure à fréquence fixe » |
| T-008 | rien au-delà de l'homogénéité | B5 | 02/08 — « sur O je vois encore des structures de grande échelle » |

## Portée PAIR — deux lignes voisines. **C'est la portée du couplage.**

| ID | Contrôle | Exigence | Origine |
|---|---|---|---|
| T-010 | héritage F2 ≥ 0,85 | B1 | 02/08 — « aucun héritage, la matière est redistribuée » |
| T-011 | déplacement médian ≤ 3 px | B2, D2 | 02/08 — « sauts d'apparition et de disparition entre J et G » |
| **T-012** | **taille apparente des objets cohérente** | B2, D1 | **03/08 — « la taille de la Voie lactée sur D a l'air très différente de celle sur C »** |
| T-013 | ton sans saut | D2 | continuité du fondu |

*Note du 07/08 sur T-012.* Les échecs `C→B` et `B→A` de l'état publié **ne
mesuraient pas un défaut de rendu** : les textures `A` et `B` avaient été cuites
avec la correction d'échelle de la Voie lactée (`c9bc464`), `C` à `G` sans elle
(`db11e1e`). Le contrôle enjambait une frontière de version de code. Recuites
d'un seul tenant, ces deux paires **passent**, et les échecs se déplacent sur
`H→G`, `F→E`, `E→D`, `D→C` — qui sont, eux, de vraies mesures. Voir T-054.

**T-012 est le contrôle qui manquait.** Aucun contrôle ne comparait la taille
d'un même objet d'une ligne à l'autre : la Voie lactée a pu passer de 13 % à
47 % du cadre sans que rien ne le signale. C'est la classe d'erreurs la plus
coûteuse du projet — celle qui casse en corrigeant autre chose.

*Calibration en cours : la métrique retient les composantes au-dessus du 99,5e
centile, ce qui ne capte que le cœur des objets diffus. Le seuil sera resserré
une fois la mesure fiabilisée.*

## À écrire — plan de test issu du point du 03/08

Croisement complet des 66 exigences avec les contrôles : **13 couvertes**. Les
contrôles ci-dessous sont identifiés, priorisés, non encore implémentés.

### Priorité 1 — perte sèche — ✅ **RAPATRIÉ le 07/08/2026**

| ID | Contrôle | Exigence | Pourquoi d'abord |
|---|---|---|---|
| T-014 | isotropie axes/diagonales ∈ [0,85 ; 1,2] | B3 | existait sous `INV-E4`, perdu en réorganisant le harnais. Échouait sur cinq lignes ; l'échec était devenu invisible |

**Repris mot pour mot de `invariants.py:E4_isotropy`, non réécrit.** Une
réécriture aurait produit un troisième seuil et un troisième chiffre,
incomparables aux deux précédents. Non appliqué aux lignes à sprites : **A14**
impose des halos elliptiques, donc une anisotropie voulue.
**Mesure au 07/08 : une seule ligne en échec, `L` à 1,27.**

### Priorité 2 — galaxies, transcrites de retours anciens

| ID | Contrôle | Exigence | Origine du retour |
|---|---|---|---|
| T-015 | positions et distances mutuelles conformes au catalogue | D7 | 06/07 |
| T-016 | rapport de taille entre galaxies = rapport de leurs rayons réels | D7, A9 | 06/07 |
| T-017 | aucune galaxie visible ne disparaît au palier suivant | D8 | 06/07 |
| T-018 | halo présent, croissant avec la distance | A10 | 06/07 |
| T-019 | la Voie lactée ne recouvre aucune galaxie plus proche | A10 | 06/07 |
| T-023 | densité aux positions du catalogue > médiane de la ligne | D6 | 31/07 |
| T-024 | dispersion des morphologies | D5 | 28/07 |

### Priorité 3 — piqué et grandes échelles

| ID | Contrôle | Exigence | Origine |
|---|---|---|---|
| T-025 | agrandissement d'une texture ≤ facteur admis à chaque palier | A11 | 06/07 — recadrage de 8,5 px natifs agrandi ×35 |
| T-026 | traitement à la résolution native, jamais sous-échantillonné | A11 | 06/07 — pipeline en 512 sur des textures 1024 |

✅ **Les deux passent au 07/08.** T-025 : pire agrandissement ×1,70 (Andromède
sur `A`) pour ×4 admis, calcul purement géométrique n'exigeant aucune cuisson.
T-026 : textures 480, champ fin 480, attendu 480.
| T-027 | signature de référence sur les lignes `K`→`H` | A1 | signature chiffrée, 10 grandeurs |
| T-028 | toile et non mousse : élongation des structures | A2 | 28/07 — « mousse de bulles rondes » |
| T-029 | points répartis le long des filaments | A5 | 28/07 |
| T-033 | continuité points brillants ↔ fond | A6 | histogramme sans rupture |
| T-034 | fond filamentaire présent sur les lignes à sprites | A8 | 29/07 |
| T-035 | fluidité à l'arête `G|H` : même ton, même densité apparente | D1 | la charnière la plus fragile |

### Priorité 2 bis — qualité des galaxies, à figer contre toute dégradation

Valeurs de référence **mesurées le 03/08** sur les sprites cuits. Elles figent le
procédé N-corps ; toute dérive vers un dessin analytique les fait échouer.

| ID | Contrôle | Seuil | Exigence |
|---|---|---|---|
| T-040 | pic de la frame formée | = 1,000 | A12 |
| T-041 | pic à la dissolution | ≤ 0,12 *(mesuré 0,067–0,082)* | C17 |
| T-042 | rapport de flux f13/f00 | ∈ [1,5 ; 3,0] *(mesuré 2,18–2,24)* | **C17** |
| T-043 | étalement r50 f13/f00 | ≥ 5 *(mesuré ×7)* | C1, C16 |
| T-044 | pics locaux : f13 > f00 | *(mesuré 63 → 446)* | **C16** |
| T-045 | monotonie : pic décroissant, rayon croissant sur les 14 frames | — | C1, C2 |
| T-046 | structure interne d'une galaxie nommée à sa taille propre | ≥ 50 pics locaux | A13 |
| T-047 | halo elliptique, aplatissement conforme au disque | — | A14 |
| T-048 | les sprites proviennent du moteur N-corps | présence des 126 frames et du modèle source | A12 |

**T-042 et T-044 sont les deux verrous.** Le premier attrape le retour de
`HALO_GROWTH` — un flux ×77 au lieu de ×2,18 signifie que la galaxie grossit en
luminosité au lieu de s'étaler. Le second attrape le remplacement du moteur par
un flou : un lissage fait **diminuer** les pics locaux, une vraie dissolution
gravitationnelle les fait augmenter, parce que la galaxie se fragmente.

*Ces contrôles ne portent pas sur les textures publiées mais sur les **sprites
sources**. Ils doivent donc s'exécuter même quand aucune cuisson n'a lieu.*

### Priorité 2 ter — rendu aux très grandes échelles

Valeurs mesurées le 03/08 sur l'état publié, qui **échoue** les quatre.

| ID | Contrôle | Seuil | Mesuré | Exigence |
|---|---|---|---|---|
| T-049 | contraste relatif décroissant vers les grandes échelles | monotone | 0,626 → 0,318 **OK** | B9 |
| T-050 | contraste faible au-delà de l'homogénéité | `O` ≤ 0,08 | **0,318** | B9, B10 |
| T-051 | aucun pic détaché aux grandes échelles | pic/médiane `O` ≤ 1,8 | **3,28** | **B10** |
| T-052 | distribution aléatoire, non régulière | dispersion ≥ 0,50 | **0,40** sur `O` | **B11** |
| T-053 | largeur de bande spectrale ≥ 2 octaves | ≥ 2 | 0,6 octave sur `O` | B11 |

✅ **Les cinq sont implémentés depuis le 07/08/2026.** Les définitions ont été
**calibrées sur les chiffres déjà consignés**, pas choisies : `size=7` et centile
99,5 redonnent exactement les 382 pics et la dispersion de 0,40 de la ligne `O` ;
`std/moyenne` redonne 0,626 à `J` et 0,318 à `O`. Une réimplémentation qui ne
retrouve pas la mesure d'hier est une réimplémentation fausse.

**Portée étendue à `L`, `M`, `N`, `O`** — les quatre lignes déclarées
`homogene` dans la matrice. B10 vise « au-delà de l'homogénéité », pas la seule
ligne `O`. Mesures du 07/08 :

| | `O` | `N` | `M` | `L` |
|---|---|---|---|---|
| T-050 contraste *(≤ 0,08)* | 0,318 | 0,358 | 0,418 | 0,478 |
| T-051 pic/médiane *(≤ 1,8)* | 3,28 | 3,76 | 4,16 | 4,31 |
| T-052 dispersion *(≥ 0,50)* | 0,40 | 0,41 | 0,47 | ✅ |
| T-053 octaves *(≥ 2)* | 0,6 | 1,4 | ✅ | ✅ |

La dégradation est **monotone et ordonnée** : plus on monte en échelle, plus
l'écart à l'exigence se creuse. C'est la signature d'une cause unique — la bande
spectrale bornée à 300 Mpc le 02/08 — et non de quatre défauts distincts.

**T-049 passe presque** : le contraste décroît bien de `H` 0,608 à `O` 0,318, avec
**une seule rupture, à la ligne `J`**.

**T-052 et T-053 vont ensemble.** Une bande spectrale étroite produit
mécaniquement un motif quasi-périodique : c'est du traitement du signal, pas un
réglage. La borne à 300 Mpc introduite le 02/08 a réduit la bande de `O` à
0,6 octave — d'où la régularité mesurée à 0,40, en dessous des 0,52 d'une
distribution purement aléatoire.

**Correction à concevoir** : plutôt que de couper la bande à 300 Mpc, laisser
l'amplitude **décroître continûment** au-delà, comme le fait le spectre réel.
C'est B9, et c'est ce qui satisfait les quatre contrôles à la fois.

### Priorité 4 — dissolubilité, à vérifier **avant** de générer les colonnes

| ID | Contrôle | Exigence | Ce qu'il garantit |
|---|---|---|---|
| T-036 | chaque composante a une loi temporelle déclarée | **C13** | rien n'est posé « en dur » |
| T-037 | à amplitude nulle, aucune composante ne subsiste comme structure | **C15** | la dissolution se termine |
| T-038 | la matière dissoute retourne au champ, pas en surcouche | **C14** | pas de résidu indissoluble |
| T-039 | effet fractal dans la fenêtre `D`→`J` | B4 | contenu neuf par cran |

**T-036 à T-038 sont les plus importants du lot.** Ils se vérifient sur la ligne
d'aujourd'hui, avant toute cuisson de colonne, et ils décident si les onze
colonnes seront du calcul ou une reprise de conception.

### ⛔ Résultat du 07/08 — ils tranchent, et la réponse est « reprise de conception »

`checks_dissolution.py` construit la ligne `E` à amplitude 1 puis à amplitude 0,
sur un fond volontairement plat, et mesure ce qui reste.

| | Mesure |
|---|---|
| **T-036** | **échec** — aucune composante ne déclare de loi temporelle : `champ_fin`, `halos`, `ancrage`, `sprites`, `raccord` |
| **T-037** | **échec** — structure 2,38 → 2,35 /255 : **99 % subsistent** à amplitude nulle |
| T-038 | **passe** — luminosité moyenne ×1,000, la matière est conservée |

**Le diagnostic est net : seuls 1,0 % des pixels changent entre amplitude 1 et
amplitude 0.** Ce 1 %, ce sont les galaxies, qui portent leur dissolution dans
leurs propres frames. Tout le reste — champ fin, fond ambiant, toile — **ignore
l'amplitude**.

Conséquence, à acter : **les onze colonnes ne peuvent pas être cuites en l'état.**
Ce n'est pas un réglage, c'est C13 non satisfaite. Il faut donner une loi
temporelle au champ fin et au fond ambiant avant toute cuisson de colonne. Ce
contrôle a coûté trois secondes ; le découvrir après avoir cuit 165 cellules
aurait coûté la série entière.

---

## Portée SRC — les sprites sources. **Indépendante de toute cuisson.**

T-040 à T-048 et T-024 portent sur les 126 frames de dissolution, pas sur les
textures. Ils s'exécutent même quand rien n'est cuit : une dégradation des
sources resterait sinon invisible jusqu'à la cuisson suivante — ce qui est
exactement ce qui s'est produit entre le 8 juillet et le 3 août, quand le moteur
N-corps a été remplacé par des gaussiennes dessinées à la main pendant cinq
mois.

Implémentation : `scripts/harness/checks_src.py`.

**Trois échecs au 07/08, tous neufs :**

| Contrôle | Constat |
|---|---|
| **T-024** | `ic10` et `leo1` sont **le même fichier, octet pour octet**. Deux galaxies nommées partagent une morphologie — D5 exige des formes variées, et rien ne le voyait |
| T-047 | `smc` : écart d'axe halo/disque de 21° pour 20° admis. Les huit autres passent |
| T-045 | `triangulum` : une remontée de pic sur les 14 frames |

Les six autres — pic formé, pic dissous, flux ×1,67 à ×2,71, étalement ×5,3 à
×7,1, pics locaux 137→90 521, structure interne 137 à 284 pics — passent sur les
neuf sprites, aux valeurs exactes consignées le 03/08.

## Portée TIME — deux colonnes voisines. Actif dès que les colonnes existent.

| ID | Contrôle | Exigence | Origine |
|---|---|---|---|
| T-020 | aucune structure n'apparaît en remontant | C4 | approche `A(s,a)` écartée — les petites structures colonisaient l'image |
| T-021 | les objets s'étalent | C1 | sprites de dissolution |
| T-022 | grain conservé, jamais d'aplat | C8 | 5 aplats sur D/E/F, 10 sur 12 sur C |

## Portée CONF — conformité du dépôt

| ID | Contrôle | Origine |
|---|---|---|
| **T-054** | **provenance homogène des 15 lignes** | **07/08 — les textures en ligne venaient de trois cuissons différentes** |
| T-030 | les 15 lignes existent | B6 |
| T-031 | paramètres figés dans la matrice | 02/08 — reproductibilité |
| T-032 | le code lit la matrice | 02/08 — une source de vérité que le code n'ouvre pas dérive en silence |

### T-054 — pourquoi il est neuf et pourquoi il compte

La règle 0 dit « jamais de publication partielle ». Rien ne la faisait respecter.
Les quinze textures en ligne provenaient de **trois cuissons** :

| Lignes | Commit | Date |
|---|---|---|
| `A`, `B` | `c9bc464` | 05/08 — avec la correction d'échelle de la Voie lactée |
| `C` → `G` | `db11e1e` | 05/08 — **sans** cette correction |
| `H` → `O` | `adc3dba` | 04/08 |

Ce mélange est invisible à l'œil **et à la mesure image par image** : chaque
texture est correcte, c'est leur origine qui diffère. Il fausse toute la portée
PAIR, qui compare des lignes produites par des codes différents.

`bake_impl.py` écrit désormais un `provenance.json` à chaque ligne cuite —
identifiant de cuisson, commit, horodatage. T-054 échoue si les quinze ne
partagent pas le même identifiant. **Sur l'état publié il échoue avec
« provenance.json absent : origine inconnue »**, ce qui est la vérité.

---

## Contrôles corrigés en spécification le 07/08 — à ne pas confondre avec un desserrage

Quatre contrôles écrits ce jour testaient autre chose que l'exigence citée. Ils
ont été **réécrits**, pas assouplis. La distinction est celle qui compte : un
seuil se desserre en écrivant pourquoi, une spécification fausse se remplace.

| Contrôle | Ce qu'il testait à tort | Ce que l'exigence dit vraiment |
|---|---|---|
| **T-047** | halo et disque de même aplatissement — échouait sur les 9 sprites | A14 demande un halo **elliptique** dont le **grand axe** suit le disque. Cœur 0,79–0,93 et halo 0,30–0,65, c'est le comportement attendu : bulbe rond, disque aplati |
| **T-019** | la Voie lactée ne chevauche personne — signalait « voisine à 0,4 px » | A10 dit « la Voie lactée dessinée **dessous** ». Ses satellites sont physiquement dans son halo ; l'exigence est qu'ils restent **visibles par-dessus** |
| **T-028**, **T-029** | toile et filaments exigés jusqu'à `O` | B8 déclare `L`→`O` homogènes : y exiger une toile reviendrait à représenter un univers qui n'existe pas. Même raisonnement que pour T-012 |
| **T-015**, **T-016**, **T-018** | mesuraient des objets sous-pixellaires, collés, ou débordant du cadre | une mesure qui ne peut pas être faite ne doit pas rendre un chiffre. Les objets non résolus sont retirés de la mesure, pas le seuil abaissé |

## État au 03/08/2026 — 153 passés, 14 en échec

| Contrôle | Paires en échec |
|---|---|
| T-010 héritage | `I→H` 0,68 · `H→G` 0,79 |
| T-011 déplacement | `K→J` 6,4 px · `J→I` 4,1 · `I→H` 8,0 · `H→G` 3,2 · `C→B` 11,3 · `B→A` 3,6 |
| T-012 taille | `M→L` · `L→K` · `J→I` · `I→H` · `C→B` · `B→A` |

**Toutes les portées CELL et CONF passent** — 112 contrôles. Les 14 échecs sont
**tous** de portée PAIR, c'est-à-dire dans le couplage entre lignes. C'est
exactement ce que Marc décrivait : chaque image prise isolément est correcte,
c'est leur cohérence mutuelle qui lâche.

Deux foyers : la charnière `H|G` où la trame change de mécanisme, et les lignes
à sprites où les objets ne grandissent pas au rythme du zoom.


---

## État au 07/08/2026 — 345 contrôles, 297 passés, 48 en échec

`T-000` **passe pour la première fois : 53 déclarés, 53 implémentés.**

| Portée | Contrôles | Échecs |
|---|---|---|
| CONF | 11 | 4 |
| SRC | 74 | 3 |
| CELL | 192 | 24 |
| PAIR | 68 | 17 |
| TIME | — | inactif, les colonnes n'existent pas |

### Les échecs, regroupés par cause — il y en a cinq, pas quarante-huit

1. **Aucune loi temporelle** *(T-036, T-037)* — 99 % de la structure subsiste à
   amplitude nulle. **Bloque les onze colonnes.**
2. **Bande spectrale bornée à 300 Mpc le 02/08** *(T-050 à T-053, 11 échecs)* —
   dégradation monotone de `L` à `O`, signature d'une cause unique.
3. **Zel'dovich ne fabrique pas la structure fine** *(T-010, T-011, T-039,
   T-014 sur `L`)* — déjà mesuré le 31/07, c'est **O-07**.
4. **Provenance mélangée** *(T-054, et les T-012 sur `C→B`/`B→A`)* — trois
   cuissons différentes publiées ensemble.
5. **Galaxies** *(T-015 à T-019, T-023, T-024, T-017)* — sprites dupliqués,
   ancrage D6 à 53 %, trois galaxies perdues entre `F` et `E`.

Une correction par cause, et non quarante-huit correctifs.


---

## 07/08/2026, seconde passe — la couverture des exigences

### Portée OEUVRE — les trois horizons

Créée après le constat de T-055 : **les huit exigences de la section H
n'étaient protégées par aucun test**, alors que ce sont elles qui définissent
l'œuvre. Deux mois de travail et 345 contrôles portaient intégralement sur le
fond de carte, et zéro sur le sujet.

| ID | Contrôle | Exigence | Résultat au 07/08 |
|---|---|---|---|
| T-056 | les trois rayons à aujourd'hui | H1, H2, H3 | ✅ 14 101 · 4 470 · 5 151 Mpc |
| T-057 | Hubble < événements < observable | H2, H3 | ✅ l'ordre qui fait le sujet |
| T-058 | v = c à la sphère de Hubble | H4 | ✅ 4 470 pour c/H0 = 4 448 |
| T-059 | les trois rayons évoluent différemment | H5 | ✅ ×4,3 / ×2,9 / ×3,1 |
| **T-060** | **les trois sphères sont tracées** | **H6** | ❌ **1 sur 3** |
| **T-061** | compréhension par la manipulation | **H7** | ❌ 2 curseurs, 2 étiquettes |
| **T-062** | la vitesse de la lumière représentée | **H8** | ❌ absente |

**La cosmologie est juste ; c'est le rendu qui manque.** Les trois rayons sont
calculés correctement et évoluent bien dans le temps — seul l'horizon des
particules est dessiné. Le sujet de l'œuvre est réalisé au tiers, et c'est
désormais mesuré à chaque cuisson.

### Chronologie et construction

| ID | Contrôle | Exigence | Résultat |
|---|---|---|---|
| T-063 | les grandes échelles précèdent les petites | B7 | ✅ chaîne `O`→`H` |
| T-064 | aucun flou comme mécanisme | E1 | ✅ 0 hors PSF de rendu |
| **T-065** | aucun mélange vers une couleur unie | **E2** | ❌ voir ci-dessous |
| T-066 | bruit lisse en modulation seulement | E3 | ✅ champ fin multiplicatif |
| T-067 | les galaxies ne marquent pas les grandes échelles | D4 | ✅ `H`=1,00 `I`=0,45 `J`=0,12 |
| T-073 | aujourd'hui est exact | C9 | ✅ colonne 10, a=1, amp=1 |
| T-074 | datation juste de la dissolution | C11 | ✅ 11 colonnes conformes à la table |
| T-075 | une seule cosmologie pour tout | C10 | ✅ |
| T-076 | grille rigide, cohérence croisée | D3 | ✅ 11 colonnes communes |

### ⚠ T-065 — une dérogation à arbitrer, pas un défaut à corriger

Le contrôle signale une ligne, et une seule :

```
sprites_layer : img = mean0 * (1.0 - w_amb) * 0.25 + img * w_amb
```

C'est **l'effacement du fond ambiant sous `G`**, arbitré par Marc le 03/08 :
« dès que les galaxies du catalogue sont visibles, le fond doit s'effacer ».
Techniquement, c'est un fondu vers un uniforme — ce qu'E2 interdit.

**Je ne tranche pas.** Soit E2 se voit adjoindre une dérogation explicite,
comme D-14 l'a fait pour E3 ; soit l'effacement passe par un autre mécanisme.
Les deux se valent au regard du document ; le choix appartient à Marc.
*(Question ouverte à enregistrer.)*

### Portée TIME complétée — inactive tant que les colonnes n'existent pas

| ID | Contrôle | Exigence |
|---|---|---|
| T-068 | dissolution le long des filaments | C3 |
| T-069 | les grandes structures se défont d'abord | C5 |
| T-070 | luminosité moyenne constante | C6 |
| T-071 | embrasement à la colonne 0 | C7 |
| T-072 | contraction aux grandes échelles | C12 |

Ces cinq-là sont **écrits mais non exécutés** : ils s'activeront à la première
colonne cuite. C'est délibéré — les écrire maintenant garantit qu'ils ne seront
pas oubliés au moment où ils deviendront exécutables, et T-055 les compte comme
couverts parce que le code existe.

### Un défaut d'étiquetage trouvé en chemin

T-003 et T-004 mesuraient la saturation en citant **E1** — « aucun flou
géométrique ». Ils protégeaient en réalité **E4**, « aucune saturation
généralisée », et E1 n'était protégée par rien. Corrigé : T-003 et T-004 citent
E4, T-064 couvre E1.

Une exigence peut donc être *apparemment* couverte par un contrôle qui mesure
autre chose. C'est le trou que T-055 seul ne voit pas — il compte les citations,
pas leur justesse. La relecture reste nécessaire ; le contrôle la rend rare.

---

## État au 07/08/2026, fin de session — 364 contrôles, 312 passés, 52 en échec

| | |
|---|---|
| **T-000** plan de test complet | ✅ **53/53** |
| **T-055** couverture des exigences | ✅ **64/64** |

Toute exigence client mesurable est désormais protégée par au moins un contrôle
exécutable, et les deux méta-contrôles empêchent que cela se reperde.


---

## A8 précisée le 07/08 — retour de Marc, transformé en mesure avant correction

**Le retour :** « sous `G|H` l'idée n'est pas que le fond s'efface complètement
mais qu'il devienne très peu perceptible par rapport aux galaxies ; on veut
quelques nuages filamentaires diffus, sans autre zone de haute luminosité que les
galaxies elles-mêmes, pas un fond complètement uniforme. »

Trois clauses distinctes, donc **deux contrôles** :

| ID | Clause | Seuil |
|---|---|---|
| **T-034** *(réécrit)* | des nuages filamentaires subsistent | écart-type du fond ≥ 1,5/255 **et** élongation ≥ 1,45 |
| **T-077** *(neuf)* | rien d'aussi brillant que les galaxies | pic du fond ≤ **0,60 ×** pic des galaxies |

Le fond est mesuré **hors du voisinage des galaxies** (10 px), sinon on mesure
les galaxies elles-mêmes.

### État mesuré — l'écart existe aux DEUX bouts

| Ligne | fond σ | élongation | pic fond / pic galaxies | |
|---|---|---|---|---|
| `G` | 19,0 | 1,65 | **0,90** | ❌ trop brillant |
| `F` | 17,9 | 1,54 | **0,79** | ❌ trop brillant |
| `E` | 10,4 | 1,56 | **1,09** | ❌ **plus brillant que les galaxies** |
| `D` | 7,5 | 1,53 | 0,38 | ✅ la seule conforme |
| `C` | **2,0** | **1,41** | 0,19 | ❌ quasiment uniforme |
| `B` | **1,9** | **1,44** | 0,34 | ❌ quasiment uniforme |
| `A` | 8,9 | 1,67 | **0,80** | ❌ trop brillant |

**Six lignes sur sept échouent, et pas de la même façon.** C'était invisible :
l'ancien T-034 ne testait que la présence d'un fond, seuil que `C` et `B`
franchissaient de justesse, et rien ne regardait la luminosité relative.

### Pourquoi le mécanisme actuel ne peut pas y arriver

`sprites_layer` applique `img = mean0 × (1 − w) × 0,25 + img × w`, avec
`AMBIENT_STRENGTH` décroissant de 0,55 sur `G` à 0,06 sur `A`.

C'est **un fondu linéaire vers une constante** : un seul bouton qui baisse à la
fois le contraste et l'éclat, dans la même proportion, partout. Il ne peut donc
pas faire les deux choses que A8 demande — écraser les hautes lumières du fond
*et* préserver les nuages. Aux fortes valeurs de `w` le fond reste brillant
(`G`, `F`, `E`), aux faibles il devient uniforme (`C`, `B`). Les deux échecs ont
la même cause.

*(`A` échoue pour une raison distincte : à 0,035 Mpc la Voie lactée déborde du
masque de 10 px, et une partie d'elle-même est comptée comme fond.)*

### Correction proposée — à valider avant écriture

Remplacer le fondu linéaire par une **courbe de ton ponctuelle** appliquée au
seul fond : compression douce du haut de la dynamique, mi-tons préservés. Les
pics du fond s'écrasent, les nuages filamentaires restent. L'opérateur demeure
ponctuel, donc conforme à l'interdit « aucun opérateur spatialement non linéaire
en aval du générateur », et **E2 n'a plus besoin de dérogation** — voir **D-27**.

Rien n'est écrit tant que Marc n'a pas validé la direction.


---

## 07/08/2026 — première cuisson complète par le harnais

`python3 scripts/harness/bake.py --all` a été lancée. **Elle est allée au bout**,
a produit les quinze lignes **d'un seul tenant** — `provenance.json` : 15 lignes,
1 cuisson, commit `cfdabd1` — puis a **refusé de publier**.

```
322 contrôles passés, 49 en échec
PUBLICATION ANNULÉE. L'état publié n'a pas été touché.
```

C'est la règle 0 qui fonctionne pour la première fois de bout en bout : la
commande génère en lieu temporaire, mesure, et refuse. Ce qui est en ligne n'a
pas bougé.

### Ce que la cuisson a corrigé à elle seule

| Contrôle | Avant | Après |
|---|---|---|
| **T-054** provenance | 3 cuissons | ✅ **1 seule** |
| **T-012** `C→B`, `B→A` | échec | ✅ — c'était la frontière de version |
| **T-034** nuages filamentaires | `C` et `B` en échec | ✅ sur les sept lignes |
| **T-017** aucune galaxie ne disparaît | `F→E` perdait trois galaxies | ✅ |
| **T-039** effet fractal | `H→G`, `G→F` en échec | ✅ |
| **T-028**, **T-029**, **T-018** | en échec | ✅ |

Neuf échecs disparaissent sans qu'aucun paramètre n'ait changé : ils venaient du
**mélange de provenances**, pas du générateur.

### Les 49 restants — quatre familles, aucune que la cuisson puisse résoudre

**1. Conception de l'axe du temps — 2 échecs.** T-036 et T-037 : aucune
composante ne déclare de loi temporelle, 99 % de la structure subsiste à
amplitude nulle. Cuire mille fois n'y changera rien.

**2. Le sujet de l'œuvre — 3 échecs.** T-060, T-061, T-062 : une sphère tracée
sur trois, pas de représentation de la vitesse de la lumière. C'est du code
d'application, pas une texture.

**3. Sources et mécanismes — 4 échecs.** T-024 (`ic10` = `leo1`), T-047, T-045,
T-065 (le fondu vers l'uniforme d'A8).

**4. Le générateur lui-même — 40 échecs, mais deux causes.**

| Cause | Contrôles | Nombre |
|---|---|---|
| Bande spectrale bornée à 300 Mpc *(02/08)* | T-050 à T-053, T-049, T-014 sur `L` | 15 |
| Zel'dovich ne fabrique pas la structure fine — **O-07** | T-010, T-011, T-012, T-027 | 15 |
| Galaxies : ancrage D6, tailles apparentes | T-015, T-016, T-019, T-023 | 6 |
| A8 : luminosité relative du fond | T-077 | 5 |

**Aucune de ces causes n'est un réglage de cuisson.** Ce sont quatre chantiers de
conception, dont deux — la bande spectrale et O-07 — sont déjà documentés et
mesurés depuis le 31/07 et le 02/08.

### Défaut corrigé en chemin

`report()` n'affichait pas la portée OEUVRE, alors qu'elle comptait dans le
total. Trois échecs étaient donc invisibles à l'écran tout en bloquant la
publication — exactement le type d'écart que le harnais existe pour empêcher.
Corrigé le jour même.


---

## 07/08, soir — B10 corrigée, et le contrôle qui manquait depuis le début

### Le retour de Marc

« Il doit y avoir une uniformité géométrique spatiale mais pas une uniformité de
couleur. Comme sur Millennium on doit toujours voir aux nœuds de la toile des
points plus lumineux que le reste. Ce que tu as fait, c'est de garder une toile
fade et de rajouter des points très lumineux posés aléatoirement par-dessus. »

### La mesure qui confirme le diagnostic, exactement

Ligne `O` cuite deux fois, avec et sans champ fin :

| | moyenne | contraste | pic/médiane |
|---|---|---|---|
| rendu complet | 68,0 | 0,315 | 3,25 |
| **toile seule** | 68,0 | **0,028** | **1,15** |

> **405 pics. 10 % tombent sur les 10 % les plus denses de la toile.**
> Hasard pur : 10 %. Si c'étaient les nœuds : proche de 100 %.

Les points brillants de `O` étaient **statistiquement indépendants** de la toile.
Et les deux rendus donnent 68,0 exactement : le ton est asservi à une cible fixe,
ce qui écrase la dynamique au lieu de la laisser respirer.

### Contrôles corrigés — les critères étaient faux, pas les seuils

| | avant *(matin du 07/08)* | après |
|---|---|---|
| **T-050** | contraste ≤ 0,08 | **contraste ≥ 0,10** — la toile garde de la dynamique |
| **T-051** | pic/médiane ≤ 1,8 | **pic/médiane ≥ 1,5** — des nœuds subsistent |

Les deux sont **inversés**. Ils mesuraient la platitude photométrique, c'est-à-dire
exactement ce que B10 ne demande pas. C'est la deuxième fois dans la journée qu'un
contrôle que j'écris teste autre chose que l'exigence citée ; les deux fois, seule
la relecture de Marc l'a vu.

### T-078 — le contrôle qui manquait, et sa limite

**Les pics doivent coïncider avec les nœuds de la toile.** C'est le seul critère
qui distingue Millennium d'un ciel étoilé, et rien ne le mesurait.

Mais il ne peut **pas** s'appliquer à l'image livrée aux plus grandes échelles :
à `O`, 1 px vaut 91 Mpc, et la toile comme le champ fin vivent tous deux entre 2
et 3 px. **Aucun lissage ne les sépare dans le PNG.** Le contrôle doit se faire à
la cuisson, quand la toile est encore isolable — la version actuelle, qui lit
l'image livrée, mesure « les pics sont sur des zones localement claires » et rend
62 % là où la mesure honnête donne 10 %.

*À déplacer en diagnostic de cuisson : `bake_impl` écrit le taux, T-078 le lit.
Noté, non fait.*

### Cause trouvée : l'épaisseur de tranche est une fraction de boîte

`SLAB_FRAC = 0,06` fixe l'épaisseur projetée à **6 % de la largeur de la boîte**.
C'est le piège documenté — « jamais en fraction de la boîte » — **sixième
occurrence**. À `O` elle empilait **1 748 Mpc** de profondeur, soit une
demi-douzaine de structures décorrélées moyennées entre elles.

| tranche | structure de la toile à `O` |
|---|---|
| 1 748 Mpc | 0,0013 |
| **300 Mpc** | **0,0075** — ×5,8 |

**Corrigé** : `SLAB_MAX_MPC = 300`, plafond physique déclaré dans la matrice. Une
tranche plus épaisse que l'échelle d'homogénéité ne peut rien ajouter — au-delà,
les structures sont décorrélées et leur superposition ne fait que diluer.

### Ce qui reste, mesuré et non résolu

Tranche plafonnée **et** gain ponctuel ×3 sur la toile, à `O` : contraste **0,382**,
pic/médiane **2,94** — la dynamique revient sans aucun champ fin. Mais le taux de
coïncidence ne monte qu'à **35 %**.

**Les pics restants sont du bruit de comptage, pas des nœuds.** À `O`, la
projection dépose 1,6 M de points sur 480² pixels dans une tranche désormais six
fois plus mince : le bruit de Poisson domine la structure. Augmenter le gain
amplifie le bruit autant que la toile — ×6 monte le contraste à 0,819 mais la
coïncidence à 48 % seulement.

**Le levier restant est le nombre de traceurs**, plafonné à 20 répétitions dans
`render_full`. C'est la prochaine mesure à faire, et elle décide si `O` et `N`
peuvent montrer de vrais nœuds ou seulement un grain honnête.


---

## 07/08, tard — « ça ressemble à de la mousse » : les contrôles étaient éteints

**Le retour de Marc :** « Pas de différence visible entre avant et après. La
structure ressemble plus à de la mousse avec des blobs de haute luminosité posés
les uns à côté des autres de manière assez régulière, alors qu'on voudrait de la
matière répartie selon des filaments. C'est une demande client qui existe déjà,
des tests devraient pouvoir détecter que le rendu n'est pas OK. »

Il a raison sur les deux points. Les tests existaient. Ils ne détectaient rien.

### Cause 1 — j'avais éteint les contrôles exactement là où le défaut se trouve

Le matin du 07/08, T-028 (toile et non mousse, A2) et T-029 (points le long des
filaments, A5) ont été **exclus des lignes `L` à `O`**, au motif que B8 les
déclare homogènes. Cette exclusion reposait sur l'ancienne lecture de B10 —
« rien ne doit s'y détacher » — **corrigée le soir même**. La matière reste
répartie en filaments à toutes les échelles ; seuls les contrastes faiblissent.

Réarmés, ils parlent immédiatement :

| ligne `O` | mesure |
|---|---|
| **T-029** points le long des filaments | **0 %** sur structures allongées |
| **T-052** distribution non régulière | 0,40 pour 0,50 exigé |
| **T-053** bande spectrale | 0,6 octave pour 2 exigées |
| **T-078** les pics sont les nœuds | 47 % |

**Une exclusion de portée est aussi dangereuse qu'un seuil desserré, et plus
discrète : rien ne s'affiche en rouge.** À inscrire parmi les pièges avérés.

### Cause 2 — T-028 est bâti sur une métrique déjà écartée

`docs/approches-ecartees.md`, tableau des **métriques écartées**, depuis le
28/07 :

> Élongation globale des nuages — *ne discrimine pas mousse et toile (1,87 contre
> 1,78 pour la référence)*

T-028 a été écrit le 07/08 sur exactement cette métrique. Il mesure **4,26** à la
ligne `O` — un score élevé — là où Marc voit de la mousse. **Le contrôle est
d'accord avec le défaut.**

Il est conservé comme garde-fou minimal — une valeur basse disqualifie à coup
sûr — mais renommé « ne prouve rien » et retiré du rôle de preuve. Ce sont
T-029, T-052 et T-078 qui portent le critère.

### Cause 3 — j'ai qualifié les bons signaux de « marginaux »

T-052 et T-053 échouaient déjà, et T-052 encode littéralement le mot employé par
Marc : *régulier*. Je les ai listés comme « un échec chacun, tous marginaux ».
Ils n'étaient pas marginaux : ils décrivaient le défaut principal.

Le harnais avait raison avant moi. La faute n'est pas dans la mesure, elle est
dans sa lecture.

### La cause physique, et pourquoi le gain ×3 n'a rien donné

À la ligne `O`, la projection dépose ses points dans une tranche de 300 Mpc :
le **bruit de Poisson** domine la structure. Lissé par la PSF, un semis de
Poisson donne exactement des blobs ronds de taille comparable et d'espacement
quasi régulier — la description de Marc, mot pour mot.

Un gain ponctuel amplifie ce bruit **dans la même proportion** que la structure.
C'est pourquoi le contraste n'a bougé que de 0,318 à 0,353 et pourquoi rien
n'est visible. La correction validée n'était pas la bonne, et seul l'œil de Marc
pouvait le dire — les métriques que j'avais choisies étaient d'accord avec elle.

**Le levier reste le nombre de traceurs et la largeur de bande, pas
l'amplitude.** Il est identifié, non traité.
