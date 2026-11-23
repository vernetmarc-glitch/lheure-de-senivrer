#!/usr/bin/env python3
"""Fabrique la vidéo d'essai du lecteur de texture vidéo (N27).

Une planète inventée en projection équirectangulaire 1024 × 512, dont les couleurs
changent au fil des images (océans verts puis bleus, terres nues, rouillées puis
vertes, calottes qui avancent et reculent). Ce n'est pas une donnée : c'est un banc
d'essai pour le décodage, image par image, posé en texture sur un globe.

Bande du bas (latitudes < -67,5°), qui sert aux contrôles :
  - rangée 448–479 : horodatage, 16 cases de 64 px : case 0 blanche, case 1 noire
    (repères), cases 2–11 = bits 9…0 du numéro d'image, cases 12–15 = témoins de couleur ;
  - rangée 480–511 : 8 témoins de couleur de 128 px.
Les 12 témoins sont les 12 premières plages de la mire ColorChecker (sRGB).

Codage : H.264 (High, yuv420p) et AV1 (SVT-AV1), image clé toutes les 8 images,
sans images B ; matrice BT.709, primaires BT.709, transfert sRGB, plage limitée.

  python3 app/public/labo/video/fabrique_video.py
"""
import json
import subprocess
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
L, H, N, IPS = 1024, 512, 192, 24
GOP = 8

TEMOINS = [  # ColorChecker, valeurs sRGB 8 bits usuelles
    ("peau sombre", (115, 82, 68)), ("peau claire", (194, 150, 130)), ("ciel bleu", (98, 122, 157)),
    ("feuillage", (87, 108, 67)), ("fleur bleue", (133, 128, 177)), ("vert bleuté", (103, 189, 170)),
    ("orange", (214, 126, 44)), ("bleu violacé", (80, 91, 166)), ("rouge modéré", (193, 90, 99)),
    ("violet", (94, 60, 108)), ("vert jaune", (157, 188, 64)), ("jaune orangé", (224, 163, 46)),
]


def plages():
    """Rectangles (x0, y0, x1, y1) des témoins et des cases d'horodatage."""
    cases = [(64 * k, 448, 64 * (k + 1), 480) for k in range(16)]
    tem = cases[12:16] + [(128 * k, 480, 128 * (k + 1), 512) for k in range(8)]
    return cases[:12], tem


def champ_relief():
    lon = (np.arange(L) + 0.5) / L * 2 * np.pi - np.pi
    lat = np.pi / 2 - (np.arange(H) + 0.5) / H * np.pi
    lo, la = np.meshgrid(lon, lat)
    x, y, z = np.cos(la) * np.sin(lo), np.sin(la), np.cos(la) * np.cos(lo)
    g = np.random.default_rng(1977)
    f = np.zeros_like(x)
    for k in range(28):
        d = g.normal(size=3)
        d /= np.linalg.norm(d)
        fr = 1.2 + 4.5 * g.random() ** 1.5
        f += np.sin(fr * (d[0] * x + d[1] * y + d[2] * z) + 6.28 * g.random()) / fr
    f = (f - f.mean()) / f.std()
    return f, np.degrees(la)


def melange(a, b, t):
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def image(i, f, lat):
    tau = i / (N - 1)
    terre = np.clip((f - 0.35) * 6, 0, 1)[..., None]
    rel = np.clip((f - 0.35) / 2.2, 0, 1)[..., None]
    prof = np.clip((0.35 - f) / 2.5, 0, 1)[..., None]
    # Océans : verts (fer dissous) → bleus
    ocean = melange(melange((52, 104, 70), (22, 70, 96), min(1, tau * 2)), (12, 34, 84), max(0, tau * 2 - 1))
    ocean = ocean * (1 - 0.55 * prof)
    # Terres : nues → rouillées → vertes, éclaircies en altitude
    if tau < 0.4:
        sol = melange((128, 112, 96), (156, 84, 52), tau / 0.4)
    elif tau < 0.75:
        sol = melange((156, 84, 52), (66, 104, 48), (tau - 0.4) / 0.35)
    else:
        sol = melange((66, 104, 48), (98, 118, 62), (tau - 0.75) / 0.25)
    sol = sol * (0.85 + 0.45 * rel) + 30 * rel
    img = ocean * (1 - terre) + sol * terre
    # Calottes : avancent et reculent, grand froid vers τ = 0,35
    bord = 90 - (22 + 10 * np.sin(2 * np.pi * 5 * tau) + 48 * np.exp(-((tau - 0.35) / 0.07) ** 2))
    glace = np.clip((np.abs(lat) - bord) / 3, 0, 1)[..., None]
    img = img * (1 - glace) + np.array([232, 238, 244.0]) * glace
    img = np.clip(np.rint(img), 0, 255).astype(np.uint8)
    # Bande de contrôle
    cases, tem = plages()
    bits = [255, 0] + [255 if (i >> (9 - b)) & 1 else 0 for b in range(10)]
    for (x0, y0, x1, y1), v in zip(cases, bits):
        img[y0:y1, x0:x1] = v
    for (x0, y0, x1, y1), (_, rgb) in zip(tem, TEMOINS):
        img[y0:y1, x0:x1] = rgb
    return img


def code(sortie, args):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L}x{H}", "-r", str(IPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "iec61966-2-1", "-color_range", "tv",
           *args, "-movflags", "+faststart", str(sortie)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def main():
    f, lat = champ_relief()
    h264 = code(ICI / "essai.h264.mp4", ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
                                         "-x264-params", f"keyint={GOP}:min-keyint={GOP}:scenecut=0:bframes=0:ref=1:open-gop=0"])
    av1 = code(ICI / "essai.av1.mp4", ["-c:v", "libsvtav1", "-preset", "6", "-crf", "28", "-g", str(GOP),
                                       "-svtav1-params", "pred-struct=1:irefresh-type=2:enable-overlays=0:scd=0"])
    for i in range(N):
        b = image(i, f, lat).tobytes()
        h264.stdin.write(b)
        av1.stdin.write(b)
    for p in (h264, av1):
        p.stdin.close()
        assert p.wait() == 0
    cases, tem = plages()
    (ICI / "essai.json").write_text(json.dumps({
        "largeur": L, "hauteur": H, "images": N, "images_par_seconde": IPS, "gop": GOP,
        "horodatage": {"cases": cases, "repere_blanc": 0, "repere_noir": 1, "bits": list(range(2, 12)), "nb_bits": 10},
        "temoins": [{"nom": n, "rgb": rgb, "rect": r} for (n, rgb), r in zip(TEMOINS, tem)],
        "codage": "matrice BT.709, primaires BT.709, transfert sRGB, plage limitée, yuv420p",
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
