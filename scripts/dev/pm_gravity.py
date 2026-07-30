"""Particle-Mesh cosmologique minimal (numpy) + metriques de ponctualite.

Pourquoi : l'approximation de Zel'dovich est LINEAIRE et cesse d'etre valable au
croisement des trajectoires. Les particules traversent la caustique et se
dispersent -> noeuds etales en taches, sous-structure detruite.
En laissant la gravite agir apres le croisement, les noeuds se virialisent en
amas compacts et la hierarchie (fractalite) apparait.

Schema : leapfrog kick-drift-kick, temps = facteur d'echelle a.
  dx/da = u / (a^2 E(a))
  du/da = -grad(phi) / (a^2 E(a))     avec   lap(phi) = 1.5 * Omega_m * delta / a
CIC n'est utilise QUE pour le calcul des forces (interne). La sortie reste les
positions continues des particules.
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M

OMEGA_M = 0.315
OMEGA_L = 1.0 - OMEGA_M


def E(a):
    return np.sqrt(OMEGA_M / a ** 3 + OMEGA_L)


def cic_deposit(x, ng, box):
    """Depot CIC -> densite de contraste. Usage INTERNE (forces) uniquement."""
    g = (x + box / 2.0) / box * ng
    i0 = np.floor(g).astype(np.int32)
    f = (g - i0).astype(np.float32)
    rho = np.zeros((ng, ng, ng), np.float32)
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1 - f[:, 0]
        ix = (i0[:, 0] + dx) % ng
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1 - f[:, 1]
            iy = (i0[:, 1] + dy) % ng
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1 - f[:, 2]
                iz = (i0[:, 2] + dz) % ng
                np.add.at(rho, (ix, iy, iz), wx * wy * wz)
    rho *= ng ** 3 / len(x)
    return rho - 1.0


def cic_sample(field, x, ng, box):
    g = (x + box / 2.0) / box * ng
    i0 = np.floor(g).astype(np.int32)
    f = (g - i0).astype(np.float32)
    out = np.zeros(len(x), np.float32)
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1 - f[:, 0]
        ix = (i0[:, 0] + dx) % ng
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1 - f[:, 1]
            iy = (i0[:, 1] + dy) % ng
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1 - f[:, 2]
                iz = (i0[:, 2] + dz) % ng
                out += field[ix, iy, iz] * wx * wy * wz
    return out


def accel(x, ng, box, a, kx, ky, kz, k2inv):
    delta = cic_deposit(x, ng, box)
    dk = np.fft.rfftn(delta)
    del delta
    phik = -1.5 * OMEGA_M / a * dk * k2inv
    del dk
    acc = np.empty((len(x), 3), np.float32)
    for j, K in enumerate((kx, ky, kz)):
        gj = np.fft.irfftn(-1j * K * phik, s=(ng,) * 3).astype(np.float32)
        acc[:, j] = cic_sample(gj, x, ng, box)
        del gj
    return acc


def run_pm(n_field, n_part, box, seed, a_init=0.02, a_end=1.0, n_steps=32,
           lam_min_mpc=None, verbose=True):
    """ICs de Zel'dovich a a_init, puis integration PM jusqu'a a_end."""
    ng = n_field
    delta = M.gen_delta3(ng, box, seed)
    KX, KY, KZ, kmag = M.k_grid3(ng, box)
    dk = np.fft.rfftn(delta)
    del delta
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = kmag <= (2 * np.pi / lam_min_mpc if lam_min_mpc else np.inf)

    step = ng // n_part
    g = (np.arange(n_part) * step + 0.5) * (box / ng) - box / 2.0
    x = np.stack(np.meshgrid(g, g, g, indexing="ij"), axis=-1).astype(np.float32)
    u = np.zeros_like(x)
    # facteur de croissance lineaire normalise : D(a) ~ a en matiere dominante
    for j, K in enumerate((KX, KY, KZ)):
        psi = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=(ng,) * 3).astype(np.float32)
        x[..., j] += a_init * psi[::step, ::step, ::step]
        u[..., j] = a_init ** 2 * E(a_init) * a_init * psi[::step, ::step, ::step]
        del psi
    del dk
    x = x.reshape(-1, 3)
    u = u.reshape(-1, 3)

    k2inv = np.where(kmag > 0, 1.0 / k2, 0.0)
    das = np.diff(np.linspace(a_init, a_end, n_steps + 1))
    a = a_init
    for s, da in enumerate(das):
        ah = a + da / 2
        acc = accel(x, ng, box, a, KX, KY, KZ, k2inv)
        u += acc * (da / (a ** 2 * E(a)))          # kick
        x += u * (da / (ah ** 2 * E(ah)))          # drift
        x = np.mod(x + box / 2, box) - box / 2
        a += da
        if verbose and (s + 1) % 8 == 0:
            print(f"  pas {s+1}/{len(das)}  a={a:.3f}", flush=True)
    return x


# ---- metriques de ponctualite et de fractalite ---------------------------
def punctuality(t, pct=99.0):
    """Aire des composantes au-dessus du percentile haut : petit = ponctuel."""
    b = t > np.percentile(t, pct)
    lbl, n = ndimage.label(b)
    if n == 0:
        return 0.0, 0
    sz = np.bincount(lbl.ravel())[1:]
    return float(np.median(sz)), int(n)


def peak_sharpness(t, k=150, r=5):
    """Rapport pic / anneau local : eleve = lumiere concentree en points."""
    mx = ndimage.maximum_filter(t, size=2 * r + 1)
    m = (t >= mx) & (t > np.percentile(t, 97))
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return 0.0
    v = t[ys, xs]
    o = np.argsort(v)[::-1][:k]
    ys, xs = ys[o], xs[o]
    sm = ndimage.uniform_filter(t, 2 * r + 1)
    ok = sm[ys, xs] > 0
    return float(np.median(t[ys, xs][ok] / sm[ys, xs][ok]))


def fractal_slope(t, pct=95):
    """Pente de comptage en boites sur les pixels brillants : dimension fractale."""
    b = t > np.percentile(t, pct)
    n0 = b.shape[0]
    ss, cs = [], []
    for f in (2, 4, 8, 16, 32):
        m = (n0 // f) * f
        blk = b[:m, :m].reshape(m // f, f, m // f, f).any(axis=(1, 3))
        ss.append(f)
        cs.append(max(blk.sum(), 1))
    return float(-np.polyfit(np.log(ss), np.log(cs), 1)[0])
