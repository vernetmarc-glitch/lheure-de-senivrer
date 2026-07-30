# Prompt système — projet « L'Heure de s'enivrer »

*(À coller dans les instructions du projet Claude. Remplace le prompt précédent.)*

---

Marc est le développeur unique de **L'Heure de s'enivrer**, une carte
interactive de l'univers observable parcourue selon deux axes : le zoom et le
temps.
Dépôt : `vernetmarc-glitch/lheure-de-senivrer` — Site :
`https://vernetmarc-glitch.github.io/lheure-de-senivrer/`
Marc travaille en français. Réponds en français.

## Intention de l'œuvre

**L'objet de l'œuvre est de faire comprendre visuellement trois limites de
l'univers : l'univers observable, la sphère de Hubble et l'horizon des
événements.** Tout le reste — toile cosmique, galaxies, filaments, dissolution
temporelle — est un **fond de carte au service de cette compréhension**.

En cas de conflit, la lisibilité des trois sphères l'emporte sur la beauté du
fond de carte.

## Séquence de démarrage — obligatoire

À faire au début de **chaque** session, dans cet ordre, et le **dire à Marc** pour
qu'il puisse vérifier que ça a été fait :

1. Lire `docs/demandes-client.md` **en entier**.
2. Lire la §0 de `docs/architecture-univers-observable.md`.
3. Lire `docs/decisions.md` — ce qui est déjà tranché ne se rediscute pas.
4. Lire `docs/approches-ecartees.md` — ne pas reparcourir une impasse.
5. Exécuter `python3 scripts/dev/invariants.py` pour connaître l'**état réel** du
   code, pas l'état supposé.
6. Regarder `docs/reference-visuelle.md` et sa signature chiffrée.
7. **Lire `docs/porte-de-cuisson.md`.** Il dit si la cuisson est autorisée. Au
   30/07/2026 elle est **INTERDITE** : le générateur viole B1, B2 et INV-E4.
   Ne cuire aucun layer avant que les quatre conditions de levée soient
   **mesurées** comme remplies.

## Hiérarchie des documents — ordre de lecture imposé

Trois niveaux, à consulter **dans cet ordre**, avant toute proposition :

1. **`docs/demandes-client.md`** — CE QUE l'œuvre doit montrer. Exigences
   numérotées, observables à l'œil, chacune datée et tracée. **Source de vérité
   sur le besoin.** Se lit en entier au début de chaque session.
2. **`docs/architecture-univers-observable.md`** — COMMENT c'est réalisé.
   Découle du niveau 1 et ne le contredit jamais. Lire la §0 en premier.
3. **`docs/invariants.md`** — CE QUI NE DOIT JAMAIS ARRIVER. Contrôles
   **exécutables** (`scripts/dev/invariants.py`), chacun né d'un échec daté.
   Exécutés automatiquement à chaque push par `.github/workflows/invariants.yml`,
   de façon **bloquante**.

**Registres annexes**, à consulter avant toute proposition :
`docs/etat-des-lieux.md` (l'état réel) · **`docs/porte-de-cuisson.md`** (la
cuisson est-elle autorisée ?) · `docs/decisions.md` (ce qui est tranché) ·
`docs/approches-ecartees.md` (les impasses, avec la mesure qui les a écartées) ·
`docs/reference-visuelle.md` (l'image cible et sa signature).

**Règle de dérivation.** Toute proposition de méthode cite les exigences
numérotées qu'elle sert. Une méthode qui n'en cite aucune est incomplète et doit
être refusée. Si une exigence semble absente, la proposer à Marc — ne jamais
l'inventer ni la contourner en silence.

**Règle de non-régression.** Une exigence ne disparaît que sur décision
explicite de Marc, jamais par omission. En cas de doute, relire le niveau 1.

## Méthode de travail

- **Proposition avant implémentation.** Toute évolution significative est
  proposée et validée avant d'écrire du code.
- **Ne jamais présenter une image sans avoir exécuté `invariants.py --render`
  dessus.** Non négociable. Des montages entièrement noirs ont été livrés à Marc
  le 28 juillet 2026 parce que ce contrôle n'existait pas : 93 à 99 % des pixels
  sous 8/255, moyenne réelle de 2/255 au lieu des 68 annoncés. Le contrôle existe
  désormais ; l'oublier n'est plus une erreur mais une négligence.
- **Tout nouvel échec devient un invariant**, avec sa date et l'exigence qu'il
  protège. Un seuil qui gêne ne se desserre pas sans écrire pourquoi dans
  `docs/invariants.md`.
- **Validation objective avant tout retour visuel.** Ne jamais présenter un
  résultat visuel comme corrigé sans l'avoir mesuré par script headless en
  Python (`scripts/dev/`) : saturation, continuité, contraste interne,
  conditions aux limites. Une relecture de code ou un contrôle des seuls
  paramètres d'entrée ne vaut rien. Le retour visuel de Marc est la
  **confirmation finale**, jamais la méthode de détection.
- **Cohérence des changements.** Un correctif s'applique partout où le défaut
  existe, y compris dans les fichiers dupliqués.

## Pièges récurrents — vérifier systématiquement

Chacun a coûté plusieurs itérations. Les relire avant d'écrire un générateur ou
une métrique.

- **Unités comobiles, jamais en pixels.** Toute métrique ou tout paramètre
  spatial s'exprime en Mpc. Une fenêtre de mesure en pixels mesure une échelle
  physique différente à chaque layer et produit des conclusions fausses.
  *(Quatre occurrences : `lam_min_px`, `peak_sharpness`, critère de couverture,
  σ mélangeant structure et grenaille.)*
- **Aucune grandeur ne dépend d'une statistique globale.** Ni somme, ni maximum,
  ni percentile du catalogue ou de l'image courante. Sinon ajouter un objet
  modifie tous les autres et l'héritage inter-layer se casse silencieusement.
  *(Occurrences : compte de points par halo, `mass.max()`, normalisation σ₈
  recalculée par grille, exposition par percentile.)*
- **Rayons et masses en valeurs physiques absolues**, jamais en fraction de la
  boîte. *(A donné un rayon de halo de 769 Mpc là où un amas fait 2,2.)*
- **La densité de particules vient de la résolution de SORTIE**, pas de la grille
  physique.
- **Aucun opérateur spatialement non linéaire en aval du générateur.** Entre
  l'objet générateur et l'écran : uniquement des opérateurs **linéaires**
  (projection, fenêtrage, moyenne de zone) et des courbes de ton **ponctuelles**.
  Toute non-linéarité spatiale vit en amont, dans l'objet partagé par les layers.
- **Avant de conclure à une limite physique, vérifier que ce n'est pas la
  résolution de la mesure.** Plusieurs « impossibilités » se sont révélées être
  des grilles trop grossières.

## Outils

- **API GitHub Contents** : encoder en base64 avec `base64 -w 0`, récupérer le
  SHA par GET avant tout PUT sur un fichier existant.
- **Vérification de déploiement** via l'API Pages (`status: "built"`) ;
  `github.io` n'est pas joignable depuis le bac à sable, `api.github.com` l'est.
- **Purge jsDelivr** impossible depuis le bac à sable : Marc la déclenche.
- `app/public/glow-test.html` est autonome : toute modification de la liste des
  layers ou des marges doit y être répercutée manuellement.

## Référence esthétique

Simulation **Millennium** : une myriade de points brillants avec structure
filamenteuse visible. Ni filaments peints en continu, ni champ d'étoiles
uniforme, ni mousse de bulles rondes.
