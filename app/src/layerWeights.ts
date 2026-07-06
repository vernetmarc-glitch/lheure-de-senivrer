/**
 * Calcul des poids de fondu entre TOUS les layers (Phase 4), du plus fin
 * (Voie lactée) au plus grossier (univers homogène). Un seul endroit pour
 * cette logique, partagé entre MilkyWayLayer et DensityLayer, pour éviter
 * toute divergence entre les deux.
 */

export const LAYER_ORDER = ['milkyway', 'localgroup', 'l2', 'l3', 'l4', 'l4b', 'l5'] as const
export type LayerKey = (typeof LAYER_ORDER)[number]

// Frontières (Mpc comobiles) entre layers consécutifs, dans l'ordre de LAYER_ORDER.
// 0.1 Mpc : la Voie lactée cède la place aux galaxies du Groupe Local.
// 2.4 Mpc : frontière Groupe Local -> L2, calibrée avec l'outil glow-test.html
// (KDE avec halo+point central vs texture L2), largeur de fondu ~4 Mpc.
export const LAYER_EDGES_MPC = [0.1, 2.4, 30, 150, 300, 2100]

const DEFAULT_FADE_WIDTH_DEX = 0.15 // largeur par défaut, en décades (log10)
// Largeur spécifique pour la frontière Groupe Local/L2 (index 1), calibrée à
// ~4 Mpc de large centrée sur 2.4 Mpc (cf. glow-test.html).
const FADE_WIDTHS_DEX = [DEFAULT_FADE_WIDTH_DEX, 0.52, DEFAULT_FADE_WIDTH_DEX, DEFAULT_FADE_WIDTH_DEX, DEFAULT_FADE_WIDTH_DEX, DEFAULT_FADE_WIDTH_DEX]

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1)
  return t * t * (3 - 2 * t)
}

/** Poids de mélange de tous les layers pour un champ de vue donné (partition de 1). */
export function getLayerWeights(halfWidthMpc: number): Record<LayerKey, number> {
  const x = Math.log10(halfWidthMpc)
  const logEdges = LAYER_EDGES_MPC.map(Math.log10)
  const gates = logEdges.map((e, i) => smoothstep(e - FADE_WIDTHS_DEX[i], e + FADE_WIDTHS_DEX[i], x))

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
