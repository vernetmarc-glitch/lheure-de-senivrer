#!/usr/bin/env python3
"""Assemble les données publiées de la page labo/soleil à partir des sorties compactes.

    python3 assembler.py --trajectoire BHAC15_brut.txt --sortie ../donnees VARIANTE_DIR...

Chaque VARIANTE_DIR contient `extrait/` (instant_*.npz, bilan.jsonl, sphere.json) et
`beta` (rapport rotation/gravitation). La variante retenue l'est par un critère écrit
ici, pas à la main : une seule étoile (le puits principal porte ≥ 80 % de la masse
stellaire), puis la plus longue durée après la naissance (plafonnée à 100 000 ans), puis
le disque le plus mince.

Sorties (`donnees/`) :
  soleil.json             méta-données, bilans, étoiles, trajectoire, codage ;
  paquet_NN.bin           10 instants par fichier ; par instant : positions uint16 ×3
                          (0 = absente, sinon 32768 + 32767·x/L) puis température uint8 ;
  bhac15_1.0Msol.txt      trajectoire publiée, lignes brutes du fichier téléchargé.
"""
import argparse
import glob
import json
import os

import numpy as np

G_CGS = 6.674e-8
MSOL = 1.98847e33
RSOL = 6.957e10
LSOL = 3.828e33
AN = 3.15576e7
LOG_T = (0.8, 3.5)
N_INSTANTS = 120
PAR_PAQUET = 10
R_ETOILE = 3.0   # rayon d'une protoétoile en accrétion (R☉) — hypothèse, Palla & Stahler 1991-1993


def charge_variante(d):
    ex = os.path.join(d, "extrait")
    bilan = [json.loads(l) for l in open(os.path.join(ex, "bilan.jsonl"))]
    vus, b2 = set(), []
    for x in sorted(bilan, key=lambda x: x["num"]):
        if x["num"] not in vus:
            vus.add(x["num"]); b2.append(x)
    beta = open(os.path.join(d, "beta")).read().strip() if os.path.exists(os.path.join(d, "beta")) else "?"
    return {"dir": d, "ex": ex, "bilan": b2, "beta": beta,
            "sphere": json.load(open(os.path.join(ex, "sphere.json")))}


def score(v):
    b = v["bilan"]
    nais = next((x for x in b if x["puits"]), None)
    if nais is None:
        return (0, 0.0, 0.0), None
    der = b[-1]["puits"]
    mt = sum(p["m"] for p in der); mp = max(p["m"] for p in der)
    seule = 1 if mp >= 0.8 * mt else 0
    duree = min(b[-1]["t_an"] - nais["t_an"], 1e5)
    return (seule, duree, mp), nais["t_an"]


def choisit_instants(b, t_c):
    t = np.array([x["t_an"] for x in b])
    avant = np.where(t < t_c)[0]
    apres = np.where(t >= t_c)[0]
    choix = {0}
    if len(avant) > 1:
        dt = t_c - t[avant]
        cibles = np.geomspace(dt.max(), max(dt.min(), 50.0), N_INSTANTS // 2)
        for c in cibles:
            choix.add(int(avant[np.argmin(np.abs(np.log(dt) - np.log(c)))]))
    if len(apres):
        dt = t[apres] - t_c + 1.0
        cibles = np.geomspace(max(dt.min(), 1.0), dt.max(), N_INSTANTS // 2)
        for c in cibles:
            choix.add(int(apres[np.argmin(np.abs(np.log(dt) - np.log(c)))]))
    choix = sorted(choix)
    # compléter jusqu'à N_INSTANTS par les sorties les plus éloignées des choisies
    while len(choix) < min(N_INSTANTS, len(t)):
        reste = [i for i in range(len(t)) if i not in choix]
        ec = [min(abs(i - j) for j in choix) for i in reste]
        choix.append(reste[int(np.argmax(ec))]); choix.sort()
    return choix


def trajectoire(brut, sortie):
    lignes, entete = [], []
    for l in open(brut, encoding="utf-8", errors="replace"):
        c = l.split()
        if len(c) >= 6:
            try:
                vals = [float(x) for x in c[:6]]
            except ValueError:
                if "log t" in l or "Teff" in l:
                    entete.append(l.rstrip())
                continue
            if abs(vals[0] - 1.0) < 1e-6:
                lignes.append(l.rstrip())
    if not lignes:
        raise SystemExit("aucune ligne 1,0 M☉ dans la trajectoire téléchargée")
    with open(os.path.join(sortie, "bhac15_1.0Msol.txt"), "w", encoding="utf-8") as f:
        f.write("# Baraffe, Homeier, Allard & Chabrier 2015, A&A 577, A42 — trajectoire 1,0 M☉, Z☉\n")
        f.write("# lignes copiées sans modification de BHAC15_tracks+structure\n")
        f.write("# (perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/), téléchargé par le workflow chantier-soleil\n")
        for e in entete[:1]:
            f.write("# " + e.lstrip("! ").rstrip() + "\n")
        f.write("\n".join(lignes) + "\n")
    a = np.array([[float(x) for x in l.split()[:6]] for l in lignes])
    return {"age_an": (10 ** a[:, 1]).tolist(), "Teff": a[:, 2].tolist(),
            "L": (10 ** a[:, 3]).tolist(), "R": a[:, 5].tolist()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variantes", nargs="+")
    ap.add_argument("--trajectoire", required=True)
    ap.add_argument("--sortie", required=True)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)

    vs = []
    for d in a.variantes:
        try:
            vs.append(charge_variante(d))
        except Exception as e:  # noqa: BLE001
            print(f"variante {d} illisible : {e}")
    notes = []
    for v in vs:
        v["score"], v["t_c"] = score(v)
        notes.append(f"β = {v['beta']} : {len(v['bilan'])} sorties, jusqu'à {v['bilan'][-1]['t_an']:.0f} ans, "
                     f"naissance {v['t_c'] and round(v['t_c'])}, score {v['score']}")
        print(notes[-1])
    vs = [v for v in vs if v["t_c"] is not None]
    if not vs:
        raise SystemExit("aucune variante n'a encore formé d'étoile : rien à publier")
    v = max(vs, key=lambda v: v["score"])
    print(f"retenue : β = {v['beta']}")
    b, t_c = v["bilan"], v["t_c"]

    traj = trajectoire(a.trajectoire, a.sortie)

    choix = choisit_instants(b, t_c)
    npz = {x["num"]: os.path.join(v["ex"], f"instant_{x['num']:05d}.npz") for x in b}
    # masse portée par l'étoile principale et taux d'accrétion
    t_all = np.array([x["t_an"] for x in b])
    m_all = np.array([max((p["m"] for p in x["puits"]), default=0.0) for x in b])

    pos_l, T_l, H_l, instants = [], [], [], []
    for i in choix:
        x = b[i]
        z = np.load(npz[x["num"]])
        P = z["pos"].astype(np.float64)
        lt = z["logT"].astype(np.float64)
        hz = z["h"].astype(np.float64) if "h" in z.files else np.full(len(P), np.nan)
        vivant = ~np.isnan(P[:, 0])
        d = np.linalg.norm(P[vivant], axis=1)
        n = len(P)
        absorbes = n - vivant.sum()
        dd = np.sort(d)
        def rq(q):
            j = int(q * n) - absorbes
            return 0.0 if j <= 0 else float(dd[min(j, len(dd) - 1)])
        r50, r90 = rq(0.5), rq(0.9)
        # accrétion : dérivée centrée de la masse de l'étoile principale
        j0, j1 = max(i - 2, 0), min(i + 2, len(b) - 1)
        mdot = (m_all[j1] - m_all[j0]) / max(t_all[j1] - t_all[j0], 1e-9) if m_all[i] > 0 else 0.0
        M = m_all[i]
        Lacc = G_CGS * M * MSOL * max(mdot, 0.0) * MSOL / AN / (R_ETOILE * RSOL) / LSOL
        instants.append({"t": x["t_an"], "num": x["num"], "r50": r50, "r90": r90,
                         "puits": [{k: p[k] for k in ("x", "y", "z", "m")} for p in x["puits"]],
                         "mdot": mdot, "Lacc": Lacc})
        pos_l.append(P); T_l.append(lt); H_l.append(hz)

    # cadre de la caméra : il suit la moitié de la masse du nuage, de loin (exposant 0,6),
    # pour que l'on VOIE le nuage se contracter ; jamais en deçà de 250 UA
    r50_0 = instants[0]["r50"]
    for ins in instants:
        r = max(ins["r50"], 1.0)
        ins["R_vue"] = max(1.15 * 9500.0 * (r / r50_0) ** 0.6, 250.0)
    for k, ins in enumerate(instants):
        voisins = [instants[j]["R_vue"] for j in range(max(k - 1, 0), min(k + 2, len(instants)))]
        ins["L"] = 2.4 * max(voisins)

    N = len(pos_l[0])
    for k0 in range(0, len(instants), PAR_PAQUET):
        nom = f"paquet_{k0 // PAR_PAQUET:02d}.bin"
        with open(os.path.join(a.sortie, nom), "wb") as f:
            for k in range(k0, min(k0 + PAR_PAQUET, len(instants))):
                ins = instants[k]
                P = pos_l[k]; lt = T_l[k]
                q = np.zeros((N, 3), np.uint16)
                ok = ~np.isnan(P[:, 0]) & (np.abs(P) <= ins["L"]).all(axis=1)
                q[ok] = np.clip(np.round(32768 + 32767 * P[ok] / ins["L"]), 1, 65535).astype(np.uint16)
                tb = np.zeros(N, np.uint8)
                tb[ok] = np.clip(np.round(1 + 254 * (lt[ok] - LOG_T[0]) / (LOG_T[1] - LOG_T[0])), 1, 255).astype(np.uint8)
                ins["fichier"] = nom; ins["octet"] = f.tell()
                f.write(q.astype("<u2").tobytes()); f.write(tb.tobytes())

    # un point affiché porte la masse de n_sphere/N particules : noyau élargi de (n_sphere/N)^(1/3)
    sph = v["sphere"]
    fac = (sph["n_sphere"] / N) ** (1 / 3)
    LOG_H = (-1.0, 4.5)
    hb = np.zeros((len(instants), N), np.uint8)
    for k, hz in enumerate(H_l):
        ok = ~np.isnan(hz) & (hb[k] == 0)
        hb[k, ok] = np.clip(np.round(1 + 254 * (np.log10(np.maximum(hz[ok] * fac, 1e-3)) - LOG_H[0]) / (LOG_H[1] - LOG_H[0])), 1, 255).astype(np.uint8)
    hb.tofile(os.path.join(a.sortie, "h.bin"))
    emp = f"{len(instants)}-{N}-{sum(i['num'] for i in instants)}-{round(sum(i['L'] for i in instants))}"
    json.dump({"codage_h": {"log_min": LOG_H[0], "log_max": LOG_H[1]}, "source": "longueur de lissage Phantom × (n_sphere/N)^(1/3)",
               "facteur": fac, "n_points": N, "n_instants": len(instants), "empreinte": emp},
              open(os.path.join(a.sortie, "h.json"), "w"))
    meta = {
        "version": 1,
        "source": {
            "code": "Phantom (Price et al. 2018, PASA 35, e031), SPH, gravité, puits",
            "phantom": os.environ.get("PHANTOM_SHA", "?"),
            "nuage": "sphère de Bonnor-Ebert, 1,2 M☉, rayon 0,15 al, 10 K, rotation solide",
            "beta": v["beta"],
            "n_sphere": sph["n_sphere"], "masse_particule": sph["masse_particule"],
            "variantes": notes,
            "luminosite_accretion": f"L = G M Ṁ / R*, R* = {R_ETOILE} R☉ (hypothèse)",
        },
        "unites": {"longueur": "UA", "temps": "an", "masse": "M☉"},
        "n_points": N, "codage_T": {"log_min": LOG_T[0], "log_max": LOG_T[1]},
        "t_naissance": t_c,
        "instants": instants,
        "bilan": [{k: x[k] for k in ("t_an", "masse", "Lx", "Ly", "Lz", "msphere", "Lsphere", "rho_max_cgs")}
                  for x in b],
        "trajectoire": traj,
    }
    for x in meta["bilan"]:
        x["t"] = x.pop("t_an")
    with open(os.path.join(a.sortie, "soleil.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
    tot = sum(os.path.getsize(p) for p in glob.glob(os.path.join(a.sortie, "*")))
    print(f"{len(instants)} instants × {N} points, {tot/1e6:.1f} Mo")


if __name__ == "__main__":
    main()
