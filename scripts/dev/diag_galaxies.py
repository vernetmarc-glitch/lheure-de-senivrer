"""Pourquoi T-015, T-016, T-017 et T-012 echouent-ils ENSEMBLE sur les lignes a
sprites ? Portee dev : mesure seule, aucune cuisson, aucune publication."""
import os, sys
import numpy as np
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.normpath(os.path.join(HERE,'..','..'))
sys.path.insert(0,os.path.join(ROOT,'scripts','harness')); sys.path.insert(0,os.path.join(ROOT,'scripts','dev'))
from checks import matrix  # noqa
from checks_image import _catalog, _positions, _local_extent, MARGIN  # noqa
import sprites_layer as S  # noqa
DATA=os.path.join(ROOT,'app','public','essai-v4','data','v4')
rows=matrix()['zoom_axis']['rows']

def load(c):
    f=os.path.join(DATA,'density_%s.png'%c)
    return np.asarray(Image.open(f).convert('L'),np.float64)/255.0 if os.path.exists(f) else None

for code in "GFEDCBA":
    img=load(code)
    if img is None: continue
    n=img.shape[0]; med=float(np.median(img))
    px=2.0*rows[code]['halfwidth_mpc']*MARGIN/n
    print("== ligne %s : %d px, %.5f Mpc/px, mediane %.3f ==" % (code,n,px,med))
    for g,cx,cy in _positions(code,img):
        r_px=g['radiusMpc']/px
        if r_px<0.5: continue
        y0,y1=int(max(0,cy-3)),int(min(n,cy+4)); x0,x1=int(max(0,cx-3)),int(min(n,cx+4))
        pic=float(img[y0:y1,x0:x1].max())
        # ou est le VRAI pic le plus proche ?
        R=int(max(6,3*r_px))
        y0,y1=int(max(0,cy-R)),int(min(n,cy+R+1)); x0,x1=int(max(0,cx-R)),int(min(n,cx+R+1))
        w=img[y0:y1,x0:x1]
        if w.size:
            iy,ix=np.unravel_index(np.argmax(w),w.shape)
            d=np.hypot(iy+y0-cy,ix+x0-cx)
        else: d=-1
        key=S.SPRITE_FILE.get(g['name'])
        print("  %-26s r=%6.2f px  pic/med %.2f  ecart au pic local %.1f px  %s"
              % ((g.get('name') or 'proc %.3f'%g['distanceMpc'])[:26], r_px,
                 pic/max(med,1e-9), d, 'sprite' if key else 'procedurale'))
