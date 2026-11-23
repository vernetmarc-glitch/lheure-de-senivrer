"""Assemble les coupes calculées (geodyn.py) en paquet publié pour la page : carte des Alpes
(≈ 800 km) et coupes, une image par million d'années.

La carte est faite des coupes : chaque point de la carte est rapporté à l'arc alpin actuel
(front pennique simplifié) par sa position le long de l'arc (s) et sa distance à l'arc (n,
positive côté Adria) ; son altitude et son fragment sont lus dans les coupes voisines à
l'abscisse x_front + n, interpolées linéairement le long de l'arc. Cadre lié à l'Europe.
Hypothèse signalée : la géométrie en plan de l'arc est celle d'aujourd'hui à tous les instants
(la rotation de l'Adria et le déplacement de la Corse-Sardaigne viendront avec les fichiers
GPlates de van Hinsbergen et al. 2020).

Usage : python3 carte.py coupes.json <dossier des .npz> <dossier donnees>
"""
import gzip, json, os, sys
import numpy as np

FRAGMENTS = [
    {"id": 1, "nom": "Europe", "couleur": "#b9a48a"},
    {"id": 2, "nom": "Valais", "couleur": "#8fa3ad"},
    {"id": 3, "nom": "Briançonnais", "couleur": "#c98f6b"},
    {"id": 4, "nom": "océan liguro-piémontais", "couleur": "#4f7f6a"},
    {"id": 5, "nom": "Adria", "couleur": "#d7b26c"},
    {"id": 6, "nom": "sédiments de la chaîne", "couleur": "#e3d6a8"},
]
LITHOLOGIES = [
    {"id": 1, "nom": "sédiments", "couleur": "#e8d49a"},
    {"id": 2, "nom": "croûte supérieure", "couleur": "#c47f5a"},
    {"id": 3, "nom": "croûte inférieure", "couleur": "#8c5a6e"},
    {"id": 4, "nom": "manteau lithosphérique", "couleur": "#4e6b52"},
    {"id": 5, "nom": "asthénosphère", "couleur": "#2f3d48"},
    {"id": 6, "nom": "croûte océanique", "couleur": "#2c8c86"},
    {"id": 7, "nom": "serpentinites", "couleur": "#9fd3a0"},
]


def km_local(lon, lat, o):
    return ((np.asarray(lon) - o[0]) * 111.32 * np.cos(np.radians(o[1])), (np.asarray(lat) - o[1]) * 110.57)


def projette(px, py, ax, ay):
    """Abscisse curviligne s et distance signée n (positive à droite du sens de l'arc) au plus proche point."""
    best = np.full(px.shape, np.inf)
    S = np.zeros(px.shape)
    Nn = np.zeros(px.shape)
    s0 = 0.0
    for k in range(len(ax) - 1):
        dx, dy = ax[k + 1] - ax[k], ay[k + 1] - ay[k]
        L = np.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        u = (px - ax[k]) * ux + (py - ay[k]) * uy
        premier, dernier = k == 0, k == len(ax) - 2
        uc = np.clip(u, -np.inf if premier else 0, np.inf if dernier else L)
        qx, qy = ax[k] + uc * ux, ay[k] + uc * uy
        d = np.hypot(px - qx, py - qy)
        n = (px - ax[k]) * uy - (py - ay[k]) * ux          # à droite du sens de parcours
        m = d < best
        best[m], S[m], Nn[m] = d[m], s0 + uc[m], np.sign(n[m]) * d[m]
        s0 += L
    return S, Nn


def main(cfgf, dsim, dout):
    cfg = json.load(open(cfgf))
    o = cfg["carte"]["origine"]
    ax, ay = km_local(*np.array(cfg["arc"]).T, o)
    c = cfg["carte"]
    nx, ny, pas = c["nx"], c["ny"], c["pas_km"]
    X, Y = np.meshgrid(c["x0_km"] + np.arange(nx) * pas, c["y0_km"] + np.arange(ny) * pas)
    S, Nn = projette(X, Y, ax, ay)
    coupes, meta_coupes, suivi = [], [], {}
    for cp in cfg["coupes"]:
        d = np.load(os.path.join(dsim, cp["nom"] + ".npz"))
        img, topo, T = d["image"].copy(), d["topo"], d["t"]
        # demi-mailles d'affichage sans marqueur : matériau dominant de la maille du modèle qui les contient
        nt_, nz_, nx_ = img.shape
        bl = img[:, : nz_ // 2 * 2, : nx_ // 2 * 2].reshape(nt_, nz_ // 2, 2, nx_ // 2, 2).transpose(0, 1, 3, 2, 4).reshape(nt_, nz_ // 2, nx_ // 2, 4)
        dom_ = np.zeros(bl.shape[:3], np.uint8) + 255
        for q4 in range(4):
            v = bl[..., q4]
            dom_ = np.where((dom_ == 255) & (v != 255), v, dom_)
        rempli = np.repeat(np.repeat(dom_, 2, axis=1), 2, axis=2)
        sub = img[:, : nz_ // 2 * 2, : nx_ // 2 * 2]
        img[:, : nz_ // 2 * 2, : nx_ // 2 * 2] = np.where(sub == 255, rempli, sub)
        pas_s = float(d["pas_km"])
        p_r = pas_s / 2
        nxr = img.shape[2]
        xr = (np.arange(nxr) + 0.5) * p_r
        xs = np.arange(topo.shape[1]) * pas_s
        topo_r = np.array([np.interp(xr, xs, z) for z in topo])
        dom = img // 8
        roche = (img % 8) != 0
        itop = np.argmax(roche, axis=1)                          # (nt, nxr)
        dsurf = np.take_along_axis(dom, itop[:, None, :], 1)[:, 0, :]
        penn = np.isin(dsurf[-1], (2, 3, 4))
        xf = float(xr[np.argmax(penn)]) if penn.any() else float(xr[np.argmax(topo_r[-1])])
        sx, sy = km_local(*cp["point_arc"], o)
        sk, _ = projette(np.array([sx]), np.array([sy]), ax, ay)
        # trace : normale à l'arc au point de la coupe, de n = −200 à +200 km
        k = int(np.searchsorted(np.cumsum(np.r_[0, np.hypot(np.diff(ax), np.diff(ay))]), sk[0]) - 1)
        k = min(max(k, 0), len(ax) - 2)
        ux, uy = ax[k + 1] - ax[k], ay[k + 1] - ay[k]
        L = np.hypot(ux, uy)
        nxv, nyv = uy / L, -ux / L
        trace = [[float(sx - 200 * nxv), float(sy - 200 * nyv)], [float(sx + 200 * nxv), float(sy + 200 * nyv)]]
        coupes.append(dict(s=float(sk[0]), xf=xf, xr=xr, topo=topo_r, dsurf=dsurf, img=img, T=T))
        meta_coupes.append(dict(nom=cp["nom"], fichier=f"coupe_{len(meta_coupes)}.bin.gz", nx=int(nxr), nz=int(img.shape[1]),
                                pas_km=p_r, z_haut_km=(20000.0 - float(d["mer_m"]) if "mer_m" in d else 19900.0) / 1000, x_front_km=xf, s_km=float(sk[0]), trace=trace,
                                facteur_35=cp.get("facteur_35", 1.0), largeur_km=float(nxr * p_r)))
        su = json.loads(str(d["suivi"]))
        suivi[cp["nom"]] = {kk: [None if not np.isfinite(v) else round(float(v), 2) for v in vv] for kk, vv in su.items()}
    T = coupes[0]["T"]
    nt = len(T)
    ordre = np.argsort([cc["s"] for cc in coupes])
    coupes = [coupes[i] for i in ordre]
    meta_coupes = [meta_coupes[i] for i in ordre]
    for i, m in enumerate(meta_coupes):
        m["fichier"] = f"coupe_{i}.bin.gz"
    sk = np.array([cc["s"] for cc in coupes])
    # poids le long de l'arc
    j = np.clip(np.searchsorted(sk, S) - 1, 0, len(sk) - 2)
    w = np.clip((S - sk[j]) / (sk[j + 1] - sk[j]), 0, 1)
    H = np.zeros((nt, ny, nx), np.int16)
    F = np.zeros((nt, ny, nx), np.uint8)
    for t in range(nt):
        hz, fz = [], []
        for cc in coupes:
            xq = cc["xf"] + Nn
            hz.append(np.interp(xq, cc["xr"], cc["topo"][t]))
            col = np.clip(np.round(xq / (cc["xr"][1] - cc["xr"][0]) - 0.5).astype(int), 0, len(cc["xr"]) - 1)
            fz.append(cc["dsurf"][t][col])
        hz, fz = np.array(hz), np.array(fz)
        ii, jj = np.indices(S.shape)
        h = (1 - w) * hz[j, ii, jj] + w * hz[j + 1, ii, jj]
        f = np.where(w < 0.5, fz[j, ii, jj], fz[j + 1, ii, jj])
        H[t] = np.round(np.clip(h, -12000, 12000)).astype(np.int16)
        F[t] = f
    os.makedirs(dout, exist_ok=True)
    with gzip.open(os.path.join(dout, "carte.bin.gz"), "wb", 9) as g:
        g.write(H.astype("<i2").tobytes() + F.tobytes())
    for m, cc in zip(meta_coupes, coupes):
        with gzip.open(os.path.join(dout, m["fichier"]), "wb", 9) as g:
            g.write(cc["img"].astype(np.uint8).tobytes() + np.round(cc["topo"]).astype("<i2").tobytes())
    meta = dict(
        titre="L'orogenèse géodynamique des Alpes, 84 Ma → aujourd'hui",
        temps_ma=[round(float(t), 3) for t in T],
        carte=dict(fichier="carte.bin.gz", nx=nx, ny=ny, pas_km=pas, x0_km=c["x0_km"], y0_km=c["y0_km"],
                   origine_lonlat=o, niveau_mer_m=0, arc_km=[[round(float(a), 1), round(float(b), 1)] for a, b in zip(ax, ay)]),
        coupes=meta_coupes, suivi=suivi, fragments=FRAGMENTS, lithologies=LITHOLOGIES,
        glaciaire_m=[0.0] * nt,
        modele=dict(code="geodyn.py : Stokes visco-plastique 2D, différences finies décalées, marqueurs, air collant + FSSA, "
                         "chaleur implicite, érosion FastScape (fastscapelib SPL, m = 0,4, n = 1) + sédimentation marine",
                    pas_km=float(coupes[0]["xr"][1] - coupes[0]["xr"][0]) * 2,
                    convergence="Le Breton et al. 2021 : 420 km (84→35 Ma) puis 260 km (35→0 Ma), Europe fixe",
                    hypotheses=[cfg["source"], cfg["arc_source"],
                                "Géométrie en plan de l'arc fixe (celle d'aujourd'hui) ; convergence normale à l'arc partout égale.",
                                "Niveau de la mer 200 m sous la surface d'un continent de référence de 35 km de croûte (les plaines continentales émergent)."]))
    json.dump(meta, open(os.path.join(dout, "meta.json"), "w"), ensure_ascii=False)
    print("paquet :", {f: os.path.getsize(os.path.join(dout, f)) for f in os.listdir(dout)})


if __name__ == "__main__":
    main(*sys.argv[1:4])
