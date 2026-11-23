"""Film FastScape des 45 derniers Ma autour de Grenoble (chantier S7).

FastScape (fastscapelib 0.3) calcule rivières (loi de puissance du courant, m = 0,45,
n = 1), versants (diffusion) ; le soulèvement et le raccourcissement horizontal sont
imposés par sim/scenario.py.

Gabarit de soulèvement : le taux qui maintient le relief réel en équilibre sous ces
mêmes lois d'érosion (inversion stationnaire sur le MNT Copernicus). Chaque domaine
structural en reçoit une part croissante selon sa chronologie.

Sur les 2 derniers Ma, un terme d'ajustement rapproche le relief du relief réel
(fermeture de l'écart au prorata du temps restant, jusqu'à −10 ka ; les 10 derniers ka
évoluent librement). L'ajustement positif est compté comme soulèvement, l'ajustement
négatif comme érosion (creusement glaciaire, non modélisé explicitement).

Sortie (dossier --sortie) : meta.json, etats_XX.bin.gz, reel_256.bin.gz, reel_1024.bin.gz.
"""
import argparse, gzip, json, os, sys, time
import numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter
import fastscapelib as fs

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import scenario as sc

TAILLE_KM = 204.8
N_PUB = 512                                  # publié à pleine résolution FastScape (400 m)
K_F, M_EXP, N_EXP = 1.2e-5, 0.45, 1.0      # m^(1-2m)/an
K_D = 0.05                                   # m²/an
H_ZERO, H_PAS = -1000.0, 2.0                 # quantification du relief (m)
TAUX_MAX = 8.0                               # mm/an, codage racine carrée
X_MAX = 20000.0                              # m, profondeur d'origine des roches
PAR_PAQUET = 6                               # clés par fichier
N_GRAINS = 1000
PAS_CLE, Q_CLE, N_RES, Q_RES = 4, 10.0, 128, 8.0     # images clés et résidus (codage v3)
N_X, N_UE = 256, 64                         # résolution des roches, du soulèvement et de l'érosion


def bloc(a, n):
    f = a.shape[0] // n
    return a.reshape(n, f, n, f).mean(axis=(1, 3))


def temps_etats():
    a = np.round(np.arange(-45.0, -2.0 + 1e-9, 0.25), 4)
    b = np.round(np.arange(-1.95, 0.0 + 1e-9, 0.05), 4)
    return np.concatenate([a, b])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--sortie", default=os.path.join(ICI, "..", "..", "app", "public", "labo", "alpes", "donnees"))
    ap.add_argument("--dt", type=float, default=10000.0)
    args = ap.parse_args()
    N = args.n
    global N_PUB, N_X
    N_PUB = min(N_PUB, N); N_X = min(N_X, N_PUB)
    pas = TAILLE_KM * 1000 / N
    os.makedirs(args.sortie, exist_ok=True)

    reel1024 = np.load(os.path.join(ICI, "reel_1024.npz"))["h"].astype(np.float64)
    cible = bloc(reel1024, N)
    c = (np.arange(N) + 0.5) * pas / 1000 - TAILLE_KM / 2
    X, Y = np.meshgrid(c, -c)
    dom = sc.domaines(X, Y)
    fr = sc.champ_raccourcissement(X, Y)

    grid = fs.RasterGrid([N, N], [pas, pas], fs.NodeStatus.FIXED_VALUE)
    fg = fs.FlowGraph(grid, [fs.SingleFlowRouter(), fs.MSTSinkResolver()])
    spl = fs.SPLEroder(fg, K_F, M_EXP, N_EXP, 1e-5)
    dif = fs.DiffusionADIEroder(grid, K_D)
    A = np.empty((N, N))
    coeur = np.zeros((N, N), bool); coeur[1:-1, 1:-1] = True

    # Gabarit : taux d'érosion du relief réel sous ces lois (m/an)
    fg.update_routes(cible); fg.accumulate(A, 1.0)
    e1 = spl.erode(cible, A, 1.0); e2 = dif.erode(cible - e1, 1.0)
    U0 = np.clip(e1 + e2, 0, 6e-3) * coeur
    print(f"gabarit : médiane {1e3*np.median(U0):.3f}, p95 {1e3*np.percentile(U0,95):.2f}, "
          f"max {1e3*U0.max():.2f} mm/an", flush=True)

    # Relief initial (−45 Ma) : plaine basse, prisme naissant à l'est
    rng = np.random.default_rng(45)
    bruit = gaussian_filter(rng.standard_normal((N, N)), 2.0)
    bruit /= bruit.std()
    h0 = 20 + 0.1 * (X + TAILLE_KM / 2) + 400 * dom["interne"]
    h = h0 + 15 * bruit * coeur
    Xr = np.zeros((N, N))                       # profondeur d'origine des roches au jour (m)

    # Grains de roche suivis, dans une tranche de ±3 km autour de la coupe
    # ouest-nord-ouest → est-sud-est passant par Grenoble (axe du raccourcissement)
    axe = -sc.DIRECTION                          # vers l'ESE
    nrm = np.array([-axe[1], axe[0]])
    rg = np.random.default_rng(7)
    gs = rg.uniform(-85, 85, N_GRAINS); gq = rg.uniform(-3, 3, N_GRAINS)
    gx = gs * axe[0] + gq * nrm[0]; gy = gs * axe[1] + gq * nrm[1]
    def idx(xk, yk):
        j = np.clip(np.round((xk + TAILLE_KM / 2) / (pas / 1000) - 0.5).astype(int), 0, N - 1)
        i = np.clip(np.round((TAILLE_KM / 2 - yk) / (pas / 1000) - 0.5).astype(int), 0, N - 1)
        return i, j
    gi, gj = idx(gx, gy)
    gz = h[gi, gj] - rg.uniform(0, 18000, N_GRAINS)     # altitude du grain (m)
    gdmax = h[gi, gj] - gz
    gvif = np.ones(N_GRAINS, bool); gtex = np.full(N_GRAINS, 1e9)
    grains = []

    T = temps_etats()
    dt = args.dt
    t = -45.0
    etats = []
    accU = np.zeros((N, N)); accE = np.zeros((N, N)); acc_t = 0.0
    racc_etat = [0.0]
    racc_max = 0.0
    depl = 0.0                                   # déplacement cumulé non encore appliqué (m)

    def enregistrer():
        U = accU / max(acc_t, 1) * 1e3; E = accE / max(acc_t, 1) * 1e3
        etats.append((bloc(h, N_PUB).astype(np.float32), bloc(U, N_UE).astype(np.float32),
                      bloc(E, N_UE).astype(np.float32), bloc(Xr, N_X).astype(np.float32)))
        grains.append(((gx * axe[0] + gy * axe[1]).copy(), gz.copy(), gdmax.copy()))

    enregistrer()
    k_suiv = 1
    t0 = time.time()
    t_fin_ajust = -0.01
    while k_suiv < len(T):
        tn = T[k_suiv]
        dts = dt if t < -2.0 - 1e-9 else dt / 2
        pas_t = min(dts / 1e6, tn - t)
        dty = pas_t * 1e6
        tm = t + pas_t / 2
        prog = sc.progression(tm)
        g = sum(dom[d] * prog[d] for d in prog)
        U = U0 * g
        wb = sc.poids_bassin(tm, dom, prog)
        nb = sc.niveau_bassin(tm)

        # raccourcissement : advection semi-lagrangienne bilinéaire (monotone), par pas d'une maille
        v = sc.raccourcissement_mm_an(tm)
        racc_max = max(racc_max, v)
        depl += v * 1e-3 * dty
        if depl > pas or (depl > 0 and k_suiv == len(T) - 1):
            dx = sc.DIRECTION[0] * depl * fr / pas
            dy = sc.DIRECTION[1] * depl * fr / pas
            ii, jj = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
            src = [ii + dy, jj - dx]          # ligne 0 = nord : y positif = vers le haut
            h = map_coordinates(h, src, order=1, mode="nearest")
            gi, gj = idx(gx, gy)
            gx = gx + sc.DIRECTION[0] * depl / 1000 * fr[gi, gj] * gvif
            gy = gy + sc.DIRECTION[1] * depl / 1000 * fr[gi, gj] * gvif
            Xr = map_coordinates(Xr, src, order=1, mode="nearest")
            depl = 0.0

        # bord : suit la progression du domaine (niveau de base imposé)
        bord = ~coeur
        hb = wb * nb + (1 - wb) * (h0 + (cible - h0) * g)
        wf = sc._rampe(tm, -6, -2)
        h[bord] = ((1 - wf) * hb + wf * cible)[bord]

        hu = h + U * dty
        gi, gj = idx(gx, gy)
        gz = gz + U[gi, gj] * dty * gvif               # la roche monte avec le soulèvement
        fg.update_routes(hu); fg.accumulate(A, 1.0)
        es = spl.erode(hu, A, dty)
        ed = dif.erode(hu - es, dty)
        h = hu - es - ed
        e = (es + ed) * coeur
        Xr = np.maximum(Xr + e, 0)
        # bassin d'avant-pays : la surface suit le niveau imposé (subsidence ou dépôt)
        db = (nb - h) * min(dty / 1e6, 1.0) * wb * coeur
        h = h + db
        gz = gz + np.minimum(db, 0)[gi, gj] * gvif      # subsidence : la roche descend aussi
        Xr = np.where(db > 1.0, 0.0, Xr)          # sédiment frais : roches de surface
        accU += U * dty + np.minimum(db, 0); accE += e - np.maximum(db, 0)

        if t + pas_t > -2.0 + 1e-9 and t < t_fin_ajust - 1e-9:
            reste = max(t_fin_ajust - t, pas_t)
            C = (cible - h) * min(pas_t / reste, 1.0) * coeur
            h = h + C
            gz = gz + np.maximum(C, 0)[gi, gj] * gvif
            accU += np.maximum(C, 0); accE += np.maximum(-C, 0)
            Xr = Xr + np.maximum(-C, 0)

        prof = h[gi, gj] - gz
        gdmax = np.where(gvif, np.maximum(gdmax, prof), gdmax)
        sort = gvif & (prof <= 0)
        gtex[sort] = t + pas_t; gz[sort] = h[gi, gj][sort]; gvif &= ~sort
        t = round(t + pas_t, 9)
        acc_t += dty
        if abs(t - tn) < 1e-7:
            t = tn
            enregistrer()
            racc_etat.append(racc_max)
            accU[:] = 0; accE[:] = 0; acc_t = 0.0; racc_max = 0.0
            if abs(tn + 2.0) < 1e-9:
                print(f"  à −2 Ma, avant ajustement : écart moyen au réel "
                      f"{np.abs(h - cible).mean():.0f} m", flush=True)
            if k_suiv % 20 == 0:
                print(f"  {tn:7.2f} Ma  max {h.max():5.0f} m  moy {h.mean():5.0f} m  "
                      f"({time.time()-t0:.0f} s)", flush=True)
            k_suiv += 1

    print(f"fin : écart moyen au réel {np.abs(h - cible).mean():.1f} m", flush=True)
    print(f"grains : {int((~gvif).sum())} / {N_GRAINS} arrivés au jour", flush=True)
    ecrire(args.sortie, T, etats, racc_etat, reel1024, (grains, gtex, gq, axe))


def q_h(a):
    return np.clip(np.round((a - H_ZERO) / H_PAS), 0, 65535).astype(np.int64)


def q_taux(r):
    return np.round(255 * np.sqrt(np.clip(r, 0, TAUX_MAX) / TAUX_MAX)).astype(np.uint8)


def q_x(x):
    return np.round(255 * np.log1p(np.clip(x, 0, X_MAX) / 200) / np.log1p(X_MAX / 200)).astype(np.uint8)


def agrandir(a, n):
    """Bilinéaire aux centres de mailles, bords répétés — identique à alpes.js (agrandir)."""
    m = a.shape[0]
    c = np.clip((np.arange(n) + 0.5) * m / n - 0.5, 0, m - 1)
    i0 = np.floor(c).astype(int); i1 = np.minimum(i0 + 1, m - 1); w = c - i0
    a = a[i0] * (1 - w)[:, None] + a[i1] * w[:, None]
    return a[:, i0] * (1 - w)[None, :] + a[:, i1] * w[None, :]


def plans(a16):
    a16 = np.ascontiguousarray(a16, "<i2")
    v = a16.view(np.uint8).reshape(-1, 2)
    return v[:, 0].tobytes() + v[:, 1].tobytes()


def ecrire(sortie, T, etats, racc, reel1024, gr):
    """Paquet v3 (voir meta.json, « codage »). Images clés tous les PAS_CLE états : relief
    512² au pas Q_CLE, en différences d'une clé à l'autre (boucle fermée). Entre deux clés :
    résidus 128² au pas Q_RES par rapport à l'interpolation linéaire des clés reconstruites,
    ajoutés après agrandissement bilinéaire. Roches (X) aux clés ; soulèvement et érosion à
    chaque état (64²)."""
    for f in os.listdir(sortie):
        if f.startswith("etats_") or f.startswith("reel_"):
            os.remove(os.path.join(sortie, f))
    K, n = len(T), N_PUB
    cles = list(range(0, K, PAS_CLE))
    if cles[-1] != K - 1:
        cles.append(K - 1)
    rec, prev, qprev, xprev = {}, None, None, None
    flux = []                                    # un bloc par clé : clé, résidus précédents, X, U/E
    for ic, k in enumerate(cles):
        h = etats[k][0].astype(np.float64)
        q = np.round(h / Q_CLE).astype(np.int64)
        d = q if qprev is None else q - qprev
        rec[k] = q * Q_CLE; qprev = q
        bloc_ = plans(d.astype(np.int16).ravel())
        res = b""
        ue = b""
        if prev is not None:
            for j in range(prev + 1, k):
                f = (j - prev) / (k - prev)
                p = rec[prev] * (1 - f) + rec[k] * f
                r = (etats[j][0] - p).reshape(N_RES, n // N_RES, N_RES, n // N_RES).mean(axis=(1, 3))
                res += np.clip(np.round(r / Q_RES), -127, 127).astype(np.int8).tobytes()
            rng_ue = range(prev + 1, k + 1)
        else:
            rng_ue = range(0, 1)
        for j in rng_ue:
            ue += q_taux(etats[j][1]).tobytes() + q_taux(etats[j][2]).tobytes()
        x = q_x(etats[k][3]).astype(np.int16)
        dx = (x if xprev is None else (x - xprev)) % 256
        xprev = x
        flux.append(bloc_ + res + dx.astype(np.uint8).tobytes() + ue)
        prev = k
    paquets = []
    for p0 in range(0, len(cles), PAR_PAQUET):
        nom = f"etats_{p0 // PAR_PAQUET:02d}.bin.gz"
        with gzip.open(os.path.join(sortie, nom), "wb", 9) as f:
            f.write(b"".join(flux[p0:p0 + PAR_PAQUET]))
        paquets.append({"fichier": nom, "cles": cles[p0:p0 + PAR_PAQUET]})
    grains, gtex, gq, axe = gr
    S = np.array([np.round(g[0] * 100) for g in grains]).astype(np.int64)
    Z = np.array([np.clip(np.round(g[1]), -32000, 32000) for g in grains]).astype(np.int64)
    D = np.array([np.clip(np.round(g[2] / 100), 0, 255) for g in grains]).astype(np.int64)
    dS = np.diff(S, axis=0, prepend=0).astype(np.int16); dZ = np.diff(Z, axis=0, prepend=0).astype(np.int16)
    dD = (np.diff(D, axis=0, prepend=0) % 256).astype(np.uint8)
    with gzip.open(os.path.join(sortie, "grains.bin.gz"), "wb", 9) as f:
        f.write(gtex.astype("<f4").tobytes() + gq.astype("<f4").tobytes() + plans(dS.ravel()) + plans(dZ.ravel()) + dD.tobytes())
    with gzip.open(os.path.join(sortie, f"reel_{n}.bin.gz"), "wb", 9) as f:
        f.write(q_h(bloc(reel1024, n)).astype("<u2").tobytes())
    detail = reel1024 - agrandir(bloc(reel1024, n), 1024)
    with gzip.open(os.path.join(sortie, "reel_detail_1024.bin.gz"), "wb", 9) as f:
        f.write(np.clip(np.round(detail / 2.0), -127, 127).astype(np.int8).tobytes())
    meta = {
        "version": 3, "n": n, "n_res": N_RES, "n_x": N_X, "n_ue": N_UE, "pas_m": TAILLE_KM * 1000 / n,
        "taille_km": TAILLE_KM, "centre": {"lat": sc.LAT0, "lon": sc.LON0},
        "projection": "azimutale équidistante, nord en haut",
        "temps_Ma": [float(t) for t in T], "cles": cles, "q_cle_m": Q_CLE, "q_res_m": Q_RES,
        "raccourcissement_mm_an": [round(float(r), 3) for r in racc],
        "h_zero_m": H_ZERO, "h_pas_m": H_PAS, "reel": f"reel_{n}.bin.gz", "reel_detail": "reel_detail_1024.bin.gz",
        "taux_max_mm_an": TAUX_MAX, "x_max_m": X_MAX,
        "codage": ("par clé, dans l'ordre : relief int16 (plans bas puis hauts) = q − q_clé_précédente "
                   "(la première absolue), h = q·q_cle ; puis pour chaque état entre la clé précédente et "
                   "celle-ci : résidu int8 n_res², h = interpolation linéaire des clés + agrandir(résidu·q_res) "
                   "(bilinéaire aux centres) ; puis roches de la clé : uint8 n_x², différence mod 256, "
                   "v = 255·ln(1+x/200 m)/ln(1+x_max/200 m) ; puis soulèvement et érosion (uint8 n_ue² chacun, "
                   "v = 255·√(taux/taux_max)) de chaque état depuis la clé précédente (exclue) jusqu'à celle-ci. "
                   "reel : uint16, h = v·h_pas + h_zero ; reel_detail : int8 ×2 m, relief réel 1024² moins "
                   "agrandir(moyenne 512²)"),
        "paquets": paquets,
        "grains": {"fichier": "grains.bin.gz", "nombre": int(len(gtex)), "axe_est": [float(axe[0]), float(axe[1])],
                   "codage": "G float32 âge d'arrivée au jour (Ma, 1e9 = jamais) | G float32 écart à la coupe (km) | "
                             "abscisse int16 (10 m), altitude int16 (m) : différences d'un état au suivant, plans bas "
                             "puis hauts, [état][grain] | profondeur maximale uint8 (100 m), différences mod 256"},
        "modele": f"fastscapelib {fs.__version__} — K_f {K_F}, m {M_EXP}, n {N_EXP}, K_d {K_D} m²/an",
        "source_relief": "Copernicus DEM GLO-90 (© DLR e.V. 2010-2014 et © Airbus Defence and Space GmbH 2014-2018, programme Copernicus)",
    }
    with open(os.path.join(sortie, "meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False)
    tot = sum(os.path.getsize(os.path.join(sortie, f)) for f in os.listdir(sortie) if f.startswith(("etats", "grains", "reel", "meta")))
    print(f"paquet : {K} états, {len(cles)} clés, {tot/1e6:.1f} Mo (film)", flush=True)


if __name__ == "__main__":
    main()
