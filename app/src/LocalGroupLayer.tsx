import { useEffect, useRef, useState } from 'react'
import { getLayerWeights } from './layerWeights'
import { colorForValue, type DensityStyle } from './colormaps'
import { onGalaxyReady, type GalaxyStar, type GalaxyModelApi } from './galaxyModelLoader'

const LY_PER_MPC = 3.26156e6

/**
 * Galaxies connues du Groupe Local — distances réelles approximatives,
 * direction (angle) arbitraire (simplification : pas de conversion depuis
 * les coordonnées célestes réelles à ce stade).
 */
interface NearbyGalaxy {
  name: string
  distanceMpc: number
  radiusMpc: number
  angleDeg: number
  brightness: number
}

const NEARBY_GALAXIES: NearbyGalaxy[] = [
  { name: 'Andromède (M31)', distanceMpc: 0.78, radiusMpc: 0.034, angleDeg: 20, brightness: 0.9 },
  { name: 'Triangulum (M33)', distanceMpc: 0.84, radiusMpc: 0.0092, angleDeg: 55, brightness: 0.7 },
  { name: 'Grand Nuage de Magellan', distanceMpc: 0.05, radiusMpc: 0.0022, angleDeg: 200, brightness: 0.75 },
  { name: 'Petit Nuage de Magellan', distanceMpc: 0.061, radiusMpc: 0.0011, angleDeg: 210, brightness: 0.65 },
  { name: 'Naine du Sagittaire', distanceMpc: 0.024, radiusMpc: 0.0015, angleDeg: 320, brightness: 0.5 },
  { name: 'NGC 6822', distanceMpc: 0.46, radiusMpc: 0.001, angleDeg: 110, brightness: 0.55 },
  { name: 'IC 10', distanceMpc: 0.66, radiusMpc: 0.0008, angleDeg: 150, brightness: 0.5 },
  { name: 'Leo I', distanceMpc: 0.82, radiusMpc: 0.0005, angleDeg: 290, brightness: 0.45 },
]

// Population procédurale complémentaire (PAS des données réelles) pour peupler
// progressivement 1 à 10 Mpc et éviter un vide brutal avant le layer 2 —
// illustratif, pas dérivé d'un calcul rigoureux de fonction de luminosité.
function mulberry32(seed: number) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

interface FieldGalaxy {
  distanceMpc: number
  radiusMpc: number
  angleDeg: number
  brightness: number
}

const FIELD_GALAXIES: FieldGalaxy[] = (() => {
  const rng = mulberry32(20260705)
  const list: FieldGalaxy[] = []
  for (let i = 0; i < 55; i++) {
    const distanceMpc = 1 + rng() * 9 // 1 -> 10 Mpc
    list.push({
      distanceMpc,
      radiusMpc: 0.0003 + rng() * 0.0012,
      angleDeg: rng() * 360,
      brightness: 0.3 + rng() * 0.5,
    })
  }
  return list
})()

interface LocalGroupLayerProps {
  halfWidthMpc: number
  opacity: number
  style: DensityStyle
}

export default function LocalGroupLayer({ halfWidthMpc, opacity, style }: LocalGroupLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number | null>(null)
  const starsRef = useRef<GalaxyStar[] | null>(null)
  const gmRef = useRef<GalaxyModelApi | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    return onGalaxyReady((stars, gm) => {
      starsRef.current = stars
      gmRef.current = gm
      setReady(true)
    })
  }, [])

  const weight = getLayerWeights(halfWidthMpc).localgroup

  useEffect(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)

    rafRef.current = requestAnimationFrame(() => {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const size = canvas.width
      ctx.clearRect(0, 0, size, size)
      if (weight < 0.003) return

      const scale = size / 2 / halfWidthMpc // px par Mpc
      const originX = size / 2
      const originY = size / 2

      // --- Notre propre galaxie : même forme que sur le layer "Voie lactée",
      // juste rendue à l'échelle du Mpc au lieu de l'année-lumière. Utilise le
      // même cache d'étoiles -> aucune discontinuité de forme à la transition.
      const stars = starsRef.current
      const gm = gmRef.current
      if (stars && gm) {
        const scalePerLy = scale / LY_PER_MPC
        for (let i = 0; i < stars.length; i++) {
          const star = stars[i]
          const x = originX + star.gx * scalePerLy
          const y = originY + star.gy * scalePerLy * gm.YSCALE
          if (x < -2 || x > size + 2 || y < -2 || y > size + 2) continue
          const r = Math.max(star.sz * scalePerLy * 400, 0.3)
          const [cr, cg, cb] = colorForValue(Math.min(star.b + 0.15, 1), style)
          ctx.fillStyle = `rgb(${cr},${cg},${cb})`
          ctx.globalAlpha = Math.min(star.b + 0.3, 1)
          ctx.beginPath()
          ctx.arc(x, y, r, 0, Math.PI * 2)
          ctx.fill()
        }
        ctx.globalAlpha = 1
      }

      // --- Galaxies réelles du Groupe Local ---
      for (const gal of NEARBY_GALAXIES) {
        const rad = (gal.angleDeg * Math.PI) / 180
        const x = originX + Math.cos(rad) * gal.distanceMpc * scale
        const y = originY + Math.sin(rad) * gal.distanceMpc * scale
        const rPx = Math.max(gal.radiusMpc * scale, 1.2)
        if (x < -rPx || x > size + rPx || y < -rPx || y > size + rPx) continue

        const [cr, cg, cb] = colorForValue(gal.brightness, style)
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, rPx)
        gradient.addColorStop(0, `rgba(${cr},${cg},${cb},0.95)`)
        gradient.addColorStop(1, `rgba(${cr},${cg},${cb},0)`)
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(x, y, rPx, 0, Math.PI * 2)
        ctx.fill()

        if (rPx > 4 && halfWidthMpc < 1.5) {
          ctx.fillStyle = 'rgba(255,255,255,0.75)'
          ctx.font = '10px monospace'
          ctx.fillText(gal.name, x + rPx + 3, y + 3)
        }
      }

      // --- Population procédurale complémentaire (1-10 Mpc), sans étiquette ---
      for (const gal of FIELD_GALAXIES) {
        const rad = (gal.angleDeg * Math.PI) / 180
        const x = originX + Math.cos(rad) * gal.distanceMpc * scale
        const y = originY + Math.sin(rad) * gal.distanceMpc * scale
        const rPx = Math.max(gal.radiusMpc * scale, 0.8)
        if (x < -rPx || x > size + rPx || y < -rPx || y > size + rPx) continue

        const [cr, cg, cb] = colorForValue(gal.brightness, style)
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, rPx)
        gradient.addColorStop(0, `rgba(${cr},${cg},${cb},0.85)`)
        gradient.addColorStop(1, `rgba(${cr},${cg},${cb},0)`)
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(x, y, rPx, 0, Math.PI * 2)
        ctx.fill()
      }
    })

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [halfWidthMpc, weight, style, ready])

  return (
    <canvas
      ref={canvasRef}
      width={640}
      height={640}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        opacity: opacity * weight,
        borderRadius: 8,
      }}
    />
  )
}
