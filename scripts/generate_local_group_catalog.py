"""
Catalogue unique des galaxies du Groupe Local : galaxies réelles (distances
approximatives connues) + population procédurale complémentaire (1-10 Mpc).

Source de vérité UNIQUE, consommée par :
  - generate_layers.py (pour ancrer la structure du champ L2 sur ces positions)
  - le frontend (app/public/data/local_group_catalog.json, chargé par
    LocalGroupLayer.tsx) — garantit que le layer discret (points) et le champ
    continu L2 sont construits à partir des mêmes positions, donc cohérents.
"""

import json
import numpy as np

NEARBY_GALAXIES = [
    {"name": "Andromède (M31)", "distanceMpc": 0.78, "radiusMpc": 0.034, "angleDeg": 20, "brightness": 0.9, "isReal": True},
    {"name": "Triangulum (M33)", "distanceMpc": 0.84, "radiusMpc": 0.0092, "angleDeg": 55, "brightness": 0.7, "isReal": True},
    {"name": "Grand Nuage de Magellan", "distanceMpc": 0.05, "radiusMpc": 0.0022, "angleDeg": 200, "brightness": 0.75, "isReal": True},
    {"name": "Petit Nuage de Magellan", "distanceMpc": 0.061, "radiusMpc": 0.0011, "angleDeg": 210, "brightness": 0.65, "isReal": True},
    {"name": "Naine du Sagittaire", "distanceMpc": 0.024, "radiusMpc": 0.0015, "angleDeg": 320, "brightness": 0.5, "isReal": True},
    {"name": "NGC 6822", "distanceMpc": 0.46, "radiusMpc": 0.001, "angleDeg": 110, "brightness": 0.55, "isReal": True},
    {"name": "IC 10", "distanceMpc": 0.66, "radiusMpc": 0.0008, "angleDeg": 150, "brightness": 0.5, "isReal": True},
    {"name": "Leo I", "distanceMpc": 0.82, "radiusMpc": 0.0005, "angleDeg": 290, "brightness": 0.45, "isReal": True},
]


def generate_field_galaxies(seed=20260705, count=90):
    rng = np.random.default_rng(seed)
    galaxies = []
    for _ in range(count):
        galaxies.append({
            "name": None,
            "distanceMpc": float(1 + rng.random() * 9),
            "radiusMpc": float(0.0003 + rng.random() * 0.0012),
            "angleDeg": float(rng.random() * 360),
            "brightness": float(0.3 + rng.random() * 0.5),
            "isReal": False,
        })
    return galaxies


def build_catalog():
    return NEARBY_GALAXIES + generate_field_galaxies()


if __name__ == "__main__":
    catalog = build_catalog()
    out_path = "../app/public/data/local_group_catalog.json"
    with open(out_path, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"Catalogue genere : {len(catalog)} galaxies -> {out_path}")
