"""Télécharge le progéniteur principal d'une galaxie TNG50 à N époques
réparties uniformément en temps cosmique, avec les identifiants des
particules (pour suivre chaque étoile d'une époque à l'autre).

Usage : python3 sim/tng/telechargement.py SUBHALO SORTIE [N] [T_MIN_GA]
Clef : variable d'environnement TNG_API_KEY.
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
import h5py
import numpy as np
import requests

BASE, SIM = "https://www.tng-project.org/api", "TNG50-1"
S = requests.Session()
S.headers["api-key"] = os.environ["TNG_API_KEY"].strip()


def get(url, params=None, fichier=None):
    url = url if url.startswith("http") else f"{BASE}/{url}"
    url = url.replace("http://", "https://", 1)
    for k in range(5):
        try:
            r = S.get(url, params=params, timeout=900)
            r.raise_for_status()
            if fichier:
                tmp = fichier + ".part"
                open(tmp, "wb").write(r.content)
                os.replace(tmp, fichier)
                return fichier
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  essai {k+1} : {e}", flush=True)
            time.sleep(6 * (k + 1))
    raise RuntimeError(url)


def age_gyr(z):
    a = 1 / (1 + np.asarray(z)); Om, H0 = 0.3089, 67.74; OL = 1 - Om
    return 2 / (3 * np.sqrt(OL)) * np.arcsinh(np.sqrt(OL / Om) * a ** 1.5) * 977.8 / H0


def main():
    sub, sortie = int(sys.argv[1]), sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 48
    tmin = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8
    os.makedirs(sortie, exist_ok=True)
    snaps = get(f"{SIM}/snapshots/")
    zs = np.array([s["redshift"] for s in snaps]); nums = np.array([s["number"] for s in snaps])
    t = age_gyr(zs)
    mpbf = f"{sortie}/mpb.hdf5"
    if not os.path.exists(mpbf):
        d = get(f"{SIM}/snapshots/99/subhalos/{sub}/")
        get(d["trees"]["sublink_mpb"], fichier=mpbf)
    with h5py.File(mpbf) as f:
        msn = list(f["SnapNum"][:]); mid = f["SubfindID"][:]; grn = f["SubhaloGrNr"][:]
    halo = os.environ.get("MODE", "") == "halo"   # découpe du groupe entier (satellites compris)
    cibles = np.linspace(tmin, t[-1], n)
    choix = sorted({int(nums[np.argmin(abs(t - c))]) for c in cibles})
    choix = [s for s in choix if s in msn]
    print(f"{len(choix)} époques : {choix}", flush=True)
    prm = {"stars": "Coordinates,Velocities,Masses,GFM_StellarFormationTime,ParticleIDs",
           "gas": "Coordinates,Masses,ParticleIDs"}
    if os.environ.get("CHAMPS") == "gaz":          # gaz seul, avec le taux de formation d'étoiles
        prm = {"gas": "Coordinates,Masses,ParticleIDs,StarFormationRate,Velocities"}

    def une(sn):
        sid = int(mid[msn.index(sn)])
        fic = f"{sortie}/e{sn:03d}.hdf5"
        obj = f"halos/{int(grn[msn.index(sn)])}" if halo else f"subhalos/{sid}"
        if not os.path.exists(fic):
            get(f"{SIM}/snapshots/{sn}/{obj}/cutout.hdf5", prm, fic)
        print(f"  snap {sn} ({sid}) {os.path.getsize(fic)/1e6:.0f} Mo", flush=True)
        return {"snap": sn, "id": sid, "z": float(zs[sn]), "t": float(t[sn])}

    with ThreadPoolExecutor(3) as ex:
        meta = list(ex.map(une, choix))
    json.dump({"subhalo": sub, "epoques": meta}, open(f"{sortie}/meta.json", "w"), indent=1)
    print("fini", flush=True)


if __name__ == "__main__":
    main()
