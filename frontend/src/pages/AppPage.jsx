// AppPage.jsx — The graph explorer with collapsible chat panel
import { useState, useEffect, useCallback, createContext } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import GraphCanvas from '../GraphCanvas'
import ChatPanel from '../ChatPanel'

export const HighlightContext = createContext(new Set())

export default function AppPage() {
  const [stats, setStats] = useState({ nodes: '…', edges: '…', status: 'checking' })
  const [highlightIds, setHighlightIds] = useState(new Set())
  const [chatOpen, setChatOpen] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/health')
      .then(r => setStats({ nodes: r.data.nodes, edges: r.data.edges, status: 'ok' }))
      .catch(() => setStats(s => ({ ...s, status: 'error' })))
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') {
        // Let graph canvas handle its own inspector close
      }
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        // Focus chat input
        const chatInput = document.getElementById('chat-input')
        if (chatInput && document.activeElement !== chatInput) {
          e.preventDefault()
          chatInput.focus()
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const toggleChat = useCallback(() => setChatOpen(o => !o), [])

  return (
    <HighlightContext.Provider value={highlightIds}>
    <div className="app-shell">
      {/* Header */}
      <header className="header">
        <div className="header-logo" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            <span className="header-title">Nexora</span>
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
          <button
            className="header-chat-toggle"
            onClick={toggleChat}
            title={chatOpen ? 'Collapse chat (/)' : 'Open chat (/)'}
          >
            {chatOpen ? '◧ Hide Chat' : '◨ Show Chat'}
          </button>
          <button className="header-upload-btn" onClick={() => navigate('/upload')}>
            ↑ Upload Data
          </button>
        </div>
      </header>

      {/* Main */}
      <div className={`main-layout${chatOpen ? '' : ' chat-collapsed'}`}>
        <GraphCanvas />
        <div className={`chat-panel-wrapper${chatOpen ? '' : ' collapsed'}`}>
          {chatOpen && <ChatPanel onHighlightsChange={setHighlightIds} />}
        </div>
      </div>
    </div>
    </HighlightContext.Provider>
  )
}
