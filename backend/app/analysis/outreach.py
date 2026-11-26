"""Генерація готових повідомлень для першого контакту з бізнесом.

Текст складається з блоків (привітання, що ми помітили, пропозиція, користь, заклик), кожен блок має кілька
формулювань. Варіант детерміновано залежить від ID бізнесу та номера варіанту, тож різні бізнеси отримують
різні тексти, а кнопка «Інший варіант» дає нове формулювання. Згадуються лише факти, які застосунок реально
виявив; неперевірене в текст не потрапляє.
"""
from __future__ import annotations

import random
from typing import Any

from ..categories import get_category

GREET = {
    "instagram": ["Добрий день!", "Вітаю!", "Доброго дня!", "Привіт! 👋", "Добрий день 🙂", "Вітаю 👋"],
    "email": ["Добрий день!", "Доброго дня!", "Вітаю!", "Добрий день, шановна команда!"],
}

INTRO = [
    "Мене звати {sender}, {company_part}я допомагаю місцевим бізнесам з онлайн-присутністю.",
    "Я {sender}{company_part2} — робимо сайти та цифрові інструменти для локального бізнесу.",
    "Пишу вам як {sender}{company_part2}: ми займаємося сайтами, онлайн-меню та системами запису.",
    "Мене звати {sender}. {company_cap}Допомагаю закладам і сервісам отримувати більше клієнтів з інтернету.",
]
INTRO_NO_SENDER = [
    "Я займаюся сайтами та цифровими інструментами для місцевого бізнесу.",
    "Ми допомагаємо локальним бізнесам з сайтами, онлайн-меню та записом.",
    "Робимо сайти й онлайн-сервіси для закладів і місцевих компаній.",
]

LOOKED = [
    "Подивився(-лася), як в інтернеті виглядає {name}.",
    "Натрапив(-ла) на вас у пошуку — {name}.",
    "Переглянув(-ла), що про вас є в інтернеті.",
    "Подивився(-лася) інформацію про вас онлайн.",
    "Шукав(-ла) {noun_acc} поруч і знайшов(-ла) вас.",
]

# Факти: формулюються як «не знайшов(-ла)», бо це саме те, що ми перевірили
FACT = {
    "social_only": [
        "Бачу, що у вас є {social}, але власного сайту я не знайшов(-ла).",
        "Ви ведете {social} — це чудово, проте окремого сайту в мережі немає.",
        "Знайшов(-ла) ваш {social}, а от сайту, куди можна відправити клієнта, не побачив(-ла).",
    ],
    "no_website": [
        "Не знайшов(-ла) у вас власного сайту.",
        "Схоже, у вас поки немає сайту — у відкритих джерелах я його не знайшов(-ла).",
        "Власного сайту я в інтернеті не знайшов(-ла).",
    ],
    "website_unreachable": [
        "Спробував(-ла) відкрити ваш сайт, але він зараз не працює.",
        "Ваш сайт, на жаль, не відкривається — клієнти бачать помилку.",
    ],
    "no_menu": [
        "Меню онлайн знайти не вдалося, а це перше, що шукають гості перед візитом.",
        "Не побачив(-ла) онлайн-меню — людям доводиться писати чи дзвонити, щоб дізнатися ціни.",
        "Онлайн-меню з цінами я не знайшов(-ла).",
    ],
    "no_catalog": [
        "Не знайшов(-ла) онлайн-каталогу з товарами й цінами.",
        "Каталогу товарів онлайн немає, тож покупцям складно щось обрати заздалегідь.",
    ],
    "no_booking": [
        "Онлайн-запису я не знайшов(-ла) — схоже, записатися можна лише дзвінком чи в повідомленнях.",
        "Не побачив(-ла) можливості записатися онлайн, а багато клієнтів зараз саме так і роблять.",
        "Записатися до вас онлайн, без дзвінка, не вийшло.",
    ],
    "no_reservation": [
        "Не знайшов(-ла), як забронювати онлайн.",
        "Онлайн-бронювання я не побачив(-ла) — лише телефон.",
    ],
    "outdated_website": [
        "Ваш сайт виглядає застарілим: {signal}.",
        "Помітив(-ла), що сайт давно не оновлювався: {signal}.",
    ],
    "website_improvable": [
        "Сайт у вас є, і його можна підсилити: {signal}.",
        "На сайті є кілька моментів, які легко покращити: {signal}.",
    ],
}

OFFER_LEAD = [
    "Що можу запропонувати: {service}.",
    "Моя ідея для вас — {service}.",
    "Що могло б допомогти: {service}.",
    "Пропозиція проста: {service}.",
    "Що ми можемо зробити: {service}.",
]

BENEFIT = {
    "food": [
        "Гості зможуть переглянути меню ще до візиту й одразу замовити.",
        "Так більше людей, які шукають, де поїсти поруч, обиратимуть саме вас.",
        "Це економить час персоналу на відповідях про меню й ціни.",
    ],
    "beauty": [
        "Клієнти записуватимуться самі в будь-який час, навіть уночі, без дзвінків.",
        "Менше пропущених дзвінків і «вікон» у розкладі майстрів.",
        "Нові клієнти бачитимуть послуги й ціни та одразу обиратимуть час.",
    ],
    "auto": [
        "Клієнти зможуть обрати послугу й час без дзвінка, а ви бачитимете завантаження наперед.",
        "Люди, які шукають СТО поруч, одразу бачитимуть ціни й записуватимуться.",
    ],
    "hotel": [
        "Прямі бронювання без комісій агрегаторів.",
        "Гості бронюватимуть напряму, а ви економитимете на комісіях.",
    ],
    "shop": [
        "Покупці зможуть переглянути асортимент і замовити онлайн.",
        "Це ще один канал продажів, який працює цілодобово.",
    ],
    "construction": [
        "Портфоліо з фото робіт і формою заявки викликає більше довіри, ніж сторінка в соцмережі.",
        "Клієнти бачитимуть ваші роботи й залишатимуть заявки самі.",
    ],
    "medical": [
        "Пацієнти записуватимуться онлайн, а адміністратор менше часу проводитиме на телефоні.",
        "Сайт з лікарями, послугами й цінами додає довіри новим пацієнтам.",
    ],
    "services": [
        "Нові клієнти знаходитимуть вас у Google й одразу звертатимуться.",
        "Це додасть довіри й спростить звернення для нових клієнтів.",
    ],
}

CTA = {
    "instagram": [
        "Якщо цікаво — можу надіслати кілька прикладів і орієнтовну вартість. Вам зручно тут?",
        "Можу коротко показати, як це виглядатиме саме для вас. Цікаво?",
        "Надіслати приклади робіт і ціни?",
        "Якщо актуально, підкажіть, кому краще написати з цього питання 🙂",
        "Чи було б вам цікаво обговорити це за 10 хвилин?",
    ],
    "email": [
        "Якщо тема актуальна, із задоволенням надішлю приклади робіт і орієнтовний кошторис.",
        "Буду радий(-а) коротко зідзвонитися й показати, як це виглядатиме для вас.",
        "Підкажіть, будь ласка, чи цікаво вам це, і кому краще адресувати пропозицію.",
    ],
}

SIGN = ["Гарного дня!", "Дякую за увагу!", "Хорошого дня 🙂", "З повагою,", "Дякую!"]

SUBJECT = [
    "Пропозиція для {name}",
    "{name}: як отримувати більше клієнтів з інтернету",
    "Ідея для {name}",
    "Сайт і онлайн-запис для {name}",
]

NOUN_ACC = {"restaurant": "ресторан", "cafe": "кав'ярню", "bar": "бар", "fast_food": "де поїсти", "bakery": "пекарню",
            "beauty": "салон краси", "hairdresser": "перукарню", "nails": "студію манікюру", "car_repair": "СТО",
            "car_wash": "автомийку", "tyres": "шиномонтаж", "car_parts": "автозапчастини", "hotel": "готель",
            "hostel": "хостел", "apartment": "житло", "shop": "магазин", "construction": "ремонтну бригаду",
            "dentist": "стоматологію", "clinic": "клініку", "veterinary": "ветклініку", "fitness": "спортзал",
            "services": "такі послуги"}

GROUP_OF = {"food": "food", "beauty": "beauty", "auto": "auto", "hotel": "hotel", "shop": "shop",
            "construction": "construction", "medical": "medical", "services": "services"}


def _lc(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def generate(biz: Any, variant: int = 0, channel: str = "instagram", sender: dict | None = None) -> dict:
    sender = sender or {}
    rng = random.Random(f"{biz.id}:{variant}:{channel}")
    cat = get_category(biz.category)
    group = GROUP_OF.get(cat.group if cat else "services", "services")
    name = biz.name
    problems = list(biz.problems or [])
    wa = biz.website_analysis or {}

    socials = [n for n, v in (("Instagram", biz.instagram), ("Facebook", biz.facebook)) if v]
    signals = [s["text"] for s in wa.get("outdated_signals", [])] + list(wa.get("improvement_signals", []))
    signal = _lc(signals[0]).rstrip(".") if signals else "його варто оновити"

    ctx = {"name": name, "noun_acc": NOUN_ACC.get(biz.category, "такий бізнес"), "social": " та ".join(socials) or "сторінка в соцмережі",
           "signal": signal}

    def pick(options: list[str]) -> str:
        return rng.choice(options).format(**ctx)

    parts: list[str] = []
    greet = pick(GREET[channel])
    parts.append(greet)

    sname, company = (sender.get("sender_name") or "").strip(), (sender.get("company") or "").strip()
    if sname:
        tpl = rng.choice(INTRO)
        intro = tpl.format(sender=sname, company_part=f"представляю {company}, " if company else "",
                           company_part2=f" з {company}" if company else "", company_cap=f"Представляю {company}. " if company else "")
    else:
        intro = rng.choice(INTRO_NO_SENDER)
    looked = pick(LOOKED)

    # Факти (не більше двох, щоб повідомлення не було довгим)
    facts: list[str] = []
    order = ["social_only", "no_website", "website_unreachable", "outdated_website", "no_menu", "no_booking", "no_reservation", "website_improvable"]
    for code in order:
        if code not in problems:
            continue
        if code == "no_website" and "social_only" in problems:
            continue
        key = code
        if code == "no_menu" and cat and cat.offer_kind == "catalog":
            key = "no_catalog"
        facts.append(pick(FACT[key]))
        if len(facts) >= 2:
            break

    services = list(biz.recommended_services or [])
    if services:
        service = _lc(services[0])
        if len(services) > 1 and rng.random() < 0.6:
            service += ", а також " + _lc(services[1])
    else:
        service = "аудит вашої онлайн-присутності й план покращень"
    offer = rng.choice(OFFER_LEAD).format(service=service)
    benefit = rng.choice(BENEFIT[group])
    cta = rng.choice(CTA[channel])

    if channel == "instagram":
        # коротко: привітання + (інтро або «дивився») + факти + пропозиція + користь + заклик
        opener = rng.choice([intro, looked, f"{looked} {intro}"])
        body = [opener, " ".join(facts), f"{offer} {benefit}", cta]
        text = greet + "\n\n" + "\n\n".join(x for x in body if x)
        sign_line = sname and rng.random() < 0.5
        if sign_line:
            text += f"\n\n{sname}"
        subject = None
    else:
        lines = [greet, "", f"{intro} {looked}", "", " ".join(facts), "", f"{offer} {benefit}", "", cta, "", rng.choice(SIGN)]
        sig = [x for x in (sname, company, (sender.get("phone") or "").strip(), (sender.get("portfolio") or "").strip()) if x]
        lines += sig
        text = "\n".join(lines).replace("\n\n\n", "\n\n").strip()
        subject = rng.choice(SUBJECT).format(name=name)

    if channel == "instagram" and (sender.get("portfolio") or "").strip() and rng.random() < 0.5:
        text += f"\n\nПриклади робіт: {sender['portfolio'].strip()}"
    gender = sender.get("gender") or "m"
    text = apply_gender("\n".join(line.rstrip() for line in text.strip().splitlines()), gender)
    return {"text": text, "subject": subject, "variant": variant, "channel": channel}


def apply_gender(text: str, gender: str) -> str:
    """«помітив(-ла)» → «помітив» / «помітила»; «дивився(-лася)» → «дивився» / «дивилася»."""
    import re

    f = gender == "f"
    text = text.replace("знайшов(-ла)", "знайшла" if f else "знайшов")
    text = re.sub(r"(\w+)вся\(-лася\)", lambda m: m.group(1) + ("лася" if f else "вся"), text)
    text = re.sub(r"(\w+)в\(-ла\)", lambda m: m.group(1) + ("ла" if f else "в"), text)
    text = text.replace("радий(-а)", "рада" if f else "радий")
    return text
