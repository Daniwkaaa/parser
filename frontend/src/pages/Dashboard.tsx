import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Building2, Globe2, UtensilsCrossed, Flame, PhoneCall, Search as SearchIcon, Gauge } from "lucide-react";
import { api, type Stats } from "../lib/api";
import { useMeta } from "../lib/meta";
import { Empty, PageHeader, Spinner, StatCard } from "../components/ui";
import JobRow from "../components/JobRow";

const tooltipStyle = { background: "#171a21", border: "1px solid rgba(255,255,255,.08)", borderRadius: 12, color: "#e4e4e7", fontSize: 12 };
const TIER_COLORS: Record<string, string> = { high: "#34d399", medium: "#fbbf24", low: "#52525b" };

export default function Dashboard() {
  const meta = useMeta();
  const [s, setS] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.stats().then(setS).catch((e) => setErr(e.message)); }, []);
  const catLabel = (k: string) => meta.categories.find((c) => c.key === k)?.label || k;

  if (err) return <Empty title="Не вдалося завантажити статистику" text={err} />;
  if (!s) return <div className="flex items-center gap-2 text-zinc-500"><Spinner /> Завантаження…</div>;
  const t = s.totals;

  return (
    <div>
      <PageHeader title="Головна панель" subtitle="Огляд бази потенційних клієнтів"
        actions={<Link to="/search" className="btn-primary"><SearchIcon className="h-4 w-4" /> Новий пошук</Link>} />

      {t.businesses === 0 ? (
        <Empty title="База поки порожня" text="Запустіть перший пошук: оберіть місто й категорії — програма збере реальні бізнеси з OpenStreetMap і проаналізує їхню цифрову присутність."
          action={<Link to="/search" className="btn-primary">Почати пошук</Link>} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
            <StatCard label="Усього бізнесів" value={t.businesses} icon={<Building2 className="h-4 w-4" />} />
            <StatCard label="Без сайту" value={t.no_website} hint={`з них лише соцмережі: ${t.social_only}`} icon={<Globe2 className="h-4 w-4" />} accent="#f472b6" />
            <StatCard label="Без онлайн-меню" value={t.no_menu} hint="меню або каталог" icon={<UtensilsCrossed className="h-4 w-4" />} accent="#fb923c" />
            <StatCard label="Перспективні" value={t.high_potential} hint={`середній потенціал: ${t.medium_potential}`} icon={<Flame className="h-4 w-4" />} accent="#34d399" />
            <StatCard label="Перевірені контакти" value={t.verified_contacts} hint="валідний телефон або email" icon={<PhoneCall className="h-4 w-4" />} accent="#38bdf8" />
            <StatCard label="Середній Lead Score" value={t.avg_score} icon={<Gauge className="h-4 w-4" />} accent="#a78bfa" />
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-3">
            <div className="card card-pad xl:col-span-2">
              <div className="mb-4 text-sm font-medium text-zinc-300">Бізнеси за категоріями</div>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={s.by_category.slice(0, 12)} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <CartesianGrid stroke="#20242d" horizontal={false} />
                  <XAxis type="number" stroke="#52525b" fontSize={11} allowDecimals={false} />
                  <YAxis type="category" dataKey="label" stroke="#71717a" fontSize={11} width={170} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(124,108,255,.06)" }} formatter={(v: number, n: string) => [v, n === "count" ? "Кількість" : n]} />
                  <Bar dataKey="count" fill="#7c6cff" radius={[0, 6, 6, 0]} animationDuration={700} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card card-pad">
              <div className="mb-4 text-sm font-medium text-zinc-300">Потенціал (Lead Score)</div>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={s.by_tier} dataKey="count" nameKey="label" innerRadius={55} outerRadius={85} paddingAngle={3} stroke="none" animationDuration={700}>
                    {s.by_tier.map((x) => <Cell key={x.key} fill={TIER_COLORS[x.key]} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1.5">
                {s.by_tier.map((x) => (
                  <Link key={x.key} to={`/businesses?tiers=${x.key}`} className="flex items-center justify-between rounded-lg px-2 py-1 text-sm hover:bg-white/[0.04]">
                    <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: TIER_COLORS[x.key] }} />{x.label}</span>
                    <span className="font-mono text-zinc-400">{x.count}</span>
                  </Link>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <div className="card card-pad">
              <div className="mb-4 text-sm font-medium text-zinc-300">Виявлені цифрові проблеми</div>
              <div className="space-y-2.5">
                {s.by_problem.filter((p) => p.count > 0).sort((a, b) => b.count - a.count).map((p) => (
                  <Link key={p.key} to={`/businesses?problems=${p.key}`} className="block group">
                    <div className="mb-1 flex justify-between text-xs"><span className="text-zinc-400 group-hover:text-zinc-200">{p.label}</span><span className="font-mono text-zinc-500">{p.count}</span></div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
                      <div className="h-full rounded-full bg-gradient-to-r from-accent-500 to-indigo-400 transition-all duration-700" style={{ width: `${(p.count / Math.max(1, t.businesses)) * 100}%` }} />
                    </div>
                  </Link>
                ))}
              </div>
            </div>
            <div className="card card-pad">
              <div className="mb-4 text-sm font-medium text-zinc-300">Розподіл Lead Score</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={s.score_histogram}>
                  <CartesianGrid stroke="#20242d" vertical={false} />
                  <XAxis dataKey="range" stroke="#52525b" fontSize={10} />
                  <YAxis stroke="#52525b" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(124,108,255,.06)" }} formatter={(v: number) => [v, "Бізнесів"]} />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]} animationDuration={700}>
                    {s.score_histogram.map((_, i) => <Cell key={i} fill={i >= 7 ? "#34d399" : i >= 4 ? "#fbbf24" : "#52525b"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card card-pad">
              <div className="mb-3 flex items-center justify-between text-sm font-medium text-zinc-300">
                Останні пошуки <Link to="/search" className="text-xs text-accent-400 hover:underline">усі</Link>
              </div>
              <div className="-mx-3 space-y-0.5">
                {s.recent_jobs.length === 0 && <div className="px-3 text-sm text-zinc-500">Ще немає пошуків</div>}
                {s.recent_jobs.map((j) => <JobRow key={j.id} job={j} catLabel={catLabel} />)}
              </div>
            </div>
          </div>

          <div className="mt-4 card card-pad">
            <div className="mb-3 text-sm font-medium text-zinc-300">Воронка клієнтів</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
              {s.by_status.map((x) => (
                <Link key={x.key} to={`/businesses?statuses=${x.key}`} className="rounded-xl border border-white/[0.06] bg-ink-850 px-3 py-2.5 transition hover:border-accent-500/40">
                  <div className="font-mono text-xl text-white">{x.count}</div>
                  <div className="text-xs text-zinc-500">{x.label}</div>
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
