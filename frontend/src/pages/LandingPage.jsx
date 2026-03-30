// LandingPage.jsx — SaaS marketing homepage
import { useNavigate } from 'react-router-dom'

const FEATURES = [
  {
    icon: '⬡',
    title: 'Knowledge Graph Visualization',
    desc: 'Transform flat spreadsheets into living, interactive network graphs. See how customers, orders, products, and deliveries connect in real-time.',
  },
  {
    icon: '⌘',
    title: 'Natural Language Queries',
    desc: 'Ask questions in plain English. No SQL, no dashboards. Type "show me top customers in Europe" and watch the graph respond instantly.',
  },
  {
    icon: '⚡',
    title: 'Powered by LLaMA 3 via Groq',
    desc: 'Sub-second AI inference with Groq\'s hardware. Your queries are processed at the speed of thought — no waiting, no spinning.',
  },
  {
    icon: '⬢',
    title: 'Bring Your Own Data',
    desc: 'Upload your own Excel or CSV business exports. The system auto-detects schema and wires up the graph. Structured or messy — it handles both.',
  },
  {
    icon: '◎',
    title: 'Complete Business Flow Tracking',
    desc: 'See the full lifecycle: Sales Order → Delivery → Invoice → Payment. Instantly spot incomplete flows, outstanding invoices and open orders.',
  },
  {
    icon: '◈',
    title: 'Zero Config, Runs Locally',
    desc: 'No cloud. No subscriptions. Your business data stays entirely on your machine. Just drop in your file and run two commands.',
  },
]

const STEPS = [
  { num: '01', label: 'Drop in your data', desc: 'Upload a CSV or Excel export from SAP, Salesforce, or any ERP system.' },
  { num: '02', label: 'Graph is built instantly', desc: 'Nodes for customers, orders, products, deliveries — edges for every relationship.' },
  { num: '03', label: 'Ask anything', desc: 'Use natural language in the chat panel to surface insights from your entire dataset.' },
]

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="landing">

      {/* ── NAV ── */}
      <nav className="landing-nav">
        <div className="landing-nav-logo">
          <span className="landing-nav-brand">Nexora</span>
        </div>

        <div className="landing-nav-links">
          <a href="#features" className="landing-nav-link">Features</a>
          <a href="#how-it-works" className="landing-nav-link">How it works</a>
          <button className="landing-btn-ghost" onClick={() => navigate('/upload')}>Upload Data</button>
          <button className="landing-btn-primary" onClick={() => navigate('/app')}>Try Demo →</button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="landing-hero">
        <div className="landing-hero-bg-grid" />
        <div className="landing-hero-content">
          <div className="landing-eyebrow">Business Intelligence, Reimagined</div>

          <h1 className="landing-headline">
            Your data as a<br />
            <span className="landing-headline-accent">knowledge graph</span>
          </h1>

          <p className="landing-subheadline">
            Upload your business data and explore it visually — with an AI that answers
            questions in plain English. No dashboards, no SQL, no setup.
          </p>

          <div className="landing-hero-ctas">
            <button className="landing-cta-primary" onClick={() => navigate('/app')}>
              Explore Demo
              <span className="landing-cta-arrow">→</span>
            </button>
            <button className="landing-cta-secondary" onClick={() => navigate('/upload')}>
              Upload Your Data
            </button>
          </div>

          <div className="landing-hero-meta">
            <span className="landing-meta-pill">● LLaMA 3 70B</span>
            <span className="landing-meta-pill">● Runs locally</span>
            <span className="landing-meta-pill">● Zero cloud</span>
          </div>
        </div>

        {/* Hero visual — animated graph preview */}
        <div className="landing-hero-visual">
          <div className="landing-graph-mock">
            <div className="mock-node mock-node--customer" style={{ top: '18%', left: '22%' }}>
              <span className="mock-node-icon">👤</span>
              <span className="mock-node-label">Acme Corp</span>
            </div>
            <div className="mock-node mock-node--order" style={{ top: '38%', left: '48%' }}>
              <span className="mock-node-icon">📋</span>
              <span className="mock-node-label">SO-001</span>
            </div>
            <div className="mock-node mock-node--product" style={{ top: '62%', left: '20%' }}>
              <span className="mock-node-icon">📦</span>
              <span className="mock-node-label">Pump X2</span>
            </div>
            <div className="mock-node mock-node--invoice" style={{ top: '55%', left: '65%' }}>
              <span className="mock-node-icon">🧾</span>
              <span className="mock-node-label">INV-001</span>
            </div>
            <div className="mock-node mock-node--delivery" style={{ top: '20%', left: '68%' }}>
              <span className="mock-node-icon">🚚</span>
              <span className="mock-node-label">D-001</span>
            </div>

            {/* SVG edges */}
            <svg className="mock-edges" viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
              <line x1="115" y1="60" x2="195" y2="115" className="mock-edge" />
              <line x1="195" y1="115" x2="80" y2="185" className="mock-edge" />
              <line x1="195" y1="115" x2="270" y2="165" className="mock-edge" />
              <line x1="195" y1="115" x2="280" y2="60" className="mock-edge" />
              <line x1="280" y1="60" x2="270" y2="165" className="mock-edge" />
            </svg>

            <div className="mock-chat-bubble">
              <span className="mock-chat-icon">⌘</span>
              "Show orders from Acme Corp this quarter"
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <div className="landing-stats-bar">
        {[
          { val: '6+', label: 'Entity Types' },
          { val: 'LLaMA 3', label: 'AI Engine' },
          { val: '<1s', label: 'Query latency' },
          { val: '100%', label: 'Local & private' },
        ].map(s => (
          <div className="landing-stat" key={s.label}>
            <span className="landing-stat-val">{s.val}</span>
            <span className="landing-stat-label">{s.label}</span>
          </div>
        ))}
      </div>

      {/* ── HOW IT WORKS ── */}
      <section className="landing-section" id="how-it-works">
        <div className="landing-section-header">
          <div className="landing-eyebrow">How it works</div>
          <h2 className="landing-section-title">Three steps to graph intelligence</h2>
        </div>
        <div className="landing-steps">
          {STEPS.map((step) => (
            <div className="landing-step" key={step.num}>
              <div className="landing-step-num">{step.num}</div>
              <h3 className="landing-step-label">{step.label}</h3>
              <p className="landing-step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="landing-section" id="features">
        <div className="landing-section-header">
          <div className="landing-eyebrow">Features</div>
          <h2 className="landing-section-title">Everything you need to understand your data</h2>
        </div>
        <div className="landing-features-grid">
          {FEATURES.map((f) => (
            <div className="landing-feature-card" key={f.title}>
              <div className="landing-feature-icon">{f.icon}</div>
              <h3 className="landing-feature-title">{f.title}</h3>
              <p className="landing-feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA BAND ── */}
      <section className="landing-cta-band">
        <h2 className="landing-cta-band-title">Ready to explore your data?</h2>
        <p className="landing-cta-band-desc">
          Try the live demo with sample SAP O2C data, or upload your own file to get started immediately.
        </p>
        <div className="landing-cta-band-actions">
          <button className="landing-cta-primary" onClick={() => navigate('/app')}>
            Try Demo →
          </button>
          <button className="landing-cta-secondary" onClick={() => navigate('/upload')}>
            Upload My Data
          </button>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="landing-footer">
        <div className="landing-footer-brand">
          <span className="landing-nav-brand">Nexora</span>
          <span className="landing-footer-tagline">Business Intelligence Explorer</span>
        </div>

        <div className="landing-footer-copy">
          Powered by LLaMA 3 · Groq · FastAPI · React
        </div>
      </footer>
    </div>
  )
}
