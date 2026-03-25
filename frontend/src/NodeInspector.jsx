// NodeInspector.jsx — slide-out metadata panel for selected nodes
import axios from 'axios'
import { useState, useEffect } from 'react'

export default function NodeInspector({ nodeId, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!nodeId) return
    setLoading(true)
    axios.get(`/api/graph/node/${encodeURIComponent(nodeId)}`)
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [nodeId])

  if (!nodeId) return null

  return (
    <div className="inspector-overlay">
      <div className="inspector-header">
        <span className="inspector-title">
          {data ? `${data.icon || '⬡'} ${data.label}` : 'Loading…'}
        </span>
        <button className="inspector-close" onClick={onClose} title="Close">×</button>
      </div>

      {loading && (
        <div style={{ padding: 24, display: 'flex', justifyContent: 'center' }}>
          <div className="spinner" style={{ width: 24, height: 24, borderWidth: 2 }} />
        </div>
      )}

      {data && (() => {
        const metaEntries = Object.entries(data.meta || {})
        const displayEntries = metaEntries.slice(0, 10)
        const totalConnections = (data.in_edges?.length || 0) + (data.out_edges?.length || 0)

        return (
          <div className="inspector-body">
            <div className="meta-list">
              <div className="meta-row">
                <span className="meta-key">Entity:</span> {data.node_type}
              </div>
              
              {displayEntries.map(([k, v]) => (
                <div key={k} className="meta-row">
                  <span className="meta-key">{k}:</span> {v === null || v === 'None' || v === '' ? '' : String(v)}
                </div>
              ))}

              {metaEntries.length > 10 && (
                <div className="meta-hidden-text">
                  Additional fields hidden for readability
                </div>
              )}

              <div className="meta-row" style={{ marginTop: '8px' }}>
                <span className="meta-key">Connections:</span> {totalConnections}
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
