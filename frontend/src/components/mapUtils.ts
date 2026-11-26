import L from "leaflet";
import { tierColor } from "../lib/format";

export const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
export const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

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
