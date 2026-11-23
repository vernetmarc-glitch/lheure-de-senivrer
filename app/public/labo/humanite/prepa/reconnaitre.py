"""Reconnaissance des sources (tourne sur le runner GitHub : le bac à sable ne joint
pas ces sites). Écrit prepa/reconnaissance.txt : statut, taille, listes de liens.

Sources visées :
  - HYDE 3.3 (Utrecht, doi 10.24416/UU01-67UHB4) : population 10 000 av. J.-C. -> 2023, 5'
  - NASA Black Marble 2016 (niveaux de gris, 0,1° et 3 km)
  - Timmermann et al. 2022 (Nature 604, 495) : habitats (serveur IBS), table S1 (sites)
  - niveau marin : Spratt & Lisiecki 2016 ; Bintanja & van de Wal 2008 (NOAA)
  - relief : serveur GMT (earth_relief), ETOPO 2022 (NOAA)
  - ROAD (ROCEEH)
"""
import re, sys, pathlib, urllib.request, urllib.parse, html

SORTIE = pathlib.Path(sys.argv[1])
lignes = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lignes.append(s)

UA = {"User-Agent": "curl/8.5.0", "Accept": "*/*"}

def tete(url, lire=0):
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=60) as r:
            n = r.headers.get("Content-Length")
            corps = r.read(lire) if lire else b""
            return r.status, n, r.geturl(), corps
    except urllib.error.HTTPError as e:
        return e.code, None, url, b""
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"[:160], None, url, b""

def liens(url, motif=None, lire=400000):
    st, n, fin, corps = tete(url, lire)
    log(f"[{st}] {url} -> {fin} ({n} o)")
    t = corps.decode("utf-8", "replace")
    if "anubis" in t.lower():
        log("   (page Anubis : protection anti-robots)")
    hs = sorted(set(html.unescape(h) for h in re.findall(r'href=["\']([^"\'#]+)', t)))
    out = []
    for h in hs:
        a = urllib.parse.urljoin(fin, h)
        if motif is None or re.search(motif, a, re.I):
            out.append(a)
    for a in out[:200]:
        log("   ->", a)
    return out, t

log("== HYDE 3.3")
for u in ["https://geo.public.data.uu.nl/vault-hyde/",
          "https://geo.public.data.uu.nl/vault-hyde-data/",
          "https://doi.org/10.24416/UU01-67UHB4",
          "https://public.yoda.uu.nl/geo/UU01/67UHB4.html"]:
    out, _ = liens(u)
    for a in out:
        if "3.3" in urllib.parse.unquote(a) and a.startswith("https://geo.public"):
            out2, _ = liens(a)
            for b in out2:
                if b.startswith(a) and b != a:
                    out3, _ = liens(b)
                    for c in out3:
                        if c.startswith(b) and c != b and c.endswith("/"):
                            liens(c)

log("== Black Marble 2016")
BM = "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/144000/"
for f in ["144897/BlackMarble_2016_01deg_gray_geo.tif", "144897/BlackMarble_2016_3km_gray_geo.tif",
          "144898/BlackMarble_2016_01deg.jpg", "144898/BlackMarble_2016_3km.jpg"]:
    st, n, fin, _ = tete(BM + f)
    log(f"[{st}] {BM+f} ({n} o)")

log("== Timmermann 2022")
for u in ["https://climatedata.ibs.re.kr/data/hominin-habitats/hominin-habitats-data",
          "https://climatedata.ibs.re.kr/data/hominin-habitats",
          "https://climatedata.ibs.re.kr/data/papers/timmermann-et-al-2022-nature"]:
    liens(u, r"opendap|thredds|las|dods|\.nc|download|hominin|data/")
for k in range(1, 5):
    for ext in ["xlsx", "xls", "csv", "zip", "pdf", "txt"]:
        u = f"https://static-content.springer.com/esm/art%3A10.1038%2Fs41586-022-04600-9/MediaObjects/41586_2022_4600_MOESM{k}_ESM.{ext}"
        st, n, fin, _ = tete(u)
        if st == 200:
            log(f"[{st}] {u} ({n} o)")
liens("https://www.nature.com/articles/s41586-022-04600-9", r"MOESM|static-content|supplementary")

log("== Niveau marin")
for u in ["https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/spratt2016/spratt2016.txt",
          "https://www.ncei.noaa.gov/pub/data/paleo/contributions_by_author/bintanja2008/bintanja2008.txt",
          "https://www1.ncdc.noaa.gov/pub/data/paleo/contributions_by_author/spratt2016/spratt2016.txt"]:
    st, n, fin, c = tete(u, 300)
    log(f"[{st}] {u} ({n} o) {c[:120]!r}")

log("== Relief")
for u in ["https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_05m_g.grd",
          "https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_06m_g.grd",
          "https://oceania.generic-mapping-tools.org/server/earth/earth_relief/earth_relief_10m_g.grd",
          "https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc",
          "https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/ice_surface/grid_registered/netcdf/ETOPO1_Ice_g_gmt4.grd.gz"]:
    st, n, fin, _ = tete(u)
    log(f"[{st}] {u} ({n} o)")

log("== ROAD")
liens("https://www.roceeh.uni-tuebingen.de/roadweb/smarty_road_simple_search.php")
liens("https://www.roceeh.uni-tuebingen.de/roadweb/", r"road|query|login|guest|csv|download")

SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
