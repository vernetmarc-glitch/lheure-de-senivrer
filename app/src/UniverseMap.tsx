import { useEffect, useMemo, useRef, useState } from 'react'
import { densityDilutionFactor, type CosmologyState } from './cosmology'
import DensityLayer from './DensityLayer'
import RealGalaxiesLayer from './RealGalaxiesLayer'
import { type DensityStyle } from './colormaps'
import InfoModal from './InfoModal'

const MIN_HALF_WIDTH_MPC = 0.02 // ~65 000 al — la Voie lactée (rayon 52 000 al) remplit le cadre
const MAX_HALF_WIDTH_MPC = 14570 // ~95 Gal de côté au total
const GLY_PER_MPC = 3.26156e-3

// Style et présence du fond de densité : fixés (l'ancien bouton réglages,
// devenu inutile, a été retiré) — Astro reste le style par défaut.
const DENSITY_STYLE: DensityStyle = 'astro'
const DENSITY_PRESENCE = 1.0

const DPR = Math.min(window.devicePixelRatio || 1, 3)
// Au-delà de ce ratio largeur/hauteur (ou l'inverse), on fige la zone de
// rendu à ce ratio et on ajoute des bandes noires fixes plutôt que de
// laisser un espace qu'aucun layer ne remplit encore (observé sur écrans
// très larges en PC, ou très étirés verticalement).
const MAX_ASPECT = 2.4

function formatDistance(mpc: number): string {
  const gly = mpc * GLY_PER_MPC
  if (gly >= 1) return `${gly.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} Gal`
  const mly = gly * 1000
  if (mly >= 1) return `${mly.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mal`
  const ly = mly * 1e6
  return `${Math.round(ly).toLocaleString('fr-FR')} al`
}

function niceGridStep(target: number): number {
  const exp = Math.floor(Math.log10(target))
  const base = target / Math.pow(10, exp)
  const niceBase = base < 1.5 ? 1 : base < 3.5 ? 2 : base < 7.5 ? 5 : 10
  return niceBase * Math.pow(10, exp)
}

/** Suit la taille réelle (en pixels) d'un conteneur, pour un rendu plein écran non déformé. */
function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return [ref, size] as const
}

interface UniverseMapProps {
  cosmology: CosmologyState
  tGyr: number
  tMin: number
  tMax: number
  onTimeChange: (t: number) => void
}

export default function UniverseMap({ cosmology, tGyr, tMin, tMax, onTimeChange }: UniverseMapProps) {
  const [containerRef, { width, height }] = useElementSize<HTMLDivElement>()
  const [zoomSliderRef, zoomSliderSize] = useElementSize<HTMLDivElement>()
  const gridCanvasRef = useRef<HTMLCanvasElement>(null)
  const [logHalfWidth, setLogHalfWidth] = useState(Math.log10(MAX_HALF_WIDTH_MPC))
  const [loadProgress, setLoadProgress] = useState({ loaded: 0, total: 1 })
  const [aboutOpen, setAboutOpen] = useState(false)
  const [horizonInfoOpen, setHorizonInfoOpen] = useState(false)
  // Position (en px CSS, relative au cadre de rendu) de l'étiquette "Horizon
  // des particules" dessinée sur le canvas — recalculée à chaque frame de la
  // grille pour placer le bouton "i" HTML par-dessus au bon endroit.
  const [horizonLabelPos, setHorizonLabelPos] = useState<{ x: number; y: number } | null>(null)
  const halfWidthMpc = Math.pow(10, logHalfWidth)
  const dilution = densityDilutionFactor(cosmology.a)

  // Zone de rendu clampée au ratio max — le reste (bandes) montre juste le
  // fond noir du conteneur. Évite qu'un layer "disparaisse" avant que le
  // suivant ait eu la place de le remplacer sur un écran hors gabarit.
  let renderWidth = width
  let renderHeight = height
  if (width > height * MAX_ASPECT) renderWidth = height * MAX_ASPECT
  if (height > width * MAX_ASPECT) renderHeight = width * MAX_ASPECT

  // Résolution physique réelle (pas seulement CSS) : évite qu'un canvas trop
  // petit soit ré-agrandi (et donc flouté) par le navigateur sur un écran
  // haute densité (Retina, la plupart des smartphones récents).
  const pixelWidth = renderWidth * DPR
  const pixelHeight = renderHeight * DPR

  // Zoom à la molette, sur toute la zone de carte.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      setLogHalfWidth((v) => {
        const next = v + e.deltaY * 0.001
        return Math.min(Math.max(next, Math.log10(MIN_HALF_WIDTH_MPC)), Math.log10(MAX_HALF_WIDTH_MPC))
      })
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const gridStepMpc = useMemo(() => niceGridStep(halfWidthMpc / 4), [halfWidthMpc])

  useEffect(() => {
    const canvas = gridCanvasRef.current
    if (!canvas || width < 1 || height < 1) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width
    const H = canvas.height
    const shortSide = Math.min(W, H)
    const pxPerMpc = shortSide / (2 * halfWidthMpc)
    const cx = W / 2
    const cy = H / 2

    // Fond transparent : la couche de densité (DensityLayer) est affichée en dessous.
    ctx.clearRect(0, 0, W, H)
    const densityGlow = Math.min(0.08, 0.012 * Math.log10(dilution + 1))
    ctx.fillStyle = `rgba(10, 10, 20, ${0.15 + densityGlow})`
    ctx.fillRect(0, 0, W, H)

    ctx.strokeStyle = 'rgba(255,255,255,0.12)'
    ctx.lineWidth = 1 * DPR
    const nLinesX = Math.ceil(W / 2 / pxPerMpc / gridStepMpc) + 1
    const nLinesY = Math.ceil(H / 2 / pxPerMpc / gridStepMpc) + 1
    for (let i = -nLinesX; i <= nLinesX; i++) {
      const px = cx + i * gridStepMpc * pxPerMpc
      if (px >= 0 && px <= W) {
        ctx.beginPath()
        ctx.moveTo(px, 0)
        ctx.lineTo(px, H)
        ctx.stroke()
      }
    }
    for (let i = -nLinesY; i <= nLinesY; i++) {
      const py = cy + i * gridStepMpc * pxPerMpc
      if (py >= 0 && py <= H) {
        ctx.beginPath()
        ctx.moveTo(0, py)
        ctx.lineTo(W, py)
        ctx.stroke()
      }
    }

    ctx.strokeStyle = 'rgba(255,255,255,0.22)'
    ctx.fillStyle = 'rgba(255,255,255,0.55)'
    ctx.font = `${11 * DPR}px monospace`
    const maxRingLines = Math.max(nLinesX, nLinesY)
    const maxRingPx = Math.max(W, H) * 0.75
    for (let i = 1; i <= maxRingLines; i++) {
      const rMpc = i * gridStepMpc
      const rPx = rMpc * pxPerMpc
      if (rPx > maxRingPx) break
      ctx.beginPath()
      ctx.arc(cx, cy, rPx, 0, Math.PI * 2)
      ctx.stroke()
      ctx.fillText(formatDistance(rMpc), cx + 4 * DPR, cy - rPx - 4 * DPR)
    }

    const horizonRPx = cosmology.chiParticleComovingMpc * pxPerMpc
    ctx.strokeStyle = '#5aa9e6'
    ctx.lineWidth = 2 * DPR
    ctx.beginPath()
    ctx.arc(cx, cy, horizonRPx, 0, Math.PI * 2)
    ctx.stroke()
    if (horizonRPx < Math.max(W, H) * 0.9) {
      ctx.fillStyle = '#5aa9e6'
      ctx.font = `bold ${11 * DPR}px monospace`
      ctx.fillText('Horizon des particules', cx + 6 * DPR, cy - horizonRPx + 14 * DPR)
      // Position CSS (pas device-pixel) du bouton "i" superposé, cf. state
      // horizonLabelPos — le canvas est en pixels physiques (pixelWidth =
      // renderWidth * DPR), donc on repasse en CSS en divisant par DPR.
      setHorizonLabelPos({ x: (cx + 6 * DPR) / DPR, y: (cy - horizonRPx + 14 * DPR) / DPR })
    } else {
      setHorizonLabelPos(null)
    }
  }, [halfWidthMpc, gridStepMpc, cosmology, dilution, width, height])

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        inset: 0,
        overflow: 'hidden',
        background: '#05050a',
        touchAction: 'none',
      }}
    >
      {width > 0 && height > 0 && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: renderWidth,
            height: renderHeight,
            transform: 'translate(-50%, -50%)',
          }}
        >
          <DensityLayer
            style={DENSITY_STYLE}
            opacity={DENSITY_PRESENCE}
            halfWidthMpc={halfWidthMpc}
            width={pixelWidth}
            height={pixelHeight}
            onLoadProgress={(loaded, total) => setLoadProgress({ loaded, total })}
          />
          <RealGalaxiesLayer
            style={DENSITY_STYLE}
            opacity={DENSITY_PRESENCE}
            halfWidthMpc={halfWidthMpc}
            width={pixelWidth}
            height={pixelHeight}
          />
          <canvas
            ref={gridCanvasRef}
            width={Math.round(pixelWidth)}
            height={Math.round(pixelHeight)}
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
          />

          {/* Bouton "i" superposé au label "Horizon des particules", positionné
              dynamiquement pour suivre le cercle qui grandit avec le temps. */}
          {horizonLabelPos && (
            <button
              onClick={() => setHorizonInfoOpen(true)}
              aria-label="En savoir plus sur l'horizon des particules"
              style={{
                position: 'absolute',
                left: horizonLabelPos.x + 140,
                top: horizonLabelPos.y - 15,
                width: 16,
                height: 16,
                borderRadius: 9,
                background: 'rgba(90,169,230,0.18)',
                border: '1px solid #5aa9e6',
                color: '#5aa9e6',
                fontSize: 10,
                fontStyle: 'italic',
                fontFamily: 'Georgia, serif',
                lineHeight: '14px',
                padding: 0,
                cursor: 'pointer',
              }}
            >
              i
            </button>
          )}
        </div>
      )}

      {/* Indicateur de chargement discret — n'empêche jamais la navigation */}
      {loadProgress.loaded < loadProgress.total && (
        <div
          style={{
            position: 'absolute',
            bottom: 'max(8px, env(safe-area-inset-bottom))',
            right: 'max(8px, env(safe-area-inset-right))',
            fontSize: 10,
            fontFamily: 'monospace',
            color: 'rgba(255,255,255,0.45)',
            background: 'rgba(10,10,16,0.5)',
            padding: '3px 7px',
            borderRadius: 5,
            pointerEvents: 'none',
          }}
        >
          Chargement… {loadProgress.loaded}/{loadProgress.total}
        </div>
      )}

      {/* Titre + bouton "à propos" */}
      <div
        style={{
          position: 'absolute',
          top: 'max(14px, env(safe-area-inset-top))',
          left: 'max(14px, env(safe-area-inset-left))',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <div
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: 16,
            fontWeight: 600,
            letterSpacing: '0.03em',
            color: '#eee',
            textShadow: '0 1px 4px rgba(0,0,0,0.8)',
            pointerEvents: 'none',
          }}
        >
          L'Heure de s'enivrer
        </div>
        <button
          onClick={() => setAboutOpen(true)}
          aria-label="À propos de ce projet"
          style={{
            width: 18,
            height: 18,
            borderRadius: 10,
            background: 'rgba(30,30,40,0.55)',
            border: '1px solid rgba(255,255,255,0.35)',
            color: '#ddd',
            fontSize: 11,
            fontStyle: 'italic',
            fontFamily: 'Georgia, serif',
            lineHeight: '16px',
            padding: 0,
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          i
        </button>
      </div>

      {/* Curseur de zoom, vertical, sur le bord droit — s'étire sur toute la hauteur disponible */}
      <div
        style={{
          position: 'absolute',
          top: 'calc(max(14px, env(safe-area-inset-top)) + 30px)',
          right: 'max(4px, env(safe-area-inset-right))',
          fontSize: 9,
          fontFamily: 'system-ui, sans-serif',
          color: 'rgba(255,255,255,0.5)',
          textAlign: 'center',
          width: 48,
          lineHeight: 1.3,
          pointerEvents: 'none',
        }}
      >
        <div style={{ fontSize: 13 }}>🌌</div>
        95 Gal
      </div>
      <div
        ref={zoomSliderRef}
        style={{
          position: 'absolute',
          top: 'calc(max(14px, env(safe-area-inset-top)) + 68px)',
          bottom: 'calc(max(14px, env(safe-area-inset-bottom)) + 78px)',
          right: 'max(6px, env(safe-area-inset-right))',
          width: 40,
          touchAction: 'none',
        }}
      >
        {zoomSliderSize.height > 0 && (
          <input
            type="range"
            min={Math.log10(MIN_HALF_WIDTH_MPC)}
            max={Math.log10(MAX_HALF_WIDTH_MPC)}
            step={0.002}
            value={logHalfWidth}
            onChange={(e) => setLogHalfWidth(Number(e.target.value))}
            style={{
              position: 'absolute',
              // L'input est horizontal puis pivoté de 90° : sa largeur AVANT
              // rotation doit correspondre à la hauteur RÉELLE du conteneur
              // (mesurée via ResizeObserver), pas à sa largeur (40px) — d'où
              // la mesure dynamique plutôt qu'un simple "100%".
              width: zoomSliderSize.height,
              height: 32,
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%) rotate(90deg)',
              transformOrigin: 'center',
              margin: 0,
              touchAction: 'none',
            }}
          />
        )}
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: 'calc(max(14px, env(safe-area-inset-bottom)) + 62px)',
          right: 'max(4px, env(safe-area-inset-right))',
          fontSize: 9,
          fontFamily: 'system-ui, sans-serif',
          color: 'rgba(255,255,255,0.5)',
          textAlign: 'center',
          width: 48,
          lineHeight: 1.3,
          pointerEvents: 'none',
        }}
      >
        <div style={{ fontSize: 13 }}>🌠</div>
        Galaxie
      </div>

      {/* Curseur de temps, horizontal, en bas (au-dessus des zones de geste système) */}
      <div
        style={{
          position: 'absolute',
          left: 16,
          right: 56,
          bottom: 'calc(max(14px, env(safe-area-inset-bottom)) + 24px)',
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 9,
          fontFamily: 'system-ui, sans-serif',
          color: 'rgba(255,255,255,0.5)',
          pointerEvents: 'none',
        }}
      >
        <span>⏳ Big Bang</span>
        <span>Aujourd'hui ☉</span>
      </div>
      <div
        style={{
          position: 'absolute',
          left: 16,
          right: 56,
          bottom: 'calc(max(14px, env(safe-area-inset-bottom)) + 6px)',
          touchAction: 'none',
        }}
      >
        <input
          type="range"
          min={tMin}
          max={tMax}
          step={(tMax - tMin) / 3000}
          value={tGyr}
          onChange={(e) => onTimeChange(Number(e.target.value))}
          style={{ width: '100%', touchAction: 'none' }}
        />
      </div>

      {aboutOpen && (
        <InfoModal title="L'Heure de s'enivrer" onClose={() => setAboutOpen(false)}>
          <p>
            Cette carte est une tentative — nécessairement imparfaite — de rendre sensible ce que les nombres,
            seuls, ne peuvent qu'énoncer : que la lumière qui vous atteint ce soir a parfois quitté sa source
            avant que la Terre n'existe ; que l'espace lui-même s'étire, silencieusement, entre chaque point que
            vous voyez ; que l'univers observable, ce halo de 95 milliards d'années-lumière qui vous entoure,
            n'est peut-être qu'une fraction infime de ce qui existe réellement au-delà de ce que la lumière a eu
            le temps de nous apporter.
          </p>
          <p>
            Zoomez, et vous traverserez en un geste ce que la lumière met 100&nbsp;000 ans à parcourir à travers
            notre seule galaxie. Remontez le temps, et vous verrez la matière se resserrer, s'échauffer, jusqu'au
            seuil où l'univers devient trop dense, trop jeune, pour qu'aucune lumière n'ait encore pu s'en
            échapper.
          </p>
          <p>
            Il n'y a pas de centre à cette carte — seulement le point d'où nous regardons, comme n'importe quel
            autre point de l'univers pourrait le faire. C'est peut-être la chose la plus vertigineuse : que ce
            sentiment d'immensité, cette sensation d'être minuscule et pourtant reliés à tout, quiconque, n'importe
            où dans le cosmos, pourrait l'éprouver exactement de la même façon en levant les yeux.
          </p>
        </InfoModal>
      )}

      {horizonInfoOpen && (
        <InfoModal title="Horizon des particules" onClose={() => setHorizonInfoOpen(false)}>
          <p>
            L'horizon des particules marque la limite de ce qu'il est physiquement possible d'observer aujourd'hui
            : la distance parcourue par la lumière la plus ancienne qui ait jamais pu nous atteindre, depuis les
            tout premiers instants de l'univers.
          </p>
          <p>
            Ce n'est pas un mur, ni une limite de l'univers lui-même — l'univers continue sans doute bien au-delà.
            C'est simplement la frontière de notre part visible : au-delà, la lumière existe peut-être, mais elle
            n'a pas encore eu le temps de nous parvenir.
          </p>
          <p>
            Ce cercle grandit avec le temps : plus l'univers vieillit, plus la lumière a eu de temps pour voyager,
            et plus notre part visible s'agrandit — sans jamais, bien sûr, atteindre la totalité de ce qui existe
            réellement.
          </p>
        </InfoModal>
      )}
    </div>
  )
}
