// GraphCanvas.jsx — Dagre-layouted interactive graph visualization with search
import { useCallback, useEffect, useRef, useState, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType,
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'
import axios from 'axios'
import CustomNode from './CustomNode'
import NodeInspector from './NodeInspector'
import { applyDagreLayout } from './layout'

const nodeTypes = { customNode: CustomNode }

const NODE_COLORS = {
  Customer:   '#3b82f6',
  Address:    '#a855f7',
  SalesOrder: '#0ea5e9',
  OrderItem:  '#64748b',
  Product:    '#22c55e',
  Delivery:   '#eab308',
  Invoice:    '#ef4444',
  Payment:    '#10b981',
}

const LEGEND_ITEMS = [
  { type: 'Customer',   icon: '👤', color: NODE_COLORS.Customer },
  { type: 'SalesOrder', icon: '📋', color: NODE_COLORS.SalesOrder },
  { type: 'OrderItem',  icon: '🔖', color: NODE_COLORS.OrderItem },
  { type: 'Product',    icon: '📦', color: NODE_COLORS.Product },
  { type: 'Delivery',   icon: '🚚', color: NODE_COLORS.Delivery },
  { type: 'Invoice',    icon: '🧾', color: NODE_COLORS.Invoice },
  { type: 'Payment',    icon: '💳', color: NODE_COLORS.Payment },
  { type: 'Address',    icon: '📍', color: NODE_COLORS.Address },
]

const FILTERS = ['All', ...Object.keys(NODE_COLORS)]

function styledEdges(edges) {
  return edges.map(e => ({
    ...e,
    type: 'smoothstep',
    animated: false,
    style: { stroke: e.style?.stroke || '#3a4880', strokeWidth: 1.5, strokeOpacity: e.style?.strokeOpacity || 0.6 },
    labelStyle: { fill: '#64748b', fontSize: 10, fontFamily: 'Inter, sans-serif' },
    labelBgStyle: { fill: '#0f1526', fillOpacity: 0.85 },
    labelBgPadding: [4, 6],
    labelBgBorderRadius: 4,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: e.style?.stroke || '#3a4880',
      width: 12,
      height: 12,
    },
  }))
}

export default function GraphCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [stats, setStats]       = useState({ nodes: 0, edges: 0 })
  const [inspectorId, setInspectorId] = useState(null)
  const [activeFilter, setActiveFilter] = useState('All')
  const [layoutDir, setLayoutDir] = useState('LR')
  const [toast, setToast] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)

  const allNodesRef = useRef([])
  const allEdgesRef = useRef([])
  const rfInstance  = useRef(null)

  // ── Compute filter counts ─────────────────────────────────────────────────
  const filterCounts = useMemo(() => {
    const counts = {}
    allNodesRef.current.forEach(n => {
      const t = n.data?.node_type || 'Unknown'
      counts[t] = (counts[t] || 0) + 1
    })
    return counts
  }, [nodes]) // re-compute when nodes change

  // ── Search results ────────────────────────────────────────────────────────
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return []
    const q = searchQuery.toLowerCase()
    return allNodesRef.current
      .filter(n => {
        const label = (n.data?.label || '').toLowerCase()
        const type = (n.data?.node_type || '').toLowerCase()
        const id = (n.id || '').toLowerCase()
        return label.includes(q) || type.includes(q) || id.includes(q)
      })
      .slice(0, 8)
  }, [searchQuery, nodes])

  const focusNode = useCallback((nodeId) => {
    const node = allNodesRef.current.find(n => n.id === nodeId)
    if (node && rfInstance.current) {
      rfInstance.current.fitView({
        nodes: [{ id: nodeId }],
        padding: 0.5,
        duration: 600,
      })
      setInspectorId(nodeId)
      setSearchQuery('')
    }
  }, [])

  // ── Callbacks ──────────────────────────────────────────────────────────────

  const handleSelectNode = useCallback((data) => {
    setInspectorId(data.nodeId || null)
  }, [])

  const handleExpandNode = useCallback(async (data) => {
    const nodeId = data.nodeId || data.nodeId
    if (!nodeId) return
    try {
      const resp = await axios.get(`/api/graph/expand/${encodeURIComponent(nodeId)}`)
      const { nodes: newRaw, edges: newEdgesRaw } = resp.data

      const existingNodeIds = new Set(allNodesRef.current.map(n => n.id))
      const toAddNodes = newRaw
        .filter(n => !existingNodeIds.has(n.id))
        .map(n => injectCbs({ ...n, position: { x: 0, y: 0 } }))

      const existingEdgeIds = new Set(allEdgesRef.current.map(e => e.id))
      const toAddEdges = styledEdges(newEdgesRaw.filter(e => !existingEdgeIds.has(e.id)))

      if (!toAddNodes.length && !toAddEdges.length) {
        setToast('All connected data for this entity is already mapped.')
        setTimeout(() => setToast(null), 3500)
        return
      }

      const mergedNodes = [...allNodesRef.current, ...toAddNodes]
      const mergedEdges = [...allEdgesRef.current, ...toAddEdges]

      allNodesRef.current = mergedNodes
      allEdgesRef.current = mergedEdges

      const laidOutNodes = applyDagreLayout(mergedNodes, mergedEdges, layoutDir)
      
      setNodes(laidOutNodes)
      setEdges(mergedEdges)
      setTimeout(() => rfInstance.current?.fitView({ padding: 0.15, duration: 500 }), 80)
      
    } catch (e) {
      console.error('Expand failed', e)
    }
  }, [layoutDir])

  function injectCbs(node) {
    return {
      ...node,
      data: {
        ...node.data,
        nodeId: node.id,
        onSelect: handleSelectNode,
        onExpand: handleExpandNode,
      },
    }
  }

  // ── Initial load ────────────────────────────────────────────────────────────

  useEffect(() => {
    axios.get('/api/graph')
      .then(resp => {
        const { nodes: rawNodes, edges: rawEdges } = resp.data

        if (!rawNodes.length) {
          setLoading(false)
          setError('empty')
          return
        }

        const enriched  = rawNodes.map(injectCbs)
        const edgesStyled = styledEdges(rawEdges)

        const laidOut = applyDagreLayout(enriched, edgesStyled, 'LR')

        allNodesRef.current = laidOut
        allEdgesRef.current = edgesStyled

        setNodes(laidOut)
        setEdges(edgesStyled)
        setStats({ nodes: rawNodes.length, edges: rawEdges.length })
        setLoading(false)

        setTimeout(() => rfInstance.current?.fitView({ padding: 0.12, duration: 600 }), 100)
      })
      .catch(() => {
        setError('Cannot connect to backend on port 8000.')
        setLoading(false)
      })
  }, [])

  // ── Filter ──────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!allNodesRef.current.length) return

    let visNodes = allNodesRef.current
    let visEdges = allEdgesRef.current

    if (activeFilter !== 'All') {
      visNodes = allNodesRef.current.filter(n => n.data.node_type === activeFilter)
      const ids = new Set(visNodes.map(n => n.id))
      visEdges = allEdgesRef.current.filter(e => ids.has(e.source) && ids.has(e.target))
    }

    const laidOut = applyDagreLayout(visNodes, visEdges, layoutDir)
    setNodes(laidOut)
    setEdges(visEdges)
    setTimeout(() => rfInstance.current?.fitView({ padding: 0.15, duration: 500 }), 80)
  }, [activeFilter, layoutDir])

  // ── Re-layout ───────────────────────────────────────────────────────────────

  const handleRelayout = (dir) => {
    setLayoutDir(dir)
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="graph-panel">
      <div className="graph-loading">
        <div className="spinner" />
        <p>Building knowledge graph…</p>
      </div>
    </div>
  )

  if (error === 'empty') return (
    <div className="graph-panel">
      <div className="graph-loading">
        <div className="empty-state">
          <div className="empty-state-icon">⬡</div>
          <h3>No data loaded</h3>
          <p>Upload a dataset or run the preprocessor to seed demo data.</p>
        </div>
      </div>
    </div>
  )

  if (error) return (
    <div className="graph-panel">
      <div className="graph-loading">
        <div className="error-notice">{error}</div>
      </div>
    </div>
  )

  return (
    <div className="graph-panel">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onInit={inst => { rfInstance.current = inst }}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.45}
        maxZoom={2.5}
        defaultEdgeOptions={{ type: 'smoothstep' }}
        attributionPosition="bottom-right"
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        panOnScroll={true}
        zoomActivationKeyCode="Control"
      >
        <Background variant={BackgroundVariant.Dots} color="#1a2340" gap={24} size={1.2} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={n => n.data?.color || '#6366f1'}
          maskColor="rgba(10,14,26,0.88)"
          style={{ background: '#0f1526', border: '1px solid #2a3660', borderRadius: 8 }}
          pannable
          zoomable
        />

        {/* ── Top toolbar (Panel) ── */}
        <Panel position="top-left">
          <div className="graph-top-bar">
            {/* Search bar */}
            <div className="graph-search-wrap">
              <input
                className="graph-search"
                type="text"
                placeholder="Search nodes…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
              />
              {searchFocused && searchResults.length > 0 && (
                <div className="graph-search-results">
                  {searchResults.map(n => (
                    <button
                      key={n.id}
                      className="graph-search-result"
                      onMouseDown={() => focusNode(n.id)}
                    >
                      <span className="graph-search-result-icon" style={{ color: n.data?.color }}>
                        {n.data?.icon || '⬡'}
                      </span>
                      <span className="graph-search-result-label">{n.data?.label}</span>
                      <span className="graph-search-result-type">{n.data?.node_type}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Entity filter chips */}
            <div className="filter-group">
              {FILTERS.map(f => (
                <button
                  key={f}
                  className={`filter-chip${activeFilter === f ? ' active' : ''}`}
                  style={
                    activeFilter === f
                      ? { background: NODE_COLORS[f] || '#6366f1', borderColor: NODE_COLORS[f] || '#6366f1' }
                      : { borderColor: (NODE_COLORS[f] || '#3a4880') + '80' }
                  }
                  onClick={() => setActiveFilter(f)}
                >
                  {f}
                  {f !== 'All' && filterCounts[f] ? (
                    <span className="filter-chip-count">{filterCounts[f]}</span>
                  ) : null}
                </button>
              ))}
            </div>

            {/* Layout direction toggle */}
            <div className="layout-group">
              <span className="layout-label">Layout</span>
              {[['LR', '→'], ['TB', '↓'], ['RL', '←']].map(([dir, icon]) => (
                <button
                  key={dir}
                  className={`layout-btn${layoutDir === dir ? ' active' : ''}`}
                  onClick={() => handleRelayout(dir)}
                  title={`${dir} layout`}
                >
                  {icon}
                </button>
              ))}
              <button
                className="layout-btn"
                onClick={() => rfInstance.current?.fitView({ padding: 0.12, duration: 500 })}
                title="Fit view"
              >
                ⊡
              </button>
            </div>
          </div>
        </Panel>

        {/* ── Legend (Panel) ── */}
        <Panel position="bottom-left">
          <div className="legend-card">
            <div className="legend-title">Entity Types</div>
            <div className="legend-grid">
              {LEGEND_ITEMS.map(({ type, icon, color }) => (
                <div
                  key={type}
                  className={`legend-row${activeFilter === type ? ' legend-active' : ''}`}
                  onClick={() => setActiveFilter(activeFilter === type ? 'All' : type)}
                  title={`Filter by ${type}`}
                >
                  <span className="legend-dot" style={{ background: color }} />
                  <span className="legend-icon">{icon}</span>
                  <span className="legend-type">{type}</span>
                  {filterCounts[type] ? (
                    <span className="legend-count">{filterCounts[type]}</span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </ReactFlow>

      {/* Node inspector */}
      {inspectorId && (
        <NodeInspector
          nodeId={inspectorId}
          onClose={() => setInspectorId(null)}
          onExpand={(data) => handleExpandNode({ nodeId: data.nodeId })}
        />
      )}

      {/* Toast Notification */}
      {toast && (
        <div className="graph-toast">
          {toast}
        </div>
      )}
    </div>
  )
}
