// UploadPage.jsx — Data upload flow
import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

export default function UploadPage() {
  const navigate = useNavigate()
  const fileRef = useRef(null)

  const [mode, setMode] = useState('demo')        // 'demo' | 'upload'
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const isValidFile = f => f && (
    f.name.endsWith('.csv') ||
    f.name.endsWith('.xlsx') ||
    f.name.endsWith('.xls')
  )

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (isValidFile(dropped)) {
      setFile(dropped)
      setError(null)
    } else {
      setError('Please drop a CSV or Excel file (.csv, .xlsx, .xls)')
    }
  }

  function handleFileChange(e) {
    const selected = e.target.files[0]
    if (isValidFile(selected)) {
      setFile(selected)
      setError(null)
    } else {
      setError('Please select a CSV or Excel file (.csv, .xlsx, .xls)')
    }
  }

  async function handleSubmit() {
    if (mode === 'demo') {
      navigate('/app')
      return
    }

    if (!file) {
      setError('Please select a file first.')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const form = new FormData()
      form.append('file', file)
      const res = await axios.post('/api/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSuccess(`Graph loaded: ${res.data.nodes} nodes, ${res.data.edges} edges`)
      setTimeout(() => navigate('/app'), 1500)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="upload-page">
      <nav className="landing-nav" style={{ position: 'relative', borderBottom: '1px solid var(--clr-border)' }}>
        <div className="landing-nav-logo" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
          <span className="landing-nav-brand">Nexora</span>
        </div>
        <div className="landing-nav-links">
          <button className="landing-btn-ghost" onClick={() => navigate('/')}>← Home</button>
          <button className="landing-btn-primary" onClick={() => navigate('/app')}>Try Demo</button>
        </div>
      </nav>

      <div className="upload-container">
        <div className="upload-header">
          <div className="landing-eyebrow">Data Source</div>
          <h1 className="upload-title">Choose how to load your data</h1>
          <p className="upload-subtitle">
            Use the built-in SAP O2C demo to explore the app, or upload your own Excel / CSV export.
          </p>
        </div>

        {/* Toggle */}
        <div className="upload-toggle">
          <button
            className={`upload-toggle-btn ${mode === 'demo' ? 'active' : ''}`}
            onClick={() => setMode('demo')}
          >
            <span className="upload-toggle-icon">◎</span>
            <span>
              <span className="upload-toggle-label">Use Demo Data</span>
              <span className="upload-toggle-desc">SAP O2C dataset · ready instantly</span>
            </span>
          </button>
          <button
            className={`upload-toggle-btn ${mode === 'upload' ? 'active' : ''}`}
            onClick={() => setMode('upload')}
          >
            <span className="upload-toggle-icon">⬆</span>
            <span>
              <span className="upload-toggle-label">Upload My Own File</span>
              <span className="upload-toggle-desc">CSV or Excel · stays on your machine</span>
            </span>
          </button>
        </div>

        {/* Upload zone (only when mode === 'upload') */}
        {mode === 'upload' && (
          <div
            className={`upload-dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            {file ? (
              <>
                <div className="upload-dropzone-icon upload-dropzone-icon--success">✓</div>
                <div className="upload-dropzone-name">{file.name}</div>
                <div className="upload-dropzone-size">{(file.size / 1024).toFixed(1)} KB</div>
                <div className="upload-dropzone-change">Click to change file</div>
              </>
            ) : (
              <>
                <div className="upload-dropzone-icon">⬆</div>
                <div className="upload-dropzone-label">Drop your file here</div>
                <div className="upload-dropzone-hint">CSV, XLSX or XLS · Click to browse</div>
              </>
            )}
          </div>
        )}

        {/* Demo data info */}
        {mode === 'demo' && (
          <div className="upload-demo-info">
            <div className="upload-demo-info-icon">◎</div>
            <div>
              <div className="upload-demo-info-title">SAP Order-to-Cash (O2C) Sample Dataset</div>
              <div className="upload-demo-info-desc">
                Includes 3 customers, 4 products, 4 sales orders, deliveries, invoices and payments — 
                illustrating both complete and incomplete business flows.
              </div>
              <div className="upload-demo-pills">
                <span className="upload-demo-pill">Customers</span>
                <span className="upload-demo-pill">Orders</span>
                <span className="upload-demo-pill">Products</span>
                <span className="upload-demo-pill">Deliveries</span>
                <span className="upload-demo-pill">Invoices</span>
                <span className="upload-demo-pill">Payments</span>
              </div>
            </div>
          </div>
        )}

        {/* Error / success */}
        {error && <div className="upload-error">{error}</div>}
        {success && <div className="upload-success">{success}</div>}

        {/* Privacy note */}
        {mode === 'upload' && (
          <div className="upload-privacy">
            🔒 Your data never leaves your machine. Files are processed locally by the Python backend and stored in a local SQLite database.
          </div>
        )}

        {/* Submit */}
        <button
          className="upload-submit"
          onClick={handleSubmit}
          disabled={uploading || (mode === 'upload' && !file)}
        >
          {uploading ? (
            <span className="upload-submit-loading">
              <span className="upload-spinner" />
              Processing…
            </span>
          ) : mode === 'demo' ? (
            'Open Demo →'
          ) : (
            'Upload & Open Graph →'
          )}
        </button>
      </div>
    </div>
  )
}
