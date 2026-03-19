import { useState, useEffect, useRef } from 'react'
import { CalendarDays, Globe, RefreshCw, Circle, ChevronRight, ExternalLink } from 'lucide-react'
import { Spinner, EmptyState, SectionHeader, Badge } from '../components.jsx'
import { useNavigate } from 'react-router-dom'

const timelineApi = {
  get: (params={}) => fetch(`/api/timeline?${new URLSearchParams(params)}`).then(r=>r.json()),
}

const JUR_COLORS = {
  EU:'#4f8fe0',Federal:'#e07c4f',PA:'#52a878',GB:'#a06bd4',
  CA:'#d4a843',JP:'#e05252',AU:'#4fd4c8',SG:'#d44fa0',BR:'#8fe04f',
}
const JURISDICTIONS = ['','EU','Federal','GB','CA','JP','AU','SG','BR']

const EVENT_TYPE_LABELS = {
  milestone:'Milestone',effective:'Effective Date',proposed:'Proposed',
  final:'Final Rule',guidance:'Guidance',enforcement:'Enforcement',
  implementing_act:'Implementing Act',introduced:'Introduced',
  anticipated:'Anticipated',amendment:'Amendment',
}

function EventCard({event, onClick, isSelected}) {
  const cfg   = event._config || {}
  const color = cfg.color || '#607070'
  const today = new Date().toISOString().slice(0,10)
  const isFuture = event.date > today
  const isAnt    = event.status === 'anticipated'

  return (
    <div
      onClick={() => onClick(event)}
      className="card card-hover"
      style={{
        padding:'10px 14px',
        borderLeft:`3px solid ${color}`,
        background: isSelected ? 'var(--bg-3)' : 'var(--bg-2)',
        opacity: isAnt ? 0.75 : 1,
        cursor:'pointer',
        borderColor: isSelected ? 'var(--accent-dim)' : 'var(--border)',
        borderLeftColor: color,
      }}
    >
      <div className="flex items-center gap-3">
        <div style={{minWidth:80,fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)'}}>
          {event.date?.slice(0,10)}
        </div>
        <div style={{flex:1,minWidth:0}}>
          <div style={{fontSize:12,fontWeight:500,lineHeight:1.4}} className="truncate">
            {event.event}
          </div>
          <div style={{fontSize:10,color:'var(--text-3)',fontFamily:'var(--font-mono)',marginTop:1}}>
            {event.regulation_name} · {event.jurisdiction}
          </div>
        </div>
        <div style={{
          fontSize:10,fontFamily:'var(--font-mono)',
          color, background:`${color}18`,
          padding:'2px 7px',borderRadius:3,flexShrink:0,
        }}>
          {EVENT_TYPE_LABELS[event.event_type]||event.event_type}
          {isAnt && ' •'}
        </div>
      </div>
    </div>
  )
}

function YearGroup({year, events, onSelect, selected}) {
  const today = new Date().toISOString().slice(0,10)
  const currentYear = new Date().getFullYear()
  const isNow = parseInt(year) === currentYear
  const isFuture = parseInt(year) > currentYear

  return (
    <div style={{marginBottom:24}}>
      <div className="flex items-center gap-3" style={{marginBottom:8}}>
        <div style={{
          fontSize:13,fontWeight:500,
          color: isNow ? 'var(--accent)' : isFuture ? 'var(--text-3)' : 'var(--text-2)',
          fontFamily:'var(--font-mono)',
        }}>
          {year}
          {isNow && <span style={{marginLeft:8,fontSize:10,color:'var(--accent)',fontWeight:400}}>
            ← TODAY
          </span>}
          {isFuture && <span style={{marginLeft:8,fontSize:10,color:'var(--text-3)',fontWeight:400}}>
            (anticipated)
          </span>}
        </div>
        <div style={{flex:1,height:1,background:'var(--border)'}}/>
        <span style={{fontSize:10,color:'var(--text-3)',fontFamily:'var(--font-mono)'}}>
          {events.length}
        </span>
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:5}}>
        {events.map((e,i) => (
          <EventCard
            key={`${e.regulation_id}-${e.date}-${i}`}
            event={e}
            onClick={onSelect}
            isSelected={selected?.regulation_id===e.regulation_id && selected?.date===e.date}
          />
        ))}
      </div>
    </div>
  )
}

export default function Timeline() {
  const [data,        setData]        = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [selected,    setSelected]    = useState(null)
  const [jurisdiction,setJur]         = useState('')
  const [typeFilter,  setTypeFilter]  = useState(new Set())
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (jurisdiction) params.jurisdiction = jurisdiction
      const d = await timelineApi.get(params)
      setData(d)
      // Attach config to each event
      if (d.events) {
        d.events.forEach(e => {
          e._config = (d.event_type_config||{})[e.event_type] || {color:'#607070'}
        })
      }
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [jurisdiction])

  // Group events by year
  const events = (data?.events || []).filter(e =>
    typeFilter.size === 0 || typeFilter.has(e.event_type)
  )

  const byYear = {}
  events.forEach(e => {
    const yr = (e.date||'').slice(0,4) || 'Unknown'
    if (!byYear[yr]) byYear[yr] = []
    byYear[yr].push(e)
  })

  const years = Object.keys(byYear).sort()
  const uniqueTypes = [...new Set((data?.events||[]).map(e=>e.event_type))].sort()

  const toggleType = (t) => {
    setTypeFilter(prev => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }

  return (
    <div style={{display:'flex',height:'100%',overflow:'hidden'}}>
      {/* Main timeline */}
      <div style={{flex:1,overflow:'auto',padding:'24px 28px'}}>
        <div style={{maxWidth:760,margin:'0 auto'}}>
          <SectionHeader
            title="Regulatory Timeline"
            subtitle={data ? `${data.total} events` : ''}
            action={
              <button className="btn-ghost btn-sm" onClick={load} disabled={loading}>
                <RefreshCw size={12} style={{animation:loading?'spin 1s linear infinite':'none'}}/>
                Refresh
              </button>
            }
          />

          {/* Filters */}
          <div className="flex gap-3" style={{marginBottom:20,flexWrap:'wrap'}}>
            <select value={jurisdiction} onChange={e=>setJur(e.target.value)} style={{width:140,fontSize:12}}>
              {JURISDICTIONS.map(j=><option key={j} value={j}>{j||'All Jurisdictions'}</option>)}
            </select>
            {uniqueTypes.map(t => {
              const cfg = (data?.event_type_config||{})[t]||{color:'#607070',label:t}
              const active = typeFilter.size===0||typeFilter.has(t)
              return (
                <button key={t} onClick={()=>toggleType(t)} style={{
                  fontSize:10,fontFamily:'var(--font-mono)',padding:'3px 8px',
                  border:`1px solid ${active?cfg.color:'var(--border)'}`,
                  borderRadius:3,cursor:'pointer',
                  color:active?cfg.color:'var(--text-3)',
                  background:active?`${cfg.color}18`:'transparent',
                }}>
                  {cfg.label||EVENT_TYPE_LABELS[t]||t}
                </button>
              )
            })}
          </div>

          {loading ? (
            <div style={{display:'flex',justifyContent:'center',padding:40}}><Spinner/></div>
          ) : events.length === 0 ? (
            <EmptyState icon={CalendarDays} title="No timeline events" message="Timeline events come from baseline milestones, live documents, and horizon items."/>
          ) : (
            years.map(yr => (
              <YearGroup
                key={yr}
                year={yr}
                events={byYear[yr]}
                onSelect={setSelected}
                selected={selected}
              />
            ))
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selected && (
        <div style={{
          width:320,flexShrink:0,borderLeft:'1px solid var(--border)',
          overflow:'auto',padding:'20px 18px',background:'var(--bg)',
        }}>
          <div style={{marginBottom:14}}>
            <div style={{
              fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)',
              textTransform:'uppercase',marginBottom:4,
            }}>
              {EVENT_TYPE_LABELS[selected.event_type]||selected.event_type}
              {selected.status==='anticipated'&&' (Anticipated)'}
            </div>
            <div style={{fontSize:14,fontWeight:500,lineHeight:1.4,marginBottom:6}}>
              {selected.event}
            </div>
            <div style={{fontSize:12,color:'var(--text-3)'}}>
              {selected.regulation_name} · {selected.jurisdiction}
            </div>
          </div>

          <div style={{fontSize:12,color:'var(--text-3)',fontFamily:'var(--font-mono)',
                       marginBottom:12}}>
            {selected.date}
          </div>

          {selected.plain_english && (
            <div style={{fontSize:12,color:'var(--text-2)',lineHeight:1.6,marginBottom:12,
                         borderTop:'1px solid var(--border)',paddingTop:12}}>
              {selected.plain_english}
            </div>
          )}

          {selected.stage && (
            <div style={{fontSize:11,color:'var(--text-3)',marginBottom:8}}>
              Stage: {selected.stage}
            </div>
          )}

          <div style={{display:'flex',flexDirection:'column',gap:6,marginTop:12}}>
            {selected.url && (
              <a href={selected.url} target="_blank" rel="noreferrer"
                 className="btn-secondary btn-sm" style={{justifyContent:'center'}}>
                <ExternalLink size={11}/> View source
              </a>
            )}
            <button className="btn-ghost btn-sm" style={{justifyContent:'center'}}
              onClick={()=>navigate('/ask')}>
              Ask ARIS about this →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
