import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Network, ZoomIn, ZoomOut, Maximize2, RefreshCw, BookOpen, FileText,
  GitBranch, Link, Layers, AlertTriangle, Globe, X, ExternalLink, Sparkles,
} from 'lucide-react'
import { Spinner, EmptyState, Badge } from '../components.jsx'

const graphApi = {
  graph:           (p={}) => fetch(`/api/graph?${new URLSearchParams(p)}`).then(r=>r.json()),
  buildGraph:      ()     => fetch('/api/graph/build',{method:'POST'}).then(r=>r.json()),
  detectConflicts: ()     => fetch('/api/graph/conflicts',{method:'POST'}).then(r=>r.json()),
  graphStatus:     ()     => fetch('/api/graph/status').then(r=>r.json()),
}

const JUR_COLORS={EU:'#4f8fe0',Federal:'#e07c4f',PA:'#52a878',GB:'#a06bd4',CA:'#d4a843',JP:'#e05252',AU:'#4fd4c8',SG:'#d44fa0',BR:'#8fe04f',default:'#607070'}
const EDGE_COLORS={cross_ref:'#5299d4',genealogical:'#52a878',semantic:'#d4a843',document:'#a0a8af',conflict:'#e05252',amends:'#e0834a',implements:'#52a878',supersedes:'#e05252',version_of:'#a0b0af'}
const EDGE_LABELS={cross_ref:'Cross-reference',genealogical:'Genealogical',semantic:'Shared Concept',document:'Document Link',conflict:'Conflict'}
const EDGE_ICONS={cross_ref:Link,genealogical:GitBranch,semantic:Layers,document:FileText,conflict:AlertTriangle}
const JURISDICTIONS=['','EU','Federal','PA','GB','CA','JP','AU','SG','BR']

function Legend({edgeTypes,activeTypes,onToggle}){
  return(
    <div style={{position:'absolute',bottom:20,left:20,zIndex:10,background:'var(--bg-2)',border:'1px solid var(--border)',borderRadius:'var(--radius)',padding:'10px 14px',minWidth:180}}>
      <div style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)',textTransform:'uppercase',letterSpacing:'0.05em',marginBottom:8}}>Edge types</div>
      {edgeTypes.map(type=>{
        const Icon=EDGE_ICONS[type]||Link
        const color=EDGE_COLORS[type]||'#607070'
        const active=activeTypes.has(type)
        return(
          <div key={type} className="flex items-center gap-2" style={{marginBottom:5,cursor:'pointer',opacity:active?1:0.35}} onClick={()=>onToggle(type)}>
            <Icon size={11} style={{color,flexShrink:0}}/>
            <span style={{fontSize:11,color:'var(--text-2)'}}>{EDGE_LABELS[type]||type}</span>
          </div>
        )
      })}
      <div style={{borderTop:'1px solid var(--border)',marginTop:8,paddingTop:8}}>
        <div style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)',textTransform:'uppercase',letterSpacing:'0.05em',marginBottom:6}}>Nodes</div>
        <div className="flex items-center gap-2" style={{marginBottom:4}}><BookOpen size={11} style={{color:'var(--accent)'}}/><span style={{fontSize:11,color:'var(--text-2)'}}>Baseline (circle)</span></div>
        <div className="flex items-center gap-2"><FileText size={11} style={{color:'var(--text-3)'}}/><span style={{fontSize:11,color:'var(--text-2)'}}>Document (square)</span></div>
      </div>
    </div>
  )
}

function NodeDetail({node,edges,allNodes,onClose,onNavigate}){
  if(!node)return null
  const nodeMap={}
  allNodes.forEach(n=>{nodeMap[n.id]=n})
  const connectedEdges=edges.filter(e=>{
    const src=e.source?.id||e.source
    const tgt=e.target?.id||e.target
    return src===node.id||tgt===node.id
  })
  return(
    <div style={{position:'absolute',right:20,top:20,bottom:20,width:320,zIndex:10,background:'var(--bg-2)',border:'1px solid var(--border)',borderRadius:'var(--radius)',overflow:'auto',padding:16}}>
      <div className="flex items-center justify-between" style={{marginBottom:14}}>
        <div className="flex items-center gap-2">
          {node.node_type==='baseline'?<BookOpen size={14} style={{color:'var(--accent)'}}/>:<FileText size={14} style={{color:'var(--text-3)'}}/>}
          <span style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)',textTransform:'uppercase'}}>{node.node_type}</span>
        </div>
        <button className="btn-icon" onClick={onClose}><X size={14}/></button>
      </div>
      <div style={{fontWeight:500,fontSize:14,marginBottom:6,lineHeight:1.4}}>{node.title||node.label}</div>
      {node.jurisdiction&&(
        <div className="flex items-center gap-2" style={{marginBottom:10}}>
          <Globe size={11} style={{color:'var(--text-3)'}}/>
          <span style={{fontSize:12,color:'var(--text-3)'}}>{node.jurisdiction}</span>
          {node.status&&<span style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)'}}>· {node.status}</span>}
        </div>
      )}
      {node.overview&&(
        <div style={{fontSize:12,color:'var(--text-2)',lineHeight:1.6,marginBottom:12,borderBottom:'1px solid var(--border)',paddingBottom:12}}>
          {node.overview}
        </div>
      )}
      <div style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)',textTransform:'uppercase',letterSpacing:'0.05em',marginBottom:8}}>
        Connections ({connectedEdges.length})
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:6}}>
        {connectedEdges.slice(0,12).map((e,i)=>{
          const src=e.source?.id||e.source
          const tgt=e.target?.id||e.target
          const otherId=src===node.id?tgt:src
          const other=nodeMap[otherId]
          const color=EDGE_COLORS[e.type]||'#607070'
          const Icon=EDGE_ICONS[e.type]||Link
          return(
            <div key={i} style={{background:'var(--bg-3)',border:'1px solid var(--border)',borderLeft:`3px solid ${color}`,borderRadius:'var(--radius)',padding:'7px 10px'}}>
              <div className="flex items-center gap-2" style={{marginBottom:3}}>
                <Icon size={10} style={{color,flexShrink:0}}/>
                <span style={{fontSize:10,color,fontFamily:'var(--font-mono)'}}>{EDGE_LABELS[e.type]||e.type}</span>
                {e.concept&&<span style={{fontSize:10,color:'var(--text-3)',fontFamily:'var(--font-mono)'}}>· {e.concept.replace(/_/g,' ')}</span>}
              </div>
              <div style={{fontSize:11,color:'var(--text-2)',fontWeight:500}}>{other?.label||other?.title||otherId}</div>
              {e.evidence&&<div style={{fontSize:10,color:'var(--text-3)',marginTop:2,lineHeight:1.4,fontStyle:'italic'}}>{(e.evidence||'').slice(0,120)}{(e.evidence||'').length>120?'…':''}</div>}
            </div>
          )
        })}
      </div>
      <button className="btn-secondary btn-sm" style={{width:'100%',marginTop:14,justifyContent:'center'}}
        onClick={()=>onNavigate&&onNavigate(`/ask`)}>
        <Sparkles size={12} style={{color:'var(--accent)'}}/>
        Ask about this regulation
      </button>
      {node.url&&(
        <a href={node.url} target="_blank" rel="noreferrer" style={{display:'flex',alignItems:'center',gap:6,fontSize:11,color:'var(--accent)',marginTop:8,justifyContent:'center'}}>
          View source <ExternalLink size={10}/>
        </a>
      )}
    </div>
  )
}

export default function Graph({navigate}){
  const [graphData,setGraphData]=useState({nodes:[],edges:[],meta:{}})
  const [loading,setLoading]=useState(true)
  const [building,setBuilding]=useState(false)
  const [selected,setSelected]=useState(null)
  const [jurisdiction,setJur]=useState('')
  const [activeEdgeTypes,setActive]=useState(new Set(['cross_ref','genealogical','semantic','document','conflict']))
  const [status,setStatus]=useState(null)
  const [ForceGraph,setForceGraph]=useState(null)
  const containerRef=useRef(null)
  const fgRef=useRef(null)

  useEffect(()=>{import('react-force-graph-2d').then(m=>setForceGraph(()=>m.default))},[])

  const load=useCallback(async()=>{
    setLoading(true)
    try{
      const params={}
      if(jurisdiction)params.jurisdiction=jurisdiction
      const et=[...activeEdgeTypes].join(',')
      if(et)params.edge_types=et
      const data=await graphApi.graph(params)
      setGraphData(data)
    }finally{setLoading(false)}
  },[jurisdiction,activeEdgeTypes])

  useEffect(()=>{load()},[load])
  useEffect(()=>{graphApi.graphStatus().then(setStatus).catch(()=>{})},[])

  const buildGraph=async()=>{
    setBuilding(true)
    try{
      await graphApi.buildGraph()
      let attempts=0
      const poll=setInterval(async()=>{
        const s=await graphApi.graphStatus()
        setStatus(s)
        if(s.total_edges>0||++attempts>15){clearInterval(poll);setBuilding(false);load()}
      },2000)
    }catch{setBuilding(false)}
  }

  const toggleEdgeType=type=>{
    setActive(prev=>{const next=new Set(prev);if(next.has(type))next.delete(type);else next.add(type);return next})
  }

  const visibleEdges=graphData.edges.filter(e=>activeEdgeTypes.has(e.type))
  const nodes=graphData.nodes
  const links=visibleEdges.map(e=>({...e,source:e.source,target:e.target}))

  const nodeColor=n=>{
    if(n.node_type==='baseline')return JUR_COLORS[n.jurisdiction]||JUR_COLORS.default
    const uc={Critical:'#e05252',High:'#e0834a',Medium:'#d4a843'}
    return uc[n.urgency]||'#607070'
  }

  const nodeVal=n=>n.node_type==='baseline'?4:2

  const paintNode=(node,ctx,globalScale)=>{
    const {x,y}=node
    const r=Math.sqrt(nodeVal(node))*5
    const col=nodeColor(node)
    ctx.beginPath()
    if(node.node_type==='baseline')ctx.arc(x,y,r,0,2*Math.PI)
    else ctx.rect(x-r*0.8,y-r*0.8,r*1.6,r*1.6)
    ctx.fillStyle=col
    ctx.fill()
    if(selected?.id===node.id){ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.stroke()}
    if(globalScale>1.2){
      ctx.font=`${Math.max(8,10/globalScale)}px sans-serif`
      ctx.fillStyle='rgba(200,210,210,0.9)'
      ctx.textAlign='center'
      ctx.textBaseline='middle'
      ctx.fillText((node.label||'').slice(0,20),x,y+r+8)
    }
  }

  const allEdgeTypes=Object.keys(EDGE_LABELS)
  const isEmpty=!loading&&nodes.length===0

  return(
    <div style={{display:'flex',height:'100%',overflow:'hidden'}}>
      <div style={{flex:1,position:'relative',background:'var(--bg)'}} ref={containerRef}>
        {/* Top bar */}
        <div style={{position:'absolute',top:0,left:0,right:0,zIndex:10,display:'flex',alignItems:'center',gap:10,flexWrap:'wrap',padding:'12px 16px',background:'linear-gradient(to bottom, var(--bg) 70%, transparent)'}}>
          <div style={{fontFamily:'var(--font-mono)',fontSize:11,color:'var(--text-3)',textTransform:'uppercase',letterSpacing:'0.06em'}}>Knowledge Graph</div>
          {status&&<span style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)'}}>{status.total_edges} edges{graphData.meta?.total_nodes?` · ${graphData.meta.total_nodes} nodes`:''}</span>}
          <div style={{flex:1}}/>
          <select value={jurisdiction} onChange={e=>setJur(e.target.value)} style={{width:130,fontSize:12}}>
            {JURISDICTIONS.map(j=><option key={j} value={j}>{j||'All Jurisdictions'}</option>)}
          </select>
          <button className="btn-secondary btn-sm" onClick={buildGraph} disabled={building}>
            <RefreshCw size={12} style={{animation:building?'spin 1s linear infinite':'none'}}/>
            {building?'Building…':(status?.built?'Rebuild':'Build Graph')}
          </button>
        </div>
        {/* Zoom controls */}
        <div style={{position:'absolute',top:56,right:selected?350:20,zIndex:10,display:'flex',flexDirection:'column',gap:4,transition:'right 0.2s'}}>
          {[[ZoomIn,'Zoom in',()=>fgRef.current?.zoom(1.5)],[ZoomOut,'Zoom out',()=>fgRef.current?.zoom(0.7)],[Maximize2,'Fit',()=>fgRef.current?.zoomToFit(400)]].map(([Icon,label,fn])=>(
            <button key={label} className="btn-icon" onClick={fn} title={label} style={{background:'var(--bg-2)',border:'1px solid var(--border)'}}>
              <Icon size={14}/>
            </button>
          ))}
        </div>

        {loading?(
          <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100%',gap:12,color:'var(--text-3)',fontSize:13}}>
            <Spinner/>Loading graph…
          </div>
        ):isEmpty?(
          <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100%'}}>
            <EmptyState icon={Network} title="No knowledge graph yet" message='Click "Build Graph" to detect relationships across all 19 baselines and your documents.'/>
          </div>
        ):ForceGraph?(
          <ForceGraph
            ref={fgRef}
            graphData={{nodes,links}}
            nodeCanvasObject={paintNode}
            nodeCanvasObjectMode={()=>'replace'}
            linkColor={l=>EDGE_COLORS[l.type]||'#3a4444'}
            linkWidth={l=>l.type==='conflict'?2:l.strength>0.8?1.5:1}
            linkDirectionalArrowLength={l=>['genealogical','implements'].includes(l.type)?4:0}
            linkDirectionalArrowRelPos={1}
            onNodeClick={node=>setSelected(prev=>prev?.id===node.id?null:node)}
            onBackgroundClick={()=>setSelected(null)}
            cooldownTicks={120}
            nodeLabel={n=>n.title||n.label}
            width={(containerRef.current?.clientWidth||800)-(selected?340:0)}
            height={containerRef.current?.clientHeight||600}
          />
        ):null}

        {!isEmpty&&<Legend edgeTypes={allEdgeTypes} activeTypes={activeEdgeTypes} onToggle={toggleEdgeType}/>}
      </div>

      {selected&&(
        <NodeDetail
          node={selected}
          edges={graphData.edges}
          allNodes={graphData.nodes}
          onClose={()=>setSelected(null)}
          onNavigate={navigate}
        />
      )}
    </div>
  )
}
