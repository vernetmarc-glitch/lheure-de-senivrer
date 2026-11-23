"""Téléchargement et préparation des données publiées du chantier S6 (runner GitHub).

Usage : python preparer.py <cache des téléchargements> <répertoire des intermédiaires>

Sorties (intermédiaires compacts, préparés ensuite par construire.py dans le bac à sable) :
  relief_0p1.npz        relief + bathymétrie, 0,1° (serveur GMT, earth_relief_06m, SRTM15+)
  blackmarble_0p1.npz   NASA Black Marble 2016, niveaux de gris, 0,1° (3600 × 1800)
  blackmarble_2016_01deg.jpg   la même en couleur (référence visuelle des planches)
  spratt2016.txt        niveau marin 0–798 ka (Spratt & Lisiecki 2016)
  bintanja2008.txt      niveau marin 0–3 Ma (Bintanja & van de Wal 2008)
  timmermann2022_S1.xlsx, timmermann2022_S2.xlsx   tables supplémentaires (sites ROAD)
  hyde33_*.npz          HYDE 3.3 (si joignable) : population par tranche, 0,5°, + 5' agrégé
  sources.json          URL, taille, empreinte SHA-256 de chaque fichier téléchargé
"""
import hashlib, html, io, json, os, re, sys, time, pathlib, urllib.request, urllib.parse, zipfile
import numpy as np

DL = pathlib.Path(sys.argv[1]); DL.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "curl/8.5.0", "Accept": "*/*"}
sources = {}

def log(*a):
    print(" ".join(str(x) for x in a), flush=True)

def get(url, nom, essais=3, timeout=900):
    dest = DL / nom
    if dest.exists() and dest.stat().st_size > 0:
        log("  (cache)", nom)
    else:
        for i in range(essais):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=timeout) as r, open(str(dest) + ".part", "wb") as f:
                    while True:
                        b = r.read(1 << 22)
                        if not b:
                            break
                        f.write(b)
                os.replace(str(dest) + ".part", dest)
                break
            except Exception as e:
                log("  échec", url, e)
                time.sleep(5 * (i + 1))
        else:
            return None
    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    sources[nom] = {"url": url, "octets": dest.stat().st_size, "sha256": h}
    log("  ok", nom, dest.stat().st_size)
    return dest

def texte(url, n=2_000_000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.geturl(), r.read(n).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return f"ERR {e}"[:120], url, ""

# ---------------------------------------------------------------- relief
log("== relief (GMT earth_relief_06m, gridline 0,1°)")
f = get("https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_06m_g.grd", "earth_relief_06m_g.grd")
if f and not (OUT / "relief_0p1.npz").exists():
    import netCDF4
    ds = netCDF4.Dataset(f)
    log("  variables", list(ds.variables))
    vz = [v for v in ds.variables if ds.variables[v].ndim == 2][0]
    z = np.asarray(ds.variables[vz][:], dtype=np.float32)
    lat = np.asarray(ds.variables[[v for v in ds.variables if v.startswith("lat") or v == "y"][0]][:])
    lon = np.asarray(ds.variables[[v for v in ds.variables if v.startswith("lon") or v == "x"][0]][:])
    log("  forme", z.shape, "lat", lat[0], lat[-1], "lon", lon[0], lon[-1], "z", z.min(), z.max())
    # grille aux noeuds (3601 × 1801) -> mailles centrées 0,1° (3600 × 1800) : moyenne des 4 coins
    if lat[0] > lat[-1]:
        z = z[::-1]; lat = lat[::-1]
    zc = 0.25 * (z[:-1, :-1] + z[1:, :-1] + z[:-1, 1:] + z[1:, 1:])
    zc = zc[::-1]  # ligne 0 = nord
    np.savez_compressed(OUT / "relief_0p1.npz", z=np.round(zc).astype(np.int16),
                        note="mailles 0,1°, ligne 0 au nord (89,95°N), colonne 0 à 179,95°W ; m")
    log("  relief_0p1.npz", zc.shape)

# ---------------------------------------------------------------- Black Marble
log("== Black Marble 2016")
BM = "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/144000/"
f = get(BM + "144897/BlackMarble_2016_01deg_gray_geo.tif", "BlackMarble_2016_01deg_gray_geo.tif")
if f:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = np.asarray(Image.open(f))
    log("  forme", im.shape, im.dtype, im.min(), im.max())
    if im.ndim == 3:
        im = im[..., 0]
    np.savez_compressed(OUT / "blackmarble_0p1.npz", v=im.astype(np.uint8),
                        note="NASA Black Marble 2016, niveaux de gris, 0,1°, ligne 0 au nord")
f = get(BM + "144898/BlackMarble_2016_01deg.jpg", "BlackMarble_2016_01deg.jpg")
if f:
    (OUT / "blackmarble_2016_01deg.jpg").write_bytes(f.read_bytes())

# ---------------------------------------------------------------- niveau marin
log("== niveau marin")
for nom, url in [("spratt2016.txt", "https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/spratt2016/spratt2016.txt"),
                 ("bintanja2008.txt", "https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/bintanja2008/bintanja2008.txt")]:
    f = get(url, nom)
    if f:
        (OUT / nom).write_bytes(f.read_bytes())

# ---------------------------------------------------------------- Timmermann 2022
log("== Timmermann et al. 2022, tables supplémentaires")
ESM = "https://static-content.springer.com/esm/art%3A10.1038%2Fs41586-022-04600-9/MediaObjects/"
for k, nom in [(3, "timmermann2022_S1.xlsx"), (4, "timmermann2022_S2.xlsx")]:
    f = get(ESM + f"41586_2022_4600_MOESM{k}_ESM.xlsx", nom)
    if f:
        (OUT / nom).write_bytes(f.read_bytes())

rec = []
def note(*a):
    s = " ".join(str(x) for x in a); log(s); rec.append(s)

note("== habitats (serveur IBS) : reconnaissance")
for u in ["https://climatedata.ibs.re.kr/data/hominin-habitats",
          "https://climatedata.ibs.re.kr:8443/thredds/catalog.html",
          "https://climatedata.ibs.re.kr:8443/thredds/catalog/catalog.html",
          "https://climatedata.ibs.re.kr:8443/thredds/catalog.xml",
          "https://climatedata.ibs.re.kr:8443/las/",
          "https://climatedata.ibs.re.kr:8443/las/getDatasets.do"]:
    st, fin, t = texte(u)
    note(f"[{st}] {u} -> {fin} ({len(t)} car.)")
    for h in sorted(set(re.findall(r'(?:href|url|urlPath|ID)=["\']([^"\']+)', t)))[:150]:
        note("   ->", html.unescape(h))
    if "hominin" in t.lower():
        for m in re.finditer(r".{0,160}hominin.{0,160}", t, re.I):
            note("   …", m.group(0).replace("\n", " ")[:320])

note("== HYDE 3.3 : DANS (doi 10.17026/dans-25g-gez3)")
st, fin, t = texte("https://doi.org/10.17026/dans-25g-gez3")
note(f"[{st}] doi -> {fin} ({len(t)} car.)")
hote = urllib.parse.urlsplit(fin).netloc if isinstance(st, int) else ""
fichiers = []
for base in ([f"https://{hote}"] if hote else []) + ["https://ssh.datastations.nl", "https://lifesciences.datastations.nl", "https://phys-techsciences.datastations.nl", "https://dataverse.nl"]:
    st, fin2, t = texte(f"{base}/api/datasets/:persistentId/?persistentId=doi:10.17026/dans-25g-gez3")
    note(f"[{st}] {base} api ({len(t)} car.)")
    if st == 200 and t:
        try:
            d = json.loads(t)
            fs = d["data"]["latestVersion"]["files"]
            for x in fs:
                df = x["dataFile"]
                fichiers.append((base, df["id"], x.get("directoryLabel", ""), df["filename"], df.get("filesize", 0)))
            break
        except Exception as e:
            note("   lecture api", e, t[:300])
note(f"   {len(fichiers)} fichiers")
for b, i, dl, fn, sz in fichiers[:400]:
    note(f"   {i}\t{dl}/{fn}\t{sz}")
(OUT / "hyde33_fichiers.json").write_text(json.dumps(fichiers, ensure_ascii=False, indent=0))
(OUT / "reconnaissance-2.txt").write_text("\n".join(rec) + "\n", encoding="utf-8")
(OUT / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1))
log("fin")
