#!/usr/bin/env python3
"""Longueur de lissage de chaque point publié, pour un rendu en densité de colonne.

    python3 app/public/labo/soleil/densite.py

Lit `donnees/` (positions publiées) et écrit `densite/h.bin` + `densite/h.json` : pour
chaque instant et chaque point, h = demi-distance au 32ᵉ voisin parmi les points
publiés (UA), codé log10 sur un octet (0 = point absent). La page dessine chaque point
comme un noyau gaussien de largeur h : la luminance est alors la densité de colonne du
gaz, indépendante du zoom de la caméra (unités physiques, jamais des pixels).

À relancer après chaque dépôt de données par le workflow (`h.json` porte l'empreinte
des données ; la page et les contrôles refusent une densité qui ne correspond pas).
"""
import json
import os

import numpy as np
from scipy.spatial import cKDTree

ICI = os.path.dirname(os.path.abspath(__file__))
DON = os.path.join(ICI, "donnees")
SORT = os.path.join(ICI, "densite")
LOG_H = (-1.0, 4.5)
KVOIS = 32


def empreinte(meta):
    """Empreinte simple, recalculable à l'identique dans la page."""
    ins = meta["instants"]
    return f"{len(ins)}-{meta['n_points']}-{sum(i['num'] for i in ins)}-{round(sum(i['L'] for i in ins))}"


def main():
    meta = json.load(open(os.path.join(DON, "soleil.json"), encoding="utf-8"))
    N = meta["n_points"]
    os.makedirs(SORT, exist_ok=True)
    out = np.zeros((len(meta["instants"]), N), np.uint8)
    for k, ins in enumerate(meta["instants"]):
        with open(os.path.join(DON, ins["fichier"]), "rb") as f:
            f.seek(ins["octet"])
            q = np.frombuffer(f.read(6 * N), "<u2").reshape(N, 3).astype(np.float64)
        ok = (q > 0).all(axis=1)
        p = (q[ok] - 32768) / 32767 * ins["L"]
        if len(p) > KVOIS + 1:
            d, _ = cKDTree(p).query(p, k=KVOIS + 1)
            h = np.maximum(d[:, -1] / 2, 1e-3)
            c = np.clip(np.round(1 + 254 * (np.log10(h) - LOG_H[0]) / (LOG_H[1] - LOG_H[0])), 1, 255)
            out[k, ok] = c.astype(np.uint8)
    out.tofile(os.path.join(SORT, "h.bin"))
    json.dump({"codage_h": {"log_min": LOG_H[0], "log_max": LOG_H[1]}, "voisins": KVOIS,
               "n_points": N, "n_instants": len(meta["instants"]), "empreinte": empreinte(meta)},
              open(os.path.join(SORT, "h.json"), "w"))
    print(f"{len(meta['instants'])} instants × {N} points → densite/h.bin ({out.nbytes/1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
