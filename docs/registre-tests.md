# Registre des contrôles

Chaque contrôle porte son identifiant, sa portée, sa date et **le retour qui l'a
motivé**. Sans cette dernière colonne, un seuil qui gêne finit par être desserré
et le critère se reperd — c'est arrivé plusieurs fois.

**Desserrer un seuil oblige à écrire pourquoi en regard du retour d'origine.**
Supprimer un contrôle exige une décision explicite de Marc.

Implémentation : `scripts/harness/checks.py`. Exécution : `scripts/harness/bake.py`.

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
