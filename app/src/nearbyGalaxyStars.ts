/**
 * Génère un semis de points (façon étoiles) pour les galaxies réelles du
 * Groupe Local — pas la formule "halo gaussien" utilisée pour les galaxies
 * procédurales lointaines. Objectif : un rendu visuellement cohérent avec la
 * Voie lactée (un nuage de points individuels), pas une simple tache floue.
 *
 * Ceci est un générateur SIMPLIFIÉ propre à ce projet — pas le modèle
 * GalaxyModel partagé (spécifique à la Voie lactée, cf. galaxyModelLoader.ts,
 * ne jamais dupliquer ses constantes). Les galaxies spirales (Andromède,
 * M33) reçoivent une légère structure en bras ; les naines irrégulières
 * (Nuages de Magellan, naines sphéroïdales) un nuage plus diffus.
 */

export interface NearbyStar {
  dx: number // décalage par rapport au centre de la galaxie, en Mpc
  dy: number
  b: number // brillance 0-1
}

function mulberry32(seed: number) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// Classification simplifiée par nom — détermine la morphologie du semis.
const SPIRAL_NAMES = new Set(['Andromède (M31)', 'Triangulum (M33)'])

function starCountFor(radiusMpc: number, brightness: number): number {
  // Plus la galaxie est grande/brillante, plus le semis est dense — reste
  // modeste (perf) : ces galaxies sont petites à l'écran de toute façon.
  return Math.round(60 + brightness * 120 + radiusMpc * 4000)
}

const cache = new Map<string, NearbyStar[]>()

export function generateNearbyGalaxyStars(name: string, radiusMpc: number, brightness: number, seed: number): NearbyStar[] {
  const cacheKey = `${name}`
  const cached = cache.get(cacheKey)
  if (cached) return cached

  const rng = mulberry32(seed)
  const spiral = SPIRAL_NAMES.has(name)
  const flatten = spiral ? 0.38 : 0.7 // aplatissement du disque (vu avec une légère inclinaison)
  const starCount = starCountFor(radiusMpc, brightness)
  const stars: NearbyStar[] = []

  for (let i = 0; i < starCount; i++) {
    const u = rng()
    // Profil radial de type disque exponentiel, tronqué à ~1.3x le rayon.
    let r = radiusMpc * Math.sqrt(-Math.log(1 - u * 0.98)) * 0.55
    r = Math.min(r, radiusMpc * 1.3)
    let theta = rng() * Math.PI * 2
    if (spiral) {
      const pitch = 2.6
      theta += pitch * Math.log(r / radiusMpc + 0.15)
      theta += (rng() - 0.5) * 0.7 // dispersion autour du bras
    }
    const dx = r * Math.cos(theta)
    const dy = r * Math.sin(theta) * flatten
    const b = 0.25 + rng() * 0.55
    stars.push({ dx, dy, b })
  }

  // Petit noyau central plus brillant (bulbe), commun aux deux morphologies.
  const coreCount = Math.round(starCount * 0.12)
  for (let i = 0; i < coreCount; i++) {
    const r = radiusMpc * 0.12 * rng()
    const theta = rng() * Math.PI * 2
    stars.push({ dx: r * Math.cos(theta), dy: r * Math.sin(theta) * flatten, b: 0.75 + rng() * 0.25 })
  }

  cache.set(cacheKey, stars)
  return stars
}
