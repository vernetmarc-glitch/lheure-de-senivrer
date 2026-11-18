import numpy as np, sys
sys.path.insert(0, '.')
import rendu as R
import contours as K
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
N = 1024
cx, cy = map(float, open('noeud.txt').read().split())
def png(a, nom):
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(nom)
def fond(N, c=(0.06, 0.04, 0.26), r0=0.75, k=0.55):
    y, x = np.mgrid[0:N, 0:N] / N - 0.5; r = np.hypot(x, y) / r0
    return np.array(c)[None, None, :] * k * np.clip(1 - r, 0, 1)[..., None] ** 1.5
def ecran(a, b):                      # mélange additif doux (screen)
    return 1 - (1 - np.clip(a, 0, 1)) * (1 - np.clip(b, 0, 1))
def trace(N, dessin, larg, flou):
    S = 4; im = Image.new('L', (N * S, N * S), 0); d = ImageDraw.Draw(im)
    dessin(d, S, larg * S); im = im.resize((N, N), Image.LANCZOS)
    a = np.asarray(im).astype(float) / 255
    return a, gaussian_filter(a, flou)
OR, CREME = np.array([1.0, 0.70, 0.32]), np.array([1.0, 0.93, 0.78])

# ---------- A. Amas : un vrai nœud de la toile de l'application, et ses filaments ----------
R.charge('pts.npz')
demi = 0.08
D = R.densite(cx, cy, demi, N=N, ech=0.45, smin=1.0, smax=18); m = len(R.XY) / (N / (2 * demi)) ** 2
A = R.ton(D, m, contraste=1.2, glow=0.6)
y0, x0 = np.mgrid[0:N, 0:N] / N - 0.5; A = ecran(A, (np.exp(-np.hypot(x0, y0) ** 2 / 0.02) * 0.10)[..., None] * OR)
y, x = np.mgrid[0:N, 0:N] / N - 0.5; vig = np.clip(1.25 - 1.3 * np.hypot(x, y), 0, 1)[..., None]
A = ecran(A * vig, fond(N))
png(A, 'A-amas.png')

# ---------- B. Coupe : un verre de lumière, rempli de toile cosmique ----------
def verre(d, S, L):
    W = N * S
    bol = [(0.27, 0.16), (0.73, 0.16)]
    # bol en tulipe : courbe paramétrique
    pts = []
    for k in range(0, 101):
        u = k / 100; yy = 0.16 + 0.42 * u
        half = 0.23 * np.sin(np.pi * (0.18 + 0.82 * (1 - u) ** 0.9) ) ** 0.7 * (1 - 0.15 * u) + 0.0
        half = 0.235 * (1 - u ** 2.2) ** 0.55 if u < 1 else 0.0
        pts.append((yy, half))
    gauche = [((0.5 - h) * W, yy * W) for yy, h in pts]; droite = [((0.5 + h) * W, yy * W) for yy, h in pts][::-1]
    d.line(gauche + [(0.5 * W, 0.58 * W)] + droite + [gauche[0]], fill=255, width=int(L), joint='curve')
    d.line([(0.5 * W, 0.58 * W), (0.5 * W, 0.80 * W)], fill=255, width=int(L))
    d.ellipse([0.36 * W, 0.785 * W, 0.64 * W, 0.835 * W], outline=255, width=int(L))
def bol_masque(d, S, L):
    W = N * S; pts = []
    for k in range(0, 101):
        u = k / 100; yy = 0.16 + 0.42 * u; h = 0.235 * (1 - u ** 2.2) ** 0.55
        pts.append((yy, h))
    niveau = 0.30
    g = [((0.5 - h) * W, yy * W) for yy, h in pts if yy >= niveau]; dr = [((0.5 + h) * W, yy * W) for yy, h in pts if yy >= niveau][::-1]
    d.polygon(g + dr, fill=255)
ligne, halo = trace(N, verre, 9, 14)
masque, _ = trace(N, bol_masque, 0, 1); masque = gaussian_filter(masque, 1.5)
Dv = R.densite(cx + 0.012, cy - 0.006, 0.07, N=N, ech=0.5, smin=1.0, smax=18); mv = len(R.XY) / (N / 0.14) ** 2
web = R.ton(Dv, mv, contraste=1.2, glow=0.6) * masque[..., None]
# bulles de lumière qui montent au-dessus du niveau
rg = np.random.default_rng(7); bul = np.zeros((N, N))
for _ in range(38):
    px = 0.5 + rg.normal(0, 0.06); py = rg.uniform(0.06, 0.30)
    bul[int(py * N), int(np.clip(px, 0.3, 0.7) * N)] = rg.uniform(0.4, 1.0) * (0.3 + py)
bul = gaussian_filter(bul, 2.2) * 60 + gaussian_filter(bul, 9) * 200
B = fond(N, k=0.65) + web
fin, lueur = K.etoiles(K.poly_verre(), N, graine=4)
B = ecran(B, fin[..., None] * CREME * 1.7 + lueur[..., None] * OR * 1.0)
B = ecran(B, bul[..., None] * CREME)
png(B, 'B-coupe.png')

# ---------- C. Sablier : la lumière lisse des débuts s'écoule et devient amas ----------
def sab(d, S, L):
    W = N * S; e = 0.012
    haut = [(0.25 * W, 0.12 * W), (0.75 * W, 0.12 * W)]
    d.line([(0.25 * W, 0.12 * W), (0.75 * W, 0.12 * W)], fill=255, width=int(L))
    d.line([(0.25 * W, 0.88 * W), (0.75 * W, 0.88 * W)], fill=255, width=int(L))
    for sx in (-1, 1):
        cote = []
        for k in range(101):
            u = k / 100; yy = 0.13 + 0.74 * u; z = abs(u - 0.5) * 2
            h = e + (0.215 - e) * (z ** 1.6) * (1 + 0.15 * np.sin(np.pi * z))
            cote.append(((0.5 + sx * h) * W, yy * W))
        d.line(cote, fill=255, width=int(L), joint='curve')
def sab_masque(haut):
    def f(d, S, L):
        W = N * S; e = 0.012; g, dr = [], []
        for k in range(101):
            u = k / 100; yy = 0.13 + 0.74 * u; z = abs(u - 0.5) * 2
            if (u < 0.5) != haut: continue
            h = e + (0.215 - e) * (z ** 1.6) * (1 + 0.15 * np.sin(np.pi * z)) - 0.012
            g.append(((0.5 - h) * W, yy * W)); dr.append(((0.5 + h) * W, yy * W))
        if haut: g = [p for p in g if p[1] > 0.20 * W]; dr = [p for p in dr if p[1] > 0.20 * W]
        else: g = [p for p in g if p[1] > 0.62 * W]; dr = [p for p in dr if p[1] > 0.62 * W]
        d.polygon(g + dr[::-1], fill=255)
    return f
ligne, halo = trace(N, sab, 8, 13)
mh, _ = trace(N, sab_masque(True), 0, 1); mb, _ = trace(N, sab_masque(False), 0, 1)
R.charge('pts12.npz'); Dh = R.densite(cx, cy, 0.09, N=N, ech=0.7, smin=1.2, smax=20); mhm = len(R.XY) / (N / 0.18) ** 2
jeune = R.ton(Dh, mhm, contraste=1.25, glow=0.6)
R.charge('pts.npz'); Db = R.densite(cx, cy - 0.02, 0.06, N=N, ech=0.5, smin=1.0, smax=18); mbm = len(R.XY) / (N / 0.12) ** 2
amas = R.ton(Db, mbm, contraste=1.2, glow=0.6)
fil = np.zeros((N, N)); rg = np.random.default_rng(3)
for _ in range(70):
    yy = rg.uniform(0.47, 0.70); xx = 0.5 + rg.normal(0, 0.004 + 0.02 * max(0, yy - 0.55))
    fil[int(yy * N), int(xx * N)] = rg.uniform(0.5, 1)
fil = gaussian_filter(fil, 1.6) * 30 + gaussian_filter(fil, 6) * 80
C = fond(N, k=0.6) + jeune * gaussian_filter(mh, 2)[..., None] + amas * gaussian_filter(mb, 2)[..., None]
fin, lueur = K.etoiles(K.poly_sablier(), N, graine=9)
C = ecran(C, fin[..., None] * CREME * 1.7 + lueur[..., None] * OR * 1.0)
C = ecran(C, fil[..., None] * CREME)
png(C, 'C-sablier.png')
print('ok')
