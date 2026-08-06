# Registre des contrôles

Chaque contrôle porte son identifiant, sa portée, sa date et **le retour qui l'a
motivé**. Sans cette dernière colonne, un seuil qui gêne finit par être desserré
et le critère se reperd — c'est arrivé plusieurs fois.

**Desserrer un seuil oblige à écrire pourquoi en regard du retour d'origine.**
Supprimer un contrôle exige une décision explicite de Marc.

Implémentation : `scripts/harness/checks.py`. Exécution : `scripts/harness/bake.py`.

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

### Priorité 1 — perte sèche

| ID | Contrôle | Exigence | Pourquoi d'abord |
|---|---|---|---|
| T-014 | isotropie axes/diagonales ∈ [0,85 ; 1,2] | B3 | **existait sous `INV-E4`, perdu en réorganisant le harnais**. Échouait sur cinq lignes ; l'échec est devenu invisible |

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
| T-027 | signature de référence sur les lignes `K`→`H` | A1 | signature chiffrée, 10 grandeurs |
| T-028 | toile et non mousse : élongation des structures | A2 | 28/07 — « mousse de bulles rondes » |
| T-029 | points répartis le long des filaments | A5 | 28/07 |
| T-033 | continuité points brillants ↔ fond | A6 | histogramme sans rupture |
| T-034 | fond filamentaire présent sur les lignes à sprites | A8 | 29/07 |
| T-035 | fluidité à l'arête `G|H` : même ton, même densité apparente | D1 | la charnière la plus fragile |

### Priorité 4 — dissolubilité, à vérifier **avant** de générer les colonnes

| ID | Contrôle | Exigence | Ce qu'il garantit |
|---|---|---|---|
| T-036 | chaque composante a une loi temporelle déclarée | **C13** | rien n'est posé « en dur » |
| T-037 | à amplitude nulle, aucune composante ne subsiste comme structure | **C15** | la dissolution se termine |
| T-038 | la matière dissoute retourne au champ, pas en surcouche | **C14** | pas de résidu indissoluble |
| T-039 | effet fractal dans la fenêtre `D`→`J` | B4 | contenu neuf par cran |

**T-036 à T-038 sont les plus importants du lot.** Ils se vérifient sur la ligne
d'aujourd'hui, avant toute cuisson de colonne, et ils décident si les onze
colonnes seront du calcul ou une reprise de conception. Une composante sans loi
temporelle bloque la colonne entière — et on ne s'en apercevrait qu'après avoir
tout cuit.

---

## Portée TIME — deux colonnes voisines. Actif dès que les colonnes existent.

| ID | Contrôle | Exigence | Origine |
|---|---|---|---|
| T-020 | aucune structure n'apparaît en remontant | C4 | approche `A(s,a)` écartée — les petites structures colonisaient l'image |
| T-021 | les objets s'étalent | C1 | sprites de dissolution |
| T-022 | grain conservé, jamais d'aplat | C8 | 5 aplats sur D/E/F, 10 sur 12 sur C |

## Portée CONF — conformité du dépôt

| ID | Contrôle | Origine |
|---|---|---|
| T-030 | les 15 lignes existent | B6 |
| T-031 | paramètres figés dans la matrice | 02/08 — reproductibilité |
| T-032 | le code lit la matrice | 02/08 — une source de vérité que le code n'ouvre pas dérive en silence |

---

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
