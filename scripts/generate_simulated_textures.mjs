/**
 * Pré-cuit en textures statiques (même logique que generate_layers.py /
 * generate_local_group_texture.py) les DEUX layers qui étaient jusqu'ici
 * rendus en direct, étoile par étoile, dans le navigateur :
 *
 *   1. "milkyway"       -> app/public/data/density_milkyway.png
 *      Disque + bulbe de la Voie lactée, généré en appelant le VRAI module
 *      partagé GalaxyModel (récupéré à chaque exécution depuis le dépôt
 *      "le-silence-du-cosmos", jamais réimplémenté ici) + les galaxies
 *      réelles très proches (Nuages de Magellan, Naine du Sagittaire) qui
 *      tombent dans son champ.
 *
 *   2. "localgroup_real" -> app/public/data/density_localgroup_real.png
 *      Les 8 galaxies réelles nommées du Groupe Local (Andromède, M33...),
 *      à l'échelle du Mpc, en plus du halo procédural existant
 *      (density_localgroup.png, généré séparément par
 *      generate_local_group_texture.py).
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

// Plancher de taille VISIBLE pour le nuage d'étoiles d'une galaxie réelle,
// exprimé en fraction de la demi-largeur NOMINALE (avant marge) de la
// texture qui l'accueille — même esprit que VISIBILITY_SCALE/MIN_SIZE_MPC
// dans generate_local_group_texture.py, mais relatif plutôt qu'absolu pour
// rester valable aussi bien à l'échelle année-lumière (milkyway) qu'à
// l'échelle Mpc (localgroup_real). Sans ça, LMC/SMC/Naine du Sagittaire/
// NGC6822/IC10/Leo I sont sub-pixel à la résolution de la texture (rayon
// réel < 1 px) et disparaissent presque totalement.
function effectiveRadius(radiusUnit, nominalHalfWidthUnit) {
  return Math.max(radiusUnit, nominalHalfWidthUnit * 0.005)
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
// 4. Génération "milkyway" (échelle année-lumière)
// ─────────────────────────────────────────────────────────────────────────
async function generateMilkyWay(catalog) {
  const GalaxyModel = await loadGalaxyModel()
  const stars = GalaxyModel.generateGalaxy() // déterministe (RNG_SEED fixe)
  console.log(`GalaxyModel: ${stars.length} étoiles générées (MW_R=${GalaxyModel.MW_R} al, YSCALE=${GalaxyModel.YSCALE})`)

  const N = 1024
  const MARGIN_FACTOR = 1.5
  // Demi-largeur nominale (avant marge) : ~2.2x MW_R, suffisant pour couvrir
  // tout le disque (taper à 1.45x MW_R). ~2.7x est ce qu'il faut en plus
  // pour couvrir aussi les 3 galaxies réelles les plus proches (LMC, Naine
  // du Sagittaire, ET le Petit Nuage de Magellan qui passait tout juste à
  // côté du seuil avec 2.2x) — cf. diagnostic du 6 juillet : une galaxie
  // proche laissée hors de CE texte finit rendue UNIQUEMENT par
  // localgroup_real, dont la résolution effective est ~14x plus faible ici
  // (tout le Groupe Local en 2.4 Mpc vs seulement l'environnement proche de
  // la Voie lactée) — d'où les gros blocs pixelisés constatés au lieu d'un
  // halo net.
  const HALF_LY = GalaxyModel.MW_R * 2.7
  const boxLy = 2 * HALF_LY * MARGIN_FACTOR
  const pxPerLy = N / boxLy
  const cx = N / 2
  const cy = N / 2

  const field = new Float32Array(N * N)

  for (const star of stars) {
    const sigmaLy = Math.max(star.sz * 0.55, 0.12) * (GalaxyModel.MW_R / 1600) // ~cohérent avec sz d'origine (échelle écran)
    splatGaussian(field, N, pxPerLy, cx, cy, star.gx, star.gy * GalaxyModel.YSCALE, sigmaLy, 0.55, 0.18 + star.b * 0.55)
  }

  // Galaxies réelles proches qui tombent dans ce champ (pas de YSCALE : ce
  // sont des galaxies distinctes, pas le disque de la Voie lactée).
  for (const gal of catalog) {
    const distanceLy = gal.distanceMpc * LY_PER_MPC
    if (distanceLy > HALF_LY * MARGIN_FACTOR * 1.05) continue
    const radiusLy = effectiveRadius(gal.radiusMpc * LY_PER_MPC, HALF_LY)
    const rad = (gal.angleDeg * Math.PI) / 180
    const centerX = Math.cos(rad) * distanceLy
    const centerY = Math.sin(rad) * distanceLy
    const seed = (gal.name?.length ?? 1) * 7919 + Math.round(gal.distanceMpc * 100000)
    const galStars = generateNearbyGalaxyStars(gal.name ?? '', gal.radiusMpc, gal.brightness, seed)
    for (const s of galStars) {
      const gx = centerX + s.dx * radiusLy
      const gy = centerY + s.dy * radiusLy
      splatGaussian(field, N, pxPerLy, cx, cy, gx, gy, radiusLy * 0.06, 0.6, 0.18 + s.b * 0.4)
    }
  }

  tonemapAndSave(field, N, new URL('density_milkyway.png', OUT_DIR), 1.0)

  const inclusionThresholdLy = HALF_LY * MARGIN_FACTOR * 1.05
  return { maxMpc: HALF_LY / LY_PER_MPC, inclusionThresholdLy } // maxMpc nominal à reporter dans DensityLayer.tsx
}

// ─────────────────────────────────────────────────────────────────────────
// 5. Génération "localgroup_real" (échelle Mpc) — les 8 galaxies nommées
// ─────────────────────────────────────────────────────────────────────────
function generateLocalGroupReal(catalog, milkywayInclusionThresholdLy) {
  const N = 1024
  const MAX_MPC = 2.4 // identique à generate_local_group_texture.py
  const MARGIN_FACTOR = 1.5
  const boxMpc = 2 * MAX_MPC * MARGIN_FACTOR
  const pxPerMpc = N / boxMpc
  const cx = N / 2
  const cy = N / 2

  const field = new Float32Array(N * N)

  for (const gal of catalog) {
    if (!gal.isReal) continue
    // Les galaxies déjà couvertes en haute résolution par le layer
    // "milkyway" (LMC, Naine du Sagittaire, SMC — cf. generateMilkyWay) ne
    // doivent PAS être rendues une seconde fois ici : à cette résolution
    // (tout le Groupe Local en 2.4 Mpc, ~14x moins précis que le champ
    // dédié à l'environnement proche de la Voie lactée), le rendu de ces
    // galaxies très proches donne un pâté de quelques pixels qui devient un
    // gros bloc visible dès qu'on zoome dans la zone de fondu milkyway <->
    // localgroup — cf. diagnostic du 6 juillet. Elles restent visibles,
    // nettes, via le layer milkyway.
    if (gal.distanceMpc * LY_PER_MPC <= milkywayInclusionThresholdLy) continue
    const rad = (gal.angleDeg * Math.PI) / 180
    const centerX = Math.cos(rad) * gal.distanceMpc
    const centerY = Math.sin(rad) * gal.distanceMpc
    const seed = (gal.name?.length ?? 1) * 7919 + Math.round(gal.distanceMpc * 100000)
    const galStars = generateNearbyGalaxyStars(gal.name ?? '', gal.radiusMpc, gal.brightness, seed)
    const radiusMpc = effectiveRadius(gal.radiusMpc, MAX_MPC)
    for (const s of galStars) {
      const gx = centerX + s.dx * radiusMpc
      const gy = centerY + s.dy * radiusMpc
      splatGaussian(field, N, pxPerMpc, cx, cy, gx, gy, radiusMpc * 0.06, 0.6, 0.18 + s.b * 0.4)
    }
  }

  tonemapAndSave(field, N, new URL('density_localgroup_real.png', OUT_DIR), 1.0)
}

// ─────────────────────────────────────────────────────────────────────────
async function main() {
  const catalog = JSON.parse(readFileSync(CATALOG_PATH, 'utf8'))
  const { maxMpc: maxMpcMilkyWay, inclusionThresholdLy } = await generateMilkyWay(catalog)
  generateLocalGroupReal(catalog, inclusionThresholdLy)
  console.log(`\nmaxMpc à utiliser pour l'entrée "milkyway" dans DensityLayer.tsx : ${maxMpcMilkyWay.toFixed(6)}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
