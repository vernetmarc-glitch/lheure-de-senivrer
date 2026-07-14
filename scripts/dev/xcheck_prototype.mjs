// Contrôle croisé §13 : exécute le VRAI code du prototype. Prérequis :
//   python3 xcheck_dump_ref.py   (dumpe les frames brutes + la référence Python)
// Ce harnais a détecté un vrai écart le 13 juillet (embrasement appliqué
// dans render() côté JS mais dans render_cell() côté Python) — le garder
// à jour avec le prototype.
// Contrôle croisé §13 : exécute le VRAI code du prototype
// (computeTone extrait de app/public/spacetime-matrix-test.html) sous Node,
// avec les vraies frames, et compare au pipeline Python de référence
// (scripts/dev/spacetime_pipeline.py). Usage : node xcheck_prototype.mjs
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { createRequire } from 'module'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const APP = path.resolve(__dirname, '../../app/public')
const XDIR = path.join(__dirname, 'xcheck_tmp')   // rempli par xcheck_dump_ref.py

const require = createRequire(import.meta.url)
// app/package.json est en "type":"module" -> copie .cjs pour require()
const cjsTmp = path.join(XDIR, 'spacetime-shared.cjs')
fs.copyFileSync(path.join(APP, 'spacetime-shared.js'), cjsTmp)
const SpacetimeShared = require(cjsTmp)

// Extraire le script inline du prototype (2e bloc <script>)
const html = fs.readFileSync(path.join(APP, 'spacetime-matrix-test.html'), 'utf8')
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1])
let script = blocks[blocks.length - 1]
script = script.replace(/\nboot\(\)\s*$/, '\n/* boot() neutralisé pour le harnais */')

// Stubs DOM minimaux (aucun rendu, on n'appelle que computeTone)
const noopEl = { value: '0', textContent: '', innerHTML: '', addEventListener: () => {} }
const sandboxDecls = `
const document = { getElementById: () => (${JSON.stringify({})}, { value:'0', textContent:'', innerHTML:'', addEventListener: ()=>{} }) }
const cv = null, ctx = null
`
// cv/ctx sont déclarés dans le script via getElementById -> nos stubs suffisent.

const MATRIX = JSON.parse(fs.readFileSync(path.join(APP, 'data/spacetime_matrix.json')))
const COSMO_TABLE = JSON.parse(fs.readFileSync(path.join(APP, 'data/cosmology_table.json')))


const harness = `
;(function () {
  MATRIX = __MATRIX__
  COSMO = __COSMO__.rows
  for (const l of MATRIX.layers) {
    FRAMES[l.key] = l.keyframes_a.map((_, i) => {
      const raw = __READRAW__(l.key, i)
      const arr = new Float32Array(raw.length)
      for (let j = 0; j < raw.length; j++) arr[j] = raw[j] / 255
      return { arr, n: 512 }
    })
  }
  for (const g of MATRIX.real_galaxies.entries) {
    SPRITE_FRAMES[g.slug] = Array.from({ length: MATRIX.sprites.n_frames }, (_, i) => {
      const raw = __READRAW__('sprites/' + g.slug, i)
      const arr = new Float32Array(raw.length)
      for (let j = 0; j < raw.length; j++) arr[j] = raw[j] / 255
      return { arr, n: 512 }
    })
  }
  framesTotal = 1; framesLoaded = 1
  globalThis.__computeTone = computeTone
})()
`

const full = script + harness
// Les frames de layers sont dans xcheck_tmp/frames/, les sprites dans
// xcheck_tmp/sprites/ (la clé contient alors déjà son sous-dossier).
const readRaw = (key, i) =>
  fs.readFileSync(path.join(XDIR, key.includes('/') ? '.' : 'frames',
    `${key}_${String(i).padStart(2, '0')}.raw`))

// Évaluation dans une fonction partageant la portée lexicale du script
const fn = new Function('SpacetimeShared', 'document', '__MATRIX__', '__COSMO__',
  '__READRAW__',
  'const cvStub=null;' + full.replace(/const cv = document.getElementById\('cv'\)\s*\nconst ctx = cv.getContext\('2d'\)/,
    'const cv = null, ctx = null'))
const docStub = { getElementById: () => ({ value: '0', textContent: '', innerHTML: '', addEventListener: () => {} }) }
fn(SpacetimeShared, docStub, MATRIX, COSMO_TABLE, readRaw)

const computeTone = globalThis.__computeTone
if (!computeTone) { console.error('computeTone introuvable'); process.exit(1) }

const ref = JSON.parse(fs.readFileSync(path.join(XDIR, 'python_ref.json')))
const PIXELS = [[10, 10], [150, 150], [80, 220], [250, 40], [299, 299]]
const N = 300
let worstMean = 0, worstPx = 0, fail = 0
for (const r of ref) {
  const { tone, white } = computeTone(r.hw, r.a)
  let sum = 0
  for (let i = 0; i < tone.length; i++) sum += tone[i]
  const mean = sum / tone.length
  const dMean = Math.abs(mean - r.mean)
  const dWhite = Math.abs(white - r.white)
  let dPx = 0
  r.px.forEach((pv, k) => {
    const [y, x] = PIXELS[k]
    dPx = Math.max(dPx, Math.abs(tone[y * N + x] - pv))
  })
  worstMean = Math.max(worstMean, dMean)
  worstPx = Math.max(worstPx, dPx)
  const ok = dMean < 2e-3 && dPx < 5e-3 && dWhite < 1e-6
  if (!ok) fail++
  console.log(`hw=${r.hw} a=${r.a}: |Δmean|=${dMean.toExponential(2)} |Δpx|max=${dPx.toExponential(2)} |Δwhite|=${dWhite.toExponential(2)} ${ok ? 'OK' : 'ÉCHEC'}`)
}
console.log(`\npire écart moyen=${worstMean.toExponential(2)}, pire écart pixel=${worstPx.toExponential(2)}`)
if (fail) { console.log(`${fail} cellule(s) en ÉCHEC`); process.exit(1) }
console.log('CONTRÔLE CROISÉ JS/PYTHON : OK — le prototype calcule bien le pipeline validé.')
