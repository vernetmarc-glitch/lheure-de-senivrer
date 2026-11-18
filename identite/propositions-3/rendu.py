import numpy as np
from scipy.ndimage import gaussian_filter
P = np.load('pts.npz'); XY, Hh = P['xy'], P['h']
HL = 2.0 ** (Hh / 16 - 14)              # h / L
C = [(0,(0,0,0)),(0.22,(0.06,0.04,0.26)),(0.45,(0.40,0.10,0.52)),(0.65,(0.90,0.32,0.30)),(0.82,(1.0,0.70,0.32)),(0.93,(1.0,0.93,0.70)),(1.0,(1,1,1))]
def palette(t):
    t = np.clip(t, 0, 1); out = np.zeros(t.shape + (3,))
    for (a, ca), (b_, cb) in zip(C[:-1], C[1:]):
        m = (t >= a) & (t <= b_); f = ((t - a) / (b_ - a))[m][:, None]
        out[m] = np.array(ca) * (1 - f) + np.array(cb) * f
    return out
def densite(cx, cy, demi, N=1024, smin=0.9, smax=40, ech=1.0):
    u = (XY - [cx, cy]); u = (u + 0.5) % 1 - 0.5            # périodique
    k = (np.abs(u[:, 0]) < demi * 1.2) & (np.abs(u[:, 1]) < demi * 1.2)
    u = u[k]; sig = np.clip(0.5 * HL[k] / (2 * demi) * N * ech, smin, smax)
    D = np.zeros((N, N))
    edges = np.geomspace(smin, smax + 1e-6, 14)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (sig >= a) & (sig < b)
        if not m.any(): continue
        Hg, _, _ = np.histogram2d((-u[m, 1] / (2 * demi) + 0.5) * N, (u[m, 0] / (2 * demi) + 0.5) * N, bins=N, range=[[0, N], [0, N]])
        D += gaussian_filter(Hg, np.sqrt(a * b))
    return D
def ton(D, m, contraste=1.0, gain=1.0, glow=0.25):
    G = gaussian_filter(D, D.shape[0] / 128)
    dl = np.log10(1 + D / m) + glow * np.log10(1 + G / m)
    dl = 0.30103 + (dl - 0.30103) * contraste
    return palette(np.clip((dl - 0.30) / 1.7, 0, 1)) * gain
def charge(nom):
    global XY, HL
    P = np.load(nom); XY = P['xy']; HL = 2.0 ** (P['h'] / 16 - 14)
