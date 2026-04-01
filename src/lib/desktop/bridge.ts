const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8765';

export function getDesktopBridge() {
  return typeof window !== 'undefined' ? window.audioProcDesktop ?? null : null;
}

export function isDesktopBridgeAvailable() {
  return Boolean(getDesktopBridge()?.isDesktop);
}

export function getBackendBaseUrl() {
  return getDesktopBridge()?.backendUrl ?? DEFAULT_BACKEND_URL;
}

export async function chooseFolder() {
  const bridge = getDesktopBridge();

  if (bridge) {
    return bridge.chooseFolder();
  }

  const folderPath = window.prompt('Desktop folder picker is only available in the Electron shell. Paste an absolute folder path for browser-only dev:');
  return folderPath?.trim() || null;
}

export async function showItemInFolder(absolutePath: string) {
  const bridge = getDesktopBridge();

  if (!bridge) {
    return false;
  }

  return bridge.showItemInFolder(absolutePath);
}
