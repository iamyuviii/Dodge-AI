// CustomNode.jsx — Redesigned React Flow node (larger, cleaner, less congested)
import { Handle, Position } from 'reactflow'
import {memo, useContext} from 'react'
import { HighlightContext } from './pages/AppPage'

const NODE_COLORS = {
  Customer:   { bg: '#3b82f6', light: '#3b82f61a', border: '#3b82f633' },
  Address:    { bg: '#a855f7', light: '#a855f71a', border: '#a855f733' },
  SalesOrder: { bg: '#0ea5e9', light: '#0ea5e91a', border: '#0ea5e933' },
  OrderItem:  { bg: '#64748b', light: '#64748b1a', border: '#64748b33' },
  Product:    { bg: '#22c55e', light: '#22c55e1a', border: '#22c55e33' },
  Delivery:   { bg: '#eab308', light: '#eab3081a', border: '#eab30833' },
  Invoice:    { bg: '#ef4444', light: '#ef44441a', border: '#ef444433' },
  Payment:    { bg: '#10b981', light: '#10b9811a', border: '#10b98133' },
}

const DEFAULT_COLOR = { bg: '#64748b', light: '#64748b1a', border: '#64748b33' }

function CustomNode({ data, selected, id }) {
  const clr = NODE_COLORS[data.node_type] || DEFAULT_COLOR

  const highlightIds = useContext(HighlightContext)
  const isHighlighted = highlightIds?.has(id) || false

  // Top 2 meta rows only, skip nulls
  const metaRows = Object.entries(data.meta || {})
    .filter(([, v]) => v && v !== 'None' && v !== 'null')
    .slice(0, 2)

  return (
    <div
      className={`custom-node${selected ? ' selected' : ''}${isHighlighted ? ' highlighted' : ''}`}
      style={{
        '--node-color': clr.bg,
        '--node-light': clr.light,
        '--node-border': clr.border,
      }}
      onClick={() => data.onSelect && data.onSelect(data)}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: clr.bg, width: 6, height: 6, border: 'none', left: -3 }}
      />

      <div className="node-header">
        <div className="node-icon" style={{ color: clr.bg }}>
          <span style={{ fontSize: 14 }}>{data.icon || '⬡'}</span>
        </div>
        <div className="node-title-group">
          <div className="node-title" title={data.label}>{data.label}</div>
          <div className="node-type-tag" style={{ color: clr.bg }}>
            {data.node_type}
          </div>
        </div>
      </div>

      {metaRows.length > 0 && (
        <div className="node-body">
          {metaRows.map(([k, v]) => (
            <div key={k} className="node-meta-row">
              <span className="node-meta-key">{k}</span>
              <span className="node-meta-val" title={String(v)}>{String(v)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="node-footer">
        <button
          className="node-expand-btn"
          onClick={e => { e.stopPropagation(); data.onExpand && data.onExpand(data) }}
          title="Expand neighbours"
        >
          ⊕ expand
        </button>
        <button
          className="node-inspect-btn"
          onClick={e => { e.stopPropagation(); data.onSelect && data.onSelect(data) }}
          title="Inspect node"
        >
          ⓘ inspect
        </button>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: clr.bg, width: 6, height: 6, border: 'none', right: -3 }}
      />
    </div>
  )
}

export default memo(CustomNode)
