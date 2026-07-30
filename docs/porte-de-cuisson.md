# ⛔ PORTE DE CUISSON — à lire avant de générer le moindre layer

**Statut au 30 juillet 2026 : LA CUISSON EST INTERDITE.**

Le générateur produit des layers qui **violent des exigences client connues**.
Lancer une cuisson maintenant produirait une série à refaire.

**Instruction de Marc, 30 juillet 2026 :**
> « Si le générateur donne des layers qui ne respectent pas les règles alors la
> prochaine instance devra le corriger avant de cuire quoi que ce soit. »

---

## Ce qui bloque

### ⛔ B1 — Héritage à 100 % : NON SATISFAIT

`docs/demandes-client.md` **B1** : *« en changeant de layer, la matière visible ne
doit jamais être redistribuée. »* C'est la contrainte la plus forte du projet.

**État** : le raccord spectral parent → enfant sur dalle anisotrope est **faux**.
Mesure : δ passe d'un écart-type de 6,28 à **85,8**, Ψ de 10 à **2 253 Mpc**.
L'héritage est donc **désactivé** dans `gen_full.py`.

Cause probable : le sous-volume du parent interpolé a une moyenne et une variation
lente non nulles, qui deviennent d'énormes modes de basse fréquence que
`Ψ ∝ δ/k` amplifie.

Le **mécanisme** est validé par ailleurs — corrélation 0,913 à 0,998, identité
d'objet à **0,00 px** (`test2_heritage.py`, `test2b_identite.py`,
`test2b_bandes.py`). C'est le **portage** sur dalle anisotrope qui est à refaire.

### ⛔ B2 — Similarité entre layers voisins : NON SATISFAIT

Conséquence directe de B1. Sans héritage, les dix textures sont indépendantes :
en montant dans les layers on perd les détails haute fréquence au lieu de les
conserver avec apparition d'échelles plus grandes. **Défaut explicitement signalé
par Marc le 29 juillet.**

### ⛔ INV-E4 — Isotropie : EN ÉCHEC sur deux layers

`l4a` sort à **0,60** et `l3b` à **0,75**, contre l'intervalle requis
[0,85 ; 1,20]. Excès de puissance diagonale, **non expliqué**.

### ⚠ D1 — Raccord sprites ↔ densité : NON TESTABLE

Les layers A, B et C ne sont pas cuits. `morphologies.py` et `bake_sprites.py`
sont prêts mais n'ont jamais été branchés sur le catalogue complet.

---

## Conditions de levée

La cuisson devient autorisée quand **les quatre** sont remplies, chacune
**mesurée**, pas estimée :

| # | Condition | Contrôle |
|---|---|---|
| 1 | Le raccord spectral produit `rms(Ψ)` dans [3, 12] Mpc et `std(δ)` cohérent avec `σ(cellule)` attendu | `INV-C3`, comparaison à la table de `norm_abs.py` |
| 2 | Corrélation inter-layer ≥ 0,85 et déplacement médian des objets partagés ≤ 1,5 px, **à plusieurs époques** | `INV-F2`, `INV-F3` |
| 3 | Isotropie dans [0,85 ; 1,20] sur **les dix** layers | `INV-E4` |
| 4 | `invariants.py --render` passe sur chaque texture produite | groupe E complet |

**Et la condition transverse** : la signature de `docs/reference-visuelle.md` doit
être approchée, sans oublier que cette signature *écarte* les rendus faux mais ne
*valide* pas les bons — le regard de Marc reste le juge (trois rendus conformes
sur six ou sept métriques ont été rejetés en juillet 2026).

---

## Ce qui est en revanche prêt à servir

| Brique | Fichier | État |
|---|---|---|
| Normalisation absolue σ₈ | `norm_abs.py` | ✅ validée, facteur 1652,7 invariant |
| Dalle anisotrope | `slab_test.py` | ✅ validée, corrélation des spectres 0,996 |
| Croissance globale `D(a)` | `test2b_bandes.py` | ✅ validée |
| Identité d'objet, graine par halo | `test2b_identite.py` | ✅ validée, 0,00 px |
| Dissolution en filaments | `test4_filaments.py` | ✅ validée, élongation 1,30 → 2,39 |
| Halos à masse conservée | `gen_full.py` | ✅ validée, dissolution complète |
| Seuil de résolution des halos | `gen_full.py` | ✅ éteint les halos sur M, L, K, J |
| Morphologies + cuisson sprites | `morphologies.py`, `bake_sprites.py` | ✅ prêts, non branchés |
| Mesure de signature | `mesure_reference.py` | ✅ opérationnel |
| **Raccord spectral** | `gen_full.py` → `field()` | ⛔ **CASSÉ** |

---

## Avertissement sur ces scripts

Ce sont des scripts de **recherche**, produits en une session, non des scripts de
production. Ils portent les défauts suivants, connus :

- `gen_full.py` a l'héritage désactivé ;
- `reference_a1.py` a produit la référence du commit `f0e0203f`, désormais
  **caduque** (variance unité par boîte, sans dalle anisotrope) ;
- `mcpm_web.py`, `pm_gravity.py`, `profils.py`, `continuity_GF.py`,
  `run_variant.py` relèvent d'**approches écartées** — voir
  `docs/approches-ecartees.md`. Conservés pour la traçabilité des mesures, **pas
  à réutiliser** ;
- la cuisson pleine résolution demande **1 492 M cellules et 6,0 Go**, hors de
  portée d'un bac à sable : elle doit tourner sur une machine de cuisson.

### Les scripts de recherche violent eux-mêmes des invariants

`invariants.py` les signale en `RECHERCHE … (non bloquant)` :

| Fichier | Violation |
|---|---|
| `zel_particles.py:197,202` · `gen_full.py:140` | rayon normalisé par `mass.max()` — INV-B1 |
| `norm_abs.py:4` · `test2_heritage.py:80` | normalisation par l'écart-type courant — INV-B1 |
| `bake_one.py:13` · `zel_particles.py:118` | filtre spatial après la courbe de ton — INV-D1 |

**Ces défauts doivent être corrigés avant qu'un de ces scripts ne devienne
production.** Le périmètre du contrôle distingue `scripts/` (bloquant) de
`scripts/dev/` (signalé) : un portail qui échoue sur du code de recherche
deviendrait du bruit et cesserait de protéger la production.

Le contenu de chaque mesure citée ici est dans
`docs/test-en-cours-generateur-particules.md`, qui est un **journal** — voir son
bandeau.
