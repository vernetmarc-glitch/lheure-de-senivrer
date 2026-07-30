"""Toile cosmique par PARTICULES DE ZEL'DOVICH (pas de MCPM).

Principe : l'effondrement gravitationnel est ANISOTROPE. Une surdensite
s'effondre d'abord selon un axe (nappe), puis deux (filament), puis trois
(noeud). C'est ce qui produit des filaments FINS reliant des amas de tailles
VARIEES -- et non une mousse de bulles rondes.

Les particules partent d'une grille reguliere et sont deplacees par Psi.
Aucun depot CIC sur grille 3D : les positions restent continues jusqu'a la
projection 2D finale a la resolution de sortie.
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M


def zeldovich_particles(n_field, n_part, box, seed, amp,
                        lam_min_mpc=1.318359, lam_max_mpc=None):
    """Retourne les positions (Mpc, centre 0) de n_part^3 particules deplacees."""
    delta = M.gen_delta3(n_field, box, seed)
    KX, KY, KZ, kmag = M.k_grid3(n_field, box)
    dk = np.fft.rfftn(delta)
    del delta
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    k_hi = 2 * np.pi / lam_min_mpc
    k_lo = 0.0 if lam_max_mpc is None else 2 * np.pi / lam_max_mpc
    band = (kmag >= k_lo) & (kmag <= k_hi)

    step = n_field // n_part
    g = (np.arange(n_part) * step + 0.5) * (box / n_field) - box / 2.0
    q = np.stack(np.meshgrid(g, g, g, indexing="ij"), axis=-1).astype(np.float32)

    # rms de Psi pour normaliser l'amplitude, calcule sur la 1re composante
    rms_acc = 0.0
    for a, K in enumerate((KX, KY, KZ)):
        pk = np.where(band, 1j * K * dk / k2, 0)
        psi = np.fft.irfftn(pk, s=(n_field,) * 3).astype(np.float32)
        del pk
        rms_acc += float(np.mean(psi ** 2))
        q[..., a] += psi[::step, ::step, ::step]
        del psi
    rms = np.sqrt(rms_acc / 3.0)
    # renormalisation a l'amplitude voulue (amp = deplacement rms en Mpc)
    q = q.reshape(-1, 3)
    q0 = np.stack(np.meshgrid(g, g, g, indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    q = q0 + (q - q0) * (amp / max(rms, 1e-9))
    return np.mod(q + box / 2.0, box) - box / 2.0


def project(part, box, half_mpc, slab_frac, out_n, psf=0.45):
    slab = slab_frac * 2 * half_mpc
    m = (np.abs(part[:, 2]) < slab / 2) & (np.abs(part[:, 0]) < half_mpc) \
        & (np.abs(part[:, 1]) < half_mpc)
    p = part[m]
    ix = np.clip(((p[:, 0] + half_mpc) / (2 * half_mpc) * out_n).astype(np.int32), 0, out_n - 1)
    iy = np.clip(((p[:, 1] + half_mpc) / (2 * half_mpc) * out_n).astype(np.int32), 0, out_n - 1)
    img = np.zeros((out_n, out_n), np.float32)
    np.add.at(img, (ix, iy), np.float32(1.0))
    return ndimage.gaussian_filter(img, psf) if psf > 0 else img, int(m.sum())


# ---- metriques -----------------------------------------------------------
def elongation(t, pct=88):
    """Elongation mediane des structures brillantes : ~1 = patates, >>1 = filaments."""
    b = t > np.percentile(t, pct)
    lbl, n = ndimage.label(b)
    if n == 0:
        return 1.0, 0
    out = []
    for sl in ndimage.find_objects(lbl):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h * w < 6:
            continue
        sub = lbl[sl] > 0
        ys, xs = np.nonzero(sub)
        if len(ys) < 6:
            continue
        c = np.cov(np.stack([ys, xs]).astype(float))
        ev = np.linalg.eigvalsh(c)
        if ev[0] > 1e-6:
            out.append(np.sqrt(ev[1] / ev[0]))
    return (float(np.median(out)) if out else 1.0), len(out)


def aniso(t):
    m = min(t.shape)
    t = t[:m, :m]
    a = (t - t.mean()) * np.hanning(m)[:, None] * np.hanning(m)[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    c = m // 2
    y, x = np.indices(F.shape)
    dy, dx = y - c, x - c
    r = np.hypot(dy, dx)
    A = np.abs(np.degrees(np.arctan2(dy, dx)))
    ang = np.minimum(A, 180 - A)
    b = (r > 3) & (r < m * 0.45)
    return F[b & ((ang < 12) | (ang > 78))].mean() / F[b & (np.abs(ang - 45) < 20)].mean()


def spec(t):
    a = t - t.mean()
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    n = F.shape[0]
    y, x = np.indices(F.shape)
    r = np.hypot(y - n // 2, x - n // 2).astype(int)
    return (np.bincount(r.ravel(), F.ravel()) / np.maximum(np.bincount(r.ravel()), 1))[1:n // 2]


def report(t, nm):
    p = spec(t)
    s = np.sort(t.ravel())[::-1]
    h, _ = np.histogram(t, bins=48, range=(0, 1))
    h = h / h.sum()
    lg = np.log10(h + 1e-9)
    el, ne = elongation(t)
    print(f"{nm:26s} ELONG {el:5.2f} ({ne:4d}) | ANISO {aniso(t):5.2f} | "
          f"P.fil/gren {p[7:40].mean()/p[80:].mean():7.1f} | "
          f"contr {float(ndimage.uniform_filter(t,12).std()/t.mean()):.2f} | "
          f"creux {min(lg[3:8].max(), lg[34:].max())-lg[6:34].min():5.2f} | "
          f"conc {s[:int(.1*s.size)].sum()/s.sum():.3f}")


def zeldovich_slab(n_field, box, seed, amp, half_mpc, slab_frac, upsample=1,
                   lam_min_mpc=1.318359):
    """Comme zeldovich_particles mais n'instancie que les particules dont la
    position initiale est proche de la tranche visee (marge = 4x le deplacement).
    Permet 20-30x plus de particules dans la tranche a memoire egale.
    """
    delta = M.gen_delta3(n_field, box, seed)
    KX, KY, KZ, kmag = M.k_grid3(n_field, box)
    dk = np.fft.rfftn(delta)
    del delta
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = kmag <= 2 * np.pi / lam_min_mpc

    cell = box / n_field
    z_half = slab_frac * 2 * half_mpc / 2.0 + 4.0 * amp
    iz = np.arange(n_field)[np.abs((np.arange(n_field) + 0.5) * cell - box / 2) < z_half]
    ax = np.arange(n_field)
    gx = (ax + 0.5) * cell - box / 2
    gz = (iz + 0.5) * cell - box / 2

    psis = []
    rms_acc = 0.0
    for K in (KX, KY, KZ):
        pk = np.where(band, 1j * K * dk / k2, 0)
        psi = np.fft.irfftn(pk, s=(n_field,) * 3).astype(np.float32)
        del pk
        rms_acc += float(np.mean(psi ** 2))
        psis.append(psi[:, :, iz].copy())
        del psi
    scale = amp / max(np.sqrt(rms_acc / 3.0), 1e-9)

    Q = np.stack(np.meshgrid(gx, gx, gz, indexing="ij"), axis=-1).astype(np.float32)
    for a in range(3):
        Q[..., a] += psis[a] * scale
    del psis
    Q = Q.reshape(-1, 3)
    if upsample > 1:   # sous-echantillonnage lagrangien : densifie sans re-FFT
        rng = np.random.default_rng(seed + 99)
        rep = np.repeat(Q, upsample, axis=0)
        rep += rng.normal(0, cell * 0.35, rep.shape).astype(np.float32)
        Q = rep
    return np.mod(Q + box / 2.0, box) - box / 2.0


def halo_clouds(delta, box, amp, n_field, seed=7, n_halo_max=60000,
                frac_points=0.45, n_web=1000000, q=0.55, rmax_mpc=2.2,
                mass_slope=0.9, sub_levels=2, sub_frac=0.30):
    """Nuages de points compacts aux noeuds, avec sous-halos recursifs.

    Profil radial pique (r = rmax * u^q, q<1 concentre vers le centre) -> les
    zones les plus brillantes sont quasi ponctuelles et non des surfaces.
    Les sous-halos reproduisent la meme structure a une echelle inferieure :
    c'est ce qui donne l'auto-similarite quand on descend dans les zooms.
    """
    pos, mass = M.extract_halos(delta, box, smooth_mpc=1.4, thresh_sigma=0.5,
                                min_sep_mpc=1.4, max_n=n_halo_max)
    pos = M.zeldovich_points(pos, delta, box, s_rms_mpc=amp)
    rng = np.random.default_rng(seed)
    w = mass ** mass_slope
    w = w / w.sum()
    n_tot = int(frac_points * n_web)
    counts = rng.multinomial(n_tot, w)
    keep = counts > 0
    pos, counts, mass = pos[keep], counts[keep], mass[keep]

    out = []
    for lvl in range(sub_levels + 1):
        scale = (sub_frac ** lvl)
        share = (1.0 - sub_frac) if lvl < sub_levels else 1.0
        c = np.maximum((counts * share * (sub_frac ** lvl)).astype(np.int64), 0)
        if c.sum() == 0:
            continue
        centres = np.repeat(pos, c, axis=0)
        if lvl > 0:  # decentrer les sous-halos dans le halo parent
            rr = rmax_mpc * (mass / mass.max()) ** 0.28
            off = np.repeat(rr, c)[:, None] * rng.normal(size=(int(c.sum()), 3)) * 0.5
            centres = centres + off.astype(np.float32)
        n = int(c.sum())
        u = rng.random(n)
        r = rmax_mpc * scale * np.repeat((mass / mass.max()) ** 0.28, c) * u ** q
        d = rng.normal(size=(n, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        out.append(centres + (r[:, None] * d).astype(np.float32))
    return np.vstack(out).astype(np.float32)
