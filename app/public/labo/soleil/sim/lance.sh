#!/usr/bin/env bash
# Effondrement d'un cœur de nuage en rotation avec Phantom (SPH, Price et al. 2018).
# Lance ou reprend une simulation dans le dossier $RUN, puis extrait les sorties.
#
#   RUN=run EXTRAIT=extrait BETA=0.01 NP=100000 TWALL=005:15 PHANTOM=bin bash lance.sh
#
# Les sorties complètes (≈ 12 Mo chacune, plus d'un millier) ne tiennent pas sur le disque
# d'une machine GitHub (constaté le 23/11 : étape 1 en échec après 5 h). Elles sont donc
# extraites au fil de l'eau puis effacées ; seule la dernière est gardée pour la reprise.
#
# Le cœur : sphère de Bonnor-Ebert de 1,2 M☉ et 0,15 année-lumière de rayon (0,3 al de
# diamètre), gaz moléculaire à 10 K (c_s = 0,189 km/s, μ = 2,31). À 10 K une sphère
# critique de 1 M☉ a justement ≈ 0,16 al de rayon : 1,2 M☉ dans 0,15 al la rend
# légèrement sur-critique (facteur ≈ 1,3), donc elle s'effondre. Rotation solide de
# rapport β = E_rot/|E_grav| = $BETA. Équation d'état barotrope (Phantom ieos=8) ;
# particule-puits (étoile) créée au-delà de 1e-10 g/cm³, rayon d'accrétion 10 UA.
set -euo pipefail
ICI="$(cd "$(dirname "$0")" && pwd)"
: "${RUN:?}" "${EXTRAIT:?}" "${BETA:?}" "${NP:=100000}" "${TWALL:=005:15}" "${PHANTOM:?}"
mkdir -p "$RUN"; cd "$RUN"

if [ ! -f soleil.in ]; then
  sed -e "s/@NP@/${NP}/" -e "s/@BETA@/${BETA}/" "$ICI/soleil.setup" > soleil.setup
  "$PHANTOM/phantomsetup" soleil < /dev/null | tee setup.log
  [ -f soleil.in ] || "$PHANTOM/phantomsetup" soleil < /dev/null | tee -a setup.log
  # unités de code : 1e16 cm, 1 M☉ → temps 8,68e10 s = 2 751 ans
  # tmax 200 (≈ 550 000 ans), une sortie toutes les 0,3 (≈ 825 ans), resserrées à
  # l'approche de l'effondrement (dtmax_dratio) jusqu'à 0,3/16
  python3 - <<'EOF'
import re
s = open("soleil.in").read()
def mets(cle, val):
    global s
    s, n = re.subn(rf"(?m)^(\s*{cle}\s*=\s*)\S+", rf"\g<1>{val}", s)
    if n == 0:
        raise SystemExit(f"option absente du .in : {cle}")
mets("tmax", "200.")
mets("dtmax", "0.3")
mets("dtmax_min", "0.01875")
mets("nfulldump", "1")
mets("icreate_sinks", "1")
open("soleil.in", "w").write(s)
EOF
fi

# reprise : partir de la dernière sortie complète
dernier=$(ls soleil_[0-9][0-9][0-9][0-9][0-9] 2>/dev/null | sort | tail -1 || true)
if [ -n "$dernier" ]; then
  sed -i -E "s/^( *dumpfile *= *)\S+/\1${dernier}/" soleil.in
fi
sed -i -E "s/^( *twallmax *= *)\S+/\1${TWALL}/" soleil.in
grep -E "^ *(dumpfile|tmax|dtmax|twallmax|ieos|icreate_sinks|h_acc|r_crit|rho_crit_cgs) *=" soleil.in

export OMP_NUM_THREADS=${OMP:-$(nproc)}
ulimit -s unlimited || true
JOURNAL="phantom_$(date +%s).log"
"$PHANTOM/phantom" soleil.in > "$JOURNAL" 2>&1 &
pid=$!
while kill -0 $pid 2>/dev/null; do
  sleep 90
  python3 "$ICI/extraire.py" . "$EXTRAIT" --nettoie --sauf-plus-recente >> "$EXTRAIT/../extraction.log" 2>&1 || echo "extraction en échec (voir extraction.log)"
done
wait $pid || echo "phantom s'est arrêté (code $?)"
python3 "$ICI/extraire.py" . "$EXTRAIT" --nettoie >> "$EXTRAIT/../extraction.log" 2>&1 || echo "extraction finale en échec"
tail -3 "$EXTRAIT/../extraction.log"
tail -25 "$JOURNAL" | tee "$EXTRAIT/../fin_phantom.txt"
df -h . | tail -1
