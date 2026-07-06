import { useEffect, useMemo, useState } from 'react'
import { ageOfUniverseGyr, interpolateAtTime, loadCosmologyTable, minAgeGyr, type CosmologyTable } from './cosmology'
import UniverseMap from './UniverseMap'

export default function App() {
  const [table, setTable] = useState<CosmologyTable | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tGyr, setTGyr] = useState(13.8)

  useEffect(() => {
    loadCosmologyTable()
      .then((t) => {
        setTable(t)
        setTGyr(ageOfUniverseGyr(t)) // curseur positionné sur "aujourd'hui" par défaut
      })
      .catch((e) => setError(String(e)))
  }, [])

  const state = useMemo(() => (table ? interpolateAtTime(table, tGyr) : null), [table, tGyr])

  if (error) {
    return <div style={{ color: '#f66', padding: 24, fontFamily: 'monospace' }}>Erreur : {error}</div>
  }
  if (!table || !state) {
    return <div style={{ color: '#ccc', padding: 24, fontFamily: 'monospace' }}>Chargement…</div>
  }

  const tMin = minAgeGyr(table)
  const tMax = ageOfUniverseGyr(table)

  return <UniverseMap cosmology={state} tGyr={tGyr} tMin={tMin} tMax={tMax} onTimeChange={setTGyr} />
}
