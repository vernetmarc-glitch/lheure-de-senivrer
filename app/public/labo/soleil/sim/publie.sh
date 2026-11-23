#!/usr/bin/env bash
# Assemble les données de la page à partir des variantes de l'étape $1 et les dépose
# sur la branche (si au moins une variante a formé son étoile).
set -uo pipefail
ETAPE="$1"
SIM=app/public/labo/soleil/sim
DON=app/public/labo/soleil/donnees
ls var || exit 0
python3 - <<'EOF' > resume.txt
import glob, json, os
for d in sorted(glob.glob("var/*")):
    try:
        b = [json.loads(l) for l in open(f"{d}/extrait/bilan.jsonl")]
    except OSError:
        print(f"{d} : pas de bilan"); continue
    nais = next((x["t_an"] for x in b if x["puits"]), None)
    der = b[-1]
    print(f"{os.path.basename(d)} : {len(b)} sorties, t = {der['t_an']:.0f} ans, naissance {nais}, "
          f"{len(der['puits'])} puits {[round(p['m'], 3) for p in der['puits']]}, rho_max {der['rho_max_cgs']:.2e}, "
          f"fini {os.path.exists(d + '/fini')}")
EOF
cat resume.txt
rm -rf nouv && mkdir nouv
if ! PHANTOM_SHA=$PHANTOM_SHA python3 $SIM/assembler.py --trajectoire traj/BHAC15_brut.txt --sortie nouv var/*; then
  echo "rien à publier à l'étape $ETAPE"; exit 0
fi
cp resume.txt nouv/variantes.txt
cp traj/source.txt nouv/source_trajectoire.txt 2>/dev/null || true
git config user.name "chantier-soleil (workflow)"
git config user.email "noreply@github.com"
for essai in 1 2 3 4 5; do
  git fetch -q origin chantier/soleil && git reset -q --hard origin/chantier/soleil
  rm -rf "$DON" && mkdir -p "$DON" && cp nouv/* "$DON"/
  git add -A "$DON"
  git diff --cached --quiet && { echo "rien de neuf"; exit 0; }
  git commit -q -m "Soleil : données de l'effondrement, étape $ETAPE ($(head -c 120 resume.txt | tr '\n' ' '))"
  git push -q origin HEAD:chantier/soleil && { echo "déposé"; exit 0; }
  sleep $((essai * 7))
done
exit 1
