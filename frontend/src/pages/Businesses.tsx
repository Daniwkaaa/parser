import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowDown, ArrowUp, Download, Filter, Search as SearchIcon, X, Instagram, Facebook, Globe, Phone, Mail } from "lucide-react";
import { api, type BusinessBrief, type Filters } from "../lib/api";
import { useMeta } from "../lib/meta";
import { Chips, Empty, PageHeader, ScoreBadge, Spinner, StatusBadge } from "../components/ui";

const PAGE = 50;
const LIST_KEYS = ["categories", "problems", "tiers", "statuses", "website_status"] as const;

function readFilters(sp: URLSearchParams): Filters {
  const f: Filters = {};
  LIST_KEYS.forEach((k) => { const v = sp.get(k); if (v) (f as any)[k] = v.split(","); });
  ["q", "city", "sort", "order"].forEach((k) => { const v = sp.get(k); if (v) (f as any)[k] = v; });
  if (sp.get("min_score")) f.min_score = Number(sp.get("min_score"));
  if (sp.get("job_id")) f.job_id = Number(sp.get("job_id"));
  if (sp.get("has_contact")) f.has_contact = sp.get("has_contact") === "true";
  return f;
}

export default function Businesses() {
  const meta = useMeta();
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const filters = useMemo(() => readFilters(sp), [sp]);
  const page = Number(sp.get("page") || 1);
  const [data, setData] = useState<{ total: number; items: BusinessBrief[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState(filters.q || "");
  const [showFilters, setShowFilters] = useState(() => LIST_KEYS.some((k) => sp.get(k)) || !!sp.get("has_contact"));

  useEffect(() => {
    setLoading(true);
    api.businesses(filters, page, PAGE).then(setData).finally(() => setLoading(false));
  }, [filters, page]);

  useEffect(() => {
    const t = setTimeout(() => { if ((filters.q || "") !== q) update({ q: q || undefined }); }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  function update(patch: Partial<Filters>, keepPage = false) {
    const next = new URLSearchParams(sp);
    Object.entries(patch).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "" || (Array.isArray(v) && !v.length)) next.delete(k);
      else next.set(k, Array.isArray(v) ? v.join(",") : String(v));
    });
    if (!keepPage) next.delete("page");
    setSp(next);
  }

  function sortBy(col: string) {
    const same = (filters.sort || "lead_score") === col;
    update({ sort: col, order: same && (filters.order || "desc") === "desc" ? "asc" : "desc" });
  }

  async function setStatus(b: BusinessBrief, status: string) {
    await api.updateBusiness(b.id, { status });
    setData((d) => d && { ...d, items: d.items.map((x) => (x.id === b.id ? { ...x, status } : x)) });
  }

  const activeCount = LIST_KEYS.reduce((n, k) => n + ((filters as any)[k]?.length || 0), 0) + (filters.min_score ? 1 : 0) + (filters.city ? 1 : 0) + (filters.job_id ? 1 : 0) + (filters.has_contact ? 1 : 0);
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE)) : 1;
  const SortIcon = ({ col }: { col: string }) => (filters.sort || "lead_score") === col ? ((filters.order || "desc") === "desc" ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />) : null;

  return (
    <div>
      <PageHeader title="База бізнесів" subtitle={data ? `${data.total} записів${filters.job_id ? ` · результати пошуку #${filters.job_id}` : ""}` : undefined}
        actions={<>
          <a className="btn-ghost" href={api.exportUrl("csv", filters)}><Download className="h-4 w-4" /> CSV</a>
          <a className="btn-ghost" href={api.exportUrl("xlsx", filters)}><Download className="h-4 w-4" /> Excel</a>
        </>} />

      <div className="card card-pad mb-4 animate-fade-up">
        <div className="flex flex-wrap gap-3">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
            <input className="input pl-9" placeholder="Пошук за назвою, адресою, телефоном або email…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <input className="input w-40" placeholder="Місто" defaultValue={filters.city} onBlur={(e) => update({ city: e.target.value || undefined })} onKeyDown={(e) => e.key === "Enter" && update({ city: (e.target as HTMLInputElement).value || undefined })} />
          <select className="input w-44" value={filters.min_score ?? ""} onChange={(e) => update({ min_score: e.target.value ? Number(e.target.value) : undefined })}>
            <option value="">Будь-який score</option><option value="40">≥ 40</option><option value="70">≥ 70</option><option value="85">≥ 85</option>
          </select>
          <button className="btn-ghost" onClick={() => setShowFilters(!showFilters)}><Filter className="h-4 w-4" /> Фільтри {activeCount > 0 && <span className="rounded-md bg-accent-500 px-1.5 text-xs text-white">{activeCount}</span>}</button>
          {activeCount > 0 && <button className="btn-ghost" onClick={() => { setQ(""); setSp(new URLSearchParams()); }}><X className="h-4 w-4" /> Скинути</button>}
        </div>
        {showFilters && (
          <div className="mt-4 grid gap-4 border-t border-white/[0.06] pt-4 lg:grid-cols-2">
            <div><div className="label">Проблеми</div><Chips options={Object.entries(meta.problems).map(([key, label]) => ({ key, label }))} value={filters.problems || []} onChange={(v) => update({ problems: v })} /></div>
            <div><div className="label">Категорії</div><Chips options={meta.categories} value={filters.categories || []} onChange={(v) => update({ categories: v })} /></div>
            <div><div className="label">Потенціал</div><Chips options={[{ key: "high", label: "Високий 70–100" }, { key: "medium", label: "Середній 40–69" }, { key: "low", label: "Низький 0–39" }]} value={filters.tiers || []} onChange={(v) => update({ tiers: v })} /></div>
            <div><div className="label">Статус клієнта</div><Chips options={Object.entries(meta.client_statuses).map(([key, label]) => ({ key, label }))} value={filters.statuses || []} onChange={(v) => update({ statuses: v })} /></div>
            <div><div className="label">Сайт</div><Chips options={[["no", "Відсутній"], ["social_only", "Лише соцмережі"], ["unreachable", "Не працює"], ["yes", "Є сайт"], ["unknown", "Не перевірено"]].map(([key, label]) => ({ key, label }))} value={filters.website_status || []} onChange={(v) => update({ website_status: v })} /></div>
            <div><div className="label">Контакти</div><Chips options={[{ key: "true", label: "Є перевірений телефон/email" }]} value={filters.has_contact ? ["true"] : []} onChange={(v) => update({ has_contact: v.length ? true : undefined })} />
              {filters.job_id && <div className="mt-3"><span className="chip-on">Пошук #{filters.job_id} <button onClick={() => update({ job_id: undefined })}><X className="h-3 w-3" /></button></span></div>}
            </div>
          </div>
        )}
      </div>

      <div className="card overflow-hidden animate-fade-up">
        {!data ? (
          <div className="flex items-center gap-2 p-6 text-zinc-500"><Spinner /> Завантаження…</div>
        ) : data.items.length === 0 ? (
          <div className="p-6"><Empty title="Нічого не знайдено" text="Змініть фільтри або запустіть новий пошук." action={<Link to="/search" className="btn-primary">До пошуку</Link>} /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1180px]">
              <thead className="border-b border-white/[0.06] bg-ink-850/60">
                <tr>
                  <th className="th cursor-pointer" onClick={() => sortBy("lead_score")}><span className="flex items-center gap-1">Score <SortIcon col="lead_score" /></span></th>
                  <th className="th cursor-pointer" onClick={() => sortBy("name")}><span className="flex items-center gap-1">Бізнес <SortIcon col="name" /></span></th>
                  <th className="th">Контакти</th>
                  <th className="th">Сайт</th>
                  <th className="th">Меню / каталог</th>
                  <th className="th">Запис / бронь</th>
                  <th className="th">Проблеми</th>
                  <th className="th cursor-pointer" onClick={() => sortBy("status")}><span className="flex items-center gap-1">Статус <SortIcon col="status" /></span></th>
                </tr>
              </thead>
              <tbody className={`divide-y divide-white/[0.04] transition ${loading ? "opacity-50" : ""}`}>
                {data.items.map((b) => (
                  <tr key={b.id} className="cursor-pointer transition hover:bg-white/[0.025]" onClick={() => nav(`/businesses/${b.id}`)}>
                    <td className="td"><ScoreBadge score={b.lead_score} tier={b.lead_tier} /></td>
                    <td className="td max-w-[280px]">
                      <div className="truncate font-medium text-zinc-100">{b.name}</div>
                      <div className="truncate text-xs text-zinc-500">{b.category_label} · {b.address || b.city || "адреса не вказана"}</div>
                    </td>
                    <td className="td">
                      <div className="flex items-center gap-2 text-zinc-500">
                        {b.phone && <span title={b.phone}><Phone className={`h-4 w-4 ${b.contact_verified ? "text-emerald-400" : ""}`} /></span>}
                        {b.email && <span title={b.email}><Mail className="h-4 w-4 text-sky-400" /></span>}
                        {b.instagram && <span title="Instagram"><Instagram className="h-4 w-4 text-pink-400" /></span>}
                        {b.facebook && <span title="Facebook"><Facebook className="h-4 w-4 text-blue-400" /></span>}
                        {b.website && <span title={b.website}><Globe className="h-4 w-4 text-zinc-300" /></span>}
                        {!b.phone && !b.email && !b.instagram && !b.facebook && !b.website && <span className="text-xs">—</span>}
                      </div>
                    </td>
                    <td className="td"><StatusBadge status={b.website_status} labels={meta.status_labels} /></td>
                    <td className="td"><StatusBadge status={b.menu_status} labels={meta.status_labels} /></td>
                    <td className="td"><StatusBadge status={b.booking_status} labels={meta.status_labels} /></td>
                    <td className="td min-w-[240px] max-w-[320px]">
                      <div className="flex flex-wrap gap-1">
                        {b.problems.slice(0, 3).map((p) => <span key={p} className="whitespace-nowrap rounded-md bg-white/[0.04] px-1.5 py-0.5 text-[11px] text-zinc-400">{meta.problems[p]}</span>)}
                        {b.problems.length > 3 && <span className="text-[11px] text-zinc-500">+{b.problems.length - 3}</span>}
                      </div>
                    </td>
                    <td className="td" onClick={(e) => e.stopPropagation()}>
                      <select className="rounded-lg border border-white/10 bg-ink-850 px-2 py-1 text-xs text-zinc-200 outline-none focus:border-accent-500" value={b.status} onChange={(e) => setStatus(b, e.target.value)}>
                        {Object.entries(meta.client_statuses).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.total > PAGE && (
          <div className="flex items-center justify-between border-t border-white/[0.06] px-4 py-3 text-sm text-zinc-400">
            <span>Сторінка {page} з {pages}</span>
            <div className="flex gap-2">
              <button className="btn-ghost px-3 py-1.5" disabled={page <= 1} onClick={() => { const n = new URLSearchParams(sp); n.set("page", String(page - 1)); setSp(n); }}>Назад</button>
              <button className="btn-ghost px-3 py-1.5" disabled={page >= pages} onClick={() => { const n = new URLSearchParams(sp); n.set("page", String(page + 1)); setSp(n); }}>Далі</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
