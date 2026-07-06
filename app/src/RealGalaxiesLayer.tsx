import { useEffect, useRef, useState } from 'react'
import { colorForValue, type DensityStyle } from './colormaps'
import { getStyleParamsForLayer } from './densityStyle'
import { getLayerWeights } from './layerWeights'

/**
 * Compose les 8 galaxies réelles nommées du Groupe Local (Andromède, M33,
 * Nuages de Magellan, Naine du Sagittaire, NGC 6822, IC 10, Leo I) à partir
 * de sprites pré-cuits individuels (cf. scripts/generate_simulated_textures.mjs
 * pour l'historique : une texture partagée à l'échelle du Groupe Local leur
 * faisait perdre toute structure visible, un split par distance créait un
 * doublon visuel — chaque galaxie a maintenant SA PROPRE texture,
 * dimensionnée sur sa propre taille).
 *
 * Reste un rendu "en direct" par nécessité (position/taille dépendent du
 * zoom courant), mais LÉGER : quelques `drawImage` par frame (un par
 * galaxie visible), pas ~40 000 tracés canvas comme l'ancien rendu
 * étoile-par-étoile.
 */

const SPRITE_MARGIN = 1.7 // GARDER SYNCHRONISÉ avec scripts/generate_simulated_textures.mjs

interface CatalogGalaxy {
  name: string | null
  distanceMpc: number
  radiusMpc: number
  angleDeg: number
  brightness: number
  isReal: boolean
}

// Nom catalogue -> fichier sprite. GARDER SYNCHRONISÉ avec SLUG_BY_NAME dans
// scripts/generate_simulated_textures.mjs.
const SLUG_BY_NAME: Record<string, string> = {
  'Andromède (M31)': 'andromede',
  'Triangulum (M33)': 'triangulum',
  'Grand Nuage de Magellan': 'lmc',
  'Petit Nuage de Magellan': 'smc',
  'Naine du Sagittaire': 'sagittaire',
  'NGC 6822': 'ngc6822',
  'IC 10': 'ic10',
  'Leo I': 'leo1',
}

interface RealGalaxiesLayerProps {
  halfWidthMpc: number
  opacity: number
  style: DensityStyle
  width: number
  height: number
}

export default function RealGalaxiesLayer({ halfWidthMpc, opacity, style, width, height }: RealGalaxiesLayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const catalogRef = useRef<CatalogGalaxy[] | null>(null)
  const spritesRef = useRef<Record<string, HTMLCanvasElement>>({}) // grayscale source, chargé une fois
  const coloredRef = useRef<Record<string, HTMLCanvasElement>>({}) // recoloré selon le style courant
  const [assetsVersion, setAssetsVersion] = useState(0)

  // Chargement du catalogue + des 8 sprites, une seule fois.
  useEffect(() => {
    let cancelled = false
    async function load() {
      const res = await fetch(`${import.meta.env.BASE_URL}data/local_group_catalog.json`)
      const catalog: CatalogGalaxy[] = await res.json()
      const real = catalog.filter((g) => g.isReal)
      catalogRef.current = real
      await Promise.all(
        real.map(
          (gal) =>
            new Promise<void>((resolve) => {
              const slug = SLUG_BY_NAME[gal.name ?? '']
              if (!slug) {
                resolve()
                return
              }
              const img = new Image()
              img.src = `${import.meta.env.BASE_URL}data/density_realgal_${slug}.png`
              img.onload = () => {
                const off = document.createElement('canvas')
                off.width = img.naturalWidth
                off.height = img.naturalHeight
                off.getContext('2d')!.drawImage(img, 0, 0)
                spritesRef.current[slug] = off
                resolve()
              }
              img.onerror = () => resolve()
            })
        )
      )
      if (!cancelled) setAssetsVersion((v) => v + 1)
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  // Recoloration des sprites (léger : 8 textures de 256x256) quand le style
  // change ou que les assets viennent de charger.
  useEffect(() => {
    const catalog = catalogRef.current
    if (!catalog) return
    const params = getStyleParamsForLayer('realgalaxy')
    for (const gal of catalog) {
      const slug = SLUG_BY_NAME[gal.name ?? '']
      const src = slug ? spritesRef.current[slug] : null
      if (!src) continue
      const n = src.width
      const srcCtx = src.getContext('2d')!
      const data = srcCtx.getImageData(0, 0, n, n)
      const out = srcCtx.createImageData(n, n)
      for (let i = 0; i < n * n; i++) {
        const v = Math.pow(data.data[i * 4] / 255, params.gamma)
        const [r, g, b] = colorForValue(v, style)
        out.data[i * 4] = r
        out.data[i * 4 + 1] = g
        out.data[i * 4 + 2] = b
        out.data[i * 4 + 3] = 255
      }
      const canvas = document.createElement('canvas')
      canvas.width = n
      canvas.height = n
      canvas.getContext('2d')!.putImageData(out, 0, 0)
      coloredRef.current[slug] = canvas
    }
    draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [style, assetsVersion])

  function draw() {
    const canvas = canvasRef.current
    const catalog = catalogRef.current
    if (!canvas || !catalog || width < 1 || height < 1) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const W = canvas.width
    const H = canvas.height
    ctx.clearRect(0, 0, W, H)

    // Visibles sur toute la plage de zoom "environnement proche" (milkyway)
    // + "Groupe Local" (localgroup) — les deux se recouvrent pendant le
    // fondu entre les deux, d'où la somme plutôt qu'un simple max.
    const weights = getLayerWeights(halfWidthMpc)
    const galaxyOpacity = Math.min(1, weights.milkyway + weights.localgroup)
    if (galaxyOpacity < 0.003) return

    const shortSide = Math.min(W, H)
    const scale = shortSide / 2 / halfWidthMpc // px par Mpc
    const originX = W / 2
    const originY = H / 2
    const MIN_SCREEN_RADIUS_PX = 1.2 // plancher pour rester visible même très dézoomé

    ctx.globalAlpha = galaxyOpacity
    for (const gal of catalog) {
      const slug = SLUG_BY_NAME[gal.name ?? '']
      const sprite = slug ? coloredRef.current[slug] : null
      if (!sprite) continue
      const rad = (gal.angleDeg * Math.PI) / 180
      const cx = originX + Math.cos(rad) * gal.distanceMpc * scale
      const cy = originY + Math.sin(rad) * gal.distanceMpc * scale
      const halfSizePx = Math.max(gal.radiusMpc * SPRITE_MARGIN * scale, MIN_SCREEN_RADIUS_PX)
      if (cx < -halfSizePx || cx > W + halfSizePx || cy < -halfSizePx || cy > H + halfSizePx) continue
      ctx.drawImage(sprite, cx - halfSizePx, cy - halfSizePx, halfSizePx * 2, halfSizePx * 2)
    }
    ctx.globalAlpha = 1
  }

  useEffect(() => {
    draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [halfWidthMpc, width, height, assetsVersion])

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
        opacity,
      }}
    />
  )
}
