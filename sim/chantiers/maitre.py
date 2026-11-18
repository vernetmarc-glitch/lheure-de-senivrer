"""Chef de chantier : un passage = constater l'état de chaque chantier, relancer ce qui s'est arrêté,
avancer d'une étape mécanique quand c'est possible, et écrire ETAT.md.

Les étapes de développement (code de la page, contrôles) ne sont pas ici : elles sont dans PLAN.md,
et c'est l'agent réveillé périodiquement qui les fait, l'une après l'autre.
Idempotent : on peut le lancer aussi souvent qu'on veut.

Usage : python3 sim/chantiers/maitre.py
"""
import json, os, subprocess, time, datetime
import numpy as np

TNG = "/home/claude/tng"
SIM = "/home/claude/lheure-de-senivrer/sim"
ETAT = f"{SIM}/chantiers/etat.json"
journal = []


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def tourne(motif):
    # « [x]yz » : pgrep ne se trouve pas lui-même dans sa propre ligne de commande
    return bool(sh(f"pgrep -f '[{motif[0]}]{motif[1:]}'"))


def lance(cmd, log):
    env = "set -a; . /home/claude/.tng.env; set +a;"
    subprocess.run(f"{env} cd {TNG} && (setsid nohup {cmd} >> {log} 2>&1 < /dev/null &)", shell=True)


etat = json.load(open(ETAT)) if os.path.exists(ETAT) else {}

# 0. serveurs locaux des contrôles
for port, dos in ((8766, "/home/claude/demo/lumiere/v2"), (8771, "/tmp/v2g")):
    if not tourne(f"http.server {port}") and os.path.isdir(dos):
        subprocess.run(f"cd {dos} && (setsid nohup python3 -m http.server {port} > /dev/null 2>&1 < /dev/null &)", shell=True)
        journal.append(f"serveur {port} relancé")

# A. voisinage autour de la nouvelle Voie lactée (537941) : histoires des halos de sa tranche
ids = np.load(f"{TNG}/historiques537-ids.npy")
faits = sum(os.path.exists(f"{TNG}/historiques/{i}.npz") for i in ids)
A = {"halos": int(faits), "total": int(len(ids))}
if faits < len(ids):
    # les derniers halos peuvent échouer durablement : au-delà de 99,5 %, on empaquette sans eux
    if faits / len(ids) < 0.995:
        if not tourne("historiques.py historiques537"):
            lance(f"python3 {SIM}/tng/historiques.py historiques537-ids.npy historiques 32", "historiques537.log")
            journal.append("téléchargement des halos relancé")
        A["etape"] = "téléchargement"
if faits / len(ids) >= 0.995:
    paquet = f"{TNG}/historiques537.bin"
    if not os.path.exists(paquet):
        if not tourne("paquet_historiques.py"):
            garde = np.array([i for i in ids if os.path.exists(f"{TNG}/historiques/{i}.npz")])
            np.save(f"{TNG}/historiques537-garde.npy", garde)
            lance(f"python3 {SIM}/tng/paquet_historiques.py historiques537-garde.npy historiques gaz537/mpb.hdf5 redshifts.json historiques537.bin",
                  "paquet537.log")
            journal.append("empaquetage du voisinage 537941 lancé")
        A["etape"] = "empaquetage"
    else:
        A["etape"] = "paquet prêt"; A["taille_Mo"] = round(os.path.getsize(paquet) / 1e6, 1)
etat["A_voisinage_537941"] = A

# D. boîte moyenne : le calcul tourne sur GitHub ; à la fin, récupérer ses sorties (txt pour l'artefact
#    et les tests, gz pour GitHub Pages) dans les dossiers de données
D = etat.get("D_maillage_fin", {})
try:
    r = json.loads(sh("gh run list -R vernetmarc-glitch/lheure-de-senivrer --workflow fond-de-carte-moyenne.yml -L 1 --json databaseId,status,conclusion"))[0]
    D["calcul"] = f"{r['status']} {r.get('conclusion') or ''}".strip(); D["run"] = r["databaseId"]
except Exception as e:
    D["calcul"] = "inconnu"
dos = f"{SIM}/sorties-v2/sorties-v2-moyenne"
if D.get("calcul", "").startswith("completed success") and not os.path.isdir(dos):
    sh(f"cd {SIM}/.. && git pull -q --rebase origin fond-de-carte")
if os.path.isdir(dos) and not os.path.exists("/home/claude/donnees-v2/matiere2-moyenne.json"):
    sh(f"cd {SIM} && python3 recentre_v2.py {dos} /home/claude/donnees-v2-gz /home/claude/donnees-v2")
    for f in os.listdir("/home/claude/donnees-v2"):
        if "moyenne" in f:
            for t in ("/tmp/v2t", "/tmp/v2g"):
                if os.path.isdir(t) and not os.path.exists(f"{t}/{f}"): os.symlink(f"/home/claude/donnees-v2/{f}", f"{t}/{f}")
    journal.append("sorties de la boîte moyenne récupérées")
if os.path.exists("/home/claude/donnees-v2/matiere2-moyenne.json"): D["donnees"] = "prêtes"
etat["D_maillage_fin"] = D

# B, C, D : chantiers de développement (suivis dans PLAN.md ; leur état est écrit par l'agent)
for k in ("B_grande_boite_points", "C_rendu_voisinage", "D_maillage_fin"):
    etat.setdefault(k, {"etape": "à faire"})

etat["passage"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
etat["journal"] = journal
json.dump(etat, open(ETAT, "w"), ensure_ascii=False, indent=1)
lignes = [f"# État des chantiers — {etat['passage']}", ""]
for k, v in etat.items():
    if k in ("passage", "journal"): continue
    lignes.append(f"- **{k}** : " + ", ".join(f"{a} {b}" for a, b in v.items()))
if journal: lignes += ["", "Ce passage : " + " ; ".join(journal)]
open(f"{SIM}/chantiers/ETAT.md", "w").write("\n".join(lignes) + "\n")
print("\n".join(lignes))
