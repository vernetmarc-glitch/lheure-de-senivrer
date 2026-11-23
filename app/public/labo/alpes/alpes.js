// L'Heure de s'enivrer — S7 : l'orogenèse alpine, vue d'avion.
// Relief : états FastScape (donnees/), interpolés ; fin = relief réel Copernicus GLO-90.
// Unités : km au sol, m pour les altitudes, Ma pour le temps.

const EXAGERATION = 1.5;
const SOLEIL = (() => { const az = 200 * Math.PI / 180, el = 36 * Math.PI / 180;
  return [Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el)]; })();

// ------------------------------------------------------------------ temps de lecture
// Vitesse (Ma par seconde de lecture, à l'allure ×1) : constante jusqu'à −8 Ma,
// puis proportionnelle à l'âge : très lente sur les deux derniers Ma (N23, D-41).
const V_MAX = 1.2, V_PENTE = 0.15, V_MIN = 0.003;
export function vitesseGeo(t) { return Math.min(V_MAX, V_PENTE * Math.abs(t) + V_MIN); }
const FRISE = (() => {          // durée de lecture cumulée D(t), table monotone
  const n = 6000, ts = new Float64Array(n + 1), ds = new Float64Array(n + 1);
  for (let i = 0; i <= n; i++) ts[i] = -45 + 45 * i / n;
  for (let i = 1; i <= n; i++) {
    const a = ts[i - 1], b = ts[i], m = (a + b) / 2;
    ds[i] = ds[i - 1] + (b - a) / 6 * (1 / vitesseGeo(a) + 4 / vitesseGeo(m) + 1 / vitesseGeo(b));
  }
  return { ts, ds, total: ds[n] };
})();
function positionDe(t) {
  const { ts, ds, total } = FRISE; const n = ts.length - 1;
  const f = Math.min(Math.max((t + 45) / 45 * n, 0), n); const i = Math.min(Math.floor(f), n - 1);
  return (ds[i] + (ds[i + 1] - ds[i]) * (f - i)) / total;
}
function tempsDe(p) {
  const { ts, ds, total } = FRISE; const d = Math.min(Math.max(p, 0), 1) * total;
  let lo = 0, hi = ts.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (ds[m] <= d) lo = m; else hi = m; }
  return ts[lo] + (ts[hi] - ts[lo]) * (d - ds[lo]) / Math.max(ds[hi] - ds[lo], 1e-12);
}

// ------------------------------------------------------------------ récit
const RECIT = [
  [-45, "La Téthys se referme. Ici, une plaine basse au bord de la mer ; à l'est, le futur cœur des Alpes sort à peine de l'eau."],
  [-36, "Collision. L'Europe plonge sous l'Adria. À l'est, la chaîne monte — et déjà les rivières la rongent."],
  [-28, "La montagne monte, l'eau la défait : les deux à la fois, aux mêmes endroits, sans cesse."],
  [-22, "Une mer peu profonde baigne le pied de la chaîne. Ses sables deviendront la molasse."],
  [-18, "Sous les calcaires, le vieux socle se soulève : Belledonne, les Écrins, le Mont-Blanc percent leur couverture."],
  [-12, "Les calcaires se froissent comme un tapis poussé contre un mur : la Chartreuse, le Vercors se dressent."],
  [-5, "La poussée s'éteint presque. Le relief, lui, continue de monter et de s'user."],
  [-2.6, "Le froid revient par vagues. Les glaciers vont et viennent, creusent le Grésivaudan, polissent les vallées."],
  [-0.6, "Le relief se fige en Alpes du Nord. Belledonne, la Chartreuse, le Vercors."],
  [-0.012, "Aujourd'hui. Un instant dans le mouvement : la montagne n'est pas un monument, c'est un équilibre."],
];
function recitDe(t) { let r = RECIT[0][1]; for (const [a, s] of RECIT) if (t >= a) r = s; return r; }

// Enneigement schématique : cycles de 41 ka puis de 100 ka (hypothèse signalée)
function froid(t) {
  if (t < -2.6) return 0;
  const ka = t * 1000;
  const montee = Math.min(1, (t + 2.6) / 0.6);
  let c;
  if (t < -1.0) c = 0.5 + 0.5 * Math.sin(2 * Math.PI * ka / 41);
  else { const ph = (((-ka) % 100) + 100) % 100 / 100; c = ph < 0.88 ? 1 - ph / 0.88 : (ph - 0.88) / 0.12; }
  const amp = t < -1.0 ? 0.55 : 0.9;
  const fin = t > -0.012 ? 0 : 1;              // aujourd'hui : interglaciaire
  return montee * amp * c * c * fin;
}
function ligneNeige(t) {
  const chaud = t < -34 ? 4300 : t < -15 ? 3900 : t < -3 ? 3500 : 3100;   // climat qui se refroidit
  return chaud - 1200 * froid(t);
}

// ------------------------------------------------------------------ lieux
const LIEUX = [
  ["Belledonne", 45.172, 5.993, true], ["Chartreuse", 45.300, 5.790, true],
  ["Vercors", 45.000, 5.520, true], ["Grésivaudan", 45.290, 5.905, true],
  ["Grenoble", 45.188, 5.724, false], ["Mont-Blanc", 45.833, 6.865, false],
  ["Écrins", 44.922, 6.360, true], ["Chambéry", 45.566, 5.920, false],
];
const KM_LON = 111.32 * Math.cos(45.188 * Math.PI / 180), KM_LAT = 111.13;
const enKm = (lat, lon) => [(lon - 5.724) * KM_LON, (lat - 45.188) * KM_LAT];

// ------------------------------------------------------------------ données
async function decompresser(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + " : " + r.status);
  const flux = r.body.pipeThrough(new DecompressionStream("gzip"));
  return new Uint8Array(await new Response(flux).arrayBuffer());
}

async function charger(progres) {
  const meta = await (await fetch("donnees/meta.json")).json();
  const nn = meta.n * meta.n, H = [], X = [];
  const total = meta.paquets.length + 2; let fait = 0;
  for (const p of meta.paquets) {
    const b = await decompresser("donnees/" + p.fichier), k = p.nombre;
    const bas = b.subarray(0, k * nn), haut = b.subarray(k * nn, 2 * k * nn);
    let prec = new Int32Array(nn);
    for (let i = 0; i < k; i++) {
      const q = new Uint16Array(nn), o = i * nn;
      for (let j = 0; j < nn; j++) {
        const d = ((haut[o + j] << 8) | bas[o + j]) << 16 >> 16;   // int16 signé
        prec[j] += d; q[j] = prec[j];
      }
      H.push(q);
      X.push(b.slice(2 * k * nn + 2 * k * nn + i * nn, 2 * k * nn + 2 * k * nn + (i + 1) * nn));
    }
    progres(++fait / total);
  }
  const r1024 = await decompresser("donnees/reel_1024.bin.gz"); progres(++fait / total);
  const reel = new Uint16Array(r1024.buffer, r1024.byteOffset, r1024.byteLength / 2);
  progres(1);
  return { meta, H, X, reel };
}

// Détail du relief réel (1024², 200 m) au-delà de la grille du film (256²) :
// pentes du détail (R, G) et hauteur du détail (B), pour l'ombrage des derniers Ma.
function textureDetail(gl, reel, meta) {
  const n = 1024, m = meta.n, f = n / m, pz = meta.h_pas_m, z0 = meta.h_zero_m;
  const h = new Float32Array(n * n);
  for (let i = 0; i < n * n; i++) h[i] = reel[i] * pz + z0;
  const g = new Float32Array(m * m);          // moyenne par blocs = grille du film
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) g[((i / f) | 0) * m + ((j / f) | 0)] += h[i * n + j] / (f * f);
  const lisse = (i, j) => {                   // bilinéaire de la grille du film
    const y = Math.min(Math.max((i + 0.5) / f - 0.5, 0), m - 1.001), x = Math.min(Math.max((j + 0.5) / f - 0.5, 0), m - 1.001);
    const a = y | 0, b = x | 0, u = y - a, v = x - b;
    return (g[a * m + b] * (1 - v) + g[a * m + b + 1] * v) * (1 - u) + (g[(a + 1) * m + b] * (1 - v) + g[(a + 1) * m + b + 1] * v) * u;
  };
  const d = new Float32Array(n * n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) d[i * n + j] = h[i * n + j] - lisse(i, j);
  const px = new Uint8Array(n * n * 4), pas = meta.taille_km * 1000 / n;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const k = i * n + j;
    const dx = (d[i * n + Math.min(j + 1, n - 1)] - d[i * n + Math.max(j - 1, 0)]) / (2 * pas);
    const dn = (d[Math.max(i - 1, 0) * n + j] - d[Math.min(i + 1, n - 1) * n + j]) / (2 * pas);
    px[4 * k] = Math.max(0, Math.min(255, 128 + dx * 64));
    px[4 * k + 1] = Math.max(0, Math.min(255, 128 + dn * 64));
    px[4 * k + 2] = Math.max(0, Math.min(255, 128 + d[k] / 4));
    px[4 * k + 3] = 255;
  }
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, n, n, 0, gl.RGBA, gl.UNSIGNED_BYTE, px);
  gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return t;
}

// ------------------------------------------------------------------ shaders
const VS = `#version 300 es
precision highp float; precision highp usampler2D;
layout(location=0) in vec2 ij;
uniform usampler2D hA, hB; uniform sampler2D xA, xB;
uniform float f, pz, z0, pasKm, tailleKm, exa;
uniform mat4 mvp; uniform vec3 oeil;
out vec3 vPos; out vec3 vNorm; out float vH; out float vX; out vec2 vUV;
float H(ivec2 c) { c = clamp(c, ivec2(0), ivec2(textureSize(hA, 0) - 1));
  return mix(float(texelFetch(hA, c, 0).r), float(texelFetch(hB, c, 0).r), f) * pz + z0; }
void main() {
  ivec2 c = ivec2(ij);
  float h = H(c);
  float hx = (H(c + ivec2(1, 0)) - H(c - ivec2(1, 0))) / (2.0 * pasKm * 1000.0);
  float hn = (H(c - ivec2(0, 1)) - H(c + ivec2(0, 1))) / (2.0 * pasKm * 1000.0);
  vNorm = normalize(vec3(-hx * exa, -hn * exa, 1.0));
  vX = mix(texelFetch(xA, c, 0).r, texelFetch(xB, c, 0).r, f);
  float x = (ij.x + 0.5) * pasKm - tailleKm * 0.5, y = tailleKm * 0.5 - (ij.y + 0.5) * pasKm;
  vH = h; vUV = (ij + 0.5) / vec2(textureSize(hA, 0));
  vPos = vec3(x, y, max(h, 0.0) * exa / 1000.0);
  gl_Position = mvp * vec4(vPos, 1.0);
}`;

const FS = `#version 300 es
precision highp float;
in vec3 vPos; in vec3 vNorm; in float vH; in float vX; in vec2 vUV;
uniform sampler2D detail; uniform float wDetail, neige, exa, tailleKm, modeRoches, xMaxLog;
uniform vec3 soleil, oeil, ciel;
out vec4 sortie;
float bruit(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(bruit(i), bruit(i+vec2(1,0)), f.x), mix(bruit(i+vec2(0,1)), bruit(i+vec2(1,1)), f.x), f.y); }
vec3 roche(float xm) {                 // couleur selon la profondeur d'origine (m)
  vec3 sed = vec3(0.85, 0.79, 0.64), calc = vec3(0.66, 0.64, 0.60), socle = vec3(0.63, 0.40, 0.48), meta = vec3(0.31, 0.50, 0.53);
  if (xm < 600.0) return mix(sed, calc, xm / 600.0);
  if (xm < 4000.0) return mix(calc, socle, (xm - 600.0) / 3400.0);
  return mix(socle, meta, clamp((xm - 4000.0) / 6000.0, 0.0, 1.0));
}
void main() {
  vec4 d = texture(detail, vUV);
  vec2 g = (d.rg * 255.0 - 128.0) / 64.0 * wDetail;
  float h = vH + wDetail * (d.b * 255.0 - 128.0) * 4.0;
  vec3 n = normalize(vNorm + vec3(-g.x * exa, -g.y * exa, 0.0));
  float pente = 1.0 - n.z;                       // 0 plat … 1 vertical
  float xm = exp(vX * xMaxLog) * 200.0 - 200.0;  // profondeur d'origine (m)
  float bn = vnoise(vPos.xy * 3.0) * 0.6 + vnoise(vPos.xy * 11.0) * 0.4;
  vec3 c;
  if (h < 0.0) {
    c = mix(vec3(0.10, 0.27, 0.36), vec3(0.03, 0.12, 0.22), clamp(-h / 150.0, 0.0, 1.0));
  } else {
    vec3 champ = mix(vec3(0.55, 0.58, 0.36), vec3(0.42, 0.50, 0.28), bn);
    vec3 foret = mix(vec3(0.16, 0.27, 0.15), vec3(0.11, 0.21, 0.13), bn);
    vec3 prairie = mix(vec3(0.46, 0.50, 0.31), vec3(0.52, 0.49, 0.36), bn);
    vec3 r = roche(xm) * (0.82 + 0.25 * bn);
    float lim = 1700.0 + 250.0 * bn;               // limite de la forêt
    c = mix(champ, foret, smoothstep(0.03, 0.12, pente + 0.08 * bn) * (1.0 - smoothstep(lim, lim + 250.0, h)));
    c = mix(c, foret, smoothstep(500.0, 900.0, h) * (1.0 - smoothstep(lim, lim + 250.0, h)));
    c = mix(c, prairie, smoothstep(lim, lim + 250.0, h));
    c = mix(c, r, smoothstep(lim + 450.0, lim + 900.0, h));
    c = mix(c, r, smoothstep(0.35, 0.55, pente));  // falaises
    float sn = smoothstep(neige - 150.0, neige + 150.0, h + 300.0 * bn) * (1.0 - smoothstep(0.45, 0.62, pente));
    c = mix(c, vec3(0.95, 0.96, 0.98), sn);
    if (modeRoches > 0.5) c = roche(xm) * (0.9 + 0.1 * bn);
  }
  float lum = max(dot(n, soleil), 0.0);
  float ambiant = 0.30 + 0.22 * n.z;
  vec3 col = c * (vec3(1.0, 0.96, 0.88) * 1.05 * lum + vec3(0.55, 0.68, 0.90) * ambiant);
  if (h < 0.0) {                                   // reflet du ciel sur la mer
    vec3 v = normalize(oeil - vPos); vec3 rf = reflect(-v, vec3(0, 0, 1));
    col += 0.35 * ciel * pow(1.0 - max(v.z, 0.0), 3.0) + 0.5 * pow(max(dot(rf, soleil), 0.0), 60.0);
  }
  float dist = length(oeil - vPos);
  float brume = 1.0 - exp(-dist / 230.0);
  float bord = max(abs(vPos.x), abs(vPos.y)) / (tailleKm * 0.5);
  brume = max(brume, smoothstep(0.86, 1.0, bord));
  col = mix(col, ciel, brume * 0.85);
  sortie = vec4(pow(col, vec3(1.0 / 1.15)), 1.0);
}`;

function programme(gl, vs, fs) {
  const p = gl.createProgram();
  for (const [t, s] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]) {
    const sh = gl.createShader(t); gl.shaderSource(sh, s); gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh));
    gl.attachShader(p, sh);
  }
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  return p;
}

// ------------------------------------------------------------------ matrices
function perspective(fov, asp, pres, loin) {
  const f = 1 / Math.tan(fov / 2), nf = 1 / (pres - loin);
  return [f / asp, 0, 0, 0, 0, f, 0, 0, 0, 0, (loin + pres) * nf, -1, 0, 0, 2 * loin * pres * nf, 0];
}
function regarder(o, c, haut) {
  const z = norm([o[0] - c[0], o[1] - c[1], o[2] - c[2]]), x = norm(croix(haut, z)), y = croix(z, x);
  return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0,
    -pt(x, o), -pt(y, o), -pt(z, o), 1];
}
const pt = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const croix = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = a => { const l = Math.hypot(...a); return a.map(v => v / l); };
function mul(a, b) {
  const r = new Array(16).fill(0);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) for (let k = 0; k < 4; k++) r[j * 4 + i] += a[k * 4 + i] * b[j * 4 + k];
  return r;
}

// ------------------------------------------------------------------ application
async function demarrer() {
  const canvas = document.getElementById("vue");
  const gl = canvas.getContext("webgl2", { antialias: true });
  const $ = id => document.getElementById(id);
  if (!gl) { $("charge").querySelector("p").textContent = "Ce navigateur ne sait pas dessiner le relief (WebGL2)."; return; }

  const D = await charger(p => { $("jauge").firstElementChild.style.width = (100 * p) + "%"; });
  const { meta, H, X } = D, n = meta.n, T = meta.temps_Ma;
  const xMaxLog = Math.log1p(meta.x_max_m / 200);

  const prog = programme(gl, VS, FS);
  const U = {}; for (const nom of ["hA", "hB", "xA", "xB", "f", "pz", "z0", "pasKm", "tailleKm", "exa", "mvp", "oeil",
    "detail", "wDetail", "neige", "soleil", "ciel", "modeRoches", "xMaxLog"]) U[nom] = gl.getUniformLocation(prog, nom);

  // maillage
  const ij = new Float32Array(n * n * 2);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { ij[2 * (i * n + j)] = j; ij[2 * (i * n + j) + 1] = i; }
  const idx = new Uint32Array((n - 1) * (n - 1) * 6); let o = 0;
  for (let i = 0; i < n - 1; i++) for (let j = 0; j < n - 1; j++) {
    const a = i * n + j; idx.set([a, a + n, a + 1, a + 1, a + n, a + n + 1], o); o += 6;
  }
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb); gl.bufferData(gl.ARRAY_BUFFER, ij, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const ib = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);

  const texH = [gl.createTexture(), gl.createTexture()], texX = [gl.createTexture(), gl.createTexture()];
  for (const t of [...texH, ...texX]) {
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  }
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  let charges = [-1, -1];
  function poser(slot, k) {
    if (charges[slot] === k) return; charges[slot] = k;
    gl.bindTexture(gl.TEXTURE_2D, texH[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R16UI, n, n, 0, gl.RED_INTEGER, gl.UNSIGNED_SHORT, H[k]);
    gl.bindTexture(gl.TEXTURE_2D, texX[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, n, n, 0, gl.RED, gl.UNSIGNED_BYTE, X[k]);
  }
  const texD = textureDetail(gl, D.reel, meta);

  // état de la vue
  const cam = { azimut: 250 * Math.PI / 180, hauteur: 27 * Math.PI / 180, distance: 150, cible: [4, 4, 0.6] };
  let t = -45, enLecture = false, allure = 1, roches = false;
  const CIEL = [0.70, 0.78, 0.88];

  function indice(tt) {
    let lo = 0, hi = T.length - 1;
    if (tt <= T[0]) return [0, 0];
    if (tt >= T[hi]) return [hi, 0];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= tt) lo = m; else hi = m; }
    return [lo, (tt - T[lo]) / (T[lo + 1] - T[lo])];
  }
  function hauteurEn(xkm, ykm) {           // altitude (m) du film au point, pour les étiquettes
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1);
    const j = Math.round((xkm + meta.taille_km / 2) / (meta.pas_m / 1000) - 0.5);
    const i = Math.round((meta.taille_km / 2 - ykm) / (meta.pas_m / 1000) - 0.5);
    if (i < 0 || j < 0 || i >= n || j >= n) return 0;
    return ((1 - f) * H[k][i * n + j] + f * H[k2][i * n + j]) * meta.h_pas_m + meta.h_zero_m;
  }
  let mvp = null, oeil = null;
  function matrices() {
    const w = canvas.width, h = canvas.height, asp = w / h;
    const ch = Math.cos(cam.hauteur);
    oeil = [cam.cible[0] + cam.distance * ch * Math.sin(cam.azimut), cam.cible[1] + cam.distance * ch * Math.cos(cam.azimut),
      cam.cible[2] + cam.distance * Math.sin(cam.hauteur)];
    const fov = (asp < 1 ? 52 : 40) * Math.PI / 180;
    mvp = mul(perspective(fov, asp, 1, 900), regarder(oeil, cam.cible, [0, 0, 1]));
  }
  function projeter(p) {
    const m = mvp, x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
      w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
    if (w <= 0) return null;
    return [(x / w * 0.5 + 0.5) * canvas.clientWidth, (0.5 - y / w * 0.5) * canvas.clientHeight];
  }

  const lieux = LIEUX.map(([nom, la, lo, massif]) => {
    const e = document.createElement("div"); e.className = "lieu" + (massif ? " massif" : ""); e.textContent = nom;
    document.body.appendChild(e); return { e, km: enKm(la, lo) };
  });

  function taille() {
    const r = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * r), h = Math.round(canvas.clientHeight * r);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }

  function dessiner() {
    taille(); matrices();
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1);
    poser(0, k); poser(1, k2);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(...CIEL, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK); gl.frontFace(gl.CW);
    gl.useProgram(prog); gl.bindVertexArray(vao);
    const unites = [[texH[0], "hA"], [texH[1], "hB"], [texX[0], "xA"], [texX[1], "xB"], [texD, "detail"]];
    unites.forEach(([tx, nom], i) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, tx); gl.uniform1i(U[nom], i); });
    gl.uniform1f(U.f, f); gl.uniform1f(U.pz, meta.h_pas_m); gl.uniform1f(U.z0, meta.h_zero_m);
    gl.uniform1f(U.pasKm, meta.pas_m / 1000); gl.uniform1f(U.tailleKm, meta.taille_km); gl.uniform1f(U.exa, EXAGERATION);
    gl.uniformMatrix4fv(U.mvp, false, mvp); gl.uniform3fv(U.oeil, oeil);
    gl.uniform1f(U.wDetail, Math.min(Math.max((t + 2) / 1.99, 0), 1));
    gl.uniform1f(U.neige, ligneNeige(t)); gl.uniform3fv(U.soleil, SOLEIL); gl.uniform3fv(U.ciel, CIEL);
    gl.uniform1f(U.modeRoches, roches ? 1 : 0); gl.uniform1f(U.xMaxLog, xMaxLog);
    gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_INT, 0);

    // étiquettes : elles apparaissent quand le relief se fige (dernier million d'années)
    const op = Math.min(Math.max((t + 1.0) / 0.8, 0), 1);
    for (const l of lieux) {
      const z = Math.max(hauteurEn(...l.km), 0) * EXAGERATION / 1000 + 0.15;
      const s = projeter([l.km[0], l.km[1], z]);
      const dedans = s && s[0] > 10 && s[0] < canvas.clientWidth - 10 && s[1] > 60 && s[1] < canvas.clientHeight - 150;
      l.e.style.opacity = dedans ? op : 0;
      if (s) l.e.style.transform = `translate(${s[0]}px, ${s[1]}px) translate(-50%, -100%)`;
    }
    $("date").textContent = dateTexte(t);
    const r = recitDe(t); if ($("recit").textContent !== r) $("recit").textContent = r;
    if (!glisse) $("curseur").value = positionDe(t);
  }

  // boucle
  let avant = performance.now();
  function image(maintenant) {
    let dt = (maintenant - avant) / 1000; avant = maintenant;
    if (dt > 2) dt = 0;
    if (enLecture) {
      t += vitesseGeo(t) * allure * dt;
      if (t >= 0) { t = 0; arreter(); }
    }
    dessiner();
    requestAnimationFrame(image);
  }
  function lancer() { if (t >= 0) t = -45; enLecture = true; $("lecture").textContent = "❚❚"; }
  function arreter() { enLecture = false; $("lecture").textContent = "▶"; }

  // commandes
  $("lecture").onclick = () => enLecture ? arreter() : lancer();
  let glisse = false;
  const curseur = $("curseur");
  curseur.addEventListener("input", () => { glisse = true; t = tempsDe(+curseur.value); });
  curseur.addEventListener("change", () => { glisse = false; });
  curseur.addEventListener("pointerdown", e => e.stopPropagation());
  const ALLURES = [0.5, 1, 2, 4];
  $("allure").onclick = () => { allure = ALLURES[(ALLURES.indexOf(allure) + 1) % ALLURES.length]; $("allure").textContent = "×" + String(allure).replace(".", ","); };
  $("roches").onclick = () => { roches = !roches; $("roches").style.background = roches ? "rgba(243,239,230,.25)" : ""; $("legende").classList.toggle("vue", roches); };
  $("infos").onclick = () => $("apropos").classList.add("ouvert");
  $("fermer").onclick = () => $("apropos").classList.remove("ouvert");

  // graduations de la frise (non linéaire : le temps ralentit)
  for (const [tg, txt] of [[-45, "45 Ma"], [-30, "30"], [-15, "15"], [-5, "5"], [-2, "2 Ma"], [-1, "1"], [-0.3, "300 ka"], [0, "0"]]) {
    const e = document.createElement("div"); e.className = "graduation"; e.textContent = txt;
    e.style.left = (100 * positionDe(tg)) + "%"; $("frise").appendChild(e);
  }
  $("ralenti").style.left = (100 * positionDe(-2)) + "%";

  // glisser au doigt (un doigt : tourner, deux doigts : rapprocher)
  const pointeurs = new Map(); let ecart0 = 0, dist0 = 0;
  canvas.addEventListener("pointerdown", e => { canvas.setPointerCapture(e.pointerId); pointeurs.set(e.pointerId, [e.clientX, e.clientY]);
    if (pointeurs.size === 2) { const [a, b] = [...pointeurs.values()]; ecart0 = Math.hypot(a[0] - b[0], a[1] - b[1]); dist0 = cam.distance; } });
  canvas.addEventListener("pointermove", e => {
    if (!pointeurs.has(e.pointerId)) return;
    const [x0, y0] = pointeurs.get(e.pointerId); pointeurs.set(e.pointerId, [e.clientX, e.clientY]);
    if (pointeurs.size === 1) {
      cam.azimut -= (e.clientX - x0) * 0.006;
      cam.hauteur = Math.min(Math.max(cam.hauteur + (e.clientY - y0) * 0.004, 0.12), 1.35);
    } else if (pointeurs.size === 2) {
      const [a, b] = [...pointeurs.values()]; const ec = Math.hypot(a[0] - b[0], a[1] - b[1]);
      cam.distance = Math.min(Math.max(dist0 * ecart0 / Math.max(ec, 1), 40), 330);
    }
  });
  const fin = e => pointeurs.delete(e.pointerId);
  canvas.addEventListener("pointerup", fin); canvas.addEventListener("pointercancel", fin);
  canvas.addEventListener("wheel", e => { e.preventDefault(); cam.distance = Math.min(Math.max(cam.distance * Math.exp(e.deltaY * 0.001), 40), 330); }, { passive: false });

  window.ALPES = {
    pret: true,
    aller: tt => { t = Math.min(Math.max(tt, -45), 0); dessiner(); },
    lire: () => { enLecture = true; $("lecture").textContent = "❚❚"; },
    pause: arreter,
    vitesse: a => { allure = a; },
    temps: () => t,
    camera: () => ({ ...cam }),
    dessiner,
    positionDe, tempsDe, vitesseGeo,
  };
  dessiner();
  $("charge").style.opacity = 0; setTimeout(() => $("charge").remove(), 1300);
  requestAnimationFrame(image);
  setTimeout(() => { if (t === -45 && !enLecture) lancer(); }, 1500);
}

function dateTexte(t) {
  if (t > -0.0005) return "aujourd'hui";
  if (t > -1) return "il y a " + (Math.round(-t * 1000 / (t > -0.1 ? 1 : 10)) * (t > -0.1 ? 1 : 10)).toLocaleString("fr-FR") + " 000 ans";
  return "il y a " + (-t).toLocaleString("fr-FR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + " millions d'années";
}

demarrer().catch(e => { console.error(e); const p = document.querySelector("#charge p"); if (p) p.textContent = "Erreur : " + e.message; });
