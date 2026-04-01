import { spawnPythonBackend, waitForHealthcheck } from './python.mjs';

const baseUrl = process.env.AUDIO_PROC_BACKEND_URL ?? 'http://127.0.0.1:8765';
const backend = spawnPythonBackend({
  stdio: 'inherit'
});

const stop = () => {
  if (!backend.killed) {
    backend.kill('SIGTERM');
  }
};

process.on('SIGINT', stop);
process.on('SIGTERM', stop);

backend.on('exit', (code) => {
  process.exit(code ?? 0);
});

waitForHealthcheck(baseUrl)
  .then(() => {
    console.log(`Python backend ready at ${baseUrl}`);
  })
  .catch((error) => {
    console.error(error.message);
    stop();
    process.exit(1);
  });
