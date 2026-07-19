import json, base64

meta = json.load(open('zoomtest_textures/meta.json'))
images_b64 = {}
for m in meta:
    with open(f"zoomtest_textures/{m['key']}.png", 'rb') as f:
        images_b64[m['key']] = base64.b64encode(f.read()).decode('ascii')

html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test de continuité de zoom (C..M)</title>
<style>
  html,body{margin:0;padding:0;background:#000;color:#ffd9a0;font-family:sans-serif;overflow:hidden;height:100%}
  #wrap{display:flex;flex-direction:column;height:100%}
  #canvasWrap{flex:1;position:relative;min-height:0}
  canvas{width:100%;height:100%;display:block;image-rendering:pixelated}
  #hud{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.6);padding:6px 10px;border-radius:6px;font-size:13px;pointer-events:none}
  #controls{padding:10px 14px 16px;background:#111}
  input[type=range]{width:100%}
  #label{font-size:14px;margin-bottom:4px}
  .note{font-size:11px;color:#a98;margin-top:6px}
</style>
</head>
<body>
<div id="wrap">
  <div id="canvasWrap">
    <canvas id="c"></canvas>
    <div id="hud"></div>
  </div>
  <div id="controls">
    <div id="label">Zoom continu (échelle log)</div>
    <input id="zoom" type="range" min="0" max="1000" value="500" step="1">
    <div class="note">Glisser lentement à travers chaque frontière de layer pour repérer un saut de structure ou de ton.</div>
  </div>
</div>
<script>
const META = __META__;
const IMAGES_B64 = __IMAGES__;

META.sort((a,b) => a.max_mpc - b.max_mpc);
const LOG_MIN = Math.log10(META[0].max_mpc);
const LOG_MAX = Math.log10(META[META.length-1].world_mpc);

const imgs = {};
let loaded = 0;
META.forEach(m => {
  const im = new Image();
  im.onload = () => { loaded++; if (loaded === META.length) render(); };
  im.src = 'data:image/png;base64,' + IMAGES_B64[m.key];
  imgs[m.key] = im;
});

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
function resize() {
  const r = canvas.parentElement.getBoundingClientRect();
  canvas.width = r.width; canvas.height = r.height;
  render();
}
window.addEventListener('resize', resize);

function findBracket(hw) {
  for (let i = 0; i < META.length - 1; i++) {
    if (hw >= META[i].max_mpc && hw < META[i+1].max_mpc) return i;
  }
  if (hw < META[0].max_mpc) return 0;
  return META.length - 2;
}

function drawLayerCropped(m, hw, alpha) {
  const im = imgs[m.key];
  if (!im.complete) return;
  const frac = Math.min(hw / m.world_mpc, 1);   // fraction de la texture visible
  const sw = im.width * frac, sh = im.height * frac;
  const sx = (im.width - sw) / 2, sy = (im.height - sh) / 2;
  ctx.globalAlpha = alpha;
  ctx.drawImage(im, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
  ctx.globalAlpha = 1;
}

function render() {
  if (!canvas.width) return;
  const slider = document.getElementById('zoom');
  const t01 = slider.value / slider.max;
  const logHw = LOG_MIN + t01 * (LOG_MAX - LOG_MIN);
  const hw = Math.pow(10, logHw);

  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const i = findBracket(hw);
  const a = META[i], b = META[i+1];
  const tt = (logHw - Math.log10(a.max_mpc)) / (Math.log10(b.max_mpc) - Math.log10(a.max_mpc));
  const ttClamped = Math.min(Math.max(tt, 0), 1);

  drawLayerCropped(a, hw, 1);
  drawLayerCropped(b, hw, ttClamped);

  const hud = document.getElementById('hud');
  hud.innerHTML = `hw = ${hw.toFixed(4)} Mpc<br>` +
    `${a.key} (${(1-ttClamped).toFixed(2)}) &harr; ${b.key} (${ttClamped.toFixed(2)})`;
}

document.getElementById('zoom').addEventListener('input', render);
resize();
</script>
</body>
</html>
"""

html = html.replace("__META__", json.dumps(meta))
html = html.replace("__IMAGES__", json.dumps(images_b64))

with open('../../app/public/zoom-continuity-test.html', 'w') as f:
    f.write(html)
print("écrit :", len(html)/1e6, "Mo")
