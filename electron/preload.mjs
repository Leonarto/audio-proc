import { contextBridge, ipcRenderer } from 'electron';

const backendArg = process.argv.find((value) => value.startsWith('--audio-proc-backend-url='));
const backendUrl = backendArg ? backendArg.replace('--audio-proc-backend-url=', '') : 'http://127.0.0.1:8765';

contextBridge.exposeInMainWorld('audioProcDesktop', {
  isDesktop: true,
  platform: process.platform,
  backendUrl,
  chooseFolder: () => ipcRenderer.invoke('audio-proc:choose-folder'),
  showItemInFolder: (absolutePath) => ipcRenderer.invoke('audio-proc:show-item-in-folder', absolutePath)
});
