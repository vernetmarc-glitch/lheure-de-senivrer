# Maquette de référence (artefact « L'Heure de s'enivrer »)

Page publiée en artefact : carte en distances propres, deux curseurs (zoom
vertical, temps horizontal), trois sphères, lumière en comètes scintillantes,
trois scénarios, loupe, matière en WebGL, Voie lactée TNG50 au zoom maximal.

## Fichiers servis à côté de `index.html`

| fichier | contenu | fabriqué par |
|---|---|---|
| `matiere.txt` | 250 000 particules de la petite boîte (512³, 300 Mpc/h), 10 époques, base64 | `sim/post.py` |
| `tuiles/{petite,grande}-a*.jpg` | densité projetée des deux boîtes, 11 époques | `sim/post.py` puis `sim/reton.py` |
| `voie-lactee.txt` | 40 000 étoiles TNG50 suivies une à une sur 48 époques | `sim/tng/suivi.py` |
| `voie-lactee-gaz.txt` | 12 000 cellules de gaz froid par intervalle, 47 intervalles | `sim/tng/gaz.py` |

## Chaîne de la Voie lactée (TNG50-1, subhalo 522530 aujourd'hui)

1. `sim/tng/telechargement.py 522530 DOSSIER 48 0.8` avec `MODE=halo` : découpes du
   groupe (satellites compris) aux 48 époques ; `CHAMPS=gaz` pour le gaz et son SFR.
   Clef dans la variable `TNG_API_KEY`, jamais dans le dépôt.
2. `sim/tng/suivi.py` : tirage stratifié en date de naissance (assez de jeunes étoiles
   à chaque époque, poids compensateur), repère du disque d'aujourd'hui, centre sur
   le progéniteur (arbre SubLink), nombre de tours entre époques tiré de la courbe
   de rotation médiane.
3. `sim/tng/gaz.py` : gaz qui forme des étoiles, un échantillon par intervalle ; la
   page fond deux échantillons voisins aux raccords.
4. `sim/tng/apercu.py` : même interpolation que le shader, pour les planches et films.

## Tons (bornes fixes, aucune statistique de l'image)

- matière : `dl = log10(1+D/m) + 0,25·log10(1+G/m)`, noir sous `dl = 0,30`
  (la densité moyenne est noire : vides noirs, structures brillantes) ;
- tuiles : même borne, recalculée par `sim/reton.py` (palette feu inversée), plus un
  coupe-bande sur la grille de départ (période 8 px) et un lissage des seules zones
  peu denses ; grande boîte à 0,34 ;
- au-delà de la résolution de la simulation (≲ 30 Mal), les particules restent des
  points de 1 à 2 px (« galaxies ») au lieu de taches floues ;
- galaxie : étoiles par kpc², borne basse 10^0,6, épaule douce (pas de saturation).

## Pavage

Chaque copie de boîte est tournée d'un quart de tour et/ou retournée selon un tirage
fixe (celle qui nous contient reste droite) ; sous 256 px par copie, super-tuile de
4×4 copies orientées.

## Contrôles

`python3 maquette/controles.py URL` : 10 contrôles mesurés sur la page servie,
chacun lié au retour de Marc qu'il protège (toile noire et brillante, matière visible
à 3,3 Ga, pas de dallage, sphères lisibles, Voie lactée visible et non saturée, bras
spiraux, danse sans saut, aucune erreur JS). Le contrôle de dallage échoue sur la
version du 16/11 à 20 h (excès 0,44) et passe ensuite (0,04).
