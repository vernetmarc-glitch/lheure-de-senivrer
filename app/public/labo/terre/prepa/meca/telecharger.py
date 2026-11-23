"""Téléchargement (runner GitHub) des données publiées du chantier S3b.

  - Cao, Collins, Pisarevsky, Flament, Li, Hasterok, Müller 2024, « Earth's tectonic and
    plate boundary evolution over 1.8 billion years », Geoscience Frontiers 15, 101922 ;
    modèle GPlates sur Zenodo (13628813, v2.4 ; 12800108 en secours) ;
  - Paleobiology Database : diversité des genres d'animaux marins par étage (comptage
    « range-through »), pour le ruban de la vie sous la frise.

Usage : python3 telecharger.py <répertoire des sources>
"""
import json, os, sys, time, urllib.request, zipfile, pathlib

SRC = pathlib.Path(sys.argv[1]); SRC.mkdir(parents=True, exist_ok=True)
ICI = pathlib.Path(__file__).resolve().parent


def log(*a): print(*a, flush=True)


def get(url, dest=None, essais=4):
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "chantier-terre/1.0"})
            with urllib.request.urlopen(req, timeout=600) as r:
                if dest is None: return r.read()
                tmp = str(dest) + ".part"
                with open(tmp, "wb") as f:
                    while True:
                        b = r.read(1 << 22)
                        if not b: break
                        f.write(b)
                os.replace(tmp, dest); return True
        except Exception as e:
            log("  échec", url, e); time.sleep(10 * (i + 1))
    return None


ok = False
for rec in ["13628813", "12800108"]:
    d = SRC / "cao" / rec; d.mkdir(parents=True, exist_ok=True)
    raw = get(f"https://zenodo.org/api/records/{rec}")
    if raw is None: continue
    (d / "record.json").write_bytes(raw); meta = json.loads(raw)
    log(f"== Cao {rec} : {meta['metadata'].get('title')} (version {meta['metadata'].get('version')})")
    for f in meta.get("files", []):
        key, taille = f["key"], f.get("size", 0)
        url = f["links"].get("self") or f["links"].get("download")
        log(f"  {key}  {taille/1e6:.1f} Mo")
        dest = d / key
        if not (dest.exists() and dest.stat().st_size == taille):
            if not get(url, dest): continue
        if key.lower().endswith(".zip"):
            cible = d / "x"
            if not cible.exists():
                with zipfile.ZipFile(dest) as z: z.extractall(cible)
            ok = True
    if ok: break
if not ok: raise SystemExit("modèle de Cao et al. 2024 introuvable")

# Paleobiology Database : genres d'animaux marins, par étage
pb = SRC / "pbdb"; pb.mkdir(exist_ok=True)
url = ("https://paleobiodb.org/data1.2/occs/diversity.txt?base_name=Metazoa&count=genera"
       "&time_reso=stage&envtype=marine&interval=Ediacaran,Holocene")
if not (pb / "diversite-genres-marins.txt").exists():
    if get(url, pb / "diversite-genres-marins.txt"):
        log("PBDB : diversité téléchargée")
    else:
        log("PBDB : injoignable")
if (pb / "diversite-genres-marins.txt").exists():
    (ICI / "pbdb-diversite-genres-marins.txt").write_bytes((pb / "diversite-genres-marins.txt").read_bytes())

# inventaire
lignes = []
for p in sorted((SRC / "cao").rglob("*")):
    if p.is_file() and "__MACOSX" not in str(p):
        lignes.append(f"{p.stat().st_size/1e6:9.2f} Mo  {p.relative_to(SRC)}")
(ICI / "inventaire-cao.txt").write_text("\n".join(lignes) + "\n")
log("\n".join(lignes))
