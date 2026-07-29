# Référence visuelle

**À quoi le fond de carte doit ressembler**, et comment le vérifier par la mesure.

Ce document complète `docs/demandes-client.md` §A1 (« la référence esthétique est
la simulation Millennium : une myriade de points brillants avec une structure
filamenteuse visible »). Une exigence formulée en mots ne suffit pas : sans image
cible **et** sans signature chiffrée, chaque nouvelle session repart de son
interprétation.

---

## L'image

`docs/reference-visuelle/reference-toile-cosmique.jpg`

Coupe de simulation cosmologique à N corps, palette noir → rouge sombre → orange
→ jaune-blanc. Fournie par Marc le 28 juillet 2026.

⚠ **Provenance à préciser par Marc** avant toute diffusion publique du dépôt. Si
l'image est issue d'une publication (Millennium / Max Planck, Illustris, Bolshoi),
elle demande une attribution, voire une autorisation. La **signature chiffrée
ci-dessous n'est en revanche pas concernée** : ce sont des mesures dérivées,
librement utilisables, et c'est elle qui sert réellement à valider.

---

## Signature mesurée — la cible

Mesures faites dans la palette « Astro » du projet, sur l'image recadrée de son
liseré (464 × 464).

| Grandeur | Cible | Ce qu'elle contrôle |
|---|---|---|
| **Moyenne** | **67,5** / 255 | luminosité générale — cohérent avec la bande validée [65, 70] |
| **Saturation claire** | **0,00 %** | aucune plage de blanc pur |
| **Saturation noire** | 4,7 % | les vides sont sombres mais pas vides |
| **Isotropie** axes/diagonales | **0,97** | aucun artefact de grille ni direction privilégiée |
| **Creux bimodal** | **−0,01** | **une seule population** de matière, pas deux calques |
| **Concentration du flux** (10 % les plus brillants) | **0,239** | la lumière est concentrée sans être ponctuelle à l'excès |
| **Structures brillantes** | **513** | densité de nœuds distincts |
| **Élongation médiane** | **1,79** | filaments, pas patates rondes |
| **Netteté des pics** | **3,19** | les nœuds sont piqués, pas étalés |
| **P(filament) / P(grenaille)** | **180,2** | structure organisée dominant le bruit de tirage |

---

## Usage

```
python3 scripts/dev/mesure_reference.py <image>            # signature brute
python3 scripts/dev/mesure_reference.py <rendu> --compare  # ecart a la cible
```

Le script inverse la palette Astro pour retrouver le ton, ce qui permet de
comparer un rendu du projet à l'image de référence **dans le même espace**.

**Toutes les fenêtres de mesure sont exprimées en fraction de l'image**
(1/40 pour la netteté), jamais en pixels absolus — sans quoi la comparaison entre
deux images de tailles différentes est fausse. C'est l'invariant INV-A1.

---

## Ce que la signature ne dit pas

Elle ne capture ni la **connectivité** du réseau — deux images peuvent avoir les
mêmes dix nombres et l'une ressembler à une mousse, l'autre à une toile — ni
l'agrément visuel. Elle sert à **écarter** les rendus manifestement faux, pas à
valider les bons. La validation finale reste le regard de Marc.

Trois échecs de cette nature ont été rencontrés en juillet 2026 : un rendu
conforme sur six métriques et jugé « mousse » ; un autre conforme sur sept et
jugé « pixelisé » ; un troisième dont la dissolution « ressemblait à une
explosion ». Chaque fois, une métrique manquait — et a été ajoutée après coup.
