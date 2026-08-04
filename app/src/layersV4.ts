/**
 * ESSAI — échelle à 15 lignes (A → O), génération du 02/08/2026.
 *
 * Ce module est INERTE tant que `USE_V4` vaut false : l'échelle de production à
 * 12 paliers reste seule active. Il n'écrase rien et n'est lu que derrière la
 * bascule, afin qu'un résultat décevant n'ait aucun effet sur l'application.
 *
 * Bascule : `?v4=1` dans l'URL, ou VITE_USE_V4=1 à la compilation.
 *
 * Différences avec l'échelle de production
 * ----------------------------------------
 * - 15 lignes géométriques de raison ×2,520 constante, contre 12 paliers dont
 *   les écarts allaient de ×1,41 à ×24 ;
 * - une seule largeur de fondu, 0,15 dex, valable partout — la production
 *   portait une exception à 0,52 sur la frontière 2,4 Mpc pour masquer un écart
 *   de ×24 ;
 * - textures `data/v4/density_<code>.png`, marge 1,5 uniforme (la production
 *   utilisait 2,4 pour `l5`, seul layer visible à son bord extrême) ;
 * - héritage vérifié : F2 ≥ 0,85 sur les 14 paires.
 *
 * Paramètres de génération : `spacetime_matrix.json`, bloc `generation`.
 */
export const V4_ORDER = [
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
] as const
export type V4Key = (typeof V4_ORDER)[number]

/** Demi-champ nominal, en Mpc comobiles (hors marge). */
export const V4_HALF_MPC: Record<V4Key, number> = {
  A: 0.035, B: 0.0882, C: 0.2223, D: 0.5601, E: 1.4113,
  F: 3.556, G: 8.96, H: 22.5821, I: 56.9048, J: 143.395,
  K: 361.3426, L: 910.5509, M: 2294.5067, N: 5781.9515, O: 14570,
}

export const V4_MARGIN = 1.5
export const V4_FADE_DEX = 0.15

/**
 * Frontières entre lignes consécutives : moyenne géométrique des demi-champs
 * encadrants. L'échelle étant géométrique, elles tombent toutes au même endroit
 * relatif — c'est ce qui permet une largeur de fondu unique.
 */
export const V4_EDGES_MPC: number[] = V4_ORDER.slice(0, -1).map((k, i) =>
  Math.sqrt(V4_HALF_MPC[k] * V4_HALF_MPC[V4_ORDER[i + 1]])
)

function smoothstep(a: number, b: number, x: number): number {
  const t = Math.min(Math.max((x - a) / (b - a), 0), 1)
  return t * t * (3 - 2 * t)
}

/** Poids de mélange des 15 lignes pour un champ de vue donné (partition de 1). */
export function getV4Weights(halfWidthMpc: number): Record<V4Key, number> {
  const x = Math.log10(halfWidthMpc)
  const gates = V4_EDGES_MPC.map((e) =>
    smoothstep(Math.log10(e) - V4_FADE_DEX, Math.log10(e) + V4_FADE_DEX, x)
  )
  const w: Partial<Record<V4Key, number>> = {}
  let remaining = 1
  for (let i = 0; i < V4_ORDER.length - 1; i++) {
    w[V4_ORDER[i]] = remaining * (1 - gates[i])
    remaining *= gates[i]
  }
  w[V4_ORDER[V4_ORDER.length - 1]] = remaining
  return w as Record<V4Key, number>
}

/** Bascule d'essai — false par défaut, donc sans effet sur la production. */
export const USE_V4: boolean =
  (typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('v4') === '1') ||
  import.meta.env.VITE_USE_V4 === '1'

export const V4_TEXTURE = (k: V4Key) => `data/v4/density_${k}.png`
