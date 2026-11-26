import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Meta } from "./api";

const Ctx = createContext<Meta | null>(null);
const ReloadCtx = createContext<() => Promise<void>>(async () => {});

export function MetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const reload = () => api.meta().then(setMeta).catch((e) => setErr(String(e.message || e)));
  useEffect(() => { reload(); }, []);
  if (err)
    return (
      <div className="flex h-full items-center justify-center p-8 text-center">
        <div className="card card-pad max-w-md">
          <div className="mb-2 text-lg font-semibold text-rose-300">Бекенд недоступний</div>
          <div className="text-sm text-zinc-400">Не вдалося з'єднатися з API ({err}). Переконайтеся, що сервер запущено: <code className="text-accent-400">python run.py</code></div>
        </div>
      </div>
    );
  if (!meta) return <div className="flex h-full items-center justify-center text-zinc-500">Завантаження…</div>;
  return <ReloadCtx.Provider value={reload}><Ctx.Provider value={meta}>{children}</Ctx.Provider></ReloadCtx.Provider>;
}

export function useMeta(): Meta {
  const m = useContext(Ctx);
  if (!m) throw new Error("Meta not loaded");
  return m;
}

export function useMetaReload() {
  return useContext(ReloadCtx);
}
