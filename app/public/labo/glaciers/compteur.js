// Compteur de vitesse du temps (N28) — copie conforme à la spécification de
// docs/references-visuelles-refonte.md, en attendant app/public/commun/compteur.js (S0).
// Cadran de voiture : aiguille sur une échelle logarithmique de 1 an à 10 milliards
// d'années par seconde ; temps à l'arrêt : aiguille sur la butée ; temps remonté : une
// flèche indique le sens ; aiguille amortie (ressort à amortissement critique).
//
//   const c = new CompteurTemps(conteneur);
//   c.regler(ansParSeconde, sens)   // sens : +1 vers aujourd'hui, -1 vers le passé, 0 arrêt
//   c.angleCible()                  // angle (degrés) que doit atteindre l'aiguille
//   c.angleAffiche()                // angle (degrés) de l'aiguille dessinée
//   CompteurTemps.angle(v)          // échelle : -135° à 1 an/s, +135° à 10 Ga/s, butée -150°
(function () {
  'use strict';
  const A_MIN = -135, A_MAX = 135, A_BUTEE = -150, LOG_MIN = 0, LOG_MAX = 10;
  const GRAD = [[0, '1 an'], [2, '100 ans'], [4, '10 000 ans'], [6, '1 Ma'], [8, '100 Ma'], [10, '10 Ga']];
  const NS = 'http://www.w3.org/2000/svg';

  function angle(v) {
    if (!(v > 0)) return A_BUTEE;
    const l = Math.min(LOG_MAX, Math.max(LOG_MIN, Math.log10(v)));
    return A_MIN + (l - LOG_MIN) / (LOG_MAX - LOG_MIN) * (A_MAX - A_MIN);
  }
  function groupe(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }
  function lecture(v) {
    if (!(v > 0)) return 'temps arrêté';
    const unites = [[1e9, 'milliard', 'milliards'], [1e6, 'million', 'millions']];
    for (const [u, s, p] of unites) if (v >= u) {
      const x = v / u, t = x >= 10 ? Math.round(x) : Math.round(x * 10) / 10;
      return `${String(t).replace('.', ',')} ${t >= 2 ? p : s} d’années par seconde`;
    }
    const r = v >= 100 ? Math.round(v / 10 ** (Math.floor(Math.log10(v)) - 1)) * 10 ** (Math.floor(Math.log10(v)) - 1) : Math.round(v);
    return `${groupe(r)} an${r >= 2 ? 's' : ''} par seconde`;
  }
  function el(nom, attrs, parent) {
    const e = document.createElementNS(NS, nom);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function polaire(a, r) { const t = (a - 90) * Math.PI / 180; return [50 + r * Math.cos(t), 50 + r * Math.sin(t)]; }

  class CompteurTemps {
    constructor(conteneur) {
      this.v = 0; this.sens = 0; this.a = A_BUTEE; this.w = 0; this.t = performance.now();
      conteneur.classList.add('compteur-temps');
      const svg = el('svg', { viewBox: '0 0 100 100', role: 'img', 'aria-label': 'vitesse du temps' }, conteneur);
      el('circle', { cx: 50, cy: 50, r: 47, fill: 'rgba(10,16,26,.55)', stroke: 'rgba(255,255,255,.35)', 'stroke-width': 1 }, svg);
      // arc gradué
      const [x0, y0] = polaire(A_MIN, 40), [x1, y1] = polaire(A_MAX, 40);
      el('path', { d: `M${x0},${y0} A40,40 0 1 1 ${x1},${y1}`, fill: 'none', stroke: 'rgba(255,255,255,.55)', 'stroke-width': 1.2 }, svg);
      for (let l = 0; l <= 10; l++) {
        const a = A_MIN + l / 10 * (A_MAX - A_MIN), maj = l % 2 === 0;
        const [xa, ya] = polaire(a, maj ? 34 : 37), [xb, yb] = polaire(a, 40);
        el('line', { x1: xa, y1: ya, x2: xb, y2: yb, stroke: '#fff', 'stroke-width': maj ? 1.4 : 0.8, opacity: maj ? 0.9 : 0.6 }, svg);
      }
      for (const [l, txt] of GRAD) {
        const a = A_MIN + l / 10 * (A_MAX - A_MIN), [x, y] = polaire(a, 25);
        const t = el('text', { x, y: y + 2.4, 'text-anchor': 'middle', 'font-size': 7, fill: 'rgba(255,255,255,.85)',
          'font-family': 'system-ui, sans-serif' }, svg);
        t.textContent = txt.replace('10 000 ans', '10⁴ ans');
      }
      const [xb0, yb0] = polaire(A_BUTEE, 44);
      el('circle', { cx: xb0, cy: yb0, r: 1.6, fill: 'rgba(255,255,255,.6)' }, svg);   // butée
      this.aiguille = el('g', { class: 'aiguille', transform: `rotate(${A_BUTEE} 50 50)` }, svg);
      el('line', { x1: 50, y1: 56, x2: 50, y2: 12, stroke: '#ffb24a', 'stroke-width': 2, 'stroke-linecap': 'round' }, this.aiguille);
      el('circle', { cx: 50, cy: 50, r: 3.4, fill: '#ffb24a' }, svg);
      this.fleche = el('path', { d: 'M58,78 L42,78 M47,74 L42,78 L47,82', fill: 'none', stroke: '#ffb24a', 'stroke-width': 1.8,
        'stroke-linecap': 'round', 'stroke-linejoin': 'round', class: 'fleche-passe', visibility: 'hidden' }, svg);
      this.texte = document.createElement('div');
      this.texte.className = 'compteur-lecture';
      conteneur.appendChild(this.texte);
      this.texte.textContent = lecture(0);
      const boucle = (t) => { this.avancer(t); requestAnimationFrame(boucle); };
      requestAnimationFrame(boucle);
    }
    regler(v, sens) {
      this.v = v > 0 ? v : 0; this.sens = this.v > 0 ? (sens < 0 ? -1 : 1) : 0;
      const txt = lecture(this.v);
      if (this.texte.textContent !== txt) this.texte.textContent = txt;
      this.fleche.setAttribute('visibility', this.sens < 0 ? 'visible' : 'hidden');
    }
    angleCible() { return angle(this.v); }
    angleAffiche() {
      const m = /rotate\(([-\d.e]+)/.exec(this.aiguille.getAttribute('transform'));
      return m ? parseFloat(m[1]) : NaN;
    }
    avancer(t) {
      const dt = Math.min(0.25, Math.max(0, (t - this.t) / 1000)); this.t = t;
      const cible = this.angleCible(), w0 = 9;                    // amortissement critique, ≈ 0,5 s
      const n = Math.ceil(dt / 0.004);                            // sous-pas : stable quelle que soit la cadence
      for (let i = 0; i < n; i++) {
        const acc = w0 * w0 * (cible - this.a) - 2 * w0 * this.w;
        this.w += acc * dt / n; this.a += this.w * dt / n;
      }
      if (Math.abs(cible - this.a) < 0.01 && Math.abs(this.w) < 0.01) { this.a = cible; this.w = 0; }
      const tr = `rotate(${this.a.toFixed(3)} 50 50)`;
      if (tr !== this.tr) { this.aiguille.setAttribute('transform', tr); this.tr = tr; }
    }
  }
  CompteurTemps.angle = angle;
  CompteurTemps.lecture = lecture;
  CompteurTemps.BORNES = { A_MIN, A_MAX, A_BUTEE, LOG_MIN, LOG_MAX };
  window.CompteurTemps = CompteurTemps;
})();
