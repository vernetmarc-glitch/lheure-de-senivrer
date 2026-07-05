/**
 * Moteur cosmologique — Phase 1
 *
 * Charge la table précalculée (générée par scripts/generate_cosmology_table.py)
 * et fournit une interpolation continue en fonction du temps (âge de l'univers
 * en milliards d'années, Ga) pour piloter le curseur temporel de l'application.
 *
 * Toutes les distances de rayon (horizon des particules, sphère de Hubble,
 * horizon des événements) sont stockées en Mpc COMOBILES dans la table —
 * c'est la grandeur à utiliser directement pour dessiner les cercles sur la
 * carte à échelle comobile fixe (voir §2 et §3.6 du document d'architecture).
 */

export interface CosmologyRow {
  a: number
  z: number
  t_Gyr: number
  chi_particle_Mpc: number
  r_hubble_comoving_Mpc: number
  chi_event_Mpc: number
}

export interface CosmologyTable {
  meta: {
    H0_km_s_Mpc: number
    omega_m: number
    omega_lambda: number
    omega_r: number
    gly_per_mpc: number
    note: string
  }
  rows: CosmologyRow[]
}

export interface CosmologyState {
  a: number
  z: number
  t_Gyr: number
  chiParticleComovingMpc: number
  rHubbleComovingMpc: number
  chiEventComovingMpc: number
  // Distances propres (physiques) à cet instant t, dérivées de a(t) :
  chiParticleProperGly: number
  rHubbleProperGly: number
  chiEventProperGly: number
}

/** Charge la table JSON précalculée depuis /public/data. */
export async function loadCosmologyTable(): Promise<CosmologyTable> {
  const res = await fetch(`${import.meta.env.BASE_URL}data/cosmology_table.json`)
  if (!res.ok) {
    throw new Error(`Impossible de charger la table cosmologique (${res.status})`)
  }
  return res.json()
}

/** Âge de l'univers aujourd'hui (Ga), c'est-à-dire au point où a est le plus proche de 1. */
export function ageOfUniverseGyr(table: CosmologyTable): number {
  const todayRow = table.rows.reduce((closest, row) =>
    Math.abs(row.a - 1) < Math.abs(closest.a - 1) ? row : closest
  )
  return todayRow.t_Gyr
}

/** Âge minimal couvert par la table (proche de la recombinaison). */
export function minAgeGyr(table: CosmologyTable): number {
  return table.rows[0].t_Gyr
}

/**
 * Interpolation linéaire sur la table triée par t_Gyr croissant.
 * Retourne l'état cosmologique complet à l'instant t_Gyr demandé.
 */
export function interpolateAtTime(table: CosmologyTable, tGyr: number): CosmologyState {
  const rows = table.rows
  const clamped = Math.min(Math.max(tGyr, rows[0].t_Gyr), rows[rows.length - 1].t_Gyr)

  // Recherche dichotomique de l'intervalle encadrant clamped
  let lo = 0
  let hi = rows.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (rows[mid].t_Gyr <= clamped) lo = mid
    else hi = mid
  }

  const r0 = rows[lo]
  const r1 = rows[hi]
  const span = r1.t_Gyr - r0.t_Gyr
  const frac = span > 0 ? (clamped - r0.t_Gyr) / span : 0

  const lerp = (x0: number, x1: number) => x0 + (x1 - x0) * frac

  const a = lerp(r0.a, r1.a)
  const chiParticle = lerp(r0.chi_particle_Mpc, r1.chi_particle_Mpc)
  const rHubble = lerp(r0.r_hubble_comoving_Mpc, r1.r_hubble_comoving_Mpc)
  const chiEvent = lerp(r0.chi_event_Mpc, r1.chi_event_Mpc)
  const glyPerMpc = table.meta.gly_per_mpc

  return {
    a,
    z: 1 / a - 1,
    t_Gyr: clamped,
    chiParticleComovingMpc: chiParticle,
    rHubbleComovingMpc: rHubble,
    chiEventComovingMpc: chiEvent,
    chiParticleProperGly: a * chiParticle * glyPerMpc,
    rHubbleProperGly: a * rHubble * glyPerMpc,
    chiEventProperGly: a * chiEvent * glyPerMpc,
  }
}

/** Facteur de dilution de la densité de matière par rapport à aujourd'hui : 1/a^3. */
export function densityDilutionFactor(a: number): number {
  return 1 / Math.pow(a, 3)
}
