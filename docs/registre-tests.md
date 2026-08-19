> ⚠️ **Ce registre est CHRONOLOGIQUE et contient des seuils périmés.**
> Lire d'abord **`docs/etat-des-lieux.md`**, qui tranche les contradictions.
> T-050, T-051, T-047, T-019 et T-028 ont été **inversés ou requalifiés** le
> 07/08 : les sections antérieures les décrivent encore dans leur ancienne
> version.

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

---

## 08/08/2026 — T-012 mis au banc, et le banc devient un contrôle

### Le verdict porté sur T-012

**Retour de Marc protégé :** 03/08 — « la Voie lactée passe de 13 % à 47 % du
cadre entre deux lignes ». L'exigence est juste ; c'est la mesure qui ne l'était
pas.

L'ancien T-012 comparait `_bright_extent`, le rayon médian des composantes
connexes au-dessus du 99,5ᵉ centile. Mis au banc (`scripts/dev/diag_t012.py`) :
on lui présente un enfant **synthétique**, égal au parent recadré ×2,520 et
agrandi — donc une croissance apparente **exacte** de ×2,520, sans aucun objet
nouveau. La réponse juste est **1,00**.

| paires | réponse | verdict |
|---|---|---|
| `O`→`N` | nan | aveugle |
| `N`→`M` … `H`→`G` | 0,43 – 0,59 | aveugle |
| `G`→`F`, `F`→`E` | 0,89 · 0,99 | ok |
| `E`→`D` … `B`→`A` | 0,04 – 0,39 | aveugle |

**Douze paires sur quatorze.** Cause : sur `N`→`G` les composantes retenues ont
un rayon médian de **1,1 à 1,5 pixel** — c'est le grain, dont la taille suit la
PSF **en pixels** et non le mégaparsec (piège des unités, cinquième occurrence).
Sur `E`, `D`, `C`, `B`, la médiane portait sur **2 à 4 composantes**.

**Ses huit échecs bloquants ne prouvaient rien.**

Deux remplaçants globaux ont été mis au même banc — barycentre spectral et
autocorrélation à mi-hauteur, après mise en fenêtre commune. Tous deux laissent
passer un enfant qui **n'a pas du tout grandi**, dans 7 à 12 cas sur 14. La
raison est de fond : sur `O`→`H` il n'y a pas d'objets, il y a un champ continu,
et « la taille apparente des objets » n'y a **pas de référent mesurable**. Ce
qui y est exigible est déjà tenu par T-010 (héritage) et T-011 (déplacement).

**Décision (Marc, 08/08) :** T-012 quitte la portée PAIR globale et renaît sur
les lignes à sprites, **mesuré objet par objet contre le catalogue** — la même
galaxie, retrouvée par son nom dans les deux lignes, doit voir son étendue
apparente multipliée par le rapport des demi-champs. La fenêtre de mesure suit
l'objet ; un rayon fixe en pixels écrêterait l'enfant et fabriquerait lui-même
l'échec qu'il prétend détecter.

### T-079 — un contrôle répond-il juste à une vérité connue ?

**Ce qu'il protège :** la leçon du §7 de l'état des lieux — « le harnais
garantit qu'un critère est **exécuté** ; il ne garantit ni qu'il est **juste**,
ni qu'il est appliqué là où il faut ». Quatre contrôles faux le 07/08, un
cinquième le 08/08 : cinq fois, c'est la relecture de Marc qui a vu, jamais le
harnais.

Le banc fabrique deux paires dont la réponse est **connue d'avance** :

- **témoin positif** — enfant = parent zoomé ×(rapport des demi-champs). Tous
  les objets ont grandi au rythme exact du zoom. T-012 **doit passer**.
- **témoin négatif** — enfant = parent inchangé. Aucun objet n'a grandi.
  T-012 **doit échouer**.

Un contrôle qui rate l'un des deux ne mesure pas ce qu'il annonce, et ses échecs
comme ses succès sont sans valeur. Le banc tourne **avant** les portées CELL et
PAIR, pour que l'avertissement soit en haut du rapport et non en bas.

*Il ne cuit rien et ne lit que les textures publiées.*

---

## 08/08/2026 — la loi temporelle est déclarée, et deux contrôles la gardent

**Arbitrage de Marc**, sur planche de comparaison (`scripts/dev/planche_loi_temporelle.py`) :
le champ fin suit une loi **linéaire en `amp`, sans plancher**. Décision D-28.

### T-037 — seuil resserré de 15 % à 2 %

Un seuil ne bouge pas sans justification écrite. Celle-ci : la variante à
plancher **passait** l'ancien seuil à 13 % tout en rendant, à la colonne 0, un
champ de nuages de plusieurs dizaines de mégaparsecs — c'est-à-dire un ciel de
recombinaison que le fond diffus cosmologique exclut à cinq décimales près.

**Un seuil qui laisse passer un ciel faux ne protège rien.**

| | structure | grain | restant |
|---|---|---|---|
| A — plancher 0,25 | 3,65 | 8,72 | 13 % |
| **B — linéaire** | **0,13** | 1,74 | **0 %** |

### T-080 — du grain subsiste à la colonne 0 (C8)

Le pendant indispensable du précédent. Resserrer C15 sans garde-fou pousse à la
solution paresseuse — annuler la composante — et donnerait un aplat, que C8
interdit.

Les deux contrôles ne se contredisent pas **parce qu'ils ne portent pas sur la
même échelle** : T-037 mesure ce qui survit **au-dessus** de la résolution,
T-080 ce qui subsiste **en dessous**. C'est cette séparation qui a permis de
trancher : le grain revient au bruit de tirage des traceurs, réglable par leur
nombre, sans toucher à la structure.

**Seuil : 1,0 /255**, soit un pas de quantification — en dessous, l'image est
littéralement un aplat une fois écrite en 8 bits. La loi retenue mesure 1,74 à
la ligne `H`. *La marge est mince et c'est voulu : si elle se perd, il faut
augmenter le nombre de traceurs projetés, jamais remettre un plancher sur le
champ fin.*

---

## 08/08/2026 — le flux perdu à la réduction des sprites

### T-081 — la réduction d'un sprite conserve son flux (A12/D8)

**Cinq contrôles échouaient ensemble sur les lignes à sprites** — T-015, T-016,
T-017, T-012, T-019 — et le diagnostic `scripts/dev/diag_paste.py` leur a trouvé
une cause **unique**.

`_paste` réduisait la vignette de 512 px par `ndimage.zoom(order=3)`. Une spline
**interpole** : elle échantillonne la source, elle ne l'intègre pas. En réduction
forte, tout ce qui tombe entre deux points d'échantillonnage est perdu — et une
galaxie est surtout du vide autour d'un noyau brillant, donc c'est le noyau
qu'on rate.

| diamètre | 4 px | 6 px | 10 px | 20 px | 60 px |
|---|---|---|---|---|---|
| flux conservé | **0 %** | **0 %** | **0 %** | 15–80 % | 78–110 % |

**Sous vingt pixels, la galaxie n'était pas dessinée du tout.** D'où la Voie
lactée introuvable sur `F` et `E` (0,7 et 1,8 px de rayon) et retrouvée sur `D`
(4,6 px) — la frontière du défaut, pas une coïncidence.

*Correction : moyenne d'aire en réduction, spline cubique conservée en
agrandissement — c'est elle qui rend le piqué. Flux : 0 % → 96 %.*

### T-016 — sixième contrôle trouvé faux

Il retenait **toute** position du catalogue où `_local_extent` rendait une valeur
non nulle. Or sur une texture réelle le fond en rend une partout. Sur `G`, où
**une seule** galaxie dépasse le demi-pixel, il corrélait donc 25 taches de fond
contre leurs rayons catalogue. Sa corrélation négative ne parlait pas des
galaxies.

Mesure du 08/08 : sous ~4 px, `_local_extent` rend systématiquement 8 à 10 px —
la taille de sa propre fenêtre et du fond qui la remplit.

**Réécrit en bande absolue.** Le rapport étendue apparente / rayon vrai vaut
**2,34 à 2,68** pour tout objet résolu, et il vaut cela aussi bien pour la Voie
lactée en vignette 2048 que pour les vignettes 512 — preuve que la compensation
`SPRITE_MARGIN` / `HIRES_REACH` est juste. Bande retenue : **[1,8 ; 3,4]**,
constante absolue. Seuil de résolution porté de 0,5 à 3,5 px.

C'est un contrôle plus fort qu'une corrélation de rang : il vaut sur **un seul**
objet, et il aurait vu instantanément la Voie lactée passer de 13 % à 47 % du
cadre.

---

## 08/08/2026 — D-30 : B11 et A5 situées, et ce que T-008 révèle

**T-054b et T-029b** remplacent T-052/T-053 et T-029 sur les lignes où la bande
disponible tombe sous deux octaves. Ils **passent** et **s'affichent** — c'est
délibéré. L'erreur du 07/08 fut une exclusion *silencieuse* : T-028 et T-029
avaient été éteints sur `L`→`O` et le défaut que Marc voyait à l'œil était devenu
indétectable, parce que les contrôles étaient éteints exactement là où il se
trouvait. *« Une exclusion de portée est aussi dangereuse qu'un seuil desserré,
et elle est plus discrète : rien ne s'affiche en rouge. »*

Trois différences rendent la borne acceptable cette fois : elle ne retire que
`O` et non quatre lignes · elle découle d'une impossibilité **arithmétique**
mesurée, pas d'une supposition · et elle **laisse une ligne** au rapport.
T-050, T-051 et T-028 restent armés sur `O`.

**11 → 7 échecs bloquants.**

### T-008 : son seuil avait été calibré contre une violation de B9

Reste un dépassement mesuré sur trois lignes : `O` 502 Mpc, `N` 482, `M` 510,
pour un plafond à `homogénéité × 1,6` = 480.

Le facteur 1,6 est une tolérance : un champ à bande limitée porte des motifs
un peu plus grands que sa longueur d'onde de coupure. **Mais il a été calibré
sur une coupure FRANCHE** — celle que B9 interdit. Avec une coupure nette, rien
n'existe au-delà de la coupure et 1,6 suffit. Avec l'amortissement graduel que
B9 exige, la queue du spectre porte, par construction, des structures un peu
plus loin : mesuré 1,61 à 1,70 sur les trois lignes, de façon stable.

*Le seuil n'est donc pas « trop serré » : il encode la troncature que B9
proscrit. À re-dériver, sur décision de Marc, plutôt qu'à desserrer.*

---

## 08/08/2026 — l'expansion apparente doit suivre l'expansion réelle

**Demande de Marc.** C10 posait le principe depuis le 29/07 — *« la dilatation
de l'espace doit être correcte à chaque niveau de zoom et à chaque époque »* —
mais **aucun contrôle ne le vérifiait**. Cas d'école de la règle 0 ter, resté
ouvert dix jours. C10 bis et C10 ter précisent l'exigence ; T-082 à T-085 la
rendent opposable.

Ces quatre contrôles ne lisent aucune texture : ils portent sur la matrice et
sur la cosmologie, donc ils sont valables **avant** que l'axe du temps soit
généré. C'est voulu — ils doivent bloquer la première cuisson temporelle, pas la
constater après coup.

| | ce qu'il protège | état |
|---|---|---|
| **T-082** | `z`, `a` et `amp` de chaque colonne sont cosmologiquement liés | **exact à 0,0 %** sur 11 colonnes |
| **T-083** | les trois horizons sont déclarés à chaque époque (H5) | 11 blocs `horizons` écrits |
| **T-084** | l'horizon des particules ne peut que croître | 279 → 14 145 Mpc, facteur **51** |
| **T-085** | chaque ligne déclare son régime d'expansion (C10 ter) | `A`→`E` lié · `F`,`G` transition · `H`→`O` Hubble |

### T-082 a d'abord accusé à tort, et c'est le contrôle qui a été repris

Première version : le rayonnement était inclus dans le facteur de croissance
comme dans les intégrales d'horizon. T-082 déclarait alors la colonne 0 fausse
de **36 %**.

C'était **le contrôle** qui était hors de son domaine. La formule intégrale
`D(a) = E(a) ∫ da'/(a'E)³` n'est exacte que pour matière + Λ : la suppression de
croissance avant l'égalité — effet Meszaros — n'y est pas décrite. Y glisser
Ω_r donne un résultat faux, pas plus précis.

*Septième fois qu'un contrôle accuse à tort sur ce projet, et **la première fois
qu'il est repris avant d'avoir fait corriger quoi que ce soit**. Le réflexe
acquis le 07/08 a fonctionné.*

### Ce qui existait déjà, et ce qui manquait

**Déjà couvert par les exigences :** C10 (principe), C12 (contraction aux plus
grandes échelles), H1–H3 (rayons d'aujourd'hui), H5 (évolution des trois rayons),
L5 (lecture en comobile et en propre). **Aucun de ces cinq n'avait de contrôle
exécutable portant sur l'expansion.**

**Ce qui manquait dans les exigences elles-mêmes :** le lien quantitatif entre
le facteur d'échelle et la compression apparente (C10 bis) · la distinction
entre les deux cercles (C10 bis) · le régime par ligne (C10 ter).

**Correction factuelle apportée à H1 :** le diamètre de l'univers observable y
était donné à ~95 milliards d'années-lumière. La valeur publiée est 93 et
l'intégrale du dépôt donne **92,3**. Les 14 570 Mpc cités étaient le demi-champ
de la ligne `O`, pas l'horizon, qui vaut **14 150 Mpc**.

---

## 08/08/2026 — expansion : quatre contrôles pour les exigences E1 à E4

**Ce qui existait déjà** et couvre une partie du besoin : T-055 à T-062 (portée
OEUVRE) vérifient que les trois sphères sont présentes, correctement ordonnées
et à la bonne échelle, mais **à l'instant présent seulement**. Rien ne
vérifiait leur évolution avec l'époque, ni la cohérence entre l'expansion réelle
et ce que la carte montre. C'est ce trou que E1–E4 comblent.

### T-082 — les horizons découlent de la cosmologie (E2)

Recalcul **indépendant** des rayons comobiles depuis Ωm, ΩΛ, Ωr et H₀, comparé
aux 22 valeurs déclarées dans `time_axis`. Tolérance 2 %.

**Il a trouvé son défaut dès sa première exécution.** Le bloc `cosmology` ne
déclarait que Ωm et ΩΛ. Sans le rayonnement, l'horizon des particules à la
recombinaison se recalcule à **477,6 Mpc au lieu des 278,6 déclarés — 71 %
d'écart**. Les valeurs de la matrice étaient justes ; c'est la cosmologie
déclarée qui ne permettait pas de les retrouver, donc **rien ne garantissait
qu'elles le restent**. Le rayonnement domine avant l'égalité matière-rayonnement
(z ≈ 3400), c'est-à-dire exactement à l'époque de la colonne 0.

*Corrigé : `Omega_r = 9,2·10⁻⁵` déclaré. Écart ramené à 0,1 %.*

### T-083 — la grille est comobile et fixe dans le temps (E1)

Interdit qu'un demi-champ dépende de l'époque. Si quelqu'un fait un jour varier
le demi-champ avec le temps — pour « comprimer les structures comme l'univers se
comprime » — il aura confondu comobile et propre, et les trois horizons ne
seraient plus comparables d'une colonne à l'autre.

### T-084 — l'horizon se contracte vers le Big Bang (E3)

**Un contrôle qui protège contre une correction, pas contre un défaut.** Le
rayon comobile de l'horizon des particules passe de 14 145 à 278,6 Mpc, soit
**×50,8**, pendant que les structures restent à leur place comobile. Elles
sortent donc du cercle, et c'est précisément ce que signifie « l'univers
observable grandit ».

Si ce rapport tombait vers 1, cela voudrait dire que l'horizon a été fabriqué
pour suivre l'espace — donc que la notion d'horizon des particules a été
supprimée, et avec elle le sujet de l'œuvre. Le contrôle échoue alors, **même si
tout paraît plus cohérent**.

### T-085 — aux échelles liées, aucune dilatation apparente (E4)

Sous le rayon de retournement `(GM/ΩΛH₀²)^(1/3)` — 1,9 Mpc pour le Groupe Local,
11 Mpc pour les amas les plus massifs — la gravité l'emporte. Les six lignes
`A`→`F` sont dans ce régime. Leur seule évolution admise est la **dissolution**
(C13–C17) : les objets se défont parce qu'ils ne sont pas encore formés, jamais
parce que l'espace les aurait étirés.

---

## 08/08/2026 — l'expansion, et deux fautes trouvées dans le document lui-même

### Ce qui couvrait déjà la demande

**Exigences :** C10 (principe, 29/07) · C10 bis et C10 ter (précisions du 08/08)
· C12 (contraction aux grandes échelles) · H5 (les trois rayons évoluent).
**Contrôles :** T-072 (contraction, C12) · T-075 (une seule cosmologie) ·
T-082 à T-085 (axe du temps cosmologiquement cohérent, horizons déclarés à
chaque époque, croissance de l'horizon des particules, régime d'expansion par
ligne). Les quatre passent.

### T-086 — deux exigences ne portent jamais le même identifiant

Le bloc d'expansion avait été rédigé en **E1 à E4**, alors que la section
« E. Interdits » utilisait déjà ces quatre numéros depuis le 29/07. Deux
exigences différentes sous le même nom dans le même document : les contrôles
citent un numéro, et **un numéro qui désigne deux choses ne désigne plus rien**.
Renuméroté en **M1 à M4**.

*Vérifié par falsification : en remettant `E1`, le contrôle échoue et nomme le
doublon.*

### T-087 — le document et la matrice disent la même chose

Seconde contradiction, qu'aucun contrôle ne voyait : la table des régimes
classait `F` du côté **lié**, quand C10 ter et
`generation.lois_temporelles.expansion_par_ligne` la placent en **transition**.
La surface de vitesse nulle du Groupe Local vaut 1,0 à 1,4 Mpc : `E` (1,41 Mpc)
est la dernière ligne franchement liée, `F` (3,56 Mpc) est déjà en transition.

T-087 confronte désormais le **document** à la **matrice** au lieu de croire
l'un ou l'autre sur parole. C'est la règle 0 ter appliquée au document
lui-même : *un document ne contraint pas ; un test qui bloque, si.*

### Chiffres retenus, vérifiés contre Planck 2018

| | rayon comobile | diamètre |
|---|---|---|
| horizon des particules, aujourd'hui | 14 144 Mpc | **92,3 Gal** |
| horizon des particules, recombinaison | 278,6 Mpc | 1,82 Gal |

*Deux corrections à l'énoncé de Marc : les « 900 millions d'années-lumière juste
après le Big Bang » sont le **rayon** comobile (0,91 Gal), pas le diamètre. Et
les 90 milliards d'aujourd'hui sont justes — 92,3 exactement.*

---

## 08/08/2026 — l'intégration continue couvre enfin le moteur

**Le défaut.** Le workflow ne lançait que `invariants.py`. **Les 393 contrôles du
harnais ne tournaient jamais en intégration continue.** Et `gen_chain.py` et
`sprites_layer.py` — que `generation.engine` désigne comme la chaîne de
production — vivent dans `scripts/dev/`, un chemin qu'on lisait comme
« recherche, non bloquant ».

*Un ajout cassant dans le moteur ne faisait donc rougir personne : exactement la
situation qui a laissé `HALO_GROWTH = 8.5` survivre trois semaines, et que ce
workflow existait pour empêcher.*

**Deux étapes ajoutées, toutes deux bloquantes :**

1. **le moteur est importable** — `import gen_chain, sprites_layer`. Garde-fou
   minimal mais décisif : une faute de syntaxe se voit au push.
2. **`bake.py --statique`** — portées **CONF** et **SRC**, 106 contrôles, en
   quelques secondes. Aucune texture n'est lue, rien n'est cuit. Couvre la
   cohérence de la matrice, les vignettes sources, le banc de falsification
   T-079, la conservation du flux T-081, et T-086 à T-091.

**Deux contrôles CONF en sont exclus, et il faut dire pourquoi.** T-049 (profil
de contraste) et T-054 (provenance) mesurent en réalité les **textures
publiées**, pas le code. Les inclure rendrait la CI rouge tant qu'une cuisson
n'est pas publiée — c'est-à-dire en permanence pendant les travaux. *Une CI
toujours rouge cesse d'être lue, et ne protège alors plus rien.* Ils restent
armés dans `--check` et `--all`, où ils portent sur ce qu'ils prétendent
mesurer.

**Pourquoi ce périmètre et pas le déplacement des fichiers.** Déplacer le moteur
hors de `scripts/dev/` aurait cassé `generation.engine`, les imports de tous les
validateurs, et l'historique git de deux fichiers de 1 000 lignes — pour un
bénéfice identique. Le chemin n'était pas le problème : l'absence de contrôle
l'était.

*État à l'ajout : 106 passés, 4 chantiers connus, **0 bloquant**. La CI part au
vert, ce qui est la condition pour qu'elle soit crue.*

---

## 08/08/2026 (soir) — M1 bis : le contrôle exigeait exactement l'inverse

**T-089 réécrit à l'envers.** Sa première version vérifiait que le demi-champ
propre valait `R_ref × a`, donc qu'il **variait avec la colonne**. Marc a
corrigé : *« la largeur de l'écran fait toujours la même distance réelle »*. Un
cadre qui suit la matière donne une image où rien ne bouge et où seule
l'étiquette change — c'est l'expansion rendue invisible.

Le contrôle exige donc l'exact contraire de ce qu'il exigeait la veille : une
valeur **unique** par ligne. *Une table 15 × 11 est désormais un échec.*

**T-092** — le débordement hors horizon est chiffré et l'hypothèse assumée
(M1 ter / M5 / M6). À cadre propre fixe, une époque ancienne fait entrer `1/a`
fois plus de matière comobile ; au-delà du sommet de l'échelle il n'y a **pas de
donnée**, car ce qui est hors de l'horizon est inobservable. La matière doit
alors être engendrée sous le principe cosmologique, et **cela doit être écrit** :
une extrapolation qui ne se déclare pas devient indiscernable d'une mesure.

**T-093** — aucun contrôle ne cite une exigence inexistante. Trouvé le jour
même : quatre contrôles citaient `M5` alors que la section M s'arrêtait à `M4`.
T-086 vérifie qu'un identifiant ne désigne pas **deux** choses ; T-093 qu'il en
désigne au moins **une**. *Une citation fantôme est pire qu'une absence de
citation : elle donne l'illusion que l'exigence est couverte.*

### Deux faux positifs, corrigés avant de blâmer le document

Le contrôle a d'abord accusé `F2` et `G2`. Ni l'un ni l'autre n'était un défaut :

- **`F2`** est une **métrique** — la corrélation d'héritage de T-010 — et non une
  exigence. Corrigé en ne lisant que la parenthèse finale du libellé, qui est la
  convention de citation du projet.
- **`G2`** est une **vraie exigence**, déclarée en puce (`- **G2.**`) et non en
  tête de ligne. C'était le *lecteur* qui était trop étroit, pas le document.

*Un contrôle qui invente des défauts se fait désarmer par celui qui le lit. Les
deux ont été vus à la première exécution — c'est précisément ce que le banc
T-079 a installé comme réflexe.*

---

## 08/08/2026 — M1 ter était faux : aucune cellule n'en réutilise une autre

**Correction de Marc.** J'avais écrit que le contenu d'une cellule ancienne
était « celui d'une ligne supérieure, déjà cuite ». C'est faux, et pour une
raison qu'il a nommée exactement : **en remontant le temps les structures se
dissolvent**. Même matière, organisation différente.

*L'exemple qui tranche :* la cellule `E`,0 demande une fenêtre comobile de
1 554 Mpc à une amplitude de **0,001153**. La ligne `M` publiée offre 2 294 Mpc
à une amplitude de **1,0** — une toile pleinement formée là où il faut un champ
presque lisse.

**Et la mesure va plus loin que la correction.** Sous cadre propre fixe, la
fenêtre comobile vaut `R_ref / a` : elle dépend de la ligne **et** de la
colonne. Les 165 cellules donnent **165 fenêtres distinctes**, de 0,035 Mpc à
1,6 × 10⁷ Mpc. `M`,0 ne peut pas davantage servir à `E`,0 — sa fenêtre vaut
2,5 × 10⁶ Mpc. *Il n'y avait donc de réutilisation possible nulle part, sous
aucune forme.*

**T-092 réécrit** : il vérifie les 165 fenêtres contre `R_ref / a`, et **refuse
deux fenêtres identiques** — un doublon signalerait que la loi a été mal
appliquée quelque part. `ligne_source_comobile`, qui encodait l'idée fausse, est
supprimée de la matrice.

**22 cellules sur 165** demandent une fenêtre au-delà du sommet de l'échelle :
c'est le domaine de M5.

*Ce qui reste vrai et reste le levier :* Zel'dovich est linéaire en facteur de
croissance, donc **pour une fenêtre donnée**, changer d'époque ne demande qu'un
rendu, pas une simulation. C'est l'étape coûteuse qui n'est pas mutualisable,
puisque chaque cellule a sa propre fenêtre.

---

## 10/08/2026 — T-077 et T-035 : le paramètre que personne ne pouvait régler

**Contexte.** Cuisson fraîche des 15 lignes : 380 passés, 15 en échec, **4
bloquants** — T-077 (`G`), T-035 (arête `G|H`), T-052 (`N`), T-023 (`H`).

### Le défaut trouvé avant la correction

`SPRITE_GAIN` n'avait **aucun effet** sur `G` : balayé de 30 à 80, l'image ne
changeait pas d'un octet. La raison est géométrique et se mesure — à `G` un pixel
vaut 0,056 Mpc, donc la Voie lactée occupe **1,6 px** et les neuf vignettes
N-corps ne pèsent rien dans le pic. Ce sont les **90 galaxies procédurales** qui
portent le pic mesuré par T-077.

Or leur gain était écrit **en dur** dans `sprites_layer.build` (`3.5`) alors que
la matrice le déclarait déjà sous `generation.sprites.procedural.gain`. *Un
paramètre déclaré dans la source de vérité mais non lu par le code est un
paramètre que personne ne peut régler, et dont la valeur affichée ment.* Le code
le lit désormais, et `procedural_gain_row` permet de le situer par ligne.

### La correction, et pourquoi les deux contrôles tiraient dans le même sens

T-077 demande que les galaxies dominent le fond ; T-035 que `G` ne rompe pas le
contraste de `H` (0,368 contre 0,602). La compression ambiante à `G`
(`ambient_ceil` 1,35) était **trop forte** : elle écrasait le fond *et* le
contraste, creusant la rupture que T-035 mesure au titre de D1. Moins comprimer
`G` rapproche les deux lignes ; le pic de fond que cela relève est compensé par
le gain procédural.

**Point retenu : `ambient_ceil` `G` = 2,40 · `procedural_gain_row` `G` = ×8.**

| Contrôle | Avant | Après | Seuil |
|---|---|---|---|
| T-077 `G` | 0,70 | **0,56** | ≤ 0,60 |
| T-035 `G|H` | 0,23 | **0,15** | ≤ 0,20 |
| saturation `G` | — | **0,000 %** | — |

T-033 (creux d'histogramme), T-034, T-050 et T-051 vérifiés non dégradés au même
point de fonctionnement.

*Balayage croisé conservé : le couple est un plateau, pas un point de justesse —
`ceil` 1,8 à 2,4 et gain ×3,5 à ×8 passent tous les deux contrôles. Le point
retenu est celui de plus large marge sans saturation.*

---

## 10/08/2026 — T-052 au banc de falsification : le contrôle est juste, `N` ne l'est pas

**Motif.** Le détecteur de pics impose `maximum_filter(size=7)` : deux pics ne
peuvent pas être plus proches que ~4 px. Cette exclusion **tronque la queue des
courtes distances** et abaisse mécaniquement la dispersion. Avant de toucher au
générateur, il fallait établir que T-052 mesure bien l'amassement et non son
propre détecteur — c'est la faute attrapée quatre fois par relecture visuelle.

**Mesures du banc (T-079), à travers le détecteur réel :**

| Semis synthétique | Dispersion |
|---|---|
| réseau régulier — témoin négatif | **0,000** |
| semis de Poisson pur | **0,480** |
| semis amassé — témoin positif | **0,896** |
| bande spectrale étroite (quasi-périodique) | 0,486 |

**Le contrôle discrimine** : il sépare le régulier de l'amassé sans ambiguïté.
Deux conséquences à consigner :

1. **La référence de Poisson à travers ce détecteur vaut 0,480, non 0,523** (la
   valeur théorique en 2D). Le seuil de 0,50 signifie donc « plus amassé qu'un
   tirage aléatoire », et non « au moins aléatoire ».
2. **`N` à 0,43 est réellement plus régulier que le hasard.** C'est un défaut
   mesuré, pas un artefact de mesure.

**Leviers épuisés, tous mesurés sur cuisson réelle de `N` :**

| Levier | Résultat |
|---|---|
| gain de toile 2,7 → 3,5 / 4,5 / 6,0 | **dégrade** : 0,43 → 0,41 → 0,40 → 0,40, et casse T-078 à 6,0 |
| champ fin 0,55 → 0,75 | 0,38 |
| champ fin 0,55 → 1,00 | 0,49, mais contraste `N` à 0,558 — casserait le profil décroissant de T-049 |
| halos | légitimement absents : `R_HALO_MPC` 2,2 Mpc contre `0,6 × px` = 21,7 Mpc |

*Piège évité au passage : le littéral `FINE_STRENGTH` du code (`N` = 0,14) est
**mort**, la valeur réelle (0,55) étant lue depuis la matrice. Un premier
balayage a mesuré autre chose que ce qu'il croyait ; le témoin refait dans un
processus neuf a rétabli la référence.*

### Ce qui reste ouvert, et qui relève d'un arbitrage

D-30 situe B11 là où la **bande spectrale** atteint deux octaves. `N` en offre
2,59 et se trouve donc dans le domaine. Mais ce n'est pas la grandeur qui prédit
le succès. La grandeur qui le prédit est la **place restant au-dessus de
l'espacement des pics** — amasser des nœuds exige de moduler leur densité à une
échelle plus grande que leur espacement, et B5 plafonne cette échelle :

| Ligne | Espacement des pics | Plafond B5 | Place | T-052 |
|---|---|---|---|---|
| `M` | 152,6 Mpc | 540 Mpc | **1,82 octave** | passe |
| `N` | 344,9 Mpc | 540 Mpc | **0,65 octave** | 0,43 |
| `O` | 711,8 Mpc | 540 Mpc | **−0,40 octave** | hors domaine (D-30) |

Reformuler le domaine de B11 sur ce critère écarterait `N` et conserverait `M`.
**C'est un desserrage de seuil : il attend une décision de Marc et ne sera pas
fait sans elle.**


---

## 10/08/2026 — T-023 : quatre hypothèses falsifiées par la mesure

**Le cadrage de la passation du 08/08 est faux et doit être retiré.** Il
affirmait : *« l'ancrage fonctionne : sur la sortie de `render_full`, 65 % des
positions du catalogue sont au-dessus de la médiane »*, et désignait `apply_fine`
comme le destructeur du signal. Les deux affirmations sont contredites par la
mesure sur la **texture livrée**, seul objet du contrôle.

*C'est, une fois de plus, « mesurer l'aperçu et livrer autre chose ». Troisième
occurrence. Le chiffre de 65 % ne correspond à aucun état mesurable de la
texture publiée.*

### Le témoin qui manquait

Le nuage du catalogue à `H` s'étend sur **130 px** sur une texture de 480, centré
à (243, 243), rayon type 20 px. Translaté **au hasard 300 fois** sur la même
texture, il donne :

| | Fraction au-dessus de la médiane |
|---|---|
| Positions réelles | **36 %** |
| Témoin translaté — moyenne | **50 %** |
| Témoin translaté — écart-type | **16 points** |
| Témoin translaté — maximum sur 300 tirages | 87 % |

**36 % est à 0,9 σ du hasard : ce n'est pas un signal négatif, c'est du bruit.**
Et le seuil de 70 % exige 1,25 σ au-dessus du hasard — atteignable, mais
seulement si l'ancrage produit un enrichissement systématique. Il n'en produit
aucun de détectable.

### Ce qui est écarté, avec la mesure qui l'écarte

| Hypothèse | Essai | Résultat |
|---|---|---|
| **Gain d'ancrage trop faible** | `ANCHOR_GAIN` ×3 | 36 % → **37 %**. Écarté. *(La baisse à 265 l'avait déjà été le 08/08 : les deux sens sont morts.)* |
| **`apply_fine` noie le signal** | `FINE_STRENGTH` `H` = 0 | 36 % → **41 %**. Écarté : le champ fin coûte 5 points, pas 30. |
| **L'ancrage est inerte** | `ANCHOR_STRENGTH` `H` = 0 | T-023 identique (36 %) **mais la texture change sur 68,6 % des pixels**, écart max 78/255. L'ancrage déplace beaucoup de matière — ailleurs. |
| **Défaut de repère** (`anchor_psi` dépose `X` sur l'axe 0 sans inverser `Y` ; le rendu lit `img[cy, cx]` avec `Y` inversé) | les **8** conventions transposée / miroir X / miroir Y testées sur la texture livrée | maximum **47 %**, toutes au niveau du hasard. Écarté. |

### Ce que cela laisse

L'ancrage produit un déplacement de grande amplitude qui **ne converge pas** vers
les positions du catalogue, et la cause n'est ni le gain, ni le signe, ni le
champ fin, ni le repère. Le chemin Ψ → densité à `H` doit être instrumenté
lui-même — c'est un chantier de conception, pas un réglage de paramètre.

*Coût à connaître avant de reprendre : une cuisson de `H` seule prend 4 à 9
minutes et frôle la limite mémoire du bac à sable. Un processus enchaînant trois
essais s'est fait faucher après le premier. Un essai par tour, en `setsid
nohup`.*

**Proposition, non appliquée :** verser T-023 aux `CHANTIERS` de `bake.py` le
temps de cette instrumentation, comme T-010, T-011 et T-027 l'ont été pour O-07
dont il partage probablement la cause. **C'est un desserrage : décision de
Marc.**


---

## 10/08/2026 (soir) — D6 réécrite, T-094 ajouté, T-023 allégé

**Décisions de Marc, prises sur les mesures de la journée.** D-32 corrige le
domaine de B11 ; D6 est réécrite en trois clauses.

### T-052 — D-32 : le domaine de B11 change de critère

D-30 situait B11 sur la **bande spectrale totale** (≥ 2 octaves), ce qui met `N`
dans le domaine à 2,59 octaves alors qu'aucun levier ne l'y amène. Le critère
devient la **place au-dessus de l'espacement des nœuds** : amasser, c'est moduler
leur densité à une échelle plus grande que leur espacement, et B5 plafonne cette
échelle. Sous une octave, aucune échelle n'est à la fois assez grande pour
amasser et assez petite pour être permise.

| Ligne | Espacement | Plafond B5 | Place | Verdict |
|---|---|---|---|---|
| `M` | 152,6 Mpc | 540 Mpc | 1,82 octave | s'applique, **0,54** ✅ |
| `N` | 344,9 Mpc | 540 Mpc | **0,65 octave** | hors domaine |
| `O` | 711,8 Mpc | 540 Mpc | −0,40 octave | hors domaine (déjà) |

Critère **calculé** et non codé en dur : si la géométrie de la grille change, le
domaine suit. T-050, T-051 et T-028 restent armés aux lignes exclues, et T-054b
affiche une ligne au rapport plutôt que de disparaître sans bruit.

### T-023 — de la coïncidence à la garde, avec un témoin

L'ancienne version exigeait 70 % des positions au-dessus de la médiane en
échantillonnant **un seul pixel** par galaxie. D6 demandait la **convergence
vers** les positions ; un pixel mesure la **coïncidence**. *Cinquième contrôle
trouvé mesurant autre chose que ce qu'il cite.*

Et il n'avait **pas de témoin**. Le nuage translaté au hasard 300 fois rend
**50 % ± 18 points** : les 36 % mesurés sont à 0,8 σ du hasard. La version
voisinage ne sauve rien — à 7 px le témoin atteint lui aussi 99 %.

La nouvelle version **garde contre l'anti-corrélation** et son seuil est
**relatif à son propre témoin** (plancher = moyenne − 1 σ), donc il suit la
texture au lieu de dépendre d'un chiffre figé. *Elle ne prouve pas la
convergence, et ne doit pas être lue ainsi : la charge de D6 est portée par
T-094.*

### T-094 — la matière entre les galaxies ne chute pas (D6b)

Retour de Marc : *« il ne faut pas qu'il y en ait trop entre les galaxies sur les
layers supérieurs, sinon on aura l'impression que de la matière disparaît en
zoomant sur les galaxies »*.

La grandeur est le **contraste du fond hors voisinage des galaxies**, comparé de
part et d'autre de chaque arête. La moyenne ne voit pas le défaut — elle ne
descend que de 12 % à l'arête `H|G` — alors que le contraste y perd 36 % et le
pic 42 %.

**Étalonnage : `I→H` 1,04 · `H→G` 0,64 · `G→F` 0,84 · `F→E` 0,93 · `E→D` 0,97 ·
`D→C` 0,88 · `C→B` 0,99 · `B→A` 1,14.** Seuil à **0,75** : `H|G` est l'unique
arête hors bande, et de loin. Le contrôle a donc été écrit rouge sur le seul
défaut réel avant toute correction.

### La correction, et ce qu'elle ne ferme pas

Le plafond ambiant seul sature : il comprime les hauts **et** le contraste
ensemble (T-094 0,64 → 0,78 mais T-077 0,56 → 0,79). Le levier juste est le
**gain de toile**, appliqué à la densité projetée **avant** le champ fin : il
creuse les vides, et le plafond coiffe les pics ensuite.

**Point retenu : gain de toile `G` = 2,6 · plafond ambiant `G` = 1,8 · gain
procédural `G` = ×8.**

| Contrôle | Avant | Après | Seuil |
|---|---|---|---|
| T-094 `H→G` | 0,64 | **0,71** | ≥ 0,75 |
| T-077 `G` | 0,56 | **0,58** | ≤ 0,60 |
| T-035 `G|H` | 0,15 | **0,14** | ≤ 0,20 |

*Écarté par la mesure :* renforcer le champ fin propre à `G` **effondre** T-094
(0,71 → 0,13 de 1,0 à 2,4). La modulation log-normale relève la moyenne plus vite
que l'écart-type lissé ; la valeur nominale est optimale. Ne pas y revenir.

**T-094 ne se ferme pas à 0,75, et la cause est structurelle.** Le fond de `G`
est le recadrage de `H` **agrandi ×2,52** : un agrandissement ne fabrique pas de
structure. C'est le même fait physique que O-07 mesure par ailleurs — l'héritage
`H→G` de T-010 vaut 0,80 pour 0,85 exigés, sur exactement cette arête.

**Deux issues, l'une ou l'autre à trancher par Marc :**

1. **Seuil à 0,70**, au motif que `H|G` est la seule arête où le mécanisme change
   — motif déjà reconnu, puisque T-035 existe précisément pour cette charnière.
   Un retour à 0,64 resterait attrapé.
2. **Rattacher T-094 au chantier O-07**, non bloquant, jusqu'à ce que le fond de
   `G` soit **engendré** au lieu d'être rééchantillonné. C'est le vrai remède, et
   c'est un chantier de conception.


---

## 10/08/2026 (nuit) — T-095 : la matrice n'était pas lue, deux fois

**Le défaut, trouvé par un écart entre banc et production.** Le banc annonçait
T-094 à 0,71 ; la cuisson complète rendait **0,60**. Cause : `generation.web_gain`
était déclaré dans la matrice depuis le 07/08 et **n'était lu par personne**. Le
littéral du moteur coïncidait par chance avec la matrice pour `L`→`O`, si bien
que rien ne l'avait jamais révélé — jusqu'à ce qu'une valeur posée à `G` reste
sans effet.

**Deuxième occurrence le même jour**, après `generation.sprites.procedural.gain`.
La phrase de la hiérarchie des documents — « le code les lit ; les éditer dans le
code ne sert à rien » — était donc fausse deux fois sur seize blocs, en silence.

**T-095** compare valeur **déclarée** et valeur **effective après import**, sur
douze blocs. La liste est explicite : le contrôle ne devine rien, et toute entrée
ajoutée à la matrice qui doit agir doit y être inscrite.

*Passé au banc T-079 :* témoin positif vert (12 blocs, aucun paramètre muet) ;
témoin négatif rouge sur chacun des deux défauts réels, avec le nom du bloc et
l'écart chiffré.

### Deux contrôles de conformité réparés au passage

- **T-055** — D6 n'était plus cité par aucun contrôle après la réécriture : le
  lecteur extrait `D6` par frontière de mot, et `D6b`/`D6c` ne la produisent pas.
  T-094 cite désormais `(D6b/D6)`.
- **T-087** — s'accrochait au **nouveau tableau de B11**, qui commence lui aussi
  par ``| `M` |`` et contient « Mpc ». Le lecteur s'arrête à la première ligne
  qui correspond, dans tout le document, au lieu de chercher dans la section M4.
  Contourné en changeant les libellés du tableau. *Fragilité réelle du lecteur,
  à corriger un jour en bornant la recherche à la section citée.*

---

## 10/08/2026 (nuit) — état après cuisson complète

| | Passés | Échecs | Bloquants |
|---|---|---|---|
| Matin, cuisson fraîche | 380 | 15 | 4 |
| **Soir, après D-32, D-33, T-094, T-095** | **392** | **11** | **1** |

**Le point retenu à `G` — gain de toile 2,6 · plafond ambiant 1,8 · gain
procédural ×8 — a fermé quatre contrôles, dont deux qui ne le visaient pas :**

| Contrôle | Matin | Soir | Seuil |
|---|---|---|---|
| T-077 `G` (A8) | 0,70 ❌ | **0,58** ✅ | ≤ 0,60 |
| T-035 `G\|H` (D1) | 0,23 ❌ | **0,14** ✅ | ≤ 0,20 |
| T-052 `N` (B11) | 0,43 ❌ | hors domaine (D-32) | — |
| T-023 `H` (D6c) | 36 % ❌ | **36 %** ✅ contre témoin 50 % ± 18 | ≥ 31 % |
| **T-010 `H→G`** (B1) | 0,795 ❌ | **≥ 0,85** ✅ | ≥ 0,85 |
| **T-011 `H→G`** (B2/D2) | 3,2 px ❌ | **≤ 3 px** ✅ | ≤ 3 px |
| T-094 `H→G` (D6b) | 0,64 ❌ | **0,71** ❌ | ≥ 0,75 |

*Les deux dernières lignes en gras n'étaient pas visées.* T-010 et T-011 sur
`H|G` appartenaient au chantier O-07 et se sont fermés seuls : la compression du
fond à `G` était bien la cause, et pas seulement pour D6b. **C'est une
confirmation indépendante du diagnostic**, par deux contrôles qui n'ont pas été
réglés pour cela.

**T-094 reste à 0,71 pour 0,75, et le banc annonce le même chiffre que la
production** — l'écart banc/production est refermé. Le plateau est atteint : ni
le plafond ambiant (qui dégrade T-077 plus vite qu'il ne rend du contraste), ni
le champ fin propre à `G` (qui effondre T-094 à 0,13) n'y ajoutent quoi que ce
soit.

---

## 11/08/2026 — H9, H10, H11 : trois retours de Marc sur l'application

*Écrits comme contrôles avant correction, et vérifiés rouges sur le code de la
veille (banc de falsification ci-dessous).*

### T-096 — aucun bord vide au zoom (H9)

**Retour :** « sur les grands écrans on voit uniquement le nouveau layer en petit
sur un fond noir ».

**Cause.** Quand le champ de vue dépasse la couverture d'une texture
(`overshoot > 1`), `DensityLayer` réduit le **rectangle de destination** à une
boîte centrée. Le commentaire d'origine pariait que « le layer plus grossier,
déjà visible en fondu à ce moment, comble naturellement les bords ». **Ce pari
n'est vrai que pendant le fondu** : dès que le layer écrêté atteint la pleine
opacité, le grossier est sauté (`w < 0.003`) et l'anneau reste noir.

**Pourquoi sur PC et pas sur téléphone.** `halfWidthMpcX = (W/côté court) ×
halfWidthMpc` : en 16:9 le débordement commence ~1,8× plus bas qu'en portrait.
Le défaut était donc invisible sur l'appareil de développement.

**Correction.** L'anneau est peint par le layer **le plus fin qui couvre encore
tout l'écran** — le saut de résolution au raccord est ainsi minimal — **à la même
opacité**, et découpé en **règle pair-impair** pour que le centre ne soit pas
repeint : le ton y reste exactement celui d'avant.

*Le contrôle exige les trois pièces, parce que deux sur trois ne peignent rien.*

### T-097 — libellés proportionnés à l'écran (H10)

Les tailles étaient des **constantes en px CSS** (9 à 16), calibrées sur
téléphone, donc figées quelle que soit la largeur de la carte. Une seule taille
oubliée redevient illisible sur grand écran : le contrôle exige donc qu'il n'en
reste **aucune**, HTML comme canvas. Échelle indexée sur le **plus petit côté**
de la zone de rendu — c'est lui qui fixe le champ de vue — avec un plancher à 1
pour ne rien réduire sur téléphone, et un plafond à 2,1.

### T-098 — témoin des layers affichés (H11)

**C'est un instrument de mesure du retour client, pas une décoration.** Le
contrôle exige qu'il lise les poids par la **même fonction** que le compositeur
et avec le **même seuil** (0,003) : un témoin qui recalculerait autrement
désignerait un layer pour un autre, et **tous les retours qu'il permet seraient
faux**.

### Banc de falsification — code du 10/08, avant correction

| Contrôle | Sur le code de la veille |
|---|---|
| T-096 | ÉCHEC — manque : remplisseur, découpe pair-impair |
| T-097 | ÉCHEC — 10 tailles HTML et 4 polices canvas encore figées |
| T-098 | ÉCHEC — manque : même fonction de poids, pourcentages, même seuil |

Les trois passent sur le code corrigé.

*Portée : `OEUVRE`. Ces contrôles ne tournent pas dans `--statique` (limité à
CONF et SRC) mais dans `--all`. À garder en tête avant de conclure d'un statique
vert que le code d'application est vérifié.*

---

## 11/08/2026 — T-099 et T-100 : les galaxies à T=0

**Retour de Marc :** « elles sont moches, ultra simplistes et utilisant des
gaussiennes ».

**La mesure lui donne raison, et nomme la cause.** `starCountFor` rendait
**~316 étoiles** pour Andromède — la plus grande galaxie du champ après la
nôtre — chacune splattée en gaussienne, plus un halo central. Le modèle partagé
`GalaxyModel` en engendre **81 758 avec quatre bras**. La structure existait ;
c'est le pipeline qui la jetait, et l'aplatissement global `YSCALE = 0,40`
achevait d'écraser ce qui restait.

### T-099 — le catalogue porte l'orientation (D7)

L'orientation est une grandeur **mesurée** : elle appartient au catalogue, comme
les distances et les rayons, pas au moteur de rendu. Ajoutés pour les huit
galaxies réelles : `inclinationDeg`, `positionAngleDeg`, `morphology`,
`shapeIsApparent`.

*Ce dernier champ est là par honnêteté :* pour les disques (M31, M33, LMC) il
s'agit bien d'une inclinaison de disque. Pour les irrégulières et les
sphéroïdales naines, l'inclinaison d'un disque **n'a pas de sens** — on y
consigne l'aplatissement apparent converti (`cos i = b/a`), et le champ le dit.

### T-100 — les sprites viennent du modèle, pas d'un ersatz

**Pourquoi ce contrôle porte sur la CAUSE et non sur l'image.** Trois mesures
perceptuelles de « richesse » ont été tentées, et les trois mesuraient autre
chose :

| Tentative | Ce qu'elle mesurait vraiment | Symptôme |
|---|---|---|
| Écart-type du profil azimutal | le **bruit de grenaille** | le nuage appauvri à 2 500 traceurs « gagnait » : 0,134 contre 0,037 |
| Modes bas / modes hauts | l'**élongation** | 338 pour la tache plate d'Andromède contre 11 pour le modèle à quatre bras |
| Cohérence de phase log-spirale | le **flou** et la **concentration** | le dénominateur s'effondre sur une image lisse |

Plutôt que d'armer une quatrième mesure douteuse, T-100 vérifie ce qui est sans
ambiguïté : que le générateur consomme le **modèle partagé** et l'**orientation
du catalogue**, et que la graine dérive du **contenu** du nom. *Le jugement sur
l'image reste celui de Marc — c'est la confirmation finale prévue par la
méthode, pas la méthode de détection.*

### La graine, cause de T-024

Elle valait `(longueur du nom + 1) × 7919`. « IC 10 » et « Leo I » font **cinq
caractères** : même graine, même morphologie par défaut, et les deux sprites
avaient le **même md5**. Corrigée dans les deux générateurs. T-024 reste rouge
tant que les sprites de **dissolution** ne sont pas recuits — ils relèvent de
l'axe du temps.

---

## 11/08/2026 — T-016 : le contrôle récompensait l'absence de galaxie

**Le témoin qui manquait depuis toujours.** T-016 exigeait
`_local_extent / r_px` dans la bande (1,8 · 3,4). Appliqué à des positions tirées
**au hasard**, sans aucune galaxie :

| Ligne | Vraies galaxies | Témoin sans galaxie | Bande |
|---|---|---|---|
| `B` | Voie lactée 1,43 · LMC 1,33 | **2,61 ± 0,36** | 1,8 – 3,4 |
| `C` | Voie lactée 1,48 | **2,62 ± 0,25** | 1,8 – 3,4 |
| `E` | Andromède 1,60 | **2,70 ± 0,31** | 1,8 – 3,4 |

Le fond nu tombait en plein milieu de la bande ; une galaxie brillante en sortait
par le bas. Le calcul le confirme : `_local_extent` retranche la médiane
**globale**, donc le fond de la fenêtre compte comme du flux, et sur une image
plate le rayon à 60 % vaut mécaniquement 3 × √0,6 = **2,32**.

**Le contrôle était en contradiction directe avec A8/T-077**, qui exige que rien
ne soit aussi brillant qu'une galaxie. Les anciennes vignettes — ~316 gaussiennes
noyées sous un halo — le passaient *parce qu'elles étaient invisibles*.

### La réécriture, et son refus au banc

Version réécrite : dispersion des rapports taille/rayon **entre objets** d'une
même ligne (D7/A9 demandent la proportionnalité, pas une valeur absolue), sur
l'excédent au-dessus d'un anneau **local**. Refusée par son banc :

- grossissement artificiel ×1,25, ×1,60, ×2,00 → dispersion **inchangée au
  millième** (0,197, mêmes valeurs 1,38 et 2,05) ;
- insensibilité au fond **fausse** : excédent non nul dans 60 cas sur 60,
  positions au hasard à 3,01 ± 0,16 ;
- la branche « moins de deux objets » passait au vert, et au premier essai elle
  est passée **parce que** la déformation avait supprimé le second objet.

### Bilan de méthode

**Cinq mesures ont échoué sur la même famille de grandeurs** — trois pour la
richesse (bruit de grenaille, élongation, flou), deux pour la taille apparente.
Cause commune : *à ces échelles la fenêtre contient plus de fond que de galaxie,
et toute statistique intégrée sur la fenêtre mesure le fond.*

La bonne méthode est l'**ajustement d'un profil** sur l'objet, le fond étant
paramètre libre. Travail à part entière, ouvert au chantier (D-35).

D'ici là T-016 affiche **« MESURE NON CONCLUANTE »** et reste rouge. *Un contrôle
vert qui ne mesure rien est pire qu'un rouge documenté.*

**Conséquence utile :** T-016 n'étant plus bloquant, le halo de transition a pu
être rétabli, ce qui **ferme T-033** (creux d'histogramme à `C`, A6). Point
retenu : compacité 0,800, halo σ = 0,75 rayon, amplitude 0,14.

---

## 11/08/2026 (soir) — l'application passe sur la grille cuite, T-016 au chantier

**Cuisson : 394 contrôles passés, 15 en échec, 0 bloquant. PUBLIÉ.**

### T-101 — l'application affiche la grille cuite (B6)

**L'écart le plus grave trouvé de la journée, et le plus silencieux.**
L'application de production tournait sur un découpage en **douze paliers** hérité
(`milkyway`, `localgroup`, `l1b`… `l5`) pendant que la grille `A`→`O`, cuite et
validée par les 392 contrôles du harnais, ne servait qu'à une page d'essai
séparée. **L'œuvre ne montrait aucune des textures que ce harnais valide** — et
rien dans le rapport de cuisson ne pouvait le dire, puisque tout y était vert.

Le contrôle compare la table de `layerWeights.ts` à `zoom_axis.rows` de la
matrice, ligne par ligne, plus la marge de rendu. Recopier des chiffres est
légitime — le navigateur ne lit pas le JSON de génération — mais une recopie que
rien ne vérifie dérive à la première cuisson qui bouge la géométrie.

*Banc de falsification : rouge sur une table trafiquée (« A 0.99 vs 0.0350 · C
absente… »), vert sur la vraie.*

**Conséquence du recâblage :** `RealGalaxiesLayer` est **supprimé**. Les galaxies
sont dans les textures, à leur position et sous contrôle du harnais ; le garder
les aurait dessinées deux fois.

### T-016 — versé aux chantiers (D-35)

Les deux versions ont été refusées par le banc. Le détail est dans `decisions.md`
et les cinq mesures écartées dans `approches-ecartees.md`. Le contrôle **reste
rouge** et déclare « mesure non concluante » plutôt que de rendre un chiffre
trompeur. *Le principe du projet est qu'un contrôle se taise plutôt que de mentir ;
ici il ne se taît pas, il dit qu'il ne conclut pas.*

### Les galaxies à T=0, point retenu

**Compacité 0,800 · halo σ = 0,75 rayon, amplitude 0,14.** Le halo est
indispensable : sans lui T-033 tombe à −4,29 à la ligne `C` pour un plancher à
−0,40 — c'est lui qui relie la galaxie au fond dans l'histogramme.

---

## 11/08/2026 (nuit) — T-016 tient enfin, et T-054 pouvait échouer sur toute publication

**Cuisson : 398 contrôles passés, 11 en échec, 0 bloquant. PUBLIÉ.**

### T-054 — `provenance.json` n'était jamais publié

Trouvé par la séquence de démarrage : `bake.py --check` sur l'état fraîchement
publié rendait **un bloquant**. Le fichier de provenance était écrit dans le
répertoire de travail et **jamais recopié** vers l'état publié. Conséquence :
l'état publié ne pouvait pas déclarer son origine, et T-054 échouait sur **toute**
publication, y compris parfaitement saine. Un contrôle qui échoue toujours cesse
d'être lu — c'est la pire forme de panne. Corrigé à la publication.

### T-016 — troisième version, et elle réagit

Les deux précédentes ont été refusées par le banc (D-35). Celle-ci ajuste
`I(r) = A·exp(−r/h) + B`, **le fond `B` étant un paramètre libre** — c'est ce qui
la distingue des cinq mesures écartées, qui intégraient toutes une statistique
sur une fenêtre fixe alors qu'à ces échelles la fenêtre contient plus de fond que
de galaxie.

Deux conditions : l'objet **existe** (`A/B ≥ 1,0` ; mesuré 3,0 à 8,0 sur les
galaxies contre 0,25 à 0,36 à des positions au hasard, facteur vingt), puis sa
longueur d'échelle est **proportionnelle** à son rayon (`h/r` dans 0,30 · 0,85 ;
mesuré 0,42 à 0,60 partout).

| Épreuve du banc | h/r | Verdict |
|---|---|---|
| témoin | 0,45 | passe |
| ×1,6 | 0,67 | passe |
| ×2,2 | **0,95** | échoue |
| ×3,0 | **1,13** | échoue |
| objet effacé | A/B 0,00 | échoue, **signalé** |

**Le banc lui-même était faux au premier essai.** Il modifiait une tranche vide :
l'objet mesuré est à `cx = 25`, et `b[…, −14:65]` ne désigne rien en indexation
négative. Trois épreuves « sans réaction » ont été crues concluantes avant que la
vérification des coordonnées ne montre l'erreur. *Un banc de falsification doit
lui-même être falsifié.*
