# Processus — ce qui empêche de reperdre le même temps

*Créé le 11/08/2026, après une séance où **six mesures se sont révélées fausses**
et où trois causes proposées pour un même chantier ont été réfutées l'une après
l'autre. Chaque règle ci-dessous est née d'une erreur datée et chiffrée. Aucune
n'est une bonne intention : chacune est adossée à un contrôle exécutable, parce
qu'une exigence sans contrôle est une exigence qui sera oubliée — c'est vérifié
cinq fois maintenant.*

---

## 1. Un contrôle sans témoin ne prouve rien

**La faute.** `T-016` exigeait une grandeur dans la bande (1,8 · 3,4). Personne
n'avait jamais mesuré ce que rend cette grandeur **là où il n'y a rien**. Réponse,
obtenue le 11/08 en tirant des positions au hasard : **2,61 à 2,70** — en plein
milieu de la bande. Le contrôle récompensait donc l'**absence** de galaxie, et
contredisait `T-077` qui exige l'inverse. Il avait tenu des mois.

Trois autres contrôles ont eu le même défaut le même jour : `T-023` (témoin :
nuage translaté au hasard, 50 % ± 18), `T-011` (témoin : images sans
correspondance, 10,2 à 11,0 px), `T-052` (témoin : semis de Poisson, 0,480 alors
que la théorie annonce 0,523).

**La règle.** Tout contrôle qui compare une grandeur d'image à un seuil doit
publier, au registre, **ce que cette grandeur vaut sur un témoin sans le
phénomène**. Si le témoin tombe dans la bande acceptée, le contrôle est faux.

**Le corollaire, plus dur.** Un témoin se construit en **détruisant le
phénomène**, pas en changeant l'échelle. Translater, faire tourner, effacer.

---

## 2. Un banc de falsification doit lui-même être falsifié

**La faute.** Le banc de `T-016` modifiait `b[…, −14:65]` — une tranche **vide**
en indexation négative, l'objet mesuré étant à `cx = 25`. Trois épreuves « sans
réaction » ont été crues concluantes avant que la vérification des coordonnées ne
montre que rien n'avait jamais été modifié.

**La règle.** Avant de conclure qu'un contrôle ne réagit pas, **prouver que la
perturbation atteint bien ce qui est mesuré** — en vérifiant que la grandeur
intermédiaire a changé, pas seulement le verdict final.

---

## 3. Une cause plausible n'est pas une cause mesurée

**La faute.** Pour le chantier O-07, trois causes ont été proposées avec assurance
puis réfutées : le Ψ frais (6 à 12 % du déplacement, marginal), la dalle de
projection (la tendance s'inverse : la paire prédite la pire est la meilleure
mesurée), la bande spectrale non transmise (1,0 à 1,7 px sur 9,0). La vraie cause
— l'ancrage du catalogue, 7,08 px sur 9,01 — n'est apparue qu'avec une
**décomposition terme à terme** qui redonne la mesure à 0,3 px près.

**La règle.** Ne pas modifier le générateur sur une hypothèse. Construire d'abord
un **budget d'erreur** qui reproduit la mesure observée, terme à terme. Tant que
la somme des termes ne redonne pas le chiffre mesuré, la cause n'est pas trouvée.

**Le piège dans le piège.** Une décomposition dont un terme dépend d'une
**reconstruction** ne prouve rien sur le générateur : la première tentative
attribuait 3,67 Mpc à « la part héritée mal reconstituée », alors que la
reconstruction elle-même avait 11 % d'erreur.

---

## 4. Une mesure sans son domaine de validité est un chiffre

**La faute.** `raccord.calibration` conservait un balayage du 30/07 sans dire
**sur quelle paire** il avait été fait. `k_cut_safety = 1,0` a donc été réessayé —
une cuisson complète perdue — sans savoir que le calibrage portait sur la seule
paire `M→L`, où l'écart en pixels est invisible parce que la cellule y est
quarante fois plus grande.

**La règle.** Toute valeur calibrée s'écrit avec **l'objet sur lequel elle a été
mesurée**, et pas seulement la valeur. Contrôlé par `T-105`.

---

## 5. Un paramètre déclaré doit être lu

**La faute, deux fois le même jour.** `sprites.procedural.gain` était déclaré dans
la matrice et le code utilisait un littéral. Puis `web_gain`, muet depuis le
07/08, son littéral coïncidant **par chance** avec la matrice — donc invisible
jusqu'à ce qu'une valeur posée reste sans effet.

**La règle.** Tout bloc de la matrice qui doit agir est inscrit dans la liste de
`T-095`, qui compare valeur **déclarée** et valeur **effective après import**.

---

## 6. Un contrôle retiré reste au registre

**La faute.** Retirer `T-023` rendait le plan de test définitivement incomplet, et
la seule issue apparente était d'**effacer son histoire** — l'inverse de la
non-régression.

**La règle.** La ligne qui retire un contrôle porte le mot `RETIRÉ`, la date et le
motif. `T-000` la reconnaît et cesse de le réclamer, sans que la trace disparaisse.

---

## 7. Tout contrôle porte sa date et le retour qui l'a motivé

**La faute.** Mesure du 11/08 : **68 contrôles sur 102** n'avaient aucune trace
datée. `T-016` et `T-011` ont coûté plusieurs heures à être redécouverts.

**La règle.** `T-104`, à cliquet : le nombre de contrôles tracés ne descend pas.
Le passé se rattrape par lots ; un contrôle neuf ne peut plus naître sans trace.

---

## 8. Une exigence se vérifie sur le FAIT, pas sur la déclaration

**La faute.** `T-067` lisait la **table de paramètres** et exigeait une force
d'ancrage décroissante. Quand le mécanisme a été retiré, il bloquait toute
configuration — y compris celle où il n'y avait plus rien à décroître.

**La règle.** Un contrôle mesure l'**effet dans l'image ou dans le dépôt**, pas
l'intention écrite dans un fichier de réglages.

---

## 9. Contrainte opérationnelle — les cuissons ne survivent pas aux pauses

Une cuisson complète prend **12 à 15 minutes**, une cuisson de `H` seule 4 à 9, et
`H` frôle la limite mémoire du bac à sable. Deux faits vérifiés :

- un processus enchaînant plusieurs cuissons de `H` **se fait faucher** après la
  première : un essai par tour, en `setsid nohup` ;
- une cuisson **ne survit pas à une longue pause** entre deux tours. Elle doit
  être accompagnée par des attentes courtes et successives dans une même séance
  de travail. Deux cuissons ont été perdues ainsi, mortes aux lignes `J` et `L`.
- **nettoyer `/tmp/bake_*` avant de lancer** : neuf répertoires accumulés ont
  précédé l'une de ces morts.

---

## 10. L'état de l'art tranche ce que le réglage ne peut pas trancher

**Le cas.** D4 exigeait une influence décroissante, D6c une action précoce,
B1/B2 interdisaient l'incrément entre lignes. **Cinq configurations cuites,
aucune ne satisfait les trois.** Ce n'était pas un défaut de code mais une
contradiction d'exigences.

La sortie n'est venue ni d'un arbitrage ni d'un réglage, mais d'une **question
posée à l'observation** : que voit-on réellement entre les galaxies à ces
échelles ? Réponse : rien — les baryons du réseau sont un gaz à 10⁵–10⁷ K dont 30
à 50 % échappent encore à toute détection. L'exigence qui créait le conflit était
**contraire au ciel**, et sa disparition a dissous le nœud.

**La règle.** Quand deux exigences se contredisent et qu'aucun réglage ne les
concilie, **vérifier d'abord laquelle est fausse** — avant d'arbitrer entre elles.
