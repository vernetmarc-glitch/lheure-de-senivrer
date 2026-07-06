/**
 * Génère un semis de points (façon étoiles) pour les galaxies réelles du
 * Groupe Local — pas la formule "halo gaussien" utilisée pour les galaxies
 * procédurales lointaines. Objectif : un rendu visuellement cohérent avec la
 * Voie lactée (un nuage de points individuels), pas une simple tache floue.
 *
 * Morphologies basées sur une recherche de la vraie forme de chaque galaxie
 * (juillet 2026) :
 * - Andromède (M31), Triangulum (M33) : spirales classiques.
 * - Grand Nuage de Magellan (LMC) : spirale barrée SB(s)m — une barre
 *   centrale dominante, pas de bulbe, structure spirale très lâche.
 * - Petit Nuage de Magellan (SMC) : naine irrégulière amorphe, allongée
 *   selon la ligne de visée, avec une extension asymétrique ("aile") vers
 *   le LMC — pas de structure organisée.
 * - Naine du Sagittaire : sphéroïde elliptique en cours de démantèlement
 *   par effet de marée — allongée, lisse, sans structure interne marquée.
 * - Autres naines (IC10, NGC6822, Leo I...) : irrégulières diffuses génériques.
 *
 * Ceci est un générateur SIMPLIFIÉ propre à ce projet — pas le modèle
 * GalaxyModel partagé (spécifique à la Voie lactée, cf. galaxyModelLoader.ts,
 * ne jamais dupliquer ses constantes).
 */

export interface NearbyStar {
  dx: number // décalage par rapport au centre, normalisé (en unités du rayon de la galaxie — multiplier par le rayon réel côté appelant)
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

type Morphology = 'spiral' | 'barred' | 'irregular_wing' | 'elliptical_stream' | 'irregular'

const MORPHOLOGY_BY_NAME: Record<string, Morphology> = {
  'Andromède (M31)': 'spiral',
  'Triangulum (M33)': 'spiral',
  'Grand Nuage de Magellan': 'barred',
  'Petit Nuage de Magellan': 'irregular_wing',
  'Naine du Sagittaire': 'elliptical_stream',
}

function morphologyFor(name: string): Morphology {
  return MORPHOLOGY_BY_NAME[name] ?? 'irregular'
}

function starCountFor(radiusMpcHint: number, brightness: number): number {
  // Plus la galaxie est grande/brillante, plus le semis est dense — reste
  // modeste (perf) : ces galaxies sont petites à l'écran de toute façon.
  // radiusMpcHint sert UNIQUEMENT d'indice de taille relative (toujours en
  // Mpc, l'unité canonique du catalogue) — n'affecte pas l'échelle spatiale
  // des points générés (normalisée, cf. NearbyStar).
  return Math.round(60 + brightness * 120 + radiusMpcHint * 4000)
}

const cache = new Map<string, NearbyStar[]>()

/**
 * Génère un semis de points NORMALISÉ (rayon caractéristique = 1) pour une
 * galaxie réelle — indépendant de l'unité utilisée ensuite pour l'afficher
 * (Mpc dans LocalGroupLayer, années-lumière dans MilkyWayLayer). Multiplier
 * dx/dy par le rayon réel (dans l'unité voulue) côté appelant.
 *
 * @param radiusMpcHint Rayon en Mpc (unité canonique du catalogue), utilisé
 *   uniquement pour calibrer la densité du semis — PAS l'échelle spatiale.
 */
export function generateNearbyGalaxyStars(name: string, radiusMpcHint: number, brightness: number, seed: number): NearbyStar[] {
  const cacheKey = name
  const cached = cache.get(cacheKey)
  if (cached) return cached

  const rng = mulberry32(seed)
  const morphology = morphologyFor(name)
  const starCount = starCountFor(radiusMpcHint, brightness)
  const stars: NearbyStar[] = []
  const radius = 1 // normalisé — le rayon réel est appliqué côté appelant

  const flatten = morphology === 'spiral' ? 0.38 : morphology === 'barred' ? 0.5 : morphology === 'elliptical_stream' ? 0.42 : 0.7

  for (let i = 0; i < starCount; i++) {
    const u = rng()
    // Profil radial de type disque exponentiel, tronqué à ~1.3x le rayon.
    let r = radius * Math.sqrt(-Math.log(1 - u * 0.98)) * 0.55
    r = Math.min(r, radius * 1.3)
    let theta = rng() * Math.PI * 2

    if (morphology === 'spiral') {
      const pitch = 2.6
      theta += pitch * Math.log(r / radius + 0.15)
      theta += (rng() - 0.5) * 0.7 // dispersion autour du bras
    } else if (morphology === 'barred') {
      // Barre centrale dominante (LMC) : une fraction des étoiles s'aligne
      // sur un axe fixe plutôt qu'une distribution isotrope, + un soupçon de
      // structure spirale très lâche au-delà de la barre (SB(s)m, pas de bulbe).
      if (rng() < 0.45) {
        const barLength = radius * 0.85
        const along = (rng() * 2 - 1) * barLength
        const across = (rng() - 0.5) * radius * 0.18
        stars.push({ dx: along, dy: across * flatten, b: 0.4 + rng() * 0.5 })
        continue
      }
      const pitch = 1.1 // bras très lâche, à peine perceptible
      theta += pitch * Math.log(r / radius + 0.2)
      theta += (rng() - 0.5) * 1.4 // beaucoup plus de dispersion qu'une vraie spirale
    } else if (morphology === 'irregular_wing') {
      // SMC : nuage amorphe + extension asymétrique ("aile") vers un côté
      // fixe (tidalement étirée), pas de symétrie de rotation.
      if (rng() < 0.25) {
        const wingDir = 0.6 // angle fixe de l'aile (radians), cohérent entre étoiles
        const wingR = radius * (0.9 + rng() * 0.9)
        const spread = (rng() - 0.5) * radius * 0.4
        const dx = wingR * Math.cos(wingDir) - spread * Math.sin(wingDir)
        const dy = (wingR * Math.sin(wingDir) + spread * Math.cos(wingDir)) * flatten
        stars.push({ dx, dy, b: 0.2 + rng() * 0.4 })
        continue
      }
      theta += (rng() - 0.5) * 2.2 // amorphe : pas de structure de rotation
    } else if (morphology === 'elliptical_stream') {
      // Sphéroïde étiré par effet de marée : lisse, concentré, allongé selon
      // un axe fixe (pas de bras, pas de clumps).
      r = radius * Math.pow(rng(), 0.7) // profil lisse, plus concentré qu'un disque exponentiel
    }

    const dx = r * Math.cos(theta)
    const dy = r * Math.sin(theta) * flatten
    const b = morphology === 'elliptical_stream' ? 0.35 + rng() * 0.35 : 0.25 + rng() * 0.55
    stars.push({ dx, dy, b })
  }

  // Petit noyau central plus brillant, commun à toutes les morphologies
  // (moins marqué pour les irrégulières, qui n'ont pas vraiment de bulbe).
  const coreFraction = morphology === 'irregular' || morphology === 'irregular_wing' ? 0.05 : 0.12
  const coreCount = Math.round(starCount * coreFraction)
  for (let i = 0; i < coreCount; i++) {
    const r = radius * 0.12 * rng()
    const theta = rng() * Math.PI * 2
    stars.push({ dx: r * Math.cos(theta), dy: r * Math.sin(theta) * flatten, b: 0.75 + rng() * 0.25 })
  }

  cache.set(cacheKey, stars)
  return stars
}
