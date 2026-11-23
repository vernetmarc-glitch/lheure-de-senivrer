// Compteur de vitesse du temps (N28, D-43) — copie conforme à la spécification de
// docs/references-visuelles-refonte.md, en attendant app/public/commun/compteur.js (S0).
//
// Cadran de voiture : aiguille sur une échelle logarithmique de 1 an à 10 milliards
// d'années par seconde, graduée 1 an · 100 ans · 10 000 ans · 1 Ma · 100 Ma · 10 Ga,
// lecture chiffrée en clair. Temps à l'arrêt : aiguille sur la butée. Temps remonté :
// une flèche indique le sens. Aiguille amortie (ressort critique).
//
// Usage : const c = new Compteur(parent); à chaque image c.regler(ansParSeconde, dt).

export const LOG_MIN = 0, LOG_MAX = 10;            // log10(ans par seconde)
export const ANGLE_MIN = -125, ANGLE_MAX = 125;    // degrés, 0 = aiguille verticale
export const BUTEE = -140;

/** Angle (degrés) que doit montrer l'aiguille pour une vitesse (ans par seconde). */
export function angleCible(ansParSeconde) {
  const v = Math.abs(ansParSeconde);
  if (!(v > 0)) return BUTEE;
  const l = Math.min(Math.max(Math.log10(v), LOG_MIN), LOG_MAX);
  return ANGLE_MIN + (ANGLE_MAX - ANGLE_MIN) * (l - LOG_MIN) / (LOG_MAX - LOG_MIN);
}

/** Lecture en clair : « 10 000 ans par seconde », « 1,2 million d'années par seconde ». */
export function lecture(ansParSeconde) {
  const v = Math.abs(ansParSeconde);
  if (!(v > 0)) return "temps arrêté";
  const deux = x => { const p = Math.pow(10, Math.floor(Math.log10(x)) - 1); return Math.round(x / p) * p; };
  let s;
  if (v < 1.5) s = "1 an";
  else if (v < 1e6) s = deux(v).toLocaleString("fr-FR") + " ans";
  else if (v < 1e9) { const m = deux(v / 1e6); s = m.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + (m < 2 ? " million" : " millions") + " d'années"; }
  else { const g = deux(v / 1e9); s = g.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + (g < 2 ? " milliard" : " milliards") + " d'années"; }
  return s + " par seconde";
}

const GRADS = [[0, "1 an"], [2, "100 ans"], [4, "10 000 ans"], [6, "1 Ma"], [8, "100 Ma"], [10, "10 Ga"]];

export class Compteur {
  constructor(parent, { taille = 112, omega = 14 } = {}) {
    this.omega = omega; this.a = BUTEE; this.va = 0; this.v = 0;
    const e = document.createElement("div");
    e.className = "compteur";
    e.style.cssText = `position:fixed;top:max(10px,env(safe-area-inset-top));right:10px;width:${taille}px;` +
      `pointer-events:none;z-index:3;font-family:-apple-system,system-ui,sans-serif;color:#f3efe6;text-align:center`;
    const R = 50, ns = "http://www.w3.org/2000/svg";
    const pol = (ang, r) => { const t = (ang - 90) * Math.PI / 180; return [60 + r * Math.cos(t), 60 + r * Math.sin(t)]; };
    let svg = `<svg viewBox="0 0 120 104" width="${taille}" height="${taille * 104 / 120}" xmlns="${ns}" aria-hidden="true">` +
      `<circle cx="60" cy="60" r="${R + 4}" fill="rgba(10,15,24,.58)" stroke="rgba(243,239,230,.35)" stroke-width="1"/>`;
    for (let l = 0; l <= 10; l++) {
      const ang = ANGLE_MIN + (ANGLE_MAX - ANGLE_MIN) * l / 10, [x0, y0] = pol(ang, R - (l % 2 ? 4 : 7)), [x1, y1] = pol(ang, R);
      svg += `<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="#f3efe6" stroke-width="${l % 2 ? 0.8 : 1.4}"/>`;
    }
    for (const [l, txt] of GRADS) {
      const ang = ANGLE_MIN + (ANGLE_MAX - ANGLE_MIN) * l / 10, [x, y] = pol(ang, R - 15);
      svg += `<text x="${x}" y="${y + 2.5}" font-size="7.2" fill="rgba(243,239,230,.9)" text-anchor="middle">${txt}</text>`;
    }
    const [bx, by] = pol(BUTEE, R - 2);
    svg += `<circle cx="${bx}" cy="${by}" r="1.8" fill="rgba(243,239,230,.6)"/>` +
      `<g class="aiguille"><line x1="60" y1="66" x2="60" y2="${60 - R + 6}" stroke="#ffb35c" stroke-width="2" stroke-linecap="round"/></g>` +
      `<circle cx="60" cy="60" r="3.2" fill="#ffb35c"/>` +
      `<text class="sens" x="60" y="82" font-size="9" fill="#ffb35c" text-anchor="middle"></text></svg>`;
    e.innerHTML = svg + `<div class="lecture" style="font-size:10.5px;line-height:1.2;margin-top:-6px;text-shadow:0 1px 4px rgba(0,0,0,.9)"></div>`;
    parent.appendChild(e);
    this.e = e; this.g = e.querySelector(".aiguille"); this.sens = e.querySelector(".sens"); this.txt = e.querySelector(".lecture");
    this._dessiner();
  }
  /** Vitesse réelle du temps (ans par seconde, signée) et pas de temps écoulé (s). */
  regler(ansParSeconde, dt) {
    this.v = ansParSeconde;
    const cible = angleCible(ansParSeconde), w = this.omega;
    dt = Math.min(Math.max(dt || 0, 0), 0.1);
    const n = Math.max(1, Math.ceil(dt / 0.004)), h = dt / n;     // ressort critique
    for (let i = 0; i < n; i++) { const acc = w * w * (cible - this.a) - 2 * w * this.va; this.va += acc * h; this.a += this.va * h; }
    this._dessiner();
  }
  angle() { return this.a; }
  _dessiner() {
    this.g.setAttribute("transform", `rotate(${this.a.toFixed(2)} 60 60)`);
    this.sens.textContent = this.v < 0 ? "◀ on remonte" : "";
    const t = lecture(this.v); if (this.txt.textContent !== t) this.txt.textContent = t;
  }
}
