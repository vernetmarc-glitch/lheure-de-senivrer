interface InfoModalProps {
  title: string
  onClose: () => void
  children: React.ReactNode
}

/** Petite modale d'explication, réutilisée pour "À propos" et "Horizon des particules". */
export default function InfoModal({ title, onClose, children }: InfoModalProps) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(3,3,8,0.72)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: 480,
          maxHeight: '80vh',
          overflowY: 'auto',
          background: 'rgba(14,14,20,0.97)',
          border: '1px solid rgba(255,255,255,0.14)',
          borderRadius: 14,
          padding: '22px 24px',
          color: '#e7e2d8',
          boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
          <h2
            style={{
              margin: 0,
              fontFamily: "'Cinzel', serif",
              fontWeight: 600,
              fontSize: 19,
              letterSpacing: '0.02em',
              color: '#f2ead9',
            }}
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Fermer"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#999',
              fontSize: 20,
              cursor: 'pointer',
              lineHeight: 1,
              padding: 4,
              marginLeft: 12,
            }}
          >
            ×
          </button>
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.65, color: '#cfc9bc' }}>{children}</div>
      </div>
    </div>
  )
}
