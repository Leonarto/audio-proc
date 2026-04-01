import { spawn } from 'node:child_process';
import { spawnPythonBackend, waitForHealthcheck } from './python.mjs';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const backendUrl = 'http://127.0.0.1:8765';
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

const stopChildren = () => {
  if (!backend.killed) {
    backend.kill('SIGTERM');
  }

  if (!vite.killed) {
    vite.kill('SIGTERM');
  }
};

process.on('SIGINT', stopChildren);
process.on('SIGTERM', stopChildren);

Promise.all([waitForHealthcheck(backendUrl)])
  .then(() => {
    console.log(`Web app dev environment ready. Frontend: http://127.0.0.1:5173  Backend: ${backendUrl}`);
  })
  .catch((error) => {
    console.error(error.message);
    stopChildren();
    process.exit(1);
  });
