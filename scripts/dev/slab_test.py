"""Validation de la DALLE ANISOTROPE.

On ne rend jamais qu'une tranche mince. Generer une boite cubique gaspille donc
un facteur (boite / epaisseur) de volume -- 40x a M -- et ce gaspillage se paie
en RESOLUTION : a M la cellule vaut 182 Mpc, la toile (10-100 Mpc) n'est plus
resolue du tout, et il ne reste que des halos trop rares et trop brillants.

Doute a lever : dans une boite periodique de profondeur T, les kz autorises sont
0, +/-2pi/T, +/-4pi/T... La projection integre  int dkz P3D(sqrt(k_perp^2+kz^2)).
Le mode kz=0 -- celui qui survit le mieux a la projection -- est bien present ;
ce qu'on perd, c'est la FINESSE d'echantillonnage en kz. Tant que T est grand
devant les structures projetees, l'integrale reste bien echantillonnee.

Ce script mesure ou est la limite, en comparant a resolution EGALE :
  - boite cubique  (nx, ny, nz) = (n, n, n)
  - dalle          (nx, ny, nz) = (n, n, nz) avec nz = T/cellule
"""
import numpy as np
from scipy import ndimage
import mcpm_web as M


def k_grid_aniso(shape, box):
    """box = (Lx, Ly, Lz) ; shape = (nx, ny, nz)."""
    kx = np.fft.fftfreq(shape[0], d=box[0] / shape[0]) * 2 * np.pi
    ky = np.fft.fftfreq(shape[1], d=box[1] / shape[1]) * 2 * np.pi
    kz = np.fft.rfftfreq(shape[2], d=box[2] / shape[2]) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing="ij")
    return KX, KY, KZ, np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)


def gen_delta_aniso(shape, box, seed):
    rng = np.random.default_rng(seed)
    _, _, _, kmag = k_grid_aniso(shape, box)
    P = M.power_spectrum(kmag)
    dk = rng.normal(size=kmag.shape) + 1j * rng.normal(size=kmag.shape)
    # CONVENTION DE VOLUME -- corrigee le 30/07/2026.
    #
    # On veut  delta(x) = (1/V) somme_k delta_k e^{ikx}  avec  <|delta_k|^2> = V P(k).
    # numpy irfftn porte deja un 1/N, donc il faut  dk = (N/V) delta_k,
    # soit  E|dk|^2 = N^2 P / V,  soit une amplitude  N sqrt(P / 2V).
    #
    # L'ancienne ligne ecrivait  sqrt(P/2) * sqrt(N)  : elle supposait
    # implicitement une cellule de volume 1 Mpc^3. Le champ sortait donc
    # sqrt(V_cellule) fois trop grand -- invisible pres de la grille de
    # reference (V_cellule = 1,6 Mpc^3, facteur 1,27) et catastrophique sur la
    # dalle (facteur 3 476 a la ligne O, d'ou rms(Psi) = 5 150 Mpc au lieu de 6).
    V = float(box[0] * box[1] * box[2])
    dk *= np.sqrt(P / 2.0) * np.prod(shape) / np.sqrt(V)
    f = np.fft.irfftn(dk, s=shape)
    return (f / (f.std() + 1e-12)).astype(np.float32)


def psi_aniso(delta, box, amp, lam_min):
    shape = delta.shape
    KX, KY, KZ, kmag = k_grid_aniso(shape, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    band = kmag <= 2 * np.pi / lam_min
    out = np.empty(shape + (3,), np.float32)
    acc = 0.0
    for a, K in enumerate((KX, KY, KZ)):
        p = np.fft.irfftn(np.where(band, 1j * K * dk / k2, 0), s=shape).astype(np.float32)
        acc += float(np.mean(p ** 2))
        out[..., a] = p
        del p
    return out * np.float32(amp / max(np.sqrt(acc / 3.0), 1e-9))


def particles(shape, box, seed, amp, lam_min, rep=1):
    """Verre + deplacement, sur grille eventuellement anisotrope."""
    rng = np.random.default_rng(seed + 7)
    cell = np.array([box[i] / shape[i] for i in range(3)], np.float32)
    delta = gen_delta_aniso(shape, box, seed)
    PSI = psi_aniso(delta, box, amp, lam_min)
    g = [(np.arange(shape[i]) + 0.5) * cell[i] - box[i] / 2 for i in range(3)]
    Q = np.stack(np.meshgrid(*g, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
    Q += (rng.random(Q.shape).astype(np.float32) - 0.5) * cell
    P = PSI.reshape(-1, 3)
    del PSI
    web = Q + P
    if rep > 1:
        web = np.repeat(web, rep, axis=0)
        web += (rng.random(web.shape).astype(np.float32) - 0.5) * cell
    return web, delta


def project(web, half_xy, slab_T, out_n, psf=0.45):
    m = (np.abs(web[:, 2]) < slab_T / 2) & (np.abs(web[:, 0]) < half_xy) & (np.abs(web[:, 1]) < half_xy)
    p = web[m]
    ix = np.clip(((p[:, 0] + half_xy) / (2 * half_xy) * out_n).astype(np.int32), 0, out_n - 1)
    iy = np.clip(((p[:, 1] + half_xy) / (2 * half_xy) * out_n).astype(np.int32), 0, out_n - 1)
    img = np.zeros((out_n, out_n), np.float32)
    np.add.at(img, (ix, iy), np.float32(1.0))
    return ndimage.gaussian_filter(img, psf), int(m.sum())


def radial_spectrum(t):
    a = t - t.mean()
    F = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    n = F.shape[0]
    y, x = np.indices(F.shape)
    r = np.hypot(y - n // 2, x - n // 2).astype(int)
    return (np.bincount(r.ravel(), F.ravel()) / np.maximum(np.bincount(r.ravel()), 1))[1:n // 2]
