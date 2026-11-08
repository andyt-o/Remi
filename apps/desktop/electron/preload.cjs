const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('remiWindow', {
  minimize: () => ipcRenderer.send('window:minimize'),
  toggleMaximize: () => ipcRenderer.send('window:toggle-maximize'),
  close: () => ipcRenderer.send('window:close'),
  getDependencyHealth: () => ipcRenderer.invoke('agent:dependency-health'),
  synthesizeSessionGreeting: (role, user) => ipcRenderer.invoke('voice:session-greeting', { role, user }),
  processVoiceTurn: (payload) => ipcRenderer.invoke('voice:turn', payload),
  processVoiceReply: (payload) => ipcRenderer.invoke('voice:reply', payload),
  synthesizeText: (text) => ipcRenderer.invoke('voice:speech', text),
  startDaytonaReport: (role) => ipcRenderer.invoke('agent:start-daytona-report', role),
  getDaytonaReport: (taskId) => ipcRenderer.invoke('agent:get-daytona-report', taskId),
  getZoomFactor: () => ipcRenderer.invoke('window:get-zoom'),
  setZoomFactor: (factor) => ipcRenderer.invoke('window:set-zoom', factor),
  onZoomChanged: (callback) => {
    const listener = (_event, factor) => callback(factor);
    ipcRenderer.on('window:zoom-changed', listener);
    return () => ipcRenderer.removeListener('window:zoom-changed', listener);
  },
});
