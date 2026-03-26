// ChatPanel.jsx — Conversational query interface
import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

const SUGGESTIONS = [
  'Which products are associated with the highest number of billing documents?',
  'Trace the full flow of billing document INV001 (Sales Order → Delivery → Invoice → Payment)',
  'Which customers have the highest order value?'
]

function TypingIndicator() {
  return (
    <div className="message assistant">
      <div className="typing-indicator">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}

function SqlAccordion({ sql }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="sql-accordion">
      <button className="sql-toggle" onClick={() => setOpen(o => !o)}>
        <span>🗃</span>
        <span>SQL query</span>
        <span className={`sql-toggle-arrow${open ? ' open' : ''}`}>▶</span>
      </button>
      {open && <pre className="sql-code">{sql}</pre>}
    </div>
  )
}

function DataTable({ rows }) {
  if (!rows || rows.length === 0) return null
  const cols = Object.keys(rows[0])
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>{cols.map(c => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((row, i) => (
            <tr key={i}>
              {cols.map(c => <td key={c} title={String(row[c])}>{String(row[c] ?? '—')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ChatPanel({ onHighlightsChange }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm your business data analyst. Ask me anything about your sales orders, deliveries, invoices, and payments.",
      sql: null,
      data: [],
    }
  ])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (text) => {
    const msg = (text || input).trim()
    if (!msg || loading) return

    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setInput('')
    setLoading(true)

    try {
      const resp = await axios.post('/api/chat', { message: msg })
      const { answer, sql, data } = resp.data
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        sql,
        data: data || [],
      }])

      if (onHighlightsChange) {
        const ids = new Set()
        if (data) {
          const mapColumnToPrefix = {
            customer_id: 'C:', address_id: 'A:', order_id: 'SO:',
            item_id: 'OI:', product_id: 'P:', delivery_id: 'D:',
            invoice_id: 'INV:', payment_id: 'PAY:'
          }
          data.forEach(row => {
            Object.entries(row).forEach(([k, v]) => {
              if (mapColumnToPrefix[k] && v) {
                ids.add(mapColumnToPrefix[k] + v)
              }
            })
          })
        }
        onHighlightsChange(ids)
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error reaching the server. Is the backend running?',
        sql: null,
        data: [],
        isError: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const autoResize = (e) => {
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px'
  }

  return (
    <div className="chat-panel">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-top">
          <div className="chat-header-icon">🤖</div>
          <div>
            <div className="chat-header-name">Data Intelligence Assistant</div>
            <div className="chat-header-model">Powered by Groq · LLaMA 3 70B</div>
          </div>
        </div>
        <div className="chat-header-desc">
          Ask questions in natural language. Answers are grounded in your business dataset.
        </div>
      </div>

      {/* Suggestions */}
      {input.trim() === '' && messages.length === 1 && (
        <div className="suggestions">
          <div className="suggestions-title">Try asking</div>
          <div className="suggestion-chips">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                className="suggestion-chip"
                onClick={() => sendMessage(s)}
                disabled={loading}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="messages-area">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className={`message-bubble${msg.isError ? ' error-notice' : ''}`}>
              {msg.content}
            </div>
            {msg.sql && <SqlAccordion sql={msg.sql} />}
            {msg.data?.length > 0 && <DataTable rows={msg.data} />}
            <div className="message-meta">
              {msg.role === 'assistant' ? '🤖 Assistant' : '👤 You'}
            </div>
          </div>
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-input-wrap">
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder="Ask about orders, deliveries, invoices, payments…"
            value={input}
            onChange={e => { setInput(e.target.value); autoResize(e) }}
            onKeyDown={handleKey}
            rows={1}
            disabled={loading}
            id="chat-input"
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            title="Send (Enter)"
            id="send-btn"
          >
            {loading ? '⏳' : '➤'}
          </button>
        </div>
        <div className="chat-hint">Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  )
}
