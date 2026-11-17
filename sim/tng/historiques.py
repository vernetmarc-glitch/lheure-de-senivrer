"""Historique de chaque halo de la tranche (plan « fond de carte » P3, 17/11/2026).

Le serveur TNG refuse les catalogues entiers des époques passées ; il sert en revanche la
branche principale (SubLink, « main progenitor branch ») de chaque sous-halo. Pour chaque
halo de la tranche affichée (masse > 10^9,5 Msun), on garde à chacun des 100 instantanés :
position, masse totale, masse stellaire, taux de formation d'étoiles, rayon de demi-masse.
Reprise possible : un fichier par halo, déjà présent = déjà fait.

Usage : python3 sim/tng/historiques.py IDS.npy SORTIE [FILS]
"""
import os, sys, time, io, concurrent.futures as cf
import numpy as np, h5py, requests

ids = np.load(sys.argv[1]); out = sys.argv[2]; fils = int(sys.argv[3]) if len(sys.argv) > 3 else 16
os.makedirs(out, exist_ok=True)
S = requests.Session(); S.headers["api-key"] = os.environ["TNG_API_KEY"].strip()
ad = requests.adapters.HTTPAdapter(pool_connections=fils, pool_maxsize=fils); S.mount("https://", ad)

def un(i):
    f = f"{out}/{i}.npz"
    if os.path.exists(f): return 0
    url = f"https://www.tng-project.org/api/TNG50-1/snapshots/99/subhalos/{i}/sublink/mpb.hdf5"
    for k in range(6):
        try:
            r = S.get(url, timeout=300); r.raise_for_status()
            with h5py.File(io.BytesIO(r.content)) as h:
                np.savez(f + ".part.npz", snap=h["SnapNum"][:], pos=h["SubhaloPos"][:], m=h["SubhaloMass"][:],
                         ms=h["SubhaloMassType"][:, 4], sfr=h["SubhaloSFR"][:], rh=h["SubhaloHalfmassRad"][:])
            os.replace(f + ".part.npz", f); return 1
        except Exception as e:  # noqa: BLE001
            time.sleep(5 * (k + 1))
    return -1

t0 = time.time(); fait = err = 0
with cf.ThreadPoolExecutor(fils) as ex:
    for n, r in enumerate(ex.map(un, ids.tolist())):
        fait += r == 1; err += r == -1
        if n % 200 == 0: print(f"[{time.time() - t0:6.0f} s] {n}/{len(ids)} faits {fait}, échecs {err}", flush=True)
print("FIN", fait, err, flush=True)
