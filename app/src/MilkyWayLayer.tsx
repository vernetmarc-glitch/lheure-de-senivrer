import { useEffect, useRef, useState } from 'react'
import { getLayerWeights } from './layerWeights'
import { colorForValue, type DensityStyle } from './colormaps'
import { onGalaxyReady, type GalaxyStar, type GalaxyModelApi } from './galaxyModelLoader'
import { generateNearbyGalaxyStars } from './nearbyGalaxyStars'
import { useRealGalaxyCatalog } from './useRealGalaxyCatalog'

const LY_PER_MPC = 3.26156e6

interface MilkyWayLayerProps {
  halfWidthMpc: number
  opacity: number
  style: DensityStyle
  width: number
  height: number
  dpr: number
}

export default function MilkyWayLayer({ halfWidthMpc, opacity, style, width, height, dpr }: MilkyWayLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const starsRef = useRef<GalaxyStar[] | null>(null)
  const gmRef = useRef<GalaxyModelApi | null>(null)
  const rafRef = useRef<number | null>(null)
  const [ready, setReady] = useState(false)
  const catalog = useRealGalaxyCatalog()

  useEffect(() => {
    return onGalaxyReady((stars, gm) => {
      starsRef.current = stars
      gmRef.current = gm
      setReady(true)
    })
  }, [])

  const weight = getLayerWeights(halfWidthMpc).milkyway

  useEffect(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)

    rafRef.current = requestAnimationFrame(() => {
      const canvas = canvasRef.current
      const stars = starsRef.current
      const gm = gmRef.current
      if (!canvas || width < 1 || height < 1) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const W = canvas.width
      const H = canvas.height
      if (!stars || !gm || weight < 0.003) {
        ctx.clearRect(0, 0, W, H)
        return
      }

      const shortSide = Math.min(W, H)
      const halfWidthLy = halfWidthMpc * LY_PER_MPC
      const scale = shortSide / 2 / halfWidthLy
      const originX = W / 2
      const originY = H / 2
      const margin = 8 * dpr

      ctx.clearRect(0, 0, W, H)
      ctx.fillStyle = 'rgb(0,0,4)'
      ctx.fillRect(0, 0, W, H)

      for (let i = 0; i < stars.length; i++) {
        const star = stars[i]
        const x = originX + star.gx * scale
        const y = originY + star.gy * scale * gm.YSCALE
        if (x < -margin || x > W + margin || y < -margin || y > H + margin) continue
        const r = Math.max(star.sz * scale * 400, 0.4 * dpr)
        const [cr, cg, cb] = colorForValue(Math.min(star.b + 0.15, 1), style)
        ctx.fillStyle = `rgb(${cr},${cg},${cb})`
        ctx.globalAlpha = Math.min(star.b + 0.3, 1)
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalAlpha = 1

      // --- Galaxies réelles voisines (Nuages de Magellan, Naine du
      // Sagittaire...) : elles ne disparaissent pas juste parce qu'on zoome
      // sur la Voie lactée — elles restent physiquement là. Même générateur
      // que LocalGroupLayer, à l'échelle année-lumière au lieu du Mpc.
      if (catalog) {
        for (const gal of catalog) {
          const distanceLy = gal.distanceMpc * LY_PER_MPC
          const radiusLy = gal.radiusMpc * LY_PER_MPC
          const rad = (gal.angleDeg * Math.PI) / 180
          const centerX = originX + Math.cos(rad) * distanceLy * scale
          const centerY = originY + Math.sin(rad) * distanceLy * scale
          const galRadiusPx = radiusLy * scale
          if (
            centerX < -galRadiusPx - margin ||
            centerX > W + galRadiusPx + margin ||
            centerY < -galRadiusPx - margin ||
            centerY > H + galRadiusPx + margin
          )
            continue

          const seed = (gal.name?.length ?? 1) * 7919 + Math.round(gal.distanceMpc * 100000)
          const galStars = generateNearbyGalaxyStars(gal.name ?? '', gal.radiusMpc, gal.brightness, seed)
          for (const s of galStars) {
            const x = centerX + s.dx * radiusLy * scale
            const y = centerY + s.dy * radiusLy * scale
            const r = Math.max(0.35 * dpr, galRadiusPx * 0.02)
            const [cr, cg, cb] = colorForValue(Math.min(s.b + gal.brightness * 0.2, 1), style)
            ctx.fillStyle = `rgb(${cr},${cg},${cb})`
            ctx.globalAlpha = Math.min(s.b + 0.25, 1)
            ctx.beginPath()
            ctx.arc(x, y, r, 0, Math.PI * 2)
            ctx.fill()
          }
        }
        ctx.globalAlpha = 1
      }
    })

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [halfWidthMpc, ready, weight, style, width, height, dpr, catalog])

  return (
    <canvas
      ref={canvasRef}
      width={Math.max(Math.round(width), 1)}
      height={Math.max(Math.round(height), 1)}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        opacity: opacity * weight,
      }}
    />
  )
}
