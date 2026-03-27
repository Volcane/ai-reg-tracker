import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Send, Sparkles, BookOpen, ExternalLink, ChevronDown, ChevronUp,
  History, RefreshCw, AlertCircle, FileText, Globe, Lightbulb, X,
} from 'lucide-react'
import { Spinner, EmptyState, SectionHeader } from '../components.jsx'

const api = {
  ask:          (q, jur) => fetch('/api/qa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q, jurisdiction: jur || null }),
  }).then(r => r.json()),
  history:      ()      => fetch('/api/qa/history?limit=30').then(r => r.json()),
  rebuildIndex: ()      => fetch('/api/qa/index/rebuild', { method: 'POST' }).then(r => r.json()),
  indexStatus:  ()      => fetch('/api/qa/index/status').then(r => r.json()),
}

const JURISDICTIONS = ['', 'EU', 'Federal', 'PA', 'GB', 'CA', 'JP', 'AU', 'SG', 'BR']

const STARTER_QUESTIONS = [
  // AI Regulation
  'What are the prohibited AI practices under the EU AI Act?',
  'Which US states have specific requirements for automated hiring tools?',
  'How do the EU AI Act and Colorado AI Act differ in their risk-tier approach?',
  // Data Privacy
  'What are the GDPR requirements for data breach notification?',
  'How does CCPA/CPRA define the right to opt out of data sales?',
  'What lawful bases exist for processing personal data under GDPR?',
  // Cross-domain
  'How does GDPR Article 22 on automated decisions interact with the EU AI Act?',
  'What transparency obligations apply to AI systems that process personal data?',
]

// ── Citation badge inline ─────────────────────────────────────────────────────

function CitationBadge({ id, onHover }) {
  return (
    <span
      className="citation-badge"
      style={{
        display:       'inline-block',
        fontSize:      10,
        fontFamily:    'var(--font-mono)',
        background:    'var(--accent-dim)',
        color:         'var(--accent)',
        border:        '1px solid var(--accent)',
        borderRadius:  4,
        padding:       '0 5px',
        marginLeft:    3,
        cursor:        'pointer',
        verticalAlign: 'middle',
        lineHeight:    '16px',
      }}
      onMouseEnter={() => onHover(id)}
      onMouseLeave={() => onHover(null)}
    >
      {id}
    </span>
  )
}

// ── Render answer text with inline citation badges ────────────────────────────

function AnswerText({ text, onCitationHover }) {
  // Replace [source_id] markers with badge components
  const parts = text.split(/(\[[^\]]+\])/g)
  return (
    <span style={{ lineHeight: 1.7 }}>
      {parts.map((part, i) => {
        const match = part.match(/^\[([^\]]+)\]$/)
        if (match) {
          return (
            <CitationBadge key={i} id={match[1]} onHover={onCitationHover} />
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}

// ── Source citation card ──────────────────────────────────────────────────────

function CitationCard({ citation, highlight }) {
  const [expanded, setExpanded] = useState(false)
  const isHighlighted = highlight === citation.source_id

  return (
    <div
      style={{
        border:       `1px solid ${isHighlighted ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 'var(--radius)',
        background:   isHighlighted ? 'var(--bg-3)' : 'var(--bg-2)',
        padding:      '10px 13px',
        transition:   'all 0.15s ease',
        marginBottom: 6,
      }}
    >
      <div className="flex items-center gap-2" style={{ marginBottom: expanded ? 8 : 0 }}>
        {citation.source_type === 'baseline'
          ? <BookOpen size={12} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          : <FileText  size={12} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
        }
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500 }} className="truncate">
            {citation.source_title}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
            {citation.jurisdiction && <span style={{ marginRight: 8 }}>{citation.jurisdiction}</span>}
            {citation.section && <span>{citation.section}</span>}
          </div>
        </div>
        <span
          style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)',
                   flexShrink: 0, cursor: 'pointer', userSelect: 'none' }}
          onClick={() => setExpanded(e => !e)}
        >
          {citation.source_id}
          {expanded ? <ChevronUp size={10} style={{ marginLeft: 3 }} /> : <ChevronDown size={10} style={{ marginLeft: 3 }} />}
        </span>
      </div>
      {expanded && citation.excerpt && (
        <div style={{
          fontSize: 11, color: 'var(--text-3)', lineHeight: 1.55,
          borderTop: '1px solid var(--border)', paddingTop: 8,
          fontStyle: 'italic',
        }}>
          "{citation.excerpt}"
        </div>
      )}
    </div>
  )
}

// ── Q&A answer block ──────────────────────────────────────────────────────────

function AnswerBlock({ item, onFollowUp }) {
  const [hoveredCitation, setHoveredCitation] = useState(null)
  const [showCitations,   setShowCitations]   = useState(true)
  const isError = item.error || (!item.answer && !item.loading)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Question */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div style={{
          background:   'var(--accent)',
          color:        '#fff',
          borderRadius: '12px 12px 4px 12px',
          padding:      '10px 16px',
          maxWidth:     '75%',
          fontSize:     13,
          lineHeight:   1.55,
        }}>
          {item.question}
        </div>
      </div>

      {/* Answer */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: 'var(--bg-3)', border: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Sparkles size={13} style={{ color: 'var(--accent)' }} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          {item.loading ? (
            <div className="flex items-center gap-2" style={{ color: 'var(--text-3)', fontSize: 13 }}>
              <Spinner size={14} /> Searching corpus and generating answer…
            </div>
          ) : isError ? (
            <div className="flex items-center gap-2" style={{ color: 'var(--red)', fontSize: 13 }}>
              <AlertCircle size={14} /> {item.answer || 'An error occurred.'}
            </div>
          ) : (
            <>
              {/* Answer text with inline citation badges */}
              <div style={{
                fontSize: 13, lineHeight: 1.7, color: 'var(--text-2)',
                background: 'var(--bg-2)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', padding: '14px 16px',
                marginBottom: 12,
              }}>
                <AnswerText text={item.answer} onCitationHover={setHoveredCitation} />
              </div>

              {/* Retrieval meta */}
              <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)',
                            marginBottom: 10 }}>
                {item.retrieval_count > 0 && (
                  <span>{item.retrieval_count} passages retrieved · </span>
                )}
                {item.citations?.length > 0 && (
                  <span
                    style={{ cursor: 'pointer', color: 'var(--accent)' }}
                    onClick={() => setShowCitations(s => !s)}
                  >
                    {item.citations.length} source{item.citations.length !== 1 ? 's' : ''}
                    {showCitations ? ' ▲' : ' ▼'}
                  </span>
                )}
              </div>

              {/* Citation cards */}
              {showCitations && item.citations?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  {item.citations.map((c, i) => (
                    <CitationCard
                      key={i}
                      citation={c}
                      highlight={hoveredCitation}
                    />
                  ))}
                </div>
              )}

              {/* Follow-up suggestions */}
              {item.follow_ups?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)',
                                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 7 }}>
                    <Lightbulb size={10} style={{ marginRight: 4 }} />
                    Suggested follow-ups
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    {item.follow_ups.map((q, i) => (
                      <button
                        key={i}
                        className="btn-ghost"
                        style={{ textAlign: 'left', fontSize: 12, padding: '6px 10px',
                                 justifyContent: 'flex-start' }}
                        onClick={() => onFollowUp(q)}
                      >
                        <ChevronDown size={11} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }} />
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AskAris() {
  const [conversation, setConversation] = useState([])   // [{question, answer, citations, ...}]
  const [input,        setInput]        = useState('')
  const [jurisdiction, setJurisdiction] = useState('')
  const [loading,      setLoading]      = useState(false)
  const [indexStatus,  setIndexStatus]  = useState(null)
  const [showHistory,  setShowHistory]  = useState(false)
  const [history,      setHistory]      = useState([])
  const [rebuilding,   setRebuilding]   = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // Load index status on mount; auto-rebuild if stale
  useEffect(() => {
    api.indexStatus().then(s => {
      setIndexStatus(s)
      // Auto-kick a rebuild if index is empty or stale — silently in background
      if (s && !s.ready && s.passage_count === 0) {
        setTimeout(() => {
          api.rebuildIndex().catch(() => {})
          // Poll until ready
          const poll = setInterval(() => {
            api.indexStatus().then(st => {
              setIndexStatus(st)
              if (st?.ready) clearInterval(poll)
            }).catch(() => {})
          }, 3000)
          setTimeout(() => clearInterval(poll), 120000) // give up after 2 min
        }, 1500)
      }
    }).catch(() => {})
  }, [])

  // Scroll to bottom when conversation grows
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  const submit = useCallback(async (question) => {
    if (!question?.trim() || loading) return
    const q = question.trim()
    setInput('')
    setLoading(true)

    // Add question immediately with loading state
    const tempId = Date.now()
    setConversation(prev => [...prev, { _id: tempId, question: q, loading: true }])

    try {
      const result = await api.ask(q, jurisdiction)
      setConversation(prev => prev.map(item =>
        item._id === tempId ? { ...result, question: q, _id: tempId, loading: false } : item
      ))
      // Refresh index status after a Q&A call
      api.indexStatus().then(setIndexStatus).catch(() => {})
    } catch (e) {
      setConversation(prev => prev.map(item =>
        item._id === tempId
          ? { question: q, answer: e.message || 'Request failed.', error: true, _id: tempId, loading: false }
          : item
      ))
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }, [loading, jurisdiction])

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(input)
    }
  }

  const rebuildIndex = async () => {
    setRebuilding(true)
    try {
      await api.rebuildIndex()
      // Poll status for up to 60s
      let attempts = 0
      const poll = setInterval(async () => {
        const s = await api.indexStatus()
        setIndexStatus(s)
        if (s.ready || ++attempts > 30) {
          clearInterval(poll)
          setRebuilding(false)
        }
      }, 2000)
    } catch {
      setRebuilding(false)
    }
  }

  const loadHistory = async () => {
    const data = await api.history()
    setHistory(data.items || [])
    setShowHistory(true)
  }

  const isEmpty = conversation.length === 0

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Main chat area ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '20px 28px 0', flexShrink: 0 }}>
          <SectionHeader
            title="Ask ARIS"
            subtitle="Regulatory Q&A grounded in your corpus"
            action={
              <div className="flex gap-2">
                <button
                  className="btn-ghost btn-sm"
                  onClick={loadHistory}
                  title="View Q&A history"
                >
                  <History size={13} /> History
                </button>
                <button
                  className="btn-secondary btn-sm"
                  onClick={rebuildIndex}
                  disabled={rebuilding}
                  title="Rebuild passage index from all baselines and documents"
                >
                  <RefreshCw size={13} style={{ animation: rebuilding ? 'spin 1s linear infinite' : 'none' }} />
                  {rebuilding ? 'Rebuilding…' : 'Rebuild Index'}
                </button>
              </div>
            }
          />

          {/* Index status bar */}
          {indexStatus && (
            <div style={{
              fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-3)',
              marginTop: 4, marginBottom: 4,
              display: 'flex', gap: 16, flexWrap: 'wrap',
            }}>
              <span style={{ color: indexStatus.ready ? 'var(--green)' : 'var(--text-3)' }}>
                ● {indexStatus.ready ? 'Index ready' : indexStatus.passage_count > 0 ? 'Index may be stale — Rebuild to refresh' : 'Building index…'}
              </span>
              {indexStatus.passage_count > 0 && (
                <span>{indexStatus.passage_count} passages</span>
              )}
              {indexStatus.baselines_indexed > 0 && (
                <span>{indexStatus.baselines_indexed} baselines</span>
              )}
              {indexStatus.documents_indexed > 0 && (
                <span>{indexStatus.documents_indexed} documents</span>
              )}
            </div>
          )}

          {/* Jurisdiction filter */}
          <div className="flex items-center gap-3" style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
            <Globe size={13} style={{ color: 'var(--text-3)' }} />
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Filter to jurisdiction:</span>
            <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
              {JURISDICTIONS.map(j => (
                <button
                  key={j}
                  className={jurisdiction === j ? 'btn-primary btn-sm' : 'btn-ghost btn-sm'}
                  style={{ fontSize: 11, padding: '3px 10px' }}
                  onClick={() => setJurisdiction(j)}
                >
                  {j || 'All'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Conversation area */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px 28px' }}>
          {isEmpty ? (
            <div style={{ maxWidth: 660, margin: '0 auto' }}>
              <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <div style={{
                  width: 56, height: 56, borderRadius: '50%',
                  background: 'var(--bg-3)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 16px',
                }}>
                  <Sparkles size={24} style={{ color: 'var(--accent)' }} />
                </div>
                <div style={{ fontSize: 18, fontWeight: 300, marginBottom: 6 }}>
                  Ask about AI regulation
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
                  Every answer is grounded in your corpus — 19 baseline regulations plus
                  all summarised documents. Sources are cited inline so you can verify
                  every claim.
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {STARTER_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    className="card card-hover"
                    style={{ padding: '12px 14px', textAlign: 'left', fontSize: 12,
                             lineHeight: 1.5, color: 'var(--text-2)', cursor: 'pointer' }}
                    onClick={() => submit(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 32 }}>
              {conversation.map((item, i) => (
                <AnswerBlock
                  key={item._id || i}
                  item={item}
                  onFollowUp={submit}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input bar */}
        <div style={{
          padding:    '14px 28px',
          borderTop:  '1px solid var(--border)',
          background: 'var(--bg)',
          flexShrink:  0,
        }}>
          <div style={{ maxWidth: 760, margin: '0 auto' }}>
            <div className="flex gap-2 items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about AI regulation… (Enter to send, Shift+Enter for new line)"
                disabled={loading}
                rows={2}
                style={{
                  flex:       1,
                  resize:     'none',
                  fontSize:   13,
                  lineHeight: 1.55,
                  padding:    '10px 14px',
                  borderRadius: 'var(--radius)',
                  border:     '1px solid var(--border)',
                  background: 'var(--bg-2)',
                  color:      'var(--text)',
                  fontFamily: 'inherit',
                }}
              />
              <button
                className="btn-primary"
                style={{ padding: '10px 16px', flexShrink: 0 }}
                onClick={() => submit(input)}
                disabled={loading || !input.trim()}
              >
                {loading ? <Spinner size={14} /> : <Send size={14} />}
              </button>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
              Answers draw from {indexStatus?.passage_count || '…'} passages across baselines and documents.
              {indexStatus && !indexStatus.ready && indexStatus.passage_count === 0 && ' Building index…'}
            </div>
          </div>
        </div>
      </div>

      {/* ── History sidebar ── */}
      {showHistory && (
        <div style={{
          width:      340,
          borderLeft: '1px solid var(--border)',
          overflow:   'auto',
          padding:    '20px 18px',
          background: 'var(--bg)',
          flexShrink: 0,
        }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Q&A History</div>
            <button className="btn-icon" onClick={() => setShowHistory(false)}>
              <X size={14} />
            </button>
          </div>
          {history.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No history yet.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {history.map(item => (
                <div
                  key={item.id}
                  className="card card-hover"
                  style={{ padding: '9px 12px', cursor: 'pointer' }}
                  onClick={() => {
                    submit(item.question)
                    setShowHistory(false)
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 500, lineHeight: 1.4, marginBottom: 3 }}>
                    {item.question}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    {item.asked_at?.slice(0, 10)} · {item.citations?.length || 0} sources
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
