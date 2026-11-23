// Compteur de vitesse du temps (N28, docs/references-visuelles-refonte.md).
// Copie conforme à la spécification, en attendant le composant commun
// app/public/commun/compteur.js (chantier S0) : même interface, à remplacer par lui.
//
// Cadran de voiture : aiguille sur une échelle logarithmique de 1 an à 10 milliards
// d'années par seconde, graduée 1 an · 100 ans · 10 000 ans · 1 Ma · 100 Ma · 10 Ga,
// lecture chiffrée en clair ; à l'arrêt l'aiguille tombe sur la butée ; temps remonté :
// une flèche indique le sens ; aiguille amortie (ressort critique).
//
//   const c = new Compteur(conteneur, {taille, style, disposition: "ligne" | "colonne"});  c.regler(ansParSeconde, sens);   // sens -1 : vers le passé
//   c.angle(), c.angleCible(), Compteur.angleDe(v)   (degrés, 0 = midi, sens horaire)
(function () {
  "use strict";
  const A0 = -120, PAR_DECADE = 24, BUTEE = -138;      // 1 an/s -> -120°, 10 Ga/s -> +120°
  const GRAD = [[0, "1 an"], [2, "100 ans"], [4, "10 000 ans"], [6, "1 Ma"], [8, "100 Ma"], [10, "10 Ga"]];
  const NS = "http://www.w3.org/2000/svg";

  function lecture(v) {
    if (!(v > 0)) return "temps à l'arrêt";
    const f = (x, u1, u2) => { const r = x >= 100 ? Math.round(x) : x >= 10 ? Math.round(x) : Math.round(x * 10) / 10;
      return r.toLocaleString("fr-FR") + " " + (r >= 2 ? u2 : u1); };
    if (v < 1e3) return f(v, "an", "ans") + " par seconde";
    if (v < 1e6) return (Math.round(v / 100) * 100).toLocaleString("fr-FR") + " ans par seconde";
    if (v < 1e9) return f(v / 1e6, "million d'années", "millions d'années") + " par seconde";
    return f(v / 1e9, "milliard d'années", "milliards d'années") + " par seconde";
  }

  class Compteur {
    static angleDe(v) {
      if (!(v > 0)) return BUTEE;
      return A0 + PAR_DECADE * Math.min(10, Math.max(0, Math.log10(v)));
    }
    constructor(parent, opts = {}) {
      const T = opts.taille || 76;
      this.el = document.createElement("div");
      this.el.className = "compteur";
      const ligne = opts.disposition === "ligne";       // lecture à gauche du cadran
      this.el.style.cssText = `position:absolute;${ligne ? "display:flex;flex-direction:row-reverse;align-items:center;gap:6px;" : `width:${T}px;`}pointer-events:none;text-align:${ligne ? "right" : "center"};` +
        "font:10px/1.2 var(--f-corps, sans-serif);color:#c9ccd3;" + (opts.style || "");
      const svg = document.createElementNS(NS, "svg");
      svg.setAttribute("viewBox", "-50 -50 100 100"); svg.setAttribute("width", T); svg.setAttribute("height", T);
      const arc = (r, a, b) => { const p = d => [r * Math.sin(d * Math.PI / 180), -r * Math.cos(d * Math.PI / 180)];
        const [x0, y0] = p(a), [x1, y1] = p(b); return `M${x0} ${y0} A${r} ${r} 0 ${b - a > 180 ? 1 : 0} 1 ${x1} ${y1}`; };
      let h = `<circle r="47" fill="rgba(4,5,10,.55)" stroke="rgba(232,230,223,.35)" stroke-width="1"/>`;
      h += `<path d="${arc(40, A0, -A0)}" fill="none" stroke="rgba(232,230,223,.5)" stroke-width="1.2"/>`;
      for (let d = 0; d <= 10; d++) {
        const a = (A0 + PAR_DECADE * d) * Math.PI / 180, r1 = d % 2 ? 37 : 34;
        h += `<line x1="${40 * Math.sin(a)}" y1="${-40 * Math.cos(a)}" x2="${r1 * Math.sin(a)}" y2="${-r1 * Math.cos(a)}" stroke="#e8e6df" stroke-width="${d % 2 ? .8 : 1.4}"/>`;
      }
      for (const [d, s] of GRAD) {
        const a = (A0 + PAR_DECADE * d) * Math.PI / 180, r = 25;
        h += `<text x="${r * Math.sin(a)}" y="${-r * Math.cos(a) + 2.5}" font-size="7.2" fill="#e8e6df" text-anchor="middle">${s}</text>`;
      }
      h += `<g class="aiguille"><line x1="0" y1="6" x2="0" y2="-41" stroke="#ff8a5c" stroke-width="2" stroke-linecap="round"/></g>`;
      h += `<circle r="3.2" fill="#e8e6df"/>`;
      h += `<text class="sens" x="0" y="22" font-size="9" fill="#ff8a5c" text-anchor="middle"></text>`;
      svg.innerHTML = h;
      this.el.appendChild(svg);
      this.txt = document.createElement("div"); this.txt.className = "lecture";
      this.txt.style.cssText = ligne ? "width:96px;text-shadow:0 0 4px #04050a" : "margin-top:-4px;text-shadow:0 0 4px #04050a";
      this.el.appendChild(this.txt);
      parent.appendChild(this.el);
      this.aig = svg.querySelector(".aiguille"); this.fl = svg.querySelector(".sens");
      this.a = BUTEE; this.va = 0; this.cible = BUTEE; this.v = 0; this.sens = 1;
      this.tp = performance.now();
      const pas = now => {
        // ressort critique (≈ 0,3 s), intégré exactement : juste quelle que soit la cadence
        const dt = Math.min((now - this.tp) / 1000, 1); this.tp = now;
        const w = 14, x0 = this.a - this.cible, v0 = this.va, e = Math.exp(-w * dt), k = v0 + w * x0;
        this.a = this.cible + (x0 + k * dt) * e;
        this.va = (v0 - w * dt * k) * e;
        this.aig.setAttribute("transform", `rotate(${this.a})`);
        requestAnimationFrame(pas);
      };
      requestAnimationFrame(pas);
      this.regler(0, 1);
    }
    regler(v, sens = 1) {
      this.v = v > 0 ? v : 0; this.sens = sens < 0 ? -1 : 1;
      this.cible = Compteur.angleDe(this.v);
      const t = lecture(this.v);
      if (this.txt.textContent !== t) this.txt.textContent = t;
      this.fl.textContent = this.v > 0 && this.sens < 0 ? "◀ passé" : "";
    }
    angle() { return this.a; }
    angleCible() { return this.cible; }
  }
  Compteur.BUTEE = BUTEE;
  window.Compteur = Compteur;
})();
