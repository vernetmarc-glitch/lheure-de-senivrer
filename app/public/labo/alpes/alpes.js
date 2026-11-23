// L'Heure de s'enivrer — S7 : l'orogenèse alpine, vue d'avion.
// Relief : états FastScape (donnees/), interpolés ; fin = relief réel Copernicus GLO-90
// drapé de la mosaïque Sentinel-2 sans nuages (EOX). Unités : km au sol, m d'altitude, Ma.
import { Compteur } from "./compteur.js";

const EXAGERATION = 1.5;
const SOLEIL_AZ = 205, SOLEIL_EL = 28;           // degrés ; Soleil fixe (milieu d'après-midi)
const SOLEIL = (() => { const az = SOLEIL_AZ * Math.PI / 180, el = SOLEIL_EL * Math.PI / 180;
  return [Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el)]; })();
const PAS_OMBRE = 40;                            // mailles parcourues vers le Soleil (32 km)

// ------------------------------------------------------------------ temps de lecture
// Vitesse (Ma par seconde de lecture, à l'allure ×1) : constante jusqu'à −8 Ma,
// puis proportionnelle à l'âge : très lente sur les deux derniers Ma (N23, D-41).
const V_MAX = 1.2, V_PENTE = 0.15, V_MIN = 0.003;
export function vitesseGeo(t) { return Math.min(V_MAX, V_PENTE * Math.abs(t) + V_MIN); }
const FRISE = (() => {
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

// Climat schématique (hypothèse signalée) : refroidissement cénozoïque, puis cycles
// glaciaires de 41 ka et de 100 ka. Décalage d'altitude « climatique » (m) appliqué aux
// règles de couleur : positif = plus froid (neige et roche plus bas).
function froid(t) {
  if (t < -2.6 || t > -0.012) return 0;
  const ka = t * 1000, montee = Math.min(1, (t + 2.6) / 0.6);
  let c;
  if (t < -1.0) c = 0.5 + 0.5 * Math.sin(2 * Math.PI * ka / 41);
  else { const ph = (((-ka) % 100) + 100) % 100 / 100; c = ph < 0.88 ? 1 - ph / 0.88 : (ph - 0.88) / 0.12; }
  return montee * (t < -1.0 ? 0.55 : 0.9) * c * c;
}
const CLIMAT = [[-45, -1300], [-34, -1200], [-15, -800], [-5, -400], [-2.6, -150], [-0.012, 0], [0, 0]];
export function decalageClimat(t) {
  let base = CLIMAT[0][1];
  for (let i = 1; i < CLIMAT.length; i++) if (t <= CLIMAT[i][0]) {
    const [a, va] = CLIMAT[i - 1], [b, vb] = CLIMAT[i]; base = va + (vb - va) * (t - a) / (b - a); break; }
  return base + 1200 * froid(t);
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
async function image(url) {
  const r = await fetch(url); if (!r.ok) throw new Error(url + " : " + r.status);
  return await createImageBitmap(await r.blob(), { imageOrientation: "none", premultiplyAlpha: "none", colorSpaceConversion: "none" });
}

// Paquet : voir sim/simuler.py (ecrire) et controles.py (decoder_paquet).
function decoderPaquet(b, k, meta, H, X) {
  const nn = meta.n * meta.n, nx = meta.n_x * meta.n_x;
  const bas = b.subarray(0, k * nn), haut = b.subarray(k * nn, 2 * k * nn);
  const prec = new Int32Array(nn), px = new Uint8Array(nx), o = 2 * k * nn;
  for (let i = 0; i < k; i++) {
    const q = new Uint16Array(nn), oi = i * nn;
    for (let j = 0; j < nn; j++) { prec[j] += ((haut[oi + j] << 8) | bas[oi + j]) << 16 >> 16; q[j] = prec[j]; }
    H.push(q);
    const x = new Uint8Array(nx);
    for (let j = 0; j < nx; j++) { px[j] = (px[j] + b[o + i * nx + j]) & 255; x[j] = px[j]; }
    X.push(x);
  }
}

// Détail du relief réel (1024², 200 m) au-delà de la grille du film (256²) :
// pentes du détail (R, G) et hauteur du détail (B).
function texDetail(gl, reel, meta) {
  const n = 1024, m = meta.n, f = n / m, pz = meta.h_pas_m, z0 = meta.h_zero_m;
  const h = new Float32Array(n * n);
  for (let i = 0; i < n * n; i++) h[i] = reel[i] * pz + z0;
  const g = new Float32Array(m * m);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) g[((i / f) | 0) * m + ((j / f) | 0)] += h[i * n + j] / (f * f);
  const lisse = (i, j) => {
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
    px[4 * k] = Math.max(0, Math.min(255, Math.round(128 + dx * 64)));
    px[4 * k + 1] = Math.max(0, Math.min(255, Math.round(128 + dn * 64)));
    px[4 * k + 2] = Math.max(0, Math.min(255, Math.round(128 + d[k] / 4)));
    px[4 * k + 3] = 255;
  }
  return texture(gl, n, n, px, true);
}
function texture(gl, w, h, src, mip, filtre = true) {
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  if (src instanceof Uint8Array) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, src);
  else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, src);
  if (mip) gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : filtre ? gl.LINEAR : gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filtre ? gl.LINEAR : gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return t;
}

// ------------------------------------------------------------------ shaders
const VS = `#version 300 es
precision highp float; precision highp int; precision highp usampler2D;
layout(location=0) in vec2 ij;
uniform usampler2D hA, hB; uniform sampler2D xA, xB;
uniform float f, pz, z0, pasKm, tailleKm, exa;
uniform mat4 mvp; uniform vec3 soleil;
out vec3 vPos; out vec2 vGrad; out float vH; out float vX; out vec2 vUV; out float vOmbre;
float H(ivec2 c) { c = clamp(c, ivec2(0), textureSize(hA, 0) - 1);
  return mix(float(texelFetch(hA, c, 0).r), float(texelFetch(hB, c, 0).r), f) * pz + z0; }
void main() {
  ivec2 c = ivec2(ij);
  float h = H(c), pasM = pasKm * 1000.0;
  vGrad = vec2((H(c + ivec2(1, 0)) - H(c - ivec2(1, 0))) / (2.0 * pasM),
               (H(c - ivec2(0, 1)) - H(c + ivec2(0, 1))) / (2.0 * pasM));
  // ombre portée : marche vers le Soleil sur le relief affiché (exagéré), maille par maille
  vec2 d = normalize(soleil.xy); float tg = soleil.z / length(soleil.xy);
  float hz = max(h, 0.0) * exa, marge = 1e9;
  for (int s = 1; s <= ${PAS_OMBRE}; s++) {
    vec2 p = ij + vec2(d.x, -d.y) * float(s);
    float hs = max(H(ivec2(floor(p + 0.5))), 0.0) * exa;
    marge = min(marge, (hz + float(s) * pasM * tg - hs) / (float(s) * pasM));
  }
  vOmbre = smoothstep(-0.02, 0.02, marge);
  vX = mix(texelFetch(xA, c / 2, 0).r, texelFetch(xB, c / 2, 0).r, f);
  float x = (ij.x + 0.5) * pasKm - tailleKm * 0.5, y = tailleKm * 0.5 - (ij.y + 0.5) * pasKm;
  vH = h; vUV = (ij + 0.5) / vec2(textureSize(hA, 0));
  vPos = vec3(x, y, max(h, 0.0) * exa / 1000.0);
  gl_Position = mvp * vec4(vPos, 1.0);
}`;

const FS = `#version 300 es
precision highp float;
in vec3 vPos; in vec2 vGrad; in float vH; in float vX; in vec2 vUV; in float vOmbre;
uniform sampler2D detail, regles, mosaique;
uniform float wDetail, wMosaique, climat, exa, tailleKm, modeRoches, xMaxLog;
uniform int sortieMode;            // 0 image ; 1 couleur de surface (mesure) ; 2 ombre (mesure)
uniform vec3 soleil, oeil, ciel;
out vec4 sortie;
float bruit(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(bruit(i), bruit(i+vec2(1,0)), f.x), mix(bruit(i+vec2(0,1)), bruit(i+vec2(1,1)), f.x), f.y); }
vec3 roche(float xm) {                 // machine à laver : couleur selon la profondeur d'origine (m)
  vec3 sed = vec3(0.85, 0.79, 0.64), calc = vec3(0.66, 0.64, 0.60), socle = vec3(0.63, 0.40, 0.48), meta = vec3(0.31, 0.50, 0.53);
  if (xm < 600.0) return mix(sed, calc, xm / 600.0);
  if (xm < 4000.0) return mix(calc, socle, (xm - 600.0) / 3400.0);
  return mix(socle, meta, clamp((xm - 4000.0) / 6000.0, 0.0, 1.0));
}
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
void main() {
  vec4 d = texture(detail, vUV);
  vec2 g = vGrad + (d.rg * 255.0 - 128.0) / 64.0 * wDetail;     // pente physique (sans exagération)
  float h = vH + wDetail * (d.b * 255.0 - 128.0) * 4.0;
  vec3 n = normalize(vec3(-g * exa, 1.0));
  float penteDeg = degrees(atan(length(g)));
  float xm = exp(vX * xMaxLog) * 200.0 - 200.0;
  float bn = vnoise(vPos.xy * 2.5) * 0.6 + vnoise(vPos.xy * 9.0) * 0.4;
  vec3 c;                                                         // couleur de surface, sRGB
  if (h < 0.0) {
    c = mix(vec3(0.16, 0.33, 0.40), vec3(0.06, 0.18, 0.28), clamp(-h / 150.0, 0.0, 1.0));
  } else {
    float ha = h + climat + (bn - 0.5) * 120.0;                   // altitude « climatique »
    c = texture(regles, vec2(clamp(ha / 5000.0, 0.0, 0.999), clamp(penteDeg / 64.0, 0.0, 0.999))).rgb;
    if (modeRoches > 0.5) c = roche(xm) * (0.9 + 0.1 * bn);
  }
  c = mix(c, texture(mosaique, vUV).rgb, wMosaique * (1.0 - modeRoches));
  if (sortieMode == 1) { sortie = vec4(c, 1.0); return; }
  if (sortieMode == 2) { sortie = vec4(vec3(vOmbre), 1.0); return; }
  vec3 a = lin(c);
  float lum = max(dot(n, soleil), 0.0) * vOmbre;
  float ambiant = 0.36 + 0.20 * n.z;
  vec3 col = a * (vec3(1.0, 0.95, 0.86) * 1.55 * lum + vec3(0.42, 0.52, 0.68) * ambiant);
  if (h < 0.0) {
    vec3 v = normalize(oeil - vPos); vec3 rf = reflect(-v, vec3(0, 0, 1));
    col += 0.25 * lin(ciel) * pow(1.0 - max(v.z, 0.0), 3.0) + 0.6 * pow(max(dot(rf, soleil), 0.0), 80.0) * vOmbre;
  }
  float dist = length(oeil - vPos);
  float brume = 1.0 - exp(-dist / 260.0);
  float bord = max(abs(vPos.x), abs(vPos.y)) / (tailleKm * 0.5);
  brume = max(brume, smoothstep(0.88, 1.0, bord));
  col = mix(col, lin(ciel), brume * 0.8);
  sortie = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
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
  return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -pt(x, o), -pt(y, o), -pt(z, o), 1];
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
  const jauge = p => { $("jauge").firstElementChild.style.width = (100 * p) + "%"; };

  // Première image : méta, premier paquet, détail réel, règles, mosaïque (< 10 Mo)
  const meta = await (await fetch("donnees/meta.json")).json();
  const n = meta.n, T = meta.temps_Ma, H = [], X = [];
  const [b0, r1024, imRegles, imMos] = await Promise.all([
    decompresser("donnees/" + meta.paquets[0].fichier), decompresser("donnees/reel_1024.bin.gz"),
    image("donnees/regles.png"), image("donnees/mosaique_2048.jpg")]);
  decoderPaquet(b0, meta.paquets[0].nombre, meta, H, X);
  jauge(0.5);
  const xMaxLog = Math.log1p(meta.x_max_m / 200);

  const prog = programme(gl, VS, FS);
  const U = {}; for (const nom of ["hA", "hB", "xA", "xB", "f", "pz", "z0", "pasKm", "tailleKm", "exa", "mvp", "oeil",
    "detail", "regles", "mosaique", "wDetail", "wMosaique", "climat", "soleil", "ciel", "modeRoches", "xMaxLog", "sortieMode"])
    U[nom] = gl.getUniformLocation(prog, nom);

  const ij = new Float32Array(n * n * 2);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { ij[2 * (i * n + j)] = j; ij[2 * (i * n + j) + 1] = i; }
  const idx = new Uint32Array((n - 1) * (n - 1) * 6); let o = 0;
  for (let i = 0; i < n - 1; i++) for (let j = 0; j < n - 1; j++) {
    const a = i * n + j; idx.set([a, a + n, a + 1, a + 1, a + n, a + n + 1], o); o += 6;
  }
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, ij, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);

  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  const texH = [0, 1].map(() => texture(gl, 1, 1, new Uint8Array(4), false, false));
  const texX = [0, 1].map(() => texture(gl, 1, 1, new Uint8Array(4), false, true));
  const charges = [-1, -1];
  function poser(slot, k) {
    if (charges[slot] === k) return; charges[slot] = k;
    gl.bindTexture(gl.TEXTURE_2D, texH[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R16UI, n, n, 0, gl.RED_INTEGER, gl.UNSIGNED_SHORT, H[k]);
    gl.bindTexture(gl.TEXTURE_2D, texX[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, meta.n_x, meta.n_x, 0, gl.RED, gl.UNSIGNED_BYTE, X[k]);
  }
  const reel = new Uint16Array(r1024.buffer, r1024.byteOffset, r1024.byteLength / 2);
  const texD = texDetail(gl, reel, meta);
  const texR = texture(gl, 0, 0, imRegles, false, true);
  const texM = texture(gl, 0, 0, imMos, true, true);

  const cam = { azimut: 250 * Math.PI / 180, hauteur: 26 * Math.PI / 180, distance: 150, cible: [4, 4, 0.6] };
  let t = -45, enLecture = false, allure = 1, roches = false, glisse = false;
  const CIEL = [0.72, 0.80, 0.90];
  const compteur = new Compteur(document.body);

  function indice(tt) {
    let lo = 0, hi = T.length - 1;
    if (tt <= T[0]) return [0, 0];
    if (tt >= T[hi]) return [hi, 0];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= tt) lo = m; else hi = m; }
    return [lo, (tt - T[lo]) / (T[lo + 1] - T[lo])];
  }
  const tMaxCharge = () => T[Math.min(H.length, T.length) - 1];
  function hauteurEn(xkm, ykm) {
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1);
    const j = Math.round((xkm + meta.taille_km / 2) / (meta.pas_m / 1000) - 0.5);
    const i = Math.round((meta.taille_km / 2 - ykm) / (meta.pas_m / 1000) - 0.5);
    if (i < 0 || j < 0 || i >= n || j >= n || !H[k2]) return 0;
    return ((1 - f) * H[k][i * n + j] + f * H[k2][i * n + j]) * meta.h_pas_m + meta.h_zero_m;
  }
  let mvp = null, oeil = null;
  function matrices() {
    const asp = canvas.width / canvas.height, ch = Math.cos(cam.hauteur);
    oeil = [cam.cible[0] + cam.distance * ch * Math.sin(cam.azimut), cam.cible[1] + cam.distance * ch * Math.cos(cam.azimut),
      cam.cible[2] + cam.distance * Math.sin(cam.hauteur)];
    mvp = mul(perspective((asp < 1 ? 52 : 40) * Math.PI / 180, asp, 1, 900), regarder(oeil, cam.cible, [0, 0, 1]));
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
  const wMos = tt => Math.min(Math.max((tt + 0.012) / 0.0115, 0), 1);    // l'Holocène : la photographie

  function rendre(matrice, mode, forcerMosaique) {
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1);
    poser(0, k); poser(1, H[k2] ? k2 : k);
    gl.useProgram(prog); gl.bindVertexArray(vao);
    [[texH[0], "hA"], [texH[1], "hB"], [texX[0], "xA"], [texX[1], "xB"], [texD, "detail"], [texR, "regles"], [texM, "mosaique"]]
      .forEach(([tx, nom], i) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, tx); gl.uniform1i(U[nom], i); });
    gl.uniform1f(U.f, f); gl.uniform1f(U.pz, meta.h_pas_m); gl.uniform1f(U.z0, meta.h_zero_m);
    gl.uniform1f(U.pasKm, meta.pas_m / 1000); gl.uniform1f(U.tailleKm, meta.taille_km); gl.uniform1f(U.exa, EXAGERATION);
    gl.uniformMatrix4fv(U.mvp, false, matrice); gl.uniform3fv(U.oeil, oeil || [0, 0, 500]);
    gl.uniform1f(U.wDetail, Math.min(Math.max((t + 2) / 1.99, 0), 1));
    gl.uniform1f(U.wMosaique, forcerMosaique ?? wMos(t)); gl.uniform1f(U.climat, decalageClimat(t));
    gl.uniform3fv(U.soleil, SOLEIL); gl.uniform3fv(U.ciel, CIEL);
    gl.uniform1f(U.modeRoches, roches ? 1 : 0); gl.uniform1f(U.xMaxLog, xMaxLog); gl.uniform1i(U.sortieMode, mode);
    gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK); gl.frontFace(gl.CCW);
    gl.drawElements(gl.TRIANGLES, idx.length, gl.UNSIGNED_INT, 0);
  }

  function dessiner() {
    taille(); matrices();
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(...CIEL, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    rendre(mvp, 0);
    const op = Math.min(Math.max((t + 1.0) / 0.8, 0), 1);
    const rc = compteur.e.getBoundingClientRect();
    for (const l of lieux) {
      const z = Math.max(hauteurEn(...l.km), 0) * EXAGERATION / 1000 + 0.15;
      const s = projeter([l.km[0], l.km[1], z]);
      let dedans = s && s[0] > 40 && s[0] < canvas.clientWidth - 40 && s[1] > 70 && s[1] < canvas.clientHeight - 150;
      if (dedans && s[0] > rc.left - 50 && s[1] < rc.bottom + 22) dedans = false;   // jamais sous le compteur
      l.e.style.opacity = dedans ? op : 0;
      if (s) l.e.style.transform = `translate(${s[0]}px, ${s[1]}px) translate(-50%, -100%)`;
    }
    $("date").textContent = dateTexte(t);
    const r = recitDe(t); if ($("recit").textContent !== r) $("recit").textContent = r;
    if (!glisse) $("curseur").value = positionDe(t);
  }

  // Mesure (contrôles) : couleurs de surface ou ombre vues du zénith, sur la grille du film
  let fbo = null;
  function couleurs(tt, mode, forcerMosaique) {
    const sauve = t; t = tt;
    const N = n;
    if (!fbo) {
      fbo = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      const c = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, c);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, N, N, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, c, 0);
      const z = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, z);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, N, N);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, z);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); gl.viewport(0, 0, N, N);
    gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const s = 2 / meta.taille_km;          // vue du zénith, nord en haut ; profondeur = altitude
    rendre([s, 0, 0, 0, 0, s, 0, 0, 0, 0, -0.1, 0, 0, 0, 0, 1], mode, forcerMosaique);
    const px = new Uint8Array(N * N * 4);
    gl.readPixels(0, 0, N, N, gl.RGBA, gl.UNSIGNED_BYTE, px);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    t = sauve;
    const out = new Array(N * N * 3);      // lignes du nord au sud
    for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) for (let c = 0; c < 3; c++) out[(i * N + j) * 3 + c] = px[((N - 1 - i) * N + j) * 4 + c];
    return out;
  }

  // boucle
  let avant = performance.now(), tPrec = t;
  function imageSuivante(maintenant) {
    let dt = (maintenant - avant) / 1000; avant = maintenant;
    if (dt > 2) dt = 0;
    if (enLecture) {
      t = Math.min(t + vitesseGeo(t) * allure * dt, tMaxCharge());
      if (t >= 0) { t = 0; arreter(); }
    }
    // vitesse réelle du curseur (ans par seconde), lecture ou glissé
    const v = dt > 0 ? (t - tPrec) * 1e6 / dt : 0; tPrec = t;
    compteur.regler(enLecture ? vitesseGeo(t) * allure * 1e6 : (glisse ? v : 0), dt);
    dessiner();
    requestAnimationFrame(imageSuivante);
  }
  function lancer() { if (t >= 0) t = -45; enLecture = true; $("lecture").textContent = "❚❚"; }
  function arreter() { enLecture = false; $("lecture").textContent = "▶"; }

  $("lecture").onclick = () => enLecture ? arreter() : lancer();
  const curseur = $("curseur");
  curseur.addEventListener("input", () => { glisse = true; t = Math.min(tempsDe(+curseur.value), tMaxCharge()); });
  curseur.addEventListener("change", () => { glisse = false; });
  const ALLURES = [0.5, 1, 2, 4];
  $("allure").onclick = () => { allure = ALLURES[(ALLURES.indexOf(allure) + 1) % ALLURES.length]; $("allure").textContent = "×" + String(allure).replace(".", ","); };
  $("roches").onclick = () => { roches = !roches; $("roches").style.background = roches ? "rgba(243,239,230,.25)" : ""; $("legende").classList.toggle("vue", roches); };
  $("infos").onclick = () => $("apropos").classList.add("ouvert");
  $("fermer").onclick = () => $("apropos").classList.remove("ouvert");
  for (const [tg, txt] of [[-45, "45 Ma"], [-30, "30"], [-15, "15"], [-5, "5"], [-2, "2 Ma"], [-1, "1"], [-0.3, "300 ka"], [0, "0"]]) {
    const e = document.createElement("div"); e.className = "graduation"; e.textContent = txt;
    e.style.left = (100 * positionDe(tg)) + "%"; $("frise").appendChild(e);
  }
  $("ralenti").style.left = (100 * positionDe(-2)) + "%";

  // glisser au doigt (un doigt : tourner ; deux doigts : rapprocher)
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
    pret: false,
    aller: tt => { t = Math.min(Math.max(tt, -45), 0); tPrec = t; dessiner(); },
    lire: () => { enLecture = true; $("lecture").textContent = "❚❚"; },
    pause: arreter, vitesse: a => { allure = a; }, temps: () => t, camera: () => ({ ...cam }),
    dessiner, couleurs, compteur, positionDe, tempsDe, vitesseGeo,
    soleil: { azimut: SOLEIL_AZ, hauteur: SOLEIL_EL, pas: PAS_OMBRE, exageration: EXAGERATION },
  };
  dessiner();
  $("charge").style.opacity = 0; setTimeout(() => $("charge").remove(), 1300);
  requestAnimationFrame(imageSuivante);
  setTimeout(() => { if (t === -45 && !enLecture) lancer(); }, 1200);

  // le reste du film arrive pendant qu'on regarde
  for (const p of meta.paquets.slice(1)) decoderPaquet(await decompresser("donnees/" + p.fichier), p.nombre, meta, H, X);
  window.ALPES.pret = true;
}

function dateTexte(t) {
  if (t > -0.0005) return "aujourd'hui";
  if (t > -1) { const a = Math.round(-t * 1000 / (t > -0.1 ? 1 : 10)) * (t > -0.1 ? 1 : 10); return "il y a " + a.toLocaleString("fr-FR") + " 000 ans"; }
  return "il y a " + (-t).toLocaleString("fr-FR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + " millions d'années";
}

demarrer().catch(e => { console.error(e); const p = document.querySelector("#charge p"); if (p) p.textContent = "Erreur : " + e.message; });
