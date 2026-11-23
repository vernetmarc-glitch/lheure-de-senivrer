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
try:
    import zipfile_deflate64  # noqa: F401  (HYDE 3.2.1 : zip de 5 Go en Deflate64)
except ImportError:
    pass

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


class FichierDistant(io.RawIOBase):
    """Fichier HTTP lu par plages (Range) : permet d'ouvrir un zip de 5 Go sans le télécharger."""
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, headers=dict(UA, Range="bytes=0-0"))
        with urllib.request.urlopen(req, timeout=120) as r:
            self.url = r.geturl()
            cr = r.headers.get("Content-Range")
            if not cr:
                raise IOError("pas de lecture par plages")
            self.taille = int(cr.split("/")[-1])
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.taille + off)
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.taille - self.pos
        if n == 0 or self.pos >= self.taille: return b""
        fin = min(self.taille, self.pos + n) - 1
        for i in range(5):
            try:
                req = urllib.request.Request(self.url, headers=dict(UA, Range=f"bytes={self.pos}-{fin}"))
                with urllib.request.urlopen(req, timeout=300) as r:
                    b = r.read()
                break
            except Exception as e:
                log("   plage", self.pos, fin, e); time.sleep(5 * (i + 1))
        else:
            raise IOError("lecture distante impossible")
        self.pos += len(b)
        return b
    def readinto(self, buf):
        b = self.read(len(buf)); buf[:len(b)] = b; return len(b)


def lire_asc(octets):
    t = octets.split(b"\n", 6)
    entete = {}
    for l in t[:6]:
        k, v = l.split()[:2]; entete[k.decode().lower()] = float(v)
    a = np.array(t[6].split(), dtype=np.float64)
    nc, nr = int(entete["ncols"]), int(entete["nrows"])
    a = a[:nr * nc].reshape(nr, nc)
    a[a == entete.get("nodata_value", -9999)] = 0
    a[a < 0] = 0
    return a, entete

note("== HYDE : DANS (doi 10.17026/dans-25g-gez3)")
st, fin, t = texte("https://doi.org/10.17026/dans-25g-gez3")
hote = urllib.parse.urlsplit(fin).netloc if isinstance(st, int) else ""
fichiers = []
for base in ([f"https://{hote}"] if hote else []) + ["https://archaeology.datastations.nl"]:
    st, fin2, t = texte(f"{base}/api/datasets/:persistentId/?persistentId=doi:10.17026/dans-25g-gez3")
    if st == 200 and t:
        try:
            for x in json.loads(t)["data"]["latestVersion"]["files"]:
                df = x["dataFile"]
                fichiers.append((base, df["id"], x.get("directoryLabel", ""), df["filename"], df.get("filesize", 0)))
            break
        except Exception as e:
            note("   lecture api", e)
note(f"   {len(fichiers)} fichiers")
if not fichiers:   # DANS parfois indisponible (503) : identifiant connu du zip de base
    fichiers = [["https://archaeology.datastations.nl", 5490328, "", "HYDE3_2_1-baseline.zip", 5339653974]]
(OUT / "hyde33_fichiers.json").write_text(json.dumps(fichiers, ensure_ascii=False, indent=0))

# ---------------------------------------------------------------- HYDE
note("== HYDE : recherche de la version 3.3 sur DANS")
for base in ["https://archaeology.datastations.nl", "https://ssh.datastations.nl"]:
    st, fin, t = texte(f"{base}/api/search?q=HYDE&type=dataset&per_page=50")
    note(f"[{st}] {base} recherche ({len(t)} car.)")
    try:
        for it in json.loads(t)["data"]["items"]:
            note("   ", it.get("global_id"), "|", it.get("name"), "|", it.get("published_at"))
    except Exception as e:
        note("   ", e)

ANNEES = list(range(-10000, 0, 1000)) + [0, 200, 400, 600, 800, 1000, 1200, 1400, 1500, 1600, 1700, 1750,
                                         1800, 1850, 1900, 1920, 1940, 1950, 1960, 1970, 1980, 1990, 2000,
                                         2005, 2010, 2015, 2016, 2017]
def nom_annee(a):
    return f"{-a}BC" if a < 0 else f"{a}AD"

sortie_hyde = OUT / "hyde_0p5.npz"
if not sortie_hyde.exists():
    import json as _j
    fichiers = _j.loads((OUT / "hyde33_fichiers.json").read_text()) if (OUT / "hyde33_fichiers.json").exists() else []
    base_zip = [f for f in fichiers if f[3].endswith("baseline.zip")]
    if base_zip:
        b, ident, _, nom, taille = base_zip[0]
        url = f"{b}/api/access/datafile/{ident}"
        note("HYDE 3.2.1 baseline :", url, taille)
        try:
            fd = FichierDistant(url)
            Z = zipfile.ZipFile(io.BufferedReader(fd, buffer_size=1 << 20))
            noms = Z.namelist()
            note(f"   {len(noms)} membres ; exemples :", noms[:12])
            (OUT / "hyde_membres.txt").write_text("\n".join(noms) + "\n")
            pops, totaux, sous = [], {}, None
            for an in ANNEES:
                n = nom_annee(an)
                cand = [m for m in noms if re.search(rf"(^|/){n}_pop\.zip$", m)] or \
                       [m for m in noms if re.search(rf"popc_{n}\.asc$", m)]
                if not cand:
                    note("   introuvable", n); continue
                m = cand[0]
                donnees = Z.read(m)
                if m.endswith(".zip"):
                    zi = zipfile.ZipFile(io.BytesIO(donnees))
                    mm = [x for x in zi.namelist() if re.search(rf"popc_{n}\.asc$", x)]
                    donnees = zi.read(mm[0])
                a, ent = lire_asc(donnees)
                tot = float(a.sum())
                totaux[an] = tot
                # 5' -> 0,5° : blocs de 6 × 6
                nr, nc = a.shape
                p05 = a.reshape(nr // 6, 6, nc // 6, 6).sum(axis=(1, 3))
                pops.append(p05.astype(np.float32))
                if an == ANNEES[-1]:
                    sous = a.reshape(nr // 6, 6, nc // 6, 6).transpose(0, 2, 1, 3).reshape(nr // 6, nc // 6, 36)
                note(f"   {n} : {tot/1e6:.2f} millions ({m}, {len(donnees)/1e6:.0f} Mo)")
            P = np.stack(pops)
            occ = np.flatnonzero(P.max(axis=0).ravel() > 0)
            S = sous.reshape(-1, 36)[occ]
            S = np.round(255 * S / np.maximum(S.sum(axis=1, keepdims=True), 1e-9)).astype(np.uint8)
            np.savez_compressed(sortie_hyde, annees=np.array([a for a in ANNEES if a in totaux]),
                                cellules=occ.astype(np.int32), pop=P.reshape(len(P), -1)[:, occ],
                                sous_2017=S, version="HYDE 3.2.1 (DANS doi 10.17026/dans-25g-gez3)",
                                note="0,5° : 720 × 360, ligne 0 au nord ; cellules = indices à plat ; "
                                     "sous_2017 = poids des 6 × 6 mailles de 5' en 2017 (somme 255)")
            (OUT / "hyde_totaux_annees.json").write_text(_j.dumps({str(k): v for k, v in totaux.items()}, indent=1))
            note("   hyde_0p5.npz :", P.shape, len(occ), "cellules habitées")
        except Exception as e:
            import traceback; note("   HYDE échec :", e, traceback.format_exc()[-800:])

# ---------------------------------------------------------------- habitats Timmermann 2022
note("== habitats (Timmermann et al. 2022) : THREDDS")
TH = "https://climatedata.ibs.re.kr:8443/thredds/"
st, fin, t = texte(TH + "hominin_habitatsCatalog.xml")
note(f"[{st}] catalogue ({len(t)} car.)")
note(t[:3000])
chemins = re.findall(r'urlPath="([^"]+)"', t)
for cat in re.findall(r'xlink:href="([^"]+)"', t)[:10]:
    st2, f2, t2 = texte(urllib.parse.urljoin(TH + "hominin_habitatsCatalog.xml", cat))
    note(f"[{st2}] sous-catalogue {cat} ({len(t2)} car.)"); note(t2[:2000])
    chemins += re.findall(r'urlPath="([^"]+)"', t2)
note("   chemins :", chemins)
hab = OUT / "habitats_timmermann2022.npz"
if chemins and not hab.exists():
    try:
        import netCDF4
        for ch in chemins:
            u = TH + "dodsC/" + ch
            try:
                ds = netCDF4.Dataset(u)
            except Exception as e:
                note("   OPeNDAP", u, e); continue
            note("   ouvert", u)
            for v in ds.variables:
                note("     ", v, ds.variables[v].dimensions, ds.variables[v].shape, getattr(ds.variables[v], "long_name", ""))
            res = {}
            for v in ds.variables:
                x = ds.variables[v]
                if x.ndim == 3 and x.shape[0] > 100:
                    # pas de 5 ka sur 0-300 ka, de 25 ka avant ; temps 0..2000 (2 Ma -> 0)
                    nt = x.shape[0]
                    idx = sorted(set(list(range(nt - 1, max(-1, nt - 302), -5)) + list(range(nt - 1, -1, -25))))
                    arr = np.stack([np.asarray(x[i], dtype=np.float32) for i in idx])
                    q = np.where(np.isfinite(arr), np.clip(np.round(arr * 254), 0, 254), 255).astype(np.uint8)
                    res[v] = q; res[v + "_indices"] = np.array(idx)
                    note("     ->", v, q.shape)
                elif x.ndim == 1:
                    res[v + "_axe"] = np.asarray(x[:])
            if res:
                np.savez_compressed(hab, **res, source=u)
                break
    except Exception as e:
        import traceback; note("   habitats échec", e, traceback.format_exc()[-600:])

(OUT / "reconnaissance-2.txt").write_text("\n".join(rec) + "\n", encoding="utf-8")
(OUT / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1))
log("fin")
