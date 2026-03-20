import { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, CartesianGrid, Legend,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, RefreshCw, AlertTriangle, Zap } from 'lucide-react'
import { Spinner, EmptyState, Badge, DomainFilter } from '../components.jsx'

// ── API ───────────────────────────────────────────────────────────────────────

const trendsApi = {
  all:     () => fetch('/api/trends').then(r => r.json()),
  refresh: () => fetch('/api/trends/refresh', { method: 'POST' }).then(r => r.json()),
}

// ── Colours ───────────────────────────────────────────────────────────────────

const URGENCY_COLORS = {
  Critical: '#e05252',
  High:     '#e0834a',
  Medium:   '#d4a843',
  Low:      '#52a878',
}

const TREND_STYLE = {
  accelerating: { color: 'var(--red)',    icon: TrendingUp,   label: 'Accelerating' },
  stable:       { color: 'var(--accent)', icon: Minus,        label: 'Stable'       },
  decelerating: { color: 'var(--text-3)', icon: TrendingDown, label: 'Decelerating' },
}

const JUR_COLORS = [
  '#1A5EAB','#e05252','#52a878','#d4a843','#e0834a',
  '#7b52ab','#52a8a8','#ab527b','#6a8e3e','#3e6a8e',
]

// ── Main view ─────────────────────────────────────────────────────────────────

export default function Trends() {
  const [data,      setData]      = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [refreshing,setRefreshing]= useState(false)
  const [tab,       setTab]       = useState('velocity')
  const [jurFilter, setJurFilter] = useState('')
  const [domain,    setDomain]    = useState(() => {
    try { return localStorage.getItem('aris_domain_trends') ?? null } catch { return null }
  })
  const handleDomainChange = (d) => {
    setDomain(d)
    try { localStorage.setItem('aris_domain_trends', d ?? '') } catch {}
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await trendsApi.all()
      setData(d)
    } catch (e) {
      console.error('Trends load error', e)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const refresh = async () => {
    setRefreshing(true)
    await trendsApi.refresh()
    // Poll until the background refresh completes (up to 15s)
    for (let i = 0; i < 15; i++) {
      await new Promise(r => setTimeout(r, 1000))
      try {
        const d = await trendsApi.all()
        setData(d)
      } catch {}
    }
    setRefreshing(false)
  }

  const noData = !loading && (!data || (data.total_docs === 0))

  // Domain-filter velocity data client-side
  // velocity entries have jurisdiction; we use domain tags if available,
  // otherwise fall back to known privacy-centric jurisdictions
  const PRIVACY_JURS = new Set(['EU', 'GB', 'BR', 'SG', 'JP', 'AU', 'CA'])
  const filteredVelocity = (data?.velocity || []).filter(v => {
    if (!domain) return true
    const isPrivacy = PRIVACY_JURS.has(v.jurisdiction)
    if (domain === 'privacy') return isPrivacy
    if (domain === 'ai')      return !isPrivacy
    return true
  })

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontWeight: 300, fontSize: '1.4rem', marginBottom: 4 }}>
            Regulatory Velocity &amp; Trends
          </h2>
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
            Computed from your document database · no API calls
            {data?.last_updated && ` · last updated ${data.last_updated.slice(0,16).replace('T',' ')}`}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <DomainFilter domain={domain} onChange={handleDomainChange} />
          <button className="btn-secondary btn-sm" onClick={refresh} disabled={refreshing || loading}>
            <RefreshCw size={12} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={24} /></div>
      ) : noData ? (
        <TrendsEmptyState />
      ) : (
        <>
          {/* Alert banner */}
          {(data?.alerts?.length > 0) && (
            <AlertBanner alerts={data.alerts} />
          )}

          {/* Summary stats */}
          <SummaryStats data={data} />

          {/* Tab bar */}
          <div className="flex" style={{ borderBottom: '1px solid var(--border)', marginBottom: 24, marginTop: 20 }}>
            {[
              { id: 'velocity', label: 'Velocity by Jurisdiction' },
              { id: 'heatmap',  label: `Impact Areas (${data?.heatmap?.length || 0})` },
              { id: 'alerts',   label: `Alerts (${data?.alerts?.length || 0})`, red: data?.alerts?.length > 0 },
            ].map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                background: 'transparent', border: 'none', cursor: 'pointer',
                padding: '8px 16px', fontSize: 13,
                fontWeight: tab === t.id ? 500 : 400,
                color: t.red
                  ? (tab === t.id ? 'var(--red)' : 'var(--orange)')
                  : tab === t.id ? 'var(--text)' : 'var(--text-3)',
                borderBottom: tab === t.id
                  ? `2px solid ${t.red ? 'var(--red)' : 'var(--accent)'}`
                  : '2px solid transparent',
                marginBottom: -1,
              }}>
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'velocity' && <VelocityTab velocity={filteredVelocity} />}
          {tab === 'heatmap'  && <HeatmapTab  heatmap={data?.heatmap  || []} />}
          {tab === 'alerts'   && <AlertsTab   alerts={data?.alerts    || []} />}
        </>
      )}
    </div>
  )
}

// ── Summary stats row ─────────────────────────────────────────────────────────

function SummaryStats({ data }) {
  const accel = (data?.velocity || []).filter(v => v.trend === 'accelerating').length
  const topArea = data?.heatmap?.[0]

  return (
    <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
      {[
        { label: 'Total Documents', value: data?.total_docs || 0 },
        { label: 'Jurisdictions',   value: data?.jurisdictions || 0 },
        { label: 'Impact Areas',    value: data?.impact_areas || 0 },
        { label: 'Accelerating',    value: accel, color: accel > 0 ? 'var(--orange)' : 'var(--text)' },
        { label: 'Active Alerts',   value: data?.alert_count || 0, color: data?.alert_count > 0 ? 'var(--red)' : 'var(--text)' },
      ].map(s => (
        <div key={s.label} className="card" style={{ flex: '1 1 140px', padding: '11px 14px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 300, color: s.color || 'var(--text)', marginBottom: 2 }}>
            {s.value}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {s.label}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Alert banner ──────────────────────────────────────────────────────────────

function AlertBanner({ alerts }) {
  const [open, setOpen] = useState(false)
  const critical = alerts.filter(a => a.severity === 'Critical')
  const top      = alerts[0]

  return (
    <div style={{ marginBottom: 16, padding: '10px 16px', background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.3)', borderRadius: 'var(--radius)', cursor: 'pointer' }}
      onClick={() => setOpen(o => !o)}>
      <div className="flex items-center gap-3">
        <AlertTriangle size={14} style={{ color: 'var(--red)', flexShrink: 0 }} />
        <span style={{ flex: 1, fontSize: 13, color: 'var(--text-2)' }}>
          <strong>{alerts.length} acceleration alert{alerts.length !== 1 ? 's' : ''}</strong>
          {critical.length > 0 && ` · ${critical.length} critical`}
          {top && ` · ${top.message}`}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {alerts.slice(0, 5).map((a, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-2)', paddingLeft: 22 }}>
              <span style={{ color: a.severity === 'Critical' ? 'var(--red)' : 'var(--orange)', fontWeight: 500 }}>
                {a.severity}:
              </span>{' '}{a.message}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Velocity tab ──────────────────────────────────────────────────────────────

function VelocityTab({ velocity }) {
  const [selected, setSelected] = useState(null)

  if (!velocity.length) return (
    <div style={{ color: 'var(--text-3)', fontSize: 13, fontStyle: 'italic' }}>No velocity data yet.</div>
  )

  const displayedJur = selected
    ? velocity.filter(v => v.jurisdiction === selected)
    : velocity

  // Build combined chart data — one entry per window label
  const allLabels = velocity[0]?.windows?.map(w => w.label) || []
  const topJurs   = velocity.slice(0, 6)

  const chartData = allLabels.map((label, wi) => {
    const entry = { label }
    topJurs.forEach(v => {
      entry[v.jurisdiction] = v.windows[wi]?.count || 0
    })
    return entry
  })

  return (
    <div>
      {/* Combined time-series chart */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14 }}>
          Document volume — top jurisdictions (12-month window)
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="label" tick={{ fill: 'var(--text-3)', fontSize: 10 }} axisLine={false} tickLine={false} interval={1} />
            <YAxis tick={{ fill: 'var(--text-3)', fontSize: 10 }} axisLine={false} tickLine={false} width={24} allowDecimals={false} />
            <Tooltip contentStyle={{ background: 'var(--bg-3)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
            {topJurs.map((v, i) => (
              <Line key={v.jurisdiction} type="monotone" dataKey={v.jurisdiction}
                stroke={JUR_COLORS[i % JUR_COLORS.length]} strokeWidth={2}
                dot={false} activeDot={{ r: 4 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Per-jurisdiction cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
        {velocity.map((v, i) => {
          const ts = TREND_STYLE[v.trend] || TREND_STYLE.stable
          const Icon = ts.icon
          const pct = Math.abs(Math.round(v.acceleration * 100))
          const barData = v.windows.slice(-6).map(w => ({ label: w.label, count: w.count }))
          const maxCount = Math.max(...barData.map(b => b.count), 1)

          return (
            <div key={v.jurisdiction} className="card" style={{ padding: '12px 14px' }}>
              <div className="flex items-center gap-2" style={{ marginBottom: 10 }}>
                <Badge level={v.jurisdiction}>{v.jurisdiction}</Badge>
                <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{v.total_documents} total</span>
                <Icon size={13} style={{ color: ts.color }} />
                <span style={{ fontSize: 11, color: ts.color, fontFamily: 'var(--font-mono)' }}>
                  {v.trend === 'stable' ? 'stable' : `${pct}% ${v.trend === 'accelerating' ? '↑' : '↓'}`}
                </span>
              </div>
              {/* Mini bar chart — last 6 windows */}
              <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 36 }}>
                {barData.map((b, bi) => (
                  <div key={bi} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <div style={{
                      width: '100%',
                      height: Math.max(2, Math.round((b.count / maxCount) * 30)),
                      background: bi === barData.length - 1 ? ts.color : 'var(--accent-dim)',
                      borderRadius: '2px 2px 0 0',
                      transition: 'height 0.3s',
                    }} />
                    <div style={{ fontSize: 8, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', writingMode: 'vertical-lr', transform: 'rotate(180deg)', lineHeight: 1 }}>
                      {b.label.split(' ')[0]}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-3)' }}>
                {v.recent_count} this month · {v.prior_count} six months ago
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Heatmap tab ───────────────────────────────────────────────────────────────

function HeatmapTab({ heatmap }) {
  const [filter, setFilter] = useState('')

  if (!heatmap.length) return (
    <div style={{ color: 'var(--text-3)', fontSize: 13, fontStyle: 'italic' }}>
      No impact area data yet — run summarisation to populate.
    </div>
  )

  const filtered = filter
    ? heatmap.filter(h => h.area.toLowerCase().includes(filter.toLowerCase()))
    : heatmap

  const maxScore = heatmap[0]?.activity_score || 1

  return (
    <div>
      <input
        placeholder="Filter impact areas…"
        value={filter}
        onChange={e => setFilter(e.target.value)}
        style={{ marginBottom: 16, width: 280 }}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {filtered.map((h, i) => {
          const intensity = h.activity_score / maxScore
          const bg = `rgba(26,94,171,${0.05 + intensity * 0.25})`
          const bar = Math.round(intensity * 100)
          const urg = h.urgency_counts || {}

          return (
            <div key={h.area} style={{ padding: '10px 14px', background: bg, border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
              <div className="flex items-center gap-3">
                <div style={{ width: 4, alignSelf: 'stretch', background: `rgba(26,94,171,${0.3 + intensity * 0.7})`, borderRadius: 2, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-2" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 500 }}>{h.area}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{h.total} total · {h.recent} this month</span>
                  </div>
                  {/* Activity bar */}
                  <div style={{ height: 4, background: 'var(--bg-4)', borderRadius: 2, overflow: 'hidden', marginBottom: 6 }}>
                    <div style={{ height: '100%', width: `${bar}%`, background: 'var(--accent)', borderRadius: 2 }} />
                  </div>
                  <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
                    {Object.entries(urg).filter(([, v]) => v > 0).map(([k, v]) => (
                      <span key={k} style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: URGENCY_COLORS[k] || 'var(--text-3)' }}>
                        {k}: {v}
                      </span>
                    ))}
                    {h.top_jurisdictions?.length > 0 && (
                      <span style={{ fontSize: 10, color: 'var(--text-3)', marginLeft: 'auto' }}>
                        {h.top_jurisdictions.slice(0,3).map(([j]) => j).join(' · ')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Alerts tab ────────────────────────────────────────────────────────────────

function AlertsTab({ alerts }) {
  if (!alerts.length) return (
    <div style={{ color: 'var(--green)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, padding: '16px 0' }}>
      <Zap size={16} /> No acceleration alerts — regulatory activity is within normal range.
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {alerts.map((a, i) => {
        const isRed = a.severity === 'Critical'
        const color = isRed ? 'var(--red)' : 'var(--orange)'
        const bg    = isRed ? 'rgba(224,82,82,0.07)' : 'rgba(224,131,74,0.07)'

        return (
          <div key={i} style={{ padding: '14px 16px', background: bg, border: `1px solid ${color}44`, borderRadius: 'var(--radius)' }}>
            <div className="flex items-start gap-3">
              <AlertTriangle size={14} style={{ color, flexShrink: 0, marginTop: 2 }} />
              <div style={{ flex: 1 }}>
                <div className="flex items-center gap-2" style={{ marginBottom: 4 }}>
                  <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color, textTransform: 'uppercase' }}>
                    {a.severity}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    {a.type === 'jurisdiction' ? 'Jurisdiction' : 'Impact Area'}
                  </span>
                  <Badge level={a.jurisdiction || a.label}>{a.label}</Badge>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, margin: 0 }}>
                  {a.message}
                </p>
                {a.acceleration !== undefined && (
                  <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                    acceleration: +{Math.round(a.acceleration * 100)}% vs 6 months ago
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function TrendsEmptyState() {
  return (
    <div style={{ maxWidth: 480 }}>
      <TrendingUp size={32} style={{ color: 'var(--accent)', marginBottom: 16 }} />
      <h3 style={{ fontWeight: 400, fontSize: '1.1rem', marginBottom: 12 }}>No trend data yet</h3>
      <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.7 }}>
        Trends are computed from your document database. Fetch documents first with{' '}
        <strong>Run Agents</strong>, then return here to see velocity charts, impact area
        activity, and acceleration alerts — all without any additional API calls.
      </p>
      <a href="/run" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 12,
        padding: '7px 14px', background: 'var(--accent)', color: 'var(--bg)',
        borderRadius: 'var(--radius)', fontSize: 13, fontWeight: 500, textDecoration: 'none' }}>
        Go to Run Agents →
      </a>
    </div>
  )
}
