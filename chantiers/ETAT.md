# État des chantiers

*Tenu par le maître ; chaque agent met à jour sa propre section (étape, page, questions).*

Départ (19/11/2026, 7 h 40) : `bake.py --check` sur `main` : 399 passés, 15 en échec,
0 bloquant (anciens chantiers de la grille A→O, hors refonte). Carte en production :
81 contrôles de page sur `fond-de-carte`, tous verts au 19/11 4 h.

## S0 — Fondations
Étape : lancé le 23/11 (compteur commun, lecteur vidéo).

## S1 — Soleil
Étape : 1ᵉʳ passage (19→23/11). Page `labo/soleil` construite, **pas encore publiable** :
les données de la simulation à 1e5 particules ne sont pas encore déposées.

- **Chaîne** (`app/public/labo/soleil/sim/`, workflow `chantier-soleil.yml`) : Phantom
  (commit a9ecce4) compilé sur machine GitHub ; cœur de Bonnor-Ebert 1,2 M☉, rayon 0,15 al,
  10 K, rotation β ∈ {0,005 ; 0,01 ; 0,02} en parallèle, barotrope, puits à 1e-10 g/cm³
  (rayon 10 UA) ; 3 étapes de 5 h chaînées avec reprise ; extraction au fil de l'eau
  (32 768 points, positions 16 bits, température, longueur de lissage) ; variante retenue
  par critère écrit ; dépôt des données + `diagnostic/etape_N.txt` après chaque étape.
- 1ᵉʳ lancement (23/11, 4 h 52) : les trois étapes 1 ont échoué après 5 h — disque plein
  (plus d'un millier de sorties de 12 Mo). Corrigé (extraction et effacement au fil de
  l'eau, particules relaxées `shuffle_parts`), relancé le 23/11 à 10 h 48 (run 45159388255).
  Données attendues vers 16 h UTC (étape 1), puis ≈ 21 h et ≈ 2 h.
- **Page** : WebGL2, densité de colonne en noyaux de largeur physique (h), couleur par la
  température (palette de la carte), ton à bornes fixes avec exposition liée au cadre
  (loi fixe Σ ∝ 1/R, jamais tirée de l'image), caméra sur le rayon de 10 % de la masse,
  vue oblique à 50° (comme HL Tauri), rotation au doigt, curseur log de part et d'autre
  de la naissance (−150 000 ans → +100 Ma), luminosité BHAC15, dissipation du disque
  (e-fold 2,5 Ma, hypothèse), compteur commun (`commun/compteur.js`).
- **Contrôles** (18) : 13 passés, 5 en échec, mesurés sur une simulation locale de
  contrôle (Phantom, 3e4 particules, non publiée) : D05 disque (rapport d'aspect 0,65 à
  < 1 000 UA — l'enveloppe y est encore), D06 agglutination (facteur 6 < 10 : la
  simulation locale s'arrête 9 000 ans après la naissance), D09 (table BHAC15 non encore
  lue : fausse table de test), P02 points brillants (le rendu en densité de colonne est
  lisse ; pas de « myriade de points »), P09 **anneaux HL Tauri : 0** (ne se forment pas).
- Planche : `chantiers/planches/soleil-1.png` (simulation locale de contrôle, 3e4 particules).
- **Ce qui manque** : données 1e5 (en cours) ; scintillement en points (rendu hybride
  noyau + point) ; filaments (turbulence initiale, fichiers de vitesse de Phantom) ;
  anneaux : ils ne naissent pas d'un effondrement en gaz seul — il faut des planètes
  enfouies et la poussière (SPH à deux fluides de Phantom : Dipierro et al. 2015 ont
  reproduit HL Tauri ainsi), prochaine étape du chantier, sans peindre les anneaux.
- Prochaine étape : relever `diagnostic/etape_1.txt` et les données déposées, vérifier
  la table BHAC15, régler le ton sur les vraies données, rendu hybride, contrôles verts
  hors P09 ; puis simulation disque + poussière + planètes pour P09.

## S2 — Planètes et Lune
Étape : à lancer (vague 2).

## S3 — Terre, continents
Étape : données préparées par workflow (19/11) ; relancé le 23/11.

## S4 — Climat et glaces
Étape : attend S3.

## S5 — Vie
Étape : attend S4.

## S6 — Humanité
Étape : lancé le 23/11 (globe de nuit autonome, HYDE 3.3, Black Marble).

## S7 — Alpes
Étape : relief réel et simulation recalculés par workflow (19/11) ; relancé le 23/11.

## S8 — Glaciers
Étape : données Seguinot 2018 préparées, contrôles écrits (0/8 sur page vide) ; relancé le 23/11.

## Questions au maître
(aucune)

## Journal du maître
- 19/11 7 h 40 : vague 1 lancée ; 19/11 ≈ 8 h : tous les agents arrêtés par la limite d'usage hebdomadaire.
- 23/11 5 h 50 : directives de Marc (références visuelles, styles, vidéo, compteur) ; vague 1 relancée, S0 et S6 lancés.
- 23/11 ≈ 7 h 30 : limite de 5 h atteinte (remise à 10 h 40). Publiés : compteur et vidéo (S0), puis glaciers (S8, 10/10). 11 h 45 : reprise de S7, S3, S1 ; S6 et S8 au réveil suivant.
