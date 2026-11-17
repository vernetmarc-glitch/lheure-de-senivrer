"""Télécharge, pour la galaxie TNG50 537941 (Subbox0), les étoiles à moins de
RMAX kpc physiques de son centre, sur la liste d'instantanés snaps537.npy.
Reprenable : un fichier cadre-{snap}.npz par instantané terminé.
Usage : TNG_API_KEY=… python3 subbox537.py <dossier sonde> <dossier sortie> [fils]
"""
import os, sys, io, time, h5py, numpy as np, requests, concurrent.futures as cf

SONDE, SORTIE = sys.argv[1], sys.argv[2]
FILS = int(sys.argv[3]) if len(sys.argv) > 3 else 8
os.makedirs(SORTIE, exist_ok=True)
H, RMAX = 0.6774, 40.0
CHAMPS = "Coordinates,ParticleIDs,GFM_StellarFormationTime,Velocities,Masses"
S = requests.Session(); S.headers["api-key"] = os.environ["TNG_API_KEY"].strip()
s = h5py.File(f"{SONDE}/sbl0.h5"); fac = s["SubboxScaleFac"][:]
pos = np.load(f"{SONDE}/pos537.npy"); snaps = np.load(f"{SONDE}/snaps537.npy")

def morceau(snap, k, c, rcom):
    url = f"https://www.tng-project.org/api/TNG50-1-Subbox0/files/snapshot-{snap}.{k}.hdf5"
    for essai in range(6):
        try:
            r = S.get(url, params={"stars": CHAMPS}, timeout=900); r.raise_for_status(); break
        except Exception as e:
            if essai == 5: raise
            time.sleep(10 * (essai + 1))
    with h5py.File(io.BytesIO(r.content)) as h:
        if "PartType4" not in h: return None
        g = h["PartType4"]; x = g["Coordinates"][:]
        m = np.linalg.norm(x - c, axis=1) < rcom
        if not m.any(): return None
        return {n: g[n][:][m] for n in ("Coordinates", "ParticleIDs", "GFM_StellarFormationTime", "Velocities", "Masses")}

for snap in snaps:
    f = f"{SORTIE}/cadre-{snap}.npz"
    if os.path.exists(f): continue
    a = float(fac[snap]); c = pos[snap].astype(np.float64); rcom = RMAX * H / a
    t0 = time.time()
    with cf.ThreadPoolExecutor(FILS) as ex:
        res = [r for r in ex.map(lambda k: morceau(snap, k, c, rcom), range(68)) if r]
    if res:
        d = {n: np.concatenate([r[n] for r in res]) for n in res[0]}
    else:
        d = {"Coordinates": np.zeros((0, 3)), "ParticleIDs": np.zeros(0, np.uint64),
             "GFM_StellarFormationTime": np.zeros(0), "Velocities": np.zeros((0, 3)), "Masses": np.zeros(0)}
    np.savez(f + ".tmp.npz", a=a, centre=c, **d); os.replace(f + ".tmp.npz", f)
    print(f"{snap} a={a:.3f} étoiles={len(d['ParticleIDs'])} {time.time()-t0:.0f}s", flush=True)
print("fini", flush=True)
