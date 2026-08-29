const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  navigate: (path) => ipcRenderer.send('navigate', path),
  toggleTheme: () => ipcRenderer.send('toggle-theme'),
  getTheme: () => ipcRenderer.invoke('get-theme'),
  getVersion: () => ipcRenderer.invoke('get-app-version'),
  isElectron: true,
  exportReport: () => ipcRenderer.send('export-report'),
  showShortcuts: () => ipcRenderer.send('show-shortcuts'),
  toggleCommandPalette: (callback) => ipcRenderer.on('toggle-command-palette', callback),
  platform: process.platform,
  setCursorPos: (x, y) => ipcRenderer.send('set-cursor-pos', x, y),
});
