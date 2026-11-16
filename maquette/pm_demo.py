"""Démonstration jetable : simulation N-corps particle-mesh (PM) minimale.
Boîte périodique, conditions initiales de Zel'dovich à a=0.02, intégration
kick-drift-kick en a, sauvegarde des positions à plusieurs époques.
Unités : Mpc/h, H0 = 100 h km/s/Mpc.
"""
import numpy as np, scipy.fft as sfft, sys, time, os
from scipy.integrate import quad

NP = int(sys.argv[1]) if len(sys.argv) > 1 else 192    # particules par côté
NM = int(sys.argv[2]) if len(sys.argv) > 2 else 288    # maille PM par côté
L = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0  # Mpc/h
OUT = sys.argv[4] if len(sys.argv) > 4 else "/home/claude/demo/out"
os.makedirs(OUT, exist_ok=True)
Om, Ob, h, ns, s8 = 0.315, 0.049, 0.674, 0.965, 0.811
OL = 1 - Om
H0 = 100.0
W = 2

E = lambda a: np.sqrt(Om / a**3 + OL)
H = lambda a: H0 * E(a)
def Dgrow(a):
    I = quad(lambda x: 1 / (x * E(x))**3, 0, a)[0]
    return 2.5 * Om * E(a) * I
D1 = Dgrow(1.0)
D = lambda a: Dgrow(a) / D1
f_growth = lambda a: (Om / a**3 / E(a)**2) ** 0.55

def T_EH_nowiggle(k):  # k en h/Mpc
    omh2, obh2 = Om * h * h, Ob * h * h
    fb = Ob / Om
    s = 44.5 * np.log(9.83 / omh2) / np.sqrt(1 + 10 * obh2**0.75)
    aG = 1 - 0.328 * np.log(431 * omh2) * fb + 0.38 * np.log(22.3 * omh2) * fb**2
    kk = k * h
    Geff = Om * h * (aG + (1 - aG) / (1 + (0.43 * kk * s)**4))
    q = k * (2.7255 / 2.7)**2 / Geff
    L0 = np.log(2 * np.e + 1.8 * q)
    C0 = 14.2 + 731 / (1 + 62.5 * q)
    return L0 / (L0 + C0 * q * q)

def P_unnorm(k):
    return k**ns * T_EH_nowiggle(k)**2
def sigma_R(R, A=1.0):
    def integrand(lk):
        k = np.exp(lk); x = k * R
        Wt = 3 * (np.sin(x) - x * np.cos(x)) / x**3
        return A * P_unnorm(k) * Wt**2 * k**3 / (2 * np.pi**2)
    return np.sqrt(quad(integrand, np.log(1e-4), np.log(1e2), limit=400)[0])
Anorm = (s8 / sigma_R(8.0))**2
P = lambda k: Anorm * P_unnorm(k)

rng = np.random.default_rng(31415)
t0 = time.time()
# --- conditions initiales sur la grille des particules ---
kf = 2 * np.pi / L
kx = sfft.fftfreq(NP, d=1.0 / NP) * kf
kz = sfft.rfftfreq(NP, d=1.0 / NP) * kf
KX, KY, KZ = kx[:, None, None], kx[None, :, None], kz[None, None, :]
K2 = KX**2 + KY**2 + KZ**2 + 0 * KX
K2[0, 0, 0] = 1.0
wn = rng.standard_normal((NP, NP, NP)).astype(np.float32)
dk = sfft.rfftn(wn, workers=W)
del wn
amp = np.sqrt(P(np.sqrt(K2)) / L**3) * NP**1.5  # convention FFT non normalisée
amp[0, 0, 0] = 0.0
dk = (dk * amp).astype(np.complex64)
del amp
q1 = (np.arange(NP) + 0.5) * (L / NP)
QX, QY, QZ = np.meshgrid(q1, q1, q1, indexing="ij")
psi = []
for Kc in (KX, KY, KZ):
    psi.append(sfft.irfftn(1j * Kc / K2 * dk, s=(NP,) * 3, workers=W).astype(np.float32).ravel())
del dk, KX, KY, KZ, K2
psi = np.stack(psi, 1)
print("rms psi (Mpc/h) a=1 :", float(np.sqrt((psi**2).sum(1).mean())), flush=True)
ai = 0.02
x = np.stack([QX.ravel(), QY.ravel(), QZ.ravel()], 1).astype(np.float32)
del QX, QY, QZ
x = (x + D(ai) * psi) % L
p = (ai**3 * H(ai) * f_growth(ai) * D(ai) * psi).astype(np.float32)  # p = a^2 dx/dt
del psi
print("CI en %.1fs" % (time.time() - t0), flush=True)

# --- PM ---
mk = sfft.fftfreq(NM, d=1.0 / NM) * kf
mkz = sfft.rfftfreq(NM, d=1.0 / NM) * kf
MX, MY, MZ = mk[:, None, None].astype(np.float32), mk[None, :, None].astype(np.float32), mkz[None, None, :].astype(np.float32)
MK2 = (MX**2 + MY**2 + MZ**2).astype(np.float32)
MK2[0, 0, 0] = 1.0
cell = L / NM

def cic_weights(x):
    g = x / cell - 0.5
    i0 = np.floor(g).astype(np.int64)
    d = (g - i0).astype(np.float32)
    return i0 % NM, d

def deposit(x):
    i0, d = cic_weights(x)
    rho = np.zeros(NM**3, np.float32)
    for ox in (0, 1):
        wx = d[:, 0] if ox else 1 - d[:, 0]
        ix = (i0[:, 0] + ox) % NM
        for oy in (0, 1):
            wy = d[:, 1] if oy else 1 - d[:, 1]
            iy = (i0[:, 1] + oy) % NM
            for oz in (0, 1):
                wz = d[:, 2] if oz else 1 - d[:, 2]
                iz = (i0[:, 2] + oz) % NM
                rho += np.bincount((ix * NM + iy) * NM + iz, weights=wx * wy * wz, minlength=NM**3).astype(np.float32)
    return rho.reshape(NM, NM, NM), (i0, d)

def interp(field, cache):
    i0, d = cache
    f = field.ravel()
    out = np.zeros(len(i0), np.float32)
    for ox in (0, 1):
        wx = d[:, 0] if ox else 1 - d[:, 0]
        ix = (i0[:, 0] + ox) % NM
        for oy in (0, 1):
            wy = d[:, 1] if oy else 1 - d[:, 1]
            iy = (i0[:, 1] + oy) % NM
            for oz in (0, 1):
                wz = d[:, 2] if oz else 1 - d[:, 2]
                iz = (i0[:, 2] + oz) % NM
                out += f[(ix * NM + iy) * NM + iz] * (wx * wy * wz)
    return out

def accel(x, a):
    rho, cache = deposit(x)
    delta = rho / rho.mean() - 1.0
    dk = sfft.rfftn(delta, workers=W)
    # déconvolution CIC (deux fois : dépôt + interpolation)
    Wc = (np.sinc(MX / kf / NM) * np.sinc(MY / kf / NM) * np.sinc(MZ / kf / NM))**2
    phik = -1.5 * Om * H0**2 / a * dk / MK2 / (Wc**2 + 1e-6)
    phik[0, 0, 0] = 0
    g = np.empty_like(x)
    for c, Kc in enumerate((MX, MY, MZ)):
        gc = sfft.irfftn(-1j * Kc * phik, s=(NM,) * 3, workers=W).astype(np.float32)
        g[:, c] = interp(gc, cache)
    return g  # = -grad(phi)

saves = [0.15, 0.25, 0.4, 0.6, 1.0]
nsteps = int(sys.argv[5]) if len(sys.argv) > 5 else 40
agrid = np.exp(np.linspace(np.log(ai), 0.0, nsteps + 1))
# insérer les époques de sauvegarde
agrid = np.unique(np.concatenate([agrid, saves]))
g = accel(x, ai)
for n in range(len(agrid) - 1):
    a0, a1 = agrid[n], agrid[n + 1]
    ah = np.sqrt(a0 * a1)
    p += g * quad(lambda a: 1 / (a * H(a)), a0, ah)[0]
    x = (x + p * quad(lambda a: 1 / (a**3 * H(a)), a0, a1)[0]) % L
    g = accel(x, a1)
    p += g * quad(lambda a: 1 / (a * H(a)), ah, a1)[0]
    if any(abs(a1 - s) < 1e-9 for s in saves):
        np.save(f"{OUT}/x_a{a1:.2f}.npy", x)
        print("sauvé a=%.2f  t=%.0fs" % (a1, time.time() - t0), flush=True)
    else:
        print("pas %d/%d a=%.3f t=%.0fs" % (n + 1, len(agrid) - 1, a1, time.time() - t0), flush=True)
print("FIN", flush=True)
