// Compteur de vitesse du temps (N28) — copie conforme à la spécification de
// docs/references-visuelles-refonte.md, en attendant app/public/commun/compteur.js (S0).
//
// Cadran de voiture : aiguille sur une échelle logarithmique de 1 an à 10 milliards
// d'années par seconde, graduée 1 an · 100 ans · 10 000 ans · 1 Ma · 100 Ma · 10 Ga,
// lecture chiffrée en clair. Temps à l'arrêt : l'aiguille tombe sur la butée. Temps
// remonté : une flèche indique le sens. Aiguille amortie (ressort critique).
//
//   const c = creeCompteur(document.body, { coin: "haut-droite", taille: 92 });
//   c.regle(vitesse);   // années de temps simulé par seconde réelle (négatif = remonte)
//   c.angle();          // angle actuel de l'aiguille (degrés, 0 = verticale)
//   c.angleCible(v);    // angle exact que doit atteindre l'aiguille pour la vitesse v
//   c.boite();          // rectangle occupé à l'écran (pour vérifier qu'il ne masque rien)

export const ECHELLE = { logMin: 0, logMax: 10, angleMin: -120, angleMax: 120, butee: -138 };

export function angleDe(v) {
  const a = Math.abs(v);
  if (!(a > 0)) return ECHELLE.butee;
  const l = Math.min(Math.max(Math.log10(a), ECHELLE.logMin), ECHELLE.logMax);
  return ECHELLE.angleMin + (ECHELLE.angleMax - ECHELLE.angleMin) * (l - ECHELLE.logMin) / (ECHELLE.logMax - ECHELLE.logMin);
}

const fmt = n => n.toLocaleString("fr-FR", { maximumFractionDigits: 0 }).replace(/ | /g, " ");

export function lectureDe(v) {
  const a = Math.abs(v);
  if (!(a > 0)) return "temps arrêté";
  const arr = x => { const p = Math.pow(10, Math.floor(Math.log10(x)) - 1); return Math.round(x / p) * p; };
  let s;
  if (a < 1) s = "moins d'un an";
  else if (a < 1e6) { const x = arr(a); s = x < 2 ? "1 an" : `${fmt(x)} ans`; }
  else if (a < 1e9) { const x = arr(a / 1e6); s = `${x.toLocaleString("fr-FR")} million${x >= 2 ? "s" : ""} d'années`; }
  else { const x = arr(a / 1e9); s = `${x.toLocaleString("fr-FR")} milliard${x >= 2 ? "s" : ""} d'années`; }
  return `${s} par seconde`;
}

export function creeCompteur(parent, opts = {}) {
  const T = opts.taille || 92, coin = opts.coin || "haut-droite";
  const boiteEl = document.createElement("div");
  boiteEl.className = "compteur";
  const pos = { "haut-droite": "top:10px;right:10px", "haut-gauche": "top:10px;left:10px",
                "bas-droite": "bottom:10px;right:10px", "bas-gauche": "bottom:10px;left:10px" }[coin];
  boiteEl.style.cssText = `position:absolute;${pos};width:${T}px;pointer-events:none;z-index:5;text-align:center;` +
    "font:500 10px var(--f-corps, 'Jost', sans-serif);color:rgba(230,232,240,0.9);text-shadow:0 1px 3px #000";
  const dpr = Math.min(window.devicePixelRatio || 1, 3);
  const cv = document.createElement("canvas");
  cv.width = T * dpr; cv.height = T * 0.78 * dpr;
  cv.style.cssText = `width:${T}px;height:${T * 0.78}px;display:block`;
  const lec = document.createElement("div");
  lec.className = "compteur-lecture";
  lec.style.cssText = "margin-top:-2px;line-height:1.15;min-height:24px";
  boiteEl.append(cv, lec); parent.append(boiteEl);
  const g = cv.getContext("2d");

  let cible = ECHELLE.butee, ang = ECHELLE.butee, vit = 0, v = 0, dernier = performance.now(), sens = 1;

  function dessine() {
    const W = cv.width, H = cv.height, cx = W / 2, cy = H * 0.64, R = W * 0.44;
    g.clearRect(0, 0, W, H);
    g.save(); g.translate(cx, cy);
    const rad = d => (d - 90) * Math.PI / 180;
    // fond du cadran
    g.beginPath(); g.arc(0, 0, R * 1.04, rad(-140), rad(140)); g.lineTo(0, 0); g.closePath();
    g.fillStyle = "rgba(8,10,18,0.62)"; g.fill();
    g.beginPath(); g.arc(0, 0, R, rad(ECHELLE.angleMin), rad(ECHELLE.angleMax));
    g.strokeStyle = "rgba(150,170,220,0.45)"; g.lineWidth = 1.2 * dpr; g.stroke();
    // graduations : une par décade, étiquette toutes les deux
    const et = { 0: "1 an", 2: "100 ans", 4: "10⁴ ans", 6: "1 Ma", 8: "100 Ma", 10: "10 Ga" };
    for (let l = 0; l <= 10; l++) {
      const a = rad(ECHELLE.angleMin + 24 * l), maj = l % 2 === 0;
      g.beginPath(); g.moveTo(Math.cos(a) * R, Math.sin(a) * R);
      g.lineTo(Math.cos(a) * R * (maj ? 0.8 : 0.88), Math.sin(a) * R * (maj ? 0.8 : 0.88));
      g.strokeStyle = maj ? "rgba(235,225,200,0.95)" : "rgba(200,205,225,0.6)"; g.lineWidth = (maj ? 1.4 : 1) * dpr; g.stroke();
      if (maj) {
        g.font = `${6.3 * dpr}px Jost, sans-serif`; g.fillStyle = "rgba(230,232,240,0.92)";
        g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText(et[l], Math.cos(a) * R * 0.6, Math.sin(a) * R * 0.6 + (l === 4 || l === 6 ? 2 * dpr : 0));
      }
    }
    // butée
    const b = rad(ECHELLE.butee);
    g.beginPath(); g.arc(Math.cos(b) * R * 0.92, Math.sin(b) * R * 0.92, 1.6 * dpr, 0, 7);
    g.fillStyle = "rgba(200,205,225,0.7)"; g.fill();
    // aiguille
    const a = rad(ang);
    g.beginPath(); g.moveTo(-Math.cos(a) * R * 0.12, -Math.sin(a) * R * 0.12);
    g.lineTo(Math.cos(a) * R * 0.96, Math.sin(a) * R * 0.96);
    g.strokeStyle = "rgba(255,190,110,1)"; g.lineWidth = 1.8 * dpr; g.lineCap = "round"; g.stroke();
    g.beginPath(); g.arc(0, 0, 2.6 * dpr, 0, 7); g.fillStyle = "rgba(255,210,150,1)"; g.fill();
    // flèche : temps remonté
    if (sens < 0 && cible !== ECHELLE.butee) {
      g.font = `${10 * dpr}px Jost, sans-serif`; g.fillStyle = "rgba(255,190,110,1)"; g.textAlign = "center";
      g.fillText("↺", 0, R * 0.32);
    }
    g.restore();
  }

  function pas(n) {
    const dt = Math.min((n - dernier) / 1000, 0.05); dernier = n;
    // ressort critique : ω = 9 s⁻¹ (aiguille posée en ≈ 0,6 s)
    const w = 9.0, acc = w * w * (cible - ang) - 2 * w * vit;
    vit += acc * dt; ang += vit * dt;
    if (Math.abs(cible - ang) < 0.02 && Math.abs(vit) < 0.05) { ang = cible; vit = 0; }
    dessine();
    requestAnimationFrame(pas);
  }
  requestAnimationFrame(pas);

  return {
    regle(nv) {
      v = nv; cible = angleDe(nv); sens = nv < 0 ? -1 : 1;
      const t = lectureDe(nv) + (nv < 0 ? " — le temps remonte" : "");
      if (lec.textContent !== t) lec.textContent = t;
    },
    vitesse: () => v,
    angle: () => ang,
    angleCible: angleDe,
    boite: () => boiteEl.getBoundingClientRect(),
    element: boiteEl,
  };
}
