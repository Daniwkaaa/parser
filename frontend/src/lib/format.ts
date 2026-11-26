export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("uk-UA", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function tierColor(tier: string): string {
  return tier === "high" ? "#34d399" : tier === "medium" ? "#fbbf24" : "#71717a";
}

export function tierLabel(tier: string): string {
  return tier === "high" ? "Високий" : tier === "medium" ? "Середній" : "Низький";
}

export function ensureUrl(u: string): string {
  if (/^https?:\/\//i.test(u)) return u;
  return "https://" + u.replace(/^\/\//, "");
}

export function socialUrl(net: string, v: string): string {
  if (/^https?:\/\//i.test(v) || v.startsWith("viber:")) return v;
  const h = v.replace(/^@/, "");
  const base: Record<string, string> = { instagram: "https://instagram.com/", facebook: "https://facebook.com/", telegram: "https://t.me/", tiktok: "https://tiktok.com/@", whatsapp: "https://wa.me/" };
  return base[net] ? base[net] + h : ensureUrl(v);
}
