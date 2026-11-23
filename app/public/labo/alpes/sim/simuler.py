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
N_PUB = 256
K_F, M_EXP, N_EXP = 1.2e-5, 0.45, 1.0      # m^(1-2m)/an
K_D = 0.05                                   # m²/an
H_ZERO, H_PAS = -1000.0, 1.0                 # quantification du relief (m)
TAUX_MAX = 8.0                               # mm/an, codage racine carrée
X_MAX = 20000.0                              # m, profondeur d'origine des roches
PAR_PAQUET = 16


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
    ap.add_argument("--sortie", default=os.path.join(ICI, "..", "donnees"))
    ap.add_argument("--dt", type=float, default=10000.0)
    args = ap.parse_args()
    N = args.n
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
        etats.append((bloc(h, N_PUB), bloc(U, N_PUB), bloc(E, N_PUB), bloc(Xr, N_PUB)))

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
            Xr = map_coordinates(Xr, src, order=1, mode="nearest")
            depl = 0.0

        # bord : suit la progression du domaine (niveau de base imposé)
        bord = ~coeur
        hb = wb * nb + (1 - wb) * (h0 + (cible - h0) * g)
        wf = sc._rampe(tm, -6, -2)
        h[bord] = ((1 - wf) * hb + wf * cible)[bord]

        hu = h + U * dty
        fg.update_routes(hu); fg.accumulate(A, 1.0)
        es = spl.erode(hu, A, dty)
        ed = dif.erode(hu - es, dty)
        h = hu - es - ed
        e = (es + ed) * coeur
        Xr = np.maximum(Xr + e, 0)
        # bassin d'avant-pays : la surface suit le niveau imposé (subsidence ou dépôt)
        db = (nb - h) * min(dty / 1e6, 1.0) * wb * coeur
        h = h + db
        Xr = np.where(db > 1.0, 0.0, Xr)          # sédiment frais : roches de surface
        accU += U * dty + np.minimum(db, 0); accE += e - np.maximum(db, 0)

        if t + pas_t > -2.0 + 1e-9 and t < t_fin_ajust - 1e-9:
            reste = max(t_fin_ajust - t, pas_t)
            C = (cible - h) * min(pas_t / reste, 1.0) * coeur
            h = h + C
            accU += np.maximum(C, 0); accE += np.maximum(-C, 0)
            Xr = Xr + np.maximum(-C, 0)

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
    ecrire(args.sortie, T, etats, racc_etat, reel1024)


def q_h(a):
    return np.clip(np.round((a - H_ZERO) / H_PAS), 0, 65535).astype(np.int64)


def q_taux(r):
    return np.round(255 * np.sqrt(np.clip(r, 0, TAUX_MAX) / TAUX_MAX)).astype(np.uint8)


def q_x(x):
    return np.round(255 * np.log1p(np.clip(x, 0, X_MAX) / 200) / np.log1p(X_MAX / 200)).astype(np.uint8)


def ecrire(sortie, T, etats, racc, reel1024):
    for f in os.listdir(sortie):
        if f.startswith("etats_"):
            os.remove(os.path.join(sortie, f))
    paquets = []
    for p0 in range(0, len(T), PAR_PAQUET):
        lot = etats[p0:p0 + PAR_PAQUET]
        qs = np.array([q_h(e[0]).ravel() for e in lot])
        d = np.diff(qs, axis=0, prepend=0).astype("<i2")
        d = np.concatenate([d.view(np.uint8)[:, 0::2], d.view(np.uint8)[:, 1::2]])  # plans bas/haut
        u = np.array([q_taux(e[1]).ravel() for e in lot])
        ee = np.array([q_taux(e[2]).ravel() for e in lot])
        x = np.array([q_x(e[3]).ravel() for e in lot])
        nom = f"etats_{p0 // PAR_PAQUET:02d}.bin.gz"
        with gzip.open(os.path.join(sortie, nom), "wb", 9) as f:
            f.write(d.tobytes() + u.tobytes() + ee.tobytes() + x.tobytes())
        paquets.append({"fichier": nom, "debut": p0, "nombre": len(lot)})
    for n in (256, 1024):
        with gzip.open(os.path.join(sortie, f"reel_{n}.bin.gz"), "wb", 9) as f:
            f.write(q_h(bloc(reel1024, n)).astype("<u2").tobytes())
    meta = {
        "n": N_PUB, "pas_m": TAILLE_KM * 1000 / N_PUB, "taille_km": TAILLE_KM,
        "centre": {"lat": sc.LAT0, "lon": sc.LON0}, "projection": "azimutale équidistante, nord en haut",
        "temps_Ma": [float(t) for t in T], "raccourcissement_mm_an": [round(float(r), 3) for r in racc],
        "h_zero_m": H_ZERO, "h_pas_m": H_PAS, "taux_max_mm_an": TAUX_MAX,
        "x_max_m": X_MAX, "x_codage": "v = 255·ln(1+x/200 m)/ln(1+x_max/200 m)",
        "h_codage": "par paquet : k×n² octets bas puis k×n² octets hauts d'entiers int16 ; différences successives (le premier état absolu) ; h = cumul·h_pas + h_zero",
        "taux_codage": "v = 255·√(taux/taux_max)",
        "paquets": paquets,
        "modele": f"fastscapelib {fs.__version__} — K_f {K_F}, m {M_EXP}, n {N_EXP}, K_d {K_D} m²/an",
        "source_relief": "Copernicus DEM GLO-90 (© DLR e.V. 2010-2014 et © Airbus Defence and Space GmbH 2014-2018, programme Copernicus)",
    }
    with open(os.path.join(sortie, "meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False)
    tot = sum(os.path.getsize(os.path.join(sortie, f)) for f in os.listdir(sortie))
    print(f"paquet : {len(T)} états, {tot/1e6:.1f} Mo", flush=True)


if __name__ == "__main__":
    main()
