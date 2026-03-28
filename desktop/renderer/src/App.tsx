import { useEffect, useState } from 'react';

type Phase = 'loading' | 'ready' | 'error';

export function App() {
  const [phase, setPhase] = useState<Phase>('loading');
  const [message, setMessage] = useState('正在启动本地服务（MCP → Planner → Flask）…');
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [apiBase, setApiBase] = useState<string | null>(null);

  useEffect(() => {
    const desktop = window.desktop;
    if (!desktop) {
      setPhase('error');
      setErrorDetail('未检测到 Electron 预加载桥接（请使用 npm run dev 启动桌面端）。');
      return;
    }

    let cancelled = false;
    (async () => {
      const result = await desktop.startBackend();
      if (cancelled) return;
      if (result.ok) {
        setPhase('ready');
        setApiBase(result.apiBase);
        setMessage('后端已就绪。');
      } else {
        setPhase('error');
        setErrorDetail(result.error);
        setHints(result.hints ?? []);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div style={{ padding: '2rem', maxWidth: 720 }}>
      <h1 style={{ fontWeight: 600, fontSize: '1.5rem', marginTop: 0 }}>SciAssistant 桌面端</h1>
      {phase === 'loading' && <p style={{ color: '#8b98a5' }}>{message}</p>}
      {phase === 'ready' && (
        <>
          <p style={{ color: '#00ba7c' }}>本地 API 已连接。</p>
          <p style={{ color: '#8b98a5', fontSize: '0.9rem' }}>
            API 基址：<code style={{ color: '#e7e9ea' }}>{apiBase}</code>
          </p>
          <p style={{ color: '#8b98a5', fontSize: '0.9rem' }}>
            后续可在此接入登录、会话与任务流程（当前为骨架联调页）。
          </p>
        </>
      )}
      {phase === 'error' && (
        <>
          <p style={{ color: '#f4212e' }}>启动失败</p>
          <pre
            style={{
              background: '#1e2732',
              padding: '1rem',
              borderRadius: 8,
              overflow: 'auto',
              fontSize: '0.85rem',
            }}
          >
            {errorDetail}
          </pre>
          {hints.length > 0 && (
            <ul style={{ color: '#8b98a5' }}>
              {hints.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
