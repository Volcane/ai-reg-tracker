import { useState } from 'react'
import { CheckCircle2, XCircle, ExternalLink, AlertTriangle, Info } from 'lucide-react'
import { SectionHeader } from '../components.jsx'

// What you lose without each key — shown when key is not configured
const KEY_IMPACT = {
  anthropic: {
    loses: [
      'AI summarisation — documents fetched but never interpreted',
      'Plain-English summaries, urgency ratings, requirements lists',
      'Compliance checklists and change detection (diffs)',
      'Ask ARIS Q&A, Briefs, Synthesis, Gap Analysis',
    ],
    severity: 'critical',
  },
  regulations_gov: {
    loses: [
      'Federal rulemaking dockets (proposed rules, public comments)',
      'NPRM tracking — rules in progress before they finalise',
    ],
    severity: 'moderate',
  },
  congress_gov: {
    loses: [
      'US Congressional bill tracking (House and Senate)',
      'Committee hearing schedules and markup activity',
    ],
    severity: 'moderate',
  },
  legiscan: {
    loses: [
      'All US state legislature monitoring (all 5 enabled states)',
      'State bill introductions, amendments, passage events',
      'State-level AI regulation and privacy bill tracking',
    ],
    severity: 'high',
  },
  courtlistener: {
    loses: [
      'Federal court opinions and litigation tracking',
      'CourtListener enforcement actions in the Enforcement view',
    ],
    severity: 'low',
  },
}

export default function SettingsView({ status }) {
  const [expandedKey, setExpandedKey] = useState(null)
  const keys  = status?.api_keys || {}
  const stats = status?.stats    || {}

  const apiKeyDefs = [
    {
      key:      'anthropic',
      label:    'Anthropic API Key',
      url:      'https://console.anthropic.com/settings/keys',
      required: true,
      note:     'Powers all AI analysis — summarisation, diffs, Q&A, briefs, gap analysis',
    },
    {
      key:      'legiscan',
      label:    'LegiScan API Key',
      url:      'https://legiscan.com/legiscan',
      required: false,
      note:     'US state legislature monitoring — all 5 enabled states require this',
    },
    {
      key:      'regulations_gov',
      label:    'Regulations.gov API Key',
      url:      'https://open.gsa.gov/api/regulationsgov/',
      required: false,
      note:     'Federal rulemaking dockets, NPRMs, and public comment data',
    },
    {
      key:      'congress_gov',
      label:    'Congress.gov API Key',
      url:      'https://api.congress.gov/sign-up/',
      required: false,
      note:     'US Congressional bills, committee hearings, markup schedules',
    },
    {
      key:      'courtlistener',
      label:    'CourtListener API Key',
      url:      'https://www.courtlistener.com/sign-in/',
      required: false,
      note:     'Federal court opinions and litigation data',
    },
  ]

  const missingRequired  = apiKeyDefs.filter(d => d.required  && !keys[d.key])
  const missingOptional  = apiKeyDefs.filter(d => !d.required && !keys[d.key])
  const configuredCount  = apiKeyDefs.filter(d => keys[d.key]).length

  return (
    <div style={{ padding: '28px 32px', maxWidth: 760 }}>
      <SectionHeader title="Settings" subtitle="System configuration and API key status" />

      {/* Status summary */}
      {missingRequired.length > 0 && (
        <div style={{
          marginBottom: 24, padding: '12px 16px',
          background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.3)',
          borderRadius: 'var(--radius)', display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <AlertTriangle size={15} style={{ color: 'var(--red)', flexShrink: 0, marginTop: 1 }} />
          <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5 }}>
            <strong style={{ color: 'var(--red)' }}>Anthropic API key not configured.</strong>{' '}
            ARIS can fetch documents but cannot summarise, diff, or answer questions without it.
            Set <code style={{ background: 'var(--bg-4)', padding: '1px 4px', borderRadius: 3 }}>ANTHROPIC_API_KEY</code> in{' '}
            <code style={{ background: 'var(--bg-4)', padding: '1px 4px', borderRadius: 3 }}>config/keys.env</code> and restart the server.
          </div>
        </div>
      )}

      {missingRequired.length === 0 && missingOptional.length > 0 && (
        <div style={{
          marginBottom: 24, padding: '10px 14px',
          background: 'var(--bg-3)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <Info size={14} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
          <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
            {configuredCount}/{apiKeyDefs.length} keys configured.{' '}
            {missingOptional.length} optional {missingOptional.length === 1 ? 'key' : 'keys'} not set —
            click any unconfigured key to see what you're missing.
          </div>
        </div>
      )}

      {/* API Keys */}
      <div style={{ marginBottom: 32 }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)',
          textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 14,
        }}>API Keys</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {apiKeyDefs.map(def => {
            const configured = !!keys[def.key]
            const impact     = KEY_IMPACT[def.key]
            const isExpanded = expandedKey === def.key
            const sevColor   = !configured
              ? (def.required ? 'var(--red)' : impact?.severity === 'high' ? 'var(--orange)' : impact?.severity === 'moderate' ? 'var(--yellow)' : 'var(--text-3)')
              : 'var(--green)'

            return (
              <div key={def.key}>
                <div
                  onClick={() => !configured && setExpandedKey(isExpanded ? null : def.key)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 12,
                    padding: '13px 15px',
                    background: 'var(--bg-2)',
                    border: `1px solid ${configured ? 'var(--green-dim)' : def.required ? 'rgba(224,82,82,0.4)' : 'var(--border)'}`,
                    borderRadius: isExpanded ? 'var(--radius) var(--radius) 0 0' : 'var(--radius)',
                    cursor: configured ? 'default' : 'pointer',
                    transition: 'border-color 0.15s',
                  }}
                >
                  {configured
                    ? <CheckCircle2 size={16} style={{ color: 'var(--green)', flexShrink: 0, marginTop: 1 }} />
                    : <XCircle     size={16} style={{ color: sevColor, flexShrink: 0, marginTop: 1 }} />
                  }

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{def.label}</span>
                      {def.required && (
                        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--red)', background: 'rgba(224,82,82,0.12)', padding: '1px 6px', borderRadius: 3 }}>
                          REQUIRED
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>{def.note}</div>

                    {!configured && (
                      <a href={def.url} target="_blank" rel="noreferrer"
                        onClick={e => e.stopPropagation()}
                        style={{ fontSize: 12, color: 'var(--accent)', marginTop: 6, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        Get free key <ExternalLink size={11} />
                      </a>
                    )}
                  </div>

                  <div style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)', flexShrink: 0,
                    padding: '3px 8px', borderRadius: 4,
                    background: configured ? 'var(--green-dim)' : 'var(--bg-4)',
                    color: configured ? 'var(--green)' : 'var(--text-3)',
                  }}>
                    {configured ? 'CONFIGURED' : 'NOT SET'}
                  </div>
                </div>

                {/* Impact panel — shown when unconfigured and expanded */}
                {!configured && isExpanded && impact && (
                  <div style={{
                    padding: '12px 15px',
                    background: 'var(--bg-3)',
                    border: `1px solid ${def.required ? 'rgba(224,82,82,0.4)' : 'var(--border)'}`,
                    borderTop: 'none',
                    borderRadius: '0 0 var(--radius) var(--radius)',
                  }}>
                    <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: sevColor, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                      Without this key you lose:
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                      {impact.loses.map((loss, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12, color: 'var(--text-2)', lineHeight: 1.4 }}>
                          <span style={{ color: sevColor, flexShrink: 0, marginTop: 1 }}>✕</span>
                          {loss}
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: 12, padding: '8px 10px', background: 'var(--bg-2)', borderRadius: 'var(--radius)', fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                      Set <span style={{ color: 'var(--accent)' }}>{def.key.toUpperCase()}_KEY</span> in{' '}
                      <span style={{ color: 'var(--text-2)' }}>config/keys.env</span> and restart the server
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.6 }}>
          All keys are set in{' '}
          <code style={{ background: 'var(--bg-4)', padding: '1px 5px', borderRadius: 3 }}>config/keys.env</code>{' '}
          — never committed to version control. Restart the server after changes.
        </div>
      </div>

      {/* Enabled Jurisdictions */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
          Enabled Jurisdictions
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              US States
              {!keys.legiscan && <span style={{ fontSize: 10, color: 'var(--orange)', fontFamily: 'var(--font-mono)' }}>LegiScan key required</span>}
            </div>
            {(status?.enabled_states || []).map(s => (
              <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, marginBottom: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: keys.legiscan ? 'var(--green)' : 'var(--orange)' }} />
                <span style={{ color: keys.legiscan ? 'var(--text-2)' : 'var(--text-3)' }}>{s}</span>
                {!keys.legiscan && <span style={{ fontSize: 10, color: 'var(--text-3)' }}>inactive</span>}
              </div>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 8 }}>International</div>
            {(status?.enabled_international || []).map(j => (
              <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, marginBottom: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)' }} />
                {j}
              </div>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.6 }}>
          To add or remove jurisdictions, edit{' '}
          <code style={{ background: 'var(--bg-4)', padding: '1px 5px', borderRadius: 3 }}>config/jurisdictions.py</code>.
        </div>
      </div>

      {/* Database stats — split by domain */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
          Database
        </div>
        <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
          {[
            ['Total documents',        stats.total_documents,     null],
            ['AI regulation docs',     stats.ai_documents,        'var(--accent)'],
            ['Data privacy docs',      stats.privacy_documents,   '#7c9ef7'],
            ['Summarised',             stats.total_summaries,     null],
            ['Pending summarisation',  stats.pending_summaries,   stats.pending_summaries > 0 ? 'var(--yellow)' : null],
            ['Total changes detected', stats.total_diffs,         null],
            ['Unreviewed changes',     stats.unreviewed_diffs,    stats.unreviewed_diffs > 0 ? 'var(--orange)' : null],
            ['Critical changes',       stats.critical_diffs,      stats.critical_diffs > 0 ? 'var(--red)' : null],
            ['Enforcement actions',    stats.enforcement_actions, null],
          ].map(([label, val, color]) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 14px', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
              <span style={{ color: 'var(--text-2)' }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: color || 'var(--text)' }}>{val ?? '—'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* CLI quick reference — updated with domain flag */}
      <div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
          CLI Quick Reference
        </div>
        <div style={{
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '14px 16px',
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          lineHeight: 2,
          color: 'var(--text-2)',
        }}>
          {[
            ['python main.py run --domain both',     'Full pipeline: fetch + summarize (AI + Privacy)'],
            ['python main.py run --domain ai',       'AI regulation only'],
            ['python main.py run --domain privacy',  'Data privacy only'],
            ['python main.py fetch --source EU',     'Fetch EU sources only'],
            ['python main.py summarize',             'Summarize pending docs'],
            ['python main.py changes',               'Show recent changes'],
            ['python main.py watch --interval 24',   'Run every 24h'],
          ].map(([cmd, desc]) => (
            <div key={cmd} style={{ display: 'flex', gap: 16 }}>
              <span style={{ color: 'var(--accent)', flexShrink: 0 }}>{cmd}</span>
              <span style={{ color: 'var(--text-3)' }}># {desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
