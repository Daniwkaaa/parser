import { useEffect, useState } from "react";
import { KeyRound, Database, SlidersHorizontal, Gauge, Download, Check, RotateCcw, ExternalLink, Map as MapIcon, MessageSquareText } from "lucide-react";
import { api, type MapSettings, type SettingsData } from "../lib/api";
import { useMeta, useMetaReload } from "../lib/meta";
import { PageHeader, Spinner, Toggle } from "../components/ui";

const KEY_LINKS: Record<string, string> = {
  google_places: "https://console.cloud.google.com/google/maps-apis/credentials",
  serpapi: "https://serpapi.com/manage-api-key",
};

function Saved({ show }: { show: boolean }) {
  return show ? <span className="inline-flex items-center gap-1 text-xs text-emerald-400 animate-fade-up"><Check className="h-3.5 w-3.5" />Збережено</span> : null;
}

export default function SettingsPage() {
  const [s, setS] = useState<SettingsData | null>(null);
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const meta = useMeta();
  const reloadMeta = useMetaReload();
  const [mapCfg, setMapCfg] = useState<MapSettings>(meta.map);
  const [mapErr, setMapErr] = useState<string | null>(null);
  const load = () => api.settings().then(setS);
  useEffect(() => { load(); }, []);
  const flash = (k: string) => { setSaved(k); setTimeout(() => setSaved(null), 2000); };

  if (!s) return <div className="flex items-center gap-2 text-zinc-500"><Spinner /> Завантаження…</div>;

  async function saveKeys() {
    await api.saveKeys(keys); setKeys({}); await load(); flash("keys");
  }
  async function saveScoring() {
    setBusy(true);
    try { const r = await api.saveScoring(s!.scoring); setMsg(`Оцінку перераховано для ${r.rescored} бізнесів`); flash("scoring"); }
    catch (e: any) { setMsg(e.message); } finally { setBusy(false); }
  }

  const maxPossible = Object.entries(s.scoring.weights).filter(([k]) => !["website_unreachable", "website_improvable"].includes(k)).reduce((a, [, v]) => a + v, 0);

  return (
    <div>
      <PageHeader title="Налаштування" subtitle="API-ключі, джерела даних, параметри пошуку та логіка оцінювання" />
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="card card-pad animate-fade-up">
          <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><KeyRound className="h-4 w-4 text-accent-400" /> API-ключі</div><Saved show={saved === "keys"} /></div>
          <p className="mb-4 text-xs leading-relaxed text-zinc-500">OpenStreetMap працює без ключів. Додаткові джерела підключаються вашими власними ключами. Ключі зберігаються лише у вашій локальній базі даних (або задаються у файлі <code>.env</code>).</p>
          <div className="space-y-4">
            {s.source_list.filter((x) => x.requires_key).map((src) => {
              const st = s.api_keys[src.key];
              return (
                <div key={src.key}>
                  <label className="label flex items-center justify-between">{src.label}
                    <span className={st?.configured ? "normal-case tracking-normal text-emerald-400" : "normal-case tracking-normal text-zinc-500"}>{st?.configured ? `налаштовано ${st.masked}${st.from_env ? " (.env)" : ""}` : "не налаштовано"}</span></label>
                  <input className="input font-mono" type="password" placeholder={st?.configured ? "Введіть новий ключ, щоб замінити" : "Вставте API-ключ"} value={keys[src.key] ?? ""} onChange={(e) => setKeys({ ...keys, [src.key]: e.target.value })} />
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-3 text-xs text-zinc-500">{src.key_help}
                    <a className="inline-flex items-center gap-1 text-accent-400 hover:underline" href={KEY_LINKS[src.key]} target="_blank" rel="noreferrer">Отримати ключ <ExternalLink className="h-3 w-3" /></a>
                    {st?.configured && !st.from_env && <button className="text-rose-300 hover:underline" onClick={async () => { await api.saveKeys({ [src.key]: "" }); load(); }}>видалити</button>}
                  </div>
                </div>
              );
            })}
          </div>
          <button className="btn-primary mt-4" onClick={saveKeys} disabled={!Object.values(keys).some(Boolean)}>Зберегти ключі</button>
        </section>

        <section className="card card-pad animate-fade-up">
          <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><Database className="h-4 w-4 text-accent-400" /> Джерела даних за замовчуванням</div><Saved show={saved === "sources"} /></div>
          <div className="space-y-4">
            {s.source_list.map((src) => (
              <Toggle key={src.key} checked={!!s.sources[src.key]} label={src.label} hint={src.description + (src.requires_key && !s.api_keys[src.key]?.configured ? " Потрібен API-ключ." : "")}
                onChange={async (v) => { const next = { ...s.sources, [src.key]: v }; setS({ ...s, sources: next }); await api.saveSources(next); flash("sources"); }} />
            ))}
          </div>
          <div className="mt-6 mb-4 flex items-center justify-between border-t border-white/[0.06] pt-5"><div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><SlidersHorizontal className="h-4 w-4 text-accent-400" /> Параметри пошуку за замовчуванням</div><Saved show={saved === "search"} /></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className="label">Країна</label><input className="input" value={s.search.country} onChange={(e) => setS({ ...s, search: { ...s.search, country: e.target.value } })} /></div>
            <div><label className="label">Кількість результатів</label><input className="input" type="number" min={1} max={1000} value={s.search.limit} onChange={(e) => setS({ ...s, search: { ...s.search, limit: Number(e.target.value) } })} /></div>
          </div>
          <div className="mt-4 space-y-3">
            <Toggle checked={s.search.check_websites} onChange={(v) => setS({ ...s, search: { ...s.search, check_websites: v } })} label="Перевіряти сайти бізнесів" />
            <Toggle checked={s.search.exclude_chains} onChange={(v) => setS({ ...s, search: { ...s.search, exclude_chains: v } })} label="Виключати мережеві бренди" />
          </div>
          <button className="btn-ghost mt-4" onClick={async () => { await api.saveSearchDefaults(s.search); flash("search"); }}>Зберегти параметри</button>
        </section>

        <section className="card card-pad animate-fade-up">
          <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><Gauge className="h-4 w-4 text-accent-400" /> Налаштування Lead Score</div><Saved show={saved === "scoring"} /></div>
          <div className="space-y-3">
            {Object.entries(s.scoring.weights).map(([k, v]) => (
              <div key={k} className="grid grid-cols-[1fr_140px_48px] items-center gap-3">
                <span className="text-sm text-zinc-300">{s.scoring_labels[k] || k}</span>
                <input type="range" min={0} max={50} value={v} className="accent-[#7c6cff]" onChange={(e) => setS({ ...s, scoring: { ...s.scoring, weights: { ...s.scoring.weights, [k]: Number(e.target.value) } } })} />
                <span className="text-right font-mono text-sm text-white">+{v}</span>
              </div>
            ))}
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/[0.06] pt-4">
            <div><label className="label">Високий потенціал від</label><input className="input" type="number" min={1} max={100} value={s.scoring.thresholds.high} onChange={(e) => setS({ ...s, scoring: { ...s.scoring, thresholds: { ...s.scoring.thresholds, high: Number(e.target.value) } } })} /></div>
            <div><label className="label">Середній потенціал від</label><input className="input" type="number" min={0} max={99} value={s.scoring.thresholds.medium} onChange={(e) => setS({ ...s, scoring: { ...s.scoring, thresholds: { ...s.scoring.thresholds, medium: Number(e.target.value) } } })} /></div>
          </div>
          <div className="mt-2 text-xs text-zinc-500">Максимум за основними критеріями: {maxPossible} (обрізається до 100). Після збереження оцінка перераховується для всієї бази без нових запитів.</div>
          {msg && <div className="mt-3 text-xs text-zinc-400">{msg}</div>}
          <div className="mt-4 flex gap-2">
            <button className="btn-primary" onClick={saveScoring} disabled={busy}>{busy && <Spinner />} Зберегти й перерахувати</button>
            <button className="btn-ghost" onClick={async () => { const r = await api.resetScoring(); await load(); setMsg(`Скинуто до стандартних, перераховано ${r.rescored}`); }}><RotateCcw className="h-4 w-4" /> Стандартні</button>
          </div>
        </section>

        <section className="card card-pad animate-fade-up">
          <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><MessageSquareText className="h-4 w-4 text-accent-400" /> Готові повідомлення</div><Saved show={saved === "outreach"} /></div>
          <p className="mb-4 text-xs text-zinc-500">Ці дані підставляються в повідомлення для бізнесів. Усі поля необов'язкові.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {([["sender_name", "Ваше ім'я", "Данило"], ["company", "Компанія / студія", "WebStudio"], ["phone", "Телефон для підпису", "+380…"], ["portfolio", "Посилання на портфоліо", "https://…"]] as const).map(([k, l, ph]) => (
              <div key={k}><label className="label">{l}</label><input className="input" placeholder={ph} value={(s.outreach as any)[k] || ""} onChange={(e) => setS({ ...s, outreach: { ...s.outreach, [k]: e.target.value } })} /></div>
            ))}
          </div>
          <div className="mt-3 flex gap-4 text-sm text-zinc-300">
            <span className="text-xs uppercase tracking-wider text-zinc-500">Писати від імені:</span>
            {([["m", "чоловіка"], ["f", "жінки"]] as const).map(([k, l]) => (
              <label key={k} className="flex items-center gap-1.5"><input type="radio" name="gender" className="accent-[#7c6cff]" checked={(s.outreach.gender || "m") === k} onChange={() => setS({ ...s, outreach: { ...s.outreach, gender: k } })} />{l}</label>
            ))}
          </div>
          <button className="btn-ghost mt-4" onClick={async () => { await api.saveOutreach(s.outreach as any); flash("outreach"); }}>Зберегти</button>
        </section>

        <section className="card card-pad animate-fade-up">
          <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><MapIcon className="h-4 w-4 text-accent-400" /> Карта</div><Saved show={saved === "map"} /></div>
          <div className="space-y-2">
            {([["dark", "Темна (OpenStreetMap, безкоштовно, без ключа)"], ["light", "Світла (OpenStreetMap, безкоштовно, без ключа)"], ["custom", "Власний сервер тайлів (CARTO, MapTiler тощо з вашим ключем)"]] as const).map(([k, l]) => (
              <label key={k} className="flex cursor-pointer items-center gap-2 text-sm text-zinc-300">
                <input type="radio" name="mapstyle" className="accent-[#7c6cff]" checked={mapCfg.style === k} onChange={() => setMapCfg({ ...mapCfg, style: k })} />{l}
              </label>
            ))}
          </div>
          {mapCfg.style === "custom" && (
            <div className="mt-3 space-y-3">
              <div><label className="label">URL тайлів</label><input className="input font-mono" placeholder="https://api.maptiler.com/maps/streets-v2-dark/{z}/{x}/{y}.png?key=ВАШ_КЛЮЧ" value={mapCfg.custom_url} onChange={(e) => setMapCfg({ ...mapCfg, custom_url: e.target.value })} /></div>
              <div><label className="label">Атрибуція</label><input className="input" placeholder="© MapTiler © OpenStreetMap contributors" value={mapCfg.custom_attribution} onChange={(e) => setMapCfg({ ...mapCfg, custom_attribution: e.target.value })} /></div>
            </div>
          )}
          {mapErr && <div className="mt-2 text-xs text-rose-300">{mapErr}</div>}
          <button className="btn-ghost mt-4" onClick={async () => { setMapErr(null); try { await api.saveMap(mapCfg); await reloadMeta(); flash("map"); } catch (e: any) { setMapErr(e.message); } }}>Зберегти карту</button>
        </section>

        <section className="card card-pad animate-fade-up">
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-zinc-200"><Download className="h-4 w-4 text-accent-400" /> Експорт даних</div>
          <p className="mb-4 text-sm text-zinc-400">Вивантажити всю базу. Щоб експортувати відфільтровану вибірку, скористайтеся кнопками на сторінці «База бізнесів».</p>
          <div className="flex flex-wrap gap-2">
            <a className="btn-ghost" href={api.exportUrl("xlsx", {})}><Download className="h-4 w-4" /> Уся база — Excel (XLSX)</a>
            <a className="btn-ghost" href={api.exportUrl("csv", {})}><Download className="h-4 w-4" /> Уся база — CSV</a>
            <a className="btn-ghost" href={api.exportUrl("xlsx", { tiers: ["high"] })}><Download className="h-4 w-4" /> Лише високий потенціал</a>
          </div>
        </section>
      </div>
    </div>
  );
}
