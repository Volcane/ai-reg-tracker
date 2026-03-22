import { Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext, useCallback, useRef } from 'react'
import {
  LayoutDashboard, FileText, GitCompare, Play,
  Network, Settings, Loader2, Bell, Brain, Layers,
  FileInput, BarChart3, BookOpen, TrendingUp, CalendarDays,
  Sparkles, Map, Clock, ScrollText, Shield, Search, X, ListChecks, ArrowLeftRight,
} from 'lucide-react'
import { api } from './api.js'
import Dashboard    from './views/Dashboard.jsx'
import Documents    from './views/Documents.jsx'
import Changes      from './views/Changes.jsx'
import RunAgents    from './views/RunAgents.jsx'
import Watchlist    from './views/Watchlist.jsx'
import Graph        from './views/Graph.jsx'
import Learning     from './views/Learning.jsx'
import Synthesis    from './views/Synthesis.jsx'
import PDFIngest    from './views/PDFIngest.jsx'
import GapAnalysis  from './views/GapAnalysis.jsx'
import Baselines    from './views/Baselines.jsx'
import Trends       from './views/Trends.jsx'
import Horizon      from './views/Horizon.jsx'
import AskAris      from './views/AskAris.jsx'
import ConceptMap   from './views/ConceptMap.jsx'
import Timeline     from './views/Timeline.jsx'
import Brief        from './views/Brief.jsx'
import Enforcement         from './views/Enforcement.jsx'
import ObligationRegister  from './views/ObligationRegister.jsx'
import Compare             from './views/Compare.jsx'
import SettingsView from './views/Settings.jsx'

// ── Domain Context ─────────────────────────────────────────────────────────
// Domain is now a filter, not a mode. Views read it; sidebar doesn't own it.
export const DomainContext = createContext({ domain: null, setDomain: () => {} })
export function useDomain() { return useContext(DomainContext) }

function DomainProvider({ children }) {
  // null = "All" — the default. Views persist their own preference.
  const [domain, setDomainState] = useState(null)
  const setDomain = useCallback((d) => setDomainState(d), [])
  return (
    <DomainContext.Provider value={{ domain, setDomain }}>
      {children}
    </DomainContext.Provider>
  )
}

// ── Nav config ─────────────────────────────────────────────────────────────
const NAV_GROUPS = [
  {
    items: [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
    ],
  },
  {
    label: 'Monitor',
    items: [
      { to: '/documents',   icon: FileText,     label: 'Documents'   },
      { to: '/changes',     icon: GitCompare,   label: 'Changes'     },
      { to: '/trends',      icon: TrendingUp,   label: 'Trends'      },
      { to: '/horizon',     icon: CalendarDays, label: 'Horizon'     },
      { to: '/enforcement', icon: Shield,       label: 'Enforcement' },
    ],
  },
  {
    label: 'Research',
    items: [
      { to: '/baselines', icon: BookOpen,       label: 'Baselines'    },
      { to: '/compare',   icon: ArrowLeftRight, label: 'Compare'      },
      { to: '/concepts',  icon: Map,            label: 'Concept Map'  },
      { to: '/graph',     icon: Network,    label: 'Graph'       },
      { to: '/timeline',  icon: Clock,      label: 'Timeline'    },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { to: '/ask',       icon: Sparkles,  label: 'Ask ARIS'     },
      { to: '/briefs',    icon: ScrollText,label: 'Briefs'       },
      { to: '/register',  icon: ListChecks,label: 'Obligations'  },
      { to: '/synthesis', icon: Layers,    label: 'Synthesis'    },
      { to: '/gap',       icon: BarChart3, label: 'Gap Analysis' },
      { to: '/watchlist', icon: Bell,      label: 'Watchlist'    },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/pdf',      icon: FileInput, label: 'PDF Ingest' },
      { to: '/run',      icon: Play,      label: 'Run Agents' },
      { to: '/learning', icon: Brain,     label: 'Learning'   },
    ],
  },
]

// ── NavItem ────────────────────────────────────────────────────────────────
function NavItem({ to, icon: Icon, label, badge, end: endProp }) {
  return (
    <NavLink to={to} end={endProp} style={({ isActive }) => ({
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '5px 10px', borderRadius: 'var(--radius)',
      color: isActive ? 'var(--text)' : 'var(--text-3)',
      background: isActive ? 'var(--bg-4)' : 'transparent',
      textDecoration: 'none', fontSize: 12.5,
      fontWeight: isActive ? 500 : 400, marginBottom: 1,
      transition: 'color 0.1s, background 0.1s',
      borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
    })}>
      <Icon size={13} style={{ flexShrink: 0 }} />
      <span style={{ flex: 1 }}>{label}</span>
      {badge > 0 && (
        <span style={{
          background: 'var(--red)', color: '#fff', fontSize: 10,
          borderRadius: 10, padding: '1px 5px',
          fontFamily: 'var(--font-mono)', lineHeight: '14px',
        }}>{badge}</span>
      )}
    </NavLink>
  )
}

// ── Global search overlay ──────────────────────────────────────────────────
function GlobalSearch({ onClose }) {
  const [q, setQ]         = useState('')
  const [results, setRes] = useState([])
  const [loading, setLod] = useState(false)
  const navigate          = useNavigate()
  const inputRef          = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    if (!q.trim()) { setRes([]); return }
    const t = setTimeout(async () => {
      setLod(true)
      try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=8`).then(r => r.json())
        setRes(r.items || [])
      } catch {} finally { setLod(false) }
    }, 280)
    return () => clearTimeout(t)
  }, [q])

  const go = (item) => {
    navigate('/documents')
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
      zIndex: 2000, display: 'flex', alignItems: 'flex-start',
      justifyContent: 'center', paddingTop: 80,
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        width: '100%', maxWidth: 620,
        background: 'var(--bg-2)', border: '1px solid var(--border-hi)',
        borderRadius: 'var(--radius-lg)', boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
        overflow: 'hidden',
      }}>
        {/* Input */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid var(--border)', gap: 10 }}>
          <Search size={16} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Search regulations, documents, baselines…"
            onKeyDown={e => { if (e.key === 'Escape') onClose() }}
            style={{
              flex: 1, background: 'transparent', border: 'none',
              outline: 'none', fontSize: 14, color: 'var(--text)',
              padding: 0,
            }}
          />
          {loading && <Loader2 size={14} style={{ color: 'var(--text-3)', animation: 'spin 1s linear infinite' }} />}
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-3)', cursor: 'pointer', padding: 2 }}>
            <X size={14} />
          </button>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {results.map((item, i) => (
              <div key={item.id || i} onClick={() => go(item)}
                style={{
                  padding: '10px 16px', cursor: 'pointer',
                  borderBottom: '1px solid var(--border)',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-3)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span style={{
                    fontSize: 9, fontFamily: 'var(--font-mono)', padding: '1px 5px',
                    borderRadius: 3, background: 'var(--bg-4)', color: 'var(--text-3)',
                    textTransform: 'uppercase', flexShrink: 0,
                  }}>{item.jurisdiction || item.source}</span>
                  {item.urgency && (
                    <span style={{
                      fontSize: 9, fontFamily: 'var(--font-mono)', padding: '1px 5px',
                      borderRadius: 3, flexShrink: 0,
                      background: item.urgency === 'Critical' ? 'rgba(224,82,82,0.15)' :
                                  item.urgency === 'High'     ? 'rgba(224,131,74,0.15)' :
                                  item.urgency === 'Medium'   ? 'rgba(212,168,67,0.15)' : 'var(--bg-4)',
                      color: item.urgency === 'Critical' ? 'var(--red)' :
                             item.urgency === 'High'     ? 'var(--orange)' :
                             item.urgency === 'Medium'   ? 'var(--yellow)' : 'var(--text-3)',
                    }}>{item.urgency}</span>
                  )}
                  {item.domain && item.domain !== 'ai' && (
                    <span style={{
                      fontSize: 9, fontFamily: 'var(--font-mono)', padding: '1px 5px',
                      borderRadius: 3, background: 'rgba(124,158,247,0.15)',
                      color: '#7c9ef7', flexShrink: 0,
                    }}>{item.domain === 'privacy' ? 'PRIVACY' : 'AI+PRIV'}</span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.4, marginBottom: 2 }}
                  className="truncate">{item.title}</div>
                {item.plain_english && (
                  <div style={{ fontSize: 11, color: 'var(--text-3)', lineHeight: 1.4 }}
                    className="truncate">{item.plain_english}</div>
                )}
              </div>
            ))}
            <div style={{ padding: '8px 16px', fontSize: 11, color: 'var(--text-3)', display: 'flex', justifyContent: 'space-between' }}>
              <span>{results.length} results</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Enter to open Documents</span>
            </div>
          </div>
        )}

        {q.trim() && !loading && results.length === 0 && (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-3)', fontSize: 13 }}>
            No results for "{q}"
          </div>
        )}

        {!q.trim() && (
          <div style={{ padding: '12px 16px 14px' }}>
            <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Quick search</div>
            {['GDPR data breach', 'EU AI Act prohibited', 'CCPA consumer rights', 'automated decision'].map(s => (
              <button key={s} onClick={() => setQ(s)} style={{
                display: 'inline-block', margin: '0 6px 6px 0', padding: '4px 10px',
                background: 'var(--bg-3)', border: '1px solid var(--border)',
                borderRadius: 20, fontSize: 12, color: 'var(--text-2)',
                cursor: 'pointer', transition: 'all 0.1s',
              }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-4)'; e.currentTarget.style.color = 'var(--text)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg-3)'; e.currentTarget.style.color = 'var(--text-2)' }}
              >{s}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── App inner ──────────────────────────────────────────────────────────────
function AppInner() {
  const [status,      setStatus]      = useState(null)
  const [jobRunning,  setJobRunning]  = useState(false)
  const [showSearch,  setShowSearch]  = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const load = async () => {
      try {
        const s = await api.status()
        setStatus(s)
        setJobRunning(s.job?.running || false)
      } catch {}
    }
    load()
    const id = setInterval(load, 8000)
    return () => clearInterval(id)
  }, [])

  // Keyboard shortcut: Cmd/Ctrl+K or / to open search
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowSearch(s => !s)
      }
      if (e.key === 'Escape') setShowSearch(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const stats           = status?.stats || {}
  const unreviewedDiffs = stats.unreviewed_diffs || 0

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: 200, background: 'var(--bg-2)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
      }}>
        {/* Wordmark */}
        <div style={{ padding: '16px 14px 10px', flexShrink: 0 }}>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: '1.35rem',
            fontWeight: 300, color: 'var(--accent)', letterSpacing: '-0.01em',
          }}>ARIS</div>
          <div style={{ fontSize: 9, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
            Automated Regulatory Intelligence
          </div>
        </div>

        {/* Search trigger */}
        <div style={{ padding: '0 8px 8px' }}>
          <button
            onClick={() => setShowSearch(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7, width: '100%',
              padding: '6px 10px', background: 'var(--bg-3)',
              border: '1px solid var(--border)', borderRadius: 'var(--radius)',
              cursor: 'pointer', color: 'var(--text-3)', fontSize: 12,
              transition: 'all 0.1s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-hi)'; e.currentTarget.style.color = 'var(--text-2)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-3)' }}
          >
            <Search size={12} />
            <span style={{ flex: 1, textAlign: 'left' }}>Search…</span>
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', opacity: 0.6 }}>⌘K</span>
          </button>
        </div>

        {/* Nav groups */}
        <nav style={{ flex: 1, padding: '0 8px', overflowY: 'auto' }}>
          {NAV_GROUPS.map(({ label, items }) => (
            <div key={label || 'root'} style={{ marginBottom: 10 }}>
              {label && (
                <div style={{
                  fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-3)',
                  textTransform: 'uppercase', letterSpacing: '0.08em',
                  padding: '4px 10px 3px', opacity: 0.7,
                }}>{label}</div>
              )}
              {items.map(({ to, icon, label: lbl, end }) => (
                <NavItem key={to} to={to} icon={icon} label={lbl} end={end}
                  badge={lbl === 'Changes' ? unreviewedDiffs : 0} />
              ))}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div style={{ borderTop: '1px solid var(--border)', padding: '8px 8px 6px', flexShrink: 0 }}>
          <NavItem to="/settings" icon={Settings} label="Settings" />
          <div style={{ padding: '6px 10px 2px', fontSize: 11, color: 'var(--text-3)' }}>
            {jobRunning ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--accent)' }}>
                <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
                <span>Agent running…</span>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: status ? 'var(--green)' : 'var(--red-dim)', flexShrink: 0,
                }} />
                <span>{stats.total_documents ?? '—'} docs · {stats.total_summaries ?? '—'} summarised</span>
              </div>
            )}
            {status?.job?.last_run && (
              <div style={{ marginTop: 3, fontSize: 10, fontFamily: 'var(--font-mono)' }}>
                Last run: {new Date(status.job.last_run).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Routes>
          <Route path="/"            element={<Dashboard   status={status} />} />
          <Route path="/ask"         element={<AskAris />} />
          <Route path="/concepts"    element={<ConceptMap />} />
          <Route path="/briefs"      element={<Brief />} />
          <Route path="/timeline"    element={<Timeline />} />
          <Route path="/documents"   element={<Documents />} />
          <Route path="/changes"     element={<Changes />} />
          <Route path="/baselines"   element={<Baselines />} />
          <Route path="/trends"      element={<Trends />} />
          <Route path="/horizon"     element={<Horizon />} />
          <Route path="/enforcement" element={<Enforcement />} />
          <Route path="/synthesis"   element={<Synthesis />} />
          <Route path="/gap"         element={<GapAnalysis />} />
          <Route path="/register"    element={<ObligationRegister />} />
          <Route path="/compare"     element={<Compare />} />
          <Route path="/watchlist"   element={<Watchlist />} />
          <Route path="/pdf"         element={<PDFIngest />} />
          <Route path="/run"         element={<RunAgents onJobStart={() => setJobRunning(true)} />} />
          <Route path="/graph"       element={<Graph navigate={navigate} />} />
          <Route path="/learning"    element={<Learning />} />
          <Route path="/settings"    element={<SettingsView status={status} />} />
        </Routes>

        {/* ── Disclaimer footer ── */}
        <footer style={{
          borderTop: '1px solid var(--border)',
          padding: '10px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          flexShrink: 0,
          background: 'var(--bg-1)',
        }}>
          <p style={{
            margin: 0,
            fontSize: 10,
            color: 'var(--text-3)',
            lineHeight: 1.5,
            maxWidth: 820,
          }}>
            <strong style={{ color: 'var(--text-2)', fontWeight: 500 }}>Not legal, compliance, or regulatory advice.</strong>
            {' '}ARIS is an informational research tool only. Nothing in this system — including
            summaries, gap analyses, jurisdiction comparisons, or any other output — constitutes
            legal, compliance, or regulatory advice, and should not be relied upon as such.
            Regulatory requirements vary by jurisdiction, industry, organisation type, and the
            specific facts of your situation. Always consult qualified legal counsel before making
            compliance or regulatory decisions.
          </p>
          <p style={{
            margin: 0,
            fontSize: 10,
            color: 'var(--text-3)',
            whiteSpace: 'nowrap',
            flexShrink: 0,
            textAlign: 'right',
            lineHeight: 1.6,
          }}>
            © {new Date().getFullYear()} Mitch Kwiatkowski
            {' '}·{' '}<a
              href="https://www.elastic.co/licensing/elastic-license"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--text-3)', textDecoration: 'underline', textDecorationColor: 'var(--border)' }}
            >Elastic License 2.0</a>
            {' '}·{' '}Non-commercial use only
          </p>
        </footer>
      </main>

      {/* Global search overlay */}
      {showSearch && <GlobalSearch onClose={() => setShowSearch(false)} />}
    </div>
  )
}

export default function App() {
  return (
    <DomainProvider>
      <AppInner />
    </DomainProvider>
  )
}
