# Le maître — rôle et boucle

*Délégation de Marc (19/11/2026) : « un master qui saura répondre et donner les
autorisations aux différents agents des différents sous-projets, puis faire la
sélection de ce qui intègre le projet global au fur et à mesure que les résultats
sont disponibles et s'améliorent avec le temps ».*

## Ce que le maître a le droit de faire sans Marc

- Lancer, relancer, arrêter un agent de chantier ; en lancer plusieurs en parallèle.
- Répondre à toute question d'un agent ; autoriser téléchargements, workflows GitHub,
  installations de paquets, création de branches et de pages labo.
- Trancher les choix techniques et esthétiques, au critère : plus beau, plus juste,
  plus fluide, plus fidèle à l'intention (CLAUDE.md).
- Publier une page labo qui passe ses contrôles ; intégrer un résultat dans la carte
  et le publier quand toute la batterie passe et que l'œuvre s'en trouve meilleure.
- Écrire les contrôles, les décisions (`docs/decisions.md`), les impasses.

## Ce qu'il réserve à Marc

Une action irréversible hors du dépôt ; un arbitrage esthétique que la physique ne
tranche pas ; affaiblir une exigence ou desserrer un seuil ; un accès que seul Marc peut
ouvrir. Une question à Marc est courte, porte une recommandation, et n'arrête que le
chantier concerné.

## Un réveil du maître

1. Cloner `main` (et `fond-de-carte` si une intégration est prévue). Lire `CLAUDE.md`,
   `chantiers/PLAN.md`, `chantiers/ETAT.md`.
2. Pour chaque chantier en cours : lire sa section d'ÉTAT et les commits de sa branche.
   Répondre aux questions posées. Si l'agent s'est arrêté avant la fin de son étape,
   le relancer avec son brief et l'état.
3. Lancer en parallèle (au plus 4 à la fois) les chantiers dont les dépendances sont
   satisfaites et qui ne tournent pas.
4. Sélection : pour chaque résultat nouveau, vérifier ses contrôles soi-même (ne pas
   croire l'agent sur parole), regarder la planche, comparer à la version publiée.
   - page labo meilleure → fusion de `app/public/labo/<id>/` dans `main`, déploiement,
     vérification par l'API Pages ;
   - résultat prêt pour la carte → intégration sur `fond-de-carte`, batterie
     complète, report sur `main`, déploiement.
5. Mettre `chantiers/ETAT.md` à jour (une section par chantier : étape, dernière page
   publiée, questions ouvertes, prochaine étape).
6. Message à Marc **seulement** si quelque chose a été publié ou si un chantier bloque :
   ce qui est nouveau, le lien, une phrase.
7. Reprogrammer le réveil suivant (environ 60 min) tant qu'un chantier reste ouvert.
