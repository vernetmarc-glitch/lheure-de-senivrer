# Registre des décisions

**Ce que Marc a déjà tranché.** Liste plate, datée, sans narration.

**Pourquoi ce document existe.** Les décisions étaient dispersées entre le
document d'architecture, le document de test et des conversations. Résultat : la
session du 28-29 juillet 2026 a rouvert la question du profil des halos, celle de
la politique de luminosité et celle du moteur des galaxies — toutes déjà
tranchées. Une décision introuvable est une décision perdue.

**Règle.** Une entrée de ce registre ne se rouvre que sur décision explicite de
Marc. Si une méthode proposée contredit une entrée, c'est la méthode qui est
refusée, pas l'entrée qui se discute.

---

## Rendu

| # | Décision | Date |
|---|---|---|
| **D-01** | Luminosité moyenne d'une image : **65 à 70 / 255** | 28/07/2026 |
| **D-02** | Politique de luminosité dans le temps : **moyenne constante** jusqu'à l'embrasement. Écarte le ratio ×3,4 du ton dissous et les « âges sombres » | 28/07/2026 |
| **D-03** | L'aspect du rendu à `a=1` **change** par rapport à la production. §11.7 de l'architecture devient caduque | 28/07/2026 |
| **D-04** | Palette « Astro » verrouillée | *antérieur* |

## Générateur

| # | Décision | Date |
|---|---|---|
| **D-05** | `A(s,a)` par layer **remplacé** par un facteur de croissance linéaire **global** `D(a)`. La hiérarchie de `a_form(s)` passe dans le facteur d'effondrement des halos, dérivée de la hauteur de pic | 28/07/2026 |
| **D-06** | Positions initiales en **verre** (réseau + jitter ½ cellule). Le réseau nu est interdit : anisotropie de 2,7 × 10⁹ à dissolution totale | 28/07/2026 |
| **D-07** | Les halos **prélèvent** leurs points dans la toile — masse conservée. Les ajouter empêchait la dissolution de se terminer | 28/07/2026 |
| **D-08** | Normalisation **absolue** du champ par σ₈ = 0,81, facteur unique calculé sur une grille de référence | 29/07/2026 |
| **D-09** | Dalle **anisotrope** validée (corrélation des spectres 0,996) et adoptée | 29/07/2026 |
| **D-10** | Rayons et masses en **valeurs physiques absolues**, jamais en fraction de boîte | 29/07/2026 |

## Galaxies et sprites

| # | Décision | Date |
|---|---|---|
| **D-11** | Le **moteur sprite** l'emporte visuellement sur les nuages de halos pour les galaxies. Option C : traitement de type sprite pour les 98 objets | 28/07/2026 |
| **D-12** | Splat **à flux conservé** obligatoire. ✅ **Fait le 30/07/2026** — commit `5957ae6f`, 9 sprites recuits, flux ×77 → ×2,18 | 28/07/2026 |
| **D-13** | Expansion de dissolution ramenée à **×4,2** (au lieu de ×7,7), flou à **45 %**. *Concernait le portage Python `bake_sprites.py` ; le script de production utilise désormais `HALO_GROWTH = 1,2`, la dispersion venant de la simulation N-corps* | 28/07/2026 |
| **D-14** | Le bruit de valeur multi-octave est **accepté** pour la modulation filamenteuse des sprites, par dérogation au §11.2 — il ne module qu'un champ déjà structuré et s'annule aux deux extrémités | 28/07/2026 |
| **D-15** | **Sept archétypes morphologiques** paramétriques, assignés depuis `radiusMpc` | 28/07/2026 |

## Dispositif

| # | Décision | Date |
|---|---|---|
| **D-16** | Le **redshift n'est pas affiché** | 29/07/2026 |
| **D-17** | Le temps s'exprime en **milliards d'années**. Conséquence assumée : les époques anciennes sont brèves à l'écran et l'évolution des trois sphères y sera peu lisible | 29/07/2026 |
| **D-18** | Les anneaux gradués et la grille cartésienne sont des **méthodes**, pas des demandes client. L'exigence est que l'échelle soit lisible | 29/07/2026 |

## Documentation

| # | Décision | Date |
|---|---|---|
| **D-19** | Hiérarchie à **trois niveaux** : demandes client → architecture → invariants. Ordre de lecture imposé | 29/07/2026 |
| **D-20** | Le niveau 3 est **exécutable**, pas de la prose. Une règle qui ne s'exécute pas n'empêche rien | 29/07/2026 |

## Grille de la matrice

| # | Décision | Date |
|---|---|---|
| **D-21** | Axe du zoom : **échelle géométrique à 15 lignes** `A`→`O`, raison **×2,520** constante, de 0,035 à 14 570 Mpc. Remplace les 13 lignes dont les pas allaient de ×1,41 à ×24. Le plancher est fixé par le halo de la Voie lactée (0,028 Mpc, soit 80 % du demi-champ de `A`) ; le plafond est l'horizon des particules | 30/07/2026 |
| **D-22** | Axe du temps : **11 colonnes** `0`→`10`, uniformes en **facteur de croissance `D(a)`**. La colonne *n* porte une amplitude de structure de *n*/10 ; la colonne 0 est l'ancre de recombinaison et porte seule l'embrasement. **L'affichage reste linéaire en milliards d'années** (L3, D-17) : le curseur et les keyframes sont deux choses distinctes, reliées par interpolation | 30/07/2026 |
| **D-23** | **Grille rigide.** Toutes les lignes portent les mêmes 11 colonnes. La fenêtre de dissolution d'une ligne devient un **paramètre lu aux colonnes communes**, jamais un axe du temps privé. Supprime `keyframes_a` par layer | 30/07/2026 |
| **D-24** | **Une cellule = un code = un fichier** : `st_<code>.png`, de `st_A0.png` à `st_O10.png`. La clé interne (`l1b`, `l2b`…) devient un détail d'implémentation et disparaît des noms d'actifs | 30/07/2026 |
| **D-25** | Le plafond dur de **150 Mpc** sur la bande de déplacement (« décision c » du 14/07) est **remplacé** par une loi de contraste décroissant avec l'échelle. Motif : combiné à un plancher exprimé en pixels, il vidait entièrement la bande de la ligne la plus haute | 30/07/2026 |
| **D-26** | Toute grandeur spatiale du paramétrage s'exprime en **Mpc comobiles**. `lam_min_px` est supprimé | 30/07/2026 |
| **D-27** | **E2 ne reçoit aucune dérogation.** Sous `G`, le fond ne s'efface pas *vers un uniforme* : il s'atténue **relativement aux galaxies** en conservant des nuages filamentaires. C'est donc le mécanisme d'effacement qui est en cause, pas l'interdit. Ferme **O-08**, ouverte le matin même | 07/08/2026 |

---

## Encore ouvert

Ces points reviennent régulièrement **parce qu'ils ne sont pas tranchés**. Les
proposer est légitime ; les traiter comme acquis ne l'est pas.

| # | Question | Depuis |
|---|---|---|
| **O-01** | Forme du profil radial des objets brillants : `q=0,6` convient aux amas, `q≈1,0` aux galaxies. Une loi de puissance unique ne peut pas les deux. NFW ou Einasto, qui portent un paramètre de concentration, sont les candidats | 28/07/2026 |
| **O-02** | Faut-il forcer davantage de diversité morphologique parmi les naines (~59 % du catalogue) ? | 28/07/2026 |
| **O-03** | Les trois sphères s'affichent-elles simultanément ou une à une ? | 29/07/2026 |
| **O-04** | Provenance et attribution de l'image de référence visuelle | 29/07/2026 |
| **O-05** | Les 90 galaxies procédurales du catalogue (lignes `F` et `G`) : sprites dédiés, ou points du champ généré ancrés sur leur position réelle ? *(= G2 du document client)* | 30/07/2026 |
| **O-07** | **Monter vers un moteur N-corps** (particule-maille) sur les lignes `E`→`K`, pour approcher le visuel Millennium ? Zel'dovich ne peut structurellement pas produire le resserrement des filaments après croisement de nappes, les profils de halo ni la sous-structure. À trancher **après retour visuel de Marc** sur le moteur actuel. Dossier complet : `docs/montee-en-complexite-nbody.md` | 30/07/2026 |
| **O-06** | Faut-il une seizième ligne ? À 15 lignes, `C` et `D` n'apportent aucune galaxie nouvelle — c'est un fait physique de notre voisinage, pas un défaut de l'échelle. À revoir si le rendu de ces deux lignes déçoit | 30/07/2026 |

## D-28 — la loi temporelle du champ fin est linéaire, sans plancher *(08/08/2026)*

**Tranché par Marc**, sur planche de comparaison, après mesure.

Le champ fin suit `A_fine(amp) = FINE_A × strength[ligne] × amp`. Il s'annule
franchement à la colonne 0. **Le grain que C8 exige revient au bruit de tirage
des traceurs**, jamais à un plancher sur le champ fin.

Ce qui est écarté : `amp^0,6` avec plancher 0,25 — loi écrite dans la docstring
de `sprites_layer` et **jamais implémentée**, `apply_fine` ne recevant aucune
amplitude. C'est la cause unique de T-037.

**Deux raisons, l'une physique, l'autre structurelle.**

Un plancher à 0,25 maintiendrait à la recombinaison un quart du contraste
d'aujourd'hui sur des longueurs d'onde allant jusqu'à 300 Mpc. Le contraste réel
à z = 1100 est de 10⁻⁵ à 10⁻³ — c'est le fond diffus cosmologique. La planche le
montre à l'œil.

Et un exposant propre au champ fin viole D-05 : en **régime linéaire toutes les
échelles suivent le même D(a)**, sans exception. La formation hiérarchique
appartient aux **halos**, qui ont un vrai seuil `a_form(ν)`, et à eux seuls.

**Corollaire.** La granulosité de la matière noire froide est réelle : sa coupure
de libre parcours se situe vers 10⁻⁶ masse solaire, donc **sous le pixel à toutes
les lignes et à tous les instants**. Un grain à l'échelle du pixel n'est pas un
artefact toléré, c'est la représentation honnête d'une granulosité qui existe.

*Conséquence : grain et structure sont découplés. C8 et C15 cessent de se
contredire parce qu'ils ne parlaient pas de la même chose.*

## D-29 — avancer sans demander l'arbitrage à chaque étape *(08/08/2026)*

**Consigne explicite de Marc.** Elle s'adresse à toute instance de Claude
reprenant ce projet, et elle prime sur l'habitude prise pendant les deux mois
précédents.

**Ne pas interrompre Marc pour choisir entre deux tâches.** Quand plusieurs
chantiers sont ouverts, choisir soi-même et avancer. La règle de tri :

1. **Les échecs bloquants d'abord**, du groupe de cause le plus nombreux au plus
   isolé. Un chantier déclaré non bloquant attend.
2. **À nombre égal, ce que Marc voit** l'emporte sur ce qu'il ne voit pas.
3. **Enchaîner** : résoudre un point, mesurer, passer au suivant dans la même
   séance, sans rendre la main entre deux.

**Ce qui justifie encore de s'arrêter — et rien d'autre :**

- un **arbitrage esthétique** que la physique ne tranche pas (ce qu'était le
  choix D-28 avant la planche de comparaison) ;
- une **exigence à supprimer ou à affaiblir** — jamais par omission (§ règle de
  non-régression) ;
- un **seuil de contrôle qu'il faudrait desserrer** ;
- un **résultat visuel** à confirmer, une fois la mesure objective déjà faite.

Une question de priorité entre deux tâches déjà définies n'est **aucun** de ces
cas. La poser fait perdre un tour et reporte le travail sur Marc, qui a dit
n'avoir pas d'avis a priori.

*Corollaire sur la forme : ne pas terminer chaque réponse par une question. Un
compte rendu chiffré de ce qui a été fait, puis la suite, sans demander la
permission de la prendre.*

## D-30 — B11 et A5 sont situées, non retirées *(08/08/2026)*

**Tranché par Marc**, sur mesure : *« accepter que `O` soit la ligne où l'univers
est montré homogène »*.

À la ligne `O`, un pixel vaut 91,06 Mpc. La bande disponible est bornée en bas
par Nyquist (2,2 px) et en haut par B5, que T-008 fait respecter à
`homogénéité × 1,6` = 480 Mpc, soit 5,27 px. **Il reste 1,26 octave**, quand B11
en exige 2.

**Aucune image ne peut satisfaire B5 et B11 à la fois sur cette ligne.** Ce n'est
pas un défaut de générateur, c'est de l'arithmétique. `N` autorise 2,59 octaves
et `M` 3,93 : la contradiction est **confinée à `O`**.

B11 et A5 s'appliquent donc là où la bande disponible atteint deux octaves —
critère **calculé**, non codé en dur : si la géométrie de la grille change, le
domaine suit. Exactement comme B4 a été située à la fenêtre `D`→`J` le 31/07.

**Ce qui justifie de l'accepter plutôt que de forcer.** À 14 570 Mpc de
demi-champ, l'univers observable *est* homogène — B8 le déclare déjà. Peindre
une toile filamenteuse y reviendrait à représenter un univers qui n'existe pas.
Et c'est la ligne où l'intention de l'œuvre s'applique le plus directement : en
cas de conflit, la lisibilité des trois sphères l'emporte sur le fond de carte.

**Garde-fous conservés**, parce que l'erreur du 07/08 était une exclusion
silencieuse : T-050 (dynamique), T-051 (nœuds plus lumineux), T-028 (élongation)
restent armés sur `O`. Et les contrôles écartés **affichent une ligne** dans le
rapport — T-054b et T-029b — au lieu de disparaître sans bruit.

## D-31 — toute distance montrée est réelle, jamais comobile *(08/08/2026)*

**Arbitrage de Marc. Renverse D-26**, qui imposait le Mpc comobile à tout le
paramétrage depuis le 30/07.

Le comobile reste la coordonnée **interne** du générateur — le champ y est
statique, et l'héritage entre lignes n'a de sens que là. Ce qui change est
l'**affichage** : plus aucune valeur comobile n'apparaît. `propre = comobile × a`.

*Ce que D-26 protégeait reste vrai et n'est pas remis en cause : « unités
comobiles, jamais en pixels » visait le pixel, pas le mégaparsec propre. Un
paramètre de génération exprimé en pixels reste interdit — cinq occurrences.*

**Ce que la décision entraîne, mesuré :**

- le demi-champ d'une ligne **dépend de la colonne** — table 15 × 11 dans
  `zoom_axis.demi_champ_propre_mpc` ;
- le régime d'expansion **dépend de l'époque** — à la recombinaison aucune ligne
  n'est liée, car rien ne s'est encore effondré ;
- l'échelle de zoom **n'est plus géométrique à toute époque** : le rapport entre
  lignes voisines vaut 2,52 à la colonne 10, mais descend à **1,55** à la
  colonne 0. **D-21 doit être amendée** ;
- les rayons des trois sphères sont publiés en propre
  (`horizons_propres_mpc`), en plus du comobile qui reste la source de calcul.

## D-32 — B11 est situé sur la place au-dessus de l'espacement des nœuds *(10/08/2026)*

**Tranché par Marc.** Corrige D-30, qui situait B11 sur la **bande spectrale
totale** (≥ 2 octaves). Ce n'est pas la grandeur qui prédit le résultat : `N`
offre 2,59 octaves et rendait 0,43 pour un seuil à 0,50, tous leviers épuisés et
mesurés.

Amasser des nœuds, c'est **moduler leur densité à une échelle plus grande que
leur espacement** ; B5 plafonne cette échelle à `homogénéité × 1,8` = 540 Mpc.
Sous une octave de place, aucune échelle n'est à la fois assez grande pour
amasser et assez petite pour être permise. `M` en a 1,82 et passe ; `N` 0,65 ;
`O` −0,40 et était déjà exclu.

Le critère reste **calculé**, jamais codé en dur : si la géométrie de la grille
change, le domaine suit. Les garde-fous de D-30 sont conservés — T-050, T-051 et
T-028 restent armés aux lignes exclues, et T-054b affiche une ligne au rapport.

## D-33 — D6 est réécrite : la continuité prime sur la coïncidence *(10/08/2026)*

**Reformulation de Marc.** L'ancienne D6 — « les galaxies réelles sont des
centres de gravité » — demandait que les filaments **convergent vers** les
positions du catalogue. Mesure faite, le générateur ne le produit à **aucun**
rayon de voisinage : les positions réelles sont au niveau du hasard (36 % contre
un témoin à 50 % ± 18), et à 7 px le témoin atteint lui aussi 99 %.

L'intention générale, dans les termes de Marc : *les galaxies doivent se détacher
du fond quand on zoome dessus, tout en étant déjà visibles sur les lignes
supérieures.* Trois clauses en découlent :

- **D6a** — sur les lignes à galaxies, le fond est ténu (porté par A8 clause 3) ;
- **D6b** — la matière visible **entre** les galaxies ne chute pas d'une ligne à
  la suivante, sinon le zoom donne l'impression qu'elle disparaît. **C'est la
  clause qui porte désormais D6**, et T-094 la mesure ;
- **D6c** — les galaxies ne tombent pas du côté raréfié de la toile. Clause
  **allégée** : garde contre l'anti-corrélation, seuil relatif à son propre
  témoin. Elle ne prouve plus la convergence, et le registre le dit.

*Ce que la décision ne fait pas :* elle ne retire pas l'exigence. Elle déplace la
charge de la preuve d'une grandeur que le générateur ne peut pas produire vers
celle que Marc décrit réellement à l'œil.

## D-34 — T-094 rejoint le chantier O-07 *(10/08/2026)*

**Tranché par Marc**, entre deux options mises en face l'une de l'autre : abaisser
le seuil de D6b à 0,70, ou rattacher le contrôle au chantier ouvert. **C'est la
seconde qui est retenue.** Le seuil de 0,75 n'est donc **pas desserré** : il reste
écrit, et le contrôle reste rouge et affiché.

**Motif d'admission.** Un contrôle ne rejoint cette liste que si **aucune cuisson
ne peut le corriger** — c'est le critère posé le 07/08. T-094 y satisfait : le
fond de `G` est le recadrage de `H` **agrandi ×2,52**, et un agrandissement ne
fabrique pas de structure. C'est mot pour mot ce que O-07 nomme, et deux autres
contrôles du même chantier (T-010, T-011) mesuraient déjà ce fait sur cette même
arête.

**Ce que la décision ne fait pas.** Elle ne referme pas D6b et ne baisse aucune
exigence. L'état à l'entrée est consigné — **0,71 pour 0,75** — et il n'est pas
l'état de départ : le gain de toile à `G` a rendu 0,07, et a fermé au passage
T-010 et T-011 sur cette arête.

**Ce qui le ferme :** que le fond de `G` soit **engendré** au lieu d'être
rééchantillonné depuis `H`. Tant que ce n'est pas fait, T-094 affiche sa mesure à
chaque cuisson.

## D-35 — T-016 rejoint les chantiers : la mesure est à réécrire, pas le seuil à desserrer *(11/08/2026)*

**Tranché par Marc**, sur mesure. Le contrôle est **cassé dans les deux sens** :

- **L'ancienne version récompensait l'absence de galaxie.** Elle exigeait
  `_local_extent / r_px` dans la bande (1,8 · 3,4). Or `_local_extent` retranche
  la médiane **globale**, si bien que le fond cosmique présent dans la fenêtre
  compte comme du flux. Témoin mesuré à des positions tirées **au hasard**, sans
  aucune galaxie : **2,61 ± 0,36** à `B`, **2,62 ± 0,25** à `C`, **2,70 ± 0,31**
  à `E` — en plein milieu de la bande. Les vraies galaxies rendaient 1,33 à 1,60
  et **échouaient**. Sur une image plate le rayon vaut mécaniquement
  3 × √0,6 = 2,32, ce qui explique le témoin.
  *Le contrôle était donc en contradiction directe avec A8/T-077, qui exige que
  rien ne soit aussi brillant qu'une galaxie. Les anciennes vignettes le
  passaient parce qu'elles étaient invisibles.*
- **La version réécrite ne détecte rien.** Banc du 11/08 : grossir une galaxie de
  ×1,25, ×1,60 puis ×2,00 laisse la dispersion **inchangée au millième** (0,197
  dans les trois cas). L'insensibilité au fond annoncée est fausse (excédent non
  nul dans 60 cas sur 60). Et sa branche « moins de deux objets » passait au vert
  — au premier essai de falsification, elle est passée **parce que** la
  déformation avait fait disparaître le second objet.

**Cinq mesures ont échoué sur cette famille de grandeurs** — trois pour la
richesse de structure, deux pour la taille apparente — toutes pour la même
raison : à ces échelles la fenêtre de mesure contient **plus de fond que de
galaxie**, et toute statistique intégrée sur la fenêtre mesure le fond.

**Ce que la décision fait.** Le seuil n'est pas desserré ; l'exigence D7/A9 n'est
pas retirée. Le contrôle **reste rouge**, déclaré au chantier, et affiche
« MESURE NON CONCLUANTE » à chaque cuisson. *Un contrôle vert qui ne mesure rien
est pire qu'un rouge documenté.*

**Ce qui le ferme :** une mesure de taille apparente par **ajustement de profil**
sur l'objet, le fond étant traité comme paramètre libre — et non par intégration
sur une fenêtre.

**Conséquence utile.** T-016 n'étant plus bloquant, le **halo de transition** a pu
être rétabli, ce qui ferme T-033 (creux d'histogramme à `C`, A6). Il ne reste donc
qu'un contrôle rouge de plus, pas deux.

## D-36 — l'application de production passe à la grille A→O *(11/08/2026)*

**Demandé par Marc :** « le lien que tu m'as donné n'utilise pas les nouveaux
layers ». Constat exact et grave : l'application tournait sur un découpage en
**douze paliers hérités** (`milkyway`, `localgroup`, `l1b`… `l5`) pendant que la
grille `A`→`O`, cuite et validée par les 392 contrôles, ne servait qu'à une page
d'essai séparée. **L'œuvre ne montrait aucune des textures que le harnais
valide** — un écart invisible depuis le rapport de cuisson, puisque tout y était
vert.

Trois conséquences :

1. `layerWeights.ts` porte les quinze lignes, raison ×2,520 constante, **une
   seule largeur de fondu** (0,15 dex). L'ancien découpage avait un pas de ×24
   sur une arête, masqué par une largeur spéciale de 0,52 dex à cet endroit.
2. `RealGalaxiesLayer` est **supprimé** : les galaxies sont dans les textures, à
   leur position et sous contrôle du harnais. Le garder les dessinait deux fois.
3. **T-101** interdit désormais à la table de l'application de diverger de la
   matrice. C'est le contrôle qui manquait pour que cet écart ne se reproduise
   pas en silence.

## D-35 — T-016 rejoint les chantiers : la mesure de taille apparente est à refaire *(11/08/2026)*

**Tranché par Marc**, après que le banc de falsification a refusé **les deux**
versions du contrôle.

**L'ancienne version récompensait l'absence de galaxie.** Elle exigeait
`_local_extent / r_px` dans la bande (1,8 · 3,4). Or `_local_extent` retranche la
médiane **globale**, si bien que le fond cosmique présent dans la fenêtre compte
comme du flux. Témoin à des positions tirées au hasard, sans aucune galaxie :
**2,61 à `B`, 2,62 à `C`, 2,70 à `E`** — le fond nu tombait en plein milieu de la
bande, tandis qu'une galaxie brillante en sortait par le bas (1,33 à 1,60). Le
contrôle entrait donc en contradiction directe avec A8/T-077, qui exige que rien
ne soit aussi brillant qu'une galaxie. Les anciennes vignettes le passaient parce
qu'elles étaient invisibles.

**La réécriture n'a pas tenu davantage.** Dispersion des rapports taille/rayon,
fond estimé sur un anneau local. Le banc :

- grossir artificiellement une galaxie de ×1,25, ×1,60 puis ×2,00 ne change
  **pas** la dispersion — 0,197 dans les trois cas, aux mêmes décimales ;
- l'excédent au-dessus de l'anneau local n'est nul dans **aucun** des 60 tirages
  au hasard : 3,01 ± 0,16 contre 1,38 et 2,05 pour les vraies galaxies ;
- sous deux objets résolus, la branche de repli **passait** — lors du premier
  essai, la déformation a fait disparaître le second objet et le contrôle est
  passé au vert *parce que* quelque chose était cassé.

**Le constat de fond.** Cinq mesures ont échoué sur cette famille de grandeurs —
trois sur la richesse, deux sur la taille apparente — toutes pour la même raison :
à ces échelles **la fenêtre de mesure contient plus de fond que de galaxie**, et
toute statistique intégrée sur la fenêtre mesure le fond.

**Ce que la décision fait, et ne fait pas.** Le contrôle n'est pas désarmé et son
seuil n'est pas desserré : il **reste rouge**, s'affiche à chaque cuisson, et
déclare explicitement « mesure non concluante » au lieu de rendre un chiffre
trompeur. D7 et A9 restent couvertes par T-012, qui porte la proportionnalité
d'une ligne à l'autre et qui, lui, passe.

**Ce qui le ferme :** une mesure par **ajustement de profil** sur l'objet, dont
l'échelle est un paramètre et le fond un **paramètre libre** — et non une
statistique intégrée sur une fenêtre fixe.

## D-36 — T-016 sort du chantier : la mesure par ajustement de profil tient *(11/08/2026)*

Ferme D-35, le jour même. La troisième version du contrôle ajuste
`I(r) = A·exp(−r/h) + B` autour de chaque objet, **le fond `B` étant un
paramètre libre**. C'est ce qui la distingue des cinq mesures écartées : toutes
intégraient une statistique sur une fenêtre fixe, et à ces échelles la fenêtre
contient plus de fond que de galaxie.

Deux conditions, dans cet ordre : l'objet **existe** (contraste `A/B ≥ 1,0` —
mesuré 3,0 à 8,0 sur les galaxies, 0,25 à 0,36 à des positions tirées au hasard,
soit un facteur vingt), puis sa longueur d'échelle est **proportionnelle** à son
rayon réel (`h/r` dans 0,30 · 0,85 — mesuré 0,42 à 0,60 partout).

**Banc de falsification, sur la Naine du Sagittaire :**

| Épreuve | h/r | Verdict |
|---|---|---|
| témoin | 0,45 | passe |
| ×1,6 | 0,67 | passe (dans la tolérance) |
| ×2,2 | **0,95** | échoue |
| ×3,0 | **1,13** | échoue |
| effacée | A/B 0,00 | échoue — signalée, pas de passage silencieux |

*Le banc lui-même a d'abord été faux : il modifiait une tranche vide, parce que
l'objet mesuré est à `cx = 25` et que `b[…, −14:65]` est vide en indexation
négative. Trois épreuves « sans réaction » ont ainsi été crues concluantes avant
que la vérification des coordonnées ne montre l'erreur. **Un banc de
falsification doit lui-même être falsifié** — c'est la leçon du jour.*

## D-37 — L'ancrage est retiré, et D6c avec lui *(11/08/2026)*

**Tranché par Marc, sur analyse de l'état de l'art qu'il a demandée.**

**Le nœud.** D4 exigeait une influence **décroissante** vers les grandes échelles ;
D6c que l'ancrage agisse **tôt** ; B1/B2 interdisaient l'**incrément** de force
d'une ligne à l'autre. Cinq configurations cuites et mesurées, aucune ne satisfait
les trois. Ce n'était pas un défaut de code mais une contradiction d'exigences.

**Ce que l'observation dit.** Entre les galaxies, à ces échelles, il n'y a **rien
de visible** — les baryons du réseau sont un gaz à 10⁵–10⁷ K dont 30 à 50 %
échappent encore à toute détection. Les galaxies sont les seules perles brillantes
de la toile ; le fil, on ne le voit pas.

**Conséquence.** S'il n'y a rien entre les galaxies, il n'y a **rien à faire
converger** vers elles. L'ancrage perd son objet, et avec lui D6c et T-023. Le
conflit disparaît au lieu d'être arbitré.

**Bénéfice mesuré.** L'ancrage pesait **7,08 px des 9,01 px** de perte d'héritage
à `I→H` — terme dominant du chantier O-07, établi par décomposition exacte qui
redonne T-011 à 0,3 px près.

*Ce que la décision ne fait pas :* elle ne supprime pas D4. Les galaxies restent à
leur position réelle, portées par le catalogue et les vignettes ; T-067 vérifie
désormais le **fait** — aucun mécanisme n'inscrit le catalogue au-delà de `J` —
au lieu de lire une table de paramètres.

## D-38 — Deux exigences nouvelles : le voisinage n'est ni isotrope ni homogène *(11/08/2026)*

L'analyse a révélé deux traits réels que l'œuvre ne montrait pas du tout, et qui
sont plus intéressants que les nuages qu'on cherchait à sauver.

**D9 — la structure locale est APLATIE.** Le Local Sheet mesure 10,4 Mpc de grand
axe pour **0,465 Mpc** de petit axe, soit 22 pour 1, et presque toutes les
galaxies brillantes proches y appartiennent. Aux lignes `F` et `G`, nos textures
sont isotropes — B7 l'exigeait même. **L'isotropie n'est exigible qu'au-delà de
l'échelle d'homogénéité.**

**D10 — le vide local occupe une part majeure du champ.** Le Local Void commence
juste à l'extérieur du Groupe local et paraît pratiquement dépourvu de galaxies ;
environ 23 % des galaxies du Local Volume sont des galaxies de vide. Nos contrôles
imposaient au contraire une moyenne homogène partout.

T-102 et T-103 les arment. Ils entrent **en chantier** avec leur mesure d'entrée :
le générateur produit un champ isotrope et de moyenne homogène à toutes les
lignes, et seule une évolution de la géométrie de la dalle et de la condition
initiale peut les fermer.
