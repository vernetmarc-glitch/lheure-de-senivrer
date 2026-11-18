# État des chantiers — 2026-11-18 23:10

- **A_voisinage_537941** : halos 21713, total 21734, etape paquet prêt, taille_Mo 16.5
- **B_grande_boite_points** : etape écarté (18/11) : bruit de tirage, tuiles gardées ; voir docs/approches-ecartees.md
- **C_rendu_voisinage** : etape P3 522530 publié en l'état (18/11 14 h) ; à refaire avec 537941 quand A est prêt
- **D_maillage_fin** : etape essai 3 lancé (16 h 20) : boîtes moyenne ET petite refaites, départ tiré dans les cellules (GIGUE) contre le treillis ; tranche 10 Mpc/h pour la moyenne. À l'arrivée : planche /tmp/moy.py sur 8775 (v3) contre 8772 (actuel), garder si plus beau, contrôle du treillis < 2,5, calcul completed success, run 44333882615, donnees v3 prêtes : moyenne, petite
- **E_treillis_toile** : etape constaté, non corrigé (anisotropie du maillage aux époques jeunes) ; voir docs/approches-ecartees.md ; piste : tranche hors axes ou chantier D
- **C_bascule_voisinage** : etape terminé et publié (18/11, commit 551efc8) : voisinage 537941, 21 713 halos ; batterie 76/76
- **retours_18_11_soir** : carre_blanc corrigé (décodage entier, contrôle GPU), publié 4de4894, remontee ≈17 s, freinage naine 5,2 Ga et arrivée, publié 551efc8

Ce passage : serveur 8766 relancé ; serveur 8771 relancé
