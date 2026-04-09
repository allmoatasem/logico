import { useState } from 'react'
import { api, SnapshotInfo, DiffResult } from '../api'
import FilePicker from './FilePicker'

function DiffView({ diff }: { diff: DiffResult }) {
  if (diff.summary === 'identical') return <p style={{ color: 'var(--text-dim)', marginTop: 12 }}>No differences.</p>

  return (
    <div style={{ marginTop: 16 }}>
      {(diff.tempo_changed || diff.time_sig_changed || diff.key_sig_changed) && (
        <div className="diff-section">
          <div className="diff-section-title">Structure</div>
          {diff.tempo_changed    && <div className="diff-row diff-changed"><span className="diff-sign">~</span> Tempo changed</div>}
          {diff.time_sig_changed && <div className="diff-row diff-changed"><span className="diff-sign">~</span> Time signature changed</div>}
          {diff.key_sig_changed  && <div className="diff-row diff-changed"><span className="diff-sign">~</span> Key signature changed</div>}
        </div>
      )}

      {diff.added.length > 0 && (
        <div className="diff-section">
          <div className="diff-section-title">Added ({diff.added.length})</div>
          {diff.added.map((n, i) => (
            <div key={i} className="diff-row diff-added">
              <span className="diff-sign">+</span>
              <span className="diff-name">{n.name}</span>
              <span className="diff-pos">pos {n.position}  dur {n.duration}</span>
              <span className="diff-track">{n.track}</span>
            </div>
          ))}
        </div>
      )}

      {diff.removed.length > 0 && (
        <div className="diff-section">
          <div className="diff-section-title">Removed ({diff.removed.length})</div>
          {diff.removed.map((n, i) => (
            <div key={i} className="diff-row diff-removed">
              <span className="diff-sign">−</span>
              <span className="diff-name">{n.name}</span>
              <span className="diff-pos">pos {n.position}  dur {n.duration}</span>
              <span className="diff-track">{n.track}</span>
            </div>
          ))}
        </div>
      )}

      {diff.changed.length > 0 && (
        <div className="diff-section">
          <div className="diff-section-title">Changed ({diff.changed.length})</div>
          {diff.changed.map((n, i) => (
            <div key={i} className="diff-row diff-changed">
              <span className="diff-sign">~</span>
              <span className="diff-name">{n.name}</span>
              <span className="diff-pos">
                {n.old_duration !== n.new_duration && `dur ${n.old_duration}→${n.new_duration}`}
                {n.old_velocity !== n.new_velocity && ` vel ${n.old_velocity}→${n.new_velocity}`}
              </span>
              <span className="diff-track">{n.track}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function HistoryView() {
  const [filePath, setFilePath] = useState('')
  const [snapshots, setSnapshots] = useState<SnapshotInfo[]>([])
  const [selectedSnap, setSelectedSnap] = useState<number | null>(null)
  const [diff, setDiff] = useState<DiffResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [reverting, setReverting] = useState(false)
  const [revertResult, setRevertResult] = useState<string | null>(null)

  const handleSetFile = async (p: string) => {
    setFilePath(p); setSnapshots([]); setSelectedSnap(null); setDiff(null)
    if (!p) return
    setLoading(true)
    try {
      const r = await api.log(p)
      setSnapshots(r.snapshots)
    } catch { setSnapshots([]) }
    finally { setLoading(false) }
  }

  const handleSelectSnap = async (n: number) => {
    setSelectedSnap(n); setDiff(null); setRevertResult(null)
    try {
      const d = await api.diff({ path_a: filePath, snapshot_b: n })
      setDiff(d)
    } catch { setDiff(null) }
  }

  const handleRevert = async () => {
    if (!filePath || selectedSnap === null) return
    setReverting(true); setRevertResult(null)
    try {
      const r = await api.revert(filePath, selectedSnap)
      setRevertResult(`Restored @${r.restored_snapshot}. Current state backed up as @${r.backup_snapshot}.`)
      const log = await api.log(filePath)
      setSnapshots(log.snapshots)
    } catch (e: unknown) {
      setRevertResult(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setReverting(false)
    }
  }

  const snapshotList = [...snapshots].reverse() // newest first

  return (
    <div className="panel">
      <div className="panel-title">History</div>

      <FilePicker label="Project file" value={filePath} onChange={handleSetFile} placeholder="Pick any project file" />

      {loading && <div style={{ marginTop: 16, color: 'var(--text-dim)' }}><span className="spinner" /> Loading snapshots…</div>}

      {!loading && filePath && snapshots.length === 0 && (
        <div className="empty-state">
          <div className="icon">◷</div>
          <p>No snapshots yet.</p>
          <p style={{ fontSize: 12, marginTop: 6 }}>Run a sync to create the first one.</p>
        </div>
      )}

      {snapshotList.length > 0 && (
        <div style={{ display: 'flex', gap: 24, marginTop: 8, height: 'calc(100vh - 220px)', overflow: 'hidden' }}>
          {/* Snapshot list */}
          <div style={{ width: 280, flexShrink: 0, overflowY: 'auto' }}>
            <div className="snapshot-list">
              {snapshotList.map((s, i) => (
                <div
                  key={s.number}
                  className={`snapshot-item ${selectedSnap === s.number ? 'selected' : ''}`}
                  onClick={() => handleSelectSnap(s.number)}
                >
                  <span className="snap-num">@{s.number}</span>
                  <div className="snap-meta">
                    <div className="snap-msg">{s.message || '(no message)'}</div>
                    <div className="snap-ts">{s.timestamp.slice(0, 19).replace('T', ' ')}</div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                    <span className="snap-summary">{s.summary}</span>
                    {i === 0 && <span className="snap-latest">latest</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Diff panel */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {selectedSnap !== null && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>current → @{selectedSnap}</span>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleRevert}
                    disabled={reverting}
                  >
                    {reverting ? <><span className="spinner" /> Reverting…</> : `↩  Restore @${selectedSnap}`}
                  </button>
                </div>

                {revertResult && (
                  <div className="result-box success" style={{ marginBottom: 12 }}>
                    <span className="status-dot green" />{revertResult}
                  </div>
                )}

                {diff ? <DiffView diff={diff} /> : <div style={{ color: 'var(--text-dim)' }}><span className="spinner" /></div>}
              </>
            )}

            {selectedSnap === null && (
              <div className="empty-state" style={{ paddingTop: 40 }}>
                <div className="icon" style={{ fontSize: 28 }}>←</div>
                <p>Select a snapshot to see the diff</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
