"""Cuisson du paquet publié de la page labo « Terre » (étape B).

Principe (aucun fondu d'images) : on stocke des ÉTATS CLÉS (élévation + plaque de chaque
pixel, en coordonnées paléo) et les ROTATIONS de chaque plaque à chaque Ma. Entre deux
états clés, la page fait tourner chaque pixel avec sa plaque (l'ancien vers l'avant, le
suivant vers l'arrière) : les deux champs d'élévation sont alors superposés au même
endroit, et l'on interpole l'ÉLÉVATION de deux champs co-localisés, jamais deux images.

  Segment P, 540 -> 0 Ma : PaleoDEM de Scotese & Wright 2018 (pas de 5 Ma), plaques et
    rotations du modèle PALEOMAP livré avec eux (Scotese PaleoAtlas v3). C'est le seul
    choix cohérent : les PaleoDEM ont été dessinés sur ces plaques ; les porter avec les
    rotations de Merdith les ferait glisser hors de leurs propres reconstructions.
  Segment M, 1000 -> 540 Ma : plaques et rotations de Merdith et al. 2021 (pas de 10 Ma),
    relief simplifié : le relief du PaleoDEM de 540 Ma, ramené en coordonnées actuelles par
    PALEOMAP, s'efface de 540 à 640 Ma vers un relief générique (hypothèse) ; fonds marins
    génériques (profondeur selon la distance à la croûte continentale).
  Raccord à 540 Ma : les deux modèles ne placent pas les continents au même endroit. Une
    rotation de raccord par morceau de croûte (plaque PALEOMAP × plaque Merdith) amène
    continûment les positions de Merdith (avant 580 Ma) à celles de PALEOMAP (540 Ma) ;
    l'état clé de 540 Ma du segment M est le PaleoDEM lui-même : aucun saut.

Sorties (dossier donnees/) : cles/<seg><t>.png (R = élévation codée sur 8 bits, G + 256·B =
rangée de plaque), rot-P.bin et rot-M.bin (quaternions int16, [rangée][Ma][x,y,z,w]),
manifeste.json.
"""
import json, re, glob, pathlib, time
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

T0 = time.time()
R_TERRE = 6371.0


def age_nc(f):
    """Âge (Ma) tiré du nom d'un PaleoDEM, ex. « Map88_PALEOMAP_6min_..._540Ma.nc »."""
    m = re.findall(r"(\d+(?:\.\d+)?)\s*Ma", pathlib.Path(f).name)
    if not m: raise ValueError(f"âge illisible : {f}")
    return int(round(float(m[-1])))


def log(*a):
    print(f"[cuire {time.time()-T0:7.1f} s]", *a, flush=True)


# ---------------------------------------------------------------- codage de l'élévation
H_TERRE, H_MER, G_MER = 7000.0, 9000.0, 1.5


def coder(h):
    h = np.asarray(h, np.float64)
    c = np.empty(h.shape, np.float64)
    t = h > 0
    c[t] = 128 + np.round(127 * np.sqrt(np.clip((h[t] - 10) / H_TERRE, 0, 1)))
    c[~t] = 127 - np.round(127 * np.clip((-h[~t] - 10) / H_MER, 0, 1) ** (1 / G_MER))
    return c.astype(np.uint8)


def decoder(c):
    c = np.asarray(c, np.float64)
    return np.where(c >= 128, 10 + H_TERRE * ((c - 128) / 127) ** 2,
                    -10 - H_MER * ((127 - np.minimum(c, 127)) / 127) ** G_MER)


# ---------------------------------------------------------------- géométrie
def xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz], -1)


def qconj(q):
    return q * np.array([-1, -1, -1, 1], q.dtype)


def qrot(q, v):
    u, w = q[..., :3], q[..., 3:4]
    t = 2 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def qslerp_id(q, s):
    """slerp de q (s = 0) vers l'identité (s = 1)."""
    q = np.where(q[..., 3:4] < 0, -q, q)
    ang = 2 * np.arccos(np.clip(q[..., 3], -1, 1))
    axe = q[..., :3] / np.maximum(np.linalg.norm(q[..., :3], axis=-1, keepdims=True), 1e-12)
    a2 = ang * (1 - s) / 2
    return np.concatenate([axe * np.sin(a2)[..., None], np.cos(a2)[..., None]], -1)


class Grille:
    def __init__(self, W):
        self.W, self.H = W, W // 2
        lon = -180 + (np.arange(self.W) + .5) * 360 / self.W
        lat = 90 - (np.arange(self.H) + .5) * 180 / self.H
        self.lat, self.lon = np.meshgrid(lat, lon, indexing="ij")

    def indices(self, v):
        lat = np.degrees(np.arcsin(np.clip(v[:, 2], -1, 1)))
        lon = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
        j = np.clip(((90 - lat) / 180 * self.H).astype(np.int64), 0, self.H - 1)
        i = np.clip(((lon + 180) / 360 * self.W).astype(np.int64), 0, self.W - 1)
        return j, i

    def disperser(self, v, val, fond, ordre=None, trou=2):
        """Écrit val aux pixels atteints par les points v ; comble les trous (≤ trou px)."""
        j, i = self.indices(v)
        if ordre is not None:
            j, i, val = j[ordre], i[ordre], val[ordre]
        out = np.full((self.H, self.W), fond, val.dtype); vu = np.zeros((self.H, self.W), bool)
        out[j, i] = val; vu[j, i] = True
        d, (jj, ii) = ndimage.distance_transform_edt(~vu, return_indices=True)
        # on ne bouche que les trous (fermeture morphologique) : le bord ne gonfle pas
        ferme = ndimage.binary_closing(np.pad(vu, trou, mode="wrap"), iterations=trou)[trou:-trou, trou:-trou]
        bouche = (~vu) & (d <= trou) & ferme
        out[bouche] = out[jj[bouche], ii[bouche]]
        return out, vu | bouche


def echantillonner(z, lat_src_desc, lat, lon):
    """Bilinéaire sur une grille alignée sur les nœuds : lat 90 -> -90, lon -180 -> 180."""
    ny, nx = z.shape
    y = (90 - lat) / 180 * (ny - 1); x = (lon + 180) / 360 * (nx - 1)
    return ndimage.map_coordinates(z, [y, x], order=1, mode="nearest")


# ---------------------------------------------------------------- sources
class DEM:
    def __init__(self, src, inter):
        self.fichiers = {}
        fs = [f for f in glob.glob(str(pathlib.Path(src) / "paleodem" / "**" / "*_6min_*Ma.nc"),
                                   recursive=True) if "__MACOSX" not in f] if src else []
        if fs:
            for f in fs:
                self.fichiers[age_nc(f)] = f
            self.mode = "6min"
        else:
            d = np.load(pathlib.Path(inter) / "dem1deg.npz")
            self.cube = {int(t): d["z"][k] for k, t in enumerate(d["t"])}
            self.mode = "1deg"
        self.temps = sorted(self.fichiers or self.cube)
        log(f"PaleoDEM : {len(self.temps)} états ({self.mode}), {self.temps[0]}–{self.temps[-1]} Ma")

    def __call__(self, t, grille):
        if self.mode == "6min":
            import netCDF4
            ds = netCDF4.Dataset(self.fichiers[t]); z = np.array(ds.variables["z"][:], np.float32)
            la = np.array(ds.variables[[v for v in ds.variables if v.startswith("lat")][0]][:])
            ds.close()
            if la[0] < la[-1]: z = z[::-1]
        else:
            z = self.cube[t].astype(np.float32)
        z = np.nan_to_num(z, nan=-4000.0)
        # moyenne sur la taille du pixel de sortie avant l'interpolation (pas de crénelage)
        f = (z.shape[1] - 1) / grille.W
        if f > 1.2:
            z = ndimage.uniform_filter(z, size=int(round(f)), mode="wrap")
        return echantillonner(z, None, grille.lat, grille.lon)


def bruit_spherique(v, graine=7, n=96):
    """Champ lisse isotrope sur la sphère (somme d'ondes 3D), écart-type analytique 1."""
    rng = np.random.default_rng(graine)
    k = np.exp(rng.uniform(np.log(4), np.log(90), n))
    d = rng.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    a = 1 / k; ph = rng.uniform(0, 2 * np.pi, n)
    s = np.zeros(len(v), np.float32)
    for m in range(n):
        s += (a[m] * np.sin(v @ (d[m] * k[m]) + ph[m])).astype(np.float32)
    return s / np.sqrt((a ** 2).sum() / 2)


# ---------------------------------------------------------------- cuisson
def main(src, out, inter, W=1440, pas=1, tP=None, tM=None):
    out = pathlib.Path(out); (out / "cles").mkdir(parents=True, exist_ok=True)
    inter = pathlib.Path(inter)
    g = Grille(W)
    part = np.load(inter / "partitions.npz"); rot = np.load(inter / "rotations.npz")
    dem = DEM(src, inter)

    # points actuels à 0,1° (pas > 1 pour le développement local)
    pm = part["paleomap"][::pas, ::pas].ravel().astype(np.int64)
    ms = part["merdith"][::pas, ::pas].ravel().astype(np.int64)
    mc = part["continents"][::pas, ::pas].ravel().astype(np.int64)
    ny, nx = part["paleomap"][::pas, ::pas].shape
    lat0 = 90 - (np.arange(0, 1800, pas)[:ny] + .5) / 10
    lon0 = -180 + (np.arange(0, 3600, pas)[:nx] + .5) / 10
    LA, LO = np.meshgrid(lat0, lon0, indexing="ij")
    V = xyz(LA.ravel(), LO.ravel()).astype(np.float64)
    log(f"{len(V)} points actuels ; sortie {g.W}×{g.H}")

    # ---------- segment P (PALEOMAP)
    pm_tab = np.vstack([[0, 1e4, 0], part["paleomap_table"]])
    pid2row = {int(p): r for r, p in enumerate(rot["paleomap_ids"])}
    rowP_poly = np.array([pid2row.get(int(p), 0) for p in pm_tab[:, 0]])
    QP = rot["paleomap_q"].astype(np.float64)                    # [rangée, Ma, 4]
    rowP = rowP_poly[pm]; debP, finP = pm_tab[pm, 1], pm_tab[pm, 2]
    tempsP = [t for t in dem.temps if t <= 540] if tP is None else tP
    if 540 not in tempsP: tempsP = list(tempsP) + [540]
    cles = []
    for t in tempsP:
        h = dem(t, g)
        ok = (rowP > 0) & (debP >= t) & (finP <= t)
        v = qrot(QP[rowP[ok], t], V[ok])
        rows, _ = g.disperser(v, rowP[ok].astype(np.int32), 0)
        brut = rows
        rows = combler_plaques(rows, h > -1000)
        if t == 540: h540_P, rows540_P, brut540_P = h, rows, brut
        ecrire(out / "cles" / f"P{t:04d}.png", h, rows)
        cles.append({"t": t, "seg": "P", "f": f"cles/P{t:04d}.png"})
        if t % 50 == 0: log(f"P {t} Ma : terres {(h > 0).mean()*100:.1f} % des pixels")
    ecrire_rot(out / "rot-P.bin", QP[:, :541])

    # ---------- segment M (Merdith, 1000 -> 540 Ma, raccord 580 -> 540 Ma)
    # Pas d'états clés ici : un seul nuage de points en coordonnées ACTUELLES (la grille de
    # sortie, pixel = morceau de croûte), chacun avec sa rangée de rotation et de quoi
    # calculer son élévation à tout instant. La page le transporte d'un bloc : les mêmes
    # points d'un instant à l'autre, rien à recaler, aucun mélange de deux états.
    #   type a : pixels du PaleoDEM de 540 Ma au-dessus de -1000 m, ramenés au présent par
    #            leur plaque PALEOMAP (comblée au plus proche) ; h0 = leur élévation ;
    #   type b : croûte continentale de Merdith que (a) ne recouvre pas ; h0 = -150 m.
    #   h(t) = (1-a) h0 + a cible, a = lissé((t-540)/100) ; cible = relief générique si la
    #   croûte existe à t (Merdith), sinon -3000 m (le morceau s'enfonce et disparaît).
    me_ids = rot["merdith_ids"]; QM = lisser_sauts(rot["merdith_q"].astype(np.float64), me_ids)
    mid2row = {int(p): r for r, p in enumerate(me_ids)}
    ms_tab = np.vstack([[0, 1e4, 0], part["merdith_table"]])
    mc_tab = np.vstack([[0, 0, 0], part["continents_table"]])
    croute = mc > 0
    pidM = np.where(croute, mc_tab[mc, 0], ms_tab[ms, 0])
    uniq, invi = np.unique(pidM.astype(np.int64), return_inverse=True)
    rowM = np.array([mid2row.get(int(u), 0) for u in uniq], np.int64)[invi]
    debC = mc_tab[mc, 1]
    vP540 = (rowP > 0) & (debP >= 540) & (finP <= 540)

    gv = xyz(g.lat.ravel(), g.lon.ravel())                         # grille de sortie
    jj = np.clip(((90 - g.lat.ravel()) * 10 / pas).astype(np.int64), 0, ny - 1)
    ii = np.clip(((g.lon.ravel() + 180) * 10 / pas).astype(np.int64), 0, nx - 1)
    cel = jj * nx + ii                                               # cellule 0,1° du pixel actuel
    crC, debCC, rowMC = croute[cel], debC[cel], rowM[cel]

    h540, rows540 = h540_P, rows540_P
    # 1) pixels actuels sur une plaque PALEOMAP de 540 Ma : leur élévation est lue au point
    #    où leur plaque les place à 540 Ma (lecture inverse, sans hachures) ;
    # 2) terres du PaleoDEM hors de tout polygone PALEOMAP : rattachées à la plaque la plus
    #    proche, ramenées au présent par elle.
    rowPC = np.where(vP540, rowP, 0)[cel]
    h0 = np.full(g.H * g.W, np.nan); rP = np.zeros(g.H * g.W, np.int64)
    ok1 = rowPC > 0
    p = qrot(QP[rowPC[ok1], 540], gv[ok1])
    jx, ix = g.indices(p)
    hv = h540[jx, ix]
    garde = hv > -1000
    idx = np.where(ok1)[0][garde]
    h0[idx] = hv[garde]; rP[idx] = rowPC[ok1][garde]
    hors = (brut540_P == 0) & (h540 > -1000) & (rows540 > 0)
    for r in np.unique(rows540[hors]):
        libre = np.isnan(h0)
        jx, ix = g.indices(qrot(np.broadcast_to(QP[r, 540], (int(libre.sum()), 4)), gv[libre]))
        m = (rows540[jx, ix] == r) & hors[jx, ix]
        k = np.where(libre)[0][m]
        h0[k] = h540[jx[m], ix[m]]; rP[k] = r
    vuA = ~np.isnan(h0)
    typB = crC & ~vuA
    pts = vuA | typB
    log(f"segment M : {int(vuA.sum())} points du PaleoDEM de 540 Ma, {int(typB.sum())} de croûte seule")

    cle_paire = np.where(vuA, rP, 0) * 100000 + rowMC
    paires, inv = np.unique(cle_paire[pts], return_inverse=True)
    rowH = np.zeros(g.H * g.W, np.int64); rowH[pts] = inv + 1; nH = len(paires) + 1
    pp, mm = paires // 100000, paires % 100000
    compte = np.bincount(inv, minlength=len(paires))
    ppx = pp.copy()
    for m in np.unique(mm[pp == 0]):
        kk = np.where((mm == m) & (pp > 0))[0]
        if len(kk): ppx[(mm == m) & (pp == 0)] = pp[kk[np.argmax(compte[kk])]]
    log(f"raccord : {nH-1} morceaux ; {int(((pp == 0) & (ppx > 0)).sum())} rattachés, "
        f"{int((ppx == 0).sum())} sans correspondant PALEOMAP")
    TM = np.arange(540, 1001)
    QH = np.zeros((nH, len(TM), 4)); QH[0, :, 3] = 1
    C = qmul(QP[ppx, 540], qconj(QM[mm, 540]))                     # Merdith-540 -> PALEOMAP-540
    for k, t in enumerate(TM):
        s = np.clip((t - 540) / 40.0, 0, 1); s = s * s * (3 - 2 * s)
        q = qmul(qslerp_id(C, s), QM[mm, t])
        QH[1:, k] = np.where((ppx == 0)[:, None], QM[mm, t], q)
    ecrire_rot(out / "rot-M.bin", QH)

    # relief générique (hypothèse) aux points de croûte
    cr2 = croute.reshape(ny, nx)
    bord = cr2 & ~ndimage.binary_erosion(cr2, iterations=1)
    arbre = cKDTree(V[bord.ravel()])
    hgen = np.full(g.H * g.W, -3000.0)
    d = arbre.query(gv[crC], workers=-1)[0] * R_TERRE
    nz = bruit_spherique(gv[crC])
    hgen[crC] = -120 + 560 * (1 - np.exp(-d / 300)) + 280 * nz * (1 - np.exp(-d / 150))
    log(f"relief générique : médiane {np.median(hgen[crC]):.0f} m")

    # images : M-points-1 (R = h0, G = relief générique, B = drapeaux), M-points-2 (rangée,
    # début de la croûte en pas de 4 Ma)
    h0c = np.where(vuA, h0, -150.0)
    drap = (vuA * 1 + crC * 2 + pts * 4).astype(np.uint8)
    deb = np.clip(np.round(np.minimum(debCC, 1020) / 4), 0, 255).astype(np.uint8)
    im1 = np.stack([coder(h0c), coder(hgen), drap], -1).reshape(g.H, g.W, 3)
    im2 = np.stack([(rowH & 255).astype(np.uint8), (rowH >> 8).astype(np.uint8), deb], -1).reshape(g.H, g.W, 3)
    Image.fromarray(im1, "RGB").save(out / "M-points-1.png", optimize=True)
    Image.fromarray(im2, "RGB").save(out / "M-points-2.png", optimize=True)

    # contrôle de la cuisson : surface émergée du nuage à quelques instants (sphère)
    w = np.cos(np.radians(g.lat.ravel()))
    for t in (540, 545, 550, 560, 600, 700, 1000):
        a = np.clip((t - 540) / 100.0, 0, 1); a = a * a * (3 - 2 * a)
        viv = crC & (debCC >= t)
        h = np.where(vuA, (1 - a) * h0c + a * np.where(viv, hgen, -3000.0), (1 - a) * -150 + a * hgen)
        ex = pts & np.where(vuA, viv | (a < 0.999), viv)
        log(f"M {t} Ma : terres {(w * (ex & (h > 0))).sum() / w.sum() * 100:.1f} % de la sphère")

    bm = preparer_blue_marble(src, out, inter)
    man = {
        "W": g.W, "H": g.H, "surface": bm,
        "codage": {"terre": [H_TERRE], "mer": [H_MER, G_MER]},
        "segments": {"P": {"t0": 0, "t1": 540, "rot": "rot-P.bin", "rangees": int(QP.shape[0]), "cols": 541},
                     "M": {"t0": 540, "t1": 1000, "rot": "rot-M.bin", "rangees": int(nH), "cols": len(TM),
                           "points": ["M-points-1.png", "M-points-2.png"], "fond": "cles/P0540.png",
                           "pasDebut": 4, "raccord": [540, 580], "effacement": [540, 640]}},
        "cles": cles,
        "sources": ["Scotese & Wright 2018, PALEOMAP PaleoDEMs, Zenodo 5460860",
                    "Scotese 2016, PALEOMAP Global Plate Model (PaleoAtlas v3), Zenodo 5460860",
                    "Merdith et al. 2021, Earth-Science Reviews 214, 103477, Zenodo 13635864 (v1.2.4)"],
    }
    (out / "manifeste.json").write_text(json.dumps(man, ensure_ascii=False, indent=0))
    taille = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    log(f"paquet : {len(cles)} états clés, {taille/1e6:.1f} Mo")


def preparer_blue_marble(src, out, inter):
    """Surface d'aujourd'hui (BMNG juin 2004) en coordonnées actuelles : texture de la page
    (1440 × 720, JPEG) et référence des contrôles (720 × 360, PNG sans perte)."""
    cands = [pathlib.Path(src) / "bmng" / "world.200406.3x5400x2700.jpg"] if src else []
    cands.append(pathlib.Path(inter).parent.parent / "controles" / "blue-marble-juin-2004.png")
    for f in cands:
        if f.exists():
            im = Image.open(f).convert("RGB")
            if f.suffix == ".jpg":
                im.resize((720, 360), Image.BOX).save(cands[-1], optimize=True)
            im.resize((1440, 720), Image.LANCZOS).save(out / "surface-juin.jpg", quality=88, optimize=True)
            log(f"Blue Marble : {f.name} -> surface-juin.jpg")
            return "surface-juin.jpg"
    log("Blue Marble absent")
    return None


def lisser_sauts(Q, ids, seuil=15.0, demi=5):
    """Sauts de plus de `seuil` degrés en 1 Ma dans un modèle publié (raccords de rotation
    non synchronisés : Merdith v1.2.4 en montre à 610 Ma) : étalés en rotation continue
    sur ± `demi` Ma, pour que les continents ne se téléportent pas."""
    Q = Q.copy()
    d = np.abs((Q[:, 1:] * Q[:, :-1]).sum(-1)); ang = 2 * np.degrees(np.arccos(np.clip(d, 0, 1)))
    for r, t in np.argwhere(ang > seuil):
        t0, t1 = max(t - demi, 0), min(t + 1 + demi, Q.shape[1] - 1)
        a, b = Q[r, t0], Q[r, t1]
        if np.dot(a, b) < 0: b = -b
        om = np.arccos(np.clip(np.dot(a, b), -1, 1))
        for k in range(t0 + 1, t1):
            f = (k - t0) / (t1 - t0)
            q = (np.sin((1 - f) * om) * a + np.sin(f * om) * b) / np.sin(om) if om > 1e-6 else a
            Q[r, k] = q / np.linalg.norm(q)
    n = int((ang > seuil).sum())
    if n: log(f"sauts de rotation > {seuil}°/Ma lissés : {n} (plaques {sorted(set(ids[np.argwhere(ang > seuil)[:, 0]].tolist()))[:12]}…, "
              f"vers {sorted(set((np.argwhere(ang > seuil)[:, 1]).tolist()))[:6]} Ma)")
    return Q


def lon_wrap(lo):
    return (lo + 180) % 360 - 180


def combler_plaques(rows, masque):
    """Terres et plateaux du PaleoDEM hors de tout polygone de plaque : rattachés à la plaque
    la plus proche, pour qu'ils voyagent avec leurs voisins au lieu de rester immobiles."""
    vide = (rows == 0) & masque
    if not vide.any() or not (rows > 0).any(): return rows
    _, (jj, ii) = ndimage.distance_transform_edt(rows == 0, return_indices=True)
    out = rows.copy(); out[vide] = rows[jj[vide], ii[vide]]
    return out


def dem_brut(dem, t):
    if dem.mode == "6min":
        import netCDF4
        ds = netCDF4.Dataset(dem.fichiers[t]); z = np.array(ds.variables["z"][:], np.float32)
        la = np.array(ds.variables[[v for v in ds.variables if v.startswith("lat")][0]][:]); ds.close()
        if la[0] < la[-1]: z = z[::-1]
    else:
        z = dem.cube[t].astype(np.float32)
    return np.nan_to_num(z, nan=-4000.0)


def ecrire(chemin, h, rows):
    rgb = np.stack([coder(h), (rows & 255).astype(np.uint8), (rows >> 8).astype(np.uint8)], -1)
    Image.fromarray(rgb, "RGB").save(chemin, optimize=True)


def ecrire_rot(chemin, Q):
    Q = np.where(Q[..., 3:4] < 0, -Q, Q)                       # w ≥ 0 : continuité de l'interpolation
    np.round(np.clip(Q, -1, 1) * 32767).astype("<i2").tofile(chemin)
