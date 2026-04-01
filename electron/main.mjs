import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnPythonBackend, waitForHealthcheck } from '../scripts/python.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8765';

/** @type {import('node:child_process').ChildProcessWithoutNullStreams | null} */
let backendProcess = null;
/** @type {BrowserWindow | null} */
let mainWindow = null;

function getPreloadPath() {
  return path.join(__dirname, 'preload.mjs');
}

function getIndexHtmlPath() {
  return path.join(ROOT_DIR, 'build', 'index.html');
}

async function ensureBackend() {
  const backendUrl = process.env.AUDIO_PROC_BACKEND_URL ?? DEFAULT_BACKEND_URL;

  if (!process.env.AUDIO_PROC_BACKEND_URL) {
    backendProcess = spawnPythonBackend({
      packaged: app.isPackaged,
      stdio: 'pipe',
      appDataDir: path.join(app.getPath('userData'), 'app-data')
    });

    backendProcess.stdout.on('data', (chunk) => {
      process.stdout.write(`[backend] ${chunk}`);
    });

    backendProcess.stderr.on('data', (chunk) => {
      process.stderr.write(`[backend] ${chunk}`);
    });
  }

  await waitForHealthcheck(backendUrl, { timeoutMs: 20000 });

  return backendUrl;
}

async function createWindow() {
  const backendUrl = await ensureBackend();
  const devServerUrl = process.env.AUDIO_PROC_DEV_SERVER_URL;

  mainWindow = new BrowserWindow({
    width: 1560,
    height: 960,
    minWidth: 1120,
    minHeight: 720,
    title: 'Audio Proc MVP',
    backgroundColor: '#f4f0e8',
    webPreferences: {
      preload: getPreloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [`--audio-proc-backend-url=${backendUrl}`]
    }
  });

  if (devServerUrl) {
    await mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    await mainWindow.loadFile(getIndexHtmlPath());
  }
}

ipcMain.handle('audio-proc:choose-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory']
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  return result.filePaths[0];
});

ipcMain.handle('audio-proc:show-item-in-folder', async (_event, absolutePath) => {
  if (!absolutePath) {
    return false;
  }

  shell.showItemInFolder(absolutePath);
  return true;
});

app.whenReady().then(async () => {
  await createWindow();

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }
});
