import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LayoutDashboard, Search, Database, Map, Settings, Menu, X, Radar } from "lucide-react";

const NAV = [
  { to: "/", label: "Головна", icon: LayoutDashboard },
  { to: "/search", label: "Пошук", icon: Search },
  { to: "/businesses", label: "База бізнесів", icon: Database },
  { to: "/map", label: "Карта", icon: Map },
  { to: "/settings", label: "Налаштування", icon: Settings },
];

export default function Layout() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${isActive ? "bg-accent-soft text-white" : "text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-100"}`}>
          {({ isActive }) => (
            <>
              <Icon className={`h-4 w-4 ${isActive ? "text-accent-400" : "text-zinc-500 group-hover:text-zinc-300"}`} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
  const brand = (
    <div className="flex items-center gap-2.5 px-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent-400 to-indigo-600 shadow-glow">
        <Radar className="h-5 w-5 text-white" />
      </div>
      <div>
        <div className="text-sm font-semibold text-white">LeadFinder</div>
        <div className="text-[11px] text-zinc-500">Digital gap scanner</div>
      </div>
    </div>
  );
  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-8 border-r border-white/[0.06] bg-ink-950/60 px-3 py-5 backdrop-blur lg:flex">
        {brand}
        {nav}
        <div className="mt-auto px-2 text-[11px] leading-relaxed text-zinc-600">
          Дані карт © учасники <a className="text-zinc-500 hover:text-zinc-300" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> (ODbL)
        </div>
      </aside>
      <div className="fixed inset-x-0 top-0 z-[1000] flex items-center justify-between border-b border-white/[0.06] bg-ink-950/90 px-4 py-3 backdrop-blur lg:hidden">
        {brand}
        <button className="btn-ghost px-2.5" onClick={() => setOpen(!open)} aria-label="Меню">{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
      </div>
      {open && <div className="fixed inset-x-0 top-[61px] z-[1000] border-b border-white/[0.06] bg-ink-950 p-3 lg:hidden">{nav}</div>}
      <main key={loc.pathname.split("/")[1]} className="min-w-0 flex-1 px-4 pb-10 pt-20 sm:px-6 lg:px-10 lg:pt-8">
        <div className="mx-auto max-w-[1400px]"><Outlet /></div>
      </main>
    </div>
  );
}
