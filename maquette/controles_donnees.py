"""Contrôles sur les données de la Voie lactée (sorties de suivi.py), avant la page.

Cohérence de la danse : deux étoiles voisines au début ET à la fin d'un intervalle
doivent rester voisines au milieu. Si l'interpolation les envoie chacune dans un sens
(un morceau qui tourne d'un côté, l'autre de l'autre), elles s'écartent à mi-chemin.
Protège le retour de Marc du 17/11 : « des morceaux qui se scindent en deux, l'un
tournant dans un sens, l'autre dans l'autre ».

Usage : python3 maquette/controles_donnees.py SUIVI.npz
"""
import sys
import numpy as np
from scipy.spatial import cKDTree

D = np.load(sys.argv[1])
r, phi, k, t = D["r"], D["phi"], D["k"], D["t"]
z = D["z"] if "z" in D else np.zeros_like(r)


def xyz(e, sel):
    return np.column_stack([r[e, sel] * np.cos(phi[e, sel]), r[e, sel] * np.sin(phi[e, sel]), z[e, sel]])


tot, mauvais = 0, 0
for e in range(len(t) - 1):
    ok = np.isfinite(r[e]) & np.isfinite(r[e + 1]) & (r[e] > 12)
    idx = np.where(ok)[0]
    if len(idx) < 50:
        continue
    A, B = xyz(e, idx), xyz(e + 1, idx)
    pa = cKDTree(A).query_pairs(1.0, output_type="ndarray")
    if len(pa) == 0:
        continue
    pb = np.linalg.norm(B[pa[:, 0]] - B[pa[:, 1]], axis=1) < 1.0
    pa = pa[pb]
    if len(pa) == 0:
        continue
    d = phi[e + 1, idx] - phi[e, idx]; d -= 2 * np.pi * np.round(d / (2 * np.pi)); d += 2 * np.pi * k[e, idx]
    rm = 0.5 * (r[e, idx] + r[e + 1, idx]); pm = phi[e, idx] + 0.5 * d; zm = 0.5 * (z[e, idx] + z[e + 1, idx])
    M = np.column_stack([rm * np.cos(pm), rm * np.sin(pm), zm])
    droit = k[e, idx] == -128                                  # trajet en ligne droite
    M[droit] = 0.5 * (A[droit] + B[droit])
    sep = np.linalg.norm(M[pa[:, 0]] - M[pa[:, 1]], axis=1)
    tot += len(sep); mauvais += (sep > 4).sum()
frac = mauvais / max(tot, 1)
ok = frac < 0.02
print(f"{'OK ' if ok else 'ÉCHEC'}  danse cohérente (voisins restent voisins)   {frac:.1%} de paires écartées sur {tot}   ← « morceaux qui se scindent en deux »")
sys.exit(0 if ok else 1)
