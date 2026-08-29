// ── Quantive Desktop — Electron Wrapper ──────────────────────────────
// Government-grade desktop application.
// React frontend + Python FastAPI backend, all running locally.
// Zero internet required. Air-gapped deployment ready.

const { app, BrowserWindow, Menu, globalShortcut, shell, ipcMain, nativeTheme, protocol } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow = null;
let backendProcess = null;
let frontendServer = null;

const isDev = !app.isPackaged;
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 5199;

// ── Backend Management ───────────────────────────────────────────────

function startBackend() {
  const backendPath = path.join(__dirname, '..', 'backend');
  console.log(`[Quantive] Starting Python backend from ${backendPath}`);

  backendProcess = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], {
    cwd: backendPath,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  backendProcess.stdout?.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr?.on('data', (data) => {
    console.error(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`[Quantive] Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (backendProcess) {
    console.log('[Quantive] Stopping backend...');
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

// ── Frontend Static Server ───────────────────────────────────────────

function startFrontendServer() {
  const distPath = path.join(__dirname, 'dist');

  const MIME = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf',
  };

  frontendServer = http.createServer((req, res) => {
    let url = req.url.split('?')[0];
    if (url === '/') url = '/index.html';

    const filePath = path.join(distPath, url);

    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const ext = path.extname(filePath);
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      fs.createReadStream(filePath).pipe(res);
    } else {
      // SPA fallback — serve index.html for client-side routes
      const indexPath = path.join(distPath, 'index.html');
      res.writeHead(200, { 'Content-Type': 'text/html' });
      fs.createReadStream(indexPath).pipe(res);
    }
  });

  frontendServer.listen(FRONTEND_PORT, '127.0.0.1', () => {
    console.log(`[Quantive] Frontend serving on http://127.0.0.1:${FRONTEND_PORT}`);
  });
}

function stopFrontendServer() {
  if (frontendServer) {
    frontendServer.close();
    frontendServer = null;
  }
}

// ── Window Creation ──────────────────────────────────────────────────

function createWindow() {
  const isWin11 = process.platform === 'win32';
  const isMac = process.platform === 'darwin';
  const distPath = path.join(__dirname, 'dist');

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'Quantive',
    icon: path.join(__dirname, 'public', 'favicon.ico'),
    backgroundColor: '#0C0C0E',
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    titleBarOverlay: isWin11 ? {
      color: '#0C0C0E',
      symbolColor: '#c8a951',
      height: 32,
    } : undefined,
    vibrancy: isMac ? 'under-window' : undefined,
    visualEffectState: 'active',
    trafficLightPosition: isMac ? { x: 16, y: 16 } : undefined,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'electron-preload.js'),
      sandbox: true,
    },
    show: false,
  });

  // Load from local HTTP server (backdrop-filter / glass needs HTTP, not file://)
  mainWindow.loadURL(`http://127.0.0.1:${FRONTEND_PORT}`);

  // Show when ready — no flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Security: open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── Menu ─────────────────────────────────────────────────────────────

function createMenu() {
  const template = [
    {
      label: 'Quantive',
      submenu: [
        { label: 'About Quantive', role: 'about' },
        { type: 'separator' },
        { label: 'Preferences', accelerator: 'CmdOrCtrl+,', click: () => mainWindow?.webContents.send('navigate', '/settings') },
        { type: 'separator' },
        { label: 'Quit', accelerator: 'CmdOrCtrl+Q', role: 'quit' },
      ],
    },
    {
      label: 'File',
      submenu: [
        { label: 'New Portfolio', accelerator: 'CmdOrCtrl+N', click: () => mainWindow?.webContents.send('navigate', '/portfolios/new') },
        { label: 'New Optimization', accelerator: 'CmdOrCtrl+Shift+N', click: () => mainWindow?.webContents.send('navigate', '/optimizations/new') },
        { type: 'separator' },
        { label: 'Export Report', accelerator: 'CmdOrCtrl+E', click: () => mainWindow?.webContents.send('export-report') },
        { type: 'separator' },
        { label: 'Close', role: 'close' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { label: 'Dashboard', accelerator: 'CmdOrCtrl+D', click: () => mainWindow?.webContents.send('navigate', '/dashboard') },
        { label: 'Portfolio', accelerator: 'CmdOrCtrl+1', click: () => mainWindow?.webContents.send('navigate', '/portfolios') },
        { label: 'Market Data', accelerator: 'CmdOrCtrl+2', click: () => mainWindow?.webContents.send('navigate', '/market') },
        { label: 'Risk', accelerator: 'CmdOrCtrl+3', click: () => mainWindow?.webContents.send('navigate', '/risk') },
        { label: 'Optimize', accelerator: 'CmdOrCtrl+4', click: () => mainWindow?.webContents.send('navigate', '/optimizations/new') },
        { type: 'separator' },
        { label: 'Toggle Dark Mode', accelerator: 'CmdOrCtrl+Shift+D', click: () => mainWindow?.webContents.send('toggle-theme') },
        { type: 'separator' },
        { label: 'Reload', accelerator: 'CmdOrCtrl+R', role: 'reload' },
        { label: 'Force Reload', accelerator: 'CmdOrCtrl+Shift+R', role: 'forceReload' },
        { label: 'Toggle Developer Tools', accelerator: 'F12', role: 'toggleDevTools' },
        { type: 'separator' },
        { label: 'Toggle Fullscreen', accelerator: 'F11', role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        { label: 'Documentation', click: () => shell.openExternal('https://docs.quantive.app') },
        { label: 'Keyboard Shortcuts', accelerator: 'CmdOrCtrl+/', click: () => mainWindow?.webContents.send('show-shortcuts') },
        { type: 'separator' },
        { label: 'Report Issue', click: () => shell.openExternal('https://github.com/quantive/quantive/issues') },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── App Lifecycle ────────────────────────────────────────────────────

app.whenReady().then(() => {
  startBackend();
  startFrontendServer();
  createWindow();
  createMenu();

  // Global shortcuts
  globalShortcut.register('CmdOrCtrl+Shift+Space', () => {
    mainWindow?.webContents.send('toggle-command-palette');
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopBackend();
  stopFrontendServer();
  globalShortcut.unregisterAll();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

// ── IPC Handlers ─────────────────────────────────────────────────────

ipcMain.handle('get-theme', () => {
  return nativeTheme.shouldUseDarkColors ? 'dark' : 'light';
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('get-backend-status', () => {
  return { running: backendProcess !== null, port: BACKEND_PORT };
});

ipcMain.on('set-cursor-pos', (_event, x, y) => {
  if (mainWindow) {
    mainWindow.webContents.executeJavaScript(
      `document.documentElement.style.setProperty('--cursor-x', '${x}%');
       document.documentElement.style.setProperty('--cursor-y', '${y}%');
       document.documentElement.style.setProperty('--cursor-x-raw', '${x / 100}');
       document.documentElement.style.setProperty('--cursor-y-raw', '${y / 100}');`
    );
  }
});
