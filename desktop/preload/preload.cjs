const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktop', {
  startBackend: () => ipcRenderer.invoke('backend:start-and-wait'),
  getMeta: () => ipcRenderer.invoke('backend:meta'),
});
