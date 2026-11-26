"""Каталог категорій бізнесу та їх відповідність тегам OSM і пошуковим запитам.

offer_kind: що логічно пропонувати бізнесу цієї категорії
  menu     — онлайн-меню (заклади харчування)
  catalog  — каталог товарів/послуг (магазини)
  services — перелік послуг із цінами (сервіси)
booking_kind:
  booking     — онлайн-запис (салони, СТО, клініки)
  reservation — бронювання (готелі, ресторани)
  none        — не застосовується
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    group: str
    osm: tuple[str, ...]  # фільтри Overpass без дужок, напр. 'amenity"="cafe'
    query: str  # ключове слово для текстового пошуку (Google/SerpAPI)
    offer_kind: str = "services"
    booking_kind: str = "none"
    google_types: tuple[str, ...] = field(default_factory=tuple)
    noun: str = "Бізнес"  # як назвати бізнес у тексті висновку


def _t(k: str, v: str) -> str:
    return f'"{k}"="{v}"'


def _re(k: str, pattern: str) -> str:
    return f'"{k}"~"^({pattern})$"'


CATEGORIES: list[Category] = [
    Category("restaurant", "Ресторани", "food", (_t("amenity", "restaurant"),), "ресторан", "menu", "reservation", ("restaurant",)),
    Category("cafe", "Кафе та кав'ярні", "food", (_t("amenity", "cafe"), _t("shop", "coffee")), "кав'ярня", "menu", "none", ("cafe", "coffee_shop")),
    Category("bar", "Бари та паби", "food", (_re("amenity", "bar|pub|biergarten"),), "бар", "menu", "reservation", ("bar", "pub")),
    Category("fast_food", "Фастфуд і доставка їжі", "food", (_re("amenity", "fast_food|food_court|ice_cream"),), "фастфуд", "menu", "none", ("fast_food_restaurant",)),
    Category("bakery", "Пекарні та кондитерські", "food", (_re("shop", "bakery|pastry|confectionery"),), "пекарня", "menu", "none", ("bakery",)),
    Category("beauty", "Салони краси", "beauty", (_re("shop", "beauty|cosmetics|massage"), _t("amenity", "spa")), "салон краси", "services", "booking", ("beauty_salon", "spa")),
    Category("hairdresser", "Перукарні та барбершопи", "beauty", (_t("shop", "hairdresser"),), "перукарня", "services", "booking", ("hair_salon", "barber_shop")),
    Category("nails", "Манікюр і тату", "beauty", (_re("shop", "nails|tattoo"),), "манікюр", "services", "booking", ("nail_salon",)),
    Category("car_repair", "Автосервіси (СТО)", "auto", (_t("shop", "car_repair"), _t("craft", "car_repair")), "СТО автосервіс", "services", "booking", ("car_repair",)),
    Category("car_wash", "Автомийки", "auto", (_t("amenity", "car_wash"),), "автомийка", "services", "booking", ("car_wash",)),
    Category("tyres", "Шиномонтажі", "auto", (_t("shop", "tyres"),), "шиномонтаж", "services", "booking", ()),
    Category("car_parts", "Автозапчастини", "auto", (_t("shop", "car_parts"),), "автозапчастини", "catalog", "none", ("auto_parts_store",)),
    Category("hotel", "Готелі та мотелі", "hotel", (_re("tourism", "hotel|motel"),), "готель", "services", "reservation", ("hotel", "motel")),
    Category("hostel", "Хостели та гостьові будинки", "hotel", (_re("tourism", "hostel|guest_house|chalet"),), "хостел", "services", "reservation", ("hostel", "guest_house")),
    Category("apartment", "Апартаменти", "hotel", (_t("tourism", "apartment"),), "апартаменти подобово", "services", "reservation", ()),
    Category("shop", "Магазини та торгові точки", "shop",
             (_re("shop", "clothes|shoes|florist|gift|jewelry|furniture|hardware|doityourself|electronics|mobile_phone|books|toys|pet|sports|bicycle|optician|houseware|interior_decoration|cosmetics|perfumery|bag|boutique|fabric|garden_centre|kitchen|lighting|second_hand|variety_store|chemist|deli|butcher|greengrocer|wine|alcohol|beverages|tobacco|e-cigarette|convenience|farm|frame|art|craft|music|photo|stationery|computer|appliance|curtain|bed|carpet|tiles|paint|flooring|bathroom_furnishing|baby_goods|fishing|outdoor"),),
             "магазин", "catalog", "none", ("store",)),
    Category("construction", "Будівельні та ремонтні компанії", "construction",
             (_re("craft", "builder|carpenter|electrician|plumber|roofer|tiler|painter|plasterer|glaziery|hvac|insulation|window_construction|stonemason|floorer|metal_construction|joiner|parquet_layer|scaffolder"),
              _re("office", "construction_company|architect"), _t("shop", "trade")),
             "будівельна компанія ремонт", "services", "none", ("general_contractor", "electrician", "plumber", "roofing_contractor")),
    Category("dentist", "Стоматології", "medical", (_t("amenity", "dentist"), _t("healthcare", "dentist")), "стоматологія", "services", "booking", ("dentist", "dental_clinic")),
    Category("clinic", "Приватні клініки та лікарі", "medical", (_re("amenity", "clinic|doctors"), _re("healthcare", "clinic|doctor|physiotherapist|psychotherapist|laboratory")), "приватна клініка", "services", "booking", ("doctor", "medical_clinic")),
    Category("veterinary", "Ветклініки", "medical", (_t("amenity", "veterinary"),), "ветеринарна клініка", "services", "booking", ("veterinary_care",)),
    Category("fitness", "Фітнес і спорт", "services", (_re("leisure", "fitness_centre|sports_centre|dance"), _t("amenity", "dojo")), "фітнес клуб", "services", "booking", ("gym",)),
    Category("services", "Інші локальні послуги", "services",
             (_re("shop", "dry_cleaning|laundry|tailor|copyshop|travel_agency|funeral_directors|locksmith|repair|shoe_repair|watches|pawnbroker|rental|photo_studio"),
              _re("craft", "photographer|tailor|shoemaker|key_cutter|upholsterer|sewing"),
              _re("amenity", "driving_school|language_school|music_school|childcare|kindergarten")),
             "послуги", "services", "booking", ("laundry", "travel_agency")),
]

_NOUNS = {'restaurant': 'Ресторан', 'cafe': "Кав'ярня", 'bar': 'Бар', 'fast_food': 'Заклад', 'bakery': 'Пекарня', 'beauty': 'Салон краси', 'hairdresser': 'Перукарня', 'nails': 'Студія', 'car_repair': 'Автосервіс', 'car_wash': 'Автомийка', 'tyres': 'Шиномонтаж', 'car_parts': 'Магазин автозапчастин', 'hotel': 'Готель', 'hostel': 'Хостел', 'apartment': 'Апартаменти', 'shop': 'Магазин', 'construction': 'Компанія', 'dentist': 'Стоматологія', 'clinic': 'Клініка', 'veterinary': 'Ветклініка', 'fitness': 'Клуб', 'services': 'Бізнес'}
CATEGORIES = [Category(**{**c.__dict__, "noun": _NOUNS.get(c.key, "Бізнес")}) for c in CATEGORIES]
CATEGORY_MAP = {c.key: c for c in CATEGORIES}

GROUP_LABELS = {
    "food": "Заклади харчування",
    "beauty": "Краса",
    "auto": "Авто",
    "hotel": "Проживання",
    "shop": "Торгівля",
    "construction": "Будівництво та ремонт",
    "medical": "Медицина",
    "services": "Інші послуги",
}


def get_category(key: str | None) -> Category | None:
    return CATEGORY_MAP.get(key or "")


def category_label(key: str | None) -> str:
    c = get_category(key)
    return c.label if c else "Інше"


def classify_osm_tags(tags: dict) -> str:
    """Визначає нашу категорію за тегами OSM."""
    import re

    for cat in CATEGORIES:
        for flt in cat.osm:
            m = re.match(r'"([^"]+)"(=|~)"(.+)"$', flt)
            if not m:
                continue
            k, op, v = m.groups()
            val = tags.get(k)
            if val is None:
                continue
            if op == "=" and val == v:
                return cat.key
            if op == "~" and re.match(v, val):
                return cat.key
    return "other"
