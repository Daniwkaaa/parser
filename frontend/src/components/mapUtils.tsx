import L from "leaflet";
import { TileLayer } from "react-leaflet";
import { tierColor } from "../lib/format";
import { useMeta } from "../lib/meta";

// Стандартні тайли OpenStreetMap: безкоштовно й без ключа (правила: https://operations.osmfoundation.org/policies/tiles/).
// Темний вигляд робиться CSS-фільтром (клас .tiles-dark в index.css), тож сторонній ключ не потрібен.
const OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export function BaseLayer() {
  const { map } = useMeta();
  if (map?.style === "custom" && map.custom_url) {
    return <TileLayer key={map.custom_url} url={map.custom_url} attribution={map.custom_attribution || OSM_ATTR} />;
  }
  const dark = map?.style !== "light";
  return <TileLayer key={dark ? "dark" : "light"} url={OSM_URL} attribution={OSM_ATTR} maxZoom={19} className={dark ? "tiles-dark" : ""} />;
}

const cache: Record<string, L.DivIcon> = {};
export function tierIcon(tier: string): L.DivIcon {
  if (!cache[tier]) {
    const c = tierColor(tier);
    cache[tier] = L.divIcon({
      className: "",
      html: `<div style="width:14px;height:14px;border-radius:50%;background:${c};border:2px solid #0d0f14;box-shadow:0 0 0 3px ${c}40,0 0 12px ${c}"></div>`,
      iconSize: [14, 14], iconAnchor: [7, 7],
    });
  }
  return cache[tier];
}
