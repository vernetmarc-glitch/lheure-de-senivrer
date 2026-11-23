# Plan des chantiers de la refonte (19/11/2026)

Source : proposition « L'Heure de s'enivrer — Refonte : du cosmos aux Alpes » (Claude Doc)
et décisions de Marc du 19/11, 7 h 29 :

- intention élargie : s'enivrer, appréhender l'immensité des échelles (D-39) ;
- tous les chantiers en parallèle, publiés au fur et à mesure, pilotés par un maître (D-40) ;
- les Alpes finissent sur le relief réel : on reconnaît Belledonne ; la barre de temps
  ralentit sur les 2 derniers millions d'années (D-41) ;
- nouveau chantier : l'écoulement des glaciers alpins vu d'avion, avec ses avancées et
  ses retraits, sur environ 100 000 ans, d'après les publications (D-42).

Exigences : `docs/demandes-client.md`, section N (N1–N24).

Règles communes à tous les chantiers : `CLAUDE.md`. Chaque chantier :

- travaille sur la branche `chantier/<id>`, créée depuis `main` ;
- livre une page autonome `app/public/labo/<id>/index.html` (WebGL2, téléphone d'abord),
  avec son fichier de contrôles `app/public/labo/<id>/controles.py` qui mesure la page
  servie (Playwright + Chrome sans écran) ;
- écrit d'abord ses contrôles, les montre en échec, puis construit ;
- fournit à chaque étape une planche `chantiers/planches/<id>-<n>.png` ;
- note son état et ses questions dans `chantiers/ETAT.md`, section du chantier ;
- ne fusionne jamais lui-même dans `main` : c'est le maître qui publie.

Vagues : **vague 1** (lancée le 19/11) S7, S8, S3, S1. **Vague 2** S0, S2. **Vague 3**
S4, S5, S6 (ont besoin du globe de S3).

## Directives du 23/11/2026 (Marc, 5 h 48) — valent pour tous les chantiers

- **Une référence visuelle par chantier**, objectif esthétique du rendu, avec sa
  signature chiffrée qui devient un contrôle : `docs/references-visuelles-refonte.md`
  (N25). Le style de rendu y est fixé : matière en points lumineux, surfaces en
  photographie (N26).
- **Vidéo** pour les couleurs qui changent à projection fixe (H.264/AV1, image clé toutes
  les 8 images, WebCodecs) ; jamais pour les grandeurs mesurées ; jamais pour le zoom (N27).
- **Compteur de vitesse du temps** dans un coin de chaque scène : cadran de voiture,
  aiguille log de 1 an à 10 Ga par seconde (N28). Composant commun
  `app/public/commun/compteur.js`, construit par S0 ; chaque page labo l'intègre dès
  qu'il existe (en attendant, une copie conforme à sa spécification).
- **Humanité** : lignées en couleurs, densité croissante en nombre de points (HYDE 3.3),
  Terre de nuit à la manière de Black Marble pour aujourd'hui.

Vague de relance du 23/11 : S1, S3, S7, S8 reprennent ; S0 (avec le compteur) et S6
démarrent.

---

## S0 — Fondations de la carte et composants communs (sur `fond-de-carte` et `chantier/fondations`)
- Compteur de vitesse du temps (`app/public/commun/compteur.js`, page de démonstration
  `labo/compteur`), selon `docs/references-visuelles-refonte.md` (N28).
- Lecteur de texture vidéo commun (`app/public/commun/video.js` : WebCodecs H.264/AV1,
  repli `<video>`) (N27).
- Horloge à loupe : frise fine des 13,8 Ga au-dessus du curseur, fenêtre lumineuse
  reliée au curseur ; fenêtre par scène et par récit (N19).
- Récits en chapitres : le panneau ouvre le chapitre de l'échelle courante (N18).
- Découpage de `lumiere.src.html` en modules natifs (noyau + une scène par fichier),
  sans outil de construction, sans rien changer à l'écran.
- Contrôles : les 81 de `maquette/controles.py` restent verts ; fenêtre de la frise
  exacte à 1 % ; ordre et chapitres du panneau.

## S1 — Naissance et allumage du Soleil (`labo/soleil`)
- Effondrement d'un cœur de nuage (≈ 0,3 al, 1–1,2 M☉, en rotation) en hydrodynamique
  à particules (Phantom, compilé sur une machine GitHub), 1e5 à 1e6 particules, jusqu'au
  disque et à l'étoile centrale (N4).
- Allumage : luminosité centrale selon les trajectoires d'évolution pré-séquence
  principale publiées (contraction, deutérium, hydrogène vers 30–50 Ma).
- Rendu : points lumineux colorés par la température, esthétique de la toile (N20).
- Contrôles : masse conservée à 1 % ; luminosité conforme à la trajectoire à 5 % ;
  disque formé (rapport d'aspect) ; fluidité.

## S2 — Planètes, grand ménage, Théia, Lune (`labo/planetes`)
- Dissipation du gaz du disque (modèle analytique publié) ; accrétion des planètes
  telluriques avec REBOUND (rayons grossis, calendrier recalé sur les âges publiés) ;
  nettoyage de la périphérie (N4).
- Théia : impact géant en SPH avec SWIFT + WoMa (Kegerreis et al. 2022), 1e5–1e6
  particules (N5).
- La Lune s'en va : modèle de marées recalé sur 3,8 cm/an et ≈ 19 h de jour à 1,4 Ga (N6).
- Contrôles : Terre 0,9–1,1 M⊕ ; Lune à 384 400 km aujourd'hui (1 %) ; jour 18–20 h à 1,4 Ga.

## S3 — La Terre vue de l'espace : continents (`labo/terre`)
- Globe WebGL2, réaliste, sans nuages, Soleil fixe, toujours au solstice de juin (N7).
- 1 Ga → 0 : plaques Merdith et al. 2021 (pyGPlates) ; 540 → 0 Ma : PaleoDEM Scotese &
  Wright (5 Ma, 0,1°) ; relief porté par les plaques entre deux états (pas de fondu) ;
  avant 1 Ga : hypothèse signalée sur la frise (N8, N9).
- Données téléchargées par un workflow GitHub (Zenodo n'est pas joignable du bac à sable).
- Contrôles : terres et mers d'aujourd'hui à 95 % du relief actuel ; Pangée (80 % des
  terres en un bloc entre 320 et 200 Ma) ; aucun continent fantôme pendant la dérive.

## S4 — Climat et glaces sur le globe (`labo/terre`, après S3)
- Classes de Köppen sur 28 tranches du Phanérozoïque ; volume de glace ; trois épisodes
  « boule de neige » ; scintillement des cycles glaciaires sans faux effet stroboscopique
  (N10, N11).
- Contrôles : glace sous 10° de latitude pendant les trois épisodes et jamais ailleurs.

## S5 — La vie vue de l'espace (`labo/terre`, après S4)
- Océans verts à l'Archéen (hypothèse Matsuo 2025), terres nues puis rouillées, forêts
  du Dévonien et du Carbonifère, Pangée rouge, prairies, Chicxulub ; ruban de la vie
  sous la frise (genres marins) pour l'explosion cambrienne (N12).
- Contrôles : aucune terre verte avant 420 Ma ; aujourd'hui proche des photographies
  sans nuages de la NASA.

## S6 — Les vagues humaines (`labo/humanite`)
- Démarre sur un globe de nuit autonome (relief simple + Black Marble pour aujourd'hui),
  rejoint le globe de S3 ensuite. Densité : HYDE 3.3 (10 000 av. J.-C. → 2023, 5′),
  avant l'Holocène : effectifs estimés de la littérature, signalés comme estimations.
  Un point = un nombre fixe d'humains ; une couleur par lignée.
- Sites datés (ROAD), habitats (Timmermann et al. 2022) ; croissance aléatoire de proche
  en proche dans les terres habitables, ponts de terre selon le niveau marin ; une carte
  « date d'arrivée / date de disparition » par espèce ; remplacement par *sapiens*,
  liseré de métissage (N13, N14).
- Contrôles : chaque site atteint à sa date (10 % de son âge) ; plus d'autre espèce que
  *sapiens* après 30 000 ans.

## S7 — L'orogenèse alpine, vue d'avion (`labo/alpes`)
- 300 → 45 Ma : vue régionale de l'Europe (PaleoDEM) : chaîne hercynienne usée,
  Téthys alpine ouverte puis refermée (N15).
- 45 → 0 Ma : FastScape (soulèvement + raccourcissement horizontal imposés par un
  scénario de collision tiré de la littérature ; rivières, versants, dépôts calculés)
  sur ≈ 200 km × 200 km centrés sur Grenoble ; vue d'avion oblique (N16, N17).
- **La fin est le relief réel** (Copernicus DEM 30 m) : sur les 2 derniers Ma le
  soulèvement est ajusté pour converger vers lui ; on reconnaît Belledonne, la
  Chartreuse, le Vercors, le Grésivaudan (N23).
- **La barre de temps ralentit** : vitesse de défilement variable, très lente sur les
  2 derniers Ma, pour qu'on voie le relief se figer en Alpes du Nord (N23).
- Machine à laver : grains de roche suivis (profondeur maximale atteinte) colorant la
  surface quand l'érosion les ramène au jour ; bascule possible en coupe (N17).
- Contrôles : soulèvement et érosion simultanés aux mêmes endroits sur 80 % des images ;
  dernière image à moins de 50 m (moyenne) du relief réel ; vitesse de la barre
  décroissante sur les 2 derniers Ma.

## S8 — Les glaciers des Alpes qui avancent et reculent (`labo/glaciers`, puis dans `alpes`)
- Données publiées : simulations PISM du dernier cycle glaciaire (120 → 0 ka) des Alpes
  à 1–2 km de Seguinot et al. 2018 (The Cryosphere 12, 3265), variables continues sur
  Zenodo (doi 10.5281/zenodo.1423176, version la plus récente) et agrégées
  (doi 10.5281/zenodo.1423160) : épaisseur, vitesses de surface (N22).
- Rendu, même vue d'avion que S7, sur le relief réel des Alpes du Nord : la glace
  remplit le Grésivaudan, déborde sur les plaines, recule, revient (flux et reflux) ;
  l'**écoulement** se voit : traînées de particules qui suivent les vitesses de surface,
  crevasses et moraines suggérées, sans inventer de glace là où le modèle n'en met pas.
- Échelle de temps : ≈ 120 000 ans ; vitesse du curseur adaptée pour voir à la fois le
  rythme des avancées (milliers d'années) et le mouvement de la glace.
- Contrôles : l'étendue de glace à chaque instant est celle des données (à 1 maille
  près) ; maximum vers 25 000 ans avec la glace dans le Grésivaudan ; les traînées vont
  dans le sens des vitesses publiées (écart angulaire médian < 15°).
