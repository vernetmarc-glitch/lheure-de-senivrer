"""Pourquoi la ligne O rend-elle une mousse reguliere plutot qu'une toile ?

Portee dev, mesure seule. On veut savoir si les pics de l'image sont ceux du
CHAMP DE DENSITE ou ceux de l'ECHANTILLONNAGE.
"""
import os, sys
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
sys.path.insert(0,os.path.normpath(os.path.join(HERE,'..','harness')))
import gen_chain as G  # noqa
from checks import matrix  # noqa

rows=matrix()['zoom_axis']['rows']
print("%-4s %11s %10s %9s %9s %9s %9s" %
      ("ligne","demi-champ","Mpc/px","cellule","Psi/cell","tranche","pts/px2"))
for c in "ONMLKJIH":
    half=rows[c]['halfwidth_mpc']
    nxy,nz,cell,box_xy,Lz,psirms=G.grid_for(half,G.RENDER_MARGIN)
    n=int(round(G.OUT_N*G.RENDER_MARGIN))
    px=2*half*G.RENDER_MARGIN/n
    slab=min(G.SLAB_FRAC*2*half, G.SLAB_MAX_MPC)
    ntot=nxy*nxy*nz*G.SUB_Z
    frac=min(slab/Lz,1.0)
    dans=ntot*frac
    rep=int(np.clip(round(G.TARGET_PROJ*G.RENDER_MARGIN**2/max(ntot*frac*0.9,1)),1,20))
    print("%-4s %11.1f %10.3f %9.3f %9.2f %9.1f %9.1f  (rep %d, %.0f pts dans la tranche)"
          % (c,half,px,cell,psirms/cell,slab,dans*rep/(n*n),rep,dans))
