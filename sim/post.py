"""Après la simulation : choix de l'observateur, tranche autour de lui, données
compactes pour la page (positions quantifiées par instantané + longueur de
lissage 3D), tuiles d'image de la boîte entière à chaque instantané, planche
de comparaison avec Millennium.

Usage : python post.py DOSSIER_SIM SORTIE ETIQUETTE DEMI_EPAISSEUR NPOINTS [DELTA_MIN DELTA_MAX LISSAGE]
"""
import numpy as np, json, sys, os, glob
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageDraw, ImageFont

SIM, OUT, ETQ = sys.argv[1], sys.argv[2], sys.argv[3]
HZ, NPTS = float(sys.argv[4]), int(sys.argv[5])
DMIN, DMAX, LISS = (float(v) for v in (sys.argv[6:9] if len(sys.argv) > 8 else (4, 8, 2.0)))
os.makedirs(OUT, exist_ok=True)
meta = json.load(open(f"{SIM}/meta.json")); L = meta["L"]; NP = meta["NP"]
fichiers = sorted(glob.glob(f"{SIM}/snap_a*.npy")); AS = [float(f.split("_a")[1][:-4]) for f in fichiers]
lit = lambda f: np.load(f).astype(np.float32) * np.float32(L / 65535)
print("instantanés", AS, flush=True)

# --- observateur : une cellule de surdensité modérée (un groupe de galaxies), proche du centre
x1 = lit(fichiers[-1])
ng = 128; idx = np.floor(x1 / L * ng).astype(np.int64) % ng
cnt = np.bincount((idx[:, 0] * ng + idx[:, 1]) * ng + idx[:, 2], minlength=ng**3).reshape(ng, ng, ng).astype(np.float32)
del idx
dens = gaussian_filter(cnt, LISS / (L / ng), mode="wrap"); dens /= dens.mean(); del cnt
ok = (dens > DMIN) & (dens < DMAX)
g = np.indices(dens.shape).reshape(3, -1).T.astype(np.float32)
dist = np.linalg.norm(g - ng / 2, axis=1).reshape(dens.shape)
c = np.unravel_index(np.argmin(np.where(ok, dist, 1e9)), dens.shape)
obs = (np.array(c) + 0.5) * L / ng
print("observateur", obs, "surdensité", float(dens[c]), flush=True)
w = lambda v: (v + L / 2) % L - L / 2
d1 = w(x1 - obs)
dans = np.abs(d1[:, 2]) < HZ
ids_tous = np.where(dans)[0]
rng = np.random.default_rng(1)
ids = rng.choice(ids_tous, size=min(NPTS, len(ids_tous)), replace=False)
print("tranche", len(ids_tous), "points gardés", len(ids), flush=True)

# --- données compactes
Om = 0.315; E = lambda a: np.sqrt(Om / a**3 + 1 - Om)
from scipy.integrate import quad
Dg = lambda a: 2.5 * Om * E(a) * quad(lambda t: 1 / (t * E(t))**3, 0, a)[0]
pas = L / NP
xy, hh = [], []
def rendu(dxy, N, demi, plancher_px=0.6):
    """image de densité projetée, noyau adaptatif, ton logarithmique fixe, palette feu"""
    u = dxy[:, 0] / demi * 0.5 + 0.5; v = dxy[:, 1] / demi * 0.5 + 0.5
    img, _, _ = np.histogram2d(v, u, bins=N, range=[[0, 1], [0, 1]])
    moy = len(dxy) / N**2
    lev = [max(0.6, plancher_px) * 2**k for k in range(5)]; S = [gaussian_filter(img, s, mode="wrap") for s in lev]
    out = S[-1].copy(); pris = np.zeros(img.shape, bool)
    for s, Ss in zip(lev, S):
        okk = (Ss * 2 * np.pi * s * s >= 32) & ~pris; out[okk] = Ss[okk]; pris |= okk
    glow = gaussian_filter(out, 8, mode="wrap")
    dl = np.log10(1 + out / moy) + 0.25 * np.log10(1 + glow / moy)
    t = np.clip((dl - 0.14) / (2.0 - 0.14), 0, 1)
    rgb = np.stack([np.clip(t * 1.75, 0, 1), np.clip((t - 0.4) * 1.75, 0, 1) ** 1.1, np.clip((t - 0.8) * 3.5, 0, 1)], -1)
    return Image.fromarray((rgb * 255).astype(np.uint8))

tuiles = []
for f, a in zip(fichiers, AS):
    xa = lit(f)
    da = d1 + w(xa - x1)                                   # déroulé par rapport à aujourd'hui
    sel = da[ids]
    xy.append(np.clip(np.round(sel[:, :2] / L * 60000), -32767, 32767).astype(np.int16))
    q3 = np.column_stack([np.mod(sel[:, 0], L), np.mod(sel[:, 1], L), sel[:, 2] + 10 * L])
    dist, _ = cKDTree(q3, boxsize=[L, L, 1e9]).query(q3, k=9)
    plancher = pas * (0.25 + 0.65 * (1 - Dg(a)))          # la grille de départ ne doit pas se voir
    h = np.maximum(dist[:, -1], plancher) / L
    hh.append(np.clip(np.round((np.log2(h) + 14) * 16), 0, 255).astype(np.uint8))
    # tuile : toute la boîte, centrée sur l'observateur, toutes les particules de la tranche
    tu = rendu(np.mod(da[ids_tous, :2] + L / 2, L) - L / 2, 1024, L / 2, plancher / L * 1024)
    tu.save(f"{OUT}/tuile-{ETQ}-a{a:.4f}.jpg", quality=84); tuiles.append((a, tu))
    print("a=%.4f h médian %.3f Mpc/h" % (a, np.median(dist[:, -1])), flush=True)
    del xa, da

tete = json.dumps({"n": int(len(ids)), "a": AS, "L_mpch": L, "L_gal": L / 0.674 * 3.26156e-3, "quant": 60000,
                   "observateur": [float(v) for v in obs], "demi_epaisseur": HZ, "n_tranche": int(len(ids_tous))}).encode()
blob = np.uint32(len(tete)).tobytes() + tete; blob += b"\0" * ((-len(blob)) % 2)
for v in xy: blob += v.tobytes()
for v in hh: blob += v.tobytes()
open(f"{OUT}/matiere-{ETQ}.bin", "wb").write(blob)
print("données", len(blob) / 1e6, "Mo", flush=True)

# planche : Millennium | aujourd'hui | z=1 | z=5
ref = os.path.join(os.path.dirname(__file__), "..", "docs", "reference-visuelle", "reference-toile-cosmique.jpg")
S = 512; choix = [(1.0, "aujourd'hui"), (0.5, "z = 1"), (1 / 6, "z = 5")]
pl = Image.new("RGB", (4 * S + 50, S + 60), (5, 6, 10)); dr = ImageDraw.Draw(pl)
try: F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
except Exception: F = ImageFont.load_default()
if os.path.exists(ref): pl.paste(Image.open(ref).convert("RGB").resize((S, S)), (10, 50)); dr.text((10, 15), "Millennium (référence)", fill=(230, 230, 230), font=F)
for k, (a, lab) in enumerate(choix):
    a2, tu = min(tuiles, key=lambda q: abs(q[0] - a))
    pl.paste(tu.resize((S, S), Image.LANCZOS), (10 + (k + 1) * (S + 10), 50))
    dr.text((10 + (k + 1) * (S + 10), 15), f"{ETQ} · {lab}", fill=(230, 230, 230), font=F)
pl.save(f"{OUT}/planche-{ETQ}.png")
print("FIN", flush=True)
