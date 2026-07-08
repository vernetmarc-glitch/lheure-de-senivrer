/**
 * Cuit les sprites de dissolution (niveaux de gris, comme les sprites de
 * production existants — density_realgal_*.png) à partir des positions
 * calculées par simulate_dissolution.mjs (dissolution_keyframes.json).
 *
 * Paramètres de rendu VALIDÉS interactivement par l'utilisateur via
 * app/public/time-axis-sprites-test.html (capture d'écran du 8 juillet) :
 *   pointSize = 0.5, haloGrowth = 8.5x, blurMax = 6px
 * — remplacent les valeurs par défaut du prototype (1.3-1.6 / 7 / 18-22).
 *
 * IMPORTANT (cohérence avec le pipeline existant) : contrairement aux
 * prototypes HTML (qui colorent et mélangent vers universeGlowColor(a) en
 * direct dans le navigateur, pour l'aperçu), CE script ne cuit QUE le champ
 * niveaux de gris — la couleur/palette et le mélange vers la couleur
 * uniforme de convergence restent une opération au RUNTIME (comme
 * aujourd'hui : RealGalaxiesLayer.tsx charge un PNG gris et applique
 * gamma+couleur), pas quelque chose à figer dans le sprite lui-même.
 *
 * Sortie : un PNG par (galaxie x frame clé), 9 x 14 = 126 fichiers,
 * app/public/data/dissolution_sprites/<slug>_f<00-13>.png (512x512).
 * Chaque fichier correspond au même "step" de simulation dans les 9
 * galaxies (même index de frame), pour rester synchronisé au runtime par
 * un seul indice de progression partagé.
 *
 * Usage : node scripts/generate_dissolution_sprites.mjs
 */

import { PNG } from 'pngjs'
import { writeFileSync, mkdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const N = 512
const POINT_SIZE = 0.5
const HALO_GROWTH = 8.5
const BLUR_MAX_PX = 6
const FILAMENT_AMOUNT = 0.8 // meme valeur par defaut que le prototype (jamais changee par l'utilisateur dans la capture)

const KEYFRAMES_PATH = new URL('../app/public/data/dissolution_keyframes.json', import.meta.url)
const OUT_DIR = fileURLToPath(new URL('../app/public/data/dissolution_sprites/', import.meta.url))
mkdirSync(OUT_DIR, { recursive: true })

function mulberry32(seed) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
function valueNoiseField(n, gridSize, seed) {
  const rng = mulberry32(seed)
  const g = Math.max(2, Math.round(gridSize))
  const grid = new Float32Array((g + 1) * (g + 1))
  for (let i = 0; i < grid.length; i++) grid[i] = rng() * 2 - 1
  const out = new Float32Array(n * n)
  for (let y = 0; y < n; y++) {
    const gy = (y / n) * g, gy0 = Math.min(Math.floor(gy), g - 1), fy = gy - Math.floor(gy)
    const sy = fy * fy * (3 - 2 * fy)
    for (let x = 0; x < n; x++) {
      const gx = (x / n) * g, gx0 = Math.min(Math.floor(gx), g - 1), fx = gx - Math.floor(gx)
      const sx = fx * fx * (3 - 2 * fx)
      const v00 = grid[gy0*(g+1)+gx0], v10 = grid[gy0*(g+1)+gx0+1]
      const v01 = grid[(gy0+1)*(g+1)+gx0], v11 = grid[(gy0+1)*(g+1)+gx0+1]
      const a = v00 + (v10-v00)*sx, b = v01 + (v11-v01)*sx
      out[y*n+x] = a + (b-a)*sy
    }
  }
  return out
}
function multiOctaveCloud(n, seed, baseGrid) {
  const oct1 = valueNoiseField(n, baseGrid, seed)
  const oct2 = valueNoiseField(n, baseGrid * 2.4, seed + 1)
  const oct3 = valueNoiseField(n, baseGrid * 5.5, seed + 2)
  const out = new Float32Array(n * n)
  for (let i = 0; i < out.length; i++) out[i] = (oct1[i]*0.55 + oct2[i]*0.3 + oct3[i]*0.15 + 1) / 2
  return out
}
const filamentNoiseCache = multiOctaveCloud(N, 5151, 8)

// Flou gaussien approxime par 3 passes de flou de boite (technique
// standard, cf. generate_layers.py qui utilise scipy.ndimage.gaussian_filter
// cote Python — ici en JS pur, pas de dependance canvas/DOM necessaire
// contrairement aux prototypes HTML qui utilisaient ctx.filter='blur()').
function boxBlurPass(src, n, radius) {
  if (radius < 0.5) return Float32Array.from(src)
  const r = Math.round(radius)
  const tmp = new Float32Array(n * n)
  const out = new Float32Array(n * n)
  for (let y = 0; y < n; y++) {
    let sum = 0, count = 0
    for (let x = -r; x <= r; x++) { const xi = Math.min(Math.max(x, 0), n - 1); sum += src[y*n+xi]; count++ }
    for (let x = 0; x < n; x++) {
      tmp[y*n+x] = sum / count
      const xOut = Math.min(Math.max(x - r, 0), n - 1), xIn = Math.min(Math.max(x + r + 1, 0), n - 1)
      sum += src[y*n+xIn] - src[y*n+xOut]
    }
  }
  for (let x = 0; x < n; x++) {
    let sum = 0, count = 0
    for (let y = -r; y <= r; y++) { const yi = Math.min(Math.max(y, 0), n - 1); sum += tmp[yi*n+x]; count++ }
    for (let y = 0; y < n; y++) {
      out[y*n+x] = sum / count
      const yOut = Math.min(Math.max(y - r, 0), n - 1), yIn = Math.min(Math.max(y + r + 1, 0), n - 1)
      sum += tmp[yIn*n+x] - tmp[yOut*n+x]
    }
  }
  return out
}
function gaussianBlurApprox(field, n, radius) {
  // 3 passes de flou de boite ~ flou gaussien (erreur < 3%, technique standard)
  let f = boxBlurPass(field, n, radius)
  f = boxBlurPass(f, n, radius)
  f = boxBlurPass(f, n, radius)
  return f
}

function savePng(field01, n, outPath) {
  const png = new PNG({ width: n, height: n })
  for (let i = 0; i < n * n; i++) {
    const byte = Math.max(0, Math.min(255, Math.round(field01[i] * 255)))
    const o = i * 4
    png.data[o] = byte; png.data[o+1] = byte; png.data[o+2] = byte; png.data[o+3] = 255
  }
  writeFileSync(outPath, PNG.sync.write(png))
}

function renderFrame(sim, frameIdx, progress) {
  const frame = sim.frames[frameIdx]
  const meta = sim.particleMeta

  // Cadrage : base sur l'etendue de la DERNIERE frame (la plus dispersee),
  // fixe pour toutes les frames d'une meme galaxie (pas de "zoom" qui saute
  // d'une frame a l'autre au runtime).
  const lastPos = sim.frames[sim.frames.length - 1].positions
  let maxExtent = 0
  for (const [x, y] of lastPos) maxExtent = Math.max(maxExtent, Math.abs(x), Math.abs(y))
  const halfWidthNorm = maxExtent * 1.15
  const pxPerUnit = N / (2 * halfWidthNorm)
  const cx = N / 2, cy = N / 2

  const sigmaPx = Math.max(POINT_SIZE * (1 + progress * (HALO_GROWTH - 1)), 0.5)
  const r = Math.ceil(sigmaPx * 3.2)
  const inv2s2 = 1 / (2 * sigmaPx * sigmaPx)

  const field = new Float32Array(N * N)
  for (let i = 0; i < meta.length; i++) {
    const [x, y] = frame.positions[i]
    const px = cx + x * pxPerUnit, py = cy + y * pxPerUnit
    if (px < -r || px > N + r || py < -r || py > N + r) continue
    const amp = 0.18 + meta[i].b * 0.55
    const x0 = Math.max(0, Math.floor(px-r)), x1 = Math.min(N-1, Math.ceil(px+r))
    const y0 = Math.max(0, Math.floor(py-r)), y1 = Math.min(N-1, Math.ceil(py+r))
    for (let y = y0; y <= y1; y++) {
      const dy2 = (y-py)*(y-py)
      for (let x2 = x0; x2 <= x1; x2++) {
        const dx = x2-px
        field[y*N+x2] += amp * Math.exp(-(dx*dx+dy2)*inv2s2)
      }
    }
  }

  const blurPx = Math.pow(progress, 1.5) * BLUR_MAX_PX
  const blurred = gaussianBlurApprox(field, N, blurPx)

  const filIntensity = FILAMENT_AMOUNT * 4 * progress * (1 - progress)
  const out = new Float32Array(N * N)
  for (let i = 0; i < out.length; i++) {
    const tone = 1 - Math.exp(-blurred[i])
    const v = tone * (1 + (filamentNoiseCache[i] - 0.5) * 2 * filIntensity)
    out[i] = Math.min(Math.max(v, 0), 1)
  }
  return out
}

function main() {
  const allSims = JSON.parse(readFileSync(KEYFRAMES_PATH, 'utf8'))
  for (const slug of Object.keys(allSims)) {
    const sim = allSims[slug]
    const nFrames = sim.frames.length
    for (let f = 0; f < nFrames; f++) {
      const progress = f / (nFrames - 1)
      const field = renderFrame(sim, f, progress)
      const outPath = path.join(OUT_DIR, `${slug}_f${String(f).padStart(2, '0')}.png`)
      savePng(field, N, outPath)
    }
    console.log(`${slug}: ${nFrames} frames cuites`)
  }
  console.log(`\n-> ${OUT_DIR}`)
}

main()
