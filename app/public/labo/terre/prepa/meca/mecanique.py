"""Mécanique des roches du chantier S3b (D-49) : la croûte continentale de 1,8 Ga à 540 Ma.

Modèle (grossier par choix : ~50 km, pas de 2 Ma ; hypothèses signalées) :
  1. Plaques : Cao et al. 2024 (Geoscience Frontiers 15, 101922). Chaque morceau de croûte
     continentale est un point en coordonnées ACTUELLES (pixel de la grille de la page), porté
     par la rotation de sa plaque. Les frontières topologiques résolues donnent la plaque de
     tout point du globe (océans compris) tous les 2 Ma.
  2. Lithosphère en couche mince visqueuse (champ pondéré par la croûte, couplage 0,05 des
     marges actives ; racines épaissies relaxées vers 38 km en ~80 Ma, hypothèse) : le champ de vitesse des plaques, imposé, est lissé
     sur ~600 km (largeur des zones de déformation, nombre d'Argand ~ 1–3) ; la croûte s'épaissit
     là où ce champ converge (dH/dt = -H div v) et s'amincit là où il diverge (rifts, marges).
     L'étalement gravitaire de la croûte épaisse (viscosité non linéaire) est une diffusion
     de l'épaisseur dont le coefficient croît avec l'épaisseur ; épaisseur bornée à 80 km.
  3. Relief par isostasie d'Airy : e = (1 - ρc/ρm)(H - H0) = 0,15 (H - 35,5 km).
  4. Érosion : loi de puissance du courant (algorithme FastScape, Braun & Willett 2013 :
     routage au plus raide après comblement des cuvettes, aire drainée, schéma implicite),
     sur une grille HEALPix (nside 128) ; la roue pip de fastscapelib n'a pas la grille
     HEALPix, l'algorithme est donc réécrit ici (numba). Niveau marin fixe (0 m) : base des
     rivières. Le rebond isostatique suit : enlever δ de roche abaisse la surface de 0,15 δ.
  5. Raccord à 540 Ma : la page fond le relief mécanique dans le PaleoDEM de 540 Ma de 640 à
     540 Ma (élévations co-localisées d'un même morceau de croûte, jamais deux images).

Sorties (dossier donnees/) : C-points-1.png, C-points-2.png (points, comme l'ancien segment
M), C-h-NN.png (élévation mécanique de chaque point, 3 instants par image, tous les 10 Ma),
rot-C.bin (rotations des morceaux, raccord Cao -> PALEOMAP), manifeste.json mis à jour,
diagnostic-mecanique.json.

Usage : python3 mecanique.py <sources> <intermédiaires lourds> <donnees>
"""
import sys, json, pathlib, time
import numpy as np
import healpy as hp
from numba import njit
from PIL import Image
from scipy import ndimage

ICI = pathlib.Path(__file__).resolve().parent
PREPA = ICI.parent; TERRE = PREPA.parent
sys.path.insert(0, str(PREPA))
import cuire
from cuire import xyz, qmul, qconj, qrot, qslerp_id, coder, decoder, Grille, ecrire_rot, lisser_sauts, bruit_spherique

SRC, INTER_L, OUT = (pathlib.Path(a) for a in sys.argv[1:4])
T0 = time.time()
R_KM = 6371.0
import os
T_HAUT, T_BAS, DT, PAS_CLE = int(os.environ.get("MECA_T_HAUT", 1800)), 540, 2, 10
H0, ISO = 35.5, 150.0                     # km ; m d'élévation par km d'épaisseur
NV, NE = 64, 128                          # nside : vitesses, érosion
LISSAGE = np.radians(5.0)                 # largeur à mi-hauteur du lissage des vitesses
K_SPL, M_SPL = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0e-7, 0.4
KAPPA = 1500.0                            # km²/Ma, étalement de la croûte épaisse
H_MAX, H_MIN = 75.0, 20.0                 # km : plateau du Tibet ; croûte amincie des rifts
V_MAX = 200.0                             # km/Ma (20 cm/an)
COUPLAGE = 0.05
TAU_RACINE, H_REF = 80.0, 38.0          # Ma, km : effondrement et délamination des racines (hypothèse)
AIRE_V = 4 * np.pi * R_KM ** 2 / hp.nside2npix(NV)


def log(*a): print(f"[méca {time.time()-T0:7.1f} s]", *a, flush=True)


# ---------------------------------------------------------------- érosion FastScape (HEALPix)
@njit(cache=True)
def _tas_push(hz, hi, n, z, i):
    k = n; hz[k] = z; hi[k] = i
    while k > 0:
        p = (k - 1) // 2
        if hz[p] <= hz[k]: break
        hz[p], hz[k] = hz[k], hz[p]; hi[p], hi[k] = hi[k], hi[p]; k = p
    return n + 1


@njit(cache=True)
def _tas_pop(hz, hi, n):
    z, i = hz[0], hi[0]; n -= 1
    hz[0] = hz[n]; hi[0] = hi[n]; k = 0
    while True:
        l = 2 * k + 1; r = l + 1; m = k
        if l < n and hz[l] < hz[m]: m = l
        if r < n and hz[r] < hz[m]: m = r
        if m == k: break
        hz[m], hz[k] = hz[k], hz[m]; hi[m], hi[k] = hi[k], hi[m]; k = m
    return z, i, n


@njit(cache=True)
def spl(h, fixe, voisins, dist, aire, K, m, dt):
    """Un pas implicite de la loi de puissance (n = 1). h en m, dist en m, aire en m², dt en
    années. Renvoie l'épaisseur de roche enlevée (m, ≥ 0)."""
    n = h.size
    hf = h.copy(); ferme = fixe.copy()
    hz = np.empty(n + 8 * n, np.float64); hi = np.empty(n + 8 * n, np.int64); nt = 0
    for i in range(n):
        if fixe[i]: nt = _tas_push(hz, hi, nt, hf[i], i)
    ordre = np.empty(n, np.int64); k = 0
    while nt > 0:
        z, i, nt = _tas_pop(hz, hi, nt)
        ordre[k] = i; k += 1
        for a in range(voisins.shape[1]):
            j = voisins[i, a]
            if j < 0 or ferme[j]: continue
            ferme[j] = True
            if hf[j] <= hf[i]: hf[j] = hf[i] + 1e-2
            nt = _tas_push(hz, hi, nt, hf[j], j)
    rec = np.arange(n); drec = np.ones(n)
    for i in range(n):
        if fixe[i]: continue
        best = 0.0
        for a in range(voisins.shape[1]):
            j = voisins[i, a]
            if j < 0: continue
            s = (hf[i] - hf[j]) / dist[i, a]
            if s > best: best = s; rec[i] = j; drec[i] = dist[i, a]
    A = aire.copy()
    for q in range(k - 1, -1, -1):
        i = ordre[q]
        if rec[i] != i: A[rec[i]] += A[i]
    hn = h.copy()
    for q in range(k):
        i = ordre[q]
        if fixe[i] or rec[i] == i: continue
        r = rec[i]
        if h[i] <= hn[r]: continue                 # fond de cuvette : rien n'est enlevé
        F = K * dt * A[i] ** m / drec[i]
        hn[i] = (h[i] + F * hn[r]) / (1.0 + F)
    return h - hn


@njit(cache=True)
def etaler(H, cont, voisins, dist_km, kappa, dt, hseuil, sous):
    """Étalement gravitaire : diffusion de l'épaisseur entre cellules continentales, coefficient
    kappa·((H-hseuil)/25)² borné à kappa ; flux nul vers l'océan (masse conservée)."""
    n = H.size; H = H.copy(); d = dt / sous
    for s in range(sous):
        dH = np.zeros(n)
        for i in range(n):
            if not cont[i]: continue
            for a in range(voisins.shape[1]):
                j = voisins[i, a]
                if j < 0 or j < i or not cont[j]: continue
                hm = 0.5 * (H[i] + H[j]) - hseuil
                if hm <= 0: continue
                kap = kappa * min(1.0, (hm / 25.0) ** 2)
                q = kap * (H[i] - H[j]) / (dist_km[i, a] ** 2) * d / 4.0
                dH[i] -= q; dH[j] += q
        H += dH
    return H


def geometrie(nside):
    n = hp.nside2npix(nside); P = np.array(hp.pix2vec(nside, np.arange(n))).T
    vois = hp.get_all_neighbours(nside, np.arange(n)).T.astype(np.int64)        # (n, 8)
    Pj = P[np.clip(vois, 0, None)]
    d = np.arccos(np.clip((Pj * P[:, None]).sum(-1), -1, 1)) * R_KM
    d[vois < 0] = 1.0
    return P, vois, d


def operateur_divergence(P, vois):
    """Moindres carrés sur les 8 voisins : div v = trace du gradient tangent."""
    e1 = np.cross([0, 0, 1.0], P); e1[np.linalg.norm(e1, axis=1) < 1e-9] = [1, 0, 0]
    e1 /= np.linalg.norm(e1, axis=1, keepdims=True); e2 = np.cross(P, e1)
    Pj = P[np.clip(vois, 0, None)] - P[:, None]
    A = np.stack([(Pj * e1[:, None]).sum(-1), (Pj * e2[:, None]).sum(-1)], -1) * R_KM   # (n, 8, 2)
    A[vois < 0] = 0
    Mp = np.linalg.solve(np.einsum("nki,nkj->nij", A, A), np.transpose(A, (0, 2, 1)))  # (n, 2, 8)
    return e1, e2, Mp


def divergence(v, vois, e1, e2, Mp):
    dv = v[np.clip(vois, 0, None)] - v[:, None]
    B = np.stack([(dv * e1[:, None]).sum(-1), (dv * e2[:, None]).sum(-1)], -1)
    B[vois < 0] = 0
    G = np.einsum("nik,nkj->nij", Mp, B)
    return G[:, 0, 0] + G[:, 1, 1]          # 1/Ma


def main():
    g = Grille(1440); N = g.H * g.W
    cao = np.load(INTER_L / "cao.npz"); topo = np.load(INTER_L / "topo.npz")
    ids = cao["ids"]; id2row = {int(p): r for r, p in enumerate(ids)}
    # sauts de plus de 4°/Ma (≈ 45 cm/an, deux fois la plaque la plus rapide connue) : raccords
    # de fichiers de rotation (1000 Ma) ou de plaques, étalés en rotation continue
    QC = lisser_sauts(cao["q"].astype(np.float64), ids, seuil=4.0, demi=4)       # [rangée, Ma, 4]
    st, st_t = cao["statiques"].ravel().astype(np.int64), np.vstack([[0, 1e4, 0], cao["statiques_table"]])
    co = cao["continents"].ravel().astype(np.int64)
    co_t = np.vstack([np.zeros((1, 3)), cao["continents_table"].reshape(-1, 3)])
    gv = xyz(g.lat.ravel(), g.lon.ravel())
    croute = co > 0
    if croute.mean() < 0.05:                           # pas de polygones continentaux lisibles
        log("polygones continentaux absents : croûte = terres et plateaux actuels (PaleoDEM 0 Ma > -1000 m)")
        h_now = decoder(np.asarray(Image.open(TERRE / "donnees" / "cles" / "P0000.png"))[..., 0]).ravel()
        croute = h_now > -1000
    pid = np.where(co > 0, co_t[co, 0], st_t[st, 0]).astype(np.int64)
    debut = np.where(co > 0, co_t[co, 1], st_t[st, 1])
    rows = np.array([id2row.get(int(p), 0) for p in pid])
    croute &= rows > 0
    log(f"croûte continentale : {croute.mean()*100:.1f} % des pixels actuels ; plaques {len(set(pid[croute]))}")

    I = np.where(croute)[0]; V0 = gv[I]; rI = rows[I]; debI = debut[I]
    w_aire = np.cos(np.radians(g.lat.ravel()[I])) * (np.radians(0.25) * R_KM) ** 2   # km²
    nz = bruit_spherique(V0)

    # épaisseur initiale (hypothèse) : intérieurs à 38 km, marges amincies à 30 km
    vivant0 = debI >= T_HAUT
    m2 = np.zeros(N, bool); m2[I[vivant0]] = True; m2 = m2.reshape(g.H, g.W)
    rr = np.zeros(N, np.int64); rr[I] = rI; rr = rr.reshape(g.H, g.W)
    bord = m2 & ~ndimage.binary_erosion(m2, iterations=1)
    for ax in (0, 1):
        bord |= m2 & (np.roll(rr, 1, ax) != rr) & np.roll(m2, 1, ax)
    dist = ndimage.distance_transform_edt(~bord) * 0.25 * 111.0
    dist = dist.ravel()[I]
    Hc = np.where(vivant0, 30.0 + 8.0 * (1 - np.exp(-dist / 150.0)) + 1.0 * nz, np.nan)

    PV, voisV, _ = geometrie(NV); e1, e2, Mp = operateur_divergence(PV, voisV)
    PE, voisE, dE = geometrie(NE); aireE = np.full(len(PE), 4 * np.pi * (R_KM * 1e3) ** 2 / len(PE))
    tt_topo = topo["t"]; gt = topo["g"]
    latV = np.degrees(np.arcsin(PV[:, 2])); lonV = np.degrees(np.arctan2(PV[:, 1], PV[:, 0]))
    jV = np.clip(((90 - latV) / 180 * gt.shape[1]).astype(int), 0, gt.shape[1] - 1)
    iV = np.clip(((lonV + 180) / 360 * gt.shape[2]).astype(int), 0, gt.shape[2] - 1)
    lut = np.zeros(int(max(ids.max(), gt.max())) + 1, np.int64)
    for p, r in id2row.items():
        if p < len(lut): lut[p] = r
    inconnus = sorted(set(np.unique(gt[::25]).tolist()) - set(int(x) for x in ids))
    log(f"plaques des topologies sans rotation : {inconnus[:20]} ({len(inconnus)})")

    cles = {}; diag = []
    for t in range(T_HAUT, T_BAS - 1, -DT):
        vivant = debI >= t
        neuf = vivant & np.isnan(Hc)
        Hc[neuf] = 31.0 + 1.0 * nz[neuf]                     # croûte juvénile (arcs) : hypothèse
        Hc[~vivant] = np.nan
        a = np.where(vivant)[0]
        pos = qrot(QC[rI[a], t], V0[a])
        # vitesses des plaques (km/Ma) aux nœuds HEALPix, d'après les frontières résolues
        k = int(np.argmin(np.abs(tt_topo - t)))
        rv = lut[gt[k, jV, iV]]
        x0 = qrot(qconj(QC[rv, t]), PV)
        v = (qrot(QC[rv, t - 1], x0) - PV) * R_KM / 1.0
        v[rv == 0] = 0
        nv = np.linalg.norm(v, axis=1, keepdims=True); v *= np.minimum(1, V_MAX / np.maximum(nv, 1e-9))
        # couche mince : la croûte continentale, légère, ne plonge pas ; c'est elle qui se
        # raccourcit. Le champ lissé est une moyenne pondérée par la croûte présente (poids 1)
        # et l'océan (poids COUPLAGE : couplage d'une marge active, type Andes) : deux continents
        # qui se rapprochent convergent ; une plaque océanique qui plonge raccourcit peu sa voisine.
        pxv = hp.vec2pix(NV, pos[:, 0], pos[:, 1], pos[:, 2])
        fc = np.minimum(np.bincount(pxv, weights=w_aire[a], minlength=len(PV)) / AIRE_V, 1.0)
        poids = fc + COUPLAGE * (1 - fc)
        den = hp.smoothing(poids, fwhm=LISSAGE, iter=1)
        vs = np.stack([hp.smoothing(poids * v[:, c], fwhm=LISSAGE, iter=1) for c in range(3)], -1) / np.maximum(den, 1e-3)[:, None]
        vs -= (vs * PV).sum(-1, keepdims=True) * PV
        div = divergence(vs, voisV, e1, e2, Mp)
        th, ph = hp.vec2ang(pos)
        dv = hp.get_interp_val(div, th, ph)
        Hc[a] = np.clip(Hc[a] * np.exp(np.clip(-dv * DT, -0.3, 0.3)), H_MIN, H_MAX)
        # les racines des chaînes ne durent pas : effondrement gravitaire, fluage de la croûte
        # inférieure, délamination — la croûte épaissie revient vers 38 km en ~80 Ma
        ep = Hc[a] > H_REF
        Hc[a[ep]] = H_REF + (Hc[a[ep]] - H_REF) * np.exp(-DT / TAU_RACINE)
        # érosion et étalement sur la grille HEALPix fine
        px = hp.ang2pix(NE, th, ph)
        sa = np.bincount(px, weights=w_aire[a], minlength=len(PE))
        Hp = np.bincount(px, weights=w_aire[a] * Hc[a], minlength=len(PE)) / np.maximum(sa, 1e-9)
        cont = sa > 0.3 * aireE / 1e6
        Hs = etaler(np.where(cont, Hp, 0.0), cont, voisE, dE, KAPPA, float(DT), 40.0, 8)
        e = np.where(cont, ISO * (Hs - H0), -4000.0)
        fixe = ~cont | (e <= 0)
        delta = spl(e, fixe, voisE, dE * 1e3, aireE, K_SPL, M_SPL, DT * 1e6)
        Hn = np.clip(Hs - delta / 1e3, H_MIN, H_MAX)
        f = np.where(cont & (Hp > 0), Hn / np.maximum(Hp, 1e-6), 1.0)
        Hc[a] *= f[px]
        if (t - T_BAS) % PAS_CLE == 0:
            el = np.full(len(I), np.nan); el[a] = ISO * (Hc[a] - H0)
            cles[t] = el.astype(np.float32)
            ww = w_aire[a]; ea = el[a]
            d_ = {"t": t, "terres_pct_globe": float(ww[ea > 0].sum() / (4 * np.pi * R_KM ** 2) * 100),
                  "croute_pct_globe": float(ww.sum() / (4 * np.pi * R_KM ** 2) * 100),
                  "sup2000_Mkm2": float(ww[ea > 2000].sum() / 1e6), "max_m": float(np.nanmax(ea)),
                  "H_max_km": float(np.nanmax(Hc[a])), "erosion_max_m_par_Ma": float(delta.max() / DT),
                  "v_max_km_Ma": float(np.linalg.norm(v, axis=1).max())}
            diag.append(d_)
            if t % 50 == 0: log(json.dumps(d_, ensure_ascii=False))

    # ---------------------------------------------------------------- paquet de la page
    ecrire_paquet(g, N, I, rI, debI, croute, ids, QC, cles, nz)
    (OUT / "diagnostic-mecanique.json").write_text(json.dumps(
        {"parametres": {"K_spl": K_SPL, "m": M_SPL, "kappa_km2_Ma": KAPPA, "lissage_deg": 5.0, "H0_km": H0,
                        "iso_m_par_km": ISO, "dt_Ma": DT}, "instants": diag}, ensure_ascii=False, indent=0))
    log("fin")


def ecrire_paquet(g, N, I, rI, debI, croute, ids, QC, cles, nz):
    """Points (comme l'ancien segment M de cuire.py), rotations de raccord Cao -> PALEOMAP,
    élévations mécaniques par instant clé."""
    part = np.load(PREPA / "intermediaires" / "partitions.npz"); rot = np.load(PREPA / "intermediaires" / "rotations.npz")
    pm = part["paleomap"].ravel().astype(np.int64); ny, nx = part["paleomap"].shape
    pm_tab = np.vstack([[0, 1e4, 0], part["paleomap_table"]])
    pid2row = {int(p): r for r, p in enumerate(rot["paleomap_ids"])}
    rowP_poly = np.array([pid2row.get(int(p), 0) for p in pm_tab[:, 0]])
    QP = rot["paleomap_q"].astype(np.float64)
    rowP = rowP_poly[pm]; debP, finP = pm_tab[pm, 1], pm_tab[pm, 2]
    gv = xyz(g.lat.ravel(), g.lon.ravel())
    jj = np.clip(((90 - g.lat.ravel()) * 10).astype(np.int64), 0, ny - 1)
    ii = np.clip(((g.lon.ravel() + 180) * 10).astype(np.int64), 0, nx - 1)
    cel = jj * nx + ii
    vP540 = ((rowP > 0) & (debP >= 540) & (finP <= 540))
    rowPC = np.where(vP540, rowP, 0)[cel]
    cle540 = np.asarray(Image.open(TERRE / "donnees" / "cles" / "P0540.png")).astype(np.int64)
    h540 = decoder(cle540[..., 0])
    # type a : pixels actuels portés par PALEOMAP à 540 Ma sur du PaleoDEM > -1000 m
    h0 = np.full(N, np.nan); rP = np.zeros(N, np.int64)
    ok1 = rowPC > 0
    jx, ix = g.indices(qrot(QP[rowPC[ok1], 540], gv[ok1]))
    hv = h540[jx, ix]; garde = hv > -1000
    idx = np.where(ok1)[0][garde]; h0[idx] = hv[garde]; rP[idx] = rowPC[ok1][garde]
    vuA = ~np.isnan(h0)
    rowC = np.zeros(N, np.int64); rowC[I] = rI
    typB = croute & ~vuA
    pts = vuA | typB
    # rangée Cao des points de type a hors croûte Cao : statique Cao (déjà dans rI si croûte) ;
    # sinon, la plaque Cao la plus proche parmi la croûte
    sans = pts & (rowC == 0)
    if sans.any():
        from scipy.spatial import cKDTree
        arbre = cKDTree(gv[I]); _, k = arbre.query(gv[sans], workers=-1); rowC[sans] = rI[k]
    log(f"paquet : {int(vuA.sum())} points du PaleoDEM de 540 Ma, {int(typB.sum())} de croûte seule")
    cle_paire = np.where(vuA, rP, 0) * 100000 + rowC
    paires, inv = np.unique(cle_paire[pts], return_inverse=True)
    rowH = np.zeros(N, np.int64); rowH[pts] = inv + 1; nH = len(paires) + 1
    pp, mm = paires // 100000, paires % 100000
    compte = np.bincount(inv, minlength=len(paires)); ppx = pp.copy()
    for m_ in np.unique(mm[pp == 0]):
        kk = np.where((mm == m_) & (pp > 0))[0]
        if len(kk): ppx[(mm == m_) & (pp == 0)] = pp[kk[np.argmax(compte[kk])]]
    PAS_ROT = 2
    TM = np.arange(540, T_HAUT + 1, PAS_ROT)
    QH = np.zeros((nH, len(TM), 4)); QH[0, :, 3] = 1
    C = qmul(QP[ppx, 540], qconj(QC[mm, 540]))
    for k, t in enumerate(TM):
        s = np.clip((t - 540) / 80.0, 0, 1); s = s * s * (3 - 2 * s)
        QH[1:, k] = np.where((ppx == 0)[:, None], QC[mm, t], qmul(qslerp_id(C, s), QC[mm, t]))
    ecrire_rot(OUT / "rot-C.bin", QH)
    # élévations mécaniques aux points (type a hors croûte Cao : relief de 540 Ma maintenu, hypothèse)
    ts = sorted(cles)
    # avant sa naissance, un morceau garde l'élévation qu'il aura en naissant : l'interpolation
    # entre deux instants clés reste continue, la page le fait apparaître par son poids (début)
    for k in range(1, len(ts)):
        prec, cur = cles[ts[k - 1]], cles[ts[k]]
        m_ = np.isnan(cur) & ~np.isnan(prec); cur[m_] = prec[m_]
    bz = bruit_spherique(gv[pts], graine=11)
    imgs = []
    for t in ts:
        el = np.full(N, np.nan); el[I] = cles[t]
        el = np.where(np.isnan(el) & vuA & (rowC > 0) & ~croute, np.where(np.isnan(h0), -3000, h0), el)
        el = np.where(np.isnan(el), -9000.0, el)
        e_pts = el[pts]
        e_pts = np.where(e_pts > -8000, e_pts + bz * (40 + 0.22 * np.maximum(e_pts, 0)), e_pts)
        el[pts] = e_pts
        imgs.append(coder(el).reshape(g.H, g.W))
    fichiers = []
    for k in range(0, len(imgs), 3):
        trio = imgs[k:k + 3] + [np.zeros_like(imgs[0])] * (3 - len(imgs[k:k + 3]))
        nom = f"C-h-{k // 3:02d}.png"; fichiers.append(nom)
        Image.fromarray(np.stack(trio, -1), "RGB").save(OUT / nom, optimize=True)
    drap = (vuA * 1 + croute * 2 + pts * 4).astype(np.uint8)
    debC = np.full(N, 0.0); debC[I] = debI
    deb = np.clip(np.round(np.minimum(np.where(croute, debC, 1e4), 2040) / 8), 0, 255).astype(np.uint8)
    h0c = np.where(vuA, h0, -150.0)
    im1 = np.stack([coder(h0c), np.zeros(N, np.uint8), drap], -1).reshape(g.H, g.W, 3)
    im2 = np.stack([(rowH & 255).astype(np.uint8), (rowH >> 8).astype(np.uint8), deb], -1).reshape(g.H, g.W, 3)
    Image.fromarray(im1, "RGB").save(OUT / "C-points-1.png", optimize=True)
    Image.fromarray(im2, "RGB").save(OUT / "C-points-2.png", optimize=True)
    man = json.loads((OUT / "manifeste.json").read_text())
    man["segments"]["C"] = {"t0": 540, "t1": T_HAUT, "rot": "rot-C.bin", "rangees": int(nH), "cols": len(TM),
                            "pasRot": PAS_ROT, "points": ["C-points-1.png", "C-points-2.png"],
                            "fond": "cles/P0540.png", "pasDebut": 8, "raccord": [540, 620], "effacement": [540, 640],
                            "meca": {"t0": int(ts[0]), "pas": PAS_CLE, "n": len(ts), "fichiers": fichiers}}
    src = "Cao et al. 2024, Geoscience Frontiers 15, 101922, Zenodo 13628813"
    if src not in man["sources"]: man["sources"].append(src)
    (OUT / "manifeste.json").write_text(json.dumps(man, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
