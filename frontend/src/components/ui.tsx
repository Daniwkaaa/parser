import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { tierColor, tierLabel } from "../lib/format";

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`h-4 w-4 animate-spin ${className}`} />;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 animate-fade-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({ label, value, hint, icon, accent = "#7c6cff" }: { label: string; value: ReactNode; hint?: string; icon?: ReactNode; accent?: string }) {
  return (
    <div className="card card-pad group relative overflow-hidden animate-fade-up">
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-20 blur-2xl transition group-hover:opacity-40" style={{ background: accent }} />
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</span>
        <span className="text-zinc-500" style={{ color: accent }}>{icon}</span>
      </div>
      <div className="mt-3 font-mono text-3xl font-semibold text-white">{value}</div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}

export function ScoreBadge({ score, tier, size = "sm" }: { score: number; tier: string; size?: "sm" | "lg" }) {
  const c = tierColor(tier);
  if (size === "lg") {
    const r = 34, circ = 2 * Math.PI * r;
    return (
      <div className="relative h-24 w-24">
        <svg viewBox="0 0 80 80" className="h-24 w-24 -rotate-90">
          <circle cx="40" cy="40" r={r} stroke="#20242d" strokeWidth="7" fill="none" />
          <circle cx="40" cy="40" r={r} stroke={c} strokeWidth="7" fill="none" strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={circ * (1 - score / 100)} style={{ transition: "stroke-dashoffset .8s ease" }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-semibold text-white">{score}</span>
          <span className="text-[10px] uppercase tracking-wider" style={{ color: c }}>{tierLabel(tier)}</span>
        </div>
      </div>
    );
  }
  return (
    <span className="inline-flex min-w-[46px] items-center justify-center gap-1 rounded-lg px-2 py-0.5 font-mono text-sm font-semibold"
      style={{ color: c, background: c + "1a", border: `1px solid ${c}40` }}>
      {score}
    </span>
  );
}

const STATUS_STYLE: Record<string, string> = {
  yes: "text-emerald-300 bg-emerald-500/10 border-emerald-500/25",
  no: "text-rose-300 bg-rose-500/10 border-rose-500/25",
  social_only: "text-amber-300 bg-amber-500/10 border-amber-500/25",
  unreachable: "text-rose-300 bg-rose-500/10 border-rose-500/25",
  unknown: "text-zinc-400 bg-zinc-500/10 border-zinc-500/25",
  na: "text-zinc-500 bg-transparent border-zinc-700",
};

export function StatusBadge({ status, labels }: { status: string; labels: Record<string, string> }) {
  return <span className={`chip whitespace-nowrap ${STATUS_STYLE[status] || STATUS_STYLE.unknown}`}>{labels[status] || status}</span>;
}

export function ProblemTag({ label }: { label: string }) {
  return <span className="chip border-accent-500/25 bg-accent-soft text-accent-400">{label}</span>;
}

export function Empty({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 px-6 py-14 text-center">
      <div className="text-base font-medium text-zinc-200">{title}</div>
      {text && <div className="mt-1 max-w-md text-sm text-zinc-500">{text}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Toggle({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <label className="flex cursor-pointer items-start gap-3">
      <button type="button" onClick={() => onChange(!checked)}
        className={`mt-0.5 h-5 w-9 shrink-0 rounded-full border transition ${checked ? "border-accent-500 bg-accent-500" : "border-white/15 bg-ink-700"}`}>
        <span className={`block h-4 w-4 rounded-full bg-white shadow transition ${checked ? "translate-x-4" : "translate-x-0.5"}`} />
      </button>
      <span>
        <span className="block text-sm text-zinc-200">{label}</span>
        {hint && <span className="block text-xs text-zinc-500">{hint}</span>}
      </span>
    </label>
  );
}

export function Chips({ options, value, onChange }: { options: { key: string; label: string }[]; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => {
        const on = value.includes(o.key);
        return (
          <button key={o.key} type="button" className={on ? "chip-on" : "chip-off"}
            onClick={() => onChange(on ? value.filter((x) => x !== o.key) : [...value, o.key])}>
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
