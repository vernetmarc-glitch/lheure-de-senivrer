# Matrice zoom × temps — nomenclature et paramétrage

*Version 4 — 30 juillet 2026. Remplace la v3 du 14 juillet (13 lignes, axes du
temps privés par ligne). Les moteurs et paramétrages antérieurs sont consignés
dans `approches-ecartees.md` ; ils ne sont pas repris ici.*

## 1. Source de vérité

La matrice canonique est **`app/public/data/spacetime_matrix.json`** — éditable
à la main, versionnée, et consommée telle quelle par la génération et
l'affichage. Aucun paramètre n'est redéfini ailleurs.

Après toute édition : relancer la cuisson, puis `scripts/dev/invariants.py --assets`.
Une image n'est jamais présentée sans ce contrôle.

## 2. Adressage — une cellule, un code, un fichier

La matrice compte **15 lignes × 11 colonnes = 165 cellules**, codées `A0` à `O10`.

| | |
|---|---|
| Ligne | une lettre `A`→`O` — une échelle de zoom |
| Colonne | un chiffre `0`→`10` — une époque de l'univers |
| Fichier | `st_<code>.png`, par exemple `st_J7.png` |

La lettre est l'**identité permanente** de la ligne. Les clés internes de la v3
(`l1b`, `l2b`, `l5a`…) sont supprimées des noms d'actifs : elles ne portaient
aucune information d'échelle et obligeaient à une table de correspondance.

**Règle de grille (D-23).** Toutes les lignes portent les mêmes 11 colonnes. Une
colonne est un instant de l'univers, identique d'un bout à l'autre de l'échelle.
Aucune ligne ne possède d'axe du temps propre.

## 3. Axe du zoom — 15 lignes géométriques

Raison **×2,5199** constante (0,4014 dex), de 0,035 à 14 570 Mpc.

| Code | Demi-champ (Mpc) | Contenu | Catalogue | Rendu |
|---|---|---|---|---|
| **A** | 0,0350 | La Voie lactée, plein cadre | 1 | sprites |
| **B** | 0,0882 | + Sagittaire, Grand et Petit Nuage de Magellan | 3 | sprites |
| **C** | 0,2222 | Le halo de la Voie lactée s'efface | 3 | sprites |
| **D** | 0,5600 | + NGC 6822 | 4 | sprites |
| **E** | 1,41 | **Le Groupe Local dans son ensemble** — IC 10, Andromède, Leo I, Triangulum | 11 | sprites |
| **F** | 3,56 | Le Groupe Local et ses abords | 29 | sprites |
| **G** | 8,96 | **Le voisinage complet — dernière ligne à sprites** | 86 | sprites |
| **H** | 22,58 | Le catalogue est épuisé ; la matière devient statistique | 98 | genere |
| **I** | 56,90 |  | 98 | genere |
| **J** | 143 |  | 98 | genere |
| **K** | 361 |  | 98 | genere |
| **L** | 911 |  | 98 | genere |
| **M** | 2295 |  | 98 | genere |
| **N** | 5782 | Sphère de Hubble (4 448) et horizon des événements (5 108) | 98 | genere |
| **O** | 14570 | **L'horizon des particules — l'univers observable** | 98 | genere |

**Plancher.** Le halo de la Voie lactée mesure 0,028 Mpc dans le code
(`MW_HALO_SEMI_MAJOR_MPC`) : à un demi-champ de 0,035 il occupe 80 % du cadre.

**Plafond.** L'horizon des particules aujourd'hui, 14 570 Mpc (H1).

**Fondu.** `fade_width_dex = 0,15` — valeur **unique pour toutes les arêtes**,
soit 37 % du pas. C'est ce qui rend D2 atteignable avec un seul nombre. En v3
cette valeur était 0,15 partout sauf **0,52** sur l'arête à 2,4 Mpc, pour masquer
un pas de ×24.

**Bascule sprites → champ généré : l'arête `G|H`.** La galaxie la plus lointaine
du catalogue est à 9,82 Mpc ; `G` en contient 86 sur 98. C'est le seul endroit de
l'échelle où les deux représentations montrent la même matière, donc le seul
endroit où **D1** est vérifiable.

**Lignes `C` et `D`.** Elles n'apportent aucune galaxie nouvelle : entre les
satellites de la Voie lactée (0,06 Mpc) et Andromède (0,78 Mpc), notre voisinage
est physiquement vide. Aucune échelle ne peut corriger cela. Elles portent
l'effacement du halo et le fond filamentaire ambiant (A8).

## 4. Bande de déplacement — auto-similaire par construction

| Code | Cellule de sortie (Mpc) | λ min (Mpc) | λ max (Mpc) |
|---|---|---|---|
| **A** | 0,00010 | 0,0003 | 0,1 |
| **B** | 0,00026 | 0,0008 | 0,1 |
| **C** | 0,00065 | 0,0020 | 0,3 |
| **D** | 0,00164 | 0,0049 | 0,8 |
| **E** | 0,00413 | 0,0124 | 2,1 |
| **F** | 0,01042 | 0,0313 | 5,3 |
| **G** | 0,02625 | 0,0788 | 13,4 |
| **H** | 0,06616 | 0,1985 | 33,9 |
| **I** | 0,16671 | 0,5001 | 85,4 |
| **J** | 0,42010 | 1,2603 | 215,1 |
| **K** | 1,05862 | 3,1759 | 542,0 |
| **L** | 2,66763 | 8,0029 | 1365,8 |
| **M** | 6,72219 | 20,1666 | 3441,8 |
| **N** | 16,93931 | 50,8179 | 8672,9 |
| **O** | 42,68555 | 128,0566 | 21855,0 |

- `lam_min_mpc` = 3 cellules de la résolution de **sortie** — jamais un nombre
  de pixels fixe partagé entre lignes (D-26).
- `lam_max_mpc` = moitié de la boîte, **relatif à la ligne**. Le plafond dur de
  150 Mpc est supprimé (D-25).
- Le rapport λmax/λmin vaut **170,67 sur les quinze lignes**. La bande ne peut
  pas être vide, et l'auto-similarité est ce qui rend B2 atteignable.

*En v3, le plancher valait 6 px et le plafond 150 Mpc : à la ligne la plus haute
1 px = 68,3 Mpc, donc le plancher valait 410 Mpc contre un plafond de 150. La
bande était vide et l'image un aplat exact.*

## 5. Axe du temps — 11 colonnes uniformes en croissance

Colonnes uniformes en **facteur de croissance linéaire `D(a)`** — l'amplitude de
structure, grandeur qui pilote réellement la dissolution (D-05).

| Col | Amplitude | `a` | `t` (Ga) | `z` | Δt vers la suivante |
|---|---|---|---|---|---|
| **0** | 0,00 | 0,000908 | 0,001 | 1100,32 | 0,38 Ga |
| **1** | 0,10 | 0,078796 | 0,381 | 11,69 | 0,70 Ga |
| **2** | 0,20 | 0,157807 | 1,079 | 5,34 | 0,91 Ga |
| **3** | 0,30 | 0,237587 | 1,986 | 3,21 | 1,08 Ga |
| **4** | 0,40 | 0,319093 | 3,071 | 2,13 | 1,25 Ga |
| **5** | 0,50 | 0,403763 | 4,322 | 1,48 | 1,42 Ga |
| **6** | 0,60 | 0,493671 | 5,743 | 1,03 | 1,61 Ga |
| **7** | 0,70 | 0,591856 | 7,352 | 0,69 | 1,83 Ga |
| **8** | 0,80 | 0,702951 | 9,182 | 0,42 | 2,11 Ga |
| **9** | 0,90 | 0,834503 | 11,294 | 0,20 | 2,50 Ga |
| **10** | 1,00 | 1,000000 | 13,796 | 0,00 | — |

**La colonne *n* porte une amplitude de structure de *n*/10.** La colonne 0 est
l'ancre de recombinaison et porte seule l'embrasement (C7).

**Affichage ≠ keyframes.** L3 et D-17 contraignent le **curseur**, qui reste
linéaire en milliards d'années. Les colonnes, elles, sont placées là où l'image
change. L'interpolation à l'affichage fait le raccord — c'est l'objet du champ
`time_axis.display`.

## 6. Paramétrage par cellule — héritage à trois niveaux

Bloc `cells` du JSON :

```
defaults   →  by_row   →  by_cell        (le plus spécifique gagne)
```

| Niveau | Ce qui s'y trouve |
|---|---|
| `defaults` | résolution de sortie, règles de bande, cible de ton, état dissous |
| `by_row` | ce qui dépend de l'échelle et n'est pas dérivable de la loi géométrique |
| `by_cell` | les écarts d'une cellule précise — **vide au départ** |

Éditer `J7` ne touche alors rien d'autre. En v3 les paramètres étaient répartis
entre `zeldovich`, `tone_mapping`, `field_evolution` et `layers[]`, tous couplés :
aucune cellule n'était modifiable isolément.

**La fenêtre de dissolution d'une ligne est un paramètre lu aux colonnes
communes**, jamais un axe du temps privé. Une ligne dont l'amplitude est quasi
nulle à la colonne 2 rend un champ *uniforme mais grainé* (C8) — pas un aplat.

## 7. Valeurs restant à calibrer

Explicitement marquées `À CALIBRER` dans le JSON. Elles ne doivent pas être
inventées : chacune sort d'une mesure headless.

| Bloc | Ce qu'il reste à établir |
|---|---|
| `cells.defaults.contrast_rolloff` | la loi de décroissance du contraste avec l'échelle, qui remplace le plafond de 150 Mpc (B3, D-25) |
| `web_ambient.amplitudes` | 7 lignes à sprites au lieu de 3 en v3 (A8) |
| `sprites.visible_fade_band_mpc` | la bande d'extinction des sprites, à replacer sur l'arête `G|H` (D1, D4) |
