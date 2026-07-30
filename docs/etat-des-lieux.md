# État des lieux — 30 juillet 2026

**Document de passation.** À lire après `docs/demandes-client.md` et avant toute
proposition. Décrit l'**état réel**, pas l'historique.

> ## ⛔ LA CUISSON EST INTERDITE EN L'ÉTAT
>
> Le générateur produit des layers qui violent **B1** (héritage à 100 %), **B2**
> (similarité entre layers voisins) et **INV-E4** (isotropie, en échec sur `l4a`
> et `l3b`). Le raccord spectral est cassé.
>
> **Aucun layer ne doit être cuit avant correction.** Conditions de levée,
> mesurables, dans **`docs/porte-de-cuisson.md`**.
>
> *Instruction de Marc, 30/07/2026.*

---

## Ce qui est acquis

### Méthode

La documentation est structurée en trois niveaux, avec ordre de lecture imposé
(`docs/prompt-systeme-projet.md`) :

| Document | Rôle |
|---|---|
| `demandes-client.md` | ce que l'œuvre doit montrer — **source de vérité sur le besoin** |
| `architecture-univers-observable.md` | comment c'est réalisé |
| `invariants.md` + `scripts/dev/invariants.py` | ce qui ne doit jamais arriver — **exécutable** |
| `decisions.md` | 20 décisions tranchées, 4 questions ouvertes |
| `approches-ecartees.md` | 15 impasses, chacune avec la mesure qui l'a écartée |
| `reference-visuelle.md` | l'image cible et ses 10 grandeurs mesurées |

`.github/workflows/invariants.yml` exécute les contrôles **de façon bloquante** à
chaque push.

### Correctifs appliqués en production

- **`HALO_GROWTH` 8,5 → 1,2** et **conservation du flux** dans
  `generate_dissolution_sprites.mjs`, avec recuisson des 9 sprites (126 frames).
  Flux sur `andromede` : ×77 → ×2,18 ; pic 1,000 constant → 0,067. Commit
  `5957ae6f`. *(L'architecture exigeait ces deux points depuis le 10/07 ; le code
  les violait.)*

### Résultats de recherche validés par la mesure

Tous dans `docs/test-en-cours-generateur-particules.md`.

| Acquis | Mesure |
|---|---|
| Le dépôt CIC ne peut **pas** transmettre la cohérence inter-layer | corrélation champ 0,79-0,95 → après dépôt 0,08-0,43 |
| Les particules à positions continues, elles, la transmettent | corrélation 0,913 à 0,998 |
| L'identité d'objet peut être **exacte** | déplacement médian **0,00 px** pour les halos partagés |
| Le verre est indispensable et gratuit | réseau nu : anisotropie 2,7 × 10⁹ à dissolution totale ; verre : 1,08 |
| La dalle anisotrope est valide | corrélation des spectres 0,996 jusqu'à 6 Mpc d'épaisseur |
| La normalisation absolue σ₈ fait émerger la physique | σ(cellule) 6,76 à `l1b` → 0,0075 à `l5` ; Ψ → ~7 Mpc |
| La croissance doit être **globale**, pas par bande | par bande : nombre de structures ×3,8 pendant la dissolution |
| Les halos doivent **prélever** leur masse dans la toile | sinon la dissolution stagne à 13,96/255 au lieu de 0,65 |

---

## Ce qui est cassé ou inachevé

### Bloquant — le raccord spectral

L'héritage à 100 % (**exigence B1**, la plus forte du projet) repose sur un
raccord spectral parent → enfant. Le portage sur dalle anisotrope est **faux** :
δ passe d'un écart-type de 6,28 à **85,8**, et Ψ de 10 à **2 253 Mpc**.

Cause probable : le sous-volume du parent interpolé a une moyenne et une variation
lente non nulles, qui deviennent d'énormes modes de basse fréquence que `Ψ ∝ δ/k`
amplifie.

Le **mécanisme** est validé par ailleurs (corrélation 0,913, identité 0,00 px) ;
c'est ce portage qu'il faut refaire. **C'est le premier chantier.** Il débloque
aussi l'exigence B2 — les layers au-dessus de F doivent se ressembler.

### Ouvert

| Sujet | État |
|---|---|
| `INV-E4` sur `l4a` et `l3b` | anisotropie 0,60 et 0,75, non expliquée |
| Layers A, B, C | non cuits. `morphologies.py` et `bake_sprites.py` sont prêts |
| Cuisson pleine résolution | 1 492 M cellules, 6,0 Go — hors de portée d'un bac à sable, trivial sur une machine de cuisson |
| Référence `a=1` | celle du commit `f0e0203f` est **caduque** (variance unité par boîte, sans dalle) |
| Deux sphères sur trois | `cosmology.ts` les calcule, `UniverseMap.tsx` n'en trace qu'une |
| §14 de l'architecture | vitesse de la lumière, parcours guidés, deux résolutions : **rien n'existe** |
| Matrice | `uniform_floor = 129,4` et le facteur de cascade sont **obsolètes** (décision D-02) |

---

## Chantiers, par ordre d'utilité

1. **Réparer le raccord spectral sur dalle anisotrope.** Débloque B1 et B2.
2. **Expliquer l'anisotropie de `l4a` et `l3b`.** Deux invariants en échec.
3. **Recuire la série complète D → M** en chaîne emboîtée, pleine résolution, et
   établir la nouvelle signature d'acceptation à `a=1`.
4. **Cuire A, B, C** et mesurer le raccord C/D objet par objet.
5. **Tracer les trois sphères.** Le sujet de l'œuvre n'est rempli qu'au tiers,
   alors que les données existent.
6. Concevoir §14.1 à §14.3 — demandent des décisions de Marc.

---

## Deux avertissements

**Sur les métriques.** Quatre fois dans ce projet, une conclusion fausse a été
tirée d'une métrique exprimée en pixels au lieu d'unités comobiles. Toute fenêtre
de mesure s'exprime en Mpc ou en fraction d'image. Invariant INV-A1.

**Sur les statistiques globales.** Quatre fois, une grandeur dépendant d'une somme,
d'un maximum ou d'un percentile a cassé l'héritage **silencieusement**. Aucune
grandeur par objet ne doit en dépendre. Invariants INV-B1 à B3.

Ces huit occurrences sont la principale cause des semaines perdues. Elles sont
désormais des tests, non des paragraphes.
