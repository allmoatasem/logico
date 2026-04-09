import { useState } from 'react'
import { api, ProjectInfo } from '../api'
import FilePicker from './FilePicker'

function ProjectCard({ info }: { info: ProjectInfo }) {
  const totalNotes = info.tracks.reduce((s, t) => s + t.note_count, 0)
  const tempo = info.tempo_events[0]?.bpm ?? '—'
  const timeSig = info.time_signatures[0]
    ? `${info.time_signatures[0].numerator}/${info.time_signatures[0].denominator}`
    : '—'
  const keySig = info.key_signatures[0]?.key_name ?? '—'

  return (
    <div className="project-card">
      <h3>{info.title || 'Untitled'} <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>· {info.source_format}</span></h3>
      <div className="info-row"><span className="info-key">Tempo</span><span className="info-val">{tempo} BPM</span></div>
      <div className="info-row"><span className="info-key">Time sig</span><span className="info-val">{timeSig}</span></div>
      <div className="info-row"><span className="info-key">Key</span><span className="info-val">{keySig}</span></div>
      <div className="info-row"><span className="info-key">Tracks</span><span className="info-val">{info.tracks.length}</span></div>
      <div className="info-row"><span className="info-key">Notes</span><span className="info-val">{totalNotes}</span></div>
      {info.tracks.map((t) => (
        <div className="info-row" key={t.name} style={{ paddingLeft: 12 }}>
          <span className="info-key" style={{ fontStyle: 'italic' }}>{t.name || '(unnamed)'}</span>
          <span className="info-val">{t.note_count} notes</span>
        </div>
      ))}
    </div>
  )
}

export default function SyncView() {
  const [source, setSource] = useState('')
  const [dest, setDest] = useState('')
  const [sourceInfo, setSourceInfo] = useState<ProjectInfo | null>(null)
  const [destInfo, setDestInfo] = useState<ProjectInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  const loadInfo = async (path: string, setter: (p: ProjectInfo | null) => void) => {
    if (!path) { setter(null); return }
    try { setter(await api.read(path)) } catch { setter(null) }
  }

  const handleSetSource = (p: string) => { setSource(p); setResult(null); loadInfo(p, setSourceInfo) }
  const handleSetDest   = (p: string) => { setDest(p);   setResult(null); loadInfo(p, setDestInfo) }

  const handleSync = async () => {
    if (!source || !dest) return
    setLoading(true); setResult(null)
    try {
      const r = await api.sync(source, dest)
      setResult({ ok: true, message: `${r.note_count} notes synced → snapshot @${r.snapshot} saved` })
      loadInfo(dest, setDestInfo)
    } catch (e: unknown) {
      setResult({ ok: false, message: e instanceof Error ? e.message : String(e) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-title">Sync</div>

      <FilePicker label="Source" value={source} onChange={handleSetSource} placeholder="Pick a .logicx, .dorico, or .stf file" />
      <FilePicker label="Destination" value={dest} onChange={handleSetDest} placeholder="Pick the destination project file" />

      <div style={{ marginTop: 20 }}>
        <button
          className="btn btn-primary"
          disabled={!source || !dest || loading}
          onClick={handleSync}
        >
          {loading ? <><span className="spinner" /> Syncing…</> : '⇄  Sync Now'}
        </button>
      </div>

      {result && (
        <div className={`result-box ${result.ok ? 'success' : 'error'}`} style={{ marginTop: 16 }}>
          <span className={`status-dot ${result.ok ? 'green' : 'red'}`} />
          {result.message}
        </div>
      )}

      {(sourceInfo || destInfo) && (
        <>
          <hr className="divider" />
          <div className="two-col">
            {sourceInfo ? <ProjectCard info={sourceInfo} /> : <div className="project-card" style={{ color: 'var(--text-dim)' }}>—</div>}
            {destInfo   ? <ProjectCard info={destInfo} />   : <div className="project-card" style={{ color: 'var(--text-dim)' }}>—</div>}
          </div>
        </>
      )}
    </div>
  )
}
