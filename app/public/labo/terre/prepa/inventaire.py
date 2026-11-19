"""Inventaire des sources téléchargées : arborescence, en-têtes, variables NetCDF,
plaques et bornes temporelles des fichiers de rotation. Écrit un texte."""
import sys, os, pathlib, json
SRC = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
L = []
def p(*a): L.append(" ".join(str(x) for x in a))
jt = SRC / "journal-telechargement.txt"
if jt.exists(): p(jt.read_text()); p("")
p("== Arborescence (hors .nc détaillés)")
ncs = []
for root, dirs, files in os.walk(SRC):
    dirs.sort()
    r = pathlib.Path(root)
    nc = sorted(f for f in files if f.lower().endswith((".nc", ".grd", ".tif", ".tiff")))
    ncs += [r / f for f in nc]
    autres = sorted(f for f in files if f not in nc and not f.endswith(".part"))
    p(f"[{r.relative_to(SRC)}] {len(files)} fichiers, dont {len(nc)} grilles")
    for f in autres[:60]:
        p(f"    {f}  {(r/f).stat().st_size/1e6:.2f} Mo")
    if nc: p("    grilles :", nc[:3], "…", nc[-3:])
try:
    import netCDF4
    vus = set()
    for f in ncs:
        k = (f.parent, f.suffix)
        if k in vus: continue
        vus.add(k)
        try:
            ds = netCDF4.Dataset(f)
            p(f"== {f.relative_to(SRC)}")
            for v in ds.variables.values():
                p("   ", v.name, v.dimensions, v.shape, v.dtype, {a: str(getattr(v, a))[:60] for a in v.ncattrs()})
            ds.close()
        except Exception as e: p("  illisible", f, e)
except Exception as e: p("netCDF4 absent", e)
try:
    import pygplates
    for f in sorted(SRC.rglob("*.rot")):
        fc = pygplates.FeatureCollection(str(f))
        ids, tmax = set(), 0
        for ft in fc:
            ts = ft.get_total_reconstruction_sequence()
            if ts is None: continue
            ids.add(ts[1]); tr = ft.get_valid_time()
            prop = ft.get_value(pygplates.PropertyName.gpml_total_reconstruction_pole)
            try:
                for s in prop.get_enabled_time_samples():
                    tmax = max(tmax, s.get_time())
            except Exception: pass
        p(f"== ROT {f.relative_to(SRC)} : {len(fc)} séquences, {len(ids)} plaques mobiles, t max {tmax}")
    for f in sorted(list(SRC.rglob("*.gpml")) + list(SRC.rglob("*.gpmlz")) + list(SRC.rglob("*.shp"))):
        try:
            fc = pygplates.FeatureCollection(str(f))
            pids = {ft.get_reconstruction_plate_id() for ft in fc}
            p(f"== {f.relative_to(SRC)} : {len(fc)} objets, {len(pids)} plaques")
        except Exception as e: p("  illisible", f, e)
except Exception as e: p("pygplates", e)
OUT.write_text("\n".join(L)); print("\n".join(L))
