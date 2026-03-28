/// <reference types="vite/client" />

export type BackendStartResult =
  | {
      ok: true;
      ports: { mcp: number; planner: number; flask: number };
      apiBase: string;
    }
  | {
      ok: false;
      error: string;
      ports: { mcp: number; planner: number; flask: number };
      hints?: string[];
    };

export type BackendMeta = {
  repoRoot: string;
  ports: { mcp: number; planner: number; flask: number };
  apiBase: string;
};

declare global {
  interface Window {
    desktop?: {
      startBackend: () => Promise<BackendStartResult>;
      getMeta: () => Promise<BackendMeta>;
    };
  }
}

export {};
