"""Halos de matière noire de TNG50 autour de la Voie lactée → nuage de points.

Entre 1 et 60 millions d'années-lumière, la simulation N-corps de la page (une
particule ≈ 2,6·10¹⁰ Msun) n'a plus de détail. On prend alors les halos réels de
TNG50 (catalogue SUBFIND : position et masse de chaque sous-halo) et on les
représente par des points répartis selon un profil NFW (c = 10), un point pour
MP masses solaires : le rendu reste celui de la matière (même ton, même palette),
avec la vraie position et la vraie masse de chaque halo. Le profil interne est un
modèle statistique, pas la distribution simulée.

Usage : python3 sim/tng/halos.py MPB.hdf5 SORTIE_DOSSIER snap1 snap2 …
  puis  python3 sim/tng/halos.py --paquet SORTIE_DOSSIER SORTIE.bin
Format du paquet : u32 + en-tête JSON {epoques:[{snap,a,n}], L_ckpch, mp}, puis par
époque : x, y int16 [n] entrelacés (boîte TNG50 × 60000, relatifs à la Voie lactée),
h u8 [n] (log2(h/L)+14)·16.
"""
import glob, json, os, sys, time
import h5py
import numpy as np
import requests
from scipy.spatial import cKDTree

BASE, SIM, H, L = "https://www.tng-project.org/api", "TNG50-1", 0.6774, 35000.0
Z = {99: 0.0, 91: 0.1, 84: 0.2, 78: 0.3, 72: 0.4, 67: 0.5, 59: 0.7, 50: 1.0, 40: 1.5, 33: 2.0, 25: 3.0, 21: 4.0, 17: 5.0, 13: 6.0}
MP = 1e10          # masse représentée par un point (Msun)
MMIN = 10 ** 9.5   # halos plus légers ignorés
DEMI_TRANCHE = 10000.0


def get(S, url, params, fichier):
    for k in range(8):
        try:
            r = S.get(url, params=params, timeout=900); r.raise_for_status()
            open(fichier + ".part", "wb").write(r.content); os.replace(fichier + ".part", fichier); return
        except Exception as e:  # noqa: BLE001
            print("  essai", k + 1, e, flush=True); time.sleep(15 * (k + 1))
    raise RuntimeError(url)


def telecharge(mpb, out, snaps):
    """positions : catalogue complet (un champ) ; masses : liste filtrée de l'API (rapide)"""
    S = requests.Session(); S.headers["api-key"] = os.environ["TNG_API_KEY"].strip()
    for sn in snaps:
        f = f"{out}/SubhaloPos-{sn:03d}.h5"
        if not os.path.exists(f):
            get(S, f"{BASE}/{SIM}/files/groupcat-{sn}/", {"Subhalo": "SubhaloPos"}, f)
        fm = f"{out}/masses-{sn:03d}.npz"
        if not os.path.exists(fm):
            ids, lm = [], []
            url, prm = f"{BASE}/{SIM}/snapshots/{sn}/subhalos/", {"mass__gt": MMIN * H / 1e10, "limit": 25000}
            while url:
                for k in range(8):
                    try:
                        r = S.get(url.replace("http://", "https://", 1), params=prm, timeout=900); r.raise_for_status(); r = r.json(); break
                    except Exception as e:  # noqa: BLE001
                        print("  essai", k + 1, e, flush=True); time.sleep(15 * (k + 1))
                prm = None
                for g in r["results"]: ids.append(g["id"]); lm.append(g["mass_log_msun"])
                url = r["next"]
            np.savez(fm, ids=np.array(ids), logm=np.array(lm))
        print("snap", sn, "téléchargé", flush=True)


def nuage(out, sn, pos_mw, rng):
    a = 1 / (1 + Z[sn])
    pos = h5py.File(f"{out}/SubhaloPos-{sn:03d}.h5")["Subhalo"]["SubhaloPos"][:]
    M = np.load(f"{out}/masses-{sn:03d}.npz"); m = 10 ** M["logm"]
    d = pos[M["ids"]] - pos_mw; d -= L * np.round(d / L)
    t = np.abs(d[:, 2]) < DEMI_TRANCHE; d, m = d[t], m[t]
    # rayon du viriel comobile (200 fois la densité moyenne), en ckpc/h
    rhom = 0.3089 * 2.775e11 * H ** 2 / 1e9          # Msun / kpc³ comobile
    r200 = (3 * m / (4 * np.pi * 200 * rhom)) ** (1 / 3) * H
    n = np.maximum(1, np.round(m / MP)).astype(int)
    rs = r200 / 10
    # tirage NFW (c = 10) par inversion tabulée de la masse cumulée
    xq = np.linspace(1e-3, 10, 2000); mu = np.log(1 + xq) - xq / (1 + xq); mu /= mu[-1]
    centres = np.repeat(d[:, :2], n, axis=0); rsr = np.repeat(rs, n)
    u = rng.random(len(centres)); x = np.interp(u, mu, xq) * rsr
    v = rng.normal(size=(len(centres), 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
    p = centres + (v[:, :2] * x[:, None])
    single = np.repeat(n == 1, n); p[single] = centres[single]
    print(f"snap {sn} : {len(m)} halos dans la tranche, {len(p)} points", flush=True)
    return a, p


def paquet(out, sortie):
    with h5py.File(f"{out}/mpb.hdf5") as f:
        POS = dict(zip(f["SnapNum"][:].tolist(), f["SubhaloPos"][:]))
    snaps = sorted({int(os.path.basename(f)[11:14]) for f in glob.glob(f"{out}/SubhaloPos-*.h5")
                    if os.path.exists(f"{out}/masses-{os.path.basename(f)[11:14]}.npz")}, key=lambda s: Z[s], reverse=True)
    rng = np.random.default_rng(5); ep, blocs = [], []
    for sn in snaps:
        a, p = nuage(out, sn, POS[sn], rng)
        q = np.mod(p + L / 2, L)
        dist, _ = cKDTree(q, boxsize=[L, L]).query(q, k=9)
        h = np.maximum(dist[:, -1] * 0.7, 15.0) / L
        xy = np.clip(np.round(p / L * 60000), -32767, 32767).astype(np.int16)
        hh = np.clip(np.round((np.log2(h) + 14) * 16), 0, 255).astype(np.uint8)
        o = rng.permutation(len(xy)); ep.append({"snap": sn, "a": round(a, 5), "n": int(len(xy))}); blocs.append((xy[o], hh[o]))
    hd = json.dumps({"epoques": ep, "L_ckpch": L, "mp": MP}).encode()
    with open(sortie, "wb") as f:
        f.write(np.uint32(len(hd)).tobytes()); f.write(hd)
        if (4 + len(hd)) % 2: f.write(b"\0")
        for xy, hh in blocs:
            f.write(xy.tobytes()); f.write(hh.tobytes())
            if len(hh) % 2: f.write(b"\0")
    print("écrit", sortie, [e["n"] for e in ep], flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--paquet":
        paquet(sys.argv[2], sys.argv[3])
    else:
        os.makedirs(sys.argv[2], exist_ok=True)
        telecharge(sys.argv[1], sys.argv[2], list(map(int, sys.argv[3:])))
