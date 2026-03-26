// App.jsx — Root layout
import { useState, useEffect, createContext } from 'react'
import axios from 'axios'
import GraphCanvas from './GraphCanvas'
import ChatPanel from './ChatPanel'

export const HighlightContext = createContext(new Set())

export default function App() {
  const [stats, setStats] = useState({ nodes: '…', edges: '…', status: 'checking' })
  const [highlightIds, setHighlightIds] = useState(new Set())

  useEffect(() => {
    axios.get('/api/health')
      .then(r => setStats({ nodes: r.data.nodes, edges: r.data.edges, status: 'ok' }))
      .catch(() => setStats(s => ({ ...s, status: 'error' })))
  }, [])

  return (
    <HighlightContext.Provider value={highlightIds}>
    <div className="app-shell">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
            {/* <div className="header-logo-icon">🕸</div> */}
            <span className="header-title">Dodge Graph</span>
          <span className="header-subtitle">Business Intelligence Explorer</span>
        </div>

        <div className="header-stats">
          <div className="stat-badge">
            Nodes <span>{stats.nodes}</span>
          </div>
          <div className="stat-badge">
            Edges <span>{stats.edges}</span>
          </div>
          <div className="stat-badge">
            API&nbsp;
            <span style={{ color: stats.status === 'ok' ? '#22c55e' : '#ef4444' }}>
              {stats.status === 'ok' ? '● Live' : '● Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Main */}
      <div className="main-layout">
        <GraphCanvas />
          <ChatPanel onHighlightsChange={setHighlightIds} />
      </div>
    </div>
    </HighlightContext.Provider>
  )
}
