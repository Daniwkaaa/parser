import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MapPin, Play, Square, RotateCcw, Trash2, CheckCircle2, AlertTriangle, Layers, Crosshair } from "lucide-react";
import { api, type Job, type JobLog, type SettingsData } from "../lib/api";
import { useMeta } from "../lib/meta";
import { Chips, PageHeader, Spinner, Toggle } from "../components/ui";
import { jobStatus } from "../components/JobRow";
import { fmtDate } from "../lib/format";

const STAGES: Record<string, string> = {
  queued: "У черзі", geocode: "Визначення території", collect: "Збір даних з джерел", analyze: "Аналіз цифрової присутності",
  done: "Готово", failed: "Помилка", cancelled: "Зупинено",
};

export default function SearchPage() {
  const meta = useMeta();
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [form, setForm] = useState({ country: "Україна", region: "", city: "", district: "", radius_km: 0, limit: 100 });
  const [cats, setCats] = useState<string[]>([]);
  const [problems, setProblems] = useState<string[]>([]);
  const [comprehensive, setComprehensive] = useState(true);
  const [sources, setSources] = useState<string[]>(["osm"]);
  const [checkSites, setCheckSites] = useState(true);
  const [excludeChains, setExcludeChains] = useState(true);
  const [geo, setGeo] = useState<{ label: string } | null>(null);
  const [geoBusy, setGeoBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<JobLog[]>([]);
  const [history, setHistory] = useState<Job[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.settings().then((s) => {
      setSettings(s);
      setForm((f) => ({ ...f, country: s.search.country || f.country, limit: s.search.limit || f.limit, radius_km: f.radius_km }));
      setCheckSites(s.search.check_websites);
      setExcludeChains(s.search.exclude_chains);
      setSources(Object.entries(s.sources).filter(([k, v]) => v && (k === "osm" || s.api_keys[k]?.configured)).map(([k]) => k));
    });
    api.jobs().then((js) => {
      setHistory(js);
      const active = js.find((j) => j.status === "running" || j.status === "queued");
      if (active) setJob(active);
    });
  }, []);

  // опитування стану завдання та логів у реальному часі
  useEffect(() => {
    if (!job) return;
    let stop = false;
    let after = logs.length ? logs[logs.length - 1].id : 0;
    const tick = async () => {
      try {
        const [j, newLogs] = await Promise.all([api.job(job.id), api.jobLogs(job.id, after)]);
        if (stop) return;
        if (newLogs.length) { after = newLogs[newLogs.length - 1].id; setLogs((l) => [...l, ...newLogs]); }
        setJob(j);
        if (j.status === "running" || j.status === "queued") setTimeout(tick, 1000);
        else api.jobs().then(setHistory);
      } catch { if (!stop) setTimeout(tick, 2500); }
    };
    tick();
    return () => { stop = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.id, job?.status === "queued"]);

  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" }); }, [logs.length]);

  const groups = useMemo(() => {
    const g: Record<string, typeof meta.categories> = {};
    meta.categories.forEach((c) => { (g[c.group] ||= []).push(c); });
    return g;
  }, [meta]);

  const running = job && (job.status === "running" || job.status === "queued");

  async function checkGeo() {
    setGeoBusy(true); setErr(null); setGeo(null);
    try { setGeo(await api.geocode({ ...form, radius_km: form.radius_km || null })); }
    catch (e: any) { setErr(e.message); }
    finally { setGeoBusy(false); }
  }

  async function start() {
    setErr(null);
    if (!form.city && !form.region) return setErr("Вкажіть місто (або регіон)");
    if (!cats.length) return setErr("Оберіть хоча б одну категорію бізнесу");
    if (!comprehensive && !problems.length) return setErr("Оберіть типи проблем або увімкніть комплексний пошук");
    try {
      const j = await api.search({
        country: form.country || null, region: form.region || null, city: form.city || null, district: form.district || null,
        radius_km: form.radius_km || null, limit: form.limit, categories: cats, problems: comprehensive ? [] : problems,
        comprehensive, sources, check_websites: checkSites, exclude_chains: excludeChains,
      });
      setLogs([]); setJob(j);
    } catch (e: any) { setErr(e.message); }
  }

  async function resume(j: Job) { setLogs([]); setJob(await api.resumeJob(j.id)); }

  const pct = job && job.progress_total ? Math.round((job.progress_done / job.progress_total) * 100) : 0;
  const catLabel = (k: string) => meta.categories.find((c) => c.key === k)?.label || k;

  return (
    <div>
      <PageHeader title="Пошук бізнесів" subtitle="Реальний збір даних з відкритих джерел і автоматичний аналіз цифрової присутності" />
      <div className="grid gap-5 xl:grid-cols-[1fr_440px]">
        <div className="space-y-5">
          <section className="card card-pad animate-fade-up">
            <div className="mb-4 flex items-center gap-2 text-sm font-medium text-zinc-200"><MapPin className="h-4 w-4 text-accent-400" /> Локація</div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div><label className="label">Країна</label><input className="input" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} /></div>
              <div><label className="label">Область / регіон</label><input className="input" placeholder="напр. Львівська область" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} /></div>
              <div><label className="label">Місто</label><input className="input" placeholder="напр. Львів" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
              <div><label className="label">Район (необов'язково)</label><input className="input" placeholder="напр. Галицький район" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></div>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
              <div>
                <label className="label">Радіус пошуку: {form.radius_km ? `${form.radius_km} км від центру` : "уся територія міста/району"}</label>
                <input type="range" min={0} max={25} step={0.5} value={form.radius_km} onChange={(e) => setForm({ ...form, radius_km: Number(e.target.value) })} className="w-full accent-[#7c6cff]" />
              </div>
              <button className="btn-ghost" onClick={checkGeo} disabled={geoBusy || (!form.city && !form.region)}>
                {geoBusy ? <Spinner /> : <Crosshair className="h-4 w-4" />} Перевірити локацію
              </button>
            </div>
            {geo && <div className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-300">Знайдено: {geo.label}</div>}
          </section>

          <section className="card card-pad animate-fade-up">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><Layers className="h-4 w-4 text-accent-400" /> Категорії бізнесу</div>
              <div className="flex gap-2 text-xs">
                <button className="text-accent-400 hover:underline" onClick={() => setCats(meta.categories.map((c) => c.key))}>усі</button>
                <span className="text-zinc-600">·</span>
                <button className="text-zinc-400 hover:underline" onClick={() => setCats([])}>скинути</button>
              </div>
            </div>
            <div className="space-y-3">
              {Object.entries(groups).map(([g, list]) => (
                <div key={g} className="grid gap-2 sm:grid-cols-[170px_1fr]">
                  <button className="text-left text-xs font-medium text-zinc-500 hover:text-zinc-300" onClick={() => {
                    const keys = list.map((c) => c.key); const all = keys.every((k) => cats.includes(k));
                    setCats(all ? cats.filter((c) => !keys.includes(c)) : Array.from(new Set([...cats, ...keys])));
                  }}>{meta.groups[g]}</button>
                  <Chips options={list} value={cats} onChange={setCats} />
                </div>
              ))}
            </div>
          </section>

          <section className="card card-pad animate-fade-up">
            <div className="mb-4 text-sm font-medium text-zinc-200">Тип цифрової проблеми</div>
            <Toggle checked={comprehensive} onChange={setComprehensive} label="Комплексний пошук за всіма критеріями" hint="Зберегти всі знайдені бізнеси з повним аналізом. Вимкніть, щоб зберігати лише ті, що мають обрані проблеми." />
            <div className={`mt-4 transition ${comprehensive ? "pointer-events-none opacity-40" : ""}`}>
              <Chips options={Object.entries(meta.problems).map(([key, label]) => ({ key, label }))} value={problems} onChange={setProblems} />
            </div>
          </section>

          <section className="card card-pad animate-fade-up">
            <div className="mb-4 text-sm font-medium text-zinc-200">Джерела та параметри</div>
            <div className="grid gap-3 md:grid-cols-3">
              {meta.sources.map((s) => {
                const configured = s.key === "osm" || settings?.api_keys[s.key]?.configured;
                const on = sources.includes(s.key);
                return (
                  <button key={s.key} type="button" disabled={!configured}
                    onClick={() => setSources(on ? sources.filter((x) => x !== s.key) : [...sources, s.key])}
                    className={`rounded-xl border p-3 text-left transition ${on ? "border-accent-500/60 bg-accent-soft" : "border-white/10 bg-white/[0.02] hover:border-white/20"} disabled:opacity-40`}>
                    <div className="flex items-center justify-between text-sm font-medium text-zinc-100">{s.label}
                      {on && <CheckCircle2 className="h-4 w-4 text-accent-400" />}</div>
                    <div className="mt-1 text-xs text-zinc-500">{configured ? s.description : <>Потрібен API-ключ — <Link className="text-accent-400 underline" to="/settings">додати</Link></>}</div>
                  </button>
                );
              })}
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <div>
                <label className="label">Кількість результатів</label>
                <input type="number" min={1} max={1000} className="input" value={form.limit} onChange={(e) => setForm({ ...form, limit: Math.max(1, Math.min(1000, Number(e.target.value) || 1)) })} />
              </div>
              <Toggle checked={checkSites} onChange={setCheckSites} label="Перевіряти сайти" hint="Відкриває сайти бізнесів для аналізу (з дотриманням robots.txt)" />
              <Toggle checked={excludeChains} onChange={setExcludeChains} label="Виключати мережі" hint="Пропускати великі бренди (McDonald's, АТБ тощо)" />
            </div>
          </section>

          {err && <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300"><AlertTriangle className="h-4 w-4" />{err}</div>}
          <div className="flex justify-end">
            <button className="btn-primary px-6 py-3 text-base" onClick={start} disabled={!!running}>
              {running ? <Spinner /> : <Play className="h-4 w-4" />} Почати пошук
            </button>
          </div>
        </div>

        <div className="space-y-5">
          <section className="card card-pad animate-fade-up">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-medium text-zinc-200">Процес збору</div>
              {job && <span className={`text-xs font-medium ${jobStatus(job.status)[1]}`}>{running && <span className="mr-1.5 inline-block h-2 w-2 animate-pulse-dot rounded-full bg-accent-400" />}{jobStatus(job.status)[0]}</span>}
            </div>
            {!job ? (
              <div className="py-10 text-center text-sm text-zinc-500">Налаштуйте параметри й натисніть «Почати пошук». Тут у реальному часі з'явиться хід збору даних.</div>
            ) : (
              <>
                <div className="text-xs text-zinc-500">{job.location_label || [job.params.city, job.params.region].filter(Boolean).join(", ")}</div>
                <div className="mt-3 flex items-center justify-between text-xs text-zinc-400"><span>{STAGES[job.stage] || job.stage}</span><span className="font-mono">{job.progress_done}/{job.progress_total || "?"}</span></div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-ink-700">
                  <div className={`h-full rounded-full bg-gradient-to-r from-accent-500 to-indigo-400 transition-all duration-500 ${running && !job.progress_total ? "w-1/3 animate-pulse" : ""}`} style={job.progress_total ? { width: `${pct}%` } : undefined} />
                </div>
                <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                  {[["Знайдено", job.found_count], ["Збережено", job.saved_count], ["Нових", job.new_count], ["Дублікатів", job.duplicate_count]].map(([l, v]) => (
                    <div key={l as string} className="rounded-xl bg-ink-850 py-2"><div className="font-mono text-lg text-white">{v}</div><div className="text-[10px] uppercase tracking-wider text-zinc-500">{l}</div></div>
                  ))}
                </div>
                <div ref={logRef} className="mt-4 h-72 overflow-y-auto rounded-xl border border-white/[0.06] bg-ink-950 p-3 font-mono text-[11.5px] leading-relaxed">
                  {logs.map((l) => (
                    <div key={l.id} className={l.level === "error" ? "text-rose-400" : l.level === "warning" ? "text-amber-300" : "text-zinc-400"}>
                      <span className="text-zinc-600">{new Date(l.ts).toLocaleTimeString("uk-UA")} </span>{l.message}
                    </div>
                  ))}
                  {running && <div className="text-accent-400 animate-pulse-dot">▍</div>}
                </div>
                {job.error && <div className="mt-3 text-xs text-rose-300">{job.error}</div>}
                <div className="mt-4 flex flex-wrap gap-2">
                  {running && <button className="btn-danger" onClick={() => api.cancelJob(job.id)}><Square className="h-4 w-4" /> Зупинити</button>}
                  {!running && ["interrupted", "failed", "cancelled"].includes(job.status) && <button className="btn-ghost" onClick={() => resume(job)}><RotateCcw className="h-4 w-4" /> Продовжити</button>}
                  {job.saved_count > 0 && <Link className="btn-primary" to={`/businesses?job_id=${job.id}`}>Переглянути результати ({job.saved_count})</Link>}
                </div>
              </>
            )}
          </section>

          <section className="card card-pad animate-fade-up">
            <div className="mb-3 text-sm font-medium text-zinc-200">Історія пошуків</div>
            <div className="-mx-2 max-h-96 space-y-0.5 overflow-y-auto">
              {history.length === 0 && <div className="px-2 text-sm text-zinc-500">Ще немає</div>}
              {history.map((h) => {
                const [label, cls] = jobStatus(h.status);
                return (
                  <div key={h.id} className="flex items-center gap-2 rounded-xl px-2 py-2 hover:bg-white/[0.03]">
                    <button className="min-w-0 flex-1 text-left" onClick={() => { setLogs([]); setJob(h); }}>
                      <div className="truncate text-sm text-zinc-200">{h.params.city || h.params.region} <span className="text-zinc-500">· {(h.params.categories || []).slice(0, 2).map(catLabel).join(", ")}{(h.params.categories || []).length > 2 ? "…" : ""}</span></div>
                      <div className="text-xs text-zinc-500">{fmtDate(h.created_at)} · <span className={cls}>{label}</span> · {h.saved_count} збережено</div>
                    </button>
                    {!["running", "queued"].includes(h.status) && (
                      <button title="Видалити запис про пошук (бізнеси залишаться)" className="rounded-lg p-1.5 text-zinc-600 hover:bg-white/5 hover:text-rose-300"
                        onClick={async () => { await api.deleteJob(h.id); setHistory(history.filter((x) => x.id !== h.id)); if (job?.id === h.id) setJob(null); }}>
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
