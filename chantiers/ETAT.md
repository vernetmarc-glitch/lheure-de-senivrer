# État des chantiers

*Tenu par le maître ; chaque agent met à jour sa propre section (étape, page, questions).*

Départ (19/11/2026, 7 h 40) : `bake.py --check` sur `main` : 399 passés, 15 en échec,
0 bloquant (anciens chantiers de la grille A→O, hors refonte). Carte en production :
81 contrôles de page sur `fond-de-carte`, tous verts au 19/11 4 h.

## S0 — Fondations
Étape : lancé le 23/11 (compteur commun, lecteur vidéo).

## S1 — Soleil
Étape : interrompu le 19/11 (limite d'usage), relancé le 23/11 avec les directives du jour.

## S2 — Planètes et Lune
Étape : à lancer (vague 2).

## S3 — Terre, continents
Étape : données préparées par workflow (19/11) ; relancé le 23/11.

## S4 — Climat et glaces
Étape : attend S3.

## S5 — Vie
Étape : attend S4.

## S6 — Humanité
Étape : **passage 2 terminé** (23/11) — `labo/humanite/`, branche `chantier/humanite`.
Passage 1 publié par le maître (d9626e4, D-45 : HYDE 3.2.1 + ONU 2023, hypothèse affichée).
Contrôles : **15/15** sur la page servie (`controles-resultat.txt`) ; les 4 nouveaux montrés
d'abord en échec (`controles-echec-passage2.txt` : C12 0,47–0,63, C13 R ≈ 1, C15 91,7 %).
Planche : `chantiers/planches/humanite-2.png` (2 Ma, 100 000, 46 000 — le contact —, 10 000 ans, aujourd'hui).

Passage 2 :
- **traînées radiales** (C12, cohérence du tenseur de structure de la teinte des territoires
  ≤ 0,45 ; mesuré 0,22–0,39) : c'était la texture de lichen bloquée en T (CLAMP) au sud de
  l'équateur, pas la croissance ; bruit des vitesses aussi lissé ;
- **foyers** (C13, indice de Clark et Evans ≤ 0,6 ; mesuré 0,13–0,15) : avant l'Holocène
  les points vont par 5 autour de foyers qui durent ~ 40 générations, écart ≈ 50 km ;
- **contact** (C14 : 7 instants sur 16 entre 60 et 30 ka où une maille de 5° porte des
  points de sapiens et de Néandertaliens/Dénisoviens ; seuil 6) : foyers attirés vers les
  zones de coexistence, liseré de couleur mêlée renforcé, dernière lueur de la lignée qui
  s'efface (recul) ; le contact se lit vers 46 000 ans (à 40 000 ans les Néandertaliens
  sont déjà éteints dans le modèle) ;
- **Timmermann et al. 2022** (C15 : 3 187/3 245 entrées, 98,2 %, ≥ 90 % par espèce) : les
  entrées à une espèce servent de contraintes de calage (arrivée et persistance locale),
  élargissent les domaines d'erectus/Néandertaliens ; échecs restants : sapiens précoce
  en Asie orientale (≈ 100 ka, hors des portes du modèle), Néandertaliens de Sibérie
  orientale et de Mongolie intérieure (Jinsitai) non reliés au domaine ;
- **vitesse du front selon l'habitabilité de l'instant** (habitats de Timmermann, 1°, pas
  de 5 ka puis 25 ka) : × (0,35 + 1,3 × habitabilité), neutre là où le modèle ne dit rien
  (Amériques, Sahul).

Ce qui manque : les foyers de contact restent peu nombreux (marge de C14 faible) ; points
d'avant l'Holocène sans calottes glaciaires (S4) ; densité intra-maille HYDE de 2017 pour
toutes les tranches.

Prochaine étape : jonction avec le globe de S3 ; contact plus lisible (effectifs régionaux
plutôt que globaux, carte de l'admixture néandertalienne/dénisovienne pour le liseré
permanent).

### Question au maître (S6)
Accès à HYDE 3.3 : le dépôt d'Utrecht (geo.public.data.uu.nl, public.yoda.uu.nl) répond
par une page anti-robots à toute machine ; je ne la contourne pas. Recommandation : garder
HYDE 3.2.1 (écart faible sur 10 000 av. J.-C. → 2017) ; si Marc ou le maître peut
télécharger à la main `HYDE 3.3 / baseline` (zip « pop »), le déposer dans une release
GitHub du dépôt : le workflow le prendra. Rien ne bloque la page en attendant.

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
