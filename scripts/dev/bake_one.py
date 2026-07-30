import sys, time, numpy as np, reference_a1 as R, zel_particles as Z, pm_gravity as P, mcpm_web as M
from scipy import ndimage
from PIL import Image
L = sys.argv[1]
code, key, half, mg, seed = [x for x in R.LAYERS if x[0] == L][0]
t0 = time.time()
web, box, rep, cell = R.bake(half, mg, seed, verbose=True)
t, al, cnt = R.render(web, box, half, rep=rep, cell=cell, seed=seed)
el, ne = Z.elongation(t)
rpx = max(int(round(1.5 / (2 * half / 512))), 1)
h, _ = np.histogram(t, bins=48, range=(0, 1)); h = h / h.sum(); lg = np.log10(h + 1e-9)
dip = min(lg[3:8].max(), lg[34:].max()) - lg[6:34].min()
sg = float(ndimage.gaussian_filter(t, 8).std()) * 255
print(f"{code}/{key}|{cnt/1e3:.0f}k|{t.mean()*255:.1f}|{(t>240/255).mean():.4f}|{(t<8/255).mean():.3f}|"
      f"{Z.aniso(t):.2f}|{ne}|{P.peak_sharpness(t,r=rpx):.2f}|{sg:.2f}|{dip:.2f}|{time.time()-t0:.0f}s", flush=True)
Image.fromarray(M.astro_palette(t).astype(np.uint8)).save(f"/tmp/ref_{code}.png")
np.save(f"/tmp/ref_{code}.npy", t)
