"""Prototype de generateur de toile cosmique par MCPM (Physarum) -- DEV UNIQUEMENT.

Principe (cf. proposition, remplace le depot CIC de zeldovich_engine.py pour D..M) :
  1. delta 3D emboite, herite du parent (memes phases) + detail passe-haut frais
  2. catalogue de halos par peak-patch ; les halos du parent sont REPORTES tels quels
     (identite des objets a travers les echelles -> coherence inter-layer)
  3. deplacement de Zel'dovich applique aux POINTS (pas de depot CIC)
  4. agents MCPM : reseau de transport entre les halos (attracteurs)
  5. rendu = projection LINEAIRE d'une tranche (splats de halos + trace MCPM)
  6. courbe de ton ponctuelle, alpha unique partage

P(k) / transfert BBKS repris a l'identique de scripts/generate_layers.py.
"""
import numpy as np
from scipy import ndimage

# ---- repris a l'identique de generate_layers.py -------------------------
OMEGA_M = 0.315
H = 0.674
NS = 0.965
GAMMA = OMEGA_M * H


def bbks_transfer(k_h_mpc):
    q = np.maximum(k_h_mpc, 1e-8) / GAMMA
    return (np.log(1 + 2.34 * q) / (2.34 * q)) * (
        1 + 3.89 * q + (16.1 * q) ** 2 + (5.46 * q) ** 3 + (6.71 * q) ** 4
    ) ** -0.25


def power_spectrum(k_h_mpc):
    T = bbks_transfer(k_h_mpc)
    P = (k_h_mpc ** NS) * T ** 2
    P[k_h_mpc == 0] = 0
    return P


# ---- extension 3D ------------------------------------------------------
def k_grid3(n, box):
    d = box / n
    kx = np.fft.fftfreq(n, d=d) * 2 * np.pi
    kz = np.fft.rfftfreq(n, d=d) * 2 * np.pi
    KX, KY, KZ = np.meshgrid(kx, kx, kz, indexing="ij")
    return KX, KY, KZ, np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)


def gen_delta3(n, box, seed, highpass_k=None):
    """Champ gaussien 3D contraint par P(k), passe-haut sigmoide optionnel."""
    rng = np.random.default_rng(seed)
    _, _, _, kmag = k_grid3(n, box)
    P = power_spectrum(kmag)
    if highpass_k is not None:
        with np.errstate(divide="ignore"):
            lr = np.log10(np.maximum(kmag, 1e-8) / highpass_k)
        P = P * (1 / (1 + np.exp(-lr / 0.15)))
    dk = (rng.normal(size=kmag.shape) + 1j * rng.normal(size=kmag.shape))
    dk *= np.sqrt(P / 2.0) * n ** 1.5
    f = np.fft.irfftn(dk, s=(n, n, n))
    return f / (f.std() + 1e-12)


def crop_upsample3(parent, parent_box, child_box, n):
    """Sous-cube central du parent, reechantillonne a n^3 (heritage des phases)."""
    frac = child_box / parent_box
    pn = parent.shape[0]
    half = frac * pn / 2.0
    c = pn / 2.0
    lo, hi = c - half, c + half
    g = np.linspace(lo, hi, n, endpoint=False)
    coords = np.array(np.meshgrid(g, g, g, indexing="ij"))
    out = ndimage.map_coordinates(parent, coords, order=1, mode="wrap")
    return out


def nested_delta(levels, n, seed0=42):
    """levels : liste de (cle, box_mpc) du PLUS GRAND au plus petit."""
    fields, prev = {}, None
    for i, (key, box) in enumerate(levels):
        if prev is None:
            fields[key] = gen_delta3(n, box, seed0)
        else:
            pkey, pbox = levels[i - 1]
            inherited = crop_upsample3(fields[pkey], pbox, box, n)
            # detail frais au-dela de la coupure de Nyquist utile du parent
            k_cut = np.pi * n / pbox
            fresh = gen_delta3(n, box, seed0 + 7 * i, highpass_k=k_cut)
            f = 0.74 * inherited + 0.67 * fresh  # poids de production (§0)
            fields[key] = f / (f.std() + 1e-12)
        prev = key
    return fields


# ---- catalogue de halos (peak-patch) -----------------------------------
def extract_halos(delta, box, smooth_mpc, thresh_sigma, min_sep_mpc, max_n):
    """Maxima locaux de delta lisse -> positions (Mpc, centre=0) + masses."""
    n = delta.shape[0]
    cell = box / n
    sig = max(smooth_mpc / cell, 0.6)
    ds = ndimage.gaussian_filter(delta, sig)  # lissage INTERNE (echelle de peak-patch)
    ds /= ds.std() + 1e-12
    sep = max(int(round(min_sep_mpc / cell)), 1)
    mx = ndimage.maximum_filter(ds, size=2 * sep + 1)
    mask = (ds >= mx) & (ds > thresh_sigma)
    idx = np.argwhere(mask)
    if len(idx) == 0:
        return np.zeros((0, 3)), np.zeros(0)
    val = ds[mask]
    if len(idx) > max_n:  # garder les plus significatifs
        keep = np.argsort(val)[::-1][:max_n]
        idx, val = idx[keep], val[keep]
    pos = (idx + 0.5) * cell - box / 2.0
    # masse : loi steeply decroissante -> quelques points tres brillants
    mass = np.exp(1.35 * (val - thresh_sigma))
    return pos, mass


def merge_parent(child_pos, child_mass, par_pos, par_mass, box, excl_mpc):
    """Reporte les halos parents verbatim, exclut les doublons enfants."""
    if len(par_pos) == 0:
        return child_pos, child_mass
    h = box / 2.0
    inb = np.all(np.abs(par_pos) < h, axis=1)
    pp, pm = par_pos[inb], par_mass[inb]
    if len(pp) == 0:
        return child_pos, child_mass
    if len(child_pos):
        from scipy.spatial import cKDTree
        d, _ = cKDTree(pp).query(child_pos)
        keep = d > excl_mpc
        child_pos, child_mass = child_pos[keep], child_mass[keep]
    return np.vstack([pp, child_pos]), np.concatenate([pm, child_mass])


# ---- Zel'dovich sur les POINTS ----------------------------------------
def zeldovich_points(pos, delta, box, s_rms_mpc, lam_min_mpc=1.318359):
    """Psi = i k delta_k / k^2, bande [lam_min, 150 Mpc], applique aux points."""
    n = delta.shape[0]
    KX, KY, KZ, kmag = k_grid3(n, box)
    dk = np.fft.rfftn(delta)
    k2 = np.where(kmag > 0, kmag ** 2, 1.0)
    k_hi = 2 * np.pi / lam_min_mpc
    k_lo = 2 * np.pi / 150.0
    band = (kmag >= k_lo) & (kmag <= k_hi)
    psi = []
    for K in (KX, KY, KZ):
        pk = np.where(band, 1j * K * dk / k2, 0)
        psi.append(np.fft.irfftn(pk, s=(n, n, n)))
    psi = np.array(psi)
    rms = np.sqrt(np.mean(np.sum(psi ** 2, axis=0)) / 3.0)
    if rms > 0:
        psi *= s_rms_mpc / rms
    cell = box / n
    c = (pos + box / 2.0) / cell
    coords = c.T
    disp = np.array([
        ndimage.map_coordinates(psi[a], coords, order=1, mode="wrap") for a in range(3)
    ]).T
    return pos + disp


# ---- MCPM : agents Physarum en 3D --------------------------------------
def halo_field(pos, mass, box, n):
    """Depot des halos sur grille (attracteurs des agents)."""
    cell = box / n
    c = np.clip(((pos + box / 2.0) / cell).astype(np.int32), 0, n - 1)
    g = np.zeros((n, n, n), np.float32)
    np.add.at(g, (c[:, 0], c[:, 1], c[:, 2]), mass.astype(np.float32))
    return g


def mcpm(pos, mass, box, n, n_agents, steps, seed=1,
         sense_mpc=None, step_mpc=None, sense_ang=0.5, turn=0.45,
         deposit=1.0, decay=0.12, attract=2.2, sense_div=2,
         sense_init=None, inherit_gain=3.0):
    """Agents attires par (trace + champ de halos). Parametres en Mpc comobiles.

    DEUX grilles distinctes :
      - trail_out : densite de chemins, JAMAIS lissee -> contenu HF preserve
      - trail_sense : grille grossiere (n/sense_div) diffusee, sert UNIQUEMENT
        de gradient aux capteurs des agents (dynamique interne, pas de sortie)
    """
    rng = np.random.default_rng(seed)
    cell = box / n
    ns = max(n // sense_div, 8)
    cs = box / ns
    if sense_mpc is None:
        sense_mpc = 4.0 * cell
    if step_mpc is None:
        step_mpc = 1.1 * cell

    hf = halo_field(pos, mass, box, ns)
    hf = ndimage.gaussian_filter(hf, 1.0)
    hf /= hf.max() + 1e-12

    trail_out = np.zeros((n, n, n), np.float32)
    trail_sense = np.zeros((ns, ns, ns), np.float32)
    if sense_init is not None:
        # HERITAGE DU RESEAU PARENT (§4.4 applique a la trace) : les agents
        # renforcent le tronc deja present et n'ajoutent que des branches fines.
        si = sense_init.astype(np.float32)
        si = si / (si.mean() + 1e-12)
        trail_sense += si * inherit_gain

    p = mass / mass.sum()
    pick = rng.choice(len(pos), size=n_agents, p=p)
    a = ((pos[pick] + box / 2.0) / cell).astype(np.float32)
    a += rng.normal(0, 1.5, a.shape).astype(np.float32)
    d = rng.normal(size=(n_agents, 3)).astype(np.float32)
    d /= np.linalg.norm(d, axis=1, keepdims=True)

    def ortho(v):
        r = rng.normal(size=v.shape).astype(np.float32)
        r -= np.sum(r * v, axis=1, keepdims=True) * v
        return r / np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-6)

    sc = sense_mpc / cell
    st = step_mpc / cell
    for s in range(steps):
        u = ortho(d)
        cands = [d,
                 d * np.cos(sense_ang) + u * np.sin(sense_ang),
                 d * np.cos(sense_ang) - u * np.sin(sense_ang)]
        scores = []
        for cd in cands:
            jit = rng.random((len(a), 3)).astype(np.float32) - 0.5
            q = np.mod((a + cd * sc) * (cell / cs) + jit, ns).astype(np.int32)
            scores.append(trail_sense[q[:, 0], q[:, 1], q[:, 2]]
                          + attract * hf[q[:, 0], q[:, 1], q[:, 2]])
        best = np.argmax(np.stack(scores, 1), 1)[:, None]
        newd = np.where(best == 0, cands[0], np.where(best == 1, cands[1], cands[2]))
        d = (1 - turn) * d + turn * newd
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
        a = np.mod(a + d * st, n)
        ai = a.astype(np.int32)
        np.add.at(trail_out, (ai[:, 0], ai[:, 1], ai[:, 2]), np.float32(deposit))
        qs = np.mod((a * (cell / cs)
                     + rng.random((len(a), 3)).astype(np.float32) - 0.5).astype(np.int32), ns)
        np.add.at(trail_sense, (qs[:, 0], qs[:, 1], qs[:, 2]), np.float32(deposit))
        trail_sense = ndimage.gaussian_filter(trail_sense, 0.8) * (1 - decay)
    return trail_out


# ---- rendu : projection LINEAIRE d'une tranche -------------------------
def render_slab(trail, pos, mass, box, half_mpc, slab_frac, out_n,
                n_visible, trail_gain=1.0, point_gain=1.0, splat_px=0.9):
    """Somme en profondeur (emission pure). Operateur strictement lineaire."""
    n = trail.shape[0]
    field_w = 2.0 * half_mpc
    slab = slab_frac * field_w
    cell = box / n
    # --- trace MCPM : sous-cube central, somme en z, moyenne de zone en x/y
    hw_c = min(int(round(half_mpc / cell)), n // 2)
    sl_c = max(int(round(slab / 2.0 / cell)), 1)
    c0 = n // 2
    sub = trail[c0 - hw_c:c0 + hw_c, c0 - hw_c:c0 + hw_c,
                max(c0 - sl_c, 0):min(c0 + sl_c, n)]
    proj = sub.sum(axis=2).astype(np.float32)
    zoom = out_n / proj.shape[0]
    if zoom < 1:  # minification -> MOYENNE DE ZONE (jamais point-sampling)
        f = int(round(1 / zoom))
        m = (proj.shape[0] // f) * f
        proj = proj[:m, :m].reshape(m // f, f, m // f, f).mean(axis=(1, 3))
    proj = ndimage.zoom(proj, out_n / proj.shape[0], order=1)
    proj = proj[:out_n, :out_n]
    proj /= proj.mean() + 1e-12

    # --- splats de halos : les n_visible plus massifs dans la tranche
    inx = (np.abs(pos[:, 0]) < half_mpc) & (np.abs(pos[:, 1]) < half_mpc) \
        & (np.abs(pos[:, 2]) < slab / 2.0)
    p, m = pos[inx], mass[inx]
    if len(m) > n_visible:
        k = np.argsort(m)[::-1][:n_visible]
        p, m = p[k], m[k]
    pts = np.zeros((out_n, out_n), np.float32)
    if len(p):
        px = ((p[:, 0] + half_mpc) / field_w * out_n)
        py = ((p[:, 1] + half_mpc) / field_w * out_n)
        ix = np.clip(px.astype(np.int32), 0, out_n - 1)
        iy = np.clip(py.astype(np.int32), 0, out_n - 1)
        w = (m / m.max()) ** 0.35
        np.add.at(pts, (ix, iy), w.astype(np.float32))
        if splat_px > 0:
            pts = ndimage.gaussian_filter(pts, splat_px)  # PSF du point, pas un flou de scene
        pts /= pts.mean() + 1e-12
    return trail_gain * proj + point_gain * pts


def solve_alpha(rho, target_255=38.0, gamma=1.35):
    """alpha unique tel que la moyenne du ton vaille la cible (§12.e/12.f)."""
    t = target_255 / 255.0
    lo, hi = 1e-6, 50.0
    for _ in range(60):
        mid = np.sqrt(lo * hi)
        v = np.mean((1 - np.exp(-mid * rho)) ** gamma)
        if v < t:
            lo = mid
        else:
            hi = mid
    return np.sqrt(lo * hi)


def tone(rho, alpha, gamma=1.35):
    return np.clip((1 - np.exp(-alpha * rho)) ** gamma, 0, 1)


# ---- rendu POPULATION UNIQUE : la toile EST la densite de points ---------
ASTRO_STOPS = np.array([[0, 0, 0], [0x17, 0x0a, 0x05], [0x4a, 0x1f, 0x0a],
                        [0xa8, 0x48, 0x0f], [0xe8, 0xa1, 0x3a], [0xff, 0xf3, 0xd6]],
                       dtype=np.float32)


def astro_palette(t):
    """Palette Astro de production (glow-test.html), interpolation lineaire."""
    t = np.clip(t, 0, 1)
    n = len(ASTRO_STOPS) - 1
    idx = np.clip((t * n).astype(np.int32), 0, n - 1)
    frac = (t * n - idx)[..., None]
    return ASTRO_STOPS[idx] * (1 - frac) + ASTRO_STOPS[idx + 1] * frac


def render_starfield(trail, pos, mass, box, half_mpc, slab_frac, out_n,
                     n_stars=600000, lum_slope=2.0, size_classes=(0.55, 0.9, 1.5, 2.6),
                     seed=3, diffuse_gain=0.0, halo_boost=1.0):
    """UNE seule population. Les etoiles sont tirees du champ de toile comme
    densite de probabilite ; leur luminosite suit une loi de puissance raide
    (myriade de faibles, quelques tres brillantes) et leur TAILLE croit avec
    la luminosite. Aucun calque de nuage : les zones denses fusionnent d'elles-
    memes en lueur continue, les zones vides se resolvent en etoiles isolees.
    """
    rng = np.random.default_rng(seed)
    n = trail.shape[0]
    cell = box / n
    field_w = 2.0 * half_mpc
    hw_c = min(int(round(half_mpc / cell)), n // 2)
    sl_c = max(int(round(slab_frac * field_w / 2.0 / cell)), 1)
    c0 = n // 2
    sub = trail[c0 - hw_c:c0 + hw_c, c0 - hw_c:c0 + hw_c,
                max(c0 - sl_c, 0):min(c0 + sl_c, n)].astype(np.float64)

    # --- tirage des positions selon le champ de toile (PDF)
    p = sub.ravel()
    p = np.maximum(p, p.max() * 1e-4)   # plancher : le vide n'est jamais vide
    p /= p.sum()
    pick = rng.choice(p.size, size=n_stars, p=p)
    sx, sy, _ = np.unravel_index(pick, sub.shape)
    # jitter sous-cellule -> pas de grille visible
    fx = (sx + rng.random(n_stars)) / sub.shape[0]
    fy = (sy + rng.random(n_stars)) / sub.shape[1]

    # --- luminosites : loi de puissance p(L) ~ L^-slope
    u = rng.random(n_stars)
    lum = u ** (-1.0 / (lum_slope - 1.0))
    lum = np.minimum(lum, 400.0)

    # --- halos = le haut de la distribution, a leur position exacte
    inx = (np.abs(pos[:, 0]) < half_mpc) & (np.abs(pos[:, 1]) < half_mpc) \
        & (np.abs(pos[:, 2]) < slab_frac * field_w / 2.0)
    hp, hm = pos[inx], mass[inx]
    if len(hp):
        hx = (hp[:, 0] + half_mpc) / field_w
        hy = (hp[:, 1] + half_mpc) / field_w
        hl = halo_boost * 60.0 * (hm / hm.max()) ** 0.8
        fx = np.concatenate([fx, hx]); fy = np.concatenate([fy, hy])
        lum = np.concatenate([lum, hl])

    ix = np.clip((fx * out_n).astype(np.int32), 0, out_n - 1)
    iy = np.clip((fy * out_n).astype(np.int32), 0, out_n - 1)

    # --- classes de taille : la PSF grandit avec la luminosite
    q = np.quantile(lum, np.linspace(0, 1, len(size_classes) + 1)[1:-1])
    cls = np.digitize(lum, q)
    img = np.zeros((out_n, out_n), np.float32)
    for c, sig in enumerate(size_classes):
        m = cls == c
        if not m.any():
            continue
        layer = np.zeros((out_n, out_n), np.float32)
        np.add.at(layer, (ix[m], iy[m]), lum[m].astype(np.float32))
        img += ndimage.gaussian_filter(layer, sig)  # PSF de l'etoile, pas un flou de scene

    if diffuse_gain > 0:   # residu non resolu, optionnel
        d = sub.sum(axis=2).astype(np.float32)
        d = ndimage.zoom(d, out_n / d.shape[0], order=1)[:out_n, :out_n]
        img += diffuse_gain * img.mean() * d / (d.mean() + 1e-12)
    return img


def mcpm_direct(pos, mass, box, half_mpc, slab_frac, out_n, n_agents, steps,
                seed=1, sense_mpc=None, step_mpc=None, sense_ang=0.5, turn=0.45,
                decay=0.35, attract=3.5, n_sense=96, psf=0.5, burn_in=40):
    """MCPM ou LES AGENTS SONT LES PARTICULES.

    Aucune grille d'echantillonnage : les positions des agents sont des flottants
    continus, deposes directement dans la projection 2D a la resolution de sortie.
    -> pas de maille, pas de quantification, pas de flou de sous-resolution.
    La grille de detection reste grossiere (sa douceur est interne a la dynamique).
    """
    rng = np.random.default_rng(seed)
    cs = box / n_sense
    if sense_mpc is None:
        sense_mpc = 2.0 * cs
    if step_mpc is None:
        step_mpc = 0.5 * cs

    hf = halo_field(pos, mass, box, n_sense)
    hf = ndimage.gaussian_filter(hf, 1.0)
    hf /= hf.max() + 1e-12
    sense = np.zeros((n_sense,) * 3, np.float32)
    out = np.zeros((out_n, out_n), np.float32)

    p = mass / mass.sum()
    pick = rng.choice(len(pos), size=n_agents, p=p)
    a = pos[pick].astype(np.float32) + rng.normal(0, cs * 0.5, (n_agents, 3)).astype(np.float32)
    d = rng.normal(size=(n_agents, 3)).astype(np.float32)
    d /= np.linalg.norm(d, axis=1, keepdims=True)

    half_slab = slab_frac * 2.0 * half_mpc / 2.0
    for s in range(steps):
        r = rng.normal(size=d.shape).astype(np.float32)
        r -= np.sum(r * d, axis=1, keepdims=True) * d
        u = r / np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-6)
        cands = [d,
                 d * np.cos(sense_ang) + u * np.sin(sense_ang),
                 d * np.cos(sense_ang) - u * np.sin(sense_ang)]
        sco = []
        for cd in cands:
            q = np.mod(((a + cd * sense_mpc) + box / 2.0) / cs, n_sense).astype(np.int32)
            sco.append(sense[q[:, 0], q[:, 1], q[:, 2]] + attract * hf[q[:, 0], q[:, 1], q[:, 2]])
        b = np.argmax(np.stack(sco, 1), 1)[:, None]
        nd = np.where(b == 0, cands[0], np.where(b == 1, cands[1], cands[2]))
        d = (1 - turn) * d + turn * nd
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
        a = a + d * step_mpc
        a = (np.mod(a + box / 2.0, box)) - box / 2.0

        qs = np.mod((a + box / 2.0) / cs, n_sense).astype(np.int32)
        np.add.at(sense, (qs[:, 0], qs[:, 1], qs[:, 2]), np.float32(1.0))
        sense = ndimage.uniform_filter(sense, 3) * (1 - decay)

        if s >= burn_in:   # sortie : POSITIONS CONTINUES, sous-pixel
            m = (np.abs(a[:, 2]) < half_slab) & (np.abs(a[:, 0]) < half_mpc) \
                & (np.abs(a[:, 1]) < half_mpc)
            if m.any():
                fx = (a[m, 0] + half_mpc) / (2 * half_mpc) * out_n
                fy = (a[m, 1] + half_mpc) / (2 * half_mpc) * out_n
                np.add.at(out, (np.clip(fx.astype(np.int32), 0, out_n - 1),
                                np.clip(fy.astype(np.int32), 0, out_n - 1)), np.float32(1.0))
    return ndimage.gaussian_filter(out, psf) if psf > 0 else out
