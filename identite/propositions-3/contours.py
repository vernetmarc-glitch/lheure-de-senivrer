import numpy as np
from scipy.ndimage import gaussian_filter
def poly_verre():
    L = []
    pts = [(0.16 + 0.42 * k / 100, 0.235 * (1 - (k / 100) ** 2.2) ** 0.55) for k in range(101)]
    L.append([(0.5 - h, y) for y, h in pts] + [(0.5 + h, y) for y, h in pts][::-1])
    L.append([(0.5 - 0.235, 0.16), (0.5 + 0.235, 0.16)])
    L.append([(0.5, 0.58), (0.5, 0.80)])
    L.append([(0.5 + 0.14 * np.cos(a), 0.81 + 0.025 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 80)])
    return L
def poly_sablier():
    e = 0.012; L = []
    for sx in (-1, 1):
        c = []
        for k in range(101):
            u = k / 100; yy = 0.13 + 0.74 * u; z = abs(u - 0.5) * 2
            h = e + (0.215 - e) * (z ** 1.6) * (1 + 0.15 * np.sin(np.pi * z)); c.append((0.5 + sx * h, yy))
        L.append(c)
    L.append([(0.25, 0.12), (0.75, 0.12)]); L.append([(0.25, 0.88), (0.75, 0.88)])
    return L
def etoiles(L, N, pas=0.0055, graine=1, sig=(1.4, 3.2)):
    """un contour fait d'un chapelet de petites lueurs, irrégulier, qui respire"""
    rg = np.random.default_rng(graine); I = np.zeros((N, N))
    for p in L:
        p = np.array(p); seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
        n = max(2, int(s[-1] / pas)); t = np.sort(rg.uniform(0, s[-1], n))
        x = np.interp(t, s, p[:, 0]) + rg.normal(0, 0.0025, n); y = np.interp(t, s, p[:, 1]) + rg.normal(0, 0.0025, n)
        w = rg.uniform(0.25, 1.0, n) ** 2
        for xi, yi, wi in zip(x, y, w):
            i, j = int(yi * N), int(xi * N)
            if 0 <= i < N and 0 <= j < N: I[i, j] += wi
    fin = gaussian_filter(I, sig[0]) * 2 * np.pi * sig[0] ** 2
    lueur = gaussian_filter(I, 9) * 2 * np.pi * 9 ** 2 * 0.05
    return fin, lueur
