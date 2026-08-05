// NodeInspector.jsx — slide-out metadata panel with grouped sections and edge details
import axios from 'axios'
import { useState, useEffect } from 'react'

export default function NodeInspector({ nodeId, onClose, onExpand }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!nodeId) return
    setLoading(true)
    axios.get(`/api/graph/node/${encodeURIComponent(nodeId)}`)
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [nodeId])

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (!nodeId) return null

  return (
    <div className="inspector-overlay">
      <div className="inspector-header">
        <span className="inspector-title">
          {data ? `${data.icon || '⬡'} ${data.label}` : 'Loading…'}
        </span>
        <button className="inspector-close" onClick={onClose} title="Close (Esc)">×</button>
      </div>

      {loading && (
        <div style={{ padding: 24, display: 'flex', justifyContent: 'center' }}>
          <div className="spinner" style={{ width: 24, height: 24, borderWidth: 2 }} />
        </div>
      )}

      {data && (() => {
        const metaEntries = Object.entries(data.meta || {})
        const displayEntries = metaEntries.slice(0, 12)
        const inEdges = data.in_edges || []
        const outEdges = data.out_edges || []

        return (
          <div className="inspector-body">
            {/* Properties section */}
            <div className="inspector-section">
              <div className="inspector-section-title">Properties</div>
              <div className="meta-list">
                <div className="meta-row">
                  <span className="meta-key">Entity:</span>
                  <span className="meta-value-badge" style={{ color: data.color }}>{data.node_type}</span>
                </div>
                
                {displayEntries.map(([k, v]) => (
                  <div key={k} className="meta-row">
                    <span className="meta-key">{k}:</span> {v === null || v === 'None' || v === '' ? '—' : String(v)}
                  </div>
                ))}

                {metaEntries.length > 12 && (
                  <div className="meta-hidden-text">
                    +{metaEntries.length - 12} more fields
                  </div>
                )}
              </div>
            </div>

            {/* Incoming edges */}
            {inEdges.length > 0 && (
              <div className="inspector-section">
                <div className="inspector-section-title">
                  Incoming <span className="inspector-count">{inEdges.length}</span>
                </div>
                <div className="inspector-edge-list">
                  {inEdges.map((edge, i) => (
                    <div key={i} className="inspector-edge-item">
                      <span className="inspector-edge-label">{edge.label || '—'}</span>
                      <span className="inspector-edge-id" title={edge.source}>← {edge.source}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Outgoing edges */}
            {outEdges.length > 0 && (
              <div className="inspector-section">
                <div className="inspector-section-title">
                  Outgoing <span className="inspector-count">{outEdges.length}</span>
                </div>
                <div className="inspector-edge-list">
                  {outEdges.map((edge, i) => (
                    <div key={i} className="inspector-edge-item">
                      <span className="inspector-edge-label">{edge.label || '—'}</span>
                      <span className="inspector-edge-id" title={edge.target}>→ {edge.target}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="inspector-actions">
              <button
                className="inspector-action-btn"
                onClick={() => onExpand && onExpand({ nodeId })}
              >
                ⊕ Expand from here
              </button>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
