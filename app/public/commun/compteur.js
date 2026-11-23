// Compteur de vitesse du temps (N28) — composant commun à toutes les scènes.
//
//   import { creeCompteur } from "../../commun/compteur.js";
//   const c = creeCompteur(conteneur, { coin: "bas-droite" });
//   c.vitesse(ansParSeconde, sens);   // sens : 1 en avant, -1 à rebours, 0 arrêté
//   c.detruit();
//
// Cadran de voiture en SVG : aiguille sur une échelle logarithmique de 1 an à
// 10 milliards d'années par seconde (27° par décade, de -135° à +135° depuis la
// verticale), graduée 1 an · 100 ans · 10 000 ans · 1 Ma · 100 Ma · 10 Ga.
// Temps arrêté : l'aiguille tombe sur la butée (-146°). Temps remonté : la flèche de
// sens s'allume. Aiguille amortie (ressort, ζ = 0,78, ω₀ = 9 rad/s), animation coupée
// au repos. Le cadran ne capte aucun geste (pointer-events: none).
// Module ES natif, sans dépendance ; polices Cinzel et Jost servies avec le module.

const NS = "http://www.w3.org/2000/svg";
export const ANGLE_MIN = -135;   // 1 an par seconde
export const ANGLE_MAX = 135;    // 10 milliards d'années par seconde
export const ANGLE_BUTEE = -146; // temps arrêté
const DECADES = 10;
const GRADUATIONS = [
  [1, "1", " an"], [1e2, "100", " ans"], [1e4, "10 000", " ans"],
  [1e6, "1", " Ma"], [1e8, "100", " Ma"], [1e10, "10", " Ga"],
];

/** Angle (degrés, depuis la verticale, sens horaire) d'une vitesse en années par seconde. */
export function angleVitesse(ansParSeconde, sens = 1) {
  if (!(ansParSeconde > 0) || sens === 0) return ANGLE_BUTEE;
  const d = Math.min(DECADES, Math.max(0, Math.log10(ansParSeconde)));
  return ANGLE_MIN + (ANGLE_MAX - ANGLE_MIN) * d / DECADES;
}

const nf = new Intl.NumberFormat("fr-FR", { maximumSignificantDigits: 2 });
const deuxChiffres = x => { if (x <= 0) return 0; const p = Math.pow(10, Math.floor(Math.log10(x)) - 1); return Math.round(x / p) * p; };

/** Lecture en clair : « 10 000 ans par seconde », « 2,5 millions d'années par seconde ». */
export function lectureEnClair(ansParSeconde, sens = 1) {
  if (!(ansParSeconde > 0) || sens === 0) return "temps arrêté";
  const v = deuxChiffres(ansParSeconde);
  let t;
  if (v >= 1e9) { const n = deuxChiffres(v / 1e9); t = `${nf.format(n)} ${n >= 2 ? "milliards" : "milliard"} d'années`; }
  else if (v >= 1e6) { const n = deuxChiffres(v / 1e6); t = `${nf.format(n)} ${n >= 2 ? "millions" : "million"} d'années`; }
  else if (v >= 1) t = `${nf.format(v)} ${v >= 2 ? "ans" : "an"}`;
  else if (v * 12 >= 1) t = `${nf.format(deuxChiffres(v * 12))} mois`;
  else if (v * 365.25 >= 1) { const n = deuxChiffres(v * 365.25); t = `${nf.format(n)} ${n >= 2 ? "jours" : "jour"}`; }
  else { const n = deuxChiffres(v * 8766); t = `${nf.format(n)} ${n >= 2 ? "heures" : "heure"}`; }
  return `${t} par seconde`;
}

let stylePose = false;
function poseStyle() {
  if (stylePose || document.getElementById("compteur-temps-style")) { stylePose = true; return; }
  stylePose = true;
  const p = f => new URL(`./polices/${f}`, import.meta.url).href;
  const s = document.createElement("style");
  s.id = "compteur-temps-style";
  s.textContent = `
@font-face { font-family: "Cinzel"; font-weight: 500; font-display: swap; src: url("${p("cinzel-latin-500-normal.woff2")}") format("woff2"); }
@font-face { font-family: "Cinzel"; font-weight: 600; font-display: swap; src: url("${p("cinzel-latin-600-normal.woff2")}") format("woff2"); }
@font-face { font-family: "Jost"; font-weight: 400; font-display: swap; src: url("${p("jost-latin-400-normal.woff2")}") format("woff2"); }
@font-face { font-family: "Jost"; font-weight: 500; font-display: swap; src: url("${p("jost-latin-500-normal.woff2")}") format("woff2"); }
.compteur-temps { position: absolute; z-index: 20; pointer-events: none; user-select: none; -webkit-user-select: none;
  width: var(--compteur-taille); display: flex; flex-direction: column; align-items: center; gap: 3px;
  font-family: Jost, "Helvetica Neue", Arial, sans-serif; color: #e8e6df; }
.compteur-temps svg { width: 100%; height: auto; display: block; overflow: visible; }
.compteur-temps .etiquette { font-family: Cinzel, "Cormorant Garamond", Georgia, serif; font-weight: 600; font-size: 14px;
  fill: rgba(236,232,222,0.92); text-anchor: middle; dominant-baseline: central; letter-spacing: 0.02em; }
.compteur-temps .etiquette .unite { font-family: Jost, "Helvetica Neue", Arial, sans-serif; font-weight: 500; font-size: 12.2px; fill: rgba(190,200,215,0.82); letter-spacing: 0; }
.compteur-temps .lecture { font-weight: 500; font-size: 12px; line-height: 1.25; text-align: center; text-wrap: balance;
  letter-spacing: 0.01em; text-shadow: 0 1px 6px #000, 0 0 2px #000; font-variant-numeric: lining-nums; }
.compteur-temps .sens { font-size: 11px; line-height: 1.2; color: #cfe6ff; text-shadow: 0 1px 6px #000; min-height: 1.2em; text-align: center; }
.compteur-temps .fleche-sens { transition: opacity 0.35s ease; }
`;
  document.head.appendChild(s);
}

function el(nom, attrs = {}, parent) {
  const e = document.createElementNS(NS, nom);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
const polaire = (a, r) => { const t = a * Math.PI / 180; return [100 + r * Math.sin(t), 100 - r * Math.cos(t)]; };
const arc = (a0, a1, r) => {
  const [x0, y0] = polaire(a0, r), [x1, y1] = polaire(a1, r);
  return `M ${x0.toFixed(3)} ${y0.toFixed(3)} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1.toFixed(3)} ${y1.toFixed(3)}`;
};

let nInstances = 0;

/**
 * Crée un compteur dans `conteneur`.
 * options : coin ("bas-droite" | "bas-gauche" | "haut-droite" | "haut-gauche"),
 *           marge (px, 14), taille (longueur CSS, « clamp(112px, 34vw, 150px) »),
 *           vitesse et sens initiaux (0, 0 : à l'arrêt).
 */
export function creeCompteur(conteneur, options = {}) {
  poseStyle();
  const id = `ct${++nInstances}`;
  const coin = options.coin || "bas-droite";
  const marge = options.marge ?? 14;
  const racine = document.createElement("div");
  racine.className = "compteur-temps";
  racine.setAttribute("role", "img");
  racine.style.setProperty("--compteur-taille", options.taille || "clamp(112px, 34vw, 150px)");
  if (conteneur === document.body) racine.style.position = "fixed";
  else if (getComputedStyle(conteneur).position === "static") conteneur.style.position = "relative";
  const [v, h] = coin.split("-");
  racine.style[v === "haut" ? "top" : "bottom"] = `calc(${marge}px + env(safe-area-inset-${v === "haut" ? "top" : "bottom"}, 0px))`;
  racine.style[h === "gauche" ? "left" : "right"] = `calc(${marge}px + env(safe-area-inset-${h === "gauche" ? "left" : "right"}, 0px))`;

  const svg = el("svg", { viewBox: "0 0 200 200", "aria-hidden": "true" }, racine);
  const defs = el("defs", {}, svg);
  const fond = el("radialGradient", { id: `${id}-fond`, cx: "50%", cy: "45%", r: "55%" }, defs);
  el("stop", { offset: "0", "stop-color": "#0d111b", "stop-opacity": "0.86" }, fond);
  el("stop", { offset: "1", "stop-color": "#04050a", "stop-opacity": "0.80" }, fond);
  const halo = el("filter", { id: `${id}-halo`, x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs);
  el("feGaussianBlur", { stdDeviation: "1.6", result: "f" }, halo);
  const fm = el("feMerge", {}, halo);
  el("feMergeNode", { in: "f" }, fm); el("feMergeNode", { in: "SourceGraphic" }, fm);

  // Cadran
  el("circle", { cx: 100, cy: 100, r: 97, fill: `url(#${id}-fond)`, stroke: "rgba(207,230,255,0.34)", "stroke-width": 1 }, svg);
  el("circle", { cx: 100, cy: 100, r: 93, fill: "none", stroke: "rgba(255,255,255,0.07)", "stroke-width": 0.8 }, svg);
  el("path", { d: arc(ANGLE_MIN, ANGLE_MAX, 86), fill: "none", stroke: "rgba(255,255,255,0.16)", "stroke-width": 1 }, svg);
  // Arc lumineux de la vitesse courante
  const trace = el("path", { d: arc(ANGLE_MIN, ANGLE_MAX, 86), pathLength: 270, fill: "none", stroke: "rgba(207,230,255,0.85)",
    "stroke-width": 2, "stroke-linecap": "round", "stroke-dasharray": "0 400", filter: `url(#${id}-halo)` }, svg);

  // Graduations : décades fines, graduations majeures (toutes les deux décades) et étiquettes
  for (let d = 0; d <= DECADES; d++) {
    const a = ANGLE_MIN + 27 * d;
    if (d % 2) {
      const [x0, y0] = polaire(a, 81), [x1, y1] = polaire(a, 89);
      el("line", { x1: x0, y1: y0, x2: x1, y2: y1, stroke: "rgba(232,230,223,0.5)", "stroke-width": 1 }, svg);
    }
    for (const m of [2, 5]) if (d < DECADES) {
      const am = a + 27 * Math.log10(m), [x0, y0] = polaire(am, 85.5), [x1, y1] = polaire(am, 89);
      el("line", { x1: x0, y1: y0, x2: x1, y2: y1, stroke: "rgba(232,230,223,0.26)", "stroke-width": 0.8 }, svg);
    }
  }
  for (const [val, chiffre, unite] of GRADUATIONS) {
    const a = angleVitesse(val), [x0, y0] = polaire(a, 76), [x1, y1] = polaire(a, 90);
    el("line", { class: "grad-majeure", "data-vitesse": String(val), x1: x0, y1: y0, x2: x1, y2: y1,
      stroke: "rgba(240,236,226,0.95)", "stroke-width": 1.8, "stroke-linecap": "round" }, svg);
    const [xt, yt] = polaire(a, 62);
    const t = el("text", { class: "etiquette", "data-vitesse": String(val), "data-angle": String(a), x: xt.toFixed(2), y: yt.toFixed(2) }, svg);
    t.appendChild(document.createTextNode(chiffre));
    const u = el("tspan", { class: "unite" }, t);
    u.textContent = unite;
  }
  // Taquet de butée
  { const [x, y] = polaire(ANGLE_BUTEE - 2.2, 74);
    el("circle", { class: "butee", cx: x, cy: y, r: 2.4, fill: "rgba(232,230,223,0.55)", stroke: "rgba(0,0,0,0.6)", "stroke-width": 0.6 }, svg); }

  // Flèche de sens (à rebours), sous le moyeu
  const fleche = el("g", { class: "fleche-sens", opacity: 0, style: "opacity:0", filter: `url(#${id}-halo)` }, svg);
  el("path", { d: arc(-60, 60, 30), fill: "none", stroke: "#cfe6ff", "stroke-width": 1.4, "stroke-linecap": "round", transform: "rotate(180 100 100)" }, fleche);
  { const [x, y] = polaire(-60, 30), p = (a, l) => { const [dx, dy] = [Math.sin(a * Math.PI / 180) * l, -Math.cos(a * Math.PI / 180) * l]; return `${(200 - x + dx).toFixed(2)} ${(200 - y + dy).toFixed(2)}`; };
    // pointe de flèche au bout de l'arc, tournée vers la gauche (sens anti-horaire)
    el("path", { d: `M ${p(-10, 6.5)} L ${(200 - x).toFixed(2)} ${(200 - y).toFixed(2)} L ${p(-100, 6.5)}`, fill: "none", stroke: "#cfe6ff", "stroke-width": 1.4, "stroke-linecap": "round", "stroke-linejoin": "round" }, fleche); }

  // Aiguille
  const aiguille = el("g", { class: "aiguille", transform: `rotate(${ANGLE_BUTEE} 100 100)` }, svg);
  el("path", { d: "M 98.3 112 L 99.4 100 L 99.75 19 L 100.25 19 L 100.6 100 L 101.7 112 Z", fill: "#ffd9a0",
    stroke: "rgba(255,190,120,0.6)", "stroke-width": 0.4, filter: `url(#${id}-halo)` }, aiguille);
  el("circle", { class: "pointe", cx: 100, cy: 19.5, r: 0.5, fill: "#fff2dc" }, aiguille);
  el("circle", { class: "moyeu", cx: 100, cy: 100, r: 5.2, fill: "#0b0e16", stroke: "rgba(255,217,160,0.85)", "stroke-width": 1.2 }, svg);
  el("circle", { cx: 100, cy: 100, r: 1.6, fill: "rgba(255,217,160,0.9)" }, svg);

  const lecture = document.createElement("div");
  lecture.className = "lecture";
  const sensTxt = document.createElement("div");
  sensTxt.className = "sens";
  racine.append(lecture, sensTxt);
  conteneur.appendChild(racine);

  // Étiquettes : chacune glisse le long de son rayon jusqu'à tenir à l'intérieur des
  // graduations (cercle de rayon 73), une fois la police chargée.
  const placeEtiquettes = () => {
    if (!racine.isConnected) return;
    for (const t of svg.querySelectorAll(".etiquette")) {
      const a = +t.dataset.angle;
      let r = 62;
      for (let i = 0; i < 40; i++) {
        const [x, y] = polaire(a, r);
        t.setAttribute("x", x.toFixed(2)); t.setAttribute("y", y.toFixed(2));
        const b = t.getBBox();
        if (!b.width) break;
        const coins = [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]];
        const loin = Math.max(...coins.map(([u, v]) => Math.hypot(u - 100, v - 100)));
        if (loin <= 73.5 || r < 30) break;
        r -= Math.max(0.5, loin - 73.5);
      }
    }
  };
  placeEtiquettes();
  if (document.fonts) document.fonts.ready.then(placeEtiquettes);
  document.fonts?.addEventListener?.("loadingdone", placeEtiquettes);
  const oublie = () => document.fonts?.removeEventListener?.("loadingdone", placeEtiquettes);

  // Dynamique de l'aiguille : ressort amorti sur l'angle
  const W0 = 9, ZETA = 0.78;
  let angle = ANGLE_BUTEE, omega = 0, cible = ANGLE_BUTEE;
  let vit = 0, sens = 0, raf = 0, tPrec = 0, detruit = false;

  const dessine = () => {
    aiguille.setAttribute("transform", `rotate(${angle.toFixed(3)} 100 100)`);
    const l = Math.max(0, Math.min(270, angle - ANGLE_MIN));
    trace.setAttribute("stroke-dasharray", `${l.toFixed(2)} 400`);
    trace.setAttribute("opacity", l > 0.2 ? 1 : 0);
  };
  const pas = t => {
    raf = 0;
    if (detruit) return;
    let dt = Math.min(0.05, Math.max(0, (t - tPrec) / 1000));
    tPrec = t;
    while (dt > 0) {
      const h = Math.min(dt, 0.004);
      omega += (W0 * W0 * (cible - angle) - 2 * ZETA * W0 * omega) * h;
      angle += omega * h;
      dt -= h;
    }
    if (Math.abs(cible - angle) < 0.01 && Math.abs(omega) < 0.05) { angle = cible; omega = 0; dessine(); return; }
    dessine();
    raf = requestAnimationFrame(pas);
  };
  const anime = () => { if (!raf && !detruit) { tPrec = performance.now(); raf = requestAnimationFrame(pas); } };

  const api = {
    /** Vitesse du temps en années par seconde ; sens 1 (avant), -1 (à rebours), 0 (arrêt).
     *  Une vitesse négative sans sens explicite vaut « à rebours ». */
    vitesse(ansParSeconde, s) {
      let v = Number(ansParSeconde) || 0;
      if (s === undefined) s = v < 0 ? -1 : v > 0 ? 1 : 0;
      v = Math.abs(v);
      if (v === 0) s = 0;
      vit = v; sens = Math.sign(s);
      const txt = lectureEnClair(v, sens);
      if (lecture.textContent !== txt) lecture.textContent = txt;
      const reb = sens < 0;
      sensTxt.textContent = reb ? "le temps remonte" : "";
      fleche.style.opacity = reb ? "1" : "0";
      racine.setAttribute("aria-label", `Vitesse du temps : ${txt}${reb ? ", le temps remonte" : ""}`);
      const c = angleVitesse(v, sens);
      if (c !== cible) { cible = c; anime(); }
      return api;
    },
    /** État courant (pour les contrôles et les pages hôtes). */
    etat() { return { vitesse: vit, sens, angle, cible, anime: raf !== 0 }; },
    element: racine,
    detruit() { detruit = true; oublie(); if (raf) cancelAnimationFrame(raf); raf = 0; racine.remove(); },
  };
  api.vitesse(options.vitesse ?? 0, options.sens);
  dessine();
  return api;
}
