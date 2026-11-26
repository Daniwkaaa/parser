import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Check, Shuffle, MessageSquareText, Instagram, Mail } from "lucide-react";
import { api } from "../lib/api";
import { Spinner } from "./ui";

export default function Outreach({ id, status, onContacted }: { id: number; status: string; onContacted: () => void }) {
  const [channel, setChannel] = useState<"instagram" | "email">("instagram");
  const [variant, setVariant] = useState(0);
  const [msg, setMsg] = useState<{ text: string; subject: string | null } | null>(null);
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setBusy(true);
    api.outreach(id, variant, channel).then((m) => { setMsg(m); setText(m.text); }).finally(() => setBusy(false));
  }, [id, variant, channel]);

  async function copy() {
    const full = channel === "email" && msg?.subject ? `Тема: ${msg.subject}\n\n${text}` : text;
    try { await navigator.clipboard.writeText(full); }
    catch {
      const ta = document.createElement("textarea"); ta.value = full; document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
    }
    setCopied(true); setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section className="card card-pad">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-200"><MessageSquareText className="h-4 w-4 text-accent-400" /> Готове повідомлення</div>
        <div className="flex rounded-xl border border-white/10 bg-ink-850 p-1 text-xs">
          {([["instagram", "Instagram / месенджер", Instagram], ["email", "Email", Mail]] as const).map(([k, l, Icon]) => (
            <button key={k} onClick={() => setChannel(k)} className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${channel === k ? "bg-accent-500 text-white" : "text-zinc-400 hover:text-zinc-200"}`}><Icon className="h-3.5 w-3.5" />{l}</button>
          ))}
        </div>
      </div>
      {channel === "email" && msg?.subject && <div className="mb-2 text-sm text-zinc-400">Тема: <span className="text-zinc-200">{msg.subject}</span></div>}
      <div className="relative">
        <textarea className="input min-h-[220px] resize-y leading-relaxed" value={text} onChange={(e) => setText(e.target.value)} />
        {busy && <div className="absolute right-3 top-3"><Spinner /></div>}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button className="btn-primary" onClick={copy} disabled={!text}>{copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}{copied ? "Скопійовано" : "Копіювати"}</button>
        <button className="btn-ghost" onClick={() => setVariant(variant + 1)}><Shuffle className="h-4 w-4" /> Інший варіант</button>
        {status !== "contacted" && <button className="btn-ghost" onClick={onContacted}>Позначити «Контакт встановлено»</button>}
        <span className="ml-auto text-xs text-zinc-500">Варіант {variant + 1}. Текст можна редагувати. Ім'я та підпис — у <Link className="text-accent-400 hover:underline" to="/settings">Налаштуваннях</Link>.</span>
      </div>
      <div className="mt-2 text-xs text-zinc-600">У тексті лише те, що програма реально перевірила. Перед відправкою варто глянути, чи нічого не змінилося.</div>
    </section>
  );
}
