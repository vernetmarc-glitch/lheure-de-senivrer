#!/usr/bin/env python3
"""Extrait chaque sortie Phantom d'un dossier de simulation en une forme compacte.

    python3 extraire.py RUN SORTIE [--npoints 32768]

Pour chaque sortie `RUN/soleil_NNNNN` pas encore extraite :
  - bilan sur TOUTES les particules (gaz actif + puits) : masse, moment cinétique
    (orbital + spin des puits), densité maximale ;
  - pour un sous-échantillon fixe (tiré une fois, graine fixe) des particules de la
    sphère : position (UA, float32) et log10 densité (float16), NaN si accrétée.
Écrit `SORTIE/instant_NNNNN.npz` et ajoute une ligne à `SORTIE/bilan.jsonl`.
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import sarracen

UA = 1.495978707e13
UDIST = 1.0e16           # cm (soleil.setup)
UMASS = 1.98847e33       # g
G = 6.674e-8
UTIME = np.sqrt(UDIST ** 3 / (G * UMASS))
AN = 3.15576e7
UDENS = UMASS / UDIST ** 3


def n_sphere(run):
    try:
        txt = open(os.path.join(run, "setup.log"), encoding="utf-8", errors="replace").read()
        m = re.search(r"particle numbers: \(sphere, low-density medium, total\):\s*(\d+)\s+(\d+)\s+(\d+)", txt)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("sortie")
    ap.add_argument("--npoints", type=int, default=32768)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    fichiers = sorted(f for f in glob.glob(os.path.join(a.run, "soleil_[0-9][0-9][0-9][0-9][0-9]")))
    choix_f = os.path.join(a.sortie, "choix.npy")
    for f in fichiers:
        num = f[-5:]
        dest = os.path.join(a.sortie, f"instant_{num}.npz")
        if os.path.exists(dest):
            continue
        lu = sarracen.read_phantom(f, separate_types="sinks", ignore_inactive=True)
        sdf, sinks = (lu[0], lu[1]) if isinstance(lu, list) else (lu, None)
        mp = float(sdf.params["massoftype"] if "massoftype" in sdf.params else sdf.params["mass"])
        hfact = float(sdf.params.get("hfact", 1.2))
        t = float(sdf.params["time"])
        iorig = sdf["iorig"].to_numpy().astype(np.int64)
        x = sdf[["x", "y", "z"]].to_numpy(np.float64)
        v = sdf[["vx", "vy", "vz"]].to_numpy(np.float64)
        h = sdf["h"].to_numpy(np.float64)
        rho = mp * (hfact / h) ** 3
        # température du gaz donnée par Phantom : T = (P/ρ) μ m_H / k_B, μ = 2,31
        # (k_B/m_H en unités de code = 6,220e-3 pour 1e16 cm et 1 M☉)
        T = sdf["pressure"].to_numpy(np.float64) / rho * 2.31 / 6.220e-3
        if not os.path.exists(choix_f):
            ns = n_sphere(a.run)
            if ns is None:  # repli : particules initialement dans la sphère (rayon 14,19)
                ns = int(np.sum(np.linalg.norm(x, axis=1) < 14.19 * 1.0001))
            rng = np.random.default_rng(20261119)
            choix = np.sort(rng.choice(np.arange(1, ns + 1), size=min(a.npoints, ns), replace=False))
            np.save(choix_f, choix)
            json.dump({"n_sphere": ns, "masse_particule": mp, "npart": len(x)},
                      open(os.path.join(a.sortie, "sphere.json"), "w"))
        choix = np.load(choix_f)
        # bilan sur tout
        mgaz = mp * len(x)
        Lg = (mp * np.cross(x, v)).sum(axis=0)
        ns = json.load(open(os.path.join(a.sortie, "sphere.json")))["n_sphere"]
        Lsph = (mp * np.cross(x[iorig <= ns], v[iorig <= ns])).sum(axis=0)
        ps = []
        Ms, Ls = 0.0, np.zeros(3)
        if sinks is not None and len(sinks):
            for _, s in sinks.iterrows():
                r = np.array([s["x"], s["y"], s["z"]]); u = np.array([s["vx"], s["vy"], s["vz"]])
                spin = np.array([s.get("spinx", 0.0), s.get("spiny", 0.0), s.get("spinz", 0.0)])
                Ms += s["m"]; Ls += s["m"] * np.cross(r, u) + spin
                ps.append({"x": r[0] * UDIST / UA, "y": r[1] * UDIST / UA, "z": r[2] * UDIST / UA,
                           "vx": u[0], "vy": u[1], "vz": u[2], "m": float(s["m"]),
                           "macc": float(s.get("maccreted", 0.0))})
        L = Lg + Ls
        ligne = {"num": int(num), "t_an": t * UTIME / AN, "masse": mgaz + Ms, "mgaz": mgaz, "mpuits": Ms,
                 "Lx": L[0], "Ly": L[1], "Lz": L[2],
                 "Lsphere": (Lsph + Ls).tolist(), "msphere": mp * int(np.sum(iorig <= ns)) + Ms, "rho_max_cgs": float(rho.max() * UDENS),
                 "npart": len(x), "T_max": float(T.max()), "puits": ps}
        with open(os.path.join(a.sortie, "bilan.jsonl"), "a") as fb:
            fb.write(json.dumps(ligne) + "\n")
        # sous-échantillon
        idx = np.full(len(choix), -1)
        ordre = np.argsort(iorig)
        pos_ = np.searchsorted(iorig[ordre], choix)
        pos_ = np.clip(pos_, 0, len(iorig) - 1)
        trouve = iorig[ordre][pos_] == choix
        idx[trouve] = ordre[pos_[trouve]]
        P = np.full((len(choix), 3), np.nan, np.float32)
        R = np.full(len(choix), np.nan, np.float16)
        TT = np.full(len(choix), np.nan, np.float16)
        TT[trouve] = np.log10(T[idx[trouve]]).astype(np.float16)
        P[trouve] = (x[idx[trouve]] * UDIST / UA).astype(np.float32)
        R[trouve] = np.log10(rho[idx[trouve]] * UDENS).astype(np.float16)
        np.savez_compressed(dest, t_an=t * UTIME / AN, pos=P, logrho=R, logT=TT)
        print(f"{os.path.basename(f)} t={t*UTIME/AN:9.0f} ans  n={len(x)}  puits={len(ps)}  "
              f"Mpuits={Ms:.3f}  rho_max={rho.max()*UDENS:.2e}", flush=True)


if __name__ == "__main__":
    main()
