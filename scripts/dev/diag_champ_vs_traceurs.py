"""La structure a O et N est-elle ABSENTE, ou seulement noyee sous la grenaille ?

`field_projection` rend la somme de delta sur l'epaisseur de la tranche : un
CONTRASTE, de moyenne nulle. C'est le signal exact, sans aucun bruit de tirage.
`render_full` depose des traceurs : son bruit de tirage vaut 1/sqrt(N) par pixel.

On compare les deux, et on en deduit le nombre de traceurs par pixel qu'il
faudrait pour que le signal emerge.
"""
import os, sys
import numpy as np
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
sys.path.insert(0,os.path.normpath(os.path.join(HERE,'..','harness')))
import gen_chain as G  # noqa
from checks import matrix  # noqa

rows=matrix()['zoom_axis']['rows']
print("%-4s %14s %12s %10s %14s" %
      ("ligne","signal (delta)","grenaille","S/B","traceurs/px2 requis"))
for c in ("O","N","M","L","K"):
    half=rows[c]['halfwidth_mpc']
    L=G.bake_layer(c, half, G.RENDER_MARGIN, 107)
    fp=np.asarray(G.field_projection(L,L.delta),np.float64)
    sig=float(fp.std())                      # contraste projete, sans dimension
    tr=np.asarray(G.render_full(L,107),np.float64)
    s=ndimage.gaussian_filter(tr,2.0)
    grain=float((tr-s).std()/max(tr.mean(),1e-12))
    # N traceurs par pixel -> grenaille 1/sqrt(N). Pour que S/B = 3 il faut
    # 1/sqrt(N) <= sig/3.
    req=(3.0/max(sig,1e-9))**2
    print("%-4s %14.4f %12.4f %10.2f %14.3g"%(c,sig,grain,sig/max(grain,1e-9),req))
    del L,fp,tr
