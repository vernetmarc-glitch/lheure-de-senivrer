# Montée en complexité — moteur N-corps

**Statut : possibilité ouverte, non engagée.** Consigné le 30 juillet 2026 à la
demande de Marc, pour qu'une session ultérieure n'ait pas à redécouvrir ni le
raisonnement ni les chiffres.

Ce document n'est **pas** un registre d'impasse : rien ici n'a été écarté. C'est
une porte laissée ouverte, avec ce qu'il faut pour la franchir en connaissance de
cause.

---

## Pourquoi la question se pose

La référence esthétique du projet est la simulation **Millennium**
(Springel et al., *Nature*, 2005) — cf. `demandes-client.md` A1 et
`reference-visuelle.md`.

Le générateur actuel produit le champ par **déplacement de Zel'dovich**, soit de
la théorie des perturbations lagrangiennes au **premier ordre**. Millennium est
une simulation N-corps **Tree-Particle-Mesh** : de la gravité non linéaire
complète. Trois écarts sont structurels, et aucun réglage ne les comble :

| | Zel'dovich (actuel) | N-corps |
|---|---|---|
| **Croisement de nappes** | les particules se traversent, les filaments se **délavent** après croisement | les filaments s'effondrent et se resserrent |
| **Profils de halo** | inexistants — le projet les **greffe** artificiellement | émergent de la dynamique |
| **Sous-structure** | absente | satellites dans les amas |

C'est vraisemblablement ce qui rend trois cibles de la signature visuelle
difficiles à atteindre : **netteté des pics 3,19**, **élongation médiane 1,79**,
**P(filament)/P(grenaille) 180,2**. Ces trois chiffres décrivent des filaments
fins et contrastés ; Zel'dovich les donne épais et fondus.

---

## Ce que Millennium couvre de l'échelle du projet

Paramètres vérifiés (Springel et al. 2005, et base publique du MPA) :

| | |
|---|---|
| Particules | 2160³ ≈ 10 milliards |
| Boîte | 500 Mpc/h, soit **685 Mpc** de côté (h = 0,73) |
| Masse par particule | 8,6 × 10⁸ M☉/h |
| Adoucissement comobile | 5 kpc/h |
| Résolution des halos | 20 particules → 1,72 × 10¹⁰ M☉/h |
| Séparation moyenne | 0,32 Mpc |
| Cosmologie | Ωm = 0,25, ΩΛ = 0,75, σ₈ = 0,9, h = 0,73 |
| Coût | 11 000 pas de temps, 512 processeurs, 64 époques, ~20 To |

*(Millennium-II : même nombre de particules dans une boîte de 100 Mpc/h,
adoucissement 1 kpc/h, masse 6,9 × 10⁶ M☉/h. Meilleure résolution, volume cinq
fois plus petit.)*

Reporté sur l'échelle du 30/07 :

| Lignes | Demi-champ | Millennium |
|---|---|---|
| `A` → `D` | 0,035 → 0,56 Mpc | **non** — sous la résolution ; un halo de Voie lactée n'y compte que ~700 particules |
| `E` → `J` | 1,41 → 143 Mpc | **oui** — son domaine propre |
| `K` | 361 Mpc | **marginal** — le champ de 722 Mpc dépasse la boîte entière |
| `L` → `O` | 911 → 14 570 Mpc | **non** — 21 fois la boîte à `O` |

**Six lignes sur quinze, sept en forçant.**

Et pour `L`→`O` ce n'est pas un manque de moyens : **il n'y a plus de toile à ces
échelles.** σ(δ) mesuré à 0,043 sur la boîte de la ligne `O` (43 710 Mpc) — la
cosmologie elle-même l'impose (B3, « End of Greatness »). Chercher une référence
de type Millennium pour `O` serait chercher une structure qui n'existe pas.

---

## Ce qui n'est pas envisageable

- **Rejouer Millennium.** 512 processeurs, 20 To de sorties.
- **Télécharger ses instantanés.** La base publique du MPA sert des catalogues de
  halos et de galaxies, pas les positions de particules. S'y ajouterait la
  question d'attribution déjà ouverte en **O-04**.

## Ce qui l'est

Un **N-corps particule-maille (PM)** sur les lignes `E` à `K`. Ce n'est pas
Millennium — pas de raffinement en arbre, donc pas de sous-structure profonde —
mais c'est de la gravité non linéaire, et cela ferait l'essentiel du chemin sur
les trois écarts ci-dessus.

Ordre de grandeur, à vérifier avant tout engagement : 384³ particules sur une
maille de 768³ tiennent dans ~4 Go, quelques heures par ligne, soit une journée
ou deux de calcul sur une machine de bureau pour les lignes concernées.

Un `scripts/dev/pm_gravity.py` existe déjà — **non relu au 30/07**. L'ampleur
réelle du travail restant n'a pas été évaluée.

---

## Ce qu'il faudrait repenser

Le raccord spectral réparé le 30/07 vaut pour un champ construit par bandes de
`k`. Une **chaîne emboîtée de simulations N-corps** est un problème différent —
c'est le domaine des *zoom-in* (MUSIC, GADGET), où les conditions initiales de la
région raffinée sont générées avec les grands modes de la boîte parente et où la
matière extérieure est représentée par des particules massives.

Ce n'est pas un obstacle de principe, mais ce n'est pas non plus un branchement :
c'est une reprise du §4.4.

---

## Décision — tranchée par la mesure le 31/07/2026

Le retour visuel a eu lieu, et il est négatif : « sur le layer `H`, il n'y a
quasiment aucune structure haute fréquence apparue en plus par rapport au layer
`K` » — trois lignes plus haut, soit un facteur 16 de zoom sans structure neuve.

La cause a été cherchée ailleurs d'abord, et l'alternative la moins coûteuse a
été testée puis écartée : élargir la bande fraîche du raccord de 6 à 100 pixels
fait passer les vides de 10,2 % à 8,5 % du cadre au mieux, sans monotonie, pour
une cible de 5,0 %. Détail dans `approches-ecartees.md`.

**Le verrou n'est pas le raccord, c'est le moteur.** Zel'dovich disperse les
structures fines au lieu de les faire s'effondrer.

Portée réelle du blocage : la règle `web_ambient` fait dépendre les sept lignes à
sprites `A`→`G` de la seule texture de `H`, rééchantillonnée jusqu'à ×645. Si `H`
ne porte pas de structure fine, **aucune des quinze lignes n'en portera** sous
22 Mpc. C'est la moitié basse de l'œuvre qui est en jeu, pas un layer.

**Reste à l'arbitrage de Marc**, qui a indiqué être prêt à payer du calcul pour
un résultat plus esthétique.

*(Formulation initiale : à trancher après retour visuel — question ouverte
**O-07**.)* L'écart au visuel Millennium doit être
constaté à l'œil avant qu'un changement de moteur soit engagé. Marc a indiqué le
30/07 être prêt à payer du calcul pour un résultat plus esthétique ; la question
n'est donc pas le coût, mais de savoir si l'écart le justifie.
