const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

function startBackend() {
  // Spawns the uvicorn backend server
  // In a production build, this could point to a packaged PyInstaller executable.
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  
  backendProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'backend.app.main:app', '--port', '8000'], {
    cwd: path.join(__dirname, '..'),
    shell: true
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend Error: ${data}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    title: "StackCheck DP Data Validation Automation Platform",
    backgroundColor: '#0f172a'
  });

  // Open the dev server in development, otherwise load static index file
  // Wait 1.5 seconds to give FastAPI time to boot
  setTimeout(() => {
    mainWindow.loadURL('http://localhost:5173');
  }, 1500);

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.on('ready', () => {
  startBackend();
  createWindow();
});

app.on('window-all-closed', function () {
  // Kill backend process on app exit
  if (backendProcess) {
    if (process.platform === 'win32') {
      spawn("taskkill", ["/pid", backendProcess.pid, "/f", "/t"]);
    } else {
      backendProcess.kill('SIGINT');
    }
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', function () {
  if (mainWindow === null) {
    createWindow();
  }
});
