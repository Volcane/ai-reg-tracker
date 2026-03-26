import { useState, useEffect, useCallback } from 'react'
import {
  Shield, RefreshCw, ExternalLink, AlertTriangle, Scale,
  FileText, Globe, Filter, ChevronDown, ChevronUp, Sparkles,
} from 'lucide-react'
import { Spinner, EmptyState, SectionHeader, Badge, DomainFilter, ViewHeader } from '../components.jsx'
import { useNavigate } from 'react-router-dom'

const enfApi = {
  list:  (p={}) => fetch(`/api/enforcement?${new URLSearchParams(p)}`).then(r=>r.json()),
  stats: ()     => fetch('/api/enforcement/stats').then(r=>r.json()),
  fetch: (days) => fetch(`/api/enforcement/fetch?days=${days}`,{method:'POST'}).then(r=>r.json()),
}

const SOURCE_META = {
  ftc:                     { label:'FTC',     color:'#4f8fe0', agency:'Federal Trade Commission'               },
  sec:                     { label:'SEC',     color:'#a06bd4', agency:'Securities & Exchange Commission'       },
  cfpb:                    { label:'CFPB',    color:'#52a878', agency:'Consumer Financial Protection Bureau'   },
  eeoc:                    { label:'EEOC',    color:'#d4a843', agency:'Equal Employment Opportunity Commission' },
  doj:                     { label:'DOJ',     color:'#e0834a', agency:'Department of Justice'                  },
  ico:                     { label:'ICO',     color:'#4fd4c8', agency:"Information Commissioner's Office (UK)" },
  courtlistener:           { label:'Courts',  color:'#e05252', agency:'Federal Courts (CourtListener)'         },
  google_news_enforcement: { label:'News',    color:'#6b9fd4', agency:'Various (via Google News)'              },
  regulatory_oversight:    { label:'RegOvr',  color:'#c47a3a', agency:'Regulatory Oversight (Troutman Pepper)' },
  courthouse_news:         { label:'CNS',     color:'#7a6bc4', agency:'Courthouse News Service'                },
}

// Strip HTML tags and decode entities from Google News RSS summaries
function stripHtml(html) {
  if (!html) return ''
  // Remove all tags
  let text = html.replace(/<[^>]*>/g, ' ')
  // Decode common entities
  text = text.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ')
  // Collapse whitespace
  return text.replace(/\s+/g, ' ').trim()
}

// Cluster items by story — items are in the same cluster if their titles share
// enough common words (ignoring stopwords and source attribution after " - ").
function clusterItems(items) {
  const stopwords = new Set(['the','a','an','in','of','to','and','for','is','are',
    'was','were','on','at','by','with','from','that','this','it','as','or','be',
    'its','their','has','have','had','will','can','not','but','also','about',
    'over','into','than','after','before','found','finds','find','jury','judge'])

  function keywords(title) {
    // Remove source attribution like "- Reuters" or "- BBC News" at end
    const t = title.replace(/\s[-–]\s[\w\s]+$/, '').toLowerCase()
    return new Set(t.split(/\W+/).filter(w => w.length > 3 && !stopwords.has(w)))
  }

  function similarity(a, b) {
    const ka = keywords(a), kb = keywords(b)
    const shared = [...ka].filter(w => kb.has(w)).length
    const denom = Math.min(ka.size, kb.size)
    return denom === 0 ? 0 : shared / denom
  }

  const clusters = []
  const used = new Set()

  items.forEach((item, i) => {
    if (used.has(i)) return
    const cluster = [item]
    used.add(i)
    items.forEach((other, j) => {
      if (j <= i || used.has(j)) return
      if (similarity(item.title || '', other.title || '') >= 0.45) {
        cluster.push(other)
        used.add(j)
      }
    })
    clusters.push(cluster)
  })

  return clusters
}

const TYPE_META = {
  enforcement: { label:'Enforcement', icon:Shield,       color:'var(--red)'    },
  litigation:  { label:'Litigation',  icon:Scale,        color:'var(--orange)' },
  opinion:     { label:'Opinion',     icon:FileText,     color:'var(--accent)' },
  settlement:  { label:'Settlement',  icon:Shield,       color:'var(--green)'  },
  guidance:    { label:'Guidance',    icon:FileText,     color:'var(--text-3)' },
}

const OUTCOME_COLORS = {
  fine:        'var(--red)',
  settlement:  'var(--green)',
  injunction:  'var(--orange)',
  pending:     'var(--yellow)',
  opinion:     'var(--accent)',
  enforcement: 'var(--orange)',
  dismissed:   'var(--text-3)',
}

const JURISDICTIONS = ['','Federal','GB','EU']
const ACTION_TYPES  = ['','enforcement','litigation','opinion','settlement','guidance']
const SOURCES       = ['','ftc','sec','cfpb','eeoc','doj','ico','courtlistener']

// ── Action card ───────────────────────────────────────────────────────────────

function ActionCard({ action, onSelect, isSelected, compact=false }) {
  const srcMeta  = SOURCE_META[action.source] || { label: action.source, color:'#607070' }
  const typeCfg  = TYPE_META[action.action_type] || { label: action.action_type, icon: FileText, color:'var(--text-3)' }
  const TypeIcon = typeCfg.icon

  return (
    <div
      onClick={() => onSelect(action)}
      className="card card-hover"
      style={{
        padding:    compact ? '7px 12px' : '11px 14px',
        cursor:     'pointer',
        borderLeft: `3px solid ${srcMeta.color}`,
        background: isSelected ? 'var(--bg-3)' : 'var(--bg-2)',
        marginBottom: compact ? 3 : 6,
      }}
    >
      <div className="flex items-center gap-3">
        <div style={{
          fontSize:10, fontFamily:'var(--font-mono)', fontWeight:700,
          color:srcMeta.color, minWidth:44, textAlign:'center',
          background:`${srcMeta.color}18`, padding:'2px 5px', borderRadius:3, flexShrink:0,
        }}>
          {srcMeta.label}
        </div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ fontSize:compact?11:12, fontWeight:500, lineHeight:1.4 }} className="truncate">
            {action.title}
          </div>
          {!compact && (
            <div style={{ fontSize:10, color:'var(--text-3)', fontFamily:'var(--font-mono)', marginTop:1 }}>
              {action.agency}
              {action.respondent && <span> · {action.respondent.slice(0,40)}</span>}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1" style={{
          fontSize:10, fontFamily:'var(--font-mono)', color:typeCfg.color, flexShrink:0,
        }}>
          <TypeIcon size={10} />
          {!compact && typeCfg.label}
        </div>
        {action.penalty_amount && (
          <div style={{
            fontSize:10, fontFamily:'var(--font-mono)', color:'var(--red)',
            background:'rgba(224,82,82,0.08)', padding:'2px 6px', borderRadius:3, flexShrink:0,
          }}>
            {action.penalty_amount.slice(0,20)}
          </div>
        )}
        <div style={{ fontSize:10, color:'var(--text-3)', fontFamily:'var(--font-mono)', flexShrink:0 }}>
          {action.published_date?.slice(0,10)}
        </div>
      </div>
    </div>
  )
}

// ── Story group — collapses N similar articles behind one header ──────────────

function StoryGroup({ cluster, onSelect, selectedId }) {
  const [open, setOpen] = useState(false)

  const lead      = cluster[0]
  const count     = cluster.length
  const srcMeta   = SOURCE_META[lead.source] || { label: lead.source, color:'#607070' }
  const typeCfg   = TYPE_META[lead.action_type] || { label: lead.action_type, icon:FileText, color:'var(--text-3)' }
  const TypeIcon  = typeCfg.icon
  const isAnySelected = cluster.some(a => a.id === selectedId)

  // Pick a clean title — strip " - Source Name" attribution from lead
  const cleanTitle = lead.title?.replace(/\s[-–]\s[\w\s.]+$/, '') || lead.title

  if (count === 1) {
    return <ActionCard action={lead} onSelect={onSelect} isSelected={lead.id === selectedId} />
  }

  // Collect unique sources in the cluster
  const srcLabels = [...new Set(cluster.map(a =>
    (SOURCE_META[a.source] || { label: a.source }).label
  ))].join(', ')

  // Best penalty from the cluster
  const penalty = cluster.find(a => a.penalty_amount)?.penalty_amount

  return (
    <div style={{ marginBottom:6 }}>
      {/* Group header — acts as primary card */}
      <div
        className="card card-hover"
        style={{
          padding:    '11px 14px',
          cursor:     'pointer',
          borderLeft: `3px solid ${srcMeta.color}`,
          background: isAnySelected ? 'var(--bg-3)' : 'var(--bg-2)',
        }}
      >
        <div className="flex items-center gap-3" onClick={() => onSelect(lead)}>
          {/* Source count badge */}
          <div style={{
            fontSize:10, fontFamily:'var(--font-mono)', fontWeight:700,
            color:srcMeta.color, minWidth:44, textAlign:'center',
            background:`${srcMeta.color}18`, padding:'2px 5px', borderRadius:3, flexShrink:0,
          }}>
            {srcMeta.label}
          </div>

          {/* Title + source count */}
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ fontSize:12, fontWeight:500, lineHeight:1.4 }} className="truncate">
              {cleanTitle}
            </div>
            <div style={{ fontSize:10, color:'var(--text-3)', fontFamily:'var(--font-mono)', marginTop:1 }}>
              {lead.agency} · {srcLabels}
            </div>
          </div>

          <div className="flex items-center gap-1" style={{
            fontSize:10, fontFamily:'var(--font-mono)', color:typeCfg.color, flexShrink:0,
          }}>
            <TypeIcon size={10} />{typeCfg.label}
          </div>

          {penalty && (
            <div style={{
              fontSize:10, fontFamily:'var(--font-mono)', color:'var(--red)',
              background:'rgba(224,82,82,0.08)', padding:'2px 6px', borderRadius:3, flexShrink:0,
            }}>
              {penalty.slice(0,20)}
            </div>
          )}

          <div style={{ fontSize:10, color:'var(--text-3)', fontFamily:'var(--font-mono)', flexShrink:0 }}>
            {lead.published_date?.slice(0,10)}
          </div>
        </div>

        {/* Expand toggle */}
        <div
          onClick={e => { e.stopPropagation(); setOpen(o => !o) }}
          style={{
            marginTop:6, paddingTop:5, borderTop:'1px solid var(--border)',
            display:'flex', alignItems:'center', gap:4, cursor:'pointer',
            fontSize:10, color:'var(--text-3)', fontFamily:'var(--font-mono)',
            userSelect:'none',
          }}
        >
          {open ? <ChevronUp size={10}/> : <ChevronDown size={10}/>}
          {open ? 'Hide' : `${count - 1} more article${count > 2 ? 's' : ''} about this story`}
        </div>
      </div>

      {/* Expanded articles */}
      {open && (
        <div style={{
          marginLeft:16, marginTop:2,
          borderLeft:'2px solid var(--border)', paddingLeft:8,
        }}>
          {cluster.slice(1).map(a => (
            <ActionCard key={a.id} action={a} onSelect={onSelect}
                        isSelected={a.id === selectedId} compact />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Detail panel ──────────────────────────────────────────────────────────────

function DetailPanel({ action, onClose }) {
  const navigate = useNavigate()
  if (!action) return null

  const src     = SOURCE_META[action.source] || { label: action.source, color:'#607070', agency:'' }
  const typeCfg = TYPE_META[action.action_type] || { label: action.action_type, icon:FileText, color:'var(--text-3)' }
  const TypeIcon = typeCfg.icon

  return (
    <div style={{
      width:320, flexShrink:0, borderLeft:'1px solid var(--border)',
      overflow:'auto', padding:'20px 18px', background:'var(--bg)',
    }}>
      {/* Source + type header */}
      <div className="flex items-center gap-2" style={{ marginBottom:14 }}>
        <div style={{
          fontSize:11, fontFamily:'var(--font-mono)', fontWeight:700,
          color:src.color, background:`${src.color}18`,
          padding:'3px 8px', borderRadius:3,
        }}>
          {src.label}
        </div>
        <div className="flex items-center gap-1" style={{
          fontSize:11, fontFamily:'var(--font-mono)', color:typeCfg.color,
        }}>
          <TypeIcon size={11}/> {typeCfg.label}
        </div>
        <div style={{ marginLeft:'auto' }}>
          <button className="btn-icon" onClick={onClose}
            style={{ fontSize:13, color:'var(--text-3)' }}>✕</button>
        </div>
      </div>

      <div style={{ fontWeight:500, fontSize:13, lineHeight:1.4, marginBottom:8 }}>
        {action.title}
      </div>

      {/* Meta grid */}
      <div style={{ display:'grid', gridTemplateColumns:'auto 1fr', gap:'6px 12px',
                    fontSize:12, marginBottom:14 }}>
        {action.agency && <>
          <span style={{ color:'var(--text-3)' }}>Agency</span>
          <span style={{ color:'var(--text-2)' }}>{action.agency}</span>
        </>}
        {action.respondent && <>
          <span style={{ color:'var(--text-3)' }}>Respondent</span>
          <span style={{ color:'var(--text-2)' }}>{action.respondent}</span>
        </>}
        {action.jurisdiction && <>
          <span style={{ color:'var(--text-3)' }}>Jurisdiction</span>
          <span style={{ color:'var(--text-2)' }}>{action.jurisdiction}</span>
        </>}
        {action.published_date && <>
          <span style={{ color:'var(--text-3)' }}>Date</span>
          <span style={{ color:'var(--text-2)' }}>{action.published_date.slice(0,10)}</span>
        </>}
        {action.outcome && <>
          <span style={{ color:'var(--text-3)' }}>Outcome</span>
          <span style={{
            color: OUTCOME_COLORS[action.outcome] || 'var(--text-2)',
            fontFamily:'var(--font-mono)', fontSize:11,
          }}>{action.outcome}</span>
        </>}
        {action.penalty_amount && <>
          <span style={{ color:'var(--text-3)' }}>Penalty</span>
          <span style={{ color:'var(--red)', fontWeight:500 }}>{action.penalty_amount}</span>
        </>}
      </div>

      {/* Summary */}
      {action.summary && (
        <div style={{
          fontSize:12, color:'var(--text-2)', lineHeight:1.6,
          borderTop:'1px solid var(--border)', paddingTop:12, marginBottom:12,
        }}>
          {stripHtml(action.summary)}
        </div>
      )}

      {/* Concepts */}
      {action.ai_concepts?.length > 0 && (
        <div style={{ marginBottom:12 }}>
          <div style={{ fontSize:10, fontFamily:'var(--font-mono)', color:'var(--text-3)',
                        textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:5 }}>
            AI Concepts
          </div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
            {action.ai_concepts.map(c => (
              <span key={c} style={{
                fontSize:10, fontFamily:'var(--font-mono)',
                background:'var(--bg-3)', border:'1px solid var(--border)',
                padding:'2px 7px', borderRadius:3,
                color:'var(--accent)',
              }}>
                {c.replace(/_/g,' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Related regulations */}
      {action.related_regs?.length > 0 && (
        <div style={{ marginBottom:14 }}>
          <div style={{ fontSize:10, fontFamily:'var(--font-mono)', color:'var(--text-3)',
                        textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:5 }}>
            Related Regulations
          </div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
            {action.related_regs.map(r => (
              <span key={r} style={{
                fontSize:10, fontFamily:'var(--font-mono)',
                background:'var(--bg-3)', border:'1px solid var(--border)',
                padding:'2px 7px', borderRadius:3, color:'var(--text-2)',
              }}>
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
        {action.url && (
          <a href={action.url} target="_blank" rel="noreferrer"
             className="btn-secondary btn-sm" style={{ justifyContent:'center' }}>
            <ExternalLink size={11}/> View source
          </a>
        )}
        <button className="btn-ghost btn-sm" style={{ justifyContent:'center' }}
          onClick={()=>navigate('/ask')}>
          <Sparkles size={11} style={{ color:'var(--accent)' }}/>
          Ask ARIS about this case →
        </button>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Enforcement() {
  const [domain, setDomain] = useState(() => {
    try { return localStorage.getItem('aris_domain_enforcement') ?? null } catch { return null }
  })
  const handleDomainChange = (d) => {
    setDomain(d)
    try { localStorage.setItem('aris_domain_enforcement', d ?? '') } catch {}
  }
  const [items,       setItems]       = useState([])
  const [stats,       setStats]       = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [fetching,    setFetching]    = useState(false)
  const [selected,    setSelected]    = useState(null)
  const [jurisdiction,setJur]         = useState('')
  const [source,      setSource]      = useState('')
  const [actionType,  setActionType]  = useState('')
  const [groupSimilar,setGroupSimilar]= useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = { days:365, limit:200 }
      if (jurisdiction) params.jurisdiction = jurisdiction
      if (source)       params.source       = source
      if (actionType)   params.action_type  = actionType
      const [data, s] = await Promise.all([
        enfApi.list(params),
        enfApi.stats().catch(()=>null),
      ])
      setItems(data.items || [])
      setStats(s)
    } finally { setLoading(false) }
  }, [jurisdiction, source, actionType])

  useEffect(()=>{ load() },[load])

  const triggerFetch = async () => {
    setFetching(true)
    try {
      await enfApi.fetch(90)
      // Poll for new data after a short delay
      setTimeout(()=>{ load(); setFetching(false) }, 5000)
    } catch { setFetching(false) }
  }

  // Apply domain filter client-side
  const visibleItems = domain
    ? items.filter(i => i.domain === domain || i.domain === 'both')
    : items

  // Cluster into story groups if groupSimilar is on
  const displayClusters = groupSimilar ? clusterItems(visibleItems) : visibleItems.map(i => [i])

  const isEmpty = !loading && visibleItems.length === 0

  // Source breakdown for sidebar
  const bySource = stats?.by_source || {}

  return (
    <div style={{ display:'flex', height:'100%', overflow:'hidden' }}>

      {/* ── Sidebar: source breakdown ── */}
      <div style={{
        width:220, flexShrink:0, borderRight:'1px solid var(--border)',
        overflow:'auto', padding:'20px 0', background:'var(--bg-2)',
      }}>
        <div style={{ fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-3)',
                      textTransform:'uppercase', letterSpacing:'0.06em',
                      padding:'0 16px 10px' }}>
          Sources
        </div>

        {/* All */}
        <div
          onClick={()=>setSource('')}
          style={{
            padding:'7px 16px', cursor:'pointer', fontSize:12,
            background: source==='' ? 'var(--bg-3)' : 'transparent',
            borderLeft: source==='' ? '3px solid var(--accent)' : '3px solid transparent',
          }}
        >
          <div className="flex items-center justify-between">
            <span style={{ fontWeight: source===''?500:400 }}>All Sources</span>
            <span style={{ fontSize:10, fontFamily:'var(--font-mono)',
                           color:'var(--text-3)' }}>{stats?.total||0}</span>
          </div>
        </div>

        {Object.entries(SOURCE_META).map(([key, meta]) => {
          const count = bySource[key] || 0
          return (
            <div key={key} onClick={()=>setSource(key)}
              style={{
                padding:'7px 16px', cursor:'pointer', fontSize:12,
                background: source===key ? 'var(--bg-3)' : 'transparent',
                borderLeft: source===key ? `3px solid ${meta.color}` : '3px solid transparent',
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span style={{
                    fontSize:10, fontFamily:'var(--font-mono)', fontWeight:700,
                    color: meta.color,
                  }}>{meta.label}</span>
                  <span style={{ color: source===key?'var(--text)':'var(--text-2)',
                                  fontWeight:source===key?500:400, fontSize:11 }}>
                    {meta.agency.split(' ').slice(0,3).join(' ')}
                  </span>
                </div>
                {count>0 && (
                  <span style={{ fontSize:10, fontFamily:'var(--font-mono)',
                                 color:'var(--text-3)' }}>{count}</span>
                )}
              </div>
            </div>
          )
        })}

        <div style={{ borderTop:'1px solid var(--border)', margin:'10px 0', padding:'10px 16px 0' }}>
          <div style={{ fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-3)',
                        textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:8 }}>
            Setup
          </div>
          <div style={{ fontSize:11, color:'var(--text-3)', lineHeight:1.6 }}>
            Add <code style={{ background:'var(--bg-4)', padding:'1px 4px', borderRadius:2 }}>
            COURTLISTENER_KEY</code> to <code style={{ background:'var(--bg-4)', padding:'1px 4px', borderRadius:2 }}>
            keys.env</code> for higher court data rate limits.
            <a href="https://www.courtlistener.com/sign-in/" target="_blank" rel="noreferrer"
               style={{ color:'var(--accent)', display:'block', marginTop:4 }}>
              Free registration →
            </a>
          </div>
        </div>
      </div>

      {/* ── Main content ── */}
      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>

        {/* Header */}
        <div style={{ padding:'20px 24px 0', flexShrink:0 }}>
          <ViewHeader
            title="Enforcement & Litigation"
            subtitle={stats ? `${stats.total} actions tracked` : ''}
            domain={domain}
            onDomainChange={handleDomainChange}
            action={
              <button className="btn-secondary btn-sm" onClick={triggerFetch}
                      disabled={fetching}>
                <RefreshCw size={12} style={{
                  animation: fetching?'spin 1s linear infinite':'none'
                }}/>
                {fetching ? 'Fetching…' : 'Fetch Latest'}
              </button>
            }
          />

          {/* Filters */}
          <div className="flex gap-3 items-center"
               style={{ paddingBottom:12, borderBottom:'1px solid var(--border)',
                        flexWrap:'wrap', marginTop:8 }}>
            <select value={jurisdiction} onChange={e=>setJur(e.target.value)}
                    style={{ width:130, fontSize:12 }}>
              {JURISDICTIONS.map(j=><option key={j} value={j}>{j||'All Jurisdictions'}</option>)}
            </select>
            <select value={actionType} onChange={e=>setActionType(e.target.value)}
                    style={{ width:130, fontSize:12 }}>
              {ACTION_TYPES.map(t=><option key={t} value={t}>{t||'All Types'}</option>)}
            </select>

            {/* Group similar toggle */}
            <button
              onClick={() => setGroupSimilar(g => !g)}
              style={{
                display:'flex', alignItems:'center', gap:5,
                fontSize:11, fontFamily:'var(--font-mono)',
                padding:'3px 9px', borderRadius:4, cursor:'pointer', flexShrink:0,
                border: groupSimilar ? '1px solid var(--accent)' : '1px solid var(--border)',
                background: groupSimilar ? 'var(--accent-dim)' : 'var(--bg-3)',
                color: groupSimilar ? 'var(--accent)' : 'var(--text-3)',
              }}
              title={groupSimilar ? 'Showing grouped stories — click to see all articles' : 'Click to group similar stories'}
            >
              <Filter size={10}/>
              {groupSimilar ? 'Grouped' : 'All articles'}
            </button>

            <div style={{ marginLeft:'auto', fontSize:11, color:'var(--text-3)',
                          fontFamily:'var(--font-mono)' }}>
              {groupSimilar
                ? `${displayClusters.length} stories · ${visibleItems.length} articles`
                : `${visibleItems.length} articles`
              }
            </div>
          </div>
        </div>

        {/* List */}
        <div style={{ flex:1, overflow:'auto', padding:'12px 24px' }}>
          {loading ? (
            <div style={{ display:'flex', justifyContent:'center', padding:40 }}>
              <Spinner/>
            </div>
          ) : isEmpty ? (
            <div style={{ padding:'40px 0' }}>
              <EmptyState
                icon={Shield}
                title="No enforcement actions yet"
                message='Click "Fetch Latest" to pull AI-related enforcement actions from FTC, SEC, CFPB, EEOC, DOJ, ICO, and CourtListener.'
              />
            </div>
          ) : (
            displayClusters.map((cluster, idx) => (
              <StoryGroup
                key={cluster[0].id}
                cluster={cluster}
                onSelect={setSelected}
                selectedId={selected?.id}
              />
            ))
          )}
        </div>
      </div>

      {/* ── Detail panel ── */}
      {selected && (
        <DetailPanel action={selected} onClose={()=>setSelected(null)} />
      )}
    </div>
  )
}
