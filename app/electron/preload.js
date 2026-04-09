const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getServerPort: () => ipcRenderer.invoke('get-server-port'),
  openFile: (options) => ipcRenderer.invoke('open-file-dialog', options),
  openFolder: () => ipcRenderer.invoke('open-folder-dialog'),
})
