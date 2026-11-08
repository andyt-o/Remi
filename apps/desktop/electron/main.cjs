const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('node:path');

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1120,
    minHeight: 760,
    title: 'Remi',
    icon: path.join(__dirname, '../assets/icons/remi.png'),
    backgroundColor: '#f7f7f3',
    frame: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.webContents.on('console-message', (_event, level, message, line, source) => {
    console.log(`[renderer:${level}] ${message} (${source}:${line})`);
  });
  window.webContents.on('did-fail-load', (_event, code, description, url) => {
    console.error(`[renderer:load-failed] ${description} (${code}) ${url}`);
  });
  window.webContents.on('render-process-gone', (_event, details) => {
    console.error('[renderer:process-gone]', details);
  });

  window.webContents.setZoomFactor(1.1);
  const applyZoom = (factor) => {
    const zoom = Math.max(0.8, Math.min(1.5, factor));
    window.webContents.setZoomFactor(zoom);
    window.webContents.send('window:zoom-changed', zoom);
  };
  window.webContents.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown' || !(input.control || input.meta)) return;
    const key = input.key.toLowerCase();
    if (key === '+' || key === '=' || key === 'add') {
      event.preventDefault();
      applyZoom(window.webContents.getZoomFactor() + 0.1);
    } else if (key === '-' || key === '_' || key === 'subtract') {
      event.preventDefault();
      applyZoom(window.webContents.getZoomFactor() - 0.1);
    } else if (key === '0') {
      event.preventDefault();
      applyZoom(1);
    }
  });

  if (!app.isPackaged) {
    window.loadURL('http://127.0.0.1:5173');
    if (process.env.REMI_DEVTOOLS === '1') window.webContents.openDevTools({ mode: 'detach' });
  } else {
    window.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(() => {
  ipcMain.on('window:minimize', (event) => BrowserWindow.fromWebContents(event.sender)?.minimize());
  ipcMain.on('window:toggle-maximize', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (!window) return;
    if (window.isMaximized()) window.unmaximize();
    else window.maximize();
  });
  ipcMain.on('window:close', (event) => BrowserWindow.fromWebContents(event.sender)?.close());
  ipcMain.handle('window:get-zoom', (event) => BrowserWindow.fromWebContents(event.sender)?.webContents.getZoomFactor() ?? 1);
  ipcMain.handle('window:set-zoom', (event, factor) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (!window || typeof factor !== 'number' || !Number.isFinite(factor)) return 1;
    const zoom = Math.max(0.8, Math.min(1.5, factor));
    window.webContents.setZoomFactor(zoom);
    window.webContents.send('window:zoom-changed', zoom);
    return zoom;
  });
  ipcMain.handle('agent:dependency-health', async () => {
    try {
      const response = await fetch('http://localhost:8000/health/dependencies', {
        signal: AbortSignal.timeout(3000),
      });
      if (!response.ok) throw new Error(`Agent health returned ${response.status}`);
      return response.json();
    } catch {
      return {
        agent_api: { status: 'offline', detail: 'Agent API is not reachable at localhost:8000.' },
        mock_pos: { status: 'unknown', detail: 'Cannot check connectors while the agent API is offline.' },
        elevenlabs: { status: 'unknown', detail: 'Provider status is unavailable while the agent API is offline.' },
        daytona: { status: 'unknown', detail: 'Provider status is unavailable while the agent API is offline.' },
      };
    }
  });
  ipcMain.handle('voice:session-greeting', async (_event, { role, user }) => {
    try {
      const response = await fetch('http://localhost:8000/voice/greeting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, user }),
        signal: AbortSignal.timeout(12000),
      });
      if (!response.ok) return { ok: false };
      const audio = Buffer.from(await response.arrayBuffer()).toString('base64');
      return { ok: true, audio };
    } catch {
      return { ok: false };
    }
  });
  ipcMain.handle('voice:turn', async (_event, { sessionId, role, user, audioBase64, mimeType }) => {
    try {
      const form = new FormData();
      form.append('session_id', sessionId);
      form.append('role', role);
      form.append('user', user);
      form.append('audio', new Blob([Buffer.from(audioBase64, 'base64')], { type: mimeType || 'audio/webm' }), 'staff-turn.webm');
      const response = await fetch('http://localhost:8000/voice/turn', {
        method: 'POST',
        body: form,
        signal: AbortSignal.timeout(60000),
      });
      const result = await response.json();
      return response.ok ? { ok: true, ...result } : { ok: false, error: result.detail || 'Voice turn failed.' };
    } catch {
      return { ok: false, error: 'Could not reach the Remi voice service.' };
    }
  });
  ipcMain.handle('voice:reply', async (_event, payload) => {
    try {
      const response = await fetch('http://localhost:8000/voice/reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000),
      });
      const result = await response.json();
      return response.ok ? { ok: true, ...result } : { ok: false, error: result.detail || 'Voice reply failed.' };
    } catch {
      return { ok: false, error: 'Could not reach the Remi voice service.' };
    }
  });
  ipcMain.handle('voice:speech', async (_event, text) => {
    try {
      const response = await fetch('http://localhost:8000/voice/speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: AbortSignal.timeout(30000),
      });
      if (!response.ok) return { ok: false };
      return { ok: true, audio: Buffer.from(await response.arrayBuffer()).toString('base64') };
    } catch {
      return { ok: false };
    }
  });
  ipcMain.handle('agent:start-daytona-report', async (_event, role) => {
    try {
      const response = await fetch('http://localhost:8000/tasks/daytona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind: 'next_delivery_report', role }),
        signal: AbortSignal.timeout(5000),
      });
      const result = await response.json();
      return response.ok ? { ok: true, ...result } : { ok: false, error: result.detail || 'Could not start Daytona task.' };
    } catch {
      return { ok: false, error: 'Remi Agent API is unavailable.' };
    }
  });
  ipcMain.handle('agent:get-daytona-report', async (_event, taskId) => {
    try {
      const response = await fetch(`http://localhost:8000/tasks/daytona/${encodeURIComponent(taskId)}`, {
        signal: AbortSignal.timeout(5000),
      });
      const result = await response.json();
      return response.ok ? result : { status: 'failed', error: result.detail || 'Could not read Daytona task.' };
    } catch {
      return { status: 'failed', error: 'Remi Agent API is unavailable.' };
    }
  });

  if (process.platform === 'darwin' && app.dock) {
    app.dock.setIcon(path.join(__dirname, '../assets/icons/remi.png'));
  }
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
