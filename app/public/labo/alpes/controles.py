"""Contrôles de la page labo S7 — L'orogenèse alpine, vue d'avion.

Usage : python3 app/public/labo/alpes/controles.py
Sert app/public sur un port libre (8820–8829), mesure le paquet PUBLIÉ (donnees/)
tel que la page le lit, puis la page elle-même dans Chrome (Playwright, 390 × 844).

Exigences servies : N16 (compression et érosion simultanées), N17 (relief réaliste),
N20 (fluide sur téléphone), N23 / D-41 (fin sur le relief réel, barre qui ralentit).
"""
import gzip, http.server, json, os, socket, sys, threading, time, urllib.request
from functools import partial
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", "..", ".."))   # app/public
CHEMIN = "/labo/alpes/"
resultats = []


def ok(nom, cond, detail=""):
    resultats.append((nom, bool(cond), detail))
    print(("  OK   " if cond else "  ÉCHEC ") + nom + (f" — {detail}" if detail else ""), flush=True)


def port_libre():
    for p in range(8820, 8830):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                pass
    raise SystemExit("aucun port libre entre 8820 et 8829")


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def servir():
    port = port_libre()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Silencieux, directory=RACINE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}{CHEMIN}"


def lire(url):
    return urllib.request.urlopen(url, timeout=30).read()


# ---------------------------------------------------------------- paquet publié
def decoder_paquet(base, meta):
    """Décode les états exactement comme la page (voir alpes.js, decoderPaquet)."""
    n = meta["n"]
    nn = n * n
    H, U, E, X = [], [], [], []
    for p in meta["paquets"]:
        brut = gzip.decompress(lire(base + "donnees/" + p["fichier"]))
        k = p["nombre"]
        b = np.frombuffer(brut[: 2 * nn * k], np.uint8).reshape(2, k, nn)   # plans bas / haut
        d = (b[0].astype(np.uint16) | (b[1].astype(np.uint16) << 8)).view(np.int16).astype(np.int32)
        q = np.cumsum(d, axis=0)                       # deltas sans perte dans le paquet
        o = 2 * nn * k
        u8 = np.frombuffer(brut[o:], np.uint8).reshape(3, k, nn)
        for i in range(k):
            H.append(q[i] * meta["h_pas_m"] + meta["h_zero_m"])
            U.append(u8[0, i]); E.append(u8[1, i]); X.append(u8[2, i])
    return np.array(H, np.float32), np.array(U), np.array(E), np.array(X)


def taux(v, meta):
    """octet -> mm/an (codage racine carrée)."""
    return (v.astype(np.float32) / 255.0) ** 2 * meta["taux_max_mm_an"]


def controles_donnees(base):
    print("Paquet publié", flush=True)
    try:
        meta = json.loads(lire(base + "donnees/meta.json"))
    except Exception as e:
        ok("D1 paquet présent (donnees/meta.json)", False, str(e))
        return None
    t = np.array(meta["temps_Ma"], float)
    ok("D1 paquet présent (donnees/meta.json)", True, f"{len(t)} états")
    pas = np.diff(t)
    ok("D2 états de −45 Ma à aujourd'hui, ordonnés",
       abs(t[0] + 45) < 1e-6 and abs(t[-1]) < 1e-9 and (pas > 0).all(),
       f"{t[0]} → {t[-1]} Ma")
    avant = pas[t[1:] <= -2 + 1e-9]
    apres = pas[t[1:] > -2 + 1e-9]
    ok("D3 pas réguliers ≤ 250 ka, plus serrés sur les 2 derniers Ma",
       len(avant) and avant.max() <= 0.25 + 1e-9 and len(apres) and apres.max() < avant.min(),
       f"avant {avant.max() if len(avant) else '–'} Ma, après {apres.max() if len(apres) else '–'} Ma")
    taille = sum(int(urllib.request.urlopen(base + "donnees/" + p["fichier"]).headers["Content-Length"])
                 for p in meta["paquets"])
    ok("D4 paquet léger (< 40 Mo)", taille < 40e6, f"{taille/1e6:.1f} Mo")

    H, U8, E8, X8 = decoder_paquet(base, meta)
    n = meta["n"]
    reel = np.frombuffer(gzip.decompress(lire(base + "donnees/reel_256.bin.gz")), "<u2").astype(np.float32)
    reel = reel * meta["h_pas_m"] + meta["h_zero_m"]

    # N16 : soulèvement et érosion ensemble, aux mêmes endroits
    bons, details = 0, []
    for k in range(1, len(t)):
        u, e = taux(U8[k], meta), taux(E8[k], meta)
        zone = u > 0.1
        if zone.mean() < 0.01:
            details.append((t[k], "pas de soulèvement")); continue
        frac = (e[zone] > 0.05).mean()
        r = np.corrcoef(u, e)[0, 1]
        if frac >= 0.6 and r >= 0.5:
            bons += 1
        else:
            details.append((round(t[k], 3), round(float(frac), 2), round(float(r), 2)))
    part = bons / (len(t) - 1)
    ok("N16 soulèvement et érosion simultanés aux mêmes endroits sur ≥ 80 % des états",
       part >= 0.8, f"{100*part:.0f} % ; premiers écarts : {details[:3]}")

    # N16 : bilan de masse publié cohérent (états sans raccourcissement)
    adv = np.array(meta["raccourcissement_mm_an"], float)
    ecarts = []
    for k in range(1, len(t)):
        if adv[k] > 0:
            continue
        dt = (t[k] - t[k - 1]) * 1e6
        dhdt = (H[k] - H[k - 1]) / dt * 1e3                     # mm/an
        bilan = taux(U8[k], meta) - taux(E8[k], meta)
        ecarts.append(np.abs(dhdt - bilan).mean() / max(np.abs(bilan).mean(), 1e-3))
    ok("N16 relief publié = soulèvement − érosion publiés (écart relatif moyen < 25 %)",
       len(ecarts) > 0 and np.median(ecarts) < 0.25,
       f"médiane {np.median(ecarts):.2f} sur {len(ecarts)} états" if ecarts else "aucun état")

    # N23 : la fin est le relief réel
    ecart = np.abs(H[-1] - reel).mean()
    ok("N23 dernier état à moins de 50 m (moyenne) du relief réel",
       ecart < 50, f"{ecart:.1f} m (écart-type {np.std(H[-1]-reel):.0f} m)")

    # N23 : on reconnaît les massifs (lieux en km depuis Grenoble, est/nord)
    g = H[-1].reshape(n, n)
    def zone(x0, x1, y0, y1):
        c = (np.arange(n) + 0.5) * meta["pas_m"] / 1e3 - meta["taille_km"] / 2
        ix = (c >= x0) & (c <= x1); iy = (-c >= y0) & (-c <= y1)
        return g[np.ix_(iy, ix)]
    bel = zone(15, 30, -5, 15).max()          # Grand Pic de Belledonne ~ (21, 0)
    gres = np.percentile(zone(3, 25, 5, 30), 5)  # fond du Grésivaudan
    cha = zone(-5, 10, 10, 30).max()          # Chamechaude, Dent de Crolles
    ver = zone(-25, -5, -40, -5).max()        # Grand Veymont, Moucherotte
    ok("N23 Belledonne > 2 600 m, Chartreuse et Vercors > 1 700 m, Grésivaudan < 400 m",
       bel > 2600 and cha > 1700 and ver > 1700 and gres < 400,
       f"Belledonne {bel:.0f}, Chartreuse {cha:.0f}, Vercors {ver:.0f}, Grésivaudan {gres:.0f} m")

    # N17 : machine à laver — roches profondes au jour là où l'érosion a travaillé
    xf = X8[-1].astype(float)
    ok("N17 roches profondes affleurant dans les massifs cristallins (Belledonne)",
       np.median(zone_x(xf, meta, 15, 30, -5, 15)) > np.median(zone_x(xf, meta, -60, -40, -20, 20)) + 40,
       f"indice Belledonne {np.median(zone_x(xf, meta, 15, 30, -5, 15)):.0f}, avant-pays {np.median(zone_x(xf, meta, -60, -40, -20, 20)):.0f}")
    return meta


def zone_x(xf, meta, x0, x1, y0, y1):
    n = meta["n"]
    g = xf.reshape(n, n)
    c = (np.arange(n) + 0.5) * meta["pas_m"] / 1e3 - meta["taille_km"] / 2
    ix = (c >= x0) & (c <= x1); iy = (-c >= y0) & (-c <= y1)
    return g[np.ix_(iy, ix)]


# ---------------------------------------------------------------- page
def controles_page(base):
    print("Page", flush=True)
    from playwright.sync_api import sync_playwright
    erreurs = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                 args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                       "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        page = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        page.goto(base, wait_until="load")
        try:
            page.wait_for_function("window.ALPES && window.ALPES.pret", timeout=120000)
            pret = True
        except Exception:
            pret = False
        ok("P1 page prête (paquet chargé, WebGL2)", pret)
        if pret:
            # Vitesse réelle de la barre : temps géologique écoulé par seconde de lecture
            mesures = {}
            for t0 in (-20, -1.9, -1.2, -0.6, -0.2):
                v = page.evaluate("""async (t0) => {
                    const A = window.ALPES; A.vitesse(1); A.aller(t0); A.lire();
                    await new Promise(r => setTimeout(r, 200));
                    const a = A.temps(), ta = performance.now();
                    await new Promise(r => setTimeout(r, 1500));
                    const b = A.temps(), tb = performance.now(); A.pause();
                    return (b - a) / ((tb - ta) / 1000);
                }""", t0)
                mesures[t0] = v
            r = [mesures[k] for k in (-1.9, -1.2, -0.6, -0.2)]
            ok("N23 la barre ralentit : vitesse décroissante sur les 2 derniers Ma",
               all(r[i] > r[i + 1] > 0 for i in range(3)) and mesures[-20] > 3 * r[0],
               " ; ".join(f"{k} Ma : {v*1000:.0f} ka/s" for k, v in mesures.items()))

            page.evaluate("window.ALPES.aller(0)")
            page.wait_for_timeout(600)
            vis = page.evaluate("""() => ['Belledonne','Chartreuse','Vercors','Grésivaudan'].map(n =>
                [...document.querySelectorAll('.lieu')].some(e => e.textContent.includes(n)
                 && getComputedStyle(e).opacity > 0.5 && e.getBoundingClientRect().width > 0))""")
            page.evaluate("window.ALPES.aller(-30)")
            page.wait_for_timeout(600)
            cache = page.evaluate("""() => [...document.querySelectorAll('.lieu')].every(e =>
                getComputedStyle(e).opacity < 0.2)""")
            ok("N23 noms des massifs visibles à la fin, absents à −30 Ma", all(vis) and cache,
               f"fin {vis}, −30 Ma masqués {cache}")

            page.evaluate("window.ALPES.aller(0)")
            page.wait_for_timeout(500)
            stats = page.evaluate("""() => {
                const c = document.querySelector('canvas'); const g = c.getContext('webgl2');
                const w = g.drawingBufferWidth, h = g.drawingBufferHeight;
                window.ALPES.dessiner(); const px = new Uint8Array(w*h*4);
                g.readPixels(0,0,w,h,g.RGBA,g.UNSIGNED_BYTE,px);
                let s=0,s2=0,n=0; for(let i=0;i<px.length;i+=16){const v=px[i]+px[i+1]+px[i+2]; s+=v; s2+=v*v; n++;}
                const m=s/n; return [m, Math.sqrt(s2/n-m*m)];
            }""")
            ok("P2 relief rendu (image non vide, contrastée)", stats[1] > 25, f"moyenne {stats[0]:.0f}, écart-type {stats[1]:.0f}")

            # glisser au doigt : la vue tourne
            avant = page.evaluate("window.ALPES.camera().azimut")
            page.mouse.move(200, 420); page.mouse.down(); page.mouse.move(300, 430, steps=8); page.mouse.up()
            apres = page.evaluate("window.ALPES.camera().azimut")
            ok("P3 glisser fait tourner la vue", abs(apres - avant) > 0.05, f"{avant:.2f} → {apres:.2f} rad")

            ims = page.evaluate("""async () => { const A = window.ALPES; A.aller(-44); A.vitesse(4); A.lire();
                const t0 = performance.now(); let n = 0;
                await new Promise(r => { const f = () => { n++; if (performance.now() - t0 < 3000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); });
                A.pause(); return n / 3; }""")
            print(f"       (images par seconde en rendu logiciel : {ims:.0f})")
        ok("P4 aucune erreur JavaScript", not erreurs, "; ".join(erreurs[:3]))
        nav.close()


def main():
    srv, base = servir()
    print("Servi :", base, flush=True)
    meta = controles_donnees(base)
    controles_page(base)
    srv.shutdown()
    n_ok = sum(r[1] for r in resultats)
    print(f"\n{n_ok}/{len(resultats)} contrôles passés")
    sys.exit(0 if n_ok == len(resultats) else 1)


if __name__ == "__main__":
    main()
