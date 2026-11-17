"""Galaxies de TNG50 autour de la jumelle de la Voie lactée, à plusieurs époques.

Pour chaque instantané : positions de tous les sous-halos (catalogue complet,
un seul champ à la fois sinon le serveur expire), puis la liste des galaxies
de masse stellaire > 10^7,5 Msun par tranches de masse (filtre de l'API).
On garde une tranche de ±10 Mpc/h comobiles autour du progéniteur, en
coordonnées comobiles relatives (périodiques), projetée sur (x, y).

Usage : python3 sim/tng/catalogue.py MPB.hdf5 SORTIE_DOSSIER snap1 snap2 …
Écrit SORTIE/cat-SNAP.npz : x, y (ckpc/h), logm (log10 M*/Msun), sf (SFR>0).
"""
import os, sys, time
import h5py
import numpy as np
import requests

BASE, SIM, H, BOITE = "https://www.tng-project.org/api", "TNG50-1", 0.6774, 35000.0
S = requests.Session(); S.headers["api-key"] = os.environ["TNG_API_KEY"].strip()


def get(url, params=None, fichier=None):
    url = (url if url.startswith("http") else f"{BASE}/{url}").replace("http://", "https://", 1)
    for k in range(6):
        try:
            r = S.get(url, params=params, timeout=900); r.raise_for_status()
            if fichier:
                open(fichier + ".part", "wb").write(r.content); os.replace(fichier + ".part", fichier); return fichier
            return r.json()
        except Exception as e:  # noqa: BLE001
            print("  essai", k + 1, e, flush=True); time.sleep(10 * (k + 1))
    raise RuntimeError(url)


def main():
    mpb, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    with h5py.File(mpb) as f:
        POS = dict(zip(f["SnapNum"][:].tolist(), f["SubhaloPos"][:]))
    bords = [7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 13]
    for sn in map(int, sys.argv[3:]):
        fo = f"{out}/cat-{sn:03d}.npz"
        if os.path.exists(fo): continue
        fp = os.environ.get("POSDIR", out) + f"/SubhaloPos-{sn:03d}.h5"
        if not os.path.exists(fp):
            get(f"{SIM}/files/groupcat-{sn}/", {"Subhalo": "SubhaloPos"}, fp)
        pos = h5py.File(fp)["Subhalo"]["SubhaloPos"][:]
        ids, lm, sfr = [], [], []
        for lo, hi in zip(bords[:-1], bords[1:]):
            prm = {"mass_stars__gt": 10 ** lo * H / 1e10, "mass_stars__lt": 10 ** hi * H / 1e10, "limit": 20000}
            url = f"{SIM}/snapshots/{sn}/subhalos/"
            while url:
                r = get(url, prm); prm = None
                for g in r["results"]:
                    ids.append(g["id"]); lm.append(0.5 * (lo + hi)); sfr.append(g["sfr"])
                url = r["next"]
        ids = np.array(ids, int); d = pos[ids] - POS[sn]; d -= BOITE * np.round(d / BOITE)
        dans = np.abs(d[:, 2]) < 10000
        np.savez(fo, x=d[dans, 0], y=d[dans, 1], logm=np.array(lm)[dans], sf=(np.array(sfr)[dans] > 0))
        print(f"snap {sn} : {len(ids)} galaxies, {dans.sum()} dans la tranche", flush=True)
        pass


if __name__ == "__main__":
    main()
