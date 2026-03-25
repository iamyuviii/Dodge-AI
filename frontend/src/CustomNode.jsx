// CustomNode.jsx — Redesigned React Flow node (larger, cleaner, less congested)
import { Handle, Position } from 'reactflow'
import {memo} from 'react'

const NODE_COLORS = {
  Customer:   { bg: '#6366f1', light: '#818cf820', border: '#6366f140' },
  Address:    { bg: '#8b5cf6', light: '#8b5cf620', border: '#8b5cf640' },
  SalesOrder: { bg: '#0ea5e9', light: '#0ea5e920', border: '#0ea5e940' },
  OrderItem:  { bg: '#38bdf8', light: '#38bdf820', border: '#38bdf840' },
  Product:    { bg: '#10b981', light: '#10b98120', border: '#10b98140' },
  Delivery:   { bg: '#f59e0b', light: '#f59e0b20', border: '#f59e0b40' },
  Invoice:    { bg: '#ef4444', light: '#ef444420', border: '#ef444440' },
  Payment:    { bg: '#22c55e', light: '#22c55e20', border: '#22c55e40' },
}

const DEFAULT_COLOR = { bg: '#6366f1', light: '#6366f120', border: '#6366f140' }

function CustomNode({ data, selected }) {
  const clr = NODE_COLORS[data.node_type] || DEFAULT_COLOR

  // Top 2 meta rows only, skip nulls
  const metaRows = Object.entries(data.meta || {})
    .filter(([, v]) => v && v !== 'None' && v !== 'null')
    .slice(0, 2)

  return (
    <div
      className={`custom-node${selected ? ' selected' : ''}`}
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
        style={{ background: clr.bg, width: 10, height: 10, border: '2px solid #0a0e1a', left: -5 }}
      />

      {/* Colour accent strip */}
      <div className="node-strip" style={{ background: clr.bg }} />

      <div className="node-header">
        <div className="node-icon" style={{ background: clr.light, border: `1px solid ${clr.border}` }}>
          <span style={{ fontSize: 16 }}>{data.icon || '⬡'}</span>
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
        style={{ background: clr.bg, width: 10, height: 10, border: '2px solid #0a0e1a', right: -5 }}
      />
    </div>
  )
}

export default memo(CustomNode)
