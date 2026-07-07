/**
 * Pré-cuit en textures statiques (même logique que generate_layers.py /
 * generate_local_group_texture.py) les layers qui étaient jusqu'ici rendus
 * en direct, étoile par étoile, dans le navigateur :
 *
 *   1. "milkyway" -> app/public/data/density_milkyway.png
 *      Disque + bulbe de la Voie lactée UNIQUEMENT, généré en appelant le
 *      vrai module partagé GalaxyModel (récupéré à chaque exécution depuis
 *      le dépôt "le-silence-du-cosmos", jamais réimplémenté ici).
 *
 *   2. Un SPRITE dédié par galaxie réelle nommée du Groupe Local
 *      -> app/public/data/density_realgal_<slug>.png (8 fichiers)
 *      Historique (6 juillet) : une première version mettait TOUTES les
 *      galaxies réelles dans une seule texture partagée à l'échelle du
 *      Groupe Local (2.4 Mpc) — à cette échelle chaque galaxie n'occupait
 *      que quelques pixels et perdait toute structure (bras spiraux,
 *      barre...) visible avec l'ancien rendu point-par-point en direct.
 *      Une seconde version répartissait les galaxies les plus proches
 *      (LMC, Naine du Sagittaire) dans la texture "milkyway" pour plus de
 *      résolution, mais créait un doublon visuel avec la texture partagée
 *      pendant le fondu entre les deux layers (gros blocs pixelisés).
 *      Solution retenue : CHAQUE galaxie réelle a sa propre texture,
 *      dimensionnée sur SA PROPRE taille (SPRITE_MARGIN x son rayon) —
 *      donc toujours la même résolution relative, quelle que soit sa
 *      distance, et jamais dupliquée. Composée au runtime par
 *      RealGalaxiesLayer.tsx (quelques `drawImage`, pas de champ partagé).
 *
 * Le fait de committer le code du rendu (morphologies) dans CE dépôt ne
 * duplique PAS le module GalaxyModel : seule la Voie lactée elle-même
 * (forme, seed, densité spirale) vient exclusivement de GalaxyModel, chargé
 * à distance. La fonction generateNearbyGalaxyStars ci-dessous est un
 * PORT volontaire (pas un import) de app/src/nearbyGalaxyStars.ts — ce
 * fichier est un outil hors-ligne Node, il ne peut pas importer du
 * TypeScript React directement. À maintenir synchronisé avec ce fichier,
 * au même titre que glow-test.html (cf. §0 du document d'architecture).
 *
 * Usage : node scripts/generate_simulated_textures.mjs
 * Dépendances : pngjs (cf. scripts/package.json)
 */

import { PNG } from 'pngjs'
import { writeFileSync, readFileSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'

const GALAXY_MODEL_URL =
  'https://raw.githubusercontent.com/vernetmarc-glitch/le-silence-du-cosmos/main/galaxy-model.js'

const LY_PER_MPC = 3.26156e6
const CATALOG_PATH = new URL('../app/public/data/local_group_catalog.json', import.meta.url)
const OUT_DIR = new URL('../app/public/data/', import.meta.url)

// Demi-largeur du sprite d'une galaxie réelle, en multiple de son propre
// radiusMpc — GARDER SYNCHRONISÉ avec SPRITE_MARGIN dans
// app/src/RealGalaxiesLayer.tsx (comme pour MARGIN_FACTOR ailleurs dans le
// projet). Les étoiles générées sont tronquées à 1.3x le rayon (cf.
// generateNearbyGalaxyStars) ; 2.8 laisse la place au halo de transition
// (voir HALO_SIGMA_FACTOR) en plus de cette marge.
const SPRITE_MARGIN = 2.8

// Halo doux ajouté autour de chaque galaxie (Voie lactée comprise), en plus
// du nuage d'étoiles net : sans lui, la transition entre ce layer (une
// galaxie physique nette) et le layer de densité au-dessus (un champ flou,
// sans forme de galaxie) était brutale. Le halo s'étend largement au-delà
// du nuage d'étoiles et s'estompe doucement jusqu'au bord du sprite — c'est
// lui qui doit se raccorder visuellement à la densité du layer supérieur,
// pas les étoiles individuelles.
const HALO_SIGMA_FACTOR = 0.75 // en multiple du rayon de la galaxie
const HALO_AMPLITUDE = 0.14 // volontairement faible : ne doit pas noyer le nuage d'étoiles net

// Nom catalogue -> identifiant de fichier. Explicite plutôt qu'un
// slugifier générique : les noms contiennent accents/espaces/parenthèses,
// et une table figée évite toute divergence silencieuse si un nom change.
const SLUG_BY_NAME = {
  'Andromède (M31)': 'andromede',
  'Triangulum (M33)': 'triangulum',
  'Grand Nuage de Magellan': 'lmc',
  'Petit Nuage de Magellan': 'smc',
  'Naine du Sagittaire': 'sagittaire',
  'NGC 6822': 'ngc6822',
  'IC 10': 'ic10',
  'Leo I': 'leo1',
}

// ─────────────────────────────────────────────────────────────────────────
// 1. Récupération du VRAI module GalaxyModel (source unique partagée)
// ─────────────────────────────────────────────────────────────────────────
async function loadGalaxyModel() {
  const res = await fetch(GALAXY_MODEL_URL)
  if (!res.ok) throw new Error(`Échec du téléchargement de galaxy-model.js : HTTP ${res.status}`)
  const code = await res.text()
  const dir = mkdtempSync(path.join(tmpdir(), 'galaxy-model-'))
  const file = path.join(dir, 'galaxy-model.cjs')
  writeFileSync(file, code)
  const require = createRequire(import.meta.url)
  delete require.cache[file]
  return require(file)
}

// ─────────────────────────────────────────────────────────────────────────
// 2. Port de app/src/nearbyGalaxyStars.ts (voir avertissement en tête de
//    fichier) — générateur de semis de points pour les galaxies réelles.
// ─────────────────────────────────────────────────────────────────────────
function mulberry32(seed) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const MORPHOLOGY_BY_NAME = {
  'Andromède (M31)': 'spiral',
  'Triangulum (M33)': 'spiral',
  'Grand Nuage de Magellan': 'barred',
  'Petit Nuage de Magellan': 'irregular_wing',
  'Naine du Sagittaire': 'elliptical_stream',
}

function morphologyFor(name) {
  return MORPHOLOGY_BY_NAME[name] ?? 'irregular'
}

function starCountFor(radiusMpcHint, brightness) {
  return Math.round(60 + brightness * 120 + radiusMpcHint * 4000)
}

function generateNearbyGalaxyStars(name, radiusMpcHint, brightness, seed) {
  const rng = mulberry32(seed)
  const morphology = morphologyFor(name)
  const starCount = starCountFor(radiusMpcHint, brightness)
  const stars = []
  const radius = 1

  const flatten =
    morphology === 'spiral' ? 0.38 : morphology === 'barred' ? 0.5 : morphology === 'elliptical_stream' ? 0.42 : 0.7

  for (let i = 0; i < starCount; i++) {
    const u = rng()
    let r = radius * Math.sqrt(-Math.log(1 - u * 0.98)) * 0.55
    r = Math.min(r, radius * 1.3)
    let theta = rng() * Math.PI * 2

    if (morphology === 'spiral') {
      const pitch = 2.6
      theta += pitch * Math.log(r / radius + 0.15)
      theta += (rng() - 0.5) * 0.7
    } else if (morphology === 'barred') {
      if (rng() < 0.45) {
        const barLength = radius * 0.85
        const along = (rng() * 2 - 1) * barLength
        const across = (rng() - 0.5) * radius * 0.18
        stars.push({ dx: along, dy: across * flatten, b: 0.4 + rng() * 0.5 })
        continue
      }
      const pitch = 1.1
      theta += pitch * Math.log(r / radius + 0.2)
      theta += (rng() - 0.5) * 1.4
    } else if (morphology === 'irregular_wing') {
      if (rng() < 0.25) {
        const wingDir = 0.6
        const wingR = radius * (0.9 + rng() * 0.9)
        const spread = (rng() - 0.5) * radius * 0.4
        const dx = wingR * Math.cos(wingDir) - spread * Math.sin(wingDir)
        const dy = (wingR * Math.sin(wingDir) + spread * Math.cos(wingDir)) * flatten
        stars.push({ dx, dy, b: 0.2 + rng() * 0.4 })
        continue
      }
      theta += (rng() - 0.5) * 2.2
    } else if (morphology === 'elliptical_stream') {
      r = radius * Math.pow(rng(), 0.7)
    }

    const dx = r * Math.cos(theta)
    const dy = r * Math.sin(theta) * flatten
    const b = morphology === 'elliptical_stream' ? 0.35 + rng() * 0.35 : 0.25 + rng() * 0.55
    stars.push({ dx, dy, b })
  }

  const coreFraction = morphology === 'irregular' || morphology === 'irregular_wing' ? 0.05 : 0.12
  const coreCount = Math.round(starCount * coreFraction)
  for (let i = 0; i < coreCount; i++) {
    const r = radius * 0.12 * rng()
    const theta = rng() * Math.PI * 2
    stars.push({ dx: r * Math.cos(theta), dy: r * Math.sin(theta) * flatten, b: 0.75 + rng() * 0.25 })
  }

  return stars
}

// ─────────────────────────────────────────────────────────────────────────
// 3. Accumulateur de champ (splat gaussien) + tonemap + export PNG niveaux
//    de gris — même esprit que build_field() dans generate_local_group_texture.py,
//    mais le tonemap (1 - exp(-k*accum)) remplace la normalisation par une
//    constante calibrée à la main : il s'auto-adapte à la densité d'étoiles
//    (beaucoup de points superposés = saturation douce, pas de coupure nette).
// ─────────────────────────────────────────────────────────────────────────
function splatGaussian(field, n, pxPerUnit, cx, cy, xUnit, yUnit, sigmaUnitMin, sigmaUnitScale, amplitude) {
  const px = cx + xUnit * pxPerUnit
  const py = cy + yUnit * pxPerUnit
  const sigmaPx = Math.max(sigmaUnitMin * pxPerUnit, sigmaUnitScale)
  if (px < -4 * sigmaPx || px > n + 4 * sigmaPx || py < -4 * sigmaPx || py > n + 4 * sigmaPx) return
  const r = Math.max(1, Math.ceil(sigmaPx * 4.5))
  const x0 = Math.max(0, Math.floor(px - r))
  const x1 = Math.min(n - 1, Math.ceil(px + r))
  const y0 = Math.max(0, Math.floor(py - r))
  const y1 = Math.min(n - 1, Math.ceil(py + r))
  const inv2s2 = 1 / (2 * sigmaPx * sigmaPx)
  for (let y = y0; y <= y1; y++) {
    const dy2 = (y - py) * (y - py)
    const row = y * n
    for (let x = x0; x <= x1; x++) {
      const dx = x - px
      const d2 = dx * dx + dy2
      field[row + x] += amplitude * Math.exp(-d2 * inv2s2)
    }
  }
}

function tonemapAndSave(field, n, outPath, k) {
  // pngjs alloue TOUJOURS un buffer RGBA (4 octets/pixel), même avec
  // colorType:0 au constructeur — écrire séquentiellement dans png.data
  // sans respecter ce stride de 4 ne remplit qu'un quart de l'image et de
  // façon désynchronisée entre canaux. On écrit donc explicitement R=G=B et
  // A=255 comme le fait un canvas HTML après décodage d'un PNG en niveaux
  // de gris (cf. DensityLayer.tsx qui relit `data[i*4]`).
  const png = new PNG({ width: n, height: n })
  for (let i = 0; i < n * n; i++) {
    const v = 1 - Math.exp(-k * field[i])
    const byte = Math.max(0, Math.min(255, Math.round(v * 255)))
    const o = i * 4
    png.data[o] = byte
    png.data[o + 1] = byte
    png.data[o + 2] = byte
    png.data[o + 3] = 255
  }
  writeFileSync(outPath, PNG.sync.write(png))
  console.log(`-> ${outPath}`)
}

// ─────────────────────────────────────────────────────────────────────────
// 4. Génération "milkyway" (échelle année-lumière) — disque + bulbe SEULS
//    -> density_milkyway.png, utilisée par DensityLayer.tsx au zoom rapproché.
//
//    Génère AUSSI density_realgal_milkyway.png : un sprite de la Voie
//    lactée avec le MÊME traitement (halo compris) que les 8 galaxies
//    réelles, pour que RealGalaxiesLayer.tsx puisse la dessiner comme une
//    galaxie de plus à l'échelle du Groupe Local. Sans ça, la Voie lactée
//    disparaissait complètement dès qu'on dézoomait au-delà de son propre
//    layer (diagnostic du 6 juillet : "trou noir" au centre pendant qu'on
//    voit déjà Andromède etc. autour) — dans l'ancien rendu en direct, elle
//    était dessinée sur LES DEUX layers (même cache d'étoiles, juste à une
//    échelle physique différente).
// ─────────────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────
// Bruit de valeur (grille aléatoire grossière + interpolation smoothstep) —
// même algorithme que value_noise_field() dans scripts/generate_layers.py,
// utilisé ici pour le halo "nuageux" de la Voie lactée (cf. generateMilkyWay).
// ─────────────────────────────────────────────────────────────────────────
function mulberry32b(seed) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function valueNoiseField(n, gridSize, seed) {
  const rng = mulberry32b(seed)
  const g = Math.max(2, Math.round(gridSize))
  const grid = new Float32Array((g + 1) * (g + 1))
  for (let i = 0; i < grid.length; i++) grid[i] = rng() * 2 - 1
  const out = new Float32Array(n * n)
  for (let y = 0; y < n; y++) {
    const gy = (y / n) * g
    const gy0 = Math.min(Math.floor(gy), g - 1)
    const fy = gy - Math.floor(gy)
    const sy = fy * fy * (3 - 2 * fy)
    for (let x = 0; x < n; x++) {
      const gx = (x / n) * g
      const gx0 = Math.min(Math.floor(gx), g - 1)
      const fx = gx - Math.floor(gx)
      const sx = fx * fx * (3 - 2 * fx)
      const v00 = grid[gy0 * (g + 1) + gx0]
      const v10 = grid[gy0 * (g + 1) + gx0 + 1]
      const v01 = grid[(gy0 + 1) * (g + 1) + gx0]
      const v11 = grid[(gy0 + 1) * (g + 1) + gx0 + 1]
      const a = v00 + (v10 - v00) * sx
      const b = v01 + (v11 - v01) * sx
      out[y * n + x] = a + (b - a) * sy
    }
  }
  return out
}

function multiOctaveCloud(n, seed, baseGrid) {
  const oct1 = valueNoiseField(n, baseGrid, seed)
  const oct2 = valueNoiseField(n, baseGrid * 2.4, seed + 1)
  const oct3 = valueNoiseField(n, baseGrid * 5.5, seed + 2)
  const out = new Float32Array(n * n)
  let min = Infinity
  let max = -Infinity
  for (let i = 0; i < out.length; i++) {
    const c = oct1[i] * 0.55 + oct2[i] * 0.3 + oct3[i] * 0.15
    out[i] = c
    if (c < min) min = c
    if (c > max) max = c
  }
  const span = max - min || 1
  for (let i = 0; i < out.length; i++) out[i] = (out[i] - min) / span
  return out
}

async function generateMilkyWay() {
  const GalaxyModel = await loadGalaxyModel()
  const stars = GalaxyModel.generateGalaxy() // déterministe (RNG_SEED fixe)
  console.log(`GalaxyModel: ${stars.length} étoiles générées (MW_R=${GalaxyModel.MW_R} al, YSCALE=${GalaxyModel.YSCALE})`)

  const N = 1024
  const MARGIN_FACTOR = 1.5
  const HALF_LY = GalaxyModel.MW_R * 2.2
  const boxLy = 2 * HALF_LY * MARGIN_FACTOR
  const pxPerLy = N / boxLy
  const cx = N / 2
  const cy = N / 2

  const field = new Float32Array(N * N)
  for (const star of stars) {
    const sigmaLy = Math.max(star.sz * 0.55, 0.12) * (GalaxyModel.MW_R / 1600)
    splatGaussian(field, N, pxPerLy, cx, cy, star.gx, star.gy * GalaxyModel.YSCALE, sigmaLy, 0.55, 0.18 + star.b * 0.55)
  }
  tonemapAndSave(field, N, new URL('density_milkyway.png', OUT_DIR), 1.0)

  // --- Sprite pour RealGalaxiesLayer (même logique que generateRealGalaxySprite,
  // mais à partir des VRAIES étoiles de GalaxyModel plutôt que du générateur
  // de morphologie approximatif utilisé pour les galaxies lointaines).
  //
  // Halo "variante R" (7 juillet, choisie par l'utilisateur parmi 5
  // aperçus livrés dans le chat, après deux itérations) :
  // - Un halo GAUSSIEN CIRCULAIRE simple (tentative initiale) restait
  //   visible presque jusqu'à la Naine du Sagittaire (0.024 Mpc, la plus
  //   proche des 8 galaxies réelles) et donnait une forme ronde qui ne
  //   correspond pas à celle, aplatie, du disque.
  // - Un halo "nuageux" (bruit de valeur) mais toujours à masque CIRCULAIRE
  //   donnait un rendu quasi identique quels que soient les paramètres, une
  //   fois le gamma d'affichage réel (0.45, cf. densityStyle.ts
  //   'realgalaxy') correctement pris en compte dans les aperçus.
  // - Solution retenue : un bruit de valeur multi-octaves (même algorithme
  //   que les "nuages interstellaires" de l1b, cf. generate_layers.py),
  //   mais appliqué à travers un masque ELLIPTIQUE aplati au même facteur
  //   que le disque (YSCALE) plutôt que circulaire — le halo s'étend donc
  //   dans le sens du disque, pas symétriquement dans toutes les
  //   directions. Le grand axe (SGR_HALO_SEMI_MAJOR_MPC) est choisi pour
  //   rester à distance de sécurité de la Naine du Sagittaire compte tenu
  //   de sa position réelle (angle 320°, donc majoritairement le long du
  //   petit axe aplati de l'ellipse, ce qui laisse de la marge) — vérifié
  //   à la génération (log ci-dessous).
  const MW_HALO_SEMI_MAJOR_MPC = 0.028
  const MW_HALO_FLATTEN = GalaxyModel.YSCALE // même aplatissement que le disque
  const MW_HALO_SOFTNESS_FRAC = 0.25
  const MW_HALO_AMPLITUDE = 0.55
  const MW_HALO_BASE_GRID = 7
  const MW_HALO_SEED = 103

  const mwRadiusMpc = GalaxyModel.MW_R / LY_PER_MPC
  const N2 = 640 // doublé (était 320) : la texture 'milkyway' rapprochée a une résolution
  // relative ~2.7x plus fine — sans ce doublement le sprite semblait "différent" de la
  // vraie Voie lactée vue de près, alors que ce sont les mêmes étoiles.
  const halfWidthMpc2 = mwRadiusMpc * SPRITE_MARGIN
  const pxPerMpc2 = N2 / (2 * halfWidthMpc2)
  const cx2 = N2 / 2
  const cy2 = N2 / 2
  const field2 = new Float32Array(N2 * N2)
  for (const star of stars) {
    const gxMpc = star.gx / LY_PER_MPC
    const gyMpc = (star.gy * GalaxyModel.YSCALE) / LY_PER_MPC
    const sigmaMpc = (Math.max(star.sz * 0.55, 0.12) * (GalaxyModel.MW_R / 1600)) / LY_PER_MPC
    splatGaussian(field2, N2, pxPerMpc2, cx2, cy2, gxMpc, gyMpc, sigmaMpc, 0.6, 0.18 + star.b * 0.55)
  }

  // Halo elliptique nuageux, ajouté directement dans le champ (avant tonemap,
  // comme les étoiles) pour rester cohérent avec le reste du pipeline.
  const cloud = multiOctaveCloud(N2, MW_HALO_SEED, MW_HALO_BASE_GRID)
  const semiMinorMpc = MW_HALO_SEMI_MAJOR_MPC * MW_HALO_FLATTEN
  for (let y = 0; y < N2; y++) {
    const dyMpc = (y - cy2) / pxPerMpc2
    for (let x = 0; x < N2; x++) {
      const dxMpc = (x - cx2) / pxPerMpc2
      const ed = Math.sqrt((dxMpc / MW_HALO_SEMI_MAJOR_MPC) ** 2 + (dyMpc / semiMinorMpc) ** 2)
      const t = Math.min(Math.max((1 - ed) / MW_HALO_SOFTNESS_FRAC, 0), 1)
      const mask = t * t * (3 - 2 * t)
      field2[y * N2 + x] += cloud[y * N2 + x] * mask * MW_HALO_AMPLITUDE
    }
  }

  // Vérification de sécurité (log seulement) : distance elliptique-normalisée
  // de la Naine du Sagittaire (>1 = en dehors du halo, donc en sécurité).
  const sgrRad = (320 * Math.PI) / 180
  const sgrDx = Math.cos(sgrRad) * 0.024
  const sgrDy = Math.sin(sgrRad) * 0.024
  const sgrEd = Math.sqrt((sgrDx / MW_HALO_SEMI_MAJOR_MPC) ** 2 + (sgrDy / semiMinorMpc) ** 2)
  console.log(`Halo Voie lactée : distance elliptique de la Naine du Sagittaire = ${sgrEd.toFixed(2)} (>1 = sûr)`)

  tonemapAndSave(field2, N2, new URL('density_realgal_milkyway.png', OUT_DIR), 1.0)

  return { maxMpc: HALF_LY / LY_PER_MPC, mwRadiusMpc } // maxMpc nominal -> DensityLayer.tsx, mwRadiusMpc -> RealGalaxiesLayer.tsx
}

// ─────────────────────────────────────────────────────────────────────────
// 5. Génération d'un sprite dédié par galaxie réelle nommée — dimensionné
//    sur SA PROPRE taille (résolution relative identique pour toutes,
//    quelle que soit leur distance réelle).
// ─────────────────────────────────────────────────────────────────────────
function generateRealGalaxySprite(gal) {
  const slug = SLUG_BY_NAME[gal.name ?? '']
  if (!slug) {
    console.warn(`Pas de slug pour "${gal.name}" — sprite ignoré (ajouter une entrée dans SLUG_BY_NAME).`)
    return
  }
  const N = 320 // un peu plus que 256 : compense la marge élargie (halo) pour garder le nuage d'étoiles net
  const halfWidthMpc = gal.radiusMpc * SPRITE_MARGIN
  const pxPerMpc = N / (2 * halfWidthMpc)
  const cx = N / 2
  const cy = N / 2

  const field = new Float32Array(N * N)
  const seed = (gal.name?.length ?? 1) * 7919 + Math.round(gal.distanceMpc * 100000)
  const stars = generateNearbyGalaxyStars(gal.name ?? '', gal.radiusMpc, gal.brightness, seed)
  for (const s of stars) {
    const gx = s.dx * gal.radiusMpc
    const gy = s.dy * gal.radiusMpc
    splatGaussian(field, N, pxPerMpc, cx, cy, gx, gy, gal.radiusMpc * 0.045, 0.6, 0.18 + s.b * 0.4)
  }

  // Halo de transition (cf. HALO_SIGMA_FACTOR/HALO_AMPLITUDE en tête de
  // fichier) — un unique halo centré, large, qui s'estompe doucement
  // jusqu'au bord du sprite.
  splatGaussian(field, N, pxPerMpc, cx, cy, 0, 0, gal.radiusMpc * HALO_SIGMA_FACTOR, 1, HALO_AMPLITUDE)

  tonemapAndSave(field, N, new URL(`density_realgal_${slug}.png`, OUT_DIR), 1.0)
}

// ─────────────────────────────────────────────────────────────────────────
async function main() {
  const catalog = JSON.parse(readFileSync(CATALOG_PATH, 'utf8'))

  const { maxMpc: maxMpcMilkyWay, mwRadiusMpc } = await generateMilkyWay()

  for (const gal of catalog) {
    if (!gal.isReal) continue
    generateRealGalaxySprite(gal)
  }

  console.log(`\nmaxMpc à utiliser pour l'entrée "milkyway" dans DensityLayer.tsx : ${maxMpcMilkyWay.toFixed(6)}`)
  console.log(`radiusMpc de la Voie lactée à utiliser dans RealGalaxiesLayer.tsx : ${mwRadiusMpc.toFixed(8)}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
