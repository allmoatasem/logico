interface FilePickerProps {
  label: string
  value: string
  onChange: (path: string) => void
  placeholder?: string
}

declare global {
  interface Window {
    electronAPI?: {
      openFile: (opts?: unknown) => Promise<string | null>
      openFolder: () => Promise<string | null>
    }
  }
}

async function pickFile(): Promise<string | null> {
  if (window.electronAPI) return window.electronAPI.openFile()
  // Browser fallback: prompt
  return prompt('Enter file path:')
}

export default function FilePicker({ label, value, onChange, placeholder }: FilePickerProps) {
  const handleBrowse = async () => {
    const path = await pickFile()
    if (path) onChange(path)
  }

  return (
    <div className="file-row">
      <span className="file-label">{label}</span>
      <div className="file-input-row">
        <div className={`file-path ${value ? '' : 'empty'}`}>
          {value || (placeholder ?? 'No file selected')}
        </div>
        <button className="btn btn-browse btn-sm" onClick={handleBrowse}>
          Browse
        </button>
      </div>
    </div>
  )
}
