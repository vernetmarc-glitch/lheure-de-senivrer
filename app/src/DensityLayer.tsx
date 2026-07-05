import { useEffect, useRef, useState } from 'react'
import { buildLookupTable, type DensityStyle } from './colormaps'

interface DensityLayerProps {
  style: DensityStyle
  opacity: number // 0-1, "présence" du fond
}

/**
 * Couche de densité de matière (Phase 4, démo à un seul champ pour l'instant).
 *
 * La texture source (niveaux de gris, générée offline par
 * scripts/generate_density_demo.py) est chargée une fois, puis recolorée
 * entièrement côté client à chaque changement de style — pas de round-trip
 * serveur, changement instantané.
 */
export default function DensityLayer({ style, opacity }: DensityLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const grayDataRef = useRef<ImageData | null>(null)
  const [loaded, setLoaded] = useState(false)

  // Chargement unique de la texture source en niveaux de gris.
  useEffect(() => {
    const img = new Image()
    img.src = `${import.meta.env.BASE_URL}data/density_demo.png`
    img.onload = () => {
      const off = document.createElement('canvas')
      off.width = img.naturalWidth
      off.height = img.naturalHeight
      const octx = off.getContext('2d')
      if (!octx) return
      octx.drawImage(img, 0, 0)
      grayDataRef.current = octx.getImageData(0, 0, off.width, off.height)
      setLoaded(true)
    }
  }, [])

  // Recoloration à chaque changement de style (instantané, tout se fait en mémoire).
  useEffect(() => {
    const canvas = canvasRef.current
    const gray = grayDataRef.current
    if (!canvas || !gray) return

    canvas.width = gray.width
    canvas.height = gray.height
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const lut = buildLookupTable(style)
    const out = ctx.createImageData(gray.width, gray.height)
    for (let i = 0; i < gray.data.length; i += 4) {
      const v = gray.data[i] // R=G=B en niveaux de gris
      out.data[i] = lut[v * 3]
      out.data[i + 1] = lut[v * 3 + 1]
      out.data[i + 2] = lut[v * 3 + 2]
      out.data[i + 3] = 255
    }
    ctx.putImageData(out, 0, 0)
  }, [style, loaded])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        opacity,
        borderRadius: 8,
      }}
    />
  )
}
