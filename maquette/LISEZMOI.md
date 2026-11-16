# Maquette de référence (artefact « L'Heure de s'enivrer »)

Source de la page publiée en artefact le 16/11/2026 : carte en distances propres,
deux curseurs (zoom vertical, temps horizontal), trois sphères, lumière en
comètes scintillantes, trois scénarios, loupe, matière en WebGL.

- `index.src.html` : la page ; les tuiles `__O015__`… sont remplacées à la
  construction par les images de la simulation (base64), et la page charge
  `matiere.txt` (données des particules) à côté d'elle.
- `pm_demo.py`, `matiere_demo.py`, `render2.py` : la simulation 208³ de démonstration
  et la préparation de ses données. L'étape 2 les remplace par `sim/pm.py` et `sim/post.py`.
