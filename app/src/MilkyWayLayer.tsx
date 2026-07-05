import { useEffect, useRef, useState } from 'react'
import { getLayerWeights } from './layerWeights'

// Le module GalaxyModel est chargé globalement via <script> dans index.html
// (CDN jsDelivr, source de vérité unique partagée avec "Le silence du cosmos").
// Ne jamais dupliquer sa logique ici — uniquement le consommer.
interface GalaxyStar {
  gx: number
  gy: number
  b: number
  sz: number
}
interface GalaxyModelApi {
  MW_R: number
  generateGalaxy: (opts?: { seed?: number; starCount?: number }) => GalaxyStar[]
  galacticToScreen: (
    gx: number,
    gy: number,
    scale: number,
    originX: number,
    originY: number
  ) => { x: number; y: number }
  starColor: (b: number) => string
}
declare global {
  interface Window {
    GalaxyModel?: GalaxyModelApi
  }
}

const LY_PER_MPC = 3.26156e6

interface MilkyWayLayerProps {
  halfWidthMpc: number
  opacity: number
}

export default function MilkyWayLayer({ halfWidthMpc, opacity }: MilkyWayLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const starsRef = useRef<GalaxyStar[] | null>(null)
  const [ready, setReady] = useState(false)

  // Génération unique des étoiles (seed fixe -> toujours les mêmes, cf. gouvernance du modèle partagé).
  useEffect(() => {
    let cancelled = false
    function tryInit() {
      if (window.GalaxyModel) {
        starsRef.current = window.GalaxyModel.generateGalaxy()
        if (!cancelled) setReady(true)
      } else {
        setTimeout(tryInit, 100) // le script CDN peut charger après notre bundle
      }
    }
    tryInit()
    return () => {
      cancelled = true
    }
  }, [])

  const weight = getLayerWeights(halfWidthMpc).milkyway

  useEffect(() => {
    const canvas = canvasRef.current
    const stars = starsRef.current
    const gm = window.GalaxyModel
    if (!canvas || !stars || !gm || weight < 0.003) {
      const ctx = canvas?.getContext('2d')
      if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height)
      return
    }
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const size = canvas.width
    const halfWidthLy = halfWidthMpc * LY_PER_MPC
    const scale = size / 2 / halfWidthLy // px par année-lumière
    const originX = size / 2
    const originY = size / 2

    ctx.clearRect(0, 0, size, size)
    ctx.fillStyle = '#05050a'
    ctx.fillRect(0, 0, size, size)

    for (const star of stars) {
      const p = gm.galacticToScreen(star.gx, star.gy, scale, originX, originY)
      if (p.x < -5 || p.x > size + 5 || p.y < -5 || p.y > size + 5) continue
      const r = Math.max(star.sz * scale * 400, 0.4) // taille perceptible à toutes échelles
      ctx.fillStyle = gm.starColor(star.b)
      ctx.globalAlpha = Math.min(star.b + 0.3, 1)
      ctx.beginPath()
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }, [halfWidthMpc, ready, weight])

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
