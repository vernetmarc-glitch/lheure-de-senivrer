import { useEffect, useRef } from 'react'
import { getLayerWeights } from './layerWeights'
import { colorForValue, type DensityStyle } from './colormaps'

/**
 * Galaxies connues du Groupe Local, avec leur distance réelle approximative
 * à la Voie lactée et leur rayon physique approximatif (valeurs
 * astronomiques usuelles, arrondies). La direction (angle) est en revanche
 * arbitraire : une projection 2D "vue du dessus" fidèle demanderait de
 * convertir les coordonnées célestes réelles (ascension droite/déclinaison),
 * ce qui dépasse le cadre de cette étape — simplification à noter.
 */
interface NearbyGalaxy {
  name: string
  distanceMpc: number
  radiusMpc: number
  angleDeg: number
  brightness: number // 0-1, pour la coloration via la palette du style choisi
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

interface LocalGroupLayerProps {
  halfWidthMpc: number
  opacity: number
  style: DensityStyle
}

export default function LocalGroupLayer({ halfWidthMpc, opacity, style }: LocalGroupLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number | null>(null)

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

      // Notre propre position (centre de la carte)
      const [mr, mg, mb] = colorForValue(0.9, style)
      ctx.fillStyle = `rgb(${mr},${mg},${mb})`
      ctx.beginPath()
      ctx.arc(originX, originY, Math.max(2, 0.02 * scale), 0, Math.PI * 2)
      ctx.fill()

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

        // Étiquette si assez zoomé pour que ce soit lisible sans surcharger la vue
        if (rPx > 4 && halfWidthMpc < 1.5) {
          ctx.fillStyle = 'rgba(255,255,255,0.75)'
          ctx.font = '10px monospace'
          ctx.fillText(gal.name, x + rPx + 3, y + 3)
        }
      }
    })

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [halfWidthMpc, weight, style])

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
