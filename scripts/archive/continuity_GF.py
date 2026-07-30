"""Test de continuite inter-layer G(l3, 150 Mpc) -> F(l2b, 67.08 Mpc).

C'est LE test que le depot CIC echouait (coherence 0.08-0.43).
Principe verifie ici : les halos du parent sont REPORTES verbatim dans l'enfant,
donc l'identite des objets traverse le changement de zoom.
"""
import sys, time, numpy as np, mcpm_web as M
from scipy import ndimage

N = 192
G_BOX, G_HALF = 450.0, 150.0
F_BOX, F_HALF = 201.24, 67.08
AGENTS, STEPS = 320000, 280
MK = dict(attract=2.2, decay=0.25)


def render(tr, pos, mass, box, half, slab_frac=0.06, out_n=512, n_vis=60000,
           trail_gain=1.0, point_gain=1.0, floor_gain=0.35):
    r = M.render_slab(tr, pos, mass, box, half, slab_frac, out_n, n_vis,
                      trail_gain=trail_gain, point_gain=point_gain, splat_px=0.9)
    if floor_gain > 0:  # plancher diffus : halos non resolus (PSF large)
        f = M.render_slab(tr, pos, mass, box, half, slab_frac * 3, out_n, n_vis,
                          trail_gain=0.0, point_gain=1.0, splat_px=6.0)
        r = r + floor_gain * f
    return r


def stage_G():
    d = M.gen_delta3(N, G_BOX, 102)
    pos, mass = M.extract_halos(d, G_BOX, 2.0, 0.4, 2.0, 600000)
    pos = M.zeldovich_points(pos, d, G_BOX, s_rms_mpc=4.0)
    np.save("/tmp/c_dG.npy", d); np.save("/tmp/c_pG.npy", pos); np.save("/tmp/c_mG.npy", mass)
    t0 = time.time()
    tr = M.mcpm(pos, mass, G_BOX, N, AGENTS, STEPS, sense_mpc=6 * G_BOX / N, **MK)
    np.save("/tmp/c_trG.npy", tr)
    print(f"G: {len(pos)} halos, mcpm {time.time()-t0:.0f}s", flush=True)


def stage_F():
    dG = np.load("/tmp/c_dG.npy"); pG = np.load("/tmp/c_pG.npy"); mG = np.load("/tmp/c_mG.npy")
    inh = M.crop_upsample3(dG, G_BOX, F_BOX, N)
    fresh = M.gen_delta3(N, F_BOX, 112, highpass_k=np.pi * N / G_BOX)
    d = 0.74 * inh + 0.67 * fresh
    d /= d.std()
    pos, mass = M.extract_halos(d, F_BOX, 0.9, 0.4, 0.9, 600000)
    pos = M.zeldovich_points(pos, d, F_BOX, s_rms_mpc=4.0)
    pos, mass = M.merge_parent(pos, mass, pG, mG, F_BOX, excl_mpc=1.5)
    np.save("/tmp/c_pF.npy", pos); np.save("/tmp/c_mF.npy", mass)
    t0 = time.time()
    tr = M.mcpm(pos, mass, F_BOX, N, AGENTS, STEPS, sense_mpc=6 * F_BOX / N, **MK)
    np.save("/tmp/c_trF.npy", tr)
    print(f"F: {len(pos)} halos, mcpm {time.time()-t0:.0f}s", flush=True)


def peaks(img, k=200):
    mx = ndimage.maximum_filter(img, size=7)
    m = (img >= mx) & (img > np.percentile(img, 97))
    idx = np.argwhere(m)
    v = img[m]
    return idx[np.argsort(v)[::-1][:k]]


def compare():
    pG = np.load("/tmp/c_pG.npy"); mG = np.load("/tmp/c_mG.npy"); trG = np.load("/tmp/c_trG.npy")
    pF = np.load("/tmp/c_pF.npy"); mF = np.load("/tmp/c_mF.npy"); trF = np.load("/tmp/c_trF.npy")

    # vue de G restreinte au champ de F (ce que l'oeil voit juste avant la bascule)
    rG = render(trG, pG, mG, G_BOX, F_HALF)
    rF = render(trF, pF, mF, F_BOX, F_HALF)
    alpha = M.solve_alpha(np.concatenate([rG.ravel(), rF.ravel()]))  # alpha UNIQUE partage
    tG, tF = M.tone(rG, alpha), M.tone(rF, alpha)

    print("\n--- CONTINUITE G->F (meme champ de vue, alpha unique) ---")
    print(f"moyenne   G {tG.mean()*255:6.2f}   F {tF.mean()*255:6.2f}   ecart {abs(tG.mean()-tF.mean())*255:.2f}/255")
    print(f"ecart-type G {tG.std()*255:6.2f}   F {tF.std()*255:6.2f}   ecart relatif {abs(tG.std()-tF.std())/tG.std()*100:.1f}%")
    a = ndimage.gaussian_filter(tG, 2); b = ndimage.gaussian_filter(tF, 2)
    corr = np.corrcoef(a.ravel(), b.ravel())[0, 1]
    print(f"correlation (lissee 2px)  {corr:.3f}      [cible >= 0.85 ; depot CIC : 0.08-0.43]")

    kG, kF = peaks(a), peaks(b)
    from scipy.spatial import cKDTree
    dist, _ = cKDTree(kF).query(kG)
    print(f"appariement des 200 pics : median {np.median(dist):.2f} px, "
          f"frac <=1.5px {float((dist<=1.5).mean()):.2f}, frac <=4px {float((dist<=4).mean()):.2f}")
    for nm, t in (("G", tG), ("F", tF)):
        print(f"{nm}: sat>240 {(t>240/255).mean():.4f}  sat<8 {(t<8/255).mean():.3f}  "
              f"lapvar {float(np.var(np.gradient(np.gradient(t,axis=0),axis=0))):.2e}")

    from PIL import Image
    Image.fromarray(np.hstack([(tG*255).astype(np.uint8), (tF*255).astype(np.uint8)])).save("/tmp/cont_GF.png")


if __name__ == "__main__":
    {"G": stage_G, "F": stage_F, "cmp": compare}[sys.argv[1]]()
