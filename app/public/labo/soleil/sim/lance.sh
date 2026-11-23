#!/usr/bin/env bash
# Effondrement d'un cœur de nuage en rotation avec Phantom (SPH, Price et al. 2018).
# Lance ou reprend une simulation dans le dossier $RUN, puis extrait les sorties.
#
#   RUN=run BETA=0.01 NP=100000 TWALL=005:15 PHANTOM=bin bash lance.sh
#
# Le cœur : sphère de Bonnor-Ebert de 1,2 M☉ et 0,15 année-lumière de rayon (0,3 al de
# diamètre), gaz moléculaire à 10 K (c_s = 0,189 km/s, μ = 2,31). À 10 K une sphère
# critique de 1 M☉ a justement ≈ 0,16 al de rayon : 1,2 M☉ dans 0,15 al la rend
# légèrement sur-critique (facteur ≈ 1,3), donc elle s'effondre. Rotation solide de
# rapport β = E_rot/|E_grav| = $BETA. Équation d'état barotrope (Phantom ieos=8) ;
# particule-puits (étoile) créée au-delà de 1e-10 g/cm³, rayon d'accrétion 10 UA.
set -euo pipefail
ICI="$(cd "$(dirname "$0")" && pwd)"
: "${RUN:?}" "${BETA:?}" "${NP:=100000}" "${TWALL:=005:15}" "${PHANTOM:?}"
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
"$PHANTOM/phantom" soleil.in > "phantom_$(date +%s).log" 2>&1 || echo "phantom s'est arrêté (code $?)"
tail -20 "$(ls -t phantom_*.log | head -1)"
