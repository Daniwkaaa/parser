import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MapContainer, Marker } from "react-leaflet";
import { ArrowLeft, RefreshCw, Trash2, ExternalLink, Phone, Mail, Globe, Instagram, Facebook, MapPin, Clock, Sparkles, AlertCircle, Pencil, Check, X, Send } from "lucide-react";
import { api, type BusinessFull } from "../lib/api";
import { useMeta } from "../lib/meta";
import { ensureUrl, fmtDate, socialUrl } from "../lib/format";
import { Empty, ScoreBadge, Spinner, StatusBadge } from "../components/ui";
import { BaseLayer, tierIcon } from "../components/mapUtils";
import Outreach from "../components/Outreach";

function Row({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <span className="mt-0.5 text-zinc-500">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</div>
        <div className="break-words text-sm text-zinc-200">{children}</div>
      </div>
    </div>
  );
}

const SOURCE_LABEL: Record<string, string> = { osm: "OpenStreetMap", google_places: "Google Places", serpapi: "SerpAPI" };

export default function BusinessDetail() {
  const { id } = useParams();
  const meta = useMeta();
  const nav = useNavigate();
  const [b, setB] = useState<BusinessFull | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [edit, setEdit] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});

  useEffect(() => { api.business(Number(id)).then(setB).catch((e) => setErr(e.message)); }, [id]);

  if (err) return <Empty title="Помилка" text={err} action={<Link className="btn-ghost" to="/businesses">До бази</Link>} />;
  if (!b) return <div className="flex items-center gap-2 text-zinc-500"><Spinner /> Завантаження…</div>;
  const wa = b.website_analysis || {};
  const cat = meta.categories.find((c) => c.key === b.category);

  async function recheck() {
    setBusy(true);
    try { setB(await api.recheck(b!.id)); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }
  async function saveEdit() {
    setBusy(true);
    try { setB(await api.updateBusiness(b!.id, draft)); setEdit(false); } finally { setBusy(false); }
  }
  async function addNote() {
    if (!note.trim()) return;
    setB(await api.addNote(b!.id, note)); setNote("");
  }

  const fields: [string, string][] = [["name", "Назва"], ["phone", "Телефон"], ["email", "Email"], ["website", "Вебсайт"], ["instagram", "Instagram"], ["facebook", "Facebook"], ["address", "Адреса"]];
  const yesNo = (v: boolean | null | undefined) => (v === true ? "так" : v === false ? "ні" : "—");

  return (
    <div className="animate-fade-up">
      <button onClick={() => nav(-1)} className="mb-4 inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-200"><ArrowLeft className="h-4 w-4" /> Назад</button>

      <div className="card card-pad mb-5 flex flex-wrap items-center gap-6">
        <ScoreBadge score={b.lead_score} tier={b.lead_tier} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="text-xs uppercase tracking-wider text-accent-400">{b.category_label}{b.raw_type ? ` · ${b.raw_type}` : ""}</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">{b.name}</h1>
          <div className="mt-1 text-sm text-zinc-400">{[b.address, b.city].filter(Boolean).join(", ") || "Адреса не вказана в джерелі"}</div>
          {b.brand && <div className="mt-1 text-xs text-amber-300">Позначено як частина мережі/бренду: {b.brand}</div>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select className="input w-52" value={b.status} onChange={async (e) => setB(await api.updateBusiness(b.id, { status: e.target.value }))}>
            {Object.entries(meta.client_statuses).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button className="btn-ghost" onClick={recheck} disabled={busy}>{busy ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Перевірити повторно</button>
          <button className="btn-danger px-3" title="Видалити з бази" onClick={async () => { if (confirm("Видалити цей бізнес з бази?")) { await api.deleteBusiness(b.id); nav("/businesses"); } }}><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <section className="card card-pad">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-200"><Sparkles className="h-4 w-4 text-accent-400" /> Висновок і рекомендація</div>
            <p className="text-[15px] leading-relaxed text-zinc-200">{b.summary}</p>
            <p className="mt-3 rounded-xl border border-accent-500/20 bg-accent-soft px-4 py-3 text-sm leading-relaxed text-accent-400">{b.recommendation}</p>
            {b.recommended_services.length > 0 && (
              <div className="mt-4">
                <div className="label">Що запропонувати</div>
                <ul className="space-y-1.5">{b.recommended_services.map((s) => <li key={s} className="flex items-start gap-2 text-sm text-zinc-300"><Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />{s}</li>)}</ul>
              </div>
            )}
          </section>

          <Outreach id={b.id} status={b.status} onContacted={async () => setB(await api.updateBusiness(b.id, { status: "contacted" }))} />

          <section className="card card-pad">
            <div className="mb-4 text-sm font-medium text-zinc-200">Цифрова присутність</div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[["Вебсайт", b.website_status], [cat?.offer_kind === "catalog" ? "Онлайн-каталог" : "Онлайн-меню", b.menu_status], [cat?.booking_kind === "reservation" ? "Бронювання" : "Онлайн-запис", b.booking_status], ["Застарілість сайту", b.outdated_status]].map(([l, s]) => (
                <div key={l} className="rounded-xl border border-white/[0.06] bg-ink-850 p-3">
                  <div className="mb-2 text-xs text-zinc-500">{l}</div>
                  <StatusBadge status={s} labels={l === "Застарілість сайту" ? { ...meta.status_labels, yes: "Застарілий", no: "Сучасний" } : meta.status_labels} />
                </div>
              ))}
            </div>
            <div className="mt-5">
              <div className="label">Виявлені проблеми</div>
              {b.problem_details.length === 0 ? <div className="text-sm text-zinc-500">Проблем не виявлено або дані ще не перевірені.</div> : (
                <ul className="space-y-2">
                  {b.problem_details.map((p, i) => (
                    <li key={i} className="flex gap-3 rounded-xl border border-white/[0.05] bg-white/[0.015] px-3 py-2.5">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                      <div><div className="text-sm font-medium text-zinc-200">{p.label}</div><div className="text-sm text-zinc-400">{p.text}</div></div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="card card-pad">
            <div className="mb-3 flex items-center justify-between text-sm font-medium text-zinc-200">Технічний аналіз сайту
              <span className="text-xs font-normal text-zinc-500">{wa.checked_at ? `перевірено ${fmtDate(wa.checked_at)}` : "не перевірявся"}</span></div>
            {!b.website ? <div className="text-sm text-zinc-500">Власний сайт не вказано в жодному джерелі — технічна перевірка не проводилась.</div> :
              !wa.checked ? <div className="text-sm text-zinc-500">Сайт ще не перевірено{wa.error ? `: ${wa.error}` : ""}. Натисніть «Перевірити повторно».</div> : (
                <div className="grid gap-x-8 gap-y-1 text-sm md:grid-cols-2">
                  {([
                    ["Статус", wa.status === "ok" ? "доступний" : wa.status === "unreachable" ? "не відкривається" : wa.status === "parked" ? "заглушка" : wa.status],
                    ["HTTP-код", wa.http_status ?? "—"], ["Кінцева адреса", wa.final_url || "—"], ["HTTPS", yesNo(wa.https)],
                    ["Мобільна адаптація", yesNo(wa.has_viewport)], ["Час відповіді", wa.response_time ? `${wa.response_time} с` : "—"],
                    ["Заголовок", wa.title || "—"], ["CMS / генератор", wa.generator || "—"], ["Рік у футері", wa.copyright_year || "—"],
                    ["Меню", wa.menu_evidence || yesNo(wa.has_menu)], ["Каталог", wa.catalog_evidence || yesNo(wa.has_catalog)],
                    ["Запис / бронювання", wa.booking_evidence || yesNo(wa.has_booking)], ["Послуги / ціни", wa.services_evidence || yesNo(wa.has_services)],
                    ["Email на сайті", (wa.emails || []).join(", ") || "—"],
                  ] as [string, ReactNode][]).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-4 border-b border-white/[0.04] py-1.5"><span className="text-zinc-500">{k}</span><span className="truncate text-right text-zinc-300" title={String(v)}>{v}</span></div>
                  ))}
                  {wa.error && <div className="md:col-span-2 pt-2 text-xs text-rose-300">{wa.error}</div>}
                  {(wa.outdated_signals || []).length > 0 && (
                    <div className="md:col-span-2 pt-3"><div className="label">Ознаки застарілості</div>
                      <ul className="list-disc space-y-0.5 pl-5 text-zinc-400">{wa.outdated_signals!.map((s) => <li key={s.code}>{s.text}</li>)}</ul></div>
                  )}
                </div>
              )}
          </section>

          <section className="card card-pad">
            <div className="mb-3 text-sm font-medium text-zinc-200">Нотатки</div>
            <div className="flex gap-2">
              <textarea className="input min-h-[44px] flex-1 resize-y" rows={2} placeholder="Коментар: з ким говорили, що запропонували…" value={note} onChange={(e) => setNote(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) addNote(); }} />
              <button className="btn-primary self-start" onClick={addNote} disabled={!note.trim()}><Send className="h-4 w-4" /></button>
            </div>
            <div className="mt-3 space-y-2">
              {b.notes.map((n) => (
                <div key={n.id} className="group flex gap-3 rounded-xl bg-ink-850 px-3 py-2.5">
                  <div className="flex-1"><div className="whitespace-pre-wrap text-sm text-zinc-200">{n.text}</div><div className="mt-1 text-xs text-zinc-500">{fmtDate(n.created_at)}</div></div>
                  <button className="text-zinc-600 opacity-0 transition hover:text-rose-300 group-hover:opacity-100" onClick={async () => { await api.deleteNote(b.id, n.id); setB({ ...b, notes: b.notes.filter((x) => x.id !== n.id) }); }}><X className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-5">
          <section className="card card-pad">
            <div className="mb-1 flex items-center justify-between text-sm font-medium text-zinc-200">Контакти
              {!edit ? <button className="text-zinc-500 hover:text-zinc-200" title="Редагувати" onClick={() => { setDraft(Object.fromEntries(fields.map(([k]) => [k, (b as any)[k] || ""]))); setEdit(true); }}><Pencil className="h-4 w-4" /></button>
                : <span className="flex gap-2"><button className="text-emerald-400" onClick={saveEdit}><Check className="h-4 w-4" /></button><button className="text-zinc-500" onClick={() => setEdit(false)}><X className="h-4 w-4" /></button></span>}
            </div>
            {edit ? (
              <div className="mt-3 space-y-2">{fields.map(([k, l]) => <div key={k}><label className="label">{l}</label><input className="input" value={draft[k] || ""} onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} /></div>)}</div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                <Row icon={<Phone className="h-4 w-4" />} label={b.contact_verified ? "Телефон · перевірений формат" : "Телефон"}>{b.phone ? <a className="hover:text-accent-400" href={`tel:${b.phone.split(/[;,]/)[0]}`}>{b.phone}</a> : <span className="text-zinc-500">не вказано</span>}</Row>
                <Row icon={<Mail className="h-4 w-4" />} label="Email">{b.email ? <a className="hover:text-accent-400" href={`mailto:${b.email}`}>{b.email}</a> : <span className="text-zinc-500">не знайдено</span>}</Row>
                <Row icon={<Globe className="h-4 w-4" />} label="Вебсайт">{b.website ? <a className="inline-flex items-center gap-1 hover:text-accent-400" href={ensureUrl(b.website)} target="_blank" rel="noreferrer">{b.website}<ExternalLink className="h-3 w-3" /></a> : <span className="text-zinc-500">відсутній</span>}</Row>
                <Row icon={<Instagram className="h-4 w-4" />} label="Instagram">{b.instagram ? <a className="hover:text-accent-400" href={socialUrl("instagram", b.instagram)} target="_blank" rel="noreferrer">{b.instagram}</a> : <span className="text-zinc-500">не знайдено</span>}</Row>
                <Row icon={<Facebook className="h-4 w-4" />} label="Facebook">{b.facebook ? <a className="hover:text-accent-400" href={socialUrl("facebook", b.facebook)} target="_blank" rel="noreferrer">{b.facebook}</a> : <span className="text-zinc-500">не знайдено</span>}</Row>
                {Object.entries(b.socials || {}).map(([k, v]) => <Row key={k} icon={<Globe className="h-4 w-4" />} label={k}><a className="hover:text-accent-400" href={socialUrl(k, v)} target="_blank" rel="noreferrer">{v}</a></Row>)}
                <Row icon={<Clock className="h-4 w-4" />} label="Графік роботи">{b.opening_hours || <span className="text-zinc-500">не вказано</span>}</Row>
                {b.rating != null && <Row icon={<Sparkles className="h-4 w-4" />} label="Рейтинг">{b.rating} ★ ({b.reviews_count ?? 0} відгуків)</Row>}
              </div>
            )}
          </section>

          {b.lat != null && b.lon != null && (
            <section className="card overflow-hidden">
              <div className="h-56">
                <MapContainer center={[b.lat, b.lon]} zoom={16} scrollWheelZoom={false} style={{ height: "100%", borderRadius: 0 }}>
                  <BaseLayer />
                  <Marker position={[b.lat, b.lon]} icon={tierIcon(b.lead_tier)} />
                </MapContainer>
              </div>
              <div className="flex items-center justify-between px-4 py-3 text-xs text-zinc-500">
                <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{b.lat.toFixed(5)}, {b.lon.toFixed(5)}</span>
                <a className="text-accent-400 hover:underline" target="_blank" rel="noreferrer" href={`https://www.google.com/maps/search/?api=1&query=${b.lat},${b.lon}`}>Google Maps</a>
              </div>
            </section>
          )}

          <section className="card card-pad">
            <div className="mb-1 text-sm font-medium text-zinc-200">Знайти більше вручну</div>
            <div className="mb-3 text-xs text-zinc-500">Відкритих даних мало? Перевірте сайт чи соцмережі вручну й допишіть знайдене в контакти (олівець вище).</div>
            <div className="flex flex-wrap gap-2">
              {[
                ["Google", `${b.name} ${b.city || ""}`],
                ["Instagram", `site:instagram.com ${b.name} ${b.city || ""}`],
                ["Facebook", `site:facebook.com ${b.name} ${b.city || ""}`],
              ].map(([l, q]) => (
                <a key={l} className="btn-ghost px-3 py-1.5 text-xs" target="_blank" rel="noreferrer" href={`https://www.google.com/search?q=${encodeURIComponent(q.trim())}`}>{l} <ExternalLink className="h-3 w-3" /></a>
              ))}
              <a className="btn-ghost px-3 py-1.5 text-xs" target="_blank" rel="noreferrer" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${b.name} ${b.address || b.city || ""}`.trim())}`}>Google Maps <ExternalLink className="h-3 w-3" /></a>
            </div>
          </section>

          <section className="card card-pad">
            <div className="mb-3 text-sm font-medium text-zinc-200">Оцінка Lead Score</div>
            <div className="space-y-1.5">
              {b.score_breakdown.map((s) => <div key={s.key} className="flex justify-between text-sm"><span className="text-zinc-400">{s.label}</span><span className="font-mono text-emerald-400">+{s.points}</span></div>)}
              {b.score_breakdown.length === 0 && <div className="text-sm text-zinc-500">Балів не нараховано</div>}
              <div className="flex justify-between border-t border-white/[0.06] pt-2 text-sm font-medium"><span>Разом (макс. 100)</span><span className="font-mono text-white">{b.lead_score}</span></div>
            </div>
          </section>

          <section className="card card-pad">
            <div className="mb-3 text-sm font-medium text-zinc-200">Джерела</div>
            <div className="space-y-2">
              {b.sources_full.map((s) => (
                <div key={s.source + s.source_id} className="flex items-center justify-between text-sm">
                  <span className="text-zinc-300">{SOURCE_LABEL[s.source] || s.source}</span>
                  {s.url ? <a className="inline-flex items-center gap-1 text-xs text-accent-400 hover:underline" href={s.url} target="_blank" rel="noreferrer">профіль <ExternalLink className="h-3 w-3" /></a> : <span className="font-mono text-xs text-zinc-500">{s.source_id}</span>}
                </div>
              ))}
              {b.map_url && <a className="inline-flex items-center gap-1 text-xs text-accent-400 hover:underline" href={b.map_url} target="_blank" rel="noreferrer">Відкрити на карті джерела <ExternalLink className="h-3 w-3" /></a>}
            </div>
            <div className="mt-3 text-xs text-zinc-500">Додано {fmtDate(b.created_at)} · оновлено {fmtDate(b.updated_at)}</div>
          </section>
        </div>
      </div>
    </div>
  );
}
