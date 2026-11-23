"""Modèle thermo-mécanique 2D d'une coupe des Alpes (chantier S7b, D-48).

Stokes incompressible visco-plastique, différences finies sur grille décalée (Gerya 2019,
« Introduction to Numerical Geodynamic Modelling », ch. 7–13), matière portée par des
marqueurs (lithologie, domaine paléogéographique, température, déformation plastique),
surface libre par air collant (« sticky air ») stabilisée (FSSA, Kaus et al. 2010),
chaleur implicite (conduction + radioactivité), surface suivie explicitement et érodée
par FastScape (fastscapelib : loi de puissance du courant, Braun & Willett 2013) le long
du profil, sédimentation marine sous le niveau de la mer.

Conditions aux limites : l'Europe est fixe (bord gauche) ; l'Adria entre par le bord droit
à la vitesse de la reconstruction de Le Breton et al. 2021 (Solid Earth 12, 885) :
420 km de 84 à 35 Ma puis 260 km de 35 à 0 Ma ; le manteau ressort sous l'Adria.

Usage : python3 geodyn.py coupes.json <nom> <sortie.npz> [--pas-km 5] [--budget-s 20000]
Les calculs complets tournent sur GitHub (chantier-orogenese.yml) ; ici, essais courts seulement.
"""
import argparse, json, os, sys, time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial import cKDTree

AN = 365.25 * 24 * 3600.0
MA = 1e6 * AN
KM = 1e3
G = 9.81
RG = 8.314
T0K = 273.0

# Lithologies (code % 8) et domaines (code // 8) des marqueurs
AIR, SED, CS, CI, ML, AST, CO, SERP = range(8)
D0, EUR, VAL, BRI, LIG, ADR, SYN = range(7)

# rho0, k, H (W/m3), loi de fluage (AD MPa^-n s^-1, n, Ea J/mol, Va m3/mol), C0, C1 (Pa), phi0, phi1 (deg)
QZ = (3.2e-4, 2.3, 154e3, 0.0)        # quartzite humide (Ranalli 1995)
PL = (3.3e-4, 3.2, 238e3, 0.0)        # plagioclase An75
OL = (2.5e4, 3.5, 532e3, 8e-6)        # olivine sèche
PROP = {
    AIR:  dict(rho=1.0,    k=20.0, H=0.0,    flu=None, C=(1e6, 1e6), phi=(0, 0)),
    SED:  dict(rho=2600.0, k=2.2,  H=1.5e-6, flu=QZ, C=(1e7, 2e6), phi=(20, 5)),
    CS:   dict(rho=2750.0, k=2.5,  H=1.0e-6, flu=QZ, C=(1e7, 2e6), phi=(30, 8)),
    CI:   dict(rho=2950.0, k=2.5,  H=0.4e-6, flu=PL, C=(1e7, 2e6), phi=(30, 8)),
    ML:   dict(rho=3250.0, k=3.0,  H=2e-8,   flu=OL, C=(1e7, 2e6), phi=(30, 8)),
    AST:  dict(rho=3300.0, k=3.0,  H=2e-8,   flu=OL, C=(1e7, 2e6), phi=(30, 8)),
    CO:   dict(rho=3000.0, k=2.5,  H=2.5e-7, flu=PL, C=(1e7, 1e6), phi=(15, 3)),
    SERP: dict(rho=3000.0, k=2.5,  H=0.0,    flu=None, C=(1e6, 1e6), phi=(5, 2)),
}
ETA_AIR, ETA_MIN, ETA_MAX, ETA_SERP = 1e18, 1e19, 1e24, 1e19   # manteau : 1e20 au moins
# Manteau lithosphérique appauvri (déplété) : 50 kg/m3 plus léger que l'asthénosphère à même température
ALPHA = 3e-5
RHO_ECLOGITE = 3450.0       # croûte océanique éclogitisée au-delà de 1,5 GPa
TP = 1350.0                 # température potentielle du manteau (°C)


def vitesse_adria(t_ma, f35=1.0):
    """Vitesse de convergence (m/s) à l'instant t (Ma, négatif dans le passé)."""
    v = 420.0 / 49.0 if t_ma < -35 else 260.0 * f35 / 35.0      # km/Ma
    return v * KM / MA


def creep_eta(flu, T, P, e):
    AD, n, Ea, Va = flu
    A = AD * 1e-6 ** n
    F2 = 1.0 / 2 ** ((n - 1) / n) / 3 ** ((n + 1) / (2 * n))
    return F2 * A ** (-1 / n) * e ** ((1 - n) / n) * np.exp(np.clip((Ea + np.maximum(P, 0) * Va) / (n * RG * T), 0, 600))


class Modele:
    def __init__(self, cfg, pas_km=5.0, seed=0):
        self.cfg = cfg
        self.L = cfg.get("largeur_km", 1200) * KM
        self.H = cfg.get("profondeur_km", 400) * KM
        self.yair = 20 * KM
        self.dx = self.dy = pas_km * KM
        self.Nx = int(round(self.L / self.dx)) + 1
        self.Ny = int(round(self.H / self.dy)) + 1
        self.x = np.linspace(0, self.L, self.Nx)
        self.y = np.linspace(0, self.H, self.Ny)
        self.rng = np.random.default_rng(seed)
        self.t = -84.0
        self.f35 = cfg.get("facteur_35", 1.0)
        self.nm = 4                                  # marqueurs par maille et par direction
        self.colonnes()
        self.init_marqueurs()
        self.vx = np.zeros((self.Ny + 1, self.Nx + 1))
        self.vy = np.zeros((self.Ny + 1, self.Nx + 1))
        self.P = np.zeros((self.Ny + 1, self.Nx + 1))
        self.pas = 0

    # ---------------------------------------------------------------- géométrie initiale
    def colonnes(self):
        """Paléogéographie à 84 Ma le long de la coupe (km) : épaisseurs de couches par x."""
        c = self.cfg
        wV, wB, wO = c["valais_km"], c["brianconnais_km"], c["ocean_km"]
        xs = [0.0, 380.0, 440.0]
        x1 = 440.0 + wV
        x2 = x1 + (20.0 if wV > 0 else 0.0)
        x3 = x2 + wB
        x4 = x3 + 20.0
        x5 = x4 + wO
        x6 = x5 + 40.0
        self.bornes = dict(marge=440.0, valais=(440.0, x1), bri=(x2, x3), ocean=(x4, x5), adria=x6)
        # profils (x, sed, cs, ci, lith, domaine) aux points d'appui
        eur = (2, 18, 15, 120)
        val = (2, 5, 3, 70)
        bri = (3, 12, 10, 100)
        adr = (3, 15, 14, 110)
        pts = [(0, eur, EUR), (380, eur, EUR)]
        if wV > 0:
            pts += [(440, val, VAL), (x1, val, VAL), (x2, bri, BRI)]
        else:
            pts += [(440, bri, BRI)]
        pts += [(x3, bri, BRI)]
        self.pts = pts
        self.x4, self.x5, self.x6 = x4, x5, x6
        self.adr = adr

    def colonne(self, xk):
        """(sed, cs, ci, co, lith, domaine, oceanique) en km pour une abscisse en km."""
        if xk <= self.pts[-1][0]:
            for (xa, pa, da), (xb, pb, db) in zip(self.pts[:-1], self.pts[1:]):
                if xa <= xk <= xb:
                    u = 0 if xb == xa else (xk - xa) / (xb - xa)
                    p = [a + u * (b - a) for a, b in zip(pa, pb)]
                    dom = da if u < 0.5 or da == db else db
                    if xk < 440 and xk > 380:
                        dom = EUR
                    return p[0], p[1], p[2], 0.0, p[3], dom
        if xk < self.x4:                            # transition vers l'océan
            u = (xk - self.pts[-1][0]) / (self.x4 - self.pts[-1][0])
            b = self.pts[-1][1]
            return b[0] * (1 - u) + 1 * u, b[1] * (1 - u), b[2] * (1 - u), 7 * u, b[3] * (1 - u) + 90 * u, BRI if u < 0.5 else LIG
        if xk <= self.x5:
            return 1.0, 0.0, 0.0, 7.0, 90.0, LIG
        if xk < self.x6:
            u = (xk - self.x5) / (self.x6 - self.x5)
            a = self.adr
            return 1 + u * (a[0] - 1), a[1] * u, a[2] * u, 7 * (1 - u), 90 + u * (a[3] - 90), LIG if u < 0.5 else ADR
        a = self.adr
        return a[0], a[1], a[2], 0.0, a[3], ADR

    def isostasie(self, col):
        """Profondeur (km, depuis le haut du modèle) de la surface rocheuse d'une colonne (Airy, 140 km)."""
        sed, cs, ci, co, lith, _ = col
        ref = 2 * 2600 + 18 * 2750 + 15 * 2950 + (120 - 35) * 3300
        crust = sed * 2600 + cs * 2750 + ci * 2950 + co * 3000
        tc = sed + cs + ci + co
        # (ys - 20)*1 + crust + (140 - ys - tc)*3300 = ref
        ys = (crust + (140 - tc) * 3300 - 20 - ref) / (3300 - 1)
        return ys

    def init_marqueurs(self):
        nmx = (self.Nx - 1) * self.nm
        nmy = (self.Ny - 1) * self.nm
        dxm, dym = self.L / nmx, self.H / nmy
        X, Y = np.meshgrid((np.arange(nmx) + 0.5) * dxm, (np.arange(nmy) + 0.5) * dym)
        X = X.ravel() + (self.rng.random(X.size) - 0.5) * dxm
        Y = Y.ravel() + (self.rng.random(Y.size) - 0.5) * dym
        self.mx, self.my = X, Y
        self.lit, self.dom, self.T, self.eps, self.ecl = self.proprietes(X, Y)
        # zone de faiblesse : serpentinites plongeant à 30° sous l'Adria, depuis la marge adriatique
        xs = self.x5 * KM - 10 * KM
        ys = self.surf0(xs / KM) * KM
        d = (X - xs) * np.sin(np.radians(30)) - (Y - ys) * np.cos(np.radians(30))
        le_long = (X - xs) * np.cos(np.radians(30)) + (Y - ys) * np.sin(np.radians(30))
        zf = (np.abs(d) < 8 * KM) & (le_long > 0) & (le_long < 140 * KM) & (self.lit != AIR) & (Y > ys)
        self.lit[zf & (self.lit != CO) & (self.lit != SED)] = SERP
        self.eps[zf] = 1.5
        x0 = np.arange(self.Nx) * self.dx
        self.topo = np.array([self.surf0(xk / KM) for xk in x0]) * KM     # profondeur de la surface (m)
        # marqueurs suivis (croûte supérieure à 8 km sous la surface) : x initial des fragments
        b = self.bornes
        cibles = {"Europe": 200.0, "Adria": self.L / KM - 150.0}
        if b["valais"][1] > b["valais"][0]:
            cibles["Valais"] = 0.5 * sum(b["valais"])
        cibles["Briançonnais"] = 0.5 * sum(b["bri"])
        cibles["Liguro-piémontais"] = 0.5 * sum(b["ocean"])
        self.suivis = {}
        for nom, xk in cibles.items():
            yk = (self.surf0(xk) + 3.0) * KM
            self.suivis[nom] = int(np.argmin((X - xk * KM) ** 2 + (Y - yk) ** 2))

    def surf0(self, xk):
        return self.isostasie(self.colonne(xk))

    def proprietes(self, X, Y, adria=False):
        """Lithologie, domaine, température initiales de marqueurs (m)."""
        n = X.size
        lit = np.full(n, AST, np.int8)
        dom = np.full(n, D0, np.int8)
        T = np.zeros(n)
        cache = {}
        xk_all = np.clip(np.round(X / KM).astype(int), 0, int(self.L / KM))
        for xk in np.unique(xk_all):
            sel = xk_all == xk
            col = self.colonne(10 ** 9 if adria else float(xk))
            sed, cs, ci, co, lith, d = col
            ys = self.isostasie(col)
            z = Y[sel] / KM - ys                   # profondeur sous la surface (km)
            l = np.full(z.size, AST, np.int8)
            l[z < lith] = ML
            o = sed
            l[(z >= 0) & (z < o)] = SED
            if co > 0:
                l[(z >= o) & (z < o + co)] = CO
                o += co
            l[(z >= o) & (z < o + cs)] = CS
            l[(z >= o + cs) & (z < o + cs + ci)] = CI
            l[z < 0] = AIR
            dd = np.where((l != AIR) & (l != AST), d, D0)
            # géotherme : continent en loi de puissance, océan en refroidissement de demi-espace
            zc = np.clip(z, 0, None)
            if co > 0 and cs == 0:
                kap, age = 1e-6, 60 * MA
                from scipy.special import erf
                tz = TP * erf(zc * KM / (2 * np.sqrt(kap * age)))
            else:
                tz = TP * np.clip(zc / lith, 0, 1) ** 0.8
            tz = np.minimum(tz, TP)          # manteau sous-lithosphérique à la température potentielle (Boussinesq)
            tz = np.where(z < 0, 0.0, tz)
            lit[sel], dom[sel], T[sel] = l, dd, tz + T0K
        return lit, dom, T, np.zeros(n), np.zeros(n, bool)

    # ---------------------------------------------------------------- interpolations
    def poids(self, X, Y, x0, y0, nx, ny):
        """Indices et poids bilinéaires sur une grille régulière d'origine (x0, y0), pas dx, dy."""
        fx = np.clip((X - x0) / self.dx, 0, nx - 1.000001)
        fy = np.clip((Y - y0) / self.dy, 0, ny - 1.000001)
        j = np.floor(fx).astype(int)
        i = np.floor(fy).astype(int)
        ax, ay = fx - j, fy - i
        return i, j, ax, ay

    def vers_marqueurs(self, F, x0, y0):
        ny, nx = F.shape
        i, j, ax, ay = self.poids(self.mx, self.my, x0, y0, nx, ny)
        return ((1 - ax) * (1 - ay) * F[i, j] + ax * (1 - ay) * F[i, j + 1]
                + (1 - ax) * ay * F[i + 1, j] + ax * ay * F[i + 1, j + 1])

    def vers_grille(self, vals, x0, y0, nx, ny, X=None, Y=None):
        X = self.mx if X is None else X
        Y = self.my if Y is None else Y
        i, j, ax, ay = self.poids(X, Y, x0, y0, nx, ny)
        num = np.zeros(nx * ny)
        den = np.zeros(nx * ny)
        for di, dj, w in ((0, 0, (1 - ax) * (1 - ay)), (0, 1, ax * (1 - ay)), (1, 0, (1 - ax) * ay), (1, 1, ax * ay)):
            k = (i + di) * nx + j + dj
            num += np.bincount(k, w * vals, nx * ny)
            den += np.bincount(k, w, nx * ny)
        return (num / np.maximum(den, 1e-30)).reshape(ny, nx), den.reshape(ny, nx)

    def vitesse_marqueurs(self, X, Y):
        Nx, Ny = self.Nx, self.Ny
        i, j, ax, ay = self.poids(X, Y, 0.0, -0.5 * self.dy, Nx, Ny + 1)
        V = self.vx
        vx = (1 - ax) * (1 - ay) * V[i, j] + ax * (1 - ay) * V[i, j + 1] + (1 - ax) * ay * V[i + 1, j] + ax * ay * V[i + 1, j + 1]
        i, j, ax, ay = self.poids(X, Y, -0.5 * self.dx, 0.0, Nx + 1, Ny)
        V = self.vy
        vy = (1 - ax) * (1 - ay) * V[i, j] + ax * (1 - ay) * V[i, j + 1] + (1 - ax) * ay * V[i + 1, j] + ax * ay * V[i + 1, j + 1]
        return vx, vy

    # ---------------------------------------------------------------- rhéologie
    def rheologie(self, EIIm, Pm):
        lit, T = self.lit, np.maximum(self.T, T0K + 1)
        eta = np.full(lit.size, ETA_AIR)
        rho = np.ones(lit.size)
        kk = np.zeros(lit.size)
        Hr = np.zeros(lit.size)
        plast = np.zeros(lit.size, bool)
        e = np.maximum(EIIm, 1e-18)
        u = np.clip(self.eps, 0, 1)
        for code, p in PROP.items():
            s = lit == code
            if not s.any():
                continue
            r0 = np.full(s.sum(), p["rho"])
            if code == CO:
                r0 = np.where(self.ecl[s], RHO_ECLOGITE, r0)
            rho[s] = r0 * (1 - ALPHA * (T[s] - T0K)) if code != AIR else 1.0
            kk[s], Hr[s] = p["k"], p["H"]
            if code == AIR:
                continue
            ev = ETA_SERP * np.ones(s.sum()) if p["flu"] is None else creep_eta(p["flu"], T[s], Pm[s], e[s])
            C = p["C"][0] + (p["C"][1] - p["C"][0]) * u[s]
            phi = np.radians(p["phi"][0] + (p["phi"][1] - p["phi"][0]) * u[s])
            sy = np.maximum(C + np.sin(phi) * np.maximum(Pm[s], 0), 1e6)
            ep = sy / (2 * e[s])
            pl = ep < ev
            # bandes de 40 km contre les parois : plaques rigides (ni plasticité ni fluage rapide)
            paroi = ((self.mx[s] < 40 * KM) | (self.mx[s] > self.L - 40 * KM)) & (code != AST)
            pl &= ~paroi
            ev = np.where(paroi, np.maximum(ev, 1e22), ev)
            eta[s] = np.clip(np.where(pl, ep, ev), 1e20 if code in (ML, AST) else ETA_MIN, ETA_MAX)
            plast[np.where(s)[0][pl]] = True
        return eta, rho, kk, Hr, plast

    # ---------------------------------------------------------------- Stokes
    def stokes(self, etas, etap, rho, dt, vbord):
        Nx, Ny, dx, dy = self.Nx, self.Ny, self.dx, self.dy
        N = (Nx + 1) * (Ny + 1) * 3
        Kc = 2 * 1e21 / (dx + dy)
        I, J, V = [], [], []
        R = np.zeros(N)
        ii, jj = np.meshgrid(np.arange(Ny + 1), np.arange(Nx + 1), indexing="ij")
        kvx = (jj * (Ny + 1) + ii) * 3
        kvy, kpm = kvx + 1, kvx + 2

        def ajoute(rows, cols, vals):
            rows, cols, vals = np.broadcast_arrays(rows, cols, vals)
            I.append(rows.ravel()); J.append(cols.ravel()); V.append(vals.ravel())

        # --- vx
        bord = (ii == 0) | (ii == Ny) | (jj == 0) | (jj >= Nx - 1)
        ajoute(kvx[bord], kvx[bord], 1.0)
        # valeurs imposées
        gauche = (jj == 0) & (ii > 0) & (ii < Ny)
        droite = (jj == Nx - 1) & (ii > 0) & (ii < Ny)
        R[kvx[droite]] = vbord[ii[droite]]
        haut = (ii == 0) & (jj > 0) & (jj < Nx - 1)
        ajoute(kvx[haut], kvx[haut] + 3, -1.0)                  # glissement libre
        basb = (ii == Ny) & (jj > 0) & (jj < Nx - 1)
        ajoute(kvx[basb], kvx[basb] - 3, -1.0)
        m = (ii > 0) & (ii < Ny) & (jj > 0) & (jj < Nx - 1)
        i, j, k = ii[m], jj[m], kvx[m]
        e1, e2 = etas[i - 1, j], etas[i, j]
        p1, p2 = etap[i, j], etap[i, j + 1]
        ajoute(k, kvx[i, j - 1], 2 * p1 / dx ** 2)
        ajoute(k, kvx[i, j + 1], 2 * p2 / dx ** 2)
        ajoute(k, kvx[i - 1, j], e1 / dy ** 2)
        ajoute(k, kvx[i + 1, j], e2 / dy ** 2)
        ajoute(k, k, -2 * (p1 + p2) / dx ** 2 - (e1 + e2) / dy ** 2)
        ajoute(k, kvy[i - 1, j], e1 / dx / dy)
        ajoute(k, kvy[i, j], -e2 / dx / dy)
        ajoute(k, kvy[i - 1, j + 1], -e1 / dx / dy)
        ajoute(k, kvy[i, j + 1], e2 / dx / dy)
        ajoute(k, kpm[i, j], Kc / dx)
        ajoute(k, kpm[i, j + 1], -Kc / dx)
        # --- vy
        bord = (ii == 0) | (ii >= Ny - 1) | (jj == 0) | (jj == Nx)
        ajoute(kvy[bord], kvy[bord], 1.0)
        gl = (jj == 0) & (ii > 0) & (ii < Ny - 1)
        ajoute(kvy[gl], kvy[gl] + 3 * (Ny + 1), 1.0)            # bords latéraux : vy nul à la paroi
        dr = (jj == Nx) & (ii > 0) & (ii < Ny - 1)
        ajoute(kvy[dr], kvy[dr] - 3 * (Ny + 1), 1.0)
        m = (ii > 0) & (ii < Ny - 1) & (jj > 0) & (jj < Nx)
        i, j, k = ii[m], jj[m], kvy[m]
        e1, e2 = etas[i, j - 1], etas[i, j]
        p1, p2 = etap[i, j], etap[i + 1, j]
        rv = 0.5 * (rho[i, j - 1] + rho[i, j])
        drdy = 0.25 * (rho[i + 1, j - 1] + rho[i + 1, j] - rho[i - 1, j - 1] - rho[i - 1, j]) / dy
        ajoute(k, kvy[i, j - 1], e1 / dx ** 2)
        ajoute(k, kvy[i, j + 1], e2 / dx ** 2)
        ajoute(k, kvy[i - 1, j], 2 * p1 / dy ** 2)
        ajoute(k, kvy[i + 1, j], 2 * p2 / dy ** 2)
        ajoute(k, k, -2 * (p1 + p2) / dy ** 2 - (e1 + e2) / dx ** 2 - 0.5 * dt * G * drdy)
        ajoute(k, kvx[i, j - 1], e1 / dx / dy)
        ajoute(k, kvx[i + 1, j - 1], -e1 / dx / dy)
        ajoute(k, kvx[i, j], -e2 / dx / dy)
        ajoute(k, kvx[i + 1, j], e2 / dx / dy)
        ajoute(k, kpm[i, j], Kc / dy)
        ajoute(k, kpm[i + 1, j], -Kc / dy)
        R[k] = -G * rv
        # --- continuité
        bord = (ii == 0) | (jj == 0) | (ii == Ny) | (jj == Nx) | ((ii == 1) & (jj == 1))
        ajoute(kpm[bord], kpm[bord], 1.0)
        m = ~bord
        i, j, k = ii[m], jj[m], kpm[m]
        ajoute(k, kvx[i, j], Kc / dx)
        ajoute(k, kvx[i, j - 1], -Kc / dx)
        ajoute(k, kvy[i, j], Kc / dy)
        ajoute(k, kvy[i - 1, j], -Kc / dy)
        A = sp.csc_matrix((np.concatenate(V), (np.concatenate(I), np.concatenate(J))), shape=(N, N))
        S = spla.spsolve(A, R)
        S = S.reshape(Nx + 1, Ny + 1, 3).transpose(1, 0, 2)
        self.vx, self.vy, self.P = S[..., 0].copy(), S[..., 1].copy(), S[..., 2] * Kc
        self.vx[:, Nx] = 0
        self.vy[Ny, :] = 0

    def deformation(self):
        Nx, Ny, dx, dy = self.Nx, self.Ny, self.dx, self.dy
        exx = np.zeros((Ny + 1, Nx + 1))
        exx[1:Ny, 1:Nx] = (self.vx[1:Ny, 1:Nx] - self.vx[1:Ny, 0:Nx - 1]) / dx
        exy = 0.5 * ((self.vx[1:Ny + 1, :Nx] - self.vx[0:Ny, :Nx]) / dy + (self.vy[:Ny, 1:Nx + 1] - self.vy[:Ny, 0:Nx]) / dx)
        e2 = np.zeros((Ny + 1, Nx + 1))
        e2[1:Ny, 1:Nx] = 0.25 * (exy[:-1, :-1] ** 2 + exy[1:, :-1] ** 2 + exy[:-1, 1:] ** 2 + exy[1:, 1:] ** 2)
        return np.sqrt(exx ** 2 + e2)

    # ---------------------------------------------------------------- chaleur
    def chaleur(self, rcp, kk, Hr, dt, Tg):
        Ny, Nx, dx, dy = self.Ny, self.Nx, self.dx, self.dy
        n = Nx * Ny
        idx = np.arange(n).reshape(Ny, Nx)
        I, J, V = [], [], []
        R = np.zeros(n)
        fixe = np.zeros((Ny, Nx), bool)
        fixe[0, :] = fixe[-1, :] = True
        f = idx[fixe]
        I.append(f); J.append(f); V.append(np.ones(f.size))
        R[idx[0, :]] = T0K
        R[idx[-1, :]] = self.Tbas
        m = ~fixe
        i, j = np.nonzero(m)
        k = idx[i, j]
        jl, jr = np.maximum(j - 1, 0), np.minimum(j + 1, Nx - 1)
        kl = 0.5 * (kk[i, j] + kk[i, jl]) * (j > 0)
        kr = 0.5 * (kk[i, j] + kk[i, jr]) * (j < Nx - 1)
        ku = 0.5 * (kk[i, j] + kk[i - 1, j])
        kd = 0.5 * (kk[i, j] + kk[i + 1, j])
        diag = rcp[i, j] / dt + (kl + kr) / dx ** 2 + (ku + kd) / dy ** 2
        for cols, c in ((idx[i, jl], -kl / dx ** 2), (idx[i, jr], -kr / dx ** 2), (idx[i - 1, j], -ku / dy ** 2), (idx[i + 1, j], -kd / dy ** 2)):
            I.append(k); J.append(cols); V.append(c)
        I.append(k); J.append(k); V.append(diag)
        R[k] = rcp[i, j] * Tg[i, j] / dt + Hr[i, j]
        A = sp.csr_matrix((np.concatenate(V), (np.concatenate(I), np.concatenate(J))), shape=(n, n))
        return spla.spsolve(A, R).reshape(Ny, Nx)

    # ---------------------------------------------------------------- surface
    def erosion(self, dt_an):
        """FastScape (fastscapelib) sur le profil + diffusion + sédimentation marine."""
        import fastscapelib as fs
        z = self.yair - self.topo - self.cfg.get("mer_m", 100.0)       # altitude par rapport à la mer (m)
        n = z.size
        statut = {int(i): fs.NodeStatus.FIXED_VALUE for i in np.nonzero(z <= 0)[0]}
        grille = fs.ProfileGrid(n, self.dx, [fs.NodeStatus.FIXED_VALUE, fs.NodeStatus.FIXED_VALUE], statut)
        graphe = fs.FlowGraph(grille, [fs.SingleFlowRouter(), fs.MSTSinkResolver()])
        zz = np.maximum(z, 0.0)
        graphe.update_routes(zz)
        Lup = graphe.accumulate(np.full(n, self.dx))                 # longueur drainée le long du profil
        aire = 13.6 * Lup ** 1.67                                    # loi de Hack (m², m)
        Kf = self.cfg.get("Kf", 4e-6)
        spl = fs.SPLEroder(graphe, Kf, 0.4, 1.0)
        ero = np.where(z > 0, spl.erode(zz, aire, dt_an), 0.0)
        z2 = z - np.minimum(ero, np.maximum(z, 0))
        kd = self.cfg.get("Kd", 0.05)
        z2[1:-1] += kd * dt_an / self.dx ** 2 * (z2[2:] - 2 * z2[1:-1] + z2[:-2]) * (z2[1:-1] > 0)
        mer = z2 < 0
        z2[mer] += np.minimum(-z2[mer], self.cfg.get("sedim_m_an", 2e-4) * dt_an)
        self.topo = self.topo - (z2 - z)
        self.erode_m = float(np.maximum(z - z2, 0).sum() * self.dx)

    # ---------------------------------------------------------------- pas de temps
    def avance(self):
        Nx, Ny, dx, dy = self.Nx, self.Ny, self.dx, self.dy
        if self.pas == 0:
            Pm = np.maximum(self.my - self.yair, 0) * 3000 * G
            self.EIIm = np.full(self.mx.size, 1e-15)
            self.Tbas = float(np.median(self.T[self.my > self.H - dy]))
        else:
            Pm = self.vers_marqueurs(self.P[1:Ny, 1:Nx], 0.5 * dx, 0.5 * dy)
        v = vitesse_adria(self.t, self.f35)
        roche = self.lit != AIR
        if self.pas == 0:
            vmax = 10 * v
        else:
            vxm, vym = self.vitesse_marqueurs(self.mx[roche], self.my[roche])
            vmax = max(np.abs(vxm).max(), np.abs(vym).max(), v)
        dt = min(0.25 * MA, 0.3 * dx / vmax)
        t_suivant = np.floor(self.t + 1e-9) + 1
        dt = min(dt, (t_suivant - self.t) * MA)
        # bord droit : l'Adria entre (air compris) jusqu'à 140 km de profondeur, le manteau ressort dessous
        yv = (np.arange(Ny + 1) - 0.5) * dy
        hin = self.yair + 120 * KM
        y1, y2 = hin - 20 * KM, hin + 60 * KM
        f = np.interp(yv, [y1, y2], [-1.0, 1.0])
        f[yv < self.topo[-1]] = 0.0                  # l'air ne traverse pas la paroi
        ins = np.clip(-f, 0, None).sum()
        outs = np.clip(f, 0, None).sum()
        vb = v * np.where(f < 0, f, f * ins / outs)
        for it in range(2):
            eta, rho, kk, Hr, plast = self.rheologie(self.EIIm, Pm)
            lg, _ = self.vers_grille(np.log10(eta), 0, 0, Nx, Ny)
            etas = 10 ** lg
            rg, _ = self.vers_grille(rho, 0, 0, Nx, Ny)
            lp, _ = self.vers_grille(np.log10(eta), -0.5 * dx, -0.5 * dy, Nx + 1, Ny + 1)
            etap = 10 ** lp
            self.stokes(etas, etap, rg, dt, vb)
            EII = self.deformation()
            self.EIIm = np.maximum(self.vers_marqueurs(EII[1:Ny, 1:Nx], 0.5 * dx, 0.5 * dy), 1e-18)
            Pm = self.vers_marqueurs(self.P[1:Ny, 1:Nx], 0.5 * dx, 0.5 * dy)
        # chaleur
        Tg, _ = self.vers_grille(self.T, 0, 0, Nx, Ny)
        rcp, _ = self.vers_grille(np.where(self.lit == AIR, 3e6, rho * 1000.0), 0, 0, Nx, Ny)
        kg, _ = self.vers_grille(kk, 0, 0, Nx, Ny)
        hg, _ = self.vers_grille(Hr, 0, 0, Nx, Ny)
        T2 = self.chaleur(rcp, kg, hg, dt, Tg)
        self.T += self.vers_marqueurs(T2 - Tg, 0, 0)
        self.T[self.lit == AIR] = T0K
        # déformation plastique cumulée, éclogitisation
        self.eps[plast] += self.EIIm[plast] * dt
        self.ecl |= (self.lit == CO) & (Pm > 1.5e9)
        # advection des marqueurs (Runge-Kutta 2) et de la surface
        vx1, vy1 = self.vitesse_marqueurs(self.mx, self.my)
        vx2, vy2 = self.vitesse_marqueurs(self.mx + 0.5 * dt * vx1, self.my + 0.5 * dt * vy1)
        self.mx += dt * vx2
        self.my += dt * vy2
        xt = self.x.copy()
        tx, ty = self.vitesse_marqueurs(xt, self.topo)
        xt2, yt2 = xt + dt * tx, self.topo + dt * ty
        o = np.argsort(xt2)
        self.topo = np.interp(self.x, xt2[o], yt2[o])
        self.erosion(dt / AN)
        self.renouvelle(dt, v, hin)
        # air / roche selon la surface
        st = np.interp(self.mx, self.x, self.topo)
        mange = (self.lit != AIR) & (self.my < st)
        self.lit[mange], self.dom[mange], self.eps[mange] = AIR, D0, 0
        depose = (self.lit == AIR) & (self.my > st)
        self.lit[depose], self.dom[depose] = SED, SYN
        self.t += dt / MA
        if abs(self.t - round(self.t)) < 1e-6:
            self.t = float(round(self.t))
        self.pas += 1
        return dt

    def renouvelle(self, dt, v, hin):
        """Retire les marqueurs sortis, injecte l'Adria au bord droit, comble les mailles vides."""
        dedans = (self.mx >= 0) & (self.mx <= self.L) & (self.my >= 0) & (self.my <= self.H)
        suivis = {k: i for k, i in self.suivis.items()}
        if not dedans.all():
            nouv = np.cumsum(dedans) - 1
            for k, i in suivis.items():
                self.suivis[k] = int(nouv[i]) if dedans[i] else -1
            self.garde(dedans)
        # injection : bande de largeur v dt au bord droit, jusqu'à hin
        dens = self.nm ** 2 / (self.dx * self.dy)
        w = v * dt
        nn = self.rng.poisson(dens * w * (hin - self.topo[-1]))
        if nn > 0:
            X = self.L - self.rng.random(nn) * w
            sa = self.topo[-1]
            Y = sa + self.rng.random(nn) * (hin - sa)
            ys0 = self.isostasie(self.colonne(10 ** 9)) * KM
            # cale la colonne injectée sur la surface actuelle du bord droit
            lit2, dom2, T2, _, _ = self.proprietes(X, Y - (sa - ys0), adria=True)
            self.ajoute(X, Y, lit2, dom2, T2)
        # mailles vides
        cx = np.clip((self.mx / self.dx).astype(int), 0, self.Nx - 2)
        cy = np.clip((self.my / self.dy).astype(int), 0, self.Ny - 2)
        cnt = np.bincount(cy * (self.Nx - 1) + cx, minlength=(self.Nx - 1) * (self.Ny - 1))
        vides = np.nonzero(cnt == 0)[0]
        if vides.size:
            X = ((vides % (self.Nx - 1)) + self.rng.random(vides.size)) * self.dx
            Y = ((vides // (self.Nx - 1)) + self.rng.random(vides.size)) * self.dy
            _, near = cKDTree(np.c_[self.mx, self.my]).query(np.c_[X, Y])
            self.ajoute(X, Y, self.lit[near], self.dom[near], self.T[near], self.eps[near], self.ecl[near])
        self.vides = int(vides.size)

    def garde(self, s):
        for a in ("mx", "my", "lit", "dom", "T", "eps", "ecl", "EIIm"):
            setattr(self, a, getattr(self, a)[s])

    def ajoute(self, X, Y, lit, dom, T, eps=None, ecl=None):
        n = X.size
        self.mx = np.r_[self.mx, X]; self.my = np.r_[self.my, Y]
        self.lit = np.r_[self.lit, lit].astype(np.int8); self.dom = np.r_[self.dom, dom].astype(np.int8)
        self.T = np.r_[self.T, T]
        self.eps = np.r_[self.eps, np.zeros(n) if eps is None else eps]
        self.ecl = np.r_[self.ecl, np.zeros(n, bool) if ecl is None else ecl]
        self.EIIm = np.r_[self.EIIm, np.full(n, 1e-15)]

    # ---------------------------------------------------------------- sorties
    def image(self, prof_km=200.0, fin=2):
        """Matériau dominant (code domaine*8 + lithologie) sur une grille de pas dx/fin, jusqu'à prof_km."""
        p = self.dx / fin
        nx = int(round(self.L / p))
        nz = int(round(prof_km * KM / p))
        code = (self.dom.astype(np.int32) * 8 + self.lit).astype(np.int32)
        jx = np.clip((self.mx / p).astype(int), 0, nx - 1)
        iz = (self.my / p).astype(int)
        s = iz < nz
        cell = iz[s] * nx + jx[s]
        comp = np.zeros((nx * nz, 64), np.int32)
        np.add.at(comp, (cell, code[s]), 1)
        out = np.where(comp.sum(1) > 0, comp.argmax(1), 255).astype(np.uint8).reshape(nz, nx)
        return out

    def etat(self):
        return dict(t=self.t, topo_m=(self.yair - self.topo - self.cfg.get("mer_m", 100.0)).astype(np.float32),
                    image=self.image(),
                    suivi={k: (float(self.mx[i] / KM) if i >= 0 else np.nan) for k, i in self.suivis.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("nom")
    ap.add_argument("sortie")
    ap.add_argument("--pas-km", type=float, default=5.0)
    ap.add_argument("--budget-s", type=float, default=1e9)
    ap.add_argument("--jusqua", type=float, default=0.0)
    a = ap.parse_args()
    cfg = next(c for c in json.load(open(a.config))["coupes"] if c["nom"] == a.nom)
    reprise = a.sortie + ".reprise.npz"
    t0 = time.time()
    if os.path.exists(reprise):
        import pickle
        M, images = pickle.load(open(reprise, "rb"))
        print(f"reprise à {M.t:.2f} Ma", flush=True)
    else:
        M = Modele(cfg, a.pas_km, seed=cfg.get("graine", 0))
        images = [M.etat()]
    while M.t < a.jusqua - 1e-9:
        dt = M.avance()
        if abs(M.t - round(M.t)) < 1e-9:
            images.append(M.etat())
            e = images[-1]
            print(f"{M.t:6.1f} Ma  pas {M.pas:5d}  dt {dt/MA*1e3:5.0f} ka  alt max {e['topo_m'].max():6.0f} m  "
                  f"marqueurs {M.mx.size}  vides {M.vides}  {time.time()-t0:7.0f} s", flush=True)
            if time.time() - t0 > a.budget_s and M.t < a.jusqua - 1e-9:
                import pickle
                pickle.dump((M, images), open(reprise, "wb"))
                print("budget atteint : état sauvé pour reprise", flush=True)
                return 3
    np.savez_compressed(a.sortie, t=np.array([e["t"] for e in images]),
                        topo=np.array([e["topo_m"] for e in images]),
                        image=np.array([e["image"] for e in images]),
                        suivi=json.dumps({k: [e["suivi"][k] for e in images] for k in images[0]["suivi"]}),
                        pas_km=M.dx / KM, config=json.dumps(cfg), pas=M.pas)
    if os.path.exists(reprise):
        os.remove(reprise)
    return 0


if __name__ == "__main__":
    sys.exit(main())
