#!/usr/bin/env python3
"""Contrôles du compteur de vitesse du temps (N28), mesurés sur la page servie.

Lance : python3 app/public/labo/compteur/controles.py
Sert app/public sur un port libre entre 8850 et 8859, ouvre la page de démonstration
dans Chrome sans écran (Playwright), mesure la géométrie réellement dessinée.

Échelle attendue (indépendante du code du compteur) : angle compté depuis la verticale,
positif dans le sens horaire ; 1 an/s à -135°, 10 Ga/s à +135°, logarithmique
(27° par décade) ; butée à -146° quand le temps est arrêté.
"""
import functools
import http.server
import math
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parents[2]  # app/public
CHROME = "/usr/bin/google-chrome"
A0, A1, BUTEE = -135.0, 135.0, -146.0
TOL = 1.0

resultats = []


def note(nom, ok, detail=""):
    resultats.append((nom, bool(ok), detail))
    print(("  OK   " if ok else "  ÉCHEC ") + nom + (f" — {detail}" if detail else ""), flush=True)


def angle_attendu(v):
    lv = min(10.0, max(0.0, math.log10(v)))
    return A0 + (A1 - A0) * lv / 10.0


def port_libre():
    for p in range(8850, 8860):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("aucun port libre entre 8850 et 8859")


def servir():
    port = port_libre()
    class Discret(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Discret, directory=str(RACINE))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


MESURE_JS = """() => {
  const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return {x: b.x + b.width / 2, y: b.y + b.height / 2}; };
  const m = r('.compteur-temps .moyeu'), p = r('.compteur-temps .pointe');
  if (!m || !p) return null;
  return Math.atan2(p.x - m.x, -(p.y - m.y)) * 180 / Math.PI;
}"""


def angle(page):
    return page.evaluate(MESURE_JS)


def attendre_repos(page, cible, delai=4.0):
    """Attend que l'aiguille cesse de bouger (amortissement fini), renvoie l'angle mesuré."""
    page.wait_for_timeout(300)
    prec, t = angle(page), 0.0
    while t < delai:
        page.wait_for_timeout(150)
        t += 0.15
        a = angle(page)
        if a is not None and prec is not None and abs(a - prec) < 0.02:
            return a
        prec = a
    return angle(page)


def texte(page, sel):
    return page.evaluate(f"() => {{ const e = document.querySelector('{sel}'); return e ? e.textContent.replace(/[\\u00a0\\u202f]/g, ' ').trim() : null; }}")


def main():
    srv, port = servir()
    base = f"http://127.0.0.1:{port}/labo/compteur/"
    erreurs = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"], headless=True)

        # ---------- Bureau, mode essai (vitesses imposées) ----------
        page = nav.new_page(viewport={"width": 1280, "height": 800})
        page.on("pageerror", lambda e: erreurs.append(f"pageerror: {e}"))
        page.on("console", lambda m: erreurs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.goto(base + "?essai=1")
        page.wait_for_function("() => window.compteur && document.querySelector('.compteur-temps .pointe')", timeout=10000)

        note("composant chargé depuis app/public/commun/compteur.js",
             page.evaluate("() => [...performance.getEntriesByType('resource')].some(r => r.name.endsWith('/commun/compteur.js'))"))

        # Angles de l'aiguille, après amortissement, sur 8 vitesses (6 graduations + 2 intermédiaires)
        vitesses = [1, 100, 1e4, 1e6, 1e8, 1e10, 3.2e3, 4.5e7]
        ecarts = []
        for v in vitesses:
            page.evaluate(f"() => window.compteur.vitesse({v}, 1)")
            a = attendre_repos(page, angle_attendu(v))
            e = abs(a - angle_attendu(v)) if a is not None else 999
            ecarts.append(e)
            note(f"aiguille à {v:g} an/s : {a:.2f}° pour {angle_attendu(v):.2f}° attendus", e <= TOL, f"écart {e:.2f}°")
        note("au moins 6 vitesses à 1° près", sum(e <= TOL for e in ecarts) >= 6 and max(ecarts) <= TOL)

        # Les graduations dessinées sont à l'angle de leur vitesse (l'aiguille pointe le bon chiffre)
        grad = page.evaluate("""() => { const m = document.querySelector('.compteur-temps .moyeu').getBoundingClientRect();
          const cx = m.x + m.width / 2, cy = m.y + m.height / 2;
          return [...document.querySelectorAll('.compteur-temps .grad-majeure')].map(e => { const b = e.getBoundingClientRect();
            return {v: +e.dataset.vitesse, a: Math.atan2(b.x + b.width / 2 - cx, -(b.y + b.height / 2 - cy)) * 180 / Math.PI}; }); }""")
        vus = sorted(g["v"] for g in grad)
        note("6 graduations majeures : 1 an, 100 ans, 10 000 ans, 1 Ma, 100 Ma, 10 Ga",
             vus == [1, 100, 1e4, 1e6, 1e8, 1e10], str(vus))
        pire = max((abs(g["a"] - angle_attendu(g["v"])) for g in grad), default=999)
        note("graduations à leur angle logarithmique", pire <= 0.5, f"écart max {pire:.2f}°")

        etiq = [texte(page, f'.compteur-temps .etiquette[data-vitesse="{int(v)}"]') for v in (1, 100, 1e4, 1e6, 1e8, 1e10)]
        note("étiquettes des graduations", etiq == ["1 an", "100 ans", "10 000 ans", "1 Ma", "100 Ma", "10 Ga"], str(etiq))

        # Lecture en clair
        cas = [(1, "1 an par seconde"), (100, "100 ans par seconde"), (1e4, "10 000 ans par seconde"),
               (1e6, "1 million d'années par seconde"), (2.5e6, "2,5 millions d'années par seconde"),
               (1e8, "100 millions d'années par seconde"), (1e10, "10 milliards d'années par seconde")]
        for v, attendu in cas:
            page.evaluate(f"() => window.compteur.vitesse({v}, 1)")
            page.wait_for_timeout(60)
            lu = texte(page, ".compteur-temps .lecture")
            note(f"lecture « {attendu} »", lu == attendu, f"lu « {lu} »")

        # Butée à l'arrêt
        page.evaluate("() => window.compteur.vitesse(0, 0)")
        a = attendre_repos(page, BUTEE)
        note(f"butée à l'arrêt : {a:.2f}° pour {BUTEE}°", abs(a - BUTEE) <= TOL)
        lu = texte(page, ".compteur-temps .lecture")
        note("lecture « temps arrêté »", lu == "temps arrêté", f"lu « {lu} »")
        b = page.evaluate("""() => { const m = document.querySelector('.compteur-temps .moyeu').getBoundingClientRect();
          const e = document.querySelector('.compteur-temps .butee').getBoundingClientRect();
          return Math.atan2(e.x + e.width / 2 - m.x - m.width / 2, -(e.y + e.height / 2 - m.y - m.height / 2)) * 180 / Math.PI; }""")
        note("taquet de butée dessiné juste au-delà de 1 an", BUTEE - 6 <= b <= BUTEE, f"{b:.1f}°")

        # Sens : flèche quand le temps remonte
        op = "() => +getComputedStyle(document.querySelector('.compteur-temps .fleche-sens')).opacity"
        page.evaluate("() => window.compteur.vitesse(1e4, -1)")
        page.wait_for_timeout(700)
        o_rebours = page.evaluate(op)
        lu_reb = texte(page, ".compteur-temps .sens")
        page.evaluate("() => window.compteur.vitesse(1e4, 1)")
        page.wait_for_timeout(700)
        o_avant = page.evaluate(op)
        note("flèche de sens allumée quand le temps remonte", o_rebours >= 0.8, f"opacité {o_rebours:.2f}")
        note("flèche éteinte quand le temps avance", o_avant <= 0.05, f"opacité {o_avant:.2f}")
        note("mention « le temps remonte »", lu_reb == "le temps remonte", f"lu « {lu_reb} »")

        # Amortissement : l'aiguille ne saute pas, elle rejoint la cible en moins de 2 s
        page.evaluate("() => window.compteur.vitesse(1, 1)")
        attendre_repos(page, A0)
        page.evaluate("() => window.compteur.vitesse(1e10, 1)")
        page.wait_for_timeout(40)
        a40 = angle(page)
        page.wait_for_timeout(1960)
        a2000 = angle(page)
        note("aiguille amortie : à 40 ms elle est encore en chemin", A0 + 1 < a40 < A1 - 20, f"{a40:.1f}°")
        note("aiguille arrivée à 1° près en 2 s", abs(a2000 - A1) <= TOL, f"{a2000:.2f}°")
        anime = page.evaluate("() => window.compteur.etat().anime")
        note("au repos, plus d'animation (économe)", anime is False)

        # Destruction
        page.evaluate("() => window.compteur.detruit()")
        page.wait_for_timeout(100)
        note("detruit() retire le cadran", page.evaluate("() => document.querySelectorAll('.compteur-temps').length") == 0)
        page.close()

        # ---------- Téléphone 390 × 844, démonstration en marche ----------
        tel = nav.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        tel.on("pageerror", lambda e: erreurs.append(f"pageerror (tél.): {e}"))
        tel.on("console", lambda m: erreurs.append(f"console.{m.type} (tél.): {m.text}") if m.type == "error" else None)
        tel.goto(base)
        tel.wait_for_function("() => window.compteur && document.querySelector('.compteur-temps .pointe')", timeout=10000)
        tel.wait_for_timeout(2500)
        geo = tel.evaluate("""() => {
          const b = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
          const c = document.querySelector('.compteur-temps');
          const ets = [...c.querySelectorAll('.etiquette')].map(b);
          const tailles = [...c.querySelectorAll('.etiquette, .unite, .lecture, .sens')].map(e => parseFloat(getComputedStyle(e).fontSize) * (e.ownerSVGElement ? e.ownerSVGElement.getScreenCTM().a : 1));
          const lecture = c.querySelector('.lecture');
          const scene = document.querySelector('#scene');
          return {cadre: b(c), lecture: b(lecture), etiquettes: ets, tailles, scene: scene ? b(scene) : null,
                  vw: innerWidth, vh: innerHeight, police: getComputedStyle(c.querySelector('.etiquette')).fontFamily,
                  cinzel: document.fonts.check('600 12px Cinzel')};
        }""")
        x0, y0, x1, y1 = geo["cadre"]
        note("cadran entièrement dans l'écran 390 × 844", x0 >= 0 and y0 >= 0 and x1 <= geo["vw"] and y1 <= geo["vh"], str([round(v) for v in geo["cadre"]]))
        lx0, ly0, lx1, ly1 = geo["lecture"]
        note("lecture en clair dans l'écran", lx0 >= 0 and lx1 <= geo["vw"] and ly1 <= geo["vh"], str([round(v) for v in geo["lecture"]]))
        larg = x1 - x0
        note("cadran discret : ≤ 36 % de la largeur", larg <= 0.36 * geo["vw"], f"{larg:.0f} px")
        note("chiffres lisibles : ≥ 8 px", min(geo["tailles"]) >= 8, f"min {min(geo['tailles']):.1f} px")
        ets = geo["etiquettes"]
        chev = [(i, j) for i in range(len(ets)) for j in range(i + 1, len(ets))
                if not (ets[i][2] <= ets[j][0] or ets[j][2] <= ets[i][0] or ets[i][3] <= ets[j][1] or ets[j][3] <= ets[i][1])]
        note("aucune étiquette ne chevauche une autre", not chev, str(chev))
        note("police Cinzel chargée pour les chiffres", geo["cinzel"] and "Cinzel" in geo["police"], geo["police"])
        if geo["scene"]:
            s = geo["scene"]
            inter = not (x1 <= s[0] or s[2] <= x0 or y1 <= s[1] or s[3] <= y0)
            note("le cadran ne masque pas l'objet de la scène", not inter)
        else:
            note("le cadran ne masque pas l'objet de la scène", False, "pas d'élément #scene")

        # La démonstration accélère puis ralentit : l'aiguille balaie toute l'échelle
        mini, maxi = 999, -999
        for _ in range(48):
            tel.wait_for_timeout(500)
            a = angle(tel)
            mini, maxi = min(mini, a), max(maxi, a)
        note("démonstration : l'aiguille parcourt l'échelle (1 an → 10 Ga/s → retour)", mini <= A0 + 10 and maxi >= A1 - 10, f"{mini:.0f}° → {maxi:.0f}°")
        tel.close()
        nav.close()
    srv.shutdown()

    note("aucune erreur JavaScript", not erreurs, "; ".join(erreurs[:5]))
    n_ok = sum(ok for _, ok, _ in resultats)
    print(f"\n{n_ok}/{len(resultats)} contrôles passés")
    return 0 if n_ok == len(resultats) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # page absente ou cassée : c'est un échec, pas un plantage
        note("page de démonstration chargée et mesurable", False, str(e).splitlines()[0])
        print(f"\n{sum(ok for _, ok, _ in resultats)}/{len(resultats)} contrôles passés")
        sys.exit(1)
