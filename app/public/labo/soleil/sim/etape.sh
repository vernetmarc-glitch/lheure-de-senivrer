#!/usr/bin/env bash
# Une étape (≤ 6 h) de la chaîne de simulation, sur une machine GitHub.
#   ETAT=dossier BETA=0.01 PHANTOM=bin bash etape.sh
# Le dossier $ETAT contient run/ (dernière sortie complète, .in, journaux) et extrait/
# (sorties compactes). Il passe d'une étape à la suivante comme artefact.
set -euo pipefail
ICI="$(cd "$(dirname "$0")" && pwd)"
: "${ETAT:?}" "${BETA:?}" "${PHANTOM:?}" "${NP:=100000}" "${TWALL:=005:05}"
mkdir -p "$ETAT/run" "$ETAT/extrait"

if [ -f "$ETAT/fini" ]; then
  echo "simulation déjà terminée : $(cat "$ETAT/fini")"; exit 0
fi

RUN="$ETAT/run" EXTRAIT="$ETAT/extrait" BETA="$BETA" NP="$NP" TWALL="$TWALL" PHANTOM="$PHANTOM" bash "$ICI/lance.sh"

# ne garder que la dernière sortie complète (pour la reprise)
dernier=$(ls "$ETAT"/run/soleil_[0-9][0-9][0-9][0-9][0-9] | sort | tail -1)
for f in "$ETAT"/run/soleil_[0-9][0-9][0-9][0-9][0-9]; do
  [ "$f" = "$dernier" ] || rm -f "$f"
done
rm -f "$ETAT"/run/*.tmp

# terminé si tmax atteint, ou 150 000 ans après la naissance de l'étoile
python3 - "$ETAT" <<'EOF'
import json, sys
d = sys.argv[1]
b = [json.loads(l) for l in open(f"{d}/extrait/bilan.jsonl")]
t = b[-1]["t_an"]
nais = next((x["t_an"] for x in b if x["puits"]), None)
fin = t >= 0.999 * 200 * 2750.9 or (nais is not None and t >= nais + 1.5e5)
print(f"t = {t:.0f} ans ; naissance : {nais} ; terminé : {fin}")
if fin:
    open(f"{d}/fini", "w").write(f"t = {t:.0f} ans, naissance {nais}\n")
EOF
du -sh "$ETAT"
