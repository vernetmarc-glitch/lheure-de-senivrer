import { useEffect, useRef } from 'react'
import { type DensityStyle } from './colormaps'
import { getLayerWeights } from './layerWeights'
import { processDensityField, getStyleParamsForLayer } from './densityStyle'

// Grille `A` -> `O` : quinze lignes géométriques de raison ×2,520, cuites et
// contrôlées par `scripts/harness/bake.py`. Elles REMPLACENT le découpage
// historique en douze paliers (`milkyway`, `localgroup`, `l1b`... `l5`), le
// 11/08/2026.
//
// Ce que le changement apporte, et pourquoi il valait le recâblage :
//  - les textures publiées sont celles qui passent les 392 contrôles du
//    harnais, alors que les anciennes n'en passaient aucun ;
//  - le pas est CONSTANT, donc une seule largeur de fondu ; l'ancien découpage
//    avait un pas de ×24 sur l'arête Groupe Local -> premier palier, masqué par
//    une largeur spéciale de 0,52 dex sur cette seule arête ;
//  - les galaxies nommées sont DANS la texture, à leur position et à leur
//    échelle, au lieu d'être surimprimées par un composant séparé.
//
// Chemin des textures : `essai-v4/data/v4/`, qui est la destination de
// publication du harnais (`PUBLISHED` dans bake.py). Ne pas recopier ailleurs :
// deux exemplaires divergeraient à la première cuisson.
import { LAYER_ORDER, LAYER_HALFWIDTH_MPC, LAYER_MARGIN, type LayerKey } from './layerWeights'

const TEXTURE_DIR = 'essai-v4/data/v4'

function marginFor(_key: string): number {
  // Marge UNIQUE : la grille est homogène, contrairement à l'ancien découpage
  // où `l5` avait sa propre marge de 2,4.
  return LAYER_MARGIN
}

interface ProceduralLayer {
  key: LayerKey
  maxMpc: number
}

// Du plus petit au plus grand demi-champ, comme l'ancienne liste : l'ordre de
// composition (grossier -> fin) en dépend.
const PROCEDURAL_LAYERS: ProceduralLayer[] = LAYER_ORDER.map((k) => ({
  key: k,
  maxMpc: LAYER_HALFWIDTH_MPC[k],
}))

interface DensityLayerProps {
  style: DensityStyle
  opacity: number
  halfWidthMpc: number
  width: number
  height: number
  onLoadProgress?: (loaded: number, total: number) => void
}

/**
 * Couche de densité multi-layers.
 *
 * Charge les textures procédurales (générées hors-ligne, avec héritage
 * hiérarchique entre échelles), les recolore selon le style choisi, puis les
 * mélange avec un fondu doux autour de chaque frontière d'échelle en
 * fonction du zoom courant. Le recadrage est RECTANGULAIRE (proportionnel à
 * width/height) pour remplir tout l'écran sans déformation, en coordonnées
 * flottantes (pas d'arrondi pixel) pour éviter tout jitter au zoom.
 *
 * Chargement PROGRESSIF et PRIORISÉ : le layer correspondant au zoom initial
 * est demandé en premier, et chaque texture est traitée/affichée dès son
 * arrivée (pas d'attente des 11 avant le premier rendu) — évite l'attente
 * initiale très longue observée avant cette version.
 */
export default function DensityLayer({ style, opacity, halfWidthMpc, width, height, onLoadProgress }: DensityLayerProps) {
  const outputCanvasRef = useRef<HTMLCanvasElement>(null)
  const grayDataRef = useRef<Record<string, ImageData>>({})
  const colorizedRef = useRef<Record<string, HTMLCanvasElement>>({})
  const loadedCountRef = useRef(0)

  // Chargement des textures sources, PRIORISÉ sur le layer du zoom initial.
  //
  // Point important (diagnostiqué le 7 juillet) : calculer un ORDRE de
  // priorité ne suffit pas si les 12 requêtes sont ensuite lancées
  // quasiment simultanément (assigner `.src` à 12 `Image` de suite dans la
  // même boucle synchrone) — le navigateur les traite alors comme un lot,
  // sans garantie que la texture prioritaire arrive en premier. Symptôme
  // observé : les 1-2 premières images très lentes (coût de connexion
  // TLS/DNS), puis les 10 autres qui arrivent d'un coup une fois la
  // connexion "chaude" — sans certitude que le layer actif soit dans ce
  // premier lot. Corrigé en chargeant la texture prioritaire SEULE
  // d'abord (avec un indice fetchPriority='high'), et en ne déclenchant
  // les 11 autres qu'une fois celle-ci arrivée.
  useEffect(() => {
    const ordered = [...PROCEDURAL_LAYERS].sort(
      (a, b) => Math.abs(Math.log(halfWidthMpc / a.maxMpc)) - Math.abs(Math.log(halfWidthMpc / b.maxMpc))
    )

    function loadOne(layer: ProceduralLayer, priority: 'high' | 'low') {
      const img = new Image()
      // fetchPriority n'est pas encore dans tous les typages DOM standards
      // selon la version de TS/lib — cast défensif, propriété bien
      // supportée par les moteurs de rendu principaux.
      ;(img as unknown as { fetchPriority: string }).fetchPriority = priority
      img.src = `${import.meta.env.BASE_URL}${TEXTURE_DIR}/density_${layer.key}.png`
      img.onload = () => {
        const off = document.createElement('canvas')
        off.width = img.naturalWidth
        off.height = img.naturalHeight
        const octx = off.getContext('2d')
        if (!octx) return
        octx.drawImage(img, 0, 0)
        grayDataRef.current[layer.key] = octx.getImageData(0, 0, off.width, off.height)
        recolorLayer(layer.key)
        draw()
        loadedCountRef.current += 1
        onLoadProgress?.(loadedCountRef.current, PROCEDURAL_LAYERS.length)
      }
      return img
    }

    const [first, ...rest] = ordered
    const firstImg = loadOne(first, 'high')
    const startRest = () => rest.forEach((layer) => loadOne(layer, 'low'))
    if (firstImg.complete) {
      // Déjà en cache navigateur (retour sur l'app) : pas besoin d'attendre.
      startRest()
    } else {
      firstImg.addEventListener('load', startRest, { once: true })
      firstImg.addEventListener('error', startRest, { once: true }) // ne pas bloquer le reste si la prioritaire échoue
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function recolorLayer(key: string) {
    const gray = grayDataRef.current[key]
    if (!gray) return

    // Traitement à la résolution NATIVE de la texture (pas de sous-
    // échantillonnage) : le recadrage se fait ensuite sur ce résultat, donc
    // toute perte de résolution ici se répercute directement sur le piqué
    // final à l'écran, en particulier aux niveaux de zoom qui n'utilisent
    // qu'une petite portion de la texture (agrandissement important).
    const n = gray.width
    const grayValues = new Float32Array(n * n)
    for (let i = 0; i < grayValues.length; i++) grayValues[i] = gray.data[i * 4] / 255

    const processed = processDensityField(grayValues, n, style, getStyleParamsForLayer(key))

    const canvas = document.createElement('canvas')
    canvas.width = n
    canvas.height = n
    canvas.getContext('2d')!.putImageData(processed, 0, 0)
    colorizedRef.current[key] = canvas
  }

  function recolorAll() {
    PROCEDURAL_LAYERS.forEach((layer) => recolorLayer(layer.key))
  }

  function draw() {
    const outCanvas = outputCanvasRef.current
    if (!outCanvas || width < 1 || height < 1) return
    const ctx = outCanvas.getContext('2d')
    if (!ctx) return

    const W = outCanvas.width
    const H = outCanvas.height
    ctx.clearRect(0, 0, W, H)

    const weights = getLayerWeights(halfWidthMpc)
    const shortSide = Math.min(W, H)
    // Demi-largeur physique (Mpc) couverte par chaque axe de l'écran — basée
    // sur le côté le plus court pour que "halfWidthMpc" garde son sens de
    // "zoom" habituel, l'autre axe s'étend proportionnellement.
    const halfWidthMpcX = (W / shortSide) * halfWidthMpc
    const halfWidthMpcY = (H / shortSide) * halfWidthMpc

    // Layer de REMPLISSAGE des bords (ajouté le 11/08/2026, exigence H9).
    //
    // Le défaut : quand le champ de vue dépasse la couverture d'une texture
    // (`overshoot > 1`), la destination est réduite à une boîte centrée. Le
    // pari d'origine — « le layer plus grossier, déjà visible en fondu à ce
    // moment, comble naturellement les bords » — n'est vrai QUE pendant le
    // fondu. Dès que le layer écrêté atteint la pleine opacité, le grossier
    // est sauté (`w < 0.003`) et il ne reste RIEN autour : un cadre noir.
    //
    // Et cela arrive bien plus tôt sur un écran large, parce que
    // `halfWidthMpcX` est multiplié par W/H : à 16:9 le débordement commence
    // ~1,8x plus bas qu'en portrait. D'où le symptôme signalé par Marc — le
    // nouveau layer « en petit sur fond noir » sur écran de PC.
    //
    // Le remplisseur est le layer le PLUS FIN qui couvre encore tout l'écran :
    // le saut de résolution au raccord est ainsi le plus petit possible.
    const covering = PROCEDURAL_LAYERS.filter(
      (l) =>
        Math.max(halfWidthMpcX, halfWidthMpcY) <= l.maxMpc * marginFor(l.key) &&
        colorizedRef.current[l.key]
    )
    const filler = covering.length ? covering[0] : null

    function drawFullScreen(layer: ProceduralLayer, alpha: number) {
      const source = colorizedRef.current[layer.key]
      if (!source || !ctx) return
      const n = source.width
      const texturePxPerMpc = n / (2 * layer.maxMpc * marginFor(layer.key))
      const cw = 2 * halfWidthMpcX * texturePxPerMpc
      const ch = 2 * halfWidthMpcY * texturePxPerMpc
      ctx.globalAlpha = alpha
      ctx.drawImage(source, (n - cw) / 2, (n - ch) / 2, cw, ch, 0, 0, W, H)
    }

    // Ordre du plus grand (coarse) au plus petit (fin) — cohérent avec la
    // construction emboîtée des textures (§4.4 du document d'architecture).
    for (let i = PROCEDURAL_LAYERS.length - 1; i >= 0; i--) {
      const layer = PROCEDURAL_LAYERS[i]
      const w = weights[layer.key]
      if (w < 0.003) continue
      const source = colorizedRef.current[layer.key]
      if (!source) continue

      const n = source.width // texture carrée (n x n)
      const texturePxPerMpc = n / (2 * layer.maxMpc * marginFor(layer.key))

      // Coordonnées FLOTTANTES (pas d'arrondi) : un arrondi au pixel près,
      // une fois agrandi à l'échelle de l'écran, provoquait un jitter très
      // visible aux niveaux de zoom où le recadrage source est petit.
      let cropW = 2 * halfWidthMpcX * texturePxPerMpc
      let cropH = 2 * halfWidthMpcY * texturePxPerMpc

      // Si le recadrage dépasserait la texture source (au-delà de la marge de
      // génération), on réduit LE RECTANGLE DE DESTINATION à l'écran plutôt
      // que le recadrage lui-même — sinon le facteur de compensation annule
      // exactement l'effet du zoom et l'image se fige (le layer arrête de
      // zoomer) tant que le clamp reste actif. En réduisant la destination,
      // le contenu continue de zoomer normalement sur une zone un peu plus
      // petite que l'écran ; l'anneau laissé libre est peint juste en dessous
      // par le layer de remplissage, à la MÊME opacité (H9).
      let destX = 0
      let destY = 0
      let destW = W
      let destH = H
      const overshoot = Math.max(cropW / n, cropH / n, 1)
      if (overshoot > 1) {
        cropW /= overshoot
        cropH /= overshoot
        destW = W / overshoot
        destH = H / overshoot
        destX = (W - destW) / 2
        destY = (H - destH) / 2

        // L'anneau seul, découpé en règle pair-impair : le centre n'est pas
        // repeint, donc le ton y reste exactement celui d'avant la correction.
        if (filler && filler.key !== layer.key) {
          ctx.save()
          ctx.beginPath()
          ctx.rect(0, 0, W, H)
          ctx.rect(destX, destY, destW, destH)
          ctx.clip('evenodd')
          drawFullScreen(filler, w)
          ctx.restore()
        }
      }
      const startX = (n - cropW) / 2
      const startY = (n - cropH) / 2

      ctx.globalAlpha = w
      ctx.drawImage(source, startX, startY, cropW, cropH, destX, destY, destW, destH)
    }
    ctx.globalAlpha = 1
  }

  // Recoloration complète quand le style change.
  useEffect(() => {
    recolorAll()
    draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [style])

  // Redessin (recadrage/fondu) quand le zoom ou la taille de l'écran changent.
  useEffect(() => {
    draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [halfWidthMpc, width, height])

  return (
    <canvas
      ref={outputCanvasRef}
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
