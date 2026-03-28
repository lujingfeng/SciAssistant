import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import http from 'http';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DESKTOP_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(DESKTOP_ROOT, '..');

const PORTS = {
  mcp: 6274,
  planner: 8000,
  flask: 7001,
};

const HEALTH_PATHS = {
  mcp: '/health',
  planner: '/api/status',
  flask: '/api/health',
};

const STARTUP = {
  perServiceTimeoutMs: 120_000,
  pollIntervalMs: 500,
  httpGetTimeoutMs: 3000,
};

const children = [];

function defaultPythonCmd() {
  if (process.env.SCIASSISTANT_PYTHON) return process.env.SCIASSISTANT_PYTHON;
  return process.platform === 'win32' ? 'python' : 'python3';
}

function httpGetOk(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: STARTUP.httpGetTimeoutMs }, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 300);
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('timeout'));
    });
  });
}

async function waitForUrl(url, label) {
  const deadline = Date.now() + STARTUP.perServiceTimeoutMs;
  let lastErr;
  while (Date.now() < deadline) {
    try {
      const ok = await httpGetOk(url);
      if (ok) return;
      lastErr = new Error(`HTTP not OK for ${label}`);
    } catch (e) {
      lastErr = e;
    }
    await new Promise((r) => setTimeout(r, STARTUP.pollIntervalMs));
  }
  throw new Error(
    `${label} 在 ${STARTUP.perServiceTimeoutMs / 1000}s 内未就绪: ${url} — ${lastErr?.message || 'unknown'}`
  );
}

function attachChildLogging(proc, name) {
  proc.stdout?.on('data', (chunk) => {
    process.stdout.write(`[${name}] ${chunk}`);
  });
  proc.stderr?.on('data', (chunk) => {
    process.stderr.write(`[${name}] ${chunk}`);
  });
}

function spawnPython(name, args, options) {
  const cmd = defaultPythonCmd();
  const proc = spawn(cmd, args, {
    cwd: options.cwd,
    env: { ...process.env, ...options.env },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  attachChildLogging(proc, name);
  children.push(proc);
  proc.on('exit', (code, signal) => {
    const i = children.indexOf(proc);
    if (i >= 0) children.splice(i, 1);
    console.warn(`[${name}] exited code=${code} signal=${signal}`);
  });
  return proc;
}

function killAllChildren() {
  for (const proc of [...children].reverse()) {
    try {
      proc.kill('SIGTERM');
    } catch {
      /* ignore */
    }
  }
  children.length = 0;
}

async function startMcp() {
  const script = path.join(REPO_ROOT, 'deepdiver_v2', 'src', 'tools', 'mcp_server_standard.py');
  const cwd = path.join(REPO_ROOT, 'deepdiver_v2');
  spawnPython('mcp', [script], { cwd });
  await waitForUrl(`http://127.0.0.1:${PORTS.mcp}${HEALTH_PATHS.mcp}`, 'MCP');
}

async function startPlanner() {
  const script = path.join(REPO_ROOT, 'deepdiver_v2', 'cli', 'a.py');
  spawnPython('planner', [script], { cwd: REPO_ROOT });
  await waitForUrl(`http://127.0.0.1:${PORTS.planner}${HEALTH_PATHS.planner}`, 'Planner');
}

async function startFlask() {
  const script = path.join(REPO_ROOT, 'app.py');
  spawnPython('flask', [script], { cwd: REPO_ROOT });
  await waitForUrl(`http://127.0.0.1:${PORTS.flask}${HEALTH_PATHS.flask}`, 'Flask API');
}

let backendState = 'idle';
let backendPromise = null;

async function startAllServices() {
  await startMcp();
  await startPlanner();
  await startFlask();
  return {
    ok: true,
    ports: PORTS,
    apiBase: `http://127.0.0.1:${PORTS.flask}`,
  };
}

function ensureBackendStarted() {
  if (backendState === 'ready') {
    return Promise.resolve({
      ok: true,
      ports: PORTS,
      apiBase: `http://127.0.0.1:${PORTS.flask}`,
    });
  }
  if (backendPromise) return backendPromise;

  backendPromise = (async () => {
    try {
      const result = await startAllServices();
      backendState = 'ready';
      return result;
    } catch (e) {
      backendState = 'error';
      backendPromise = null;
      killAllChildren();
      throw e;
    }
  })();

  return backendPromise;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(DESKTOP_ROOT, 'preload', 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    win.loadFile(path.join(DESKTOP_ROOT, 'renderer', 'dist', 'index.html'));
  }

  return win;
}

app.whenReady().then(() => {
  ipcMain.handle('backend:start-and-wait', async () => {
    try {
      return { ok: true, ...(await ensureBackendStarted()) };
    } catch (e) {
      return {
        ok: false,
        error: e instanceof Error ? e.message : String(e),
        ports: PORTS,
        hints: [
          '确认本机已安装 Python3，且已安装项目依赖（如 deepdiver_v2/requirements.txt）。',
          `检查端口 ${PORTS.mcp} / ${PORTS.planner} / ${PORTS.flask} 是否被占用。`,
          '可在终端手动运行各服务以查看报错。',
        ],
      };
    }
  });

  ipcMain.handle('backend:meta', () => ({
    repoRoot: REPO_ROOT,
    ports: PORTS,
    apiBase: `http://127.0.0.1:${PORTS.flask}`,
  }));

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    killAllChildren();
    app.quit();
  }
});

app.on('before-quit', () => {
  killAllChildren();
});
