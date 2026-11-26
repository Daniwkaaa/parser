import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { api, type Filters } from "../lib/api";
import { useMeta } from "../lib/meta";
import { Chips, Empty, PageHeader, ScoreBadge, Spinner } from "../components/ui";
import { BaseLayer, tierIcon } from "../components/mapUtils";

type Pt = Awaited<ReturnType<typeof api.mapPoints>>[number];

function FitBounds({ pts }: { pts: Pt[] }) {
  const map = useMap();
  useEffect(() => {
    if (!pts.length) return;
    const b = L.latLngBounds(pts.map((p) => [p.lat, p.lon] as [number, number]));
    map.fitBounds(b, { padding: [40, 40], maxZoom: 15 });
  }, [pts, map]);
  return null;
}

export default function MapPage() {
  const meta = useMeta();
  const [tiers, setTiers] = useState<string[]>([]);
  const [cats, setCats] = useState<string[]>([]);
  const [pts, setPts] = useState<Pt[] | null>(null);
  const filters: Filters = useMemo(() => ({ tiers, categories: cats }), [tiers, cats]);
  useEffect(() => { api.mapPoints(filters).then(setPts); }, [filters]);
  const catLabel = (k: string) => meta.categories.find((c) => c.key === k)?.label || k;

  return (
    <div>
      <PageHeader title="Карта бізнесів" subtitle={pts ? `${pts.length} точок на карті` : undefined} />
      <div className="card card-pad mb-4 grid gap-4 lg:grid-cols-[auto_1fr]">
        <div><div className="label">Потенціал</div><Chips options={[{ key: "high", label: "Високий" }, { key: "medium", label: "Середній" }, { key: "low", label: "Низький" }]} value={tiers} onChange={setTiers} /></div>
        <div><div className="label">Категорії</div><Chips options={meta.categories} value={cats} onChange={setCats} /></div>
      </div>
      {!pts ? <div className="flex items-center gap-2 text-zinc-500"><Spinner /> Завантаження…</div> :
        pts.length === 0 && !tiers.length && !cats.length ? <Empty title="Немає даних для карти" text="Спершу виконайте пошук." action={<Link className="btn-primary" to="/search">До пошуку</Link>} /> : (
          <div className="card overflow-hidden p-1">
            <div className="h-[calc(100vh-290px)] min-h-[420px]">
              <MapContainer center={[49.0, 31.0]} zoom={6} style={{ height: "100%" }}>
                <BaseLayer />
                <FitBounds pts={pts} />
                {pts.map((p) => (
                  <Marker key={p.id} position={[p.lat, p.lon]} icon={tierIcon(p.lead_tier)}>
                    <Popup>
                      <div className="min-w-[200px]">
                        <div className="mb-1 flex items-center justify-between gap-2"><span className="font-semibold">{p.name}</span><ScoreBadge score={p.lead_score} tier={p.lead_tier} /></div>
                        <div className="text-xs text-zinc-400">{catLabel(p.category)}</div>
                        {p.address && <div className="text-xs text-zinc-400">{p.address}</div>}
                        <div className="mt-1 text-xs">Сайт: {meta.status_labels[p.website_status]}</div>
                        <Link to={`/businesses/${p.id}`} className="mt-2 inline-block text-xs font-medium text-accent-400">Відкрити картку →</Link>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>
          </div>
        )}
      <div className="mt-3 flex gap-4 text-xs text-zinc-500">
        {[["high", "#34d399", "Високий 70–100"], ["medium", "#fbbf24", "Середній 40–69"], ["low", "#71717a", "Низький 0–39"]].map(([k, c, l]) => (
          <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />{l}</span>
        ))}
      </div>
    </div>
  );
}
