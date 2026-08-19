/**
 * Sprites des galaxies nommées à T = aujourd'hui.
 *
 *   -> app/public/data/density_realgal_<slug>.png  (9 fichiers, 1024 px)
 *
 * REMPLACE `generateRealGalaxySprite` de generate_simulated_textures.mjs, dont
 * le défaut est mesuré et nommé (T-100, 11/08/2026) : `starCountFor` rendait
 * ~316 étoiles pour Andromède — la plus grande galaxie du champ après la nôtre
 * — chacune splattée en gaussienne, plus un halo central. Le résultat était une
 * tache blanche saturée. Le modèle partagé `GalaxyModel` en engendre 81 758
 * avec quatre bras : la structure existait, c'est le pipeline qui la jetait.
 *
 * TROIS CHOSES QUI DOIVENT RESTER VRAIES
 * --------------------------------------
 * 1. `SPRITE_MARGIN = 2.8` est repris à l'identique de
 *    generate_simulated_textures.mjs et de RealGalaxiesLayer.tsx. Le sprite
 *    couvre 2,8 fois le `radiusMpc` de la galaxie. **Changer cette valeur ici
 *    sans la changer là-bas fait mentir l'échelle** — et l'échelle est ce que
 *    l'œuvre doit enseigner.
 * 2. L'orientation vient du CATALOGUE (`inclinationDeg`, `positionAngleDeg`),
 *    pas d'un aplatissement global. L'ancien `YSCALE = 0,40` appliqué à toutes
 *    donnait au LMC, quasi de face, la silhouette de M31 inclinée à 77°.
 * 3. La graine dérive du CONTENU du nom. Elle dérivait de sa LONGUEUR :
 *    « IC 10 » et « Leo I » font cinq caractères, d'où deux galaxies
 *    identiques à l'octet près (T-024).
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import zlib from 'node:zlib'

const GALAXY_MODEL_URL =
  'https://raw.githubusercontent.com/vernetmarc-glitch/le-silence-du-cosmos/main/galaxy-model.js'
const CATALOG_PATH = new URL('../app/public/data/local_group_catalog.json', import.meta.url)
const OUT_DIR = new URL('../app/public/data/', import.meta.url)

// GARDER SYNCHRONISÉ avec SPRITE_MARGIN dans RealGalaxiesLayer.tsx et
// generate_simulated_textures.mjs. Voir l'en-tête, point 1.
const SPRITE_MARGIN = 2.8
const N = 1024 // 320 auparavant : à 320 px les bras tombaient sous le pixel

// Compacité : ramène l'étendue du champ d'étoiles sur celle de la famille
// historique. Mesure du 11/08 : les vignettes engendrées ici avaient un r90 de
// 0,29 du demi-côté contre 0,10 pour les vignettes 512 — soit 2,9 fois plus
// étalées. Un disque exponentiel dont la lumière porte jusqu'à ~0,8 rayon est
// physiquement plus juste que l'ancien profil, très concentré ; mais TOUTE la
// chaîne est calibrée sur l'ancienne convention — tailles apparentes (T-016),
// courbes de ton, raccords entre lignes. Changer l'étendue et desserrer les
// seuils qui s'en plaignent serait prendre le problème à l'envers.
//
// On aligne donc l'étendue, et la richesse de structure — le sujet du retour de
// Marc — est gagnée sans rien déplacer d'autre. Si l'étalement physique est un
// jour préféré, c'est T-016 qu'il faudra ré-étalonner, explicitement.
const COMPACITE = 0.800

// Halo de transition, repris de generate_simulated_textures.mjs (mêmes valeurs).
// OMIS dans la première version de ce générateur, et l'omission s'est vue à la
// mesure : T-033 tombait à -4,29 à la ligne `C` pour un plancher à -0,40. Ce
// contrôle protège A6 — la continuité entre les points brillants et le fond. Un
// nuage d'étoiles net posé sur un fond sombre SANS palier intermédiaire creuse
// un trou dans l'histogramme : l'œil y voit deux populations au lieu d'une
// galaxie qui s'estompe. Le halo est volontairement faible pour ne pas noyer la
// structure que tout ce travail cherche justement à rendre visible.
const HALO_SIGMA_FACTOR = 0.75 // en multiple du rayon de la galaxie
const HALO_AMPLITUDE = 0.14

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

// Nombre d'étoiles tirées, par morphologie. Ce sont ces chiffres qui font la
// différence entre une galaxie et une tache : en dessous de ~20 000 les bras
// tombent dans le bruit de grenaille et ne se lisent plus.
const N_STARS = {
  spiral: 70000,
  barred: 45000,
  irregular_wing: 30000,
  irregular: 26000,
  elliptical_stream: 22000,
  spheroidal: 18000,
}

// Bras par morphologie. M31 est une spirale à deux bras dominants, la Voie
// lactée en a quatre (valeur du modèle partagé).
const ARMS = { 'Andromède (M31)': 2, 'Triangulum (M33)': 5, 'Grand Nuage de Magellan': 1 }
const PITCH = { 'Andromède (M31)': 0.28, 'Triangulum (M33)': 0.45, 'Grand Nuage de Magellan': 0.5 }

// ─────────────────────────────────────────────────────────────────────────
// Graine : dérivée du CONTENU du nom (voir en-tête, point 3).
function grainePourNom(nom) {
  let h = 2166136261
  for (let i = 0; i < nom.length; i++) {
    h ^= nom.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function mulberry32(seed) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

async function loadGalaxyModel() {
  const res = await fetch(GALAXY_MODEL_URL)
  if (!res.ok) throw new Error(`galaxy-model.js : HTTP ${res.status}`)
  const dir = mkdtempSync(path.join(tmpdir(), 'gm-'))
  const file = path.join(dir, 'galaxy-model.cjs')
  writeFileSync(file, await res.text())
  return createRequire(import.meta.url)(file)
}

// ─────────────────────────────────────────────────────────────────────────
// Champ d'étoiles paramétré. Généralisation de `spiralDensity` du modèle
// partagé : même forme de motif (log-spirale, échantillonnage à rejet), avec
// le nombre de bras et le pas ouverts en paramètres — le modèle partagé les
// fige à 4 et ne convient donc qu'à la Voie lactée.
function champEtoiles(nom, morpho, rng) {
  const nStars = N_STARS[morpho] ?? 20000
  const nArms = ARMS[nom] ?? 2
  const tanPitch = PITCH[nom] ?? 0.35
  const stars = []
  const H = 0.32 // longueur d'échelle du disque, en unités de rayon
  const forceBras = morpho === 'spiral' ? 0.55 : morpho === 'barred' ? 0.35 : 0.0
  const lisse = morpho === 'spheroidal' || morpho === 'elliptical_stream'

  let essais = 0
  while (stars.length < nStars && essais < nStars * 60) {
    essais++
    const R = 1.35 * Math.sqrt(rng())
    const phi = rng() * Math.PI * 2
    // Profil radial exponentiel, commun à toutes les morphologies.
    let rho = Math.exp(-R / H)
    if (!lisse && forceBras > 0) {
      // Motif de bras : maximum là où phi - ln(R)/tanPitch est en phase.
      const s = Math.cos(nArms * (phi - Math.log(R + 0.12) / tanPitch))
      const motif = (1 - forceBras) + forceBras * Math.pow((s + 1) / 2, 1.6)
      // Le cœur reste axisymétrique : les bras ne s'enroulent pas jusqu'au bulbe.
      const coeur = Math.min(1, Math.max(0, (R - 0.06) / 0.16))
      rho *= (1 - coeur) + coeur * motif
    }
    if (morpho === 'irregular' || morpho === 'irregular_wing') {
      // Grumeaux : trois surdensités tirées au sort, qui donnent à chaque
      // naine sa silhouette propre au lieu d'un disque anonyme.
      rho *= 0.55 + 0.9 * Math.abs(Math.sin(3.1 * phi + 2.0 * R) * Math.cos(1.7 * R * 6))
    }
    if (rng() > rho) continue
    let x = Math.cos(phi) * R
    let y = Math.sin(phi) * R
    if (morpho === 'barred' && rng() < 0.30) {
      // Barre centrale. Un tirage UNIFORME dans un rectangle donne un bâton
      // peint, aux bords nets et à la densité plate — c'est ce que rendait la
      // première version. Une barre réelle a un profil qui décroît le long du
      // grand axe ET s'éteint aux extrémités : d'où le tirage en cosinus au
      // carré le long, gaussien en travers, et l'épaisseur qui se pince aux
      // bouts.
      const t = (rng() + rng() + rng() + rng() - 2) / 2 // ~ gaussienne tronquée
      const along = t * 0.62
      const pince = Math.max(0, 1 - Math.pow(Math.abs(along) / 0.62, 1.7))
      x = along
      y = (rng() + rng() + rng() + rng() - 2) / 2 * 0.085 * pince
      stars.push({ x, y, b: Math.min(1, 0.35 + rng() * 0.5 + 0.3 * pince) })
      continue
    }
    if (morpho === 'irregular_wing' && rng() < 0.22) {
      // Aile du Petit Nuage, étirée dans une direction.
      x += 0.55 + rng() * 0.5
      y += (rng() - 0.5) * 0.22
    }
    if (morpho === 'elliptical_stream') {
      x *= 1.5
      y *= 0.42
    }
    const b = Math.min(1, 0.10 + rng() * 0.55 + (lisse ? 0.15 : 0.35) * Math.exp(-R / 0.25))
    stars.push({ x, y, b })
  }
  // Bulbe : profil exponentiel sans rayon de coupure, comme le modèle partagé.
  const nBulbe = Math.round(nStars * (lisse ? 0.35 : 0.14))
  for (let i = 0; i < nBulbe; i++) {
    const r = -0.075 * Math.log(1 - rng())
    const a = rng() * Math.PI * 2
    stars.push({ x: Math.cos(a) * r, y: Math.sin(a) * r, b: 0.4 + rng() * 0.6 })
  }
  return stars
}

// ─────────────────────────────────────────────────────────────────────────
// Rendu : dépôt bilinéaire, puis courbe de ton PONCTUELLE. Aucun opérateur
// spatialement non linéaire en aval — règle du projet.
function rendre(stars, inclinaisonDeg, angleDeg) {
  const champ = new Float32Array(N * N)
  const ci = Math.cos((inclinaisonDeg * Math.PI) / 180)
  const pa = (angleDeg * Math.PI) / 180
  const cp = Math.cos(pa)
  const sp = Math.sin(pa)
  // rayon 1 = radiusMpc, et le sprite couvre SPRITE_MARGIN * radiusMpc.
  const echelle = N / (2 * SPRITE_MARGIN)
  for (const s of stars) {
    // Inclinaison : l'axe mineur est comprimé par cos i. Puis rotation par
    // l'angle de position, pour poser l'axe majeur là où il est observé.
    const xi = s.x * COMPACITE
    const yi = s.y * ci * COMPACITE
    const px = (xi * cp - yi * sp) * echelle + N / 2
    const py = (xi * sp + yi * cp) * echelle + N / 2
    if (px < 0 || px >= N - 1 || py < 0 || py >= N - 1) continue
    const x0 = px | 0
    const y0 = py | 0
    const fx = px - x0
    const fy = py - y0
    champ[y0 * N + x0] += s.b * (1 - fx) * (1 - fy)
    champ[y0 * N + x0 + 1] += s.b * fx * (1 - fy)
    champ[(y0 + 1) * N + x0] += s.b * (1 - fx) * fy
    champ[(y0 + 1) * N + x0 + 1] += s.b * fx * fy
  }
  return champ
}

/** Halo gaussien centré, large et faible : le palier qui relie la galaxie au fond. */
function ajouterHalo(champ, fluxEtoiles) {
  const echelle = N / (2 * SPRITE_MARGIN)
  const sigma = HALO_SIGMA_FACTOR * echelle
  // Amplitude rapportée au flux du nuage d'étoiles, pour que le rapport
  // halo/étoiles ne dépende pas du nombre d'étoiles tirées.
  const amp = (HALO_AMPLITUDE * fluxEtoiles) / (2 * Math.PI * sigma * sigma)
  for (let y = 0; y < N; y++) {
    const dy = y - N / 2
    for (let x = 0; x < N; x++) {
      const dx = x - N / 2
      champ[y * N + x] += amp * Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
    }
  }
  return champ
}

function flouSeparable(champ, sigma) {
  const rayon = Math.max(1, Math.ceil(sigma * 3))
  const noyau = []
  let somme = 0
  for (let i = -rayon; i <= rayon; i++) {
    const v = Math.exp(-(i * i) / (2 * sigma * sigma))
    noyau.push(v)
    somme += v
  }
  for (let i = 0; i < noyau.length; i++) noyau[i] /= somme
  const tmp = new Float32Array(N * N)
  const out = new Float32Array(N * N)
  for (let y = 0; y < N; y++)
    for (let x = 0; x < N; x++) {
      let a = 0
      for (let k = -rayon; k <= rayon; k++) {
        const xx = x + k
        if (xx >= 0 && xx < N) a += champ[y * N + xx] * noyau[k + rayon]
      }
      tmp[y * N + x] = a
    }
  for (let y = 0; y < N; y++)
    for (let x = 0; x < N; x++) {
      let a = 0
      for (let k = -rayon; k <= rayon; k++) {
        const yy = y + k
        if (yy >= 0 && yy < N) a += tmp[yy * N + x] * noyau[k + rayon]
      }
      out[y * N + x] = a
    }
  return out
}

// PNG écrit à la main (pas de dépendance canvas), au FORMAT EXACT de
// `tonemapAndSave` de generate_simulated_textures.mjs : RGBA, R=G=B et A=255.
// Ne pas changer ce format — `RealGalaxiesLayer` relit `data[i*4]` et recolore
// ensuite ; un PNG en gris+alpha y donnerait un sprite transparent au lieu de
// la source en niveaux de gris attendue.
//
// La courbe de ton est celle du projet, reprise telle quelle : `1 - exp(-k f)`.
// Elle ne sature jamais et écrase d'autant plus les hautes valeurs qu'elles
// sont fortes — c'est ce qui garde les bras lisibles au lieu de les noyer dans
// un bulbe blanc. `k` est calé par le 99,9e centile du champ, donc sur la
// galaxie elle-même et non sur une constante qui vaudrait pour toutes.
function ecrirePNG(champ, chemin) {
  const nz = Array.from(champ).filter((v) => v > 0).sort((a, b) => a - b)
  const hi = nz.length ? nz[Math.floor(nz.length * 0.999)] : 1
  const k = 7.5 / Math.max(hi, 1e-9)
  const px = Buffer.alloc(N * (1 + N * 4))
  for (let y = 0; y < N; y++) {
    px[y * (1 + N * 4)] = 0
    for (let x = 0; x < N; x++) {
      const v = 1 - Math.exp(-k * champ[y * N + x])
      const g = Math.max(0, Math.min(255, Math.round(v * 255)))
      const o = y * (1 + N * 4) + 1 + x * 4
      px[o] = g
      px[o + 1] = g
      px[o + 2] = g
      px[o + 3] = 255
    }
  }
  const crcTable = []
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let kk = 0; kk < 8; kk++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    crcTable[n] = c >>> 0
  }
  const crc = (buf) => {
    let c = 0xffffffff
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8)
    return (c ^ 0xffffffff) >>> 0
  }
  const chunk = (type, data) => {
    const len = Buffer.alloc(4)
    len.writeUInt32BE(data.length)
    const td = Buffer.concat([Buffer.from(type, 'ascii'), data])
    const c = Buffer.alloc(4)
    c.writeUInt32BE(crc(td))
    return Buffer.concat([len, td, c])
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(N, 0)
  ihdr.writeUInt32BE(N, 4)
  ihdr[8] = 8
  ihdr[9] = 6 // RGBA
  writeFileSync(
    chemin,
    Buffer.concat([
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
      chunk('IHDR', ihdr),
      chunk('IDAT', zlib.deflateSync(px, { level: 9 })),
      chunk('IEND', Buffer.alloc(0)),
    ])
  )
}

// ─────────────────────────────────────────────────────────────────────────
async function main() {
  mkdirSync(new URL('.', OUT_DIR), { recursive: true })
  const GM = await loadGalaxyModel()

  // Voie lactée : le VRAI modèle partagé, à pleine richesse. On la voit de
  // l'intérieur, donc son inclinaison de rendu est une convention du projet
  // (équivalente à l'ancien YSCALE = 0,40, soit ~66 degrés) et non une mesure.
  const mw = GM.generateGalaxy({ starCount: 90000 }).map((s) => ({
    x: s.gx / GM.MW_R,
    y: s.gy / GM.MW_R,
    b: s.b,
  }))
  const champMw = rendre(mw, 66, 0)
  const fluxMw = champMw.reduce((a, b) => a + b, 0)
  let champ = flouSeparable(ajouterHalo(champMw, fluxMw), 0.9)
  ecrirePNG(champ, new URL('density_realgal_milkyway.png', OUT_DIR))
  console.log(`milkyway    ${mw.length} étoiles (modèle partagé)`)

  const cat = JSON.parse(readFileSync(CATALOG_PATH, 'utf8'))
  for (const gal of cat) {
    if (!gal.isReal) continue
    const slug = SLUG_BY_NAME[gal.name]
    if (!slug) continue
    const rng = mulberry32(grainePourNom(gal.name))
    const stars = champEtoiles(gal.name, gal.morphology, rng)
    const ch = rendre(stars, gal.inclinationDeg, gal.positionAngleDeg)
    const flux = ch.reduce((a, b) => a + b, 0)
    const c = flouSeparable(ajouterHalo(ch, flux), 0.9)
    ecrirePNG(c, new URL(`density_realgal_${slug}.png`, OUT_DIR))
    console.log(
      `${slug.padEnd(11)} ${String(stars.length).padStart(6)} étoiles  ${gal.morphology}  i=${gal.inclinationDeg}° PA=${gal.positionAngleDeg}°`
    )
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
