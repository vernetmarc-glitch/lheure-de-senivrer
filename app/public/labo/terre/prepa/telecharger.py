"""Téléchargement des données publiées (tourne sur le runner GitHub ; Zenodo
n'est pas joignable du bac à sable).

  - Merdith et al. 2021, modèle de plaques 1 Ga -> 0 (Zenodo 4450249 ; 13635864) ;
  - Scotese & Wright 2018, PaleoDEM 540 Ma -> 0, pas de 5 Ma (Zenodo 5460860) ;
  - modèle de plaques PALEOMAP (Scotese 2016), celui des PaleoDEM, par
    plate-model-manager (dépôt EarthByte/GPlates), plus Merdith2021 en secours.

Usage : python3 telecharger.py <répertoire des sources>
"""
import json, os, sys, time, urllib.request, zipfile, pathlib, traceback

SRC = pathlib.Path(sys.argv[1]); SRC.mkdir(parents=True, exist_ok=True)
RECORDS = {"merdith": ["4450249", "13635864"], "paleodem": ["5460860"]}
LIMITE = {"merdith": 2.0e9, "paleodem": 6.0e9}
journal = []

def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); journal.append(s)

def get(url, dest=None, essais=4):
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "chantier-terre/1.0"})
            with urllib.request.urlopen(req, timeout=600) as r:
                if dest is None:
                    return r.read()
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

for nom, recs in RECORDS.items():
    for rec in recs:
        d = SRC / nom / rec; d.mkdir(parents=True, exist_ok=True)
        raw = get(f"https://zenodo.org/api/records/{rec}")
        if raw is None: log("RECORD INJOIGNABLE", rec); continue
        (d / "record.json").write_bytes(raw)
        meta = json.loads(raw)
        log(f"== {nom} {rec} : {meta.get('metadata', {}).get('title')} "
            f"(version {meta.get('metadata', {}).get('version')})")
        for f in meta.get("files", []):
            key, taille = f["key"], f.get("size", 0)
            url = f["links"].get("self") or f["links"].get("download")
            log(f"  {key}  {taille/1e6:.1f} Mo")
            if taille > LIMITE[nom]: log("   (trop gros, ignoré)"); continue
            dest = d / key
            if not (dest.exists() and dest.stat().st_size == taille):
                if not get(url, dest): continue
            if key.lower().endswith(".zip"):
                cible = d / "x" / key[:-4]
                if not cible.exists():
                    try:
                        with zipfile.ZipFile(dest) as z: z.extractall(cible)
                    except Exception as e: log("   dézip impossible", e)

# Modèles de plaques par plate-model-manager
try:
    from plate_model_manager import PlateModelManager
    pmm = PlateModelManager()
    noms = pmm.get_available_model_names()
    log("== plate-model-manager :", ", ".join(noms))
    (SRC / "pmm").mkdir(exist_ok=True)
    (SRC / "pmm" / "models.json").write_text(json.dumps(pmm.models, indent=1))
    for m in ["PALEOMAP", "Merdith2021"]:
        try:
            mod = pmm.get_model(m, data_dir=str(SRC / "pmm"))
            log(f"  {m} : {mod.get_small_time()}–{mod.get_big_time()} Ma ; couches {mod.get_avail_layers()}")
            log("   rotations", mod.get_rotation_model())
            for c in mod.get_avail_layers():
                try: log("   ", c, mod.get_layer(c))
                except Exception as e: log("   ", c, "échec", e)
        except Exception as e:
            log("  ", m, "échec", e); traceback.print_exc()
except Exception as e:
    log("plate-model-manager indisponible", e)

(SRC / "journal-telechargement.txt").write_text("\n".join(journal))
