// L'Heure de s'enivrer — S7 : l'orogenèse alpine, vue d'avion.
// Relief : états FastScape (donnees/), interpolés ; fin = relief réel Copernicus GLO-90
// drapé de la mosaïque Sentinel-2 sans nuages (EOX). Unités : km au sol, m d'altitude, Ma.
import { creeCompteur } from "../../commun/compteur.js";

const EXAGERATION = 1.5;
const SOLEIL_AZ = 145, SOLEIL_EL = 34;           // degrés ; Soleil fixe, celui de la mosaïque (matin d'été, vers 10 h 30)
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
let climatGlace = () => null;      // part du froid tirée des glaciers PISM (120 derniers ka)
function froid(t) {
  const g = climatGlace(t); if (g !== null) return g;
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
  ["Belledonne", 45.172, 5.993, true], ["Chartreuse", 45.390, 5.790, true],
  ["Vercors", 45.000, 5.520, true], ["Grésivaudan", 45.355, 5.960, true],
  ["Grenoble", 45.188, 5.724, false], ["Mont-Blanc", 45.833, 6.865, false],
  ["Écrins", 44.922, 6.360, true], ["Chambéry", 45.566, 5.920, false],
];
const KM_LON = 111.32 * Math.cos(45.188 * Math.PI / 180), KM_LAT = 111.13;
const enKm = (lat, lon) => [(lon - 5.724) * KM_LON, (lat - 45.188) * KM_LAT];

// ------------------------------------------------------------------ données
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

// Bilinéaire aux centres de mailles, bords répétés (identique à chantiers/alpes/simuler.py, agrandir)
function agrandir(src, m, n) {
  const c0 = new Int32Array(n), c1 = new Int32Array(n), w = new Float32Array(n);
  for (let i = 0; i < n; i++) { const c = Math.min(Math.max((i + 0.5) * m / n - 0.5, 0), m - 1); c0[i] = Math.floor(c); c1[i] = Math.min(c0[i] + 1, m - 1); w[i] = c - c0[i]; }
  const out = new Float32Array(n * n);
  for (let i = 0; i < n; i++) { const a = c0[i] * m, b = c1[i] * m, wi = w[i];
    for (let j = 0; j < n; j++) out[i * n + j] = (src[a + c0[j]] * (1 - w[j]) + src[a + c1[j]] * w[j]) * (1 - wi) + (src[b + c0[j]] * (1 - w[j]) + src[b + c1[j]] * w[j]) * wi; }
  return out;
}

// Paquet v3 (voir meta.json « codage ») : images clés + résidus quantifiés.
class Film {
  constructor(meta) {
    this.m = meta; this.n = meta.n; this.T = meta.temps_Ma;
    this.qk = new Map(); this.res = new Map(); this.xk = new Map(); this.cles = [];
    this.qprev = null; this.xprev = null; this.kprev = -1; this.cache = new Map();
  }
  ajouter(b, cles) {
    const m = this.m, nn = this.n * this.n, nr = m.n_res * m.n_res, nx = m.n_x * m.n_x, nu = m.n_ue * m.n_ue;
    let o = 0;
    for (const k of cles) {
      const q = new Int16Array(nn), bas = b.subarray(o, o + nn), haut = b.subarray(o + nn, o + 2 * nn); o += 2 * nn;
      for (let j = 0; j < nn; j++) q[j] = (this.qprev ? this.qprev[j] : 0) + (((haut[j] << 8) | bas[j]) << 16 >> 16);
      for (let j = this.kprev + 1; j < k; j++) { this.res.set(j, new Int8Array(b.buffer.slice(b.byteOffset + o, b.byteOffset + o + nr))); o += nr; }
      const x = new Uint8Array(nx);
      for (let j = 0; j < nx; j++) x[j] = ((this.xprev ? this.xprev[j] : 0) + b[o + j]) & 255;
      o += nx;
      o += (this.kprev < 0 ? 1 : k - this.kprev) * 2 * nu;          // soulèvement et érosion : pour les contrôles
      this.qk.set(k, q); this.xk.set(k, x); this.cles.push(k);
      this.qprev = q; this.xprev = x; this.kprev = k;
    }
  }
  charge(k) { return k <= this.kprev; }
  encadre(k) { let a = 0; for (const c of this.cles) { if (c <= k) a = c; else return [a, c]; } return [a, a]; }
  relief(k) {                                    // Float32 n², mètres
    if (this.cache.has(k)) return this.cache.get(k);
    const n = this.n, nn = n * n, Q = this.m.q_cle_m, out = new Float32Array(nn);
    if (this.qk.has(k)) { const q = this.qk.get(k); for (let j = 0; j < nn; j++) out[j] = q[j] * Q; }
    else {
      const [a, b] = this.encadre(k), f = (k - a) / (b - a), qa = this.qk.get(a), qb = this.qk.get(b);
      const r = this.res.get(k), rf = new Float32Array(r.length);
      for (let j = 0; j < r.length; j++) rf[j] = r[j] * this.m.q_res_m;
      const up = agrandir(rf, this.m.n_res, n);
      for (let j = 0; j < nn; j++) out[j] = (qa[j] * (1 - f) + qb[j] * f) * Q + up[j];
    }
    if (this.cache.size > 6) this.cache.delete(this.cache.keys().next().value);
    this.cache.set(k, out); return out;
  }
  roches(k) {
    if (this.xk.has(k)) return this.xk.get(k);
    const [a, b] = this.encadre(k), f = (k - a) / (b - a), xa = this.xk.get(a), xb = this.xk.get(b), o = new Uint8Array(xa.length);
    for (let j = 0; j < o.length; j++) o[j] = Math.round(xa[j] * (1 - f) + xb[j] * f);
    return o;
  }
}

function cumul(b, nt, nn, o = 0) {               // différences mod 256 → tranches
  const out = new Uint8Array(nt * nn);
  for (let k = 0; k < nt; k++) for (let j = 0; j < nn; j++) out[k * nn + j] = ((k ? out[(k - 1) * nn + j] : 0) + b[o + k * nn + j]) & 255;
  return out;
}

// Détail du relief réel (1024², 200 m) au-delà de la grille du film : pentes (R, G), hauteur (B).
function texDetail(gl, d8, meta) {
  const n = 1024, pas = meta.taille_km * 1000 / n, px = new Uint8Array(n * n * 4);
  const d = k => d8[k] << 24 >> 24;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const k = i * n + j;
    const dx = 2 * (d(i * n + Math.min(j + 1, n - 1)) - d(i * n + Math.max(j - 1, 0))) / (2 * pas);
    const dn = 2 * (d(Math.max(i - 1, 0) * n + j) - d(Math.min(i + 1, n - 1) * n + j)) / (2 * pas);
    px[4 * k] = Math.max(0, Math.min(255, Math.round(128 + dx * 64)));
    px[4 * k + 1] = Math.max(0, Math.min(255, Math.round(128 + dn * 64)));
    px[4 * k + 2] = Math.max(0, Math.min(255, Math.round(128 + 2 * d(k) / 4)));
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

// Ombre portée d'un état : marche vers le Soleil fixe sur le relief affiché (exagéré), sur 256²
// (800 m) ; même calcul dans controles.py (ombre_python).
function ombreEtat(h512, nq, pasQ) {
  const n = Math.min(256, nq), f = nq / n;
  const az = SOLEIL_AZ * Math.PI / 180, el = SOLEIL_EL * Math.PI / 180, pasM = pasQ * f;
  const dx = Math.sin(az), dy = Math.cos(az), l = Math.hypot(dx, dy), tg = Math.tan(el);
  const h = new Float32Array(n * n);
  for (let i = 0; i < nq; i++) for (let j = 0; j < nq; j++) h[((i / f) | 0) * n + ((j / f) | 0)] += Math.max(h512[i * nq + j], 0) * EXAGERATION / (f * f);
  const di = [], dj = [], seuil = [];
  for (let s = 1; s <= PAS_OMBRE; s++) { dj.push(Math.floor(dx / l * s + 0.5)); di.push(Math.floor(-dy / l * s + 0.5)); seuil.push(s * pasM * tg); }
  const o = new Uint8Array(n * n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const hz = h[i * n + j]; let marge = 1e9;
    for (let s = 0; s < PAS_OMBRE; s++) {
      const ii = Math.min(Math.max(i + di[s], 0), n - 1), jj = Math.min(Math.max(j + dj[s], 0), n - 1);
      const m = (hz + seuil[s] - h[ii * n + jj]) / ((s + 1) * pasM); if (m < marge) marge = m;
    }
    const x = Math.min(Math.max((marge + 0.02) / 0.04, 0), 1);
    o[i * n + j] = Math.round(255 * x * x * (3 - 2 * x));
  }
  return o;
}

// ------------------------------------------------------------------ nuanceurs
const VS = `#version 300 es
precision highp float; precision highp int;
layout(location=0) in vec2 ij;
uniform sampler2D hA, hB, xA, xB, oA, oB, gA, gB, lit;
uniform float f, pasKm, tailleKm, exa, fg, wGlace;
uniform mat4 mvp;
out vec3 vPos; out vec2 vGrad; out float vH; out float vX; out vec2 vUV; out float vOmbre; out float vGlace;
float H(ivec2 c) { c = clamp(c, ivec2(0), textureSize(hA, 0) - 1); return mix(texelFetch(hA, c, 0).r, texelFetch(hB, c, 0).r, f); }
float G(vec2 uv) { float v = mix(texture(gA, uv).r, texture(gB, uv).r, fg); return v * v * 2500.0 * wGlace * step(5.5 / 255.0, v); }
float S(vec2 uv) { return texture(lit, uv).r + G(uv); }       // surface de la glace : lit lissé + épaisseur
void main() {
  ivec2 c = ivec2(ij);
  float h = H(c), pasM = pasKm * 1000.0;
  vGrad = vec2((H(c + ivec2(1, 0)) - H(c - ivec2(1, 0))) / (2.0 * pasM), (H(c - ivec2(0, 1)) - H(c + ivec2(0, 1))) / (2.0 * pasM));
  vUV = (ij + 0.5) / vec2(textureSize(hA, 0));
  vOmbre = mix(texture(oA, vUV).r, texture(oB, vUV).r, f);
  vX = mix(texture(xA, vUV).r, texture(xB, vUV).r, f);
  float z = max(h, 0.0);
  vGlace = mix(texture(gA, vUV).r, texture(gB, vUV).r, fg) * step(0.5, wGlace);
  if (vGlace >= 5.5 / 255.0) {
    float du = 1.0 / float(textureSize(hA, 0).x), s = S(vUV);
    if (s > h) {
      z = s;
      vGrad = vec2(S(vUV + vec2(du, 0.0)) - S(vUV - vec2(du, 0.0)), S(vUV - vec2(0.0, du)) - S(vUV + vec2(0.0, du))) / (2.0 * pasM);
      vOmbre = max(vOmbre, 0.8);
    }
  }
  float x = (ij.x + 0.5) * pasKm - tailleKm * 0.5, y = tailleKm * 0.5 - (ij.y + 0.5) * pasKm;
  vH = h;
  vPos = vec3(x, y, z * exa / 1000.0);
  gl_Position = mvp * vec4(vPos, 1.0);
}`;

const FS = `#version 300 es
precision highp float;
in vec3 vPos; in vec2 vGrad; in float vH; in float vX; in vec2 vUV; in float vOmbre; in float vGlace;
uniform sampler2D detail, regles, mosaique, vA, vB, mA, mB;
uniform float wDetail, wMosaique, climat, exa, tailleKm, modeRoches, xMaxLog, fg, vMax;
uniform int sortieMode;   // 0 image ; 1 couleur de surface ; 2 ombre ; 3 éclairé sans brume ; 4 glace ; 5 relief seul ; 6 moraines
uniform vec3 soleil, oeil, ciel;
out vec4 sortie;
float bruit(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(bruit(i), bruit(i+vec2(1,0)), f.x), mix(bruit(i+vec2(0,1)), bruit(i+vec2(1,1)), f.x), f.y); }
float fbm(vec2 p) { return 0.5 * vnoise(p) + 0.3 * vnoise(p * 2.03 + 7.1) + 0.2 * vnoise(p * 4.1 + 3.7); }
vec3 roche(float xm) {
  vec3 sed = vec3(0.85, 0.79, 0.64), calc = vec3(0.66, 0.64, 0.60), socle = vec3(0.63, 0.40, 0.48), meta = vec3(0.31, 0.50, 0.53);
  if (xm < 600.0) return mix(sed, calc, xm / 600.0);
  if (xm < 4000.0) return mix(calc, socle, (xm - 600.0) / 3400.0);
  return mix(socle, meta, clamp((xm - 4000.0) / 6000.0, 0.0, 1.0));
}
vec2 vitesse(vec2 uv) {                 // m/a, est et nord
  vec2 q = mix(texture(vA, uv).rg, texture(vB, uv).rg, fg) * 255.0 - 128.0;
  return sign(q) * (q / 127.0) * (q / 127.0) * vMax;
}
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
void main() {
  vec4 d = texture(detail, vUV);
  bool englace = vGlace >= 5.5 / 255.0;
  vec2 g = vGrad + (englace ? vec2(0.0) : (d.rg * 255.0 - 128.0) / 64.0 * wDetail);
  float h = vH + wDetail * (d.b * 255.0 - 128.0) * 4.0;
  vec3 n = normalize(vec3(-g * exa, 1.0));
  float penteDeg = degrees(atan(length(g)));
  float xm = exp(vX * xMaxLog) * 200.0 - 200.0;
  float bn = vnoise(vPos.xy * 2.5) * 0.6 + vnoise(vPos.xy * 9.0) * 0.4;
  vec3 c;
  if (h < 0.0) c = mix(vec3(0.20, 0.42, 0.45), vec3(0.05, 0.17, 0.27), clamp(-h / 120.0, 0.0, 1.0));
  else {
    float ha = h + climat + (bn - 0.5) * 120.0;
    c = texture(regles, vec2(clamp(ha / 5000.0, 0.0, 0.999), clamp(penteDeg / 64.0, 0.0, 0.999))).rgb;
    if (modeRoches > 0.5) c = roche(xm) * (0.9 + 0.1 * bn);
  }
  c = mix(c, texture(mosaique, vUV).rgb, wMosaique * (1.0 - modeRoches));
  float mor = mix(texture(mA, vUV).r, texture(mB, vUV).r, fg);
  if (englace && modeRoches < 0.5) {     // glace (Seguinot et al. 2018) : rendu repris de S8
    vec2 vit = vitesse(vUV); float s = length(vit);
    vec2 dir = s > 0.5 ? vit / s : vec2(1.0, 0.0);
    vec2 xy = vPos.xy, q = vec2(dot(xy, dir), dot(xy, vec2(-dir.y, dir.x)));
    float stries = fbm(vec2(q.x * 0.25, q.y * 3.2));                              // foliation le long du courant
    float crev = s > 80.0 ? smoothstep(0.62, 0.8, bruit(floor(vec2(q.x * 6.0, q.y * 0.9)))) * smoothstep(80.0, 400.0, s) : 0.0;
    vec3 gc = mix(vec3(0.74, 0.81, 0.88), vec3(0.93, 0.95, 0.97), stries);
    gc = mix(gc, vec3(0.34, 0.48, 0.62), 0.45 * crev);                                  // crevasses
    float debris = smoothstep(0.06, 0.4, mor) * (0.75 + 0.25 * bruit(floor(vec2(q.x * 1.5, q.y * 8.0))));
    gc = mix(gc, vec3(0.24, 0.22, 0.20), debris);                                     // moraines médianes
    float ep = vGlace * vGlace * 2500.0;
    gc = mix(gc, vec3(0.36, 0.34, 0.31), 0.7 * (1.0 - smoothstep(2.0, 40.0, ep)));      // moraines latérales
    c = gc;
  }
  if (sortieMode == 1) { sortie = vec4(c, 1.0); return; }
  if (sortieMode == 2) { sortie = vec4(vec3(vOmbre), 1.0); return; }
  if (sortieMode == 4) { sortie = vec4(vec3(englace ? 1.0 : 0.0), 1.0); return; }
  if (sortieMode == 6) { sortie = vec4(vec3(englace && mor >= 0.5 ? 1.0 : 0.0), 1.0); return; }
  float lum = max(dot(n, soleil), 0.0) * vOmbre;
  if (sortieMode == 5) { sortie = vec4(vec3(pow(0.18 * (1.9 * lum + 0.5 * (0.36 + 0.20 * n.z)), 1.0 / 2.2)), 1.0); return; }
  vec3 a = lin(c);
  vec3 col = a * (vec3(1.0, 0.95, 0.87) * 1.9 * lum + vec3(0.40, 0.50, 0.66) * (0.36 + 0.20 * n.z));
  if (englace) { vec3 v = normalize(oeil - vPos); col += 0.08 * pow(max(dot(reflect(-soleil, n), v), 0.0), 24.0); }
  if (h < 0.0 && !englace) {
    vec3 v = normalize(oeil - vPos); vec3 rf = reflect(-v, vec3(0, 0, 1));
    col += 0.25 * lin(ciel) * pow(1.0 - max(v.z, 0.0), 3.0) + 0.6 * pow(max(dot(rf, soleil), 0.0), 80.0) * vOmbre;
  }
  if (sortieMode == 3) { sortie = vec4(pow(col, vec3(1.0 / 2.2)), 1.0); return; }
  float dist = length(oeil - vPos);
  float brume = 0.55 * (1.0 - exp(-max(dist - 70.0, 0.0) / 380.0));
  float bord = max(abs(vPos.x), abs(vPos.y)) / (tailleKm * 0.5);
  brume = max(brume, smoothstep(0.88, 1.0, bord));
  col = mix(col, lin(ciel), brume);
  sortie = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
}`;

// Traînées : lignes qui suivent les vitesses de surface publiées (repris de S8)
const VS_T = `#version 300 es
layout(location=0) in vec4 p; uniform mat4 mvp; uniform float exa; out float a;
void main() { a = p.w; gl_Position = mvp * vec4(p.xy, p.z * exa / 1000.0 + 0.03, 1.0); }`;
const FS_T = `#version 300 es
precision mediump float; in float a; out vec4 o; void main() { o = vec4(vec3(0.97, 0.99, 1.0) * a * 0.55, a * 0.55); }`;
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
// ------------------------------------------------------------------ application
async function demarrer() {
  const canvas = document.getElementById("vue");
  const gl = canvas.getContext("webgl2", { antialias: true });
  const $ = id => document.getElementById(id);
  if (!gl) { $("charge").querySelector("p").textContent = "Ce navigateur ne sait pas dessiner le relief (WebGL2)."; return; }
  const jauge = p => { $("jauge").firstElementChild.style.width = (100 * p) + "%"; };

  // Première image : méta, premier paquet, règles de couleur (< 4 Mo). Le reste suit.
  const meta = await (await fetch("donnees/meta.json")).json();
  const n = meta.n, T = meta.temps_Ma, film = new Film(meta);
  const [b0, imRegles] = await Promise.all([decompresser("donnees/" + meta.paquets[0].fichier), image("donnees/regles.png")]);
  film.ajouter(b0, meta.paquets[0].cles);
  jauge(0.6);
  const xMaxLog = Math.log1p(meta.x_max_m / 200);

  const prog = programme(gl, VS, FS), progT = programme(gl, VS_T, FS_T);
  const U = {}; for (const nom of ["hA", "hB", "xA", "xB", "oA", "oB", "gA", "gB", "lit", "vA", "vB", "mA", "mB", "f", "fg", "wGlace", "vMax",
    "pasKm", "tailleKm", "exa", "mvp", "oeil", "detail", "regles", "mosaique", "wDetail", "wMosaique", "climat", "soleil", "ciel",
    "modeRoches", "xMaxLog", "sortieMode"]) U[nom] = gl.getUniformLocation(prog, nom);
  const UT = { mvp: gl.getUniformLocation(progT, "mvp"), exa: gl.getUniformLocation(progT, "exa") };

  const ij = new Float32Array(n * n * 2);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { ij[2 * (i * n + j)] = j; ij[2 * (i * n + j) + 1] = i; }
  const idx = new Uint32Array((n - 1) * (n - 1) * 6); let o = 0;
  for (let i = 0; i < n - 1; i++) for (let j = 0; j < n - 1; j++) { const a = i * n + j; idx.set([a, a + n, a + 1, a + 1, a + n, a + n + 1], o); o += 6; }
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, ij, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
  const vaoT = gl.createVertexArray(); gl.bindVertexArray(vaoT);
  const bufT = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bufT);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 0, 0);
  gl.bindVertexArray(null);

  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  const vide = () => texture(gl, 1, 1, new Uint8Array(4), false, true);
  const nouvelle = filtre => { const t = texture(gl, 1, 1, new Uint8Array(4), false, filtre); return t; };
  const texH = [nouvelle(false), nouvelle(false)], texX = [vide(), vide()], texO = [vide(), vide()];
  const texG = [vide(), vide()], texV = [vide(), vide()], texM = [vide(), vide()];
  let texLit = nouvelle(false), texD = vide(), texMos = vide();
  const charges = [-1, -1], ombres = new Map();
  const ombreDe = k => { if (!ombres.has(k)) { if (ombres.size > 8) ombres.delete(ombres.keys().next().value); ombres.set(k, ombreEtat(film.relief(k), n, meta.pas_m)); } return ombres.get(k); };
  function poser(slot, k) {
    if (charges[slot] === k) return; charges[slot] = k;
    gl.bindTexture(gl.TEXTURE_2D, texH[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, n, n, 0, gl.RED, gl.FLOAT, film.relief(k));
    gl.bindTexture(gl.TEXTURE_2D, texX[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, meta.n_x, meta.n_x, 0, gl.RED, gl.UNSIGNED_BYTE, film.roches(k));
    gl.bindTexture(gl.TEXTURE_2D, texO[slot]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, 256, 256, 0, gl.RED, gl.UNSIGNED_BYTE, ombreDe(k));
  }
  const texR = texture(gl, 0, 0, imRegles, false, true);

  const cam = { azimut: 248 * Math.PI / 180, hauteur: 37 * Math.PI / 180, distance: 118, cible: [6, 2, 0.8] };
  let t = -45, enLecture = false, allure = 1, roches = false, glisse = false, wMosPossible = 0, wDetPossible = 0;
  const CIEL = [0.72, 0.80, 0.90];
  const compteur = creeCompteur(document.body, { coin: "haut-droite", marge: 10 });

  function indice(tt) {
    let lo = 0, hi = T.length - 1;
    if (tt <= T[0]) return [0, 0];
    if (tt >= T[hi]) return [hi, 0];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= tt) lo = m; else hi = m; }
    return [lo, (tt - T[lo]) / (T[lo + 1] - T[lo])];
  }
  const tMaxCharge = () => T[film.kprev];
  function hauteurEn(xkm, ykm) {
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1);
    const j = Math.round((xkm + meta.taille_km / 2) / (meta.pas_m / 1000) - 0.5), i = Math.round((meta.taille_km / 2 - ykm) / (meta.pas_m / 1000) - 0.5);
    if (i < 0 || j < 0 || i >= n || j >= n || !film.charge(k2)) return 0;
    return (1 - f) * film.relief(k)[i * n + j] + f * film.relief(k2)[i * n + j];
  }
  let mvp = null, oeil = null;
  function matrices() {
    const asp = canvas.width / canvas.height, ch = Math.cos(cam.hauteur);
    oeil = [cam.cible[0] + cam.distance * ch * Math.sin(cam.azimut), cam.cible[1] + cam.distance * ch * Math.cos(cam.azimut), cam.cible[2] + cam.distance * Math.sin(cam.hauteur)];
    mvp = mul(perspective((asp < 1 ? 52 : 40) * Math.PI / 180, asp, 1, 900), regarder(oeil, cam.cible, [0, 0, 1]));
  }
  function projeter(p) {
    const m = mvp, x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
    if (w <= 0) return null;
    return [(x / w * 0.5 + 0.5) * canvas.clientWidth, (0.5 - y / w * 0.5) * canvas.clientHeight];
  }
  const lieux = LIEUX.map(([nom, la, lo, massif]) => {
    const e = document.createElement("div"); e.className = "lieu" + (massif ? " massif" : ""); e.textContent = nom;
    document.body.appendChild(e); return { e, km: enKm(la, lo) };
  });
  function taille() {
    const r = Math.min(window.devicePixelRatio || 1, 2), w = Math.round(canvas.clientWidth * r), h = Math.round(canvas.clientHeight * r);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  const wMos = tt => Math.min(Math.max((tt + 0.012) / 0.0115, 0), 1) * wMosPossible;

  // ---------------- glaciers (Seguinot et al. 2018), sur les 120 derniers ka
  let GL = null; const glPose = [-1, -1];
  function glaceEn(tt) {
    if (!GL) return { f: 0, w: 0, k: -1 };
    const ans = -tt * 1e6, A = GL.ages;
    if (ans > A[0] + 1e-6) return { f: 0, w: 0, k: -1 };
    let k = 0; while (k < A.length - 2 && A[k + 1] >= ans) k++;
    const fk = Math.min(Math.max((A[k] - ans) / (A[k] - A[k + 1]), 0), 1);
    for (const [slot, kk] of [[0, k], [1, k + 1]]) if (glPose[slot] !== kk) {
      glPose[slot] = kk;
      gl.bindTexture(gl.TEXTURE_2D, texG[slot]);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, GL.n, GL.n, 0, gl.RED, gl.UNSIGNED_BYTE, GL.e.subarray(kk * GL.n * GL.n, (kk + 1) * GL.n * GL.n));
      gl.bindTexture(gl.TEXTURE_2D, texV[slot]);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG8, GL.nv, GL.nv, 0, gl.RG, gl.UNSIGNED_BYTE, GL.vtex(kk));
      gl.bindTexture(gl.TEXTURE_2D, texM[slot]);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, GL.nm, GL.nm, 0, gl.RED, gl.UNSIGNED_BYTE, GL.mtex(kk));
    }
    return { f: fk, w: 1, k, aire: GL.aires[k] * (1 - fk) + GL.aires[k + 1] * fk };
  }
  climatGlace = tt => { const g = glaceEn(tt); return g.w ? 0.9 * g.aire / GL.aireMax : null; };
  // valeurs au point (km) pour les traînées
  function glaceAu(x, y, g) {
    const N = GL.n, c = (x + meta.taille_km / 2) / meta.taille_km * N - 0.5, r = (meta.taille_km / 2 - y) / meta.taille_km * N - 0.5;
    const j = Math.round(c), i = Math.round(r);
    if (i < 0 || j < 0 || i >= N || j >= N) return 0;
    const a = GL.e[g.k * N * N + i * N + j], b = GL.e[(g.k + 1) * N * N + i * N + j];
    return Math.min(a, b) >= 6 ? 1 : 0;             // glace aux deux tranches : la traînée ne sort jamais de la glace
  }
  function vitesseAu(x, y, g) {
    const N = GL.nv, c = Math.min(Math.max((x + meta.taille_km / 2) / meta.taille_km * N - 0.5, 0), N - 1.001), r = Math.min(Math.max((meta.taille_km / 2 - y) / meta.taille_km * N - 0.5, 0), N - 1.001);
    const j = c | 0, i = r | 0, u = c - j, v = r - i, out = [0, 0];
    for (const [kk, wk] of [[g.k, 1 - g.f], [g.k + 1, g.f]]) for (let comp = 0; comp < 2; comp++) {
      const A = comp ? GL.vn : GL.ve, o = kk * N * N, s = q => { const z = q << 24 >> 24; return Math.sign(z) * (z / 127) * (z / 127) * GL.vmax; };
      out[comp] += wk * ((s(A[o + i * N + j]) * (1 - u) + s(A[o + i * N + j + 1]) * u) * (1 - v) + (s(A[o + (i + 1) * N + j]) * (1 - u) + s(A[o + (i + 1) * N + j + 1]) * u) * v);
    }
    return out;
  }
  function surfaceAu(x, y) {
    const j = Math.round((x + meta.taille_km / 2) / (meta.pas_m / 1000) - 0.5), i = Math.round((meta.taille_km / 2 - y) / (meta.pas_m / 1000) - 0.5);
    if (i < 0 || j < 0 || i >= n || j >= n || !GL) return 0;
    const N = GL.n, gi = Math.min(i >> 1, N - 1), gj = Math.min(j >> 1, N - 1), g = glaceEn(t);
    const v = (GL.e[g.k * N * N + gi * N + gj] * (1 - g.f) + GL.e[(g.k + 1) * N * N + gi * N + gj] * g.f) / 255;
    return Math.max(GL.lit[i * n + j] + v * v * 2500, hauteurEn(x, y));
  }
  const L = 14, P_MAX = 1500, FLUX = 40;          // FLUX : années d'écoulement par seconde (ralenti)
  const tr = { x: new Float32Array(P_MAX), y: new Float32Array(P_MAX), vie: new Float32Array(P_MAX), duree: new Float32Array(P_MAX),
    vivant: new Uint8Array(P_MAX), hist: new Float32Array(P_MAX * L * 3), nh: new Uint8Array(P_MAX), depuis: 0 };
  let cellules = { k: -1, l: [] }, nbVoulu = 0;
  function naitre(p, g) {
    if (cellules.k !== g.k) { const l = [], N = GL.n, o = g.k * N * N, o2 = (g.k + 1) * N * N; for (let c = 0; c < N * N; c++) if (Math.min(GL.e[o + c], GL.e[o2 + c]) >= 6) l.push(c); cellules = { k: g.k, l }; }
    const l = cellules.l; if (!l.length) { tr.vivant[p] = 0; return; }
    const c = l[(Math.random() * l.length) | 0], N = GL.n, d = meta.taille_km / N;
    tr.x[p] = ((c % N) + Math.random()) * d - meta.taille_km / 2; tr.y[p] = meta.taille_km / 2 - (((c / N) | 0) + Math.random()) * d;
    tr.vie[p] = 0; tr.duree[p] = 1.8 + Math.random() * 2.2; tr.vivant[p] = 1; tr.nh[p] = 0;
  }
  function viderTrainees() { tr.vivant.fill(0); tr.nh.fill(0); }
  function avancerTrainees(dt) {
    const g = glaceEn(t);
    if (!g.w) { viderTrainees(); return; }
    nbVoulu = Math.min(P_MAX, Math.round(g.aire / 6));
    tr.depuis += dt; const noter = tr.depuis >= 0.05; if (noter) tr.depuis = 0;
    for (let p = 0; p < P_MAX; p++) {
      if (p >= nbVoulu) { tr.vivant[p] = 0; continue; }
      if (!tr.vivant[p]) naitre(p, g);
      if (!tr.vivant[p]) continue;
      const [ve, vn] = vitesseAu(tr.x[p], tr.y[p], g);
      tr.x[p] += ve * FLUX / 1000 * dt; tr.y[p] += vn * FLUX / 1000 * dt; tr.vie[p] += dt;
      if (tr.vie[p] > tr.duree[p] || !glaceAu(tr.x[p], tr.y[p], g) || Math.hypot(ve, vn) < 1) { naitre(p, g); continue; }
      if (noter || tr.nh[p] === 0) {
        const h = tr.hist, o = p * L * 3;
        h.copyWithin(o + 3, o, o + (L - 1) * 3);
        h[o] = tr.x[p]; h[o + 1] = tr.y[p]; h[o + 2] = surfaceAu(tr.x[p], tr.y[p]);
        tr.nh[p] = Math.min(tr.nh[p] + 1, L);
      }
    }
  }
  const segBuf = new Float32Array(P_MAX * (L - 1) * 8);
  function segmentsTrainees() {
    let m = 0;
    for (let p = 0; p < P_MAX; p++) {
      if (!tr.vivant[p]) continue;
      const o = p * L * 3, fade = Math.min(1, tr.vie[p] / 0.4, (tr.duree[p] - tr.vie[p]) / 0.4);
      for (let s = 0; s < tr.nh[p] - 1; s++) {
        const a = fade * (1 - s / (L - 1)), b = fade * (1 - (s + 1) / (L - 1)), h = tr.hist;
        segBuf.set([h[o + 3 * (s + 1)], h[o + 3 * (s + 1) + 1], h[o + 3 * (s + 1) + 2], b, h[o + 3 * s], h[o + 3 * s + 1], h[o + 3 * s + 2], a], m); m += 8;
      }
    }
    return m / 4;
  }

  // ---------------- dessin
  function rendre(matrice, mode, forcerMosaique) {
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1);
    poser(0, k); poser(1, film.charge(k2) ? k2 : k);
    const g = glaceEn(t);
    gl.useProgram(prog); gl.bindVertexArray(vao);
    [[texH[0], "hA"], [texH[1], "hB"], [texX[0], "xA"], [texX[1], "xB"], [texO[0], "oA"], [texO[1], "oB"], [texG[0], "gA"], [texG[1], "gB"],
     [texLit, "lit"], [texV[0], "vA"], [texV[1], "vB"], [texM[0], "mA"], [texM[1], "mB"], [texD, "detail"], [texR, "regles"], [texMos, "mosaique"]]
      .forEach(([tx, nom], i) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, tx); gl.uniform1i(U[nom], i); });
    gl.uniform1f(U.f, f); gl.uniform1f(U.fg, g.f); gl.uniform1f(U.wGlace, g.w); gl.uniform1f(U.vMax, GL ? GL.vmax : 1);
    gl.uniform1f(U.pasKm, meta.pas_m / 1000); gl.uniform1f(U.tailleKm, meta.taille_km); gl.uniform1f(U.exa, EXAGERATION);
    gl.uniformMatrix4fv(U.mvp, false, matrice); gl.uniform3fv(U.oeil, oeil || [0, 0, 500]);
    gl.uniform1f(U.wDetail, Math.min(Math.max((t + 2) / 1.99, 0), 1) * wDetPossible);
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
    if (GL && glaceEn(t).w && !roches) {
      const nv = segmentsTrainees();
      if (nv) {
        gl.useProgram(progT); gl.bindVertexArray(vaoT); gl.bindBuffer(gl.ARRAY_BUFFER, bufT);
        gl.bufferData(gl.ARRAY_BUFFER, segBuf.subarray(0, nv * 4), gl.DYNAMIC_DRAW);
        gl.uniformMatrix4fv(UT.mvp, false, mvp); gl.uniform1f(UT.exa, EXAGERATION);
        gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
        gl.drawArrays(gl.LINES, 0, nv);
        gl.depthMask(true); gl.disable(gl.BLEND); gl.bindVertexArray(null);
      }
    }
    const op = Math.min(Math.max((t + 1.0) / 0.8, 0), 1), rc = compteur.element.getBoundingClientRect();
    for (const l of lieux) {
      const z = Math.max(hauteurEn(...l.km), 0) * EXAGERATION / 1000 + 0.15, s = projeter([l.km[0], l.km[1], z]);
      let dedans = s && s[0] > 40 && s[0] < canvas.clientWidth - 40 && s[1] > 70 && s[1] < canvas.clientHeight - 150;
      if (dedans && s[0] > rc.left - 50 && s[1] < rc.bottom + 22) dedans = false;
      l.e.style.opacity = dedans ? op : 0;
      if (s) l.e.style.transform = `translate(${s[0]}px, ${s[1]}px) translate(-50%, -100%)`;
    }
    $("date").textContent = dateTexte(t);
    const r = recitDe(t); if ($("recit").textContent !== r) $("recit").textContent = r;
    if (!glisse) $("curseur").value = positionDe(t);
    if (coupeVue && GR) dessinerCoupe();
  }

  // Mesures (contrôles, planche) : vue du zénith
  let fbo = null, fboN = 0;
  function couleurs(tt, mode, forcerMosaique, N = 256) {
    const sauve = t; t = tt;
    if (!fbo || fboN !== N) {
      fboN = N; fbo = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      const c = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, c);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, N, N, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, c, 0);
      const z = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, z);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, N, N);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, z);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); gl.viewport(0, 0, N, N);
    gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const s = 2 / meta.taille_km;
    rendre([s, 0, 0, 0, 0, s, 0, 0, 0, 0, -0.1, 0, 0, 0, 0, 1], mode, forcerMosaique);
    const px = new Uint8Array(N * N * 4);
    gl.readPixels(0, 0, N, N, gl.RGBA, gl.UNSIGNED_BYTE, px);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    t = sauve;
    const out = new Array(N * N * 3);
    for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) for (let c = 0; c < 3; c++) out[(i * N + j) * 3 + c] = px[((N - 1 - i) * N + j) * 4 + c];
    return out;
  }

  // ---------------- coupe et grains suivis
  let GR = null, coupeVue = false, coupeInfo = { dessines: 0, vivants: 0 };
  const cv = $("coupe"), cx2 = cv.getContext("2d");
  const COULEURS_PROF = [[0, [216, 201, 163]], [600, [168, 164, 154]], [4000, [160, 101, 122]], [10000, [79, 127, 134]]];
  function couleurProf(d) {
    let i = 0; while (i < COULEURS_PROF.length - 2 && d > COULEURS_PROF[i + 1][0]) i++;
    const [a, ca] = COULEURS_PROF[i], [b, cb] = COULEURS_PROF[i + 1], u = Math.min(Math.max((d - a) / (b - a), 0), 1);
    return `rgb(${ca.map((v, k) => Math.round(v + (cb[k] - v) * u)).join(",")})`;
  }
  function dessinerCoupe() {
    const r = window.devicePixelRatio || 1, W = cv.clientWidth, Hc = cv.clientHeight;
    if (cv.width !== Math.round(W * r)) { cv.width = Math.round(W * r); cv.height = Math.round(Hc * r); }
    const c = cx2; c.setTransform(r, 0, 0, r, 0, 0); c.clearRect(0, 0, W, Hc);
    const S0 = -85, S1 = 85, Z0 = -20000, Z1 = 6000, mg = 8;
    const X = sk => mg + (sk - S0) / (S1 - S0) * (W - 2 * mg), Y = z => mg + (Z1 - z) / (Z1 - Z0) * (Hc - 2 * mg - 14);
    const [k, f] = indice(t), k2 = Math.min(k + 1, T.length - 1), ax = GR.axe, prof = [];
    for (let i = 0; i <= 200; i++) { const sk = S0 + (S1 - S0) * i / 200; prof.push([sk, hauteurEn(sk * ax[0], sk * ax[1])]); }
    c.fillStyle = "rgba(10,14,22,.80)"; c.fillRect(0, 0, W, Hc);
    const gr = c.createLinearGradient(0, Y(Z1), 0, Y(Z0)); gr.addColorStop(0, "#6b5a48"); gr.addColorStop(1, "#231a17");
    c.beginPath(); c.moveTo(X(S0), Y(Z0)); for (const [sk, z] of prof) c.lineTo(X(sk), Y(Math.max(z, -500))); c.lineTo(X(S1), Y(Z0)); c.closePath();
    c.fillStyle = gr; c.fill();
    c.beginPath(); for (const [sk, z] of prof) if (z < 0) { c.moveTo(X(sk), Y(0)); c.lineTo(X(sk), Y(z)); } c.strokeStyle = "rgba(60,120,150,.9)"; c.stroke();
    c.beginPath(); prof.forEach(([sk, z], i) => i ? c.lineTo(X(sk), Y(z)) : c.moveTo(X(sk), Y(z))); c.strokeStyle = "#f3efe6"; c.lineWidth = 1.2; c.stroke();
    let nd = 0, nv = 0; const G = GR.n, A = GR.etat(k), B = GR.etat(k2), fen = 4 * vitesseGeo(t);
    for (let g = 0; g < G; g++) {
      const tex = GR.tex[g];
      if (tex <= t) {
        if (t - tex < fen) { const sk = A.s[g] / 100; c.fillStyle = couleurProf(A.d[g] * 100); c.globalAlpha = 1 - (t - tex) / fen;
          c.beginPath(); c.arc(X(sk), Y(hauteurEn(sk * ax[0], sk * ax[1])), 3.2, 0, 7); c.fill(); c.globalAlpha = 1; }
        continue;
      }
      nv++;
      const sk = (A.s[g] * (1 - f) + B.s[g] * f) / 100, z = A.z[g] * (1 - f) + B.z[g] * f;
      if (sk < S0 || sk > S1) continue;
      c.fillStyle = couleurProf(Math.max(A.d[g], B.d[g]) * 100); c.fillRect(X(sk) - 1.2, Y(z) - 1.2, 2.4, 2.4); nd++;
    }
    coupeInfo = { dessines: nd, vivants: nv };
    c.fillStyle = "rgba(243,239,230,.75)"; c.font = "11px -apple-system, system-ui, sans-serif";
    c.fillText("ONO · Vercors", mg, Hc - 4); c.textAlign = "center"; c.fillText("Grenoble", X(0), Hc - 4);
    c.textAlign = "right"; c.fillText("Belledonne · ESE", W - mg, Hc - 4); c.textAlign = "left";
    c.fillText("−20 km", mg + 2, Y(Z0) - 3);
  }

  // ---------------- boucle
  let avant = performance.now(), tPrec = t, premiere = true;
  function imageSuivante(maintenant) {
    let dt = (maintenant - avant) / 1000; avant = maintenant;
    if (dt > 2) dt = 0;
    if (enLecture) { t = Math.min(t + vitesseGeo(t) * allure * dt, tMaxCharge()); if (t >= 0) { t = 0; arreter(); } }
    const v = dt > 0 ? (t - tPrec) * 1e6 / dt : 0;
    if (Math.abs(t - tPrec) > 0.002) viderTrainees();              // saut dans le temps : traînées neuves
    tPrec = t;
    compteur.vitesse(enLecture ? vitesseGeo(t) * allure * 1e6 : (glisse ? v : 0));
    if (GL) avancerTrainees(Math.min(dt, 0.1));
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
  $("roches").onclick = () => { roches = !roches; $("roches").style.background = roches ? "rgba(243,239,230,.25)" : ""; $("legende").classList.toggle("vue", roches || coupeVue); };
  $("bcoupe").onclick = () => { coupeVue = !coupeVue; document.body.classList.toggle("en-coupe", coupeVue);
    $("bcoupe").style.background = coupeVue ? "rgba(243,239,230,.25)" : ""; $("legende").classList.toggle("vue", coupeVue || roches); };
  $("infos").onclick = () => $("apropos").classList.add("ouvert");
  $("fermer").onclick = () => $("apropos").classList.remove("ouvert");
  for (const [tg, txt] of [[-45, "45 Ma"], [-30, "30"], [-15, "15"], [-5, "5"], [-2, "2 Ma"], [-1, "1"], [-0.3, "300 ka"], [0, "0"]]) {
    const e = document.createElement("div"); e.className = "graduation"; e.textContent = txt; e.style.left = (100 * positionDe(tg)) + "%"; $("frise").appendChild(e);
  }
  $("ralenti").style.left = (100 * positionDe(-2)) + "%";

  const pointeurs = new Map(); let ecart0 = 0, dist0 = 0;
  canvas.addEventListener("pointerdown", e => { canvas.setPointerCapture(e.pointerId); pointeurs.set(e.pointerId, [e.clientX, e.clientY]);
    if (pointeurs.size === 2) { const [a, b] = [...pointeurs.values()]; ecart0 = Math.hypot(a[0] - b[0], a[1] - b[1]); dist0 = cam.distance; } });
  canvas.addEventListener("pointermove", e => {
    if (!pointeurs.has(e.pointerId)) return;
    const [x0, y0] = pointeurs.get(e.pointerId); pointeurs.set(e.pointerId, [e.clientX, e.clientY]);
    if (pointeurs.size === 1) { cam.azimut -= (e.clientX - x0) * 0.006; cam.hauteur = Math.min(Math.max(cam.hauteur + (e.clientY - y0) * 0.004, 0.12), 1.35); }
    else if (pointeurs.size === 2) { const [a, b] = [...pointeurs.values()]; cam.distance = Math.min(Math.max(dist0 * ecart0 / Math.max(Math.hypot(a[0] - b[0], a[1] - b[1]), 1), 25), 330); }
  });
  const fin = e => pointeurs.delete(e.pointerId);
  canvas.addEventListener("pointerup", fin); canvas.addEventListener("pointercancel", fin);
  canvas.addEventListener("wheel", e => { e.preventDefault(); cam.distance = Math.min(Math.max(cam.distance * Math.exp(e.deltaY * 0.001), 25), 330); }, { passive: false });

  window.ALPES = {
    pret: false,
    aller: tt => { t = Math.min(Math.max(tt, -45), 0); tPrec = t; viderTrainees(); dessiner(); },
    lire: () => { enLecture = true; $("lecture").textContent = "❚❚"; },
    pause: arreter, vitesse: a => { allure = a; }, temps: () => t, camera: () => ({ ...cam }),
    regarder: o => { Object.assign(cam, o); dessiner(); },
    dessiner, couleurs, compteur, decalage: decalageClimat, positionDe, tempsDe, vitesseGeo,
    coupe: v => { if (v !== coupeVue) $("bcoupe").click(); dessiner(); return coupeInfo; },
    soleil: { azimut: SOLEIL_AZ, hauteur: SOLEIL_EL, pas: PAS_OMBRE, exageration: EXAGERATION },
    traineesDessinees: () => { const nv = segmentsTrainees(), out = []; for (let i = 0; i < nv; i += 2) { const a = segBuf.subarray(i * 4, i * 4 + 8);
      if (Math.min(a[3], a[7]) > 0.05 && (a[0] !== a[4] || a[1] !== a[5])) out.push(a[0], a[1], a[4], a[5]); } return out; },
    nombreTrainees: () => { let k = 0; for (let p = 0; p < P_MAX; p++) if (tr.vivant[p]) k++; return k; },
    avancerTrainees: s => { for (let i = 0; i < Math.round(s / 0.05); i++) avancerTrainees(0.05); },
  };
  dessiner();
  window.ALPES.poidsPremiereImage = performance.getEntriesByType("resource").reduce((s, e) => s + (e.encodedBodySize || e.transferSize || 0), 0);
  $("charge").style.opacity = 0; setTimeout(() => $("charge").remove(), 1300);
  requestAnimationFrame(imageSuivante);
  setTimeout(() => { if (t === -45 && !enLecture) lancer(); }, 1200);

  // ---------------- la suite arrive pendant qu'on regarde
  for (const p of meta.paquets.slice(1)) film.ajouter(await decompresser("donnees/" + p.fichier), p.cles);
  {
    const b = await decompresser("donnees/" + meta.grains.fichier), G = meta.grains.nombre, K = T.length, dv = new DataView(b.buffer, b.byteOffset);
    const tex = new Float32Array(G); for (let g = 0; g < G; g++) tex[g] = dv.getFloat32(4 * g, true);
    const plan16 = o => { const v = new Int16Array(K * G), lo = b.subarray(o, o + K * G), hi = b.subarray(o + K * G, o + 2 * K * G);
      for (let i = 0; i < K * G; i++) v[i] = (i >= G ? v[i - G] : 0) + (((hi[i] << 8) | lo[i]) << 16 >> 16); return v; };
    const S_ = plan16(8 * G), Z_ = plan16(8 * G + 2 * K * G), D_ = new Uint8Array(K * G), od = 8 * G + 4 * K * G;
    for (let i = 0; i < K * G; i++) D_[i] = ((i >= G ? D_[i - G] : 0) + b[od + i]) & 255;
    GR = { n: G, tex, axe: meta.grains.axe_est, etat: k => ({ s: S_.subarray(k * G, (k + 1) * G), z: Z_.subarray(k * G, (k + 1) * G), d: D_.subarray(k * G, (k + 1) * G) }) };
  }
  {
    const [mos, d8] = await Promise.all([image("donnees/mosaique_2048.jpg"), decompresser("donnees/" + meta.reel_detail)]);
    texMos = texture(gl, 0, 0, mos, true, true); texD = texDetail(gl, d8, meta); wMosPossible = 1; wDetPossible = 1;
  }
  {
    const gj = await (await fetch("donnees/glace.json")).json();
    const [ge, gv, gm] = await Promise.all(["glace", "vitesses", "moraines"].map(f => decompresser(`donnees/${f}.bin.gz`)));
    const nt = gj.ages_ans.length, N = gj.n, nv = gj.n_v, nm = gj.n_moraines;
    const e = cumul(ge, nt, N * N), ve = cumul(gv, nt, nv * nv), vn = cumul(gv, nt, nv * nv, nt * nv * nv);
    const mor = [];                                  // moraines : indices par tranche (mémoire légère)
    { let cur = new Uint8Array(nm * nm); for (let k = 0; k < nt; k++) { const o = k * nm * nm, l = [];
        for (let j = 0; j < nm * nm; j++) { cur[j] = (cur[j] + gm[o + j]) & 255; if (cur[j]) l.push(j); } mor.push(Uint32Array.from(l)); } }
    // lit lissé (≈ 2,8 km) du relief final : surface de glace sans les bosses du lit
    const fin_ = film.relief(T.length - 1), lit = new Float32Array(n * n), tmp = new Float32Array(n * n), R = 3;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { let s = 0, c = 0; for (let d = -R; d <= R; d++) { const jj = j + d; if (jj >= 0 && jj < n) { s += fin_[i * n + jj]; c++; } } tmp[i * n + j] = s / c; }
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { let s = 0, c = 0; for (let d = -R; d <= R; d++) { const ii = i + d; if (ii >= 0 && ii < n) { s += tmp[ii * n + j]; c++; } } lit[i * n + j] = s / c; }
    gl.bindTexture(gl.TEXTURE_2D, texLit); gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, n, n, 0, gl.RED, gl.FLOAT, lit);
    const vbuf = new Uint8Array(nv * nv * 2);
    GL = { ages: gj.ages_ans, n: N, nv, nm, e, ve, vn, lit, vmax: gj.v_max_m_a, aires: gj.aires_km2, aireMax: Math.max(...gj.aires_km2),
      vtex: k => { const o = k * nv * nv; for (let j = 0; j < nv * nv; j++) { vbuf[2 * j] = (ve[o + j] + 128) & 255; vbuf[2 * j + 1] = (vn[o + j] + 128) & 255; } return vbuf; },
      mtex: k => { const m = new Uint8Array(nm * nm); for (const j of mor[k]) m[j] = 255; return m; } };
  }
  window.ALPES.pret = true;
}

function dateTexte(t) {
  if (t > -0.0005) return "aujourd'hui";
  if (t > -1) { const a = Math.round(-t * 1000 / (t > -0.1 ? 1 : 10)) * (t > -0.1 ? 1 : 10); return "il y a " + a.toLocaleString("fr-FR") + " 000 ans"; }
  return "il y a " + (-t).toLocaleString("fr-FR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + " millions d'années";
}

demarrer().catch(e => { console.error(e); const p = document.querySelector("#charge p"); if (p) p.textContent = "Erreur : " + e.message; });
