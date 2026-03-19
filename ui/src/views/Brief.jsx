import { useState, useEffect } from 'react'
import { FileText, Sparkles, RefreshCw, X, ExternalLink, BookOpen, ChevronRight } from 'lucide-react'
import { Spinner, EmptyState, SectionHeader, Badge } from '../components.jsx'
import ReactMarkdown from 'react-markdown'
import { useNavigate } from 'react-router-dom'

const briefApi = {
  list:     ()        => fetch('/api/briefs').then(r=>r.json()),
  get:      (key)     => fetch(`/api/briefs/${key}`).then(r=>r.json()),
  generate: (topic,jur,force) => fetch('/api/briefs/generate',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({topic,jurisdiction:jur||null,force:force||false}),
  }).then(r=>r.json()),
}

const JURISDICTIONS = ['','EU','Federal','GB','CA','JP','AU','SG','BR']

const STARTER_TOPICS = [
  'Foundation model governance across jurisdictions',
  'Automated hiring tools and employment AI regulation',
  'AI risk assessment obligations: EU vs US',
  'Transparency and explainability requirements',
  'Bias testing and fairness auditing requirements',
  'High-risk AI system definitions and categories',
]

function CitationPill({citation}) {
  const typeColor = citation.source_type==='baseline'?'var(--accent)':'var(--text-3)'
  return (
    <div style={{
      display:'inline-flex',alignItems:'center',gap:4,
      fontSize:10,fontFamily:'var(--font-mono)',
      background:'var(--bg-3)',border:'1px solid var(--border)',
      borderRadius:3,padding:'2px 7px',margin:'0 3px 4px 0',
    }}>
      <span style={{color:typeColor}}>●</span>
      <span style={{color:'var(--text-2)'}}>{citation.source_title||citation.source_id}</span>
      {citation.jurisdiction&&<span style={{color:'var(--text-3)'}}>{citation.jurisdiction}</span>}
    </div>
  )
}

function BriefView({brief, onRegenerate, generating}) {
  return (
    <div style={{maxWidth:760,margin:'0 auto'}}>
      <div className="flex items-center justify-between" style={{marginBottom:16}}>
        <div>
          <div style={{fontSize:18,fontWeight:300,marginBottom:3}}>{brief.topic_label}</div>
          <div style={{fontSize:11,color:'var(--text-3)',fontFamily:'var(--font-mono)'}}>
            {brief.model_used&&`${brief.model_used} · `}
            {brief.built_at&&new Date(brief.built_at).toLocaleDateString()}
            {brief.passage_count&&` · ${brief.passage_count} passages`}
          </div>
        </div>
        <button className="btn-ghost btn-sm" onClick={onRegenerate} disabled={generating}>
          <RefreshCw size={12} style={{animation:generating?'spin 1s linear infinite':'none'}}/>
          Regenerate
        </button>
      </div>

      {brief.citations?.length>0 && (
        <div style={{marginBottom:16,padding:'10px 14px',
                     background:'var(--bg-2)',border:'1px solid var(--border)',
                     borderRadius:'var(--radius)'}}>
          <div style={{fontSize:10,fontFamily:'var(--font-mono)',color:'var(--text-3)',
                       textTransform:'uppercase',letterSpacing:'0.05em',marginBottom:7}}>
            Sources ({brief.citations.length})
          </div>
          <div style={{display:'flex',flexWrap:'wrap'}}>
            {brief.citations.map((c,i)=><CitationPill key={i} citation={c}/>)}
          </div>
        </div>
      )}

      <div className="markdown" style={{
        fontSize:13,lineHeight:1.7,color:'var(--text-2)',
        '& h2':{borderBottom:'1px solid var(--border)',paddingBottom:6,marginTop:24},
      }}>
        <ReactMarkdown>{brief.content}</ReactMarkdown>
      </div>
    </div>
  )
}

export default function Brief() {
  const [briefs,      setBriefs]      = useState([])
  const [loadingList, setLoadingList] = useState(true)
  const [selected,    setSelected]    = useState(null)
  const [generating,  setGenerating]  = useState(false)
  const [topic,       setTopic]       = useState('')
  const [jurisdiction,setJur]         = useState('')
  const navigate = useNavigate()

  const loadList = async () => {
    const data = await briefApi.list()
    setBriefs(data.briefs||[])
    setLoadingList(false)
  }

  useEffect(()=>{loadList()},[])

  const generate = async (t, jur, force=false) => {
    if (!t?.trim()) return
    setGenerating(true)
    setSelected(null)
    try {
      const result = await briefApi.generate(t, jur, force)
      setSelected(result)
      loadList()
    } catch(e) {
      setSelected({error:true,content:e.message,topic_label:t,citations:[]})
    } finally {
      setGenerating(false)
    }
  }

  const isEmpty = !selected && !generating

  return (
    <div style={{display:'flex',height:'100%',overflow:'hidden'}}>
      {/* Sidebar */}
      <div style={{width:260,flexShrink:0,borderRight:'1px solid var(--border)',
                   overflow:'auto',padding:'20px 0'}}>
        <div style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-3)',
                     textTransform:'uppercase',letterSpacing:'0.06em',
                     padding:'0 18px 10px'}}>
          Saved Briefs
        </div>
        {loadingList ? (
          <div style={{padding:'20px 18px'}}><Spinner/></div>
        ) : briefs.length===0 ? (
          <div style={{padding:'0 18px',fontSize:12,color:'var(--text-3)'}}>
            No briefs yet. Generate one from the main panel.
          </div>
        ) : briefs.map(b=>(
          <div key={b.topic_key} onClick={()=>briefApi.get(b.topic_key).then(setSelected)}
               style={{
                 padding:'9px 18px',cursor:'pointer',
                 background:selected?.topic_key===b.topic_key?'var(--bg-3)':'transparent',
                 borderLeft:selected?.topic_key===b.topic_key?'3px solid var(--accent)':'3px solid transparent',
               }}>
            <div style={{fontSize:12,fontWeight:selected?.topic_key===b.topic_key?500:400,
                         lineHeight:1.4,color:'var(--text-2)',marginBottom:2}}>
              {b.topic_label}
            </div>
            <div style={{fontSize:10,color:'var(--text-3)',fontFamily:'var(--font-mono)'}}>
              {b.built_at?.slice(0,10)}
            </div>
          </div>
        ))}
      </div>

      {/* Main area */}
      <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
        {/* Generate bar */}
        <div style={{padding:'16px 24px',borderBottom:'1px solid var(--border)',
                     background:'var(--bg)',flexShrink:0}}>
          <div className="flex gap-2">
            <input
              value={topic}
              onChange={e=>setTopic(e.target.value)}
              onKeyDown={e=>e.key==='Enter'&&generate(topic,jurisdiction)}
              placeholder="Enter a regulatory topic to brief…"
              style={{flex:1,fontSize:13}}
              disabled={generating}
            />
            <select value={jurisdiction} onChange={e=>setJur(e.target.value)}
                    style={{width:130,fontSize:12}} disabled={generating}>
              {JURISDICTIONS.map(j=><option key={j} value={j}>{j||'All Jurisdictions'}</option>)}
            </select>
            <button className="btn-primary" onClick={()=>generate(topic,jurisdiction)}
                    disabled={generating||!topic.trim()}>
              {generating?<><Spinner size={13}/>Generating…</>:<><Sparkles size={13}/>Generate</>}
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{flex:1,overflow:'auto',padding:'24px'}}>
          {generating ? (
            <div style={{display:'flex',alignItems:'center',justifyContent:'center',
                         height:200,gap:12,color:'var(--text-3)',fontSize:13}}>
              <Spinner/>Generating brief — retrieving passages and analysing…
            </div>
          ) : selected ? (
            selected.error ? (
              <div style={{color:'var(--red)',fontSize:13,padding:20}}>
                {selected.content}
              </div>
            ) : (
              <BriefView
                brief={selected}
                onRegenerate={()=>generate(selected.topic_label,'',true)}
                generating={generating}
              />
            )
          ) : (
            <div style={{maxWidth:600,margin:'40px auto',textAlign:'center'}}>
              <div style={{
                width:56,height:56,borderRadius:'50%',
                background:'var(--bg-3)',border:'1px solid var(--border)',
                display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 20px',
              }}>
                <FileText size={24} style={{color:'var(--accent)'}}/>
              </div>
              <div style={{fontSize:16,fontWeight:300,marginBottom:8}}>
                Regulatory Intelligence Briefs
              </div>
              <div style={{fontSize:13,color:'var(--text-3)',lineHeight:1.6,marginBottom:28}}>
                Enter any regulatory topic above to generate a structured 5-minute brief
                grounded in your corpus — baselines and summarised documents.
                Results are cached for 14 days.
              </div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,textAlign:'left'}}>
                {STARTER_TOPICS.map((t,i)=>(
                  <button key={i} className="card card-hover"
                          style={{padding:'10px 14px',textAlign:'left',fontSize:12,
                                  lineHeight:1.5,color:'var(--text-2)',cursor:'pointer'}}
                          onClick={()=>{setTopic(t);generate(t,'')}}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
