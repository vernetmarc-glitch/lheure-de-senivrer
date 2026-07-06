"""
Source UNIQUE des constantes utilisées pour représenter les galaxies RÉELLES
du Groupe Local (Andromède, M33, Nuages de Magellan, etc.) à travers les
différents scripts de génération.

Pourquoi ce fichier existe : ces mêmes constantes étaient auparavant
dupliquées indépendamment dans generate_layers.py (ancrage L1b) et
generate_local_group_texture.py (texture Groupe Local), avec des valeurs
différentes. Une correction faite dans un seul des deux fichiers ne se
répercutait pas dans l'autre — c'est exactement ce qui a provoqué la
régression du 6 juillet (fusion des galaxies réelles en une seule plaque,
l'ancien rayon 0.59 étant resté dans generate_layers.py après avoir été
corrigé ailleurs).

Règle : toute évolution de la taille/luminosité des galaxies RÉELLES doit
passer par CE fichier, jamais être redéfinie localement dans un script.

Ne concerne PAS les galaxies PROCÉDURALES (non nommées) : celles-ci n'ont pas
besoin de cohérence inter-fichiers de la même façon (pas de rendu ponctuel
JS à aligner), leurs constantes restent propres à
generate_local_group_texture.py.
"""

# Rayon (sigma) du halo d'une galaxie réelle, en Mpc. Volontairement petit :
# avec 8 galaxies réelles regroupées sur ~1 Mpc, un rayon trop large les fait
# fusionner en une seule plaque au lieu de rester des pics distincts.
REAL_GALAXY_HALO_SIGMA_MPC = 0.05

# Facteur multiplicatif du bruit ambiant local autour d'une galaxie réelle
# (0 = silence total, 1 = bruit inchangé) — permet à la bosse de la galaxie
# de dominer visuellement sans que le bruit alentour ne la brouille.
REAL_GALAXY_NOISE_SUPPRESSION = 0.15  # le bruit local descend a ~15% de son amplitude
REAL_GALAXY_SUPPRESSION_RADIUS_FACTOR = 0.55  # relatif a REAL_GALAXY_HALO_SIGMA_MPC

# Facteur d'amplitude de la bosse dominante (par rapport a l'amplitude de
# base ln(1+brightness*AMPLITUDE)) — doit rester nettement au-dessus du bruit
# ambiant (champ normalise a variance ~1).
REAL_GALAXY_DOMINANT_AMPLITUDE_FACTOR = 3.5

# Amplitude de contraste commune (utilisee par toutes les formules de
# luminosite de galaxie, reelles et procedurales, pour rester coherentes).
GALAXY_BRIGHTNESS_AMPLITUDE = 3.5
