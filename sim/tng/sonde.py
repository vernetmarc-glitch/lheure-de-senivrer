"""Sonde TNG50 — étape 4 (galaxies).

Vérifie la clef, choisit une galaxie analogue de la Voie lactée dans TNG50-1
à z=0, récupère sa branche de progéniteurs (SubLink) puis des découpes
d'étoiles et de gaz à une douzaine d'époques, pour fabriquer la « danse »
de la Voie lactée.

La clef n'est jamais écrite dans le dépôt : elle est lue dans la variable
d'environnement TNG_API_KEY (secret GitHub, ou fichier local hors dépôt).

Usage : python3 sim/tng/sonde.py SORTIE [NB_EPOQUES]
"""
import json, os, sys, time
import numpy as np
import requests

BASE = "https://www.tng-project.org/api"
SIM = "TNG50-1"
H = 0.6774
CLE = os.environ.get("TNG_API_KEY", "").strip()
if not CLE:
    sys.exit("TNG_API_KEY absente")
S = requests.Session()
S.headers["api-key"] = CLE


def get(url, params=None, fichier=None, essais=4):
    if not url.startswith("http"):
        url = f"{BASE}/{url.lstrip('/')}"
    url = url.replace("http://", "https://", 1)
    for k in range(essais):
        try:
            r = S.get(url, params=params, timeout=600)
            r.raise_for_status()
            if fichier:
                with open(fichier, "wb") as f:
                    f.write(r.content)
                return fichier
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  essai {k+1} échoué : {e}", flush=True)
            time.sleep(5 * (k + 1))
    raise RuntimeError(url)


def choisit_voie_lactee():
    # masse stellaire 4–7e10 Msun, centrale ; unités API : 1e10 Msun/h
    lo, hi = 4 * H, 7 * H
    res = get(f"{SIM}/snapshots/99/subhalos/",
              {"mass_stars__gt": lo, "mass_stars__lt": hi, "primary_flag": 1,
               "limit": 60, "order_by": "-mass_stars"})
    print(f"{res['count']} candidates", flush=True)
    meilleurs = []
    for c in res["results"][:25]:
        d = get(c["url"])
        if not d.get("primary_flag", 1):
            continue
        # disque : forte rotation, peu de formation d'étoiles éteinte
        sfr = d.get("sfr", 0)
        m200 = d.get("mass_dm", 0) / H * 1e10
        print(f"  id {d['id']}: M* {d['mass_stars']/H:.2f}e10, SFR {sfr:.2f}, "
              f"Mdm {m200:.2e}", flush=True)
        if 0.5 < sfr < 5 and 5e11 < m200 < 2.5e12:
            meilleurs.append((abs(sfr - 1.6), d))
    meilleurs.sort(key=lambda x: x[0])
    return meilleurs[0][1] if meilleurs else get(res["results"][0]["url"])


def main():
    sortie = sys.argv[1]
    n_ep = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    os.makedirs(sortie, exist_ok=True)
    print("clef :", "valide" if get("")["simulations"] else "?", flush=True)
    g = choisit_voie_lactee()
    print(f"Voie lactée retenue : subhalo {g['id']}", flush=True)
    mpb = get(g["trees"]["sublink_mpb"], fichier=f"{sortie}/mpb.hdf5")
    import h5py
    with h5py.File(mpb) as f:
        snaps = f["SnapNum"][:]
        ids = f["SubfindID"][:]
    snaps_cibles = [99, 91, 84, 78, 72, 67, 59, 50, 40, 33, 25, 21, 17, 13][:n_ep]
    meta = {"subhalo": g["id"], "epoques": []}
    for sn in snaps_cibles:
        if sn not in snaps:
            continue
        sid = int(ids[list(snaps).index(sn)])
        url = f"{SIM}/snapshots/{sn}/subhalos/{sid}/cutout.hdf5"
        prm = {"stars": "Coordinates,Masses,GFM_StellarFormationTime,Velocities",
               "gas": "Coordinates,Masses,StarFormationRate"}
        fic = get(url, prm, fichier=f"{sortie}/decoupe-{sn:03d}.hdf5")
        print(f"  snap {sn} subhalo {sid} : {os.path.getsize(fic)/1e6:.1f} Mo",
              flush=True)
        meta["epoques"].append({"snap": int(sn), "id": sid})
    json.dump(meta, open(f"{sortie}/meta.json", "w"), indent=1)
    print("fini", flush=True)


if __name__ == "__main__":
    main()
