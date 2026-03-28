import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import {
  Network, ZoomIn, ZoomOut, Maximize2, RefreshCw,
  BookOpen, FileText, GitBranch, Link, Layers,
  AlertTriangle, X, ExternalLink, Sparkles,
  Search, ChevronDown, LayoutGrid,
} from 'lucide-react'
import { Spinner, EmptyState } from '../components.jsx'

// ── API ───────────────────────────────────────────────────────────────────────
const graphApi = {
  graph:       (p={}) => fetch(`/api/graph?${new URLSearchParams(p)}`).then(r=>r.json()),
  buildGraph:  ()     => fetch('/api/graph/build?force=true',{method:'POST'}).then(r=>r.json()),
  graphStatus: ()     => fetch('/api/graph/status').then(r=>r.json()),
}

// ── Colour palettes ───────────────────────────────────────────────────────────
const JUR = {
  EU:'#4f8fe0', Federal:'#e07c4f', PA:'#52a878', GB:'#9b6dd4',
  CA:'#d4a843', JP:'#e05252',      AU:'#3ec8c0', SG:'#d44fa0',
  BR:'#8fe04f', IN:'#e08c30',      KR:'#b07fe0', CO:'#52c8a8',
  IL:'#d4608f', NY:'#608fd4',      CA_STATE:'#c8d443', INTL:'#8898a8',
  default:'#5a7878',
}
const ECOL = {
  cross_ref:'#4d8fd4', genealogical:'#48b870', semantic:'#c8a030',
  document:'#6a8090',  conflict:'#d44040',     implements:'#48c870',
  amends:'#d47030',    supersedes:'#c05050',   version_of:'#8080a0',
}
const ELBL = {
  cross_ref:'Cross-reference', genealogical:'Genealogical',
  semantic:'Shared Concept',   document:'Document Link',
  conflict:'Conflict',         implements:'Implements',
  amends:'Amends',             supersedes:'Supersedes',
}

const LAYOUT_PRESETS = [
  { id:'default',  label:'Balanced',    charge:-280, linkDist:80  },
  { id:'spread',   label:'Spread out',  charge:-500, linkDist:130 },
  { id:'tight',    label:'Tight',       charge:-120, linkDist:45  },
  { id:'radial',   label:'Radial',      charge:-400, linkDist:100 },
]

// ── Degree map ────────────────────────────────────────────────────────────────
function degreeMap(nodes, edges) {
  const m = {}
  nodes.forEach(n => { m[n.id] = 0 })
  edges.forEach(e => {
    const s = e.source?.id ?? e.source
    const t = e.target?.id ?? e.target
    m[s] = (m[s]||0)+1; m[t] = (m[t]||0)+1
  })
  return m
}

// ── Tooltip helpers ───────────────────────────────────────────────────────────
function mkTip() {
  let el = document.getElementById('aris-g-tip')
  if (!el) {
    el = document.createElement('div')
    el.id = 'aris-g-tip'
    el.style.cssText='position:fixed;z-index:9999;pointer-events:none;'+
      'background:#0e1c1c;border:1px solid #243838;border-radius:8px;'+
      'padding:10px 13px;max-width:260px;font-family:system-ui,sans-serif;'+
      'box-shadow:0 6px 24px rgba(0,0,0,.65);display:none'
    document.body.appendChild(el)
  }
  return el
}
function showTip(html, x, y) {
  const el = mkTip()
  el.innerHTML = html
  el.style.display = 'block'
  const W=window.innerWidth, H=window.innerHeight
  el.style.left = (x+20+260>W ? x-270 : x+20)+'px'
  el.style.top  = Math.max(8, Math.min(y-14, H-160))+'px'
}
function hideTip() { const el=document.getElementById('aris-g-tip'); if(el) el.style.display='none' }
function rmTip()   { const el=document.getElementById('aris-g-tip'); if(el) el.remove() }

// ── Legend ────────────────────────────────────────────────────────────────────
function Legend({ edgeTypes, active, onToggle }) {
  return (
    <div style={{ position:'absolute', bottom:16, left:16, zIndex:10,
      background:'rgba(8,18,18,.92)', backdropFilter:'blur(6px)',
      border:'1px solid #1e3232', borderRadius:8, padding:'10px 14px', minWidth:162 }}>
      <div style={{ fontSize:10, fontFamily:'monospace', color:'#5a8080',
        textTransform:'uppercase', letterSpacing:'.07em', marginBottom:8 }}>
        Edge types
      </div>
      {edgeTypes.map(t => {
        const c = ECOL[t]||'#607070'
        return (
          <div key={t} onClick={()=>onToggle(t)} style={{
            display:'flex', alignItems:'center', gap:8, marginBottom:5,
            cursor:'pointer', opacity:active.has(t)?1:.22, transition:'opacity .15s' }}>
            <svg width={22} height={6} style={{flexShrink:0}}>
              <line x1={0} y1={3} x2={22} y2={3} stroke={c} strokeWidth={1.8}
                strokeDasharray={t==='conflict'?'4 2':t==='semantic'?'2 2':'none'}/>
            </svg>
            <span style={{ fontSize:11, color:'#9ab8b8' }}>{ELBL[t]||t}</span>
          </div>
        )
      })}
      <div style={{ borderTop:'1px solid #1e3232', marginTop:9, paddingTop:9 }}>
        {[['Baseline','ellipse'],['Document','rect']].map(([lbl,sh])=>(
          <div key={lbl} style={{ display:'flex', alignItems:'center', gap:7, marginBottom:4 }}>
            <div style={{ width:10, height:10,
              borderRadius:sh==='ellipse'?'50%':3,
              background:'#486060', border:'2px solid #1e3232', flexShrink:0 }}/>
            <span style={{ fontSize:11, color:'#9ab8b8' }}>{lbl}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Node detail panel ─────────────────────────────────────────────────────────
function NodeDetail({ node, allEdges, allNodes, onClose, onNavigate }) {
  if (!node) return null
  const nMap = {}
  allNodes.forEach(n => { nMap[n.id] = n })
  const connected = allEdges.filter(e => {
    const s = e.source?.id ?? e.source
    const t = e.target?.id ?? e.target
    return s === node.id || t === node.id
  })
  const byType = {}
  connected.forEach(e => { if (!byType[e.type]) byType[e.type]=[]; byType[e.type].push(e) })
  const jc = JUR[node.jurisdiction] || JUR.default

  return (
    <div style={{ position:'absolute', right:0, top:0, bottom:0, width:334, zIndex:20,
      background:'rgba(8,16,16,.97)', backdropFilter:'blur(8px)',
      borderLeft:'1px solid #1e3232', overflowY:'auto', padding:18,
      display:'flex', flexDirection:'column' }}>

      {/* header */}
      <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:14 }}>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          {node.node_type==='baseline'
            ? <BookOpen size={13} style={{color:'var(--accent)'}}/>
            : <FileText  size={13} style={{color:'#5a8080'}}/>}
          <span style={{ fontSize:10, fontFamily:'monospace', color:'#5a8080',
            textTransform:'uppercase', letterSpacing:'.06em' }}>
            {node.node_type}
          </span>
        </div>
        <button onClick={onClose} style={{ background:'none', border:'none',
          cursor:'pointer', color:'#5a8080', lineHeight:1, padding:2 }}>
          <X size={14}/>
        </button>
      </div>

      {/* jurisdiction + urgency */}
      <div style={{ display:'flex', alignItems:'center', gap:7, marginBottom:10 }}>
        <div style={{ width:9, height:9, borderRadius:'50%', background:jc, flexShrink:0 }}/>
        <span style={{ fontSize:11, color:'#6a9090', fontFamily:'monospace' }}>
          {node.jurisdiction||'—'}
        </span>
        {node.urgency && (
          <span style={{ fontSize:10, fontFamily:'monospace', fontWeight:600, marginLeft:4,
            color:node.urgency==='Critical'?'#e05252':node.urgency==='High'?'#e0834a':'#c8a030' }}>
            {node.urgency}
          </span>
        )}
      </div>

      {/* title */}
      <div style={{ fontWeight:600, fontSize:14, color:'#cce4e4', lineHeight:1.4, marginBottom:10 }}>
        {node.title||node.label}
      </div>

      {/* status */}
      {node.status && (
        <div style={{ fontSize:11, color:'#5a8080', lineHeight:1.4, marginBottom:12 }}>
          {node.status.slice(0,80)}{node.status.length>80?'…':''}
        </div>
      )}

      {/* overview */}
      {node.overview && (
        <div style={{ fontSize:12, color:'#7aa0a0', lineHeight:1.65,
          marginBottom:16, paddingBottom:14, borderBottom:'1px solid #1e3232' }}>
          {node.overview.slice(0,300)}{node.overview.length>300?'…':''}
        </div>
      )}

      {/* connection type counts */}
      <div style={{ display:'flex', gap:12, marginBottom:14, flexWrap:'wrap' }}>
        {Object.entries(byType).map(([t,arr])=>(
          <div key={t} style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:2 }}>
            <span style={{ fontSize:16, fontWeight:700, color:ECOL[t]||'#607070' }}>{arr.length}</span>
            <span style={{ fontSize:9, color:'#4a6868', fontFamily:'monospace',
              textTransform:'uppercase', letterSpacing:'.04em' }}>
              {(ELBL[t]||t).split(' ')[0]}
            </span>
          </div>
        ))}
        <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:2, marginLeft:'auto' }}>
          <span style={{ fontSize:16, fontWeight:700, color:'#688080' }}>{connected.length}</span>
          <span style={{ fontSize:9, color:'#4a6868', fontFamily:'monospace',
            textTransform:'uppercase', letterSpacing:'.04em' }}>Total</span>
        </div>
      </div>

      {/* connections by type */}
      <div style={{ fontSize:11, fontFamily:'monospace', color:'#4a6868',
        textTransform:'uppercase', letterSpacing:'.05em', marginBottom:10 }}>
        Connections
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:10, flex:1 }}>
        {Object.entries(byType).map(([type, arr])=>{
          const c = ECOL[type]||'#607070'
          return (
            <div key={type}>
              <div style={{ display:'flex', alignItems:'center', gap:5, marginBottom:5 }}>
                <div style={{ width:14, height:2, background:c, borderRadius:1, flexShrink:0 }}/>
                <span style={{ fontSize:10, color:c, fontFamily:'monospace',
                  textTransform:'uppercase', letterSpacing:'.04em' }}>
                  {ELBL[type]||type} ({arr.length})
                </span>
              </div>
              <div style={{ display:'flex', flexDirection:'column', gap:4,
                paddingLeft:8, borderLeft:`2px solid ${c}25` }}>
                {arr.slice(0,5).map((e,i)=>{
                  const s = e.source?.id ?? e.source
                  const t = e.target?.id ?? e.target
                  const other = nMap[s===node.id ? t : s]
                  return (
                    <div key={i} style={{ background:'#0c1a1a', border:'1px solid #192828',
                      borderLeft:`3px solid ${c}`, borderRadius:5, padding:'6px 9px' }}>
                      <div style={{ fontSize:12, color:'#b8d4d4', fontWeight:500,
                        marginBottom:e.evidence?3:0 }}>
                        {((other?.label||other?.title||'')+'')}
                      </div>
                      {e.concept && (
                        <div style={{ fontSize:10, color:'#4a7070', fontFamily:'monospace', marginBottom:2 }}>
                          {e.concept.replace(/_/g,' ')}
                        </div>
                      )}
                      {e.evidence && (
                        <div style={{ fontSize:11, color:'#5a8080', lineHeight:1.4, fontStyle:'italic' }}>
                          {e.evidence.slice(0,110)}{e.evidence.length>110?'…':''}
                        </div>
                      )}
                      {e.strength!=null && (
                        <div style={{ marginTop:5, height:2, background:'#192828', borderRadius:1 }}>
                          <div style={{ height:2, width:`${(e.strength||.5)*100}%`, background:c, borderRadius:1 }}/>
                        </div>
                      )}
                    </div>
                  )
                })}
                {arr.length>5 && <div style={{ fontSize:10, color:'#4a6868', paddingLeft:4 }}>+{arr.length-5} more</div>}
              </div>
            </div>
          )
        })}
      </div>

      {/* actions */}
      <div style={{ borderTop:'1px solid #1e3232', marginTop:16, paddingTop:14,
        display:'flex', flexDirection:'column', gap:7 }}>
        <button className="btn-secondary btn-sm" style={{ width:'100%', justifyContent:'center' }}
          onClick={()=>onNavigate&&onNavigate('/ask')}>
          <Sparkles size={12} style={{color:'var(--accent)'}}/> Ask ARIS about this
        </button>
        {node.url && (
          <a href={node.url} target="_blank" rel="noreferrer"
            style={{ display:'flex', alignItems:'center', gap:5, fontSize:11,
              color:'#4a8080', justifyContent:'center' }}>
            View source <ExternalLink size={10}/>
          </a>
        )}
      </div>
    </div>
  )
}

// ── Main view ─────────────────────────────────────────────────────────────────
export default function Graph({ navigate }) {
  const [graphData,    setGraphData]   = useState({ nodes:[], edges:[], meta:{} })
  const [loading,      setLoading]     = useState(true)
  const [building,     setBuilding]    = useState(false)
  const [ForceGraph,   setForceGraph]  = useState(null)
  const [selected,     setSelected]    = useState(null)
  const [hoveredId,    setHoveredId]   = useState(null)
  const [jurisdiction, setJur]         = useState('')
  const [search,       setSearch]      = useState('')
  const [preset,       setPreset]      = useState('default')
  const [showPresets,  setShowPresets] = useState(false)
  const [activeEdge,   setActiveEdge]  = useState(
    new Set(['cross_ref','genealogical','semantic','implements','document'])
  )
  const fgRef      = useRef(null)
  const wrapRef    = useRef(null)
  const [dims, setDims] = useState({ w:800, h:600 })

  // Load ForceGraph dynamically (it uses canvas internally)
  useEffect(() => {
    import('react-force-graph-2d').then(m => setForceGraph(()=>m.default))
  }, [])

  // Resize observer
  useEffect(() => {
    if (!wrapRef.current) return
    const ro = new ResizeObserver(([e]) => {
      setDims({ w: e.contentRect.width, h: e.contentRect.height })
    })
    ro.observe(wrapRef.current)
    return () => ro.disconnect()
  }, [])

  // Load graph data
  const loadGraph = useCallback(async () => {
    setLoading(true)
    try {
      const p = {}; if (jurisdiction) p.jurisdiction = jurisdiction
      const d = await graphApi.graph(p)
      setGraphData(d)
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }, [jurisdiction])

  useEffect(() => { loadGraph() }, [loadGraph])

  // Precompute degree map
  const dmap = useMemo(()=>degreeMap(graphData.nodes, graphData.edges), [graphData])

  // Build graph data for ForceGraph
  const { nodes, links } = useMemo(() => {
    const nodes = graphData.nodes.map(n => ({
      ...n,
      color: JUR[n.jurisdiction] || JUR.default,
      degree: dmap[n.id]||0,
      __fixed: false,
    }))
    const links = graphData.edges
      .filter(e => activeEdge.has(e.type))
      .map(e => ({
        ...e,
        source: e.source?.id ?? e.source,
        target: e.target?.id ?? e.target,
        color: ECOL[e.type] || '#4a5858',
      }))
    return { nodes, links }
  }, [graphData, activeEdge, dmap])

  // Search: collect matching IDs
  const matchedIds = useMemo(() => {
    if (!search.trim()) return null
    const q = search.toLowerCase()
    const s = new Set()
    graphData.nodes.forEach(n => {
      if ((n.label||'').toLowerCase().includes(q) ||
          (n.title||'').toLowerCase().includes(q) ||
          (n.jurisdiction||'').toLowerCase().includes(q)) s.add(n.id)
    })
    return s
  }, [search, graphData.nodes])

  // Collect neighbour IDs of selected node
  const neighbourIds = useMemo(() => {
    if (!selected) return null
    const s = new Set([selected.id])
    graphData.edges.forEach(e => {
      const src = e.source?.id ?? e.source
      const tgt = e.target?.id ?? e.target
      if (src===selected.id) s.add(tgt)
      if (tgt===selected.id) s.add(src)
    })
    return s
  }, [selected, graphData.edges])

  // Apply force preset when it changes
  useEffect(() => {
    if (!fgRef.current) return
    const p = LAYOUT_PRESETS.find(x=>x.id===preset) || LAYOUT_PRESETS[0]
    const fg = fgRef.current
    fg.d3Force('charge').strength(p.charge)
    fg.d3Force('link').distance(p.linkDist)
    fg.d3ReheatSimulation()
  }, [preset])

  // Canvas node painter
  const paintNode = useCallback((node, ctx, globalScale) => {
    const deg    = node.degree || 0
    const isHub  = deg >= 15
    const r      = isHub ? 9 : node.node_type==='baseline' ? 7 : 5
    const isBase = node.node_type === 'baseline'

    // Determine opacity
    let opacity = 1
    if (hoveredId && hoveredId !== node.id) opacity = 0.15
    else if (selected && neighbourIds && !neighbourIds.has(node.id)) opacity = 0.12
    else if (matchedIds && !matchedIds.has(node.id)) opacity = 0.1

    ctx.globalAlpha = opacity

    // Node fill
    ctx.beginPath()
    if (isBase) {
      ctx.arc(node.x, node.y, r, 0, 2*Math.PI)
    } else {
      const s = r * 1.6
      ctx.roundRect(node.x-s/2, node.y-s/2, s, s, 3)
    }
    ctx.fillStyle = node.color
    ctx.fill()

    // Ring on selected / hover / hub
    const isSelected = selected?.id === node.id
    const isHovered  = hoveredId === node.id
    const isMatch    = matchedIds?.has(node.id)

    if (isSelected || isHovered || isHub || isMatch) {
      ctx.beginPath()
      if (isBase) ctx.arc(node.x, node.y, r+2, 0, 2*Math.PI)
      else { const s=r*1.6+4; ctx.roundRect(node.x-s/2, node.y-s/2, s, s, 4) }
      ctx.strokeStyle = isSelected ? '#ffffff'
                       : isHovered  ? '#7adada'
                       : isMatch    ? '#d4a843'
                       : '#4a6060'
      ctx.lineWidth = isSelected ? 2.5 : 1.8
      ctx.stroke()
    }

    // Label — always show for hubs/selected, fade small at low zoom
    const minScale = isHub ? 0.3 : isSelected ? 0.2 : 0.6
    if (globalScale >= minScale) {
      const label = (node.label || node.title || node.id)
        .replace(/\s*\(.*?\)\s*/g, '')
      const truncated = label.length > 20 ? label.slice(0,18)+'…' : label
      const fs = Math.max(isHub ? 10 : 8.5, 8.5 / globalScale * 0.85)
      ctx.font = `${isHub||isSelected?'600':'400'} ${fs}px system-ui,sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'

      // Text shadow for readability
      ctx.fillStyle = '#0a1414'
      ctx.fillText(truncated, node.x+1, node.y+r+3+1)
      ctx.fillStyle = isSelected ? '#ffffff'
                    : isHub      ? '#d4e8e8'
                    : '#a8c4c4'
      ctx.fillText(truncated, node.x, node.y+r+3)
    }

    ctx.globalAlpha = 1
  }, [selected, hoveredId, neighbourIds, matchedIds])

  // Link colour with dimming
  const linkColor = useCallback(link => {
    const src = link.source?.id ?? link.source
    const tgt = link.target?.id ?? link.target
    let opacity = '99'   // ~60%
    if (selected && neighbourIds) {
      opacity = (neighbourIds.has(src) && neighbourIds.has(tgt)) ? 'cc' : '14'
    } else if (hoveredId) {
      opacity = (src===hoveredId||tgt===hoveredId) ? 'dd' : '12'
    } else if (matchedIds) {
      opacity = (matchedIds.has(src)||matchedIds.has(tgt)) ? 'cc' : '1a'
    }
    return (link.color||'#4a6060') + opacity
  }, [selected, hoveredId, neighbourIds, matchedIds])

  const linkWidth = useCallback(link => {
    const src = link.source?.id ?? link.source
    const tgt = link.target?.id ?? link.target
    if (selected && neighbourIds && neighbourIds.has(src) && neighbourIds.has(tgt)) return 2.5
    return link.type==='conflict' ? 2 : link.type==='genealogical' ? 1.8 : 1.2
  }, [selected, neighbourIds])

  // Node hover
  const onNodeHover = useCallback(node => {
    setHoveredId(node?.id ?? null)
    if (!node) { hideTip(); return }
    const jc  = JUR[node.jurisdiction]||JUR.default
    const deg = node.degree||0
    showTip(`
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
        <div style="width:8px;height:8px;border-radius:50%;background:${jc};flex-shrink:0"></div>
        <span style="font-size:10px;color:#5a8080;font-family:monospace;text-transform:uppercase;letter-spacing:.04em">
          ${node.node_type} · ${node.jurisdiction||'—'}
        </span>
        <span style="font-size:10px;color:#3a5858;margin-left:auto">${deg} links</span>
      </div>
      <div style="font-size:12px;font-weight:600;color:#cce4e4;line-height:1.4;margin-bottom:${node.urgency||node.status?5:0}px">
        ${node.title||node.label}
      </div>
      ${node.urgency?`<div style="font-size:10px;color:${node.urgency==='Critical'?'#e05252':node.urgency==='High'?'#e0834a':'#c8a030'};font-family:monospace;margin-bottom:3px">${node.urgency}</div>`:''}
      ${node.status?`<div style="font-size:10px;color:#4a7070">${node.status.slice(0,60)}${node.status.length>60?'…':''}</div>`:''}
      <div style="font-size:10px;color:#2a4848;margin-top:5px;font-style:italic">Click to explore connections</div>
    `, window._tipX||0, window._tipY||0)
  }, [])

  // Track mouse for tooltip position
  useEffect(() => {
    const h = e => { window._tipX=e.clientX; window._tipY=e.clientY }
    window.addEventListener('mousemove', h)
    return () => window.removeEventListener('mousemove', h)
  }, [])

  const onNodeClick = useCallback(node => {
    hideTip()
    setSelected(prev => prev?.id === node.id ? null : node)
  }, [])

  const onBgClick = useCallback(() => {
    setSelected(null)
    setHoveredId(null)
    hideTip()
  }, [])

  // Zoom helpers
  const zoomIn  = () => fgRef.current?.zoom(fgRef.current.zoom()*1.3, 300)
  const zoomOut = () => fgRef.current?.zoom(fgRef.current.zoom()*0.77, 300)
  const fitAll  = () => fgRef.current?.zoomToFit(400, 60)

  // Zoom to search matches
  useEffect(() => {
    if (!matchedIds || !fgRef.current || nodes.length===0) return
    const matched = nodes.filter(n => matchedIds.has(n.id))
    if (matched.length > 0) fgRef.current.zoomToFit(400, 80, n => matchedIds.has(n.id))
  }, [matchedIds, nodes])

  // Auto-fit after load
  useEffect(() => {
    if (nodes.length > 0 && fgRef.current) {
      setTimeout(() => fgRef.current?.zoomToFit(600, 60), 1800)
    }
  }, [nodes.length])

  const buildGraph = async () => {
    setBuilding(true)
    try {
      const r = await graphApi.buildGraph()
      if (r?.status==='ok'||r?.counts) { await loadGraph() }
      else { await new Promise(res=>setTimeout(res,1500)); await loadGraph() }
    } catch(e) { console.error(e) }
    finally { setBuilding(false) }
  }

  const toggleEdge = t => setActiveEdge(prev => {
    const n=new Set(prev); n.has(t)?n.delete(t):n.add(t); return n
  })

  // cleanup tooltip on unmount
  useEffect(() => () => rmTip(), [])

  const allEdgeTypes   = [...new Set(graphData.edges.map(e=>e.type))]
  const isEmpty        = !loading && graphData.nodes.length===0
  const visibleEdges   = graphData.edges.filter(e=>activeEdge.has(e.type)).length
  const panelW         = selected ? 334 : 0

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', background:'#080f0f' }}>

      {/* ── Toolbar ──────────────────────────────────────────────────────────── */}
      <div style={{ display:'flex', alignItems:'center', gap:8, padding:'9px 14px',
        borderBottom:'1px solid #182828', flexShrink:0, flexWrap:'wrap',
        background:'#0a1212' }}>

        <span style={{ fontSize:11, fontFamily:'monospace', color:'#406060',
          letterSpacing:'.07em', textTransform:'uppercase' }}>
          Knowledge Graph
        </span>
        {!isEmpty && (
          <span style={{ fontSize:11, fontFamily:'monospace', color:'#587070' }}>
            {visibleEdges} edges · {graphData.nodes.length} nodes
          </span>
        )}

        <div style={{flex:1}}/>

        {/* Search */}
        <div style={{ position:'relative', display:'flex', alignItems:'center' }}>
          <Search size={11} style={{ position:'absolute', left:8, color:'#406060', pointerEvents:'none' }}/>
          <input value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Search…"
            style={{ paddingLeft:26, paddingRight:search?26:8, height:28, fontSize:12,
              width:148, background:'#0c1818', border:'1px solid #1e3030',
              borderRadius:6, color:'#b8d0d0', outline:'none' }}/>
          {search && (
            <button onClick={()=>setSearch('')} style={{ position:'absolute', right:6,
              background:'none', border:'none', cursor:'pointer', color:'#406060',
              lineHeight:1, padding:0 }}>
              <X size={11}/>
            </button>
          )}
        </div>

        {/* Jurisdiction */}
        <select value={jurisdiction} onChange={e=>setJur(e.target.value)}
          style={{ height:28, fontSize:12, background:'#0c1818', border:'1px solid #1e3030',
            borderRadius:6, color:'#b8d0d0', padding:'0 8px' }}>
          <option value="">All jurisdictions</option>
          {['EU','Federal','GB','CA','AU','JP','SG','BR','IN','KR','CO','IL','NY','CA_STATE','INTL'].map(j=>(
            <option key={j} value={j}>{j}</option>
          ))}
        </select>

        {/* Layout preset — opens rightward (left:0) so it never goes off-screen */}
        <div style={{ position:'relative' }}>
          <button onClick={()=>setShowPresets(v=>!v)}
            style={{ display:'flex', alignItems:'center', gap:5, height:28, padding:'0 10px',
              fontSize:12, background:'#0c1818', border:'1px solid #1e3030',
              borderRadius:6, cursor:'pointer', color:'#98b8b8' }}>
            <LayoutGrid size={12}/>
            {LAYOUT_PRESETS.find(x=>x.id===preset)?.label||'Layout'}
            <ChevronDown size={11} style={{color:'#406060'}}/>
          </button>
          {showPresets && (
            <div style={{ position:'absolute', top:34, left:0, zIndex:50,
              background:'#0c1818', border:'1px solid #1e3030', borderRadius:8,
              padding:8, minWidth:190, boxShadow:'0 8px 24px rgba(0,0,0,.65)' }}>
              {LAYOUT_PRESETS.map(p=>(
                <button key={p.id} onClick={()=>{ setPreset(p.id); setShowPresets(false) }}
                  style={{ display:'flex', flexDirection:'column', width:'100%',
                    textAlign:'left', padding:'7px 10px', borderRadius:5,
                    cursor:'pointer', border:'none',
                    background:preset===p.id?'#182828':'transparent', marginBottom:2 }}>
                  <span style={{ fontSize:12, fontWeight:500,
                    color:preset===p.id?'#6adada':'#b8d0d0' }}>{p.label}</span>
                  <span style={{ fontSize:10, color:'#406060' }}>Charge {p.charge} · Link {p.linkDist}px</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Zoom + fit */}
        {[[zoomIn,ZoomIn,'Zoom in'],[zoomOut,ZoomOut,'Zoom out'],[fitAll,Maximize2,'Fit all']].map(([fn,Icon,lbl])=>(
          <button key={lbl} onClick={fn} title={lbl}
            style={{ display:'flex', alignItems:'center', justifyContent:'center',
              width:28, height:28, background:'#0c1818', border:'1px solid #1e3030',
              borderRadius:6, cursor:'pointer', color:'#7a9898' }}>
            <Icon size={12}/>
          </button>
        ))}

        {/* Rebuild */}
        <button className="btn-secondary btn-sm" onClick={buildGraph} disabled={building}>
          {building ? <><Spinner size={11}/> Building…</> : <><RefreshCw size={11}/> Rebuild</>}
        </button>
      </div>

      {/* ── Canvas area ──────────────────────────────────────────────────────── */}
      <div style={{ flex:1, position:'relative', overflow:'hidden' }}>

        {/* ForceGraph canvas */}
        <div ref={wrapRef} style={{ position:'absolute', inset:0,
          right:panelW, transition:'right .2s ease' }}>
          {!loading && !isEmpty && ForceGraph && (
            <ForceGraph
              ref={fgRef}
              graphData={{ nodes, links }}
              width={dims.w - panelW}
              height={dims.h}
              backgroundColor="#080f0f"
              // Node painting
              nodeCanvasObject={paintNode}
              nodeCanvasObjectMode={()=>'replace'}
              nodeLabel={()=>''}            /* suppress built-in tooltip — we use our own */
              nodeRelSize={1}
              // Link styling
              linkColor={linkColor}
              linkWidth={linkWidth}
              linkDirectionalArrowLength={l=>['genealogical','implements','amends','supersedes'].includes(l.type)?4:0}
              linkDirectionalArrowRelPos={1}
              linkDirectionalParticles={l=>l.type==='conflict'?2:0}
              linkDirectionalParticleWidth={2}
              linkDirectionalParticleColor={l=>ECOL[l.type]||'#607070'}
              // Force config — good spread, prevents hairball
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              d3Force="charge"
              cooldownTicks={200}
              // Events
              onNodeHover={onNodeHover}
              onNodeClick={onNodeClick}
              onBackgroundClick={onBgClick}
              // Warm up so nodes spread before rendering
              warmupTicks={60}
            />
          )}
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ position:'absolute', inset:0, display:'flex',
            alignItems:'center', justifyContent:'center', gap:10,
            color:'#587070', fontSize:13, pointerEvents:'none' }}>
            <Spinner/> Loading graph…
          </div>
        )}

        {/* Empty */}
        {isEmpty && !loading && (
          <div style={{ position:'absolute', inset:0, display:'flex',
            alignItems:'center', justifyContent:'center' }}>
            <EmptyState icon={Network} title="No knowledge graph yet"
              message='Click "Rebuild" to detect relationships across baselines and documents.'/>
          </div>
        )}

        {/* Legend */}
        {!isEmpty && !loading && (
          <Legend edgeTypes={allEdgeTypes} active={activeEdge} onToggle={toggleEdge}/>
        )}

        {/* Hint bar */}
        {!isEmpty && !loading && !selected && (
          <div style={{ position:'absolute', top:12, left:'50%',
            transform:'translateX(-50%)', background:'rgba(8,15,15,.8)',
            backdropFilter:'blur(4px)', border:'1px solid #182828',
            borderRadius:16, padding:'4px 14px', fontSize:11,
            color:'#406060', pointerEvents:'none', whiteSpace:'nowrap' }}>
            Scroll to zoom · drag to pan · click a node to explore
          </div>
        )}

        {/* Jurisdiction colour key */}
        {!isEmpty && !loading && (
          <div style={{ position:'absolute', top:12, right:panelW+12, zIndex:10,
            background:'rgba(8,15,15,.85)', backdropFilter:'blur(4px)',
            border:'1px solid #182828', borderRadius:8, padding:'8px 12px',
            transition:'right .2s ease' }}>
            <div style={{ fontSize:10, fontFamily:'monospace', color:'#406060',
              textTransform:'uppercase', letterSpacing:'.07em', marginBottom:7 }}>
              Jurisdiction
            </div>
            {[...new Set(graphData.nodes.map(n=>n.jurisdiction))].filter(Boolean).sort().map(j=>(
              <div key={j} style={{ display:'flex', alignItems:'center', gap:6, marginBottom:3 }}>
                <div style={{ width:7, height:7, borderRadius:'50%',
                  background:JUR[j]||JUR.default, flexShrink:0 }}/>
                <span style={{ fontSize:10, color:'#7a9898', fontFamily:'monospace' }}>{j}</span>
              </div>
            ))}
          </div>
        )}

        {/* Selected node: search match count badge */}
        {matchedIds && matchedIds.size > 0 && (
          <div style={{ position:'absolute', top:12, left:'50%',
            transform:'translateX(-50%)', background:'rgba(8,15,15,.85)',
            border:'1px solid #182828', borderRadius:16, padding:'4px 14px',
            fontSize:11, color:'#c8a030', pointerEvents:'none', whiteSpace:'nowrap' }}>
            {matchedIds.size} match{matchedIds.size!==1?'es':''} — others dimmed
          </div>
        )}
      </div>

      {/* ── Detail panel ─────────────────────────────────────────────────────── */}
      {selected && (
        <div style={{ position:'absolute', right:0, top:0, bottom:0, width:334, zIndex:15 }}>
          <NodeDetail
            node={selected}
            allEdges={graphData.edges}
            allNodes={graphData.nodes}
            onClose={()=>{ setSelected(null); hideTip() }}
            onNavigate={navigate}
          />
        </div>
      )}

      {/* Layout preset backdrop */}
      {showPresets && (
        <div style={{ position:'fixed', inset:0, zIndex:40 }}
          onClick={()=>setShowPresets(false)}/>
      )}
    </div>
  )
}
