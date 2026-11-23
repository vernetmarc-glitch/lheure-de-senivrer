// L'orogenèse géodynamique (S7b) : carte des Alpes faite des coupes calculées, et coupe à la demande.
import { creeCompteur } from "../../commun/compteur.js";

const $ = id => document.getElementById(id);
const q = new URLSearchParams(location.search);
const ALLURE = 1.5;            // millions d'années par seconde de lecture

const RECIT = [
  [-84, "Entre l'Europe et l'Adria, un océan étroit : la Téthys alpine. Au milieu, un haut-fond, le Briançonnais."],
  [-70, "L'Adria remonte vers le nord. Le plancher de l'océan plonge sous elle et disparaît, lentement, dans le manteau."],
  [-52, "La fosse avale l'océan jusqu'au bout. Le Briançonnais arrive au bord du gouffre."],
  [-42, "Les fragments se heurtent. Des écailles de roche s'empilent, glissent les unes sur les autres."],
  [-33, "L'océan s'est refermé. L'Europe s'enfonce à son tour : un continent descend à cent kilomètres, puis remonte."],
  [-24, "Une chaîne neuve se dresse ; la pluie l'attaque aussitôt. Ces montagnes-là n'existent plus."],
  [-12, "Le front avance vers l'Europe. Les reliefs se déplacent, s'usent, renaissent un peu plus loin."],
  [-4, "La chaîne s'use presque aussi vite qu'elle monte. Bientôt, le froid ; bientôt, les glaciers."],
];
const VILLES = [["Grenoble", 5.72, 45.19], ["Turin", 7.68, 45.07], ["Milan", 9.19, 45.46], ["Zurich", 8.54, 47.37], ["Nice", 7.27, 43.70], ["Lyon", 4.84, 45.76]];
const NOM_COURT = { "océan liguro-piémontais": "Téthys", "sédiments de la chaîne": "" };

async function gz(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + " : " + r.status);
  const s = r.body.pipeThrough(new DecompressionStream("gzip"));
  return new Uint8Array(await new Response(s).arrayBuffer());
}
const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));

const etat = { t: -84, lecture: false, coupe: false };
let meta, T, H, F, NX, NY, PAS, X0, Y0, coupe, couleursFrag, couleursLit;
const compteur = creeCompteur(document.body, { coin: "haut-droite", marge: 10 });

async function charger() {
  meta = await (await fetch("donnees/meta.json")).json();
  T = meta.temps_ma; const c = meta.carte;
  NX = c.nx; NY = c.ny; PAS = c.pas_km; X0 = c.x0_km; Y0 = c.y0_km;
  const b = await gz("donnees/" + c.fichier), n = NX * NY;
  H = new Int16Array(b.buffer, 0, n * T.length);
  F = new Uint8Array(b.buffer, 2 * n * T.length, n * T.length);
  const ic = Math.max(0, meta.coupes.findIndex(cp => cp.nom.startsWith("Grenoble")));
  const cp = meta.coupes[ic], bc = await gz("donnees/" + cp.fichier), k = T.length * cp.nz * cp.nx;
  coupe = { ...cp, mat: bc.subarray(0, k), topo: new Int16Array(bc.slice(k).buffer, 0, T.length * cp.nx) };
  couleursFrag = []; for (const f of meta.fragments) couleursFrag[f.id] = hex(f.couleur);
  couleursLit = []; for (const l of meta.lithologies) couleursLit[l.id] = hex(l.couleur);
  $("legende").innerHTML = meta.lithologies.map(l => `<span style="--c:${l.couleur}">${l.nom}</span>`).join("");
}

// ------------------------------------------------------------------ carte
const petit = document.createElement("canvas");
let img;
function indices(t) {
  const tt = Math.min(T[T.length - 1], Math.max(T[0], t));
  let k = 0; while (k < T.length - 2 && T[k + 1] <= tt) k++;
  const w = Math.min(1, Math.max(0, (tt - T[k]) / (T[k + 1] - T[k])));
  return [k, w];
}
function hauteurs(t) {
  const [k, w] = indices(t), n = NX * NY, o0 = k * n, o1 = (k + 1) * n, h = new Float32Array(n);
  for (let i = 0; i < n; i++) h[i] = H[o0 + i] * (1 - w) + H[o1 + i] * w;
  return [h, w < 0.5 ? k : k + 1];
}
function dessinerCarte() {
  const [h, kf] = hauteurs(etat.t), off = kf * NX * NY;
  if (!img) { petit.width = NX; petit.height = NY; img = petit.getContext("2d").createImageData(NX, NY); }
  const d = img.data, ex = 3 / (PAS * 1000);          // ombrage : soleil au nord-ouest, relief exagéré ×3
  const lx = -0.5, ly = 0.5, lz = 0.707;
  for (let i = 0; i < NY; i++) for (let j = 0; j < NX; j++) {
    const p = i * NX + j, z = h[p];
    const zx = (h[i * NX + Math.min(NX - 1, j + 1)] - h[i * NX + Math.max(0, j - 1)]) * 0.5 * ex;
    const zy = (h[Math.min(NY - 1, i + 1) * NX + j] - h[Math.max(0, i - 1) * NX + j]) * 0.5 * ex;
    const nl = Math.hypot(zx, zy, 1), om = Math.max(0, (-zx * lx - zy * ly + lz) / nl);
    const fc = couleursFrag[F[off + p]] || [120, 120, 120];
    let r, g, b;
    if (z < 0) {
      const u = Math.min(1, -z / 6000);
      r = 52 - 40 * u; g = 102 - 70 * u; b = 140 - 80 * u;
      r = 0.8 * r + 0.2 * fc[0] * (1 - u); g = 0.8 * g + 0.2 * fc[1] * (1 - u); b = 0.8 * b + 0.2 * fc[2] * (1 - u);
    } else {
      const u = Math.min(1, z / 4500), s = 0.75 + 0.55 * om;
      r = (fc[0] * (1 - 0.45 * u) + 235 * 0.45 * u) * s; g = (fc[1] * (1 - 0.45 * u) + 232 * 0.45 * u) * s; b = (fc[2] * (1 - 0.45 * u) + 226 * 0.45 * u) * s;
    }
    const q = ((NY - 1 - i) * NX + j) * 4;              // nord en haut
    d[q] = r; d[q + 1] = g; d[q + 2] = b; d[q + 3] = 255;
  }
  petit.getContext("2d").putImageData(img, 0, 0);
  const cv = $("carte"), W = cv.clientWidth, dpr = Math.min(2, devicePixelRatio || 1);
  cv.width = Math.round(W * dpr); cv.height = Math.round(W * NY / NX * dpr);
  cv.style.height = (W * NY / NX) + "px";
  const g = cv.getContext("2d");
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(petit, 0, 0, cv.width, cv.height);
  placerNoms(kf);
}
const versEcran = (x, y) => { const W = $("carte").clientWidth, s = W / (NX * PAS); return [(x - X0 + PAS / 2) * s, (Y0 + NY * PAS - PAS / 2 - y) * s]; };
const kmLocal = (lon, lat) => { const o = meta.carte.origine_lonlat; return [(lon - o[0]) * 111.32 * Math.cos(o[1] * Math.PI / 180), (lat - o[1]) * 110.57]; };
let noms = null;
function placerNoms(kf) {
  const cadre = $("cadre");
  if (!noms) {
    noms = {};
    for (const f of meta.fragments) { const e = document.createElement("div"); e.className = "lieu frag"; e.textContent = NOM_COURT[f.nom] ?? f.nom; cadre.appendChild(e); noms[f.id] = e; }
    for (const [n, lo, la] of VILLES) { const e = document.createElement("div"); e.className = "lieu ville"; e.textContent = n; cadre.appendChild(e); const [x, y] = kmLocal(lo, la); const [a, b] = versEcran(x, y); e.style.left = a + "px"; e.style.top = b + "px"; }
  }
  const sx = [], sy = [], nn = [], off = kf * NX * NY;
  for (let i = 0; i < NY; i++) for (let j = 0; j < NX; j++) { const f = F[off + i * NX + j]; sx[f] = (sx[f] || 0) + j; sy[f] = (sy[f] || 0) + i; nn[f] = (nn[f] || 0) + 1; }
  for (const f of meta.fragments) {
    const e = noms[f.id], aire = (nn[f.id] || 0) * PAS * PAS;
    if (aire < 4000 || !e.textContent) { e.style.opacity = 0; continue; }
    // étiquette posée sur le pixel du fragment le plus proche de son centre de gravité
    const cj = sx[f.id] / nn[f.id], ci = sy[f.id] / nn[f.id];
    let best = 1e18, bi = 0, bj = 0;
    for (let i = 0; i < NY; i += 2) for (let j = 0; j < NX; j += 2) if (F[off + i * NX + j] === f.id) { const d = (i - ci) ** 2 + (j - cj) ** 2; if (d < best) { best = d; bi = i; bj = j; } }
    const [a, b] = versEcran(X0 + bj * PAS, Y0 + bi * PAS);
    e.style.left = a + "px"; e.style.top = b + "px"; e.style.opacity = 1;
  }
  const tr = $("trace");
  if (etat.coupe) {
    const [[xa, ya], [xb, yb]] = [coupe.trace[0], coupe.trace[1]], [a1, b1] = versEcran(xa, ya), [a2, b2] = versEcran(xb, yb);
    tr.innerHTML = `<line x1="${a1}" y1="${b1}" x2="${a2}" y2="${b2}" stroke="#fff" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.85"/>`;
  } else tr.innerHTML = "";
}

// ------------------------------------------------------------------ coupe
const FEN = [-350, 250], ZH = 6, ZB = -150, EXAG = 2;
let coupeInfo = { visible: false, couleurs_couches: [], echelle: "" };
function dessinerCoupe() {
  if (!etat.coupe) return;
  const [k, w] = indices(etat.t), kf = w < 0.5 ? k : k + 1, cp = coupe, nx = cp.nx, nz = cp.nz, p = cp.pas_km;
  const j0 = Math.max(0, Math.floor((cp.x_front_km + FEN[0]) / p)), j1 = Math.min(nx, Math.ceil((cp.x_front_km + FEN[1]) / p));
  const i0 = Math.max(0, Math.floor((cp.z_haut_km - ZH) / p)), i1 = Math.min(nz, Math.ceil((cp.z_haut_km - ZB) / p));
  const cv = $("coupe"), W = cv.clientWidth, dpr = Math.min(2, devicePixelRatio || 1);
  const kmpx = W / ((j1 - j0) * p), Hc = Math.round((i1 - i0) * p * kmpx * EXAG);
  cv.width = Math.round(W * dpr); cv.height = Math.round(Hc * dpr); cv.style.height = Hc + "px";
  const g = cv.getContext("2d"), pc = document.createElement("canvas");
  pc.width = j1 - j0; pc.height = i1 - i0;
  const im = pc.getContext("2d").createImageData(pc.width, pc.height), d = im.data, off = kf * nz * nx;
  const vus = new Set();
  for (let i = i0; i < i1; i++) for (let j = j0; j < j1; j++) {
    const c = cp.mat[off + i * nx + j], l = c % 8, q = ((i - i0) * pc.width + (j - j0)) * 4;
    const col = l === 0 || c === 255 ? [4, 5, 10] : couleursLit[l];
    if (l) vus.add(l);
    d[q] = col[0]; d[q + 1] = col[1]; d[q + 2] = col[2]; d[q + 3] = 255;
  }
  pc.getContext("2d").putImageData(im, 0, 0);
  g.imageSmoothingEnabled = false;
  g.drawImage(pc, 0, 0, cv.width, cv.height);
  // surface calculée
  g.strokeStyle = "#ffffffcc"; g.lineWidth = 1 * dpr; g.beginPath();
  for (let j = j0; j < j1; j++) {
    const z = cp.topo[kf * nx + j] / 1000, X = (j - j0 + 0.5) * p * kmpx * dpr, Y = (cp.z_haut_km - z - i0 * p) * kmpx * EXAG * dpr;
    j === j0 ? g.moveTo(X, Y) : g.lineTo(X, Y);
  }
  g.stroke();
  const ech = `${Math.round(FEN[1] - FEN[0])} km de large · ${Math.round(ZH - ZB)} km de haut · exagération verticale ×${EXAG} · coupe ${cp.nom}`;
  $("echelle").textContent = ech;
  coupeInfo = { visible: true, couleurs_couches: meta.lithologies.map(l => l.couleur), echelle: ech, presentes: [...vus] };
}

// ------------------------------------------------------------------ temps
function dateTexte(t) {
  if (t > -0.05) return "aujourd'hui";
  return (-t).toLocaleString("fr-FR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + " Ma";
}
function dessiner() {
  dessinerCarte(); dessinerCoupe();
  $("date").textContent = dateTexte(etat.t);
  let r = RECIT[0][1]; for (const [t0, s] of RECIT) if (etat.t >= t0) r = s;
  if ($("recit").textContent !== r) $("recit").textContent = r;
  $("barre").value = etat.t;
}
function aller(t) { etat.t = Math.min(0, Math.max(-84, +t)); dessiner(); }
let precedent = null;
function boucle(ts) {
  if (!etat.lecture) { precedent = null; return; }
  if (precedent !== null) {
    etat.t += ALLURE * (ts - precedent) / 1000;
    if (etat.t >= 0) { etat.t = 0; pause(); }
  }
  precedent = ts;
  dessiner();
  if (etat.lecture) requestAnimationFrame(boucle);
}
function lire() {
  if (etat.t >= 0) etat.t = -84;
  etat.lecture = true; $("blire").textContent = "❚❚"; compteur.vitesse(ALLURE * 1e6, 1);
  precedent = null; requestAnimationFrame(boucle);
}
function pause() { etat.lecture = false; $("blire").textContent = "▶"; compteur.vitesse(0, 0); }

$("blire").onclick = () => etat.lecture ? pause() : lire();
$("barre").oninput = e => { pause(); aller(e.target.value); };
$("bcoupe").onclick = () => {
  etat.coupe = !etat.coupe;
  $("panneau").classList.toggle("vu", etat.coupe); $("bcoupe").classList.toggle("actif", etat.coupe);
  if (!etat.coupe) coupeInfo = { ...coupeInfo, visible: false };
  dessiner();
};
addEventListener("resize", () => { noms && Object.values(noms).forEach(e => e.remove()); document.querySelectorAll(".ville").forEach(e => e.remove()); noms = null; dessiner(); });

function sonde(x, y) {
  const i = Math.round((y - Y0) / PAS), j = Math.round((x - X0) / PAS);
  const [h, kf] = hauteurs(etat.t);
  return { altitude_m: h[i * NX + j], fragment: F[kf * NX * NY + i * NX + j] };
}
function vue() { return { largeur_km: NX * PAS, hauteur_km: NY * PAS }; }

window.OROGENESE = { pret: false, aller, lire, pause, temps: () => etat.t, sonde, vue, compteur, coupeInfo: () => coupeInfo, dessiner };
charger().then(() => {
  aller(-84);
  window.OROGENESE.pret = true;
  if (!q.has("essai")) setTimeout(lire, 1200);
}).catch(e => { console.error(e); $("recit").textContent = "Les données n'ont pas pu être chargées."; });
