import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export const ROOT_DIR = path.resolve(__dirname, '..');
const DEFAULT_BACKEND_PORT = 8765;

function candidateList() {
  const explicit = process.env.AUDIO_PROC_PYTHON;

  if (explicit) {
    return [{ command: explicit, args: [] }];
  }

  if (process.platform === 'win32') {
    return [
      { command: 'py', args: ['-3'] },
      { command: 'python', args: [] },
      { command: 'python3', args: [] }
    ];
  }

  return [
    { command: 'python3', args: [] },
    { command: 'python', args: [] }
  ];
}

export function resolvePythonLaunch() {
  for (const candidate of candidateList()) {
    const probe = spawnSync(candidate.command, [...candidate.args, '-c', 'import sys; print(sys.executable)'], {
      encoding: 'utf8'
    });

    if (probe.status === 0) {
      return candidate;
    }
  }

  throw new Error(
    'Python 3 was not found. Install Python 3.9+ or set AUDIO_PROC_PYTHON to a valid interpreter path.'
  );
}

function resolveBackendRunner({ packaged = false } = {}) {
  if (packaged) {
    return path.join(process.resourcesPath, 'backend', 'run_backend.py');
  }

  return path.join(ROOT_DIR, 'backend', 'run_backend.py');
}

export function spawnPythonBackend({
  appDataDir,
  port = DEFAULT_BACKEND_PORT,
  packaged = false,
  stdio = 'pipe',
  extraEnv = {}
} = {}) {
  const python = resolvePythonLaunch();
  const runnerPath = resolveBackendRunner({ packaged });
  const child = spawn(
    python.command,
    [...python.args, runnerPath, '--host', '127.0.0.1', '--port', String(port)],
    {
      cwd: ROOT_DIR,
      stdio,
      windowsHide: true,
      env: {
        ...process.env,
        ...extraEnv,
        AUDIO_PROC_APP_DATA_DIR: appDataDir ?? process.env.AUDIO_PROC_APP_DATA_DIR
      }
    }
  );

  return child;
}

export async function waitForHealthcheck(baseUrl, { timeoutMs = 15000, intervalMs = 300 } = {}) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(`${baseUrl}/api/health`);

      if (response.ok) {
        return true;
      }
    } catch (error) {
      void error;
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error(`Backend did not become healthy at ${baseUrl} within ${timeoutMs}ms.`);
}

export async function waitForUrl(url, { timeoutMs = 15000, intervalMs = 300 } = {}) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);

      if (response.ok) {
        return true;
      }
    } catch (error) {
      void error;
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error(`URL did not become reachable: ${url}`);
}
