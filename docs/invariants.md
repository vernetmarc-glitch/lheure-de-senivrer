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

**État au 29 juillet 2026 : INV-G1 est EN ÉCHEC.**
`HALO_GROWTH = 8.5` au lieu de 1,2. À corriger, avec recuisson des 9 sprites.

---

## Résultats du premier passage — 29 juillet 2026

| Contrôle | Cible | Résultat |
|---|---|---|
| INV-G1 | constantes conformes | ❌ `HALO_GROWTH = 8.5` |
| INV-E1 à E5 sur `l3` | signature de rendu | ✅ 6/6 |
| INV-E4 sur `l4a` | isotropie | ❌ **0,60** |

Deux vrais défauts détectés au premier lancement, dont un vieux de trois
semaines.

---

## Règle d'usage

1. **Avant toute cuisson**, exécuter `--source` et `--constants`. Un échec
   **bloque**.
2. **Après toute cuisson**, exécuter `--render` sur chaque texture produite.
3. **Tout nouvel échec rencontré en session devient un invariant**, avec sa date
   et l'exigence qu'il protège. Un invariant ne se retire que sur décision
   explicite de Marc.
4. Un seuil qui gêne ne se desserre pas sans écrire pourquoi, ici.
