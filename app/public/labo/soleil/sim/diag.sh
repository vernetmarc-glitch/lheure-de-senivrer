#!/usr/bin/env bash
# Toujours exécuté en fin de tâche de simulation (réussie ou non) : dépose sur la branche
# un diagnostic lisible sans compte, puis allège l'état (ne garde que la dernière sortie
# complète) pour que l'artefact reste petit.   bash diag.sh ETAT NOM
ETAT="$1"; NOM="$2"
DIAG=app/public/labo/soleil/diagnostic
mkdir -p /tmp/diag
F=/tmp/diag/$NOM.txt
{
  echo "$NOM — $(date -u)"
  df -h . | tail -1
  echo "sorties complètes : $(ls "$ETAT"/run/soleil_[0-9][0-9][0-9][0-9][0-9] 2>/dev/null | wc -l) ; instants extraits : $(ls "$ETAT"/extrait/instant_*.npz 2>/dev/null | wc -l)"
  du -sh "$ETAT"/run "$ETAT"/extrait 2>/dev/null
  echo "== setup"; grep -E "particle numbers|Free fall|Overdensity|ERROR|error|stop" "$ETAT"/run/setup.log 2>/dev/null | head -20
  echo "== bilan (3 dernières lignes)"; tail -3 "$ETAT"/extrait/bilan.jsonl 2>/dev/null | cut -c1-300
  echo "== extraction (erreurs)"; tail -40 "$ETAT"/extraction.log 2>/dev/null
  echo "== phantom (fin du journal)"; tail -40 "$(ls -t "$ETAT"/run/phantom_*.log 2>/dev/null | head -1)" 2>/dev/null
  echo "== temps simulé"; grep "TIME =" "$(ls -t "$ETAT"/run/phantom_*.log 2>/dev/null | head -1)" 2>/dev/null | tail -2
} > "$F" 2>&1
cat "$F"
# allègement : la dernière sortie complète suffit à la reprise
dernier=$(ls "$ETAT"/run/soleil_[0-9][0-9][0-9][0-9][0-9] 2>/dev/null | sort | tail -1)
# n'effacer que les sorties déjà extraites (une extraction en échec ne doit rien perdre)
for f in "$ETAT"/run/soleil_[0-9][0-9][0-9][0-9][0-9]; do
  [ -e "$f" ] && [ "$f" != "$dernier" ] && [ -e "$ETAT/extrait/instant_${f: -5}.npz" ] && rm -f "$f"
done
rm -f "$ETAT"/run/*.tmp
git config user.name "chantier-soleil (workflow)"; git config user.email "noreply@github.com"
for essai in 1 2 3 4 5 6; do
  git fetch -q origin chantier/soleil && git reset -q --hard origin/chantier/soleil
  mkdir -p "$DIAG" && cp "$F" "$DIAG"/ && git add "$DIAG"
  git diff --cached --quiet && exit 0
  git commit -q -m "Soleil : diagnostic $NOM [skip ci]" && git push -q origin HEAD:chantier/soleil && exit 0
  sleep $((essai * 5 + RANDOM % 7))
done
