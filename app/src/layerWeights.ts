/**
 * Calcul des poids de fondu entre TOUS les layers (Phase 4), du plus fin
 * (Voie lactée) au plus grossier (univers homogène). Un seul endroit pour
 * cette logique, partagé entre MilkyWayLayer et DensityLayer, pour éviter
 * toute divergence entre les deux.
 */

export const LAYER_ORDER = ['milkyway', 'localgroup', 'l2', 'l3', 'l4', 'l4b', 'l5'] as const
export type LayerKey = (typeof LAYER_ORDER)[number]

// Frontières (Mpc comobiles) entre layers consécutifs, dans l'ordre de LAYER_ORDER.
// 0.1 Mpc : la Voie lactée (rayon ~0,016 Mpc) cède la place aux galaxies voisines
// du Groupe Local (Andromède, M33, etc., réparties jusqu'à ~1 Mpc).
export const LAYER_EDGES_MPC = [0.1, 3, 30, 150, 300, 2100]

const FADE_WIDTH_DEX = 0.15 // largeur de la zone de fondu, en décades (log10)

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1)
  return t * t * (3 - 2 * t)
}

/** Poids de mélange de tous les layers pour un champ de vue donné (partition de 1). */
export function getLayerWeights(halfWidthMpc: number): Record<LayerKey, number> {
  const x = Math.log10(halfWidthMpc)
  const logEdges = LAYER_EDGES_MPC.map(Math.log10)
  const gates = logEdges.map((e) => smoothstep(e - FADE_WIDTH_DEX, e + FADE_WIDTH_DEX, x))

  const weights: Partial<Record<LayerKey, number>> = {}
  let remaining = 1
  for (let i = 0; i < LAYER_ORDER.length - 1; i++) {
    const w = remaining * (1 - gates[i])
    weights[LAYER_ORDER[i]] = w
    remaining = remaining * gates[i]
  }
  weights[LAYER_ORDER[LAYER_ORDER.length - 1]] = remaining

  return weights as Record<LayerKey, number>
}
