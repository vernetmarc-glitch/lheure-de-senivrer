/**
 * Poids de fondu entre les QUINZE lignes de la grille `A` -> `O`, du plus fin
 * (0,035 Mpc, la Voie lactée remplit le cadre) au plus grossier (14 570 Mpc,
 * l'univers observable entier).
 *
 * REMPLACE le découpage historique en douze paliers (`milkyway`, `localgroup`,
 * `l1b`... `l5`), le 11/08/2026. Celui-ci avait des pas irréguliers — jusqu'à
 * ×24 entre le Groupe Local et le premier palier de texture, masqué par une
 * largeur de fondu spéciale de 0,52 dex sur cette seule arête. La grille
 * `A` -> `O` est GÉOMÉTRIQUE : raison ×2,520 constante, soit 0,401385 dex, donc
 * une seule largeur de fondu pour toutes les arêtes.
 *
 * SOURCE DE VÉRITÉ : `app/public/data/spacetime_matrix.json`, bloc `zoom_axis`.
 * Les demi-largeurs ci-dessous en sont recopiées. **Si la matrice change, ce
 * fichier doit être repris** — c'est la raison d'être de T-101, qui compare les
 * deux et refuse de laisser l'écart s'installer en silence.
 */

export const LAYER_ORDER = [
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
] as const
export type LayerKey = (typeof LAYER_ORDER)[number]

/** Demi-largeur VISIBLE de chaque ligne, en Mpc. Recopiée de la matrice. */
export const LAYER_HALFWIDTH_MPC: Record<LayerKey, number> = {
  A: 0.035,
  B: 0.0882,
  C: 0.2222,
  D: 0.56,
  E: 1.4113,
  F: 3.5563,
  G: 8.9615,
  H: 22.5821,
  I: 56.9048,
  J: 143.395,
  K: 361.3426,
  L: 910.5509,
  M: 2294.5067,
  N: 5781.9515,
  O: 14570,
}

/**
 * Marge de génération : chaque texture couvre `halfwidth * MARGIN` de
 * demi-largeur physique. GARDER SYNCHRONISÉ avec `RENDER_MARGIN` dans
 * `scripts/dev/gen_chain.py` — la texture fait 480 px pour 320 px visibles.
 */
export const LAYER_MARGIN = 1.5

/**
 * Frontières entre lignes consécutives : moyenne géométrique des deux
 * demi-largeurs encadrantes. Avec une raison constante elles tombent toutes au
 * même endroit relatif dans le pas — c'est ce qui permet une largeur unique.
 */
export const LAYER_EDGES_MPC = LAYER_ORDER.slice(0, -1).map((k, i) =>
  Math.sqrt(LAYER_HALFWIDTH_MPC[k] * LAYER_HALFWIDTH_MPC[LAYER_ORDER[i + 1]])
)

// 0,15 dex pour TOUTES les arêtes, soit 37 % du pas de 0,401385 dex.
// `zoom_axis.fade_width_dex` dans la matrice.
const FADE_WIDTH_DEX = 0.15

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1)
  return t * t * (3 - 2 * t)
}

/** Poids de mélange des quinze lignes pour un champ de vue donné (partition de 1). */
export function getLayerWeights(halfWidthMpc: number): Record<LayerKey, number> {
  const x = Math.log10(halfWidthMpc)
  const gates = LAYER_EDGES_MPC.map((e) =>
    smoothstep(Math.log10(e) - FADE_WIDTH_DEX, Math.log10(e) + FADE_WIDTH_DEX, x)
  )

  const weights: Partial<Record<LayerKey, number>> = {}
  let remaining = 1
  for (let i = 0; i < LAYER_ORDER.length - 1; i++) {
    weights[LAYER_ORDER[i]] = remaining * (1 - gates[i])
    remaining = remaining * gates[i]
  }
  weights[LAYER_ORDER[LAYER_ORDER.length - 1]] = remaining

  return weights as Record<LayerKey, number>
}
