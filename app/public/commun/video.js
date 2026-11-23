// Lecteur de texture vidéo (N27) — composant commun.
//
//   import { creeLecteurVideo } from "../../commun/video.js";
//   const lv = await creeLecteurVideo(gl, [
//     { url: "x.av1.mp4", codec: "av01.0.04M.08" },   // pris si le navigateur le décode
//     { url: "x.h264.mp4", codec: "avc1.640020" },    // sinon H.264
//   ], { surImage: n => redessine() });
//   await lv.allerImage(42);  // ou allerTemps(secondes), allerFraction(0…1)
//   gl.bindTexture(gl.TEXTURE_2D, lv.texture);   // la texture de l'image affichée
//   lv.detruit();
//
// Pour les couleurs qui changent à projection fixe (textures de globe, couleurs de
// surface) : une vidéo MP4 codée avec une image clé toutes les 8 images et sans images B
// se décode image par image avec WebCodecs ; chaque image décodée est copiée dans une
// texture WebGL2 d'un petit cache (LRU), ce qui rend l'aller-retour fluide : avancer
// d'une image = un décodage, reculer dans le cache = aucun, sauter = au plus 8.
// Sans WebCodecs (ou sans le codec) : repli sur un élément <video>, recherche par
// horodatage, une seule texture.
//
// Le lecteur lie des textures sur l'unité de texture active et restaure la liaison.
// Les vidéos sont attendues en BT.709 (matrice, primaires), transfert sRGB, plage limitée.

/* ------------------------------------------------------------------ MP4 minimal */

const lit4cc = (v, o) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));

function boites(v, debut, fin) {
  const r = [];
  let o = debut;
  while (o + 8 <= fin) {
    let taille = v.getUint32(o), entete = 8;
    const type = lit4cc(v, o + 4);
    if (taille === 1) { taille = Number(v.getBigUint64(o + 8)); entete = 16; }
    else if (taille === 0) taille = fin - o;
    if (taille < entete || o + taille > fin) break;
    r.push({ type, debut: o, contenu: o + entete, fin: o + taille });
    o += taille;
  }
  return r;
}
const enfant = (v, b, type) => boites(v, b.contenu, b.fin).find(x => x.type === type);
const chemin = (v, b, ...types) => types.reduce((x, t) => x && enfant(v, x, t), b);
const hex2 = n => n.toString(16).padStart(2, "0").toUpperCase();

/** Lit un MP4 (piste vidéo, échantillons, configuration du décodeur). */
export function lisMp4(tampon) {
  const v = new DataView(tampon);
  const moov = boites(v, 0, v.byteLength).find(b => b.type === "moov");
  if (!moov) throw new Error("MP4 sans boîte moov");
  const trak = boites(v, moov.contenu, moov.fin).filter(b => b.type === "trak").find(t => {
    const h = chemin(v, t, "mdia", "hdlr");
    return h && lit4cc(v, h.contenu + 8) === "vide";
  });
  if (!trak) throw new Error("MP4 sans piste vidéo");
  const mdhd = chemin(v, trak, "mdia", "mdhd");
  const echelle = v.getUint8(mdhd.contenu) === 1 ? v.getUint32(mdhd.contenu + 20) : v.getUint32(mdhd.contenu + 12);
  const stbl = chemin(v, trak, "mdia", "minf", "stbl");

  // Description de l'échantillon (avc1 / av01) et configuration du décodeur
  const stsd = enfant(v, stbl, "stsd");
  const entree = boites(v, stsd.contenu + 8, stsd.fin)[0];
  const largeur = v.getUint16(entree.contenu + 24), hauteur = v.getUint16(entree.contenu + 26);
  const sous = boites(v, entree.contenu + 78, entree.fin);
  let codec, description, famille;
  const cfg = sous.find(b => b.type === "avcC" || b.type === "av1C");
  if (!cfg) throw new Error(`MP4 : codec ${entree.type} non pris en charge`);
  description = new Uint8Array(tampon.slice(cfg.contenu, cfg.fin));
  if (cfg.type === "avcC") {
    famille = "h264";
    codec = `avc1.${hex2(description[1])}${hex2(description[2])}${hex2(description[3])}`;
  } else {
    famille = "av1";
    const b1 = description[1], b2 = description[2];
    const prof = b1 >> 5, niveau = b1 & 31, tier = b2 >> 7, haut = (b2 >> 6) & 1, douze = (b2 >> 5) & 1;
    codec = `av01.${prof}.${String(niveau).padStart(2, "0")}${tier ? "H" : "M"}.${haut ? (douze ? "12" : "10") : "08"}`;
  }
  let espace;
  const colr = sous.find(b => b.type === "colr");
  if (colr && lit4cc(v, colr.contenu) === "nclx") {
    const P = { 1: "bt709", 5: "bt470bg", 6: "smpte170m", 9: "bt2020", 12: "smpte432" };
    const T = { 1: "bt709", 6: "smpte170m", 8: "linear", 13: "iec61966-2-1", 16: "pq", 18: "hlg" };
    const M = { 0: "rgb", 1: "bt709", 5: "bt470bg", 6: "smpte170m", 9: "bt2020-ncl" };
    const o = colr.contenu + 4;
    espace = { primaries: P[v.getUint16(o)], transfer: T[v.getUint16(o + 2)], matrix: M[v.getUint16(o + 4)], fullRange: !!(v.getUint8(o + 6) >> 7) };
    for (const k of Object.keys(espace)) if (espace[k] === undefined) delete espace[k];
  }

  // Tables d'échantillons
  const tbl = t => enfant(v, stbl, t);
  const stsz = tbl("stsz"), stsc = tbl("stsc"), stts = tbl("stts"), stss = tbl("stss"), ctts = tbl("ctts");
  const stco = tbl("stco") || tbl("co64"), co64 = stco.type === "co64";
  const n = v.getUint32(stsz.contenu + 8), tailleFixe = v.getUint32(stsz.contenu + 4);
  const tailles = Array.from({ length: n }, (_, i) => tailleFixe || v.getUint32(stsz.contenu + 12 + 4 * i));
  const nMorceaux = v.getUint32(stco.contenu + 4);
  const morceaux = Array.from({ length: nMorceaux }, (_, i) => co64 ? Number(v.getBigUint64(stco.contenu + 8 + 8 * i)) : v.getUint32(stco.contenu + 8 + 4 * i));
  const entreesSc = Array.from({ length: v.getUint32(stsc.contenu + 4) }, (_, i) => [v.getUint32(stsc.contenu + 8 + 12 * i), v.getUint32(stsc.contenu + 12 + 12 * i)]);
  const decalages = new Array(n);
  let s = 0;
  for (let e = 0; e < entreesSc.length; e++) {
    const [premier, parMorceau] = entreesSc[e];
    const dernier = e + 1 < entreesSc.length ? entreesSc[e + 1][0] - 1 : nMorceaux;
    for (let m = premier; m <= dernier && s < n; m++) {
      let o = morceaux[m - 1];
      for (let k = 0; k < parMorceau && s < n; k++) { decalages[s] = o; o += tailles[s++]; }
    }
  }
  const dts = new Array(n), durees = new Array(n);
  { let t = 0, i = 0; const c = v.getUint32(stts.contenu + 4);
    for (let e = 0; e < c; e++) { const nb = v.getUint32(stts.contenu + 8 + 8 * e), d = v.getUint32(stts.contenu + 12 + 8 * e);
      for (let k = 0; k < nb && i < n; k++) { dts[i] = t; durees[i++] = d; t += d; } } }
  const cts = dts.slice();
  if (ctts) { let i = 0; const c = v.getUint32(ctts.contenu + 4), v1 = v.getUint8(ctts.contenu) === 1;
    for (let e = 0; e < c; e++) { const nb = v.getUint32(ctts.contenu + 8 + 8 * e), d = v1 ? v.getInt32(ctts.contenu + 12 + 8 * e) : v.getUint32(ctts.contenu + 12 + 8 * e);
      for (let k = 0; k < nb && i < n; k++) cts[i++] += d; } }
  const cles = new Set();
  if (stss) { const c = v.getUint32(stss.contenu + 4); for (let e = 0; e < c; e++) cles.add(v.getUint32(stss.contenu + 8 + 4 * e) - 1); }
  const echantillons = Array.from({ length: n }, (_, i) => ({
    decalage: decalages[i], taille: tailles[i], cle: stss ? cles.has(i) : true,
    temps: cts[i] / echelle, duree: durees[i] / echelle,
  }));
  for (let i = 1; i < n; i++) if (cts[i] <= cts[i - 1]) throw new Error("MP4 avec images B : non pris en charge (coder sans images B)");
  if (!echantillons[0]?.cle) throw new Error("MP4 : la première image n'est pas une image clé");
  return { largeur, hauteur, echelle, codec, famille, description, espace, echantillons,
    ips: n > 1 ? (n - 1) / (echantillons[n - 1].temps - echantillons[0].temps) : 1 };
}

/* ------------------------------------------------------------------ outils WebGL */

function texture(gl, l, h) {
  const prec = gl.getParameter(gl.TEXTURE_BINDING_2D);
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, l, h);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.bindTexture(gl.TEXTURE_2D, prec);
  return t;
}
function verse(gl, t, l, h, source) {
  const prec = gl.getParameter(gl.TEXTURE_BINDING_2D);
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, l, h, gl.RGBA, gl.UNSIGNED_BYTE, source);
  gl.bindTexture(gl.TEXTURE_2D, prec);
}
const dort = ms => new Promise(r => setTimeout(r, ms));

/* ------------------------------------------------------------------ socle commun */

class Lecteur {
  constructor(gl, mp4, options) {
    this.gl = gl;
    this.mp4 = mp4;
    this.largeur = mp4.largeur;
    this.hauteur = mp4.hauteur;
    this.images = mp4.echantillons.length;
    this.ips = mp4.ips;
    this.duree = this.images / this.ips;
    this.image = null;          // index de l'image affichée
    this.stats = { decodes: 0, sorties: 0, vidages: 0, cache: 0, recherches: 0, erreurs: 0 };
    this._surImage = options.surImage || (() => {});
    this._cible = null;
    this._attentes = [];
    this._occupe = false;
    this._fini = false;
  }
  /** Index de l'image affichée à l'instant t (secondes depuis le début de la vidéo). */
  indexTemps(t) {
    const e = this.mp4.echantillons, t0 = e[0].temps;
    return Math.max(0, Math.min(this.images - 1, Math.floor((t - t0) * this.ips + 1e-6)));
  }
  allerTemps(t) { return this.allerImage(this.indexTemps(t)); }
  allerFraction(f) { return this.allerImage(Math.round(Math.max(0, Math.min(1, f)) * (this.images - 1))); }
  /** Demande l'image n ; la promesse rend l'index affiché quand la dernière demande est servie. */
  allerImage(n) {
    n = Math.max(0, Math.min(this.images - 1, Math.round(n)));
    this._cible = n;
    const p = new Promise(r => this._attentes.push(r));
    if (n === this.image) this._servi(); else this._travaille();
    return p;
  }
  _servi() {
    const a = this._attentes; this._attentes = [];
    for (const r of a) r(this.image);
  }
  _montre(n) {
    this.image = n;
    this._surImage(n);
    if (n === this._cible) this._servi();
  }
  async _travaille() {
    if (this._occupe || this._fini) return;
    this._occupe = true;
    try {
      let echecs = 0;
      while (!this._fini && this._cible !== null && this._cible !== this.image) {
        const n = this._cible;
        const ok = await this._obtiens(n);
        if (ok) this._montre(n);
        else if (++echecs > 3) { console.error(`lecteur vidéo : image ${n} introuvable`); break; }
      }
    } finally { this._occupe = false; }
  }
}

/* ------------------------------------------------------------------ WebCodecs */

class LecteurWebCodecs extends Lecteur {
  constructor(gl, mp4, octets, config, options) {
    super(gl, mp4, options);
    this.mode = `webcodecs-${mp4.famille}`;
    this.codec = mp4.codec;
    this._octets = octets;
    this._config = config;
    const memoire = options.memoireMax ?? 96e6;
    this._capacite = Math.max(4, Math.min(options.cache ?? 24, Math.floor(memoire / (mp4.largeur * mp4.hauteur * 4))));
    this._cache = new Map();        // index → texture, ordre = récence
    this._libres = [];
    this._parTemps = new Map(mp4.echantillons.map((e, i) => [Math.round(e.temps * 1e6), i]));
    this._clesAvant = [];
    let k = 0;
    mp4.echantillons.forEach((e, i) => { if (e.cle) k = i; this._clesAvant[i] = k; });
    this._veilleurs = new Map();
    this._creeDecodeur();
  }
  _creeDecodeur() {
    this._envoye = -1;
    this._besoinCle = true;
    this._decodeur = new VideoDecoder({
      output: f => this._sortie(f),
      error: e => { this.stats.erreurs++; console.warn("lecteur vidéo : décodeur relancé —", e.message); this._decodeurMort = true; },
    });
    this._decodeurMort = false;
    this._decodeur.configure(this._config);
  }
  get texture() { return this.image === null ? null : this._cache.get(this.image) ?? null; }
  _sortie(f) {
    const i = this._parTemps.get(f.timestamp);
    this.stats.sorties++;
    this._derniereSortie = performance.now();
    if (i === undefined || this._fini) { f.close(); return; }
    if (this._cache.has(i)) { f.close(); return; }   // déjà en cache : rien à recopier
    let t;
    if (this._libres.length) t = this._libres.pop();
    else if (this._cache.size < this._capacite) t = texture(this.gl, this.largeur, this.hauteur);
    else {
      // éviction : la plus ancienne, jamais l'image affichée
      for (const [j, tj] of this._cache) if (j !== this.image) { this._cache.delete(j); t = tj; break; }
    }
    try { verse(this.gl, t, this.largeur, this.hauteur, f); } finally { f.close(); }
    this._cache.set(i, t);
    const v = this._veilleurs.get(i);
    if (v) { this._veilleurs.delete(i); v(); }
  }
  _envoie(i) {
    const e = this.mp4.echantillons[i];
    this._decodeur.decode(new EncodedVideoChunk({
      type: e.cle ? "key" : "delta", timestamp: Math.round(e.temps * 1e6), duration: Math.round(e.duree * 1e6),
      data: this._octets.subarray(e.decalage, e.decalage + e.taille),
    }));
    this.stats.decodes++;
  }
  _touche(n) { const t = this._cache.get(n); this._cache.delete(n); this._cache.set(n, t); }
  async _obtiens(n) {
    if (this._cache.has(n)) {
      this.stats.cache++; this._touche(n);
      // En avançant sur des images déjà en cache, le décodeur suit la tête de lecture sans
      // qu'on l'attende (un décodage par image, rattrapage depuis l'image clé au premier pas) :
      // l'image suivante hors cache ne coûtera qu'un décodage. En reculant : rien.
      if (!this._decodeurMort && this.image !== null && n > this.image && this._envoye !== n) {
        const k = this._clesAvant[n];
        const debut = (!this._besoinCle && this._envoye >= k - 1 && this._envoye < n) ? this._envoye + 1 : k;
        for (let i = debut; i <= n; i++) this._envoie(i);
        this._envoye = n; this._besoinCle = false;
      }
      return true;
    }
    if (this._decodeurMort) { try { this._decodeur.close(); } catch (e) { /* déjà fermé */ } this._creeDecodeur(); }
    const k = this._clesAvant[n];
    const debut = (!this._besoinCle && this._envoye >= k - 1 && this._envoye < n) ? this._envoye + 1 : k;
    if (debut === k) this.stats.recherches++;
    for (let i = debut; i <= n; i++) this._envoie(i);
    this._envoye = n;
    this._besoinCle = false;
    const arrive = new Promise(r => this._veilleurs.set(n, r));
    const t0 = performance.now();
    while (!this._cache.has(n)) {
      await Promise.race([arrive, dort(12)]);
      if (this._cache.has(n) || this._decodeurMort) break;
      // le décodeur garde parfois une image en réserve : on vide, et la suite repart d'une clé
      // Délai appris : 400 ms tant que le décodeur n'a jamais retenu d'image (un décodage
      // lent n'est pas une image retenue), 30 ms dès qu'un vidage a prouvé qu'il en retient.
      const delai = this._retient ? 30 : 400;
      if (this._decodeur.decodeQueueSize === 0 && performance.now() - Math.max(t0, this._derniereSortie || 0) > delai) {
        const avant = this.stats.sorties;
        try { await this._decodeur.flush(); } catch (e) { break; }
        this.stats.vidages++;
        if (this.stats.sorties > avant) this._retient = true;
        this._besoinCle = true;
        break;
      }
      if (performance.now() - t0 > 4000) break;
    }
    this._veilleurs.delete(n);
    if (this._cache.has(n)) { this._touche(n); return true; }
    return false;
  }
  detruit() {
    this._fini = true;
    try { this._decodeur.close(); } catch (e) { /* déjà fermé */ }
    for (const t of this._cache.values()) this.gl.deleteTexture(t);
    for (const t of this._libres) this.gl.deleteTexture(t);
    this._cache.clear(); this._libres = [];
  }
}

/* ------------------------------------------------------------------ repli <video> */

class LecteurBalise extends Lecteur {
  constructor(gl, mp4, url, options) {
    super(gl, mp4, options);
    this.mode = "video";
    this.codec = mp4.codec;
    this._url = url;
    this._tex = texture(gl, mp4.largeur, mp4.hauteur);
    const v = this._video = document.createElement("video");
    v.muted = true; v.playsInline = true; v.preload = "auto"; v.crossOrigin = "anonymous";
    v.src = url;
  }
  async pret() {
    const v = this._video;
    if (v.readyState < 2) await new Promise((ok, ko) => {
      v.addEventListener("loadeddata", ok, { once: true });
      v.addEventListener("error", () => ko(new Error("élément vidéo : lecture impossible")), { once: true });
    });
  }
  get texture() { return this.image === null ? null : this._tex; }
  async _obtiens(n) {
    const v = this._video, e = this.mp4.echantillons[n];
    this.stats.recherches++;
    const cherche = new Promise(r => v.addEventListener("seeked", r, { once: true }));
    v.currentTime = e.temps + e.duree / 2;   // milieu de l'image : pas d'ambiguïté d'arrondi
    await cherche;
    verse(this.gl, this._tex, this.largeur, this.hauteur, v);
    return true;
  }
  detruit() {
    this._fini = true;
    this._video.removeAttribute("src"); this._video.load();
    if (this._url.startsWith("blob:")) URL.revokeObjectURL(this._url);
    this.gl.deleteTexture(this._tex);
  }
}

/* ------------------------------------------------------------------ fabrique */

/**
 * Crée un lecteur de texture vidéo.
 * sources : une URL, ou une liste [{ url, codec? }] par ordre de préférence (AV1 avant H.264).
 * options : surImage(n) (appelé quand une nouvelle image est prête), cache (24 images),
 *           memoireMax (96 Mo de textures), forcerRepli (false).
 * Rend une promesse du lecteur, l'image 0 déjà affichée.
 */
export async function creeLecteurVideo(gl, sources, options = {}) {
  if (typeof sources === "string") sources = [{ url: sources }];
  const webcodecs = typeof VideoDecoder === "function" && !options.forcerRepli;
  const charge = async url => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`vidéo ${url} : ${r.status}`);
    return r.arrayBuffer();
  };
  let lecteur = null;
  if (webcodecs) {
    for (const s of sources) {
      try {
        if (s.codec && !(await VideoDecoder.isConfigSupported({ codec: s.codec })).supported) continue;
        const tampon = await charge(s.url);
        const mp4 = lisMp4(tampon);
        const config = { codec: mp4.codec, description: mp4.description, codedWidth: mp4.largeur, codedHeight: mp4.hauteur,
          optimizeForLatency: true, ...(mp4.espace ? { colorSpace: mp4.espace } : {}) };
        if (!(await VideoDecoder.isConfigSupported(config)).supported) continue;
        lecteur = new LecteurWebCodecs(gl, mp4, new Uint8Array(tampon), config, options);
        break;
      } catch (e) { console.warn(`lecteur vidéo : ${s.url} écarté —`, e.message); }
    }
  }
  if (!lecteur) {
    const sonde = document.createElement("video");
    const s = sources.find(x => !x.codec || sonde.canPlayType(`video/mp4; codecs="${x.codec}"`)) || sources[sources.length - 1];
    const tampon = await charge(s.url);
    const mp4 = lisMp4(tampon);
    lecteur = new LecteurBalise(gl, mp4, URL.createObjectURL(new Blob([tampon], { type: "video/mp4" })), options);
    await lecteur.pret();
  }
  await lecteur.allerImage(0);
  return lecteur;
}
