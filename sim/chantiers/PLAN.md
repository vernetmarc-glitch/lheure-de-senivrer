# Plan des chantiers (demande de Marc, 18/11/2026, 13 h 30)

L'agent est réveillé toutes les 30 minutes environ. À chaque réveil :

1. `python3 sim/chantiers/maitre.py` : constater, relancer, avancer les étapes mécaniques.
2. Prendre le premier chantier non terminé ci-dessous et avancer d'une étape. Règle 0 bis :
   contrôle d'abord, montré en échec, puis la correction.
3. Avant toute publication : la batterie complète (`maquette/controles.py`) sur la page servie
   avec les données réelles (`/tmp/v2g`, port 8771). Publier seulement si tout passe : GitHub
   Pages (`wt-main`, `app/public/carte`) et l'artefact.
4. Noter l'état dans `etat.json` (clé du chantier), committer `[skip ci]` sur `fond-de-carte`.
5. Envoyer à Marc un court message seulement quand un chantier se termine ou bloque.
6. Reprogrammer le réveil suivant ; s'arrêter quand tous les chantiers sont terminés.

## B — La grande boîte en points (fond de carte aux très grandes échelles)
- Données : `sim/sorties-v2/sorties-v2-grande` (32 époques, 400 000 points).
- But : remplacer les tuiles de la grande boîte par des points, comme la toile ; mêmes copies
  pivotées et décalées, même ton.
- Contrôles existants à garder : pas de dallage (46 et 90 Gal), grain aux très grandes échelles,
  sphères lisibles au grand champ.
- Nouveau contrôle : couche « points » seule au grand champ (plus de tuiles grande boîte).

## C — Le rendu du voisinage animé (P3)
- 18/11 13 h 50 : refait proprement (paquet complètement chargé, 12 s d'attente), le rendu à 2,5 et
  4 Ga est correct (planche /tmp/hd.png) : les défauts vus plus tôt venaient d'une capture faite
  pendant le chargement, et des traînées de la toile v2 (chantier E). Prochaine étape : batterie
  complète avec le paquet 522530 (dossier /tmp/v2c, port 8773), puis publication « en l'état »
  (demande de Marc, 9 h 29), puis bascule sur 537941 quand A est prêt.
- Défauts constatés (18/11) : vers 2,5 Ga, champ saturé et traînées verticales ; vers 4 Ga,
  voisinage presque vide alors que les données y placent une soixantaine de halos.
- Le faire sur le voisinage autour de 537941 (chantier A) dès que son paquet est prêt.
- Nouveaux contrôles : à 2,5 Ga, pas de traits droits ; à 4 Ga, des halos autour de nous.

## E — Traînées en treillis de la toile aux petites échelles, époques jeunes
- À 0,01 Gal (10 Mal) et 1,2–2,5 Ga, la toile montre des alignements horizontaux et verticaux :
  la grille de départ de la simulation, agrandie au-delà de sa résolution (aussi avec l'ancienne
  toile, moins marqué). Piste : plancher du noyau lié à l'espacement des points de la tranche,
  plus fort aux époques jeunes ; contrôle par la puissance spectrale du profil moyen (pic/médiane),
  sans grille ni catalogue.

## A — Voisinage autour de 537941 (mécanique, `maitre.py`)
- Téléchargement des histoires de halos, puis empaquetage en `tng/historiques537.bin`.

## D — Simulation à maillage plus fin
- Proposer d'abord à Marc le découpage en calculs enchaînés (reprise sur point de sauvegarde),
  avant de lancer quoi que ce soit.
