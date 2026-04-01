import { spawn } from 'node:child_process';
import { spawnPythonBackend, waitForHealthcheck, waitForUrl } from './python.mjs';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const backendUrl = 'http://127.0.0.1:8765';
const frontendUrl = 'http://127.0.0.1:5173';

const backend = spawnPythonBackend({ stdio: 'inherit' });
const vite = spawn(
  npmCommand,
  ['exec', 'vite', 'dev', '--', '--host', '127.0.0.1', '--port', '5173', '--strictPort'],
  {
    stdio: 'inherit',
    env: {
      ...process.env,
      AUDIO_PROC_BACKEND_URL: backendUrl
    }
  }
);

let electron;

const stopChildren = () => {
  if (!backend.killed) {
    backend.kill('SIGTERM');
  }

  if (!vite.killed) {
    vite.kill('SIGTERM');
  }

  if (electron && !electron.killed) {
    electron.kill('SIGTERM');
  }
};

process.on('SIGINT', stopChildren);
process.on('SIGTERM', stopChildren);

Promise.all([waitForHealthcheck(backendUrl), waitForUrl(frontendUrl, { timeoutMs: 20000 })])
  .then(() => {
    console.log(`Desktop dev started. Frontend: ${frontendUrl}  Backend: ${backendUrl}`);
    electron = spawn(npmCommand, ['exec', 'electron', '.'], {
      stdio: 'inherit',
      env: {
        ...process.env,
        AUDIO_PROC_BACKEND_URL: backendUrl,
        AUDIO_PROC_DEV_SERVER_URL: frontendUrl
      }
    });

    electron.on('exit', (code) => {
      stopChildren();
      process.exit(code ?? 0);
    });
  })
  .catch((error) => {
    console.error(error.message);
    stopChildren();
    process.exit(1);
  });
