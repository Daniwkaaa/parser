import { Link } from "react-router-dom";
import type { Job } from "../lib/api";
import { fmtDate } from "../lib/format";

const STATUS: Record<string, [string, string]> = {
  queued: ["У черзі", "text-zinc-400"],
  running: ["Виконується", "text-accent-400"],
  completed: ["Завершено", "text-emerald-400"],
  failed: ["Помилка", "text-rose-400"],
  interrupted: ["Перервано", "text-amber-400"],
  cancelled: ["Зупинено", "text-zinc-400"],
};

export function jobStatus(s: string) { return STATUS[s] || [s, "text-zinc-400"]; }

export default function JobRow({ job, catLabel }: { job: Job; catLabel: (k: string) => string }) {
  const [label, cls] = jobStatus(job.status);
  const cats: string[] = job.params?.categories || [];
  return (
    <Link to={`/businesses?job_id=${job.id}`} className="flex items-center justify-between gap-4 rounded-xl px-3 py-2.5 transition hover:bg-white/[0.04]">
      <div className="min-w-0">
        <div className="truncate text-sm text-zinc-200">
          {job.params?.scope === "country" ? "Уся Україна" : [job.params?.city, job.params?.district].filter(Boolean).join(", ") || job.params?.region || "—"}
          <span className="text-zinc-500"> · {cats.slice(0, 3).map(catLabel).join(", ")}{cats.length > 3 ? ` +${cats.length - 3}` : ""}</span>
        </div>
        <div className="text-xs text-zinc-500">{fmtDate(job.created_at)}</div>
      </div>
      <div className="shrink-0 text-right">
        <div className={`text-xs font-medium ${cls}`}>{label}</div>
        <div className="font-mono text-xs text-zinc-400">{job.saved_count} збережено</div>
      </div>
    </Link>
  );
}
