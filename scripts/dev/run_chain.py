import sys, time, pickle, os, numpy as np, gen_full as G, mcpm_web as M, zel_particles as Z
from PIL import Image
i = int(sys.argv[1])
code, key, half, margin, seed = G.CHAIN[i]
parent = p_box = p_Lz = p_cell = None
if False:
    with open('/tmp/chain_parent.pkl', 'rb') as f:
        d = pickle.load(f)
    parent, p_box, p_Lz, p_cell = d['field'], d['box'], d['Lz'], d['cell']
t0 = time.time()
web, fld, box, Lz, cell, nxy, nz, psi, nh, rpx = G.bake_layer(code, half, margin, seed, parent, p_box, p_Lz, p_cell)
del parent
t, tot, rep = G.render(web, half, cell, seed)
del web
with open('/tmp/chain_parent.pkl', 'wb') as f:
    pickle.dump(dict(field=fld, box=box, Lz=Lz, cell=cell), f)
el, ne = Z.elongation(t)
h, _ = np.histogram(t, bins=48, range=(0, 1)); h = h / h.sum(); lg = np.log10(h + 1e-9)
dip = min(lg[3:8].max(), lg[34:].max()) - lg[6:34].min()
print(f"{code}|{tot/1e3:.0f}k|x{rep}|{t.mean()*255:.1f}|{(t>240/255).mean():.4f}|{(t<8/255).mean():.3f}|"
      f"{Z.aniso(t):.2f}|{ne}|{dip:.2f}|{nh}|{time.time()-t0:.0f}s", flush=True)
Image.fromarray(M.astro_palette(t).astype(np.uint8)).save(f"/tmp/full_{code}.png")
np.save(f"/tmp/full_{code}.npy", t)
