import { useState } from 'react'
import SyncView from './components/SyncView'
import HistoryView from './components/HistoryView'
import WatchView from './components/WatchView'

type View = 'sync' | 'history' | 'watch'

const NAV = [
  { id: 'sync' as View,    icon: '⇄',  label: 'Sync' },
  { id: 'history' as View, icon: '◷',  label: 'History' },
  { id: 'watch' as View,   icon: '◉',  label: 'Watch' },
]

export default function App() {
  const [view, setView] = useState<View>('sync')

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">Logi<span>co</span></div>
        <nav className="sidebar-nav">
          {NAV.map((n) => (
            <button
              key={n.id}
              className={`nav-item no-drag ${view === n.id ? 'active' : ''}`}
              onClick={() => setView(n.id)}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="main">
        <div className="titlebar" />
        {view === 'sync'    && <SyncView />}
        {view === 'history' && <HistoryView />}
        {view === 'watch'   && <WatchView />}
      </div>
    </div>
  )
}
