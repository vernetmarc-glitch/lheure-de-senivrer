# Invariants — ce qui ne doit jamais arriver

**Niveau 3 de la hiérarchie documentaire.**
Niveau 1 : `docs/demandes-client.md` (le besoin) · Niveau 2 :
`docs/architecture-univers-observable.md` (la méthode) · **Niveau 3 : ce
document** (les garde-fous).

---

## Pourquoi ce document est du code et pas de la prose

Le document d'architecture exigeait la **conservation du flux** des sprites
depuis le **10 juillet 2026**, avec sa raison exacte, et interdisait explicitement
un facteur de croissance de `×8,5`. Le code de production utilise
`HALO_GROWTH = 8.5` et ne conserve pas le flux. **Rien ne l'a détecté pendant
trois semaines**, jusqu'à ce que le défaut soit redécouvert par la mesure le
28 juillet.

La conclusion n'est pas qu'il fallait mieux écrire la règle. Elle était écrite,
juste, et bien placée. La conclusion est qu'**une règle qui ne s'exécute pas
n'empêche rien**.

Chaque invariant de ce document est donc un **contrôle exécutable**, dans
`scripts/dev/invariants.py`, né d'un **échec daté**, et rattaché aux exigences
qu'il protège.

```
python3 scripts/dev/invariants.py --source      # statique, sur le code
python3 scripts/dev/invariants.py --constants   # code vs architecture
python3 scripts/dev/invariants.py --render f    # sur une texture cuite
```

**Code de sortie 0 si tout passe, 1 sinon. À brancher en pré-cuisson bloquant.**

---

## Groupe A — Métriques : jamais en pixels

*Quatre occurrences. Le piège le plus fréquent du projet.*

| ID | Invariant | Origine |
|---|---|---|
| **INV-A1** | Aucune métrique spatiale n'a de fenêtre par défaut exprimée en pixels | `lam_min_px` (juillet) ; `peak_sharpness` à fenêtre de 11 px (28/07) |
| **INV-A2** | La fenêtre de netteté vaut une taille **comobile** constante (~3 Mpc) | 28/07 — a fait diagnostiquer un « creux » de netteté qui n'existait pas |
| **INV-A3** | σ de structure mesuré **après lissage**, jamais σ brut | 28/07 — σ brut stagnait à 41/255 même dissous, dissolution jugée bloquée à tort |

*Protège : B2, B5.*

---

## Groupe B — Aucune dépendance à une statistique globale

*Quatre occurrences. Le piège le plus destructeur : il casse l'héritage
silencieusement.*

| ID | Invariant | Origine |
|---|---|---|
| **INV-B1** | Aucune grandeur par objet issue d'une somme, d'un maximum ou d'un percentile du catalogue | 28/07 — compte de points en part d'un budget global : ajouter un halo changeait la luminosité de tous les autres |
| **INV-B2** | Le facteur de normalisation est **invariant par grille** (<2 %) | 29/07 — σ₈ recalculé par grille faisait passer Ψ à 78 Mpc à M |
| **INV-B3** | Le nuage d'un objet est **identique hors contexte** | 28/07 — `mass.max()` dans le rayon : écart de 0,78 Mpc selon le contenu du catalogue |

*Protège : B1 (héritage à 100 %).*

---

## Groupe C — Grandeurs physiques absolues

| ID | Invariant | Origine |
|---|---|---|
| **INV-C1** | Rayon d'objet en Mpc absolus, jamais en fraction de boîte (< 20 Mpc) | **Deux fois** : 28/07 (raccord C/D) puis 29/07 (`gen_full.py`) — 769 Mpc à M là où un amas fait 2,2 |
| **INV-C2** | Densité projetée dans [4, 40] particules/px — fixée par la résolution de **sortie** | 28/07 — 1,15 px⁻¹ à G contre 16 à D : ANISO 0,72, 26 % de noir |
| **INV-C3** | Déplacement rms dans [3, 12] Mpc — grandeur physique | 29/07 — renormalisation par boîte donnait 932 Mpc à M |

*Protège : A3, A4, B5.*

---

## Groupe D — Opérateurs interdits en aval

| ID | Invariant | Origine |
|---|---|---|
| **INV-D1** | Aucun filtre spatial appliqué **après** la courbe de ton | §11.2, §11.3 |
| **INV-D2** | Un splat qui s'élargit **conserve son flux** (facteur < 3) | 10/07 documenté, **violé en production**, redécouvert le 28/07 : flux ×77 mesuré sur `andromede` |

*Protège : E1, E2, E3, C1, C2.*

---

## Groupe E — Signature de rendu

| ID | Invariant | Seuil |
|---|---|---|
| **INV-E1** | Moyenne dans [65, 70]/255 | exigence F |
| **INV-E2** | Saturation < 1 % clair, < 10 % noir | E4 |
| **INV-E3** | Distribution **continue** — creux bimodal ≤ 0,35 | A6 |
| **INV-E4** | Isotropie axes/diagonales ∈ [0,85 ; 1,20] | E5 |
| **INV-E5** | Contenu haute fréquence ≥ 1e-3, **jamais nul** | C8 |
| **INV-E6** | Positions initiales en **verre**, jamais en réseau | 28/07 — le réseau donnait une anisotropie de **2,7 × 10⁹** à dissolution totale |

---

## Groupe F — Cohérence de la matrice zoom × temps

| ID | Invariant | Seuil |
|---|---|---|
| **INV-F1** | `A(λ, a=1) = 1` **exactement**, toute échelle | §11.4.b |
| **INV-F2** | Corrélation inter-layer ≥ 0,85 | B1, B2 |
| **INV-F3** | Identité d'objet : déplacement médian ≤ 1,5 px | B1 |
| **INV-F4** | Écart de moyenne inter-layer ≤ 2/255 | D2 |
| **INV-F5** | Hors-cadre ≤ 5 % | B6 |

---

## Groupe G — Dérive du code par rapport à son architecture

**C'est le contrôle le plus important de ce fichier**, parce qu'il est le seul qui
détecte une classe d'erreur que ni la relecture humaine ni la mémoire n'ont
attrapée en trois semaines.

| ID | Invariant | Origine |
|---|---|---|
| **INV-G1** | Les constantes du code correspondent aux valeurs du document d'architecture | 29/07 — `HALO_GROWTH = 8.5` contre `1.2` documenté |

Constantes actuellement sous contrôle :

| Fichier | Constante | Attendu | Référence |
|---|---|---|---|
| `generate_dissolution_sprites.mjs` | `HALO_GROWTH` | 1,2 | §11.4.b |
| `generate_dissolution_sprites.mjs` | `POINT_SIZE` | 0,5 | §11.4.b |
| `generate_dissolution_sprites.mjs` | `FILAMENT_AMOUNT` | 0,8 | §11.4.b |
| `generate_layers.py` | `NS` | 0,965 | §4.3 |

**État au 30 juillet 2026 : INV-G1 PASSE.**
`HALO_GROWTH` corrigé à 1,2 et conservation du flux implémentée
(`fluxNorm = 1/widen²`) ; les 9 sprites ont été recuits (126 frames).
Flux mesuré sur `andromede` : **×77 → ×2,18** ; pic **1,000 constant → 0,067**.
État formé à `a=1` inchangé (flux `f00` = 830 identique). Commit `5957ae6f`.

---

## Groupe H — Grille de la matrice zoom × temps

**Origine : 30 juillet 2026.** La matrice v3 déclarait 11 colonnes communes,
mais les fichiers cuits portaient **un axe du temps par ligne**. `st_l5_k04.png`
valait `a = 0,891` quand la colonne 4 déclarée valait `a = 0,480`. Sept lignes
sur treize n'avaient aucune image avant `a = 0,794`, soit avant 10,7 Ga : le
rendu comblait avec le ton dissous uniforme. Bilan : 143 cellules déclarées,
114 fichiers, 2 lignes vides, **42 aplats**.

| ID | Invariant | Protège | Né de |
|---|---|---|---|
| **INV-H1** | L'échelle de zoom est géométrique, raison constante à 5 % près | B2, D2 | le trou de ×24 entre `B` et `C`, masqué par un fondu local de 0,52 dex |
| **INV-H2** | La bande de déplacement est non vide sur chaque ligne | B3, C8 | plancher de 6 px = 410 Mpc contre plafond de 150 Mpc → `Ψ = 0`, std = 0,00 |
| **INV-H3** | Aucun paramètre en pixels dans les blocs de génération | B5, B2 | `lam_min_px`, quatrième occurrence du même piège |
| **INV-H4** | Les 165 cellules existent, aucune manquante, aucune hors grille | D3 | 143 déclarées contre 114 fichiers |
| **INV-H5** | Continuité temporelle entre colonnes voisines d'une même ligne | **D3** | aucun contrôle n'existait — le document client appelle D3 « la contrainte la plus facile à oublier » |
| **INV-H6** | Aucun aplat parmi les actifs cuits | **C8**, B6 | voir ci-dessous |
| **INV-H7** | Densité de particules ≥ 4/px **dans la fenêtre magnifiée** | B1, B2 | INV-C2 tenait sur l'image entière et laissait passer 2,99/px là où ça compte |

### Pourquoi INV-H7 double INV-C2

INV-C2 exige 4 à 40 particules par pixel, et la borne était **tenue** : 18,9/px
mesurées à la ligne `N`. Mais la comparaison entre deux lignes voisines ne porte
que sur le carré central du parent, de côté 1/2,520. La densité y tombe à
**2,99/px**, sous le plancher, et le rendu du parent magnifié est alors à 69 % du
bruit — auto-corrélation mesurée à 0,306 entre deux réalisations du verre.

C'est ce qui plafonnait F2 à 0,25 alors que le raccord lui-même tient 0,875.
En multipliant les particules du parent par 8 : densité 23,9/px,
auto-corrélation 0,789, F2 0,442.

*Mesurer une densité sur l'image entière ne protège pas la seule zone où elle
compte. C'est le même piège que les fenêtres en pixels du groupe A, transposé à
l'aire de mesure.*

### Pourquoi INV-H6 double INV-E5

INV-E5 (« contenu haute fréquence ≥ 1e-3, jamais nul ») existait depuis le
29 juillet et attrapait exactement ce défaut. Il n'a jamais été exécuté sur les
fichiers concernés : le mode `--render` ne prend **qu'un fichier à la fois, à la
demande**. `density_l5.png` et les 9 frames `st_l5_*` sont donc partis en
production à `std = 0,00` sur 1024² — un aplat de gris uni là où l'œuvre montre
l'univers observable dans son ensemble.

Le défaut n'était pas l'absence de règle. La règle était écrite, juste, et
exécutable. Le défaut était qu'**il fallait penser à la lancer**. Le mode
`--assets` balaie désormais tous les actifs sans qu'on ait à les nommer.

*C'est la même leçon que le groupe G, à un cran de plus : une règle exécutable
qui dépend de la mémoire de quelqu'un pour être exécutée n'est pas un garde-fou.*

### Périmètre de INV-H3 — resserré le 30/07, avec son motif

Au premier passage, H3 signalait `blur_max_px` et `min_render_core_px`. Examen
fait, ce sont des grandeurs **raster** : le flou de cuisson d'un sprite dans sa
propre trame de 512 px, et un plancher de lisibilité à l'écran. Leur sens ne
varie pas d'une ligne à l'autre.

Le piège n'est pas le pixel en soi, c'est **un pixel qui vaut une échelle
physique différente à chaque ligne** — `lam_min_px = 6` valait 0,6 Mpc en bas de
l'échelle et 410 Mpc en haut. H3 ne scanne donc que les blocs qui pilotent le
champ : `zoom_axis`, `time_axis`, `cells`, `expansion`, `embrasement`.

### État au 30 juillet 2026

```
invariants.py                → 7 passes, 0 échec   (définition de la grille)
invariants.py --assets       → 0 passe,  3 échecs  (actifs)
```

| Contrôle | Résultat |
|---|---|
| INV-H1, H2, H3 | **PASSENT** — la grille est saine |
| INV-H4 | **ÉCHEC** — 165 cellules manquantes, 114 fichiers hors grille |
| INV-H5 | **ÉCHEC** — aucune paire, cuisson non faite |
| INV-H6 | **ÉCHEC** — 42 aplats parmi 136 actifs |

C'est l'état attendu : la **définition** est arrêtée, la **cuisson** ne l'est
pas. Les actifs de la v3 sont périmés et seront retirés avec la première cuisson
au nouveau nommage.

---

## Résultats du premier passage — 29 juillet 2026

| Contrôle | Cible | Résultat |
|---|---|---|
| INV-G1 | constantes conformes | ✅ *(corrigé le 30/07, commit `5957ae6f`)* |
| INV-E1 à E5 sur `l3` | signature de rendu | ✅ 6/6 |
| INV-E4 sur `l4a` | isotropie | ❌ **0,60** |

Deux vrais défauts détectés au premier lancement, dont un vieux de trois
semaines. **INV-G1 a été corrigé le 30 juillet** ; INV-E4 sur `l4a` reste ouvert.

---

## Exceptions acceptées

Un portail rouge en permanence devient du bruit et perd son effet. Une violation
**connue et assumée** se déclare ici, avec sa raison et son échéance — elle n'est
jamais ignorée en silence. Le contrôle l'affiche alors comme `TOLERE`, non comme
`OK`.

| Invariant | Fichier | Raison | Levée prévue |
|---|---|---|---|
| INV-B1 | `generate_layers.py:155` | Normalisation par boîte du moteur log-normale de **production**. Défaut réel, mais sa correction exige l'adoption du générateur par particules | chantier 3 de l'état des lieux |
| INV-B1 | `generate_density_demo.py` | Script de démonstration, hors chaîne de cuisson | — |
| INV-B1 | `test_style_layer.py` | Script de test de style, hors chaîne de cuisson | — |

*Toutes acceptées le 30/07/2026.*

Une ligne peut aussi porter le commentaire `# invariant-ok` pour un cas
légitime ponctuel — mais une exception structurelle se déclare dans le tableau
ci-dessus, pas en commentaire.

---

## Deux limites du contrôleur, corrigées le 30/07/2026

**Il se détectait lui-même.** Ses expressions régulières contiennent les motifs
qu'il traque, ce qui produisait un faux positif systématique. Il s'exclut
désormais du scan.

**Il ratait le vrai défaut.** `generate_layers.py` normalise par
`std = field.std()` sur deux lignes — forme que la regex initiale ne voyait pas,
alors qu'elle voyait les deux scripts de démonstration. Le motif a été élargi.

Leçon : un contrôle qui passe n'est pas nécessairement un contrôle qui contrôle.
Tout nouvel invariant doit être vérifié **sur un cas connu comme fautif** avant
d'être considéré comme opérationnel.

---

## Règle d'usage

1. **Avant toute cuisson**, exécuter `--source` et `--constants`. Un échec
   **bloque**.
2. **Après toute cuisson**, exécuter `--render` sur chaque texture produite.
3. **Tout nouvel échec rencontré en session devient un invariant**, avec sa date
   et l'exigence qu'il protège. Un invariant ne se retire que sur décision
   explicite de Marc.
4. Un seuil qui gêne ne se desserre pas sans écrire pourquoi, ici.
