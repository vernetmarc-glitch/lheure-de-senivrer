# État des chantiers

*Tenu par le maître ; chaque agent met à jour sa propre section (étape, page, questions).*

Départ (19/11/2026, 7 h 40) : `bake.py --check` sur `main` : 399 passés, 15 en échec,
0 bloquant (anciens chantiers de la grille A→O, hors refonte). Carte en production :
81 contrôles de page sur `fond-de-carte`, tous verts au 19/11 4 h.

## S0 — Fondations
Étape : passage 1 fini (23/11) — les deux composants communs sont prêts, branche
`chantier/fondations`. Planche : `chantiers/planches/fondations-1.png`.

Ce qui marche :
- **Compteur de vitesse du temps** (N28) : `app/public/commun/compteur.js`, module ES sans
  dépendance, cadran SVG (Cinzel et Jost servies avec le module, licence OFL, dans
  `commun/polices/`). API : `creeCompteur(conteneur, {coin, marge, taille})`,
  `c.vitesse(ansParSeconde, sens)`, `c.etat()`, `c.detruit()`. Échelle : -135° (1 an/s)
  → +135° (10 Ga/s), 27° par décade ; butée à -146° ; aiguille amortie (ressort ζ 0,78) et
  animation coupée au repos ; ne capte aucun geste. Page `labo/compteur/` (`?planche=1` :
  galerie de six vitesses ; `?essai=1` : sans faux temps). **Contrôles 39/39 verts**
  (`app/public/labo/compteur/controles.py`).
- **Lecteur de texture vidéo** (N27) : `app/public/commun/video.js` :
  `await creeLecteurVideo(gl, [{url, codec}…], {surImage})` → `allerImage(n)`,
  `allerTemps(s)`, `allerFraction(f)`, `texture`, `detruit()`. Démultiplexeur MP4 écrit
  (pas de bibliothèque), WebCodecs AV1 puis H.264 selon `isConfigSupported`, cache LRU
  de 24 textures WebGL2 (plafonné à 96 Mo), le décodeur suit la tête de lecture
  (avancer = 1 décodage, reculer = cache, saut ≤ 8) ; repli `<video>`. Vidéo d'essai
  fabriquée par `labo/video/fabrique_video.py` (ffmpeg : x264 et SVT-AV1, clé toutes
  les 8 images, sans images B, BT.709 / transfert sRGB / plage limitée), avec horodatage
  binaire et 12 témoins ColorChecker. Page `labo/video/` : globe au doigt, vue carte,
  curseur, compteur intégré. **Contrôles 37/37 verts**
  (`app/public/labo/video/controles.py`) sur les trois chemins : le Chrome du bac à sable
  décode H.264 **et** AV1 par WebCodecs (page servie en localhost, contexte sûr) ; le
  repli est contrôlé à part (`?repli=1`). ΔE2000 max 0,9 sur les témoins ; image affichée
  = image demandée (exacte, et aussi exacte par le repli).

Ce qui manque (passage suivant) : horloge à loupe (N19), récits en chapitres (N18),
découpage de `lumiere.src.html` en modules, sur `fond-de-carte`, avec les 81 contrôles.
Fluidité ≥ 50 images/s sur le téléphone de référence émulé : pas encore mesurée.

Note pour les autres chantiers : importer `../../commun/compteur.js` et
`../../commun/video.js` depuis `app/public/labo/<id>/` ; les pages doivent être servies
en https ou localhost (WebCodecs exige un contexte sûr).

Prochaine étape : le maître peut publier `labo/compteur/` et `labo/video/` (et
`commun/`) ; puis S0 passage 2 sur `fond-de-carte`.

## S1 — Soleil
Étape : lancé (vague 1).

## S2 — Planètes et Lune
Étape : à lancer (vague 2).

## S3 — Terre, continents
Étape : lancé (vague 1).

## S4 — Climat et glaces
Étape : attend S3.

## S5 — Vie
Étape : attend S4.

## S6 — Humanité
Étape : attend S3.

## S7 — Alpes
Étape : lancé (vague 1).

## S8 — Glaciers
Étape : lancé (vague 1).

## Questions au maître
(aucune)
