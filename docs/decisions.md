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
