"""Simulation N-corps particle-mesh (PM) économe en mémoire, pour GitHub Actions.

Boîte périodique, conditions initiales de Zel'dovich à a_init, intégration
kick-drift-kick en facteur d'échelle, instantanés quantifiés en uint16 (sur disque).
Unités : Mpc/h, H0 = 100 h km/s/Mpc. Cosmologie Planck 2018 (celle du projet).

Usage : python pm.py NP NM L SORTIE [PAS] [GRAINE]

Variables d'environnement (version 2, 17/11/2026, plan « fond de carte » P2/P5) :
  NSORTIES=32  instantanés régulièrement espacés en facteur de croissance D entre z = 14 et
               aujourd'hui (les particules bougent d'autant entre deux instantanés : une
               interpolation régulière suffit) ; les pas de temps sont ces instantanés mêmes.
  FOULE=8      on ne sauve qu'une particule sur FOULE (indices fixes, donc suivies d'un
               instantané à l'autre), positions ET vitesses particulières (km/s, float16).
"""
import numpy as np, scipy.fft as sfft, sys, time, os, json
from scipy.integrate import quad

NP, NM, L = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
OUT = sys.argv[4]
NSTEPS = int(sys.argv[5]) if len(sys.argv) > 5 else 48
GRAINE = int(sys.argv[6]) if len(sys.argv) > 6 else 31415
os.makedirs(OUT, exist_ok=True)
Om, Ob, h, ns, s8 = 0.315, 0.049, 0.674, 0.965, 0.811
OL = 1 - Om
H0 = 100.0
W = os.cpu_count() or 2
CH = 1 << 23                       # taille des paquets de particules (8 M)
ZS = [14, 10, 7, 5, 3.5, 2.5, 1.7, 1.0, 0.5, 0.2, 0.0]
SAVES = [1 / (1 + z) for z in ZS]
AI = 0.02
NSORTIES = int(os.environ.get("NSORTIES", "0")); FOULE = int(os.environ.get("FOULE", "1"))

E = lambda a: np.sqrt(Om / a**3 + OL)
Hf = lambda a: H0 * E(a)
def Dgrow(a): return 2.5 * Om * E(a) * quad(lambda x: 1 / (x * E(x))**3, 0, a)[0]
D1 = Dgrow(1.0); D = lambda a: Dgrow(a) / D1
fg = lambda a: (Om / a**3 / E(a)**2) ** 0.55

def T_EH(k):
    omh2, obh2, fb = Om * h * h, Ob * h * h, Ob / Om
    s = 44.5 * np.log(9.83 / omh2) / np.sqrt(1 + 10 * obh2**0.75)
    aG = 1 - 0.328 * np.log(431 * omh2) * fb + 0.38 * np.log(22.3 * omh2) * fb**2
    Geff = Om * h * (aG + (1 - aG) / (1 + (0.43 * k * h * s)**4))
    q = k * (2.7255 / 2.7)**2 / Geff
    L0 = np.log(2 * np.e + 1.8 * q); C0 = 14.2 + 731 / (1 + 62.5 * q)
    return L0 / (L0 + C0 * q * q)
Pu = lambda k: k**ns * T_EH(k)**2
def sig(R):
    f = lambda lk: (lambda k, x: Pu(k) * (3 * (np.sin(x) - x * np.cos(x)) / x**3)**2 * k**3 / (2 * np.pi**2))(np.exp(lk), np.exp(lk) * R)
    return np.sqrt(quad(f, np.log(1e-4), np.log(1e2), limit=400)[0])
A = (s8 / sig(8.0))**2
P = lambda k: A * Pu(k)

t0 = time.time()
log = lambda *m: print("[%6.0fs]" % (time.time() - t0), *m, flush=True)
kf = 2 * np.pi / L

# ---- conditions initiales ----
rng = np.random.default_rng(GRAINE)
k1 = (sfft.fftfreq(NP, d=1.0 / NP) * kf).astype(np.float32)
kz = (sfft.rfftfreq(NP, d=1.0 / NP) * kf).astype(np.float32)
dk = sfft.rfftn(rng.standard_normal((NP, NP, NP), dtype=np.float32), workers=W)
K2 = k1[:, None, None]**2 + k1[None, :, None]**2 + kz[None, None, :]**2
K2[0, 0, 0] = 1
dk *= (np.sqrt(P(np.sqrt(K2)) / L**3) * NP**1.5).astype(np.float32)
dk[0, 0, 0] = 0
dk /= K2; del K2
x = np.empty((NP**3, 3), np.float32); p = np.empty((NP**3, 3), np.float32)
q1 = ((np.arange(NP) + 0.5) * (L / NP)).astype(np.float32)
# GIGUE=1 (18/11, chantier D) : positions de départ tirées au hasard dans leur cellule. Sans cela, aux
# époques jeunes, la tranche projetée garde la grille de départ (toutes les couches en z tombent sur
# les mêmes colonnes) : un treillis aligné sur les axes, visible quand on zoome.
GIGUE = os.environ.get("GIGUE", "0") == "1"
rg = np.random.default_rng(GRAINE + 1)
for c, kc in enumerate((k1[:, None, None], k1[None, :, None], kz[None, None, :])):
    psi = sfft.irfftn(1j * kc * dk, s=(NP,) * 3, workers=W).astype(np.float32)
    qc = np.broadcast_to(q1[:, None, None] if c == 0 else q1[None, :, None] if c == 1 else q1[None, None, :], (NP,) * 3)
    gq = (rg.random(NP**3, dtype=np.float32) - 0.5) * np.float32(L / NP) if GIGUE else 0
    x[:, c] = ((qc.ravel() + gq + D(AI) * psi.ravel()) % L)
    p[:, c] = (AI**3 * Hf(AI) * fg(AI) * D(AI) * psi).ravel()
    del psi
del dk
log("conditions initiales", NP, "^3, boîte", L)

# ---- particle-mesh ----
m1 = (sfft.fftfreq(NM, d=1.0 / NM) * kf).astype(np.float32)
mz = (sfft.rfftfreq(NM, d=1.0 / NM) * kf).astype(np.float32)
MX, MY, MZ = m1[:, None, None], m1[None, :, None], mz[None, None, :]
cell = L / NM

def corners(xs):
    g = xs / cell - 0.5
    i0 = np.floor(g).astype(np.int32)
    d = (g - i0).astype(np.float32)
    return i0 % NM, d

def deposit():
    rho = np.zeros(NM**3, np.float64)
    for s0 in range(0, len(x), CH):
        i0, d = corners(x[s0:s0 + CH])
        for ox in (0, 1):
            wx = d[:, 0] if ox else 1 - d[:, 0]; ix = (i0[:, 0] + ox) % NM
            for oy in (0, 1):
                wy = d[:, 1] if oy else 1 - d[:, 1]; iy = (i0[:, 1] + oy) % NM
                wxy = wx * wy; base = (ix.astype(np.int64) * NM + iy) * NM
                for oz in (0, 1):
                    wz = d[:, 2] if oz else 1 - d[:, 2]; iz = (i0[:, 2] + oz) % NM
                    rho += np.bincount(base + iz, weights=wxy * wz, minlength=NM**3)
    return rho.reshape(NM, NM, NM)

def interp(field, out_col, acc):
    f = field.ravel()
    for s0 in range(0, len(x), CH):
        i0, d = corners(x[s0:s0 + CH])
        r = np.zeros(len(i0), np.float32)
        for ox in (0, 1):
            wx = d[:, 0] if ox else 1 - d[:, 0]; ix = (i0[:, 0] + ox) % NM
            for oy in (0, 1):
                wy = d[:, 1] if oy else 1 - d[:, 1]; iy = (i0[:, 1] + oy) % NM
                wxy = wx * wy; base = (ix.astype(np.int64) * NM + iy) * NM
                for oz in (0, 1):
                    wz = d[:, 2] if oz else 1 - d[:, 2]; iz = (i0[:, 2] + oz) % NM
                    r += f[base + iz] * (wxy * wz)
        acc[s0:s0 + CH, out_col] = r

def accel(a, acc):
    rho = deposit()
    delta = (rho / rho.mean() - 1.0).astype(np.float32); del rho
    dkm = sfft.rfftn(delta, workers=W); del delta
    sx = np.sinc(MX / kf / NM); sy = np.sinc(MY / kf / NM); sz = np.sinc(MZ / kf / NM)
    Wc2 = (sx * sy * sz)**4
    K2 = MX**2 + MY**2 + MZ**2; K2[0, 0, 0] = 1
    phik = (-1.5 * Om * H0**2 / a) * dkm / K2 / (Wc2 + 1e-6); phik[0, 0, 0] = 0
    del dkm, K2, Wc2
    for c, Kc in enumerate((MX, MY, MZ)):
        g = sfft.irfftn(-1j * Kc * phik, s=(NM,) * 3, workers=W).astype(np.float32)
        interp(g, c, acc); del g

def sauve(a):
    if FOULE > 1:
        q = np.round(np.mod(x[::FOULE], L) / L * 65535).astype(np.uint16)
        np.save(f"{OUT}/snap_a{a:.4f}.npy", q); del q
        np.save(f"{OUT}/vit_a{a:.4f}.npy", (p[::FOULE] / np.float32(a)).astype(np.float16))   # v = p / a, en km/s
    else:
        q = np.round(np.mod(x, L) / L * 65535).astype(np.uint16)
        np.save(f"{OUT}/snap_a{a:.4f}.npy", q); del q
    log("instantané a=%.4f (z=%.2f)" % (a, 1 / a - 1))

if NSORTIES:
    # instantanés réguliers en D de a = 1/15 à 1 ; avant, des pas réguliers en ln a
    from scipy.optimize import brentq
    Ds = np.linspace(D(1 / 15), 1.0, NSORTIES)
    SAVES = [float(brentq(lambda a: D(a) - d, 1e-3, 1.0001)) for d in Ds]; SAVES[-1] = 1.0
    ZS = [1 / a - 1 for a in SAVES]
    agrid = np.unique(np.concatenate([np.exp(np.linspace(np.log(AI), np.log(SAVES[0]), 13)), SAVES]))
else:
  agrid = np.unique(np.concatenate([np.exp(np.linspace(np.log(AI), 0.0, NSTEPS + 1)), SAVES]))
agrid = agrid[agrid >= AI]
acc = np.empty_like(x)
accel(AI, acc)
for n in range(len(agrid) - 1):
    a0, a1 = agrid[n], agrid[n + 1]; ah = np.sqrt(a0 * a1)
    p += acc * np.float32(quad(lambda a: 1 / (a * Hf(a)), a0, ah)[0])
    x += p * np.float32(quad(lambda a: 1 / (a**3 * Hf(a)), a0, a1)[0]); np.mod(x, L, out=x)
    accel(a1, acc)
    p += acc * np.float32(quad(lambda a: 1 / (a * Hf(a)), ah, a1)[0])
    if any(abs(a1 - s) < 1e-9 for s in SAVES): sauve(a1)
    else: log("pas %d/%d a=%.4f" % (n + 1, len(agrid) - 1, a1))
json.dump({"NP": NP, "NM": NM, "L": L, "saves": [float(v) for v in SAVES], "z": [float(v) for v in ZS], "graine": GRAINE, "foule": FOULE}, open(f"{OUT}/meta.json", "w"))
log("FIN")
