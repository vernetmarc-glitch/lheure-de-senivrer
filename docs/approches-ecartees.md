# Approches écartées

**Ne pas les reproposer.** Chaque entrée porte la **mesure** qui l'a écartée, pas
une impression.

**Pourquoi ce document existe.** Sept impasses ont été explorées et documentées de
façon narrative, donc introuvables. La session du 28 juillet 2026 a proposé MCPM
avec enthousiasme et l'a classé premier de neuf méthodes — avant de le rejeter
trois jours plus tard sur mesure. Une impasse non consignée se reparcourt.

**Règle.** Reproposer une approche de cette liste exige d'expliquer **ce qui a
changé** depuis la mesure qui l'a écartée.

---

## Générateurs de toile cosmique

### Transformation log-normale sur champ gaussien
*Moteur de production historique.*
**Écartée** : ne produit pas de filaments, mais des taches diffuses. La
transformation étant ponctuelle, elle ne peut pas créer de structure filamenteuse
qui n'est pas déjà dans le champ.

### Crêtes de la matrice hessienne (NEXUS+ / MMF)
**Écartée** : donne une **mousse** de cellules, pas une toile. La hessienne d'un
champ gaussien a des crêtes partout, à toutes les échelles, sans connectivité
privilégiée. *Reste utile comme **validateur*** des fractions de volume
nœuds/filaments/murs.

### Squelette de Morse (DisPerSE)
**Écartée** : grains uniformes. Le filtrage par persistance, qui aurait pu tuer la
mousse, n'avait pas été appliqué — l'approche n'est donc pas formellement
disqualifiée, mais elle reste un détecteur, non un générateur.

### Dépôt CIC d'une grille advectée par Zel'dovich
*Moteurs v3.2 et v3.3.*
**Écartée pour raison structurelle** : corrélation du **champ** entre layers
adjacents 0,79-0,95, corrélation après **dépôt** 0,08-0,43. Cause : un opérateur
spatialement non linéaire ne commute pas avec un changement de fenêtre.
`NonLin(resample(x)) ≠ resample(NonLin(x))`. **Aucun réglage ne peut corriger
cela.**

### MCPM / Physarum (Monte Carlo Physarum Machine)
**Écartée** : produit une **bulle par halo**, donc une mousse — 123 structures
distinctes contre 512 dans la référence, et anisotropie 1,44. Rien dans sa
dynamique ne reproduit l'effondrement **anisotrope**, qui est ce qui fabrique les
filaments.
⚠ *Classée premier choix le 25 juillet sur analyse théorique, rejetée le 28 sur
mesure.* L'article Elek/Burchett fait **ajuster** un réseau à des galaxies déjà
connues — un problème d'interpolation entre nœuds donnés, non de génération.

### Particle-mesh à résolution modeste
**Écartée** : netteté des pics **1,17**, pire que Zel'dovich seul (1,26), et
anisotropie remontée à 1,28. Avec 884 k particules la résolution de force vaut
2,34 Mpc, plus qu'un amas réel : les nœuds ne *peuvent pas* se compacter, et la
grille CIC des forces réimprime l'artefact axial. Exigerait 512-1024³ avec
raffinement adaptatif.

### Dépôt direct des positions d'agents
**Écartée** : résolution effective **0,992** contre 0,886 pour la référence — donc
plus floue que tout le reste — contraste 1,12 contre 0,51, bimodalité de retour.

---

## Mécanismes de dissolution

### `A(s,a)` appliqué par bande de k
**Écartée** : physiquement fausse. En théorie linéaire le facteur de croissance
s'applique **identiquement à toutes les échelles** ; la hiérarchie de formation est
une conséquence **émergente** de la non-linéarité. Imposer `a_form` par bande
faisait survivre les petites échelles artificiellement — 80 % d'amplitude à
λ=1,6 Mpc contre 0 % à λ≥53 Mpc — et elles envahissaient l'image.
Symptôme observé : nombre de structures ×3,8 pendant la dissolution.
*Remplacée par le facteur global `D(a)` — décision D-05.*

### Halos ajoutés à la toile (masse non conservée)
**Écartée** : la dissolution **ne se termine jamais**. Les patches sphériques
isolés ne pavent pas l'espace, il reste 13,96/255 de structure lissée à `a=0,01`
contre 0,65 pour le verre pur.
*Remplacée par le prélèvement dans la toile — décision D-07.*

### Croissance du rayon de splat sans conservation du flux
**Écartée deux fois** : documentée comme corrigée le 10 juillet, **violée en
production**, redécouverte le 28. Flux mesuré ×77 sur le sprite `andromede`,
correspondant exactement au ×72 prédit par σ² de 0,5 à 4,25 px. La tache grossit
sans jamais pâlir.
*Sous contrôle par l'invariant INV-D2 et INV-G1.*

### Flou gaussien comme mécanisme de transition
**Écartée** : passe-bas par construction. Effondrement mesuré de la variance du
laplacien.

### Bruit de valeur lisse comme source de structure
**Écartée** : passe-bas également. *Dérogation limitée pour la modulation des
sprites — décision D-14.*

### Mélange vers une couleur unie
**Écartée** : recrée exactement le défaut interdit par §11.3 de l'architecture.

---

## Choix de représentation

### Normalisation du champ à variance unité par boîte
**Écartée** : artefact de code (`f / f.std()`), pas une physique. Rendait
l'amplitude de déplacement proportionnelle à la boîte — **932 Mpc à `l5`** — et
faisait dépendre la cohérence inter-layer d'une normalisation arbitraire.
*Remplacée par la normalisation absolue σ₈ — décision D-08.*

### Boîtes cubiques
**Écartée** : on ne rend jamais qu'une tranche mince. À `l5`, calculer une boîte
cubique gaspille un facteur **39** de volume, et ce gaspillage se paie en
résolution : la cellule atteint 182 Mpc et la toile n'est plus résolue du tout.
*Remplacée par la dalle anisotrope — décision D-09.*

### Rayon d'objet en fraction de boîte
**Écartée deux fois**, les 28 et 29 juillet : donne **769 Mpc** à `l5` là où un
amas fait 2,2.
*Sous contrôle par l'invariant INV-C1.*

---

## Métriques écartées

| Métrique | Pourquoi |
|---|---|
| `peak_sharpness` à fenêtre de 11 px fixes | mesure une taille physique différente à chaque layer ; a fait diagnostiquer un « creux » inexistant |
| σ brut comme indicateur de structure | mélange structure et bruit de grenaille ; stagnait à 41/255 même dissous |
| `frac>0` de la trace | la diffusion la porte à 1,0 partout, sans information |
| Élongation globale des nuages | ne discrimine pas mousse et toile (1,87 contre 1,78 pour la référence) |
| Pic spectral à la fréquence de maille | mauvaise signature ; l'artefact de grille est une **anisotropie directionnelle**, pas une périodicité |
