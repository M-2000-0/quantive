// ── Quantive Desktop — Electron Wrapper ──────────────────────────────
// Government-grade desktop application.
// Jinja2 templates served by Python FastAPI backend, all running locally.
// Zero internet required. Air-gapped deployment ready.

const { app, BrowserWindow, Menu, globalShortcut, shell, ipcMain, nativeTheme } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow = null;
let backendProcess = null;

const isDev = !app.isPackaged;
const BACKEND_PORT = 8000;

function waitForBackend(url, maxRetries = 30, delayMs = 500) {
  return new Promise((resolve, reject) => {
    let retries = 0;
    const check = () => {
      http.get(url, (res) => {
        res.resume();
        resolve();
      }).on('error', () => {
        if (++retries >= maxRetries) return reject(new Error('Backend did not start'));
        setTimeout(check, delayMs);
      });
    };
    check();
  });
}

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

// ── Window Creation ──────────────────────────────────────────────────

function createWindow() {
  const isWin11 = process.platform === 'win32';
  const isMac = process.platform === 'darwin';

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

  // Load from FastAPI backend — serves Jinja2 templates
  mainWindow.loadURL(`http://127.0.0.1:${BACKEND_PORT}`);

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
  const nav = (route) => () => mainWindow?.loadURL(`http://127.0.0.1:${BACKEND_PORT}${route}`);

  const template = [
    {
      label: 'Quantive',
      submenu: [
        { label: 'About Quantive', role: 'about' },
        { type: 'separator' },
        { label: 'Preferences', accelerator: 'CmdOrCtrl+,', click: nav('/settings') },
        { type: 'separator' },
        { label: 'Quit', accelerator: 'CmdOrCtrl+Q', role: 'quit' },
      ],
    },
    {
      label: 'File',
      submenu: [
        { label: 'New Portfolio', accelerator: 'CmdOrCtrl+N', click: nav('/portfolios/new') },
        { label: 'New Optimization', accelerator: 'CmdOrCtrl+Shift+N', click: nav('/optimizations/new') },
        { type: 'separator' },
        { label: 'Export Report', accelerator: 'CmdOrCtrl+E', click: () => mainWindow?.webContents.send('export-report') },
        { type: 'separator' },
        { label: 'Close', role: 'close' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { label: 'Dashboard', accelerator: 'CmdOrCtrl+D', click: nav('/dashboard') },
        { label: 'Portfolio', accelerator: 'CmdOrCtrl+1', click: nav('/portfolios') },
        { label: 'Market Data', accelerator: 'CmdOrCtrl+2', click: nav('/market') },
        { label: 'Risk', accelerator: 'CmdOrCtrl+3', click: nav('/risk') },
        { label: 'Optimize', accelerator: 'CmdOrCtrl+4', click: nav('/optimizations/new') },
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

app.whenReady().then(async () => {
  startBackend();
  await waitForBackend(`http://127.0.0.1:${BACKEND_PORT}/login`);
  createWindow();
  createMenu();

  // Global shortcuts
  globalShortcut.register('CmdOrCtrl+Shift+Space', () => {
    mainWindow?.loadURL(`http://127.0.0.1:${BACKEND_PORT}/copilot`);
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
