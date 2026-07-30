# Approches écartées — code conservé pour traçabilité

**Ne pas réutiliser ce code.** Il implémente des approches **mesurées puis
écartées**, documentées dans `docs/approches-ecartees.md` avec la mesure qui les a
disqualifiées.

Il est conservé pour une seule raison : qu'une session future puisse **vérifier**
une mesure citée plutôt que refaire l'exploration.

| Fichier | Approche | Écartée parce que |
|---|---|---|
| `mcpm_web.py` | MCPM / Physarum | mousse, 123 structures contre 512, anisotropie 1,44 |
| `pm_gravity.py` | Particle-mesh | netteté 1,17, pire que Zel'dovich seul ; anisotropie 1,28 |
| `profils.py` | Comparaison de profils radiaux | question O-01 toujours ouverte, ce code n'a servi qu'aux montages |
| `continuity_GF.py` | Test de continuité sur dépôt CIC | mesure historique : corrélation 0,08-0,43 |
| `run_variant.py` | Balayage de paramètres MCPM | idem MCPM |

Ce répertoire est **exclu du scan des invariants** : il porte volontairement des
motifs interdits.
