from __future__ import annotations

import datetime
import re
import unicodedata

import dateutil

from scrapers.common.schema import FuelType, GearboxType

MAKE_ALIASES: dict[str, str] = {
    "volkswagen": "Volkswagen",
    "vw": "Volkswagen",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "bmw": "BMW",
    "peugeot": "Peugeot",
    "renault": "Renault",
    "citroen": "Citroën",
    "citroën": "Citroën",
    "toyota": "Toyota",
    "hyundai": "Hyundai",
    "kia": "Kia",
    "ford": "Ford",
    "fiat": "Fiat",
    "seat": "SEAT",
    "skoda": "Škoda",
    "škoda": "Škoda",
    "opel": "Opel",
    "audi": "Audi",
    "dacia": "Dacia",
    "nissan": "Nissan",
    "honda": "Honda",
    "suzuki": "Suzuki",
    "mitsubishi": "Mitsubishi",
    "chevrolet": "Chevrolet",
}

FUEL_MAP: dict[str, FuelType] = {
    "essence": FuelType.GASOLINE,
    "sans plomb": FuelType.GASOLINE,
    "sp95": FuelType.GASOLINE,
    "sp98": FuelType.GASOLINE,
    "diesel": FuelType.DIESEL,
    "gasoil": FuelType.DIESEL,
    "gazole": FuelType.DIESEL,
    "hybride": FuelType.HYBRID,
    "hybrid": FuelType.HYBRID,
    "électrique": FuelType.ELECTRIC,
    "electrique": FuelType.ELECTRIC,
    "electric": FuelType.ELECTRIC,
    "gpl": FuelType.GPL,
    "gaz": FuelType.GPL,
    "bi-carburant": FuelType.GPL,
    "إيسانس": FuelType.GASOLINE,
    "ديزل": FuelType.DIESEL,
    "غازوال": FuelType.DIESEL,
    "كهربائي": FuelType.ELECTRIC,
    "غاز": FuelType.GPL,
}

GEARBOX_MAP: dict[str, GearboxType] = {
    "manuelle": GearboxType.MANUAL,
    "manuel": GearboxType.MANUAL,
    "mécanique": GearboxType.MANUAL,
    "mecanique": GearboxType.MANUAL,
    "mechanique": GearboxType.MANUAL,
    "automatique": GearboxType.AUTOMATIC,
    "auto": GearboxType.AUTOMATIC,
    "automatik": GearboxType.AUTOMATIC,
    "electrique": GearboxType.ELECTRIC,
    "électrique": GearboxType.ELECTRIC,
    "électrik": GearboxType.ELECTRIC,
    "electrik": GearboxType.ELECTRIC,
}

REGION_MAP: dict[str, str] = {
    "ariana": "Ariana",
    "أريانة": "Ariana",
    "beja": "Beja",
    "باجة": "Beja",
    "ben arous": "Ben Arous",
    "بن عروس": "Ben Arous",
    "bizerte": "Bizerte",
    "بنزرت": "Bizerte",
    "gabes": "Gabes",
    "قابس": "Gabes",
    "gafsa": "Gafsa",
    "قفصة": "Gafsa",
    "jendouba": "Jendouba",
    "جندوبة": "Jendouba",
    "kairouan": "Kairouan",
    "القيروان": "Kairouan",
    "kasserine": "Kasserine",
    "القصرين": "Kasserine",
    "kebili": "Kebili",
    "قبلي": "Kebili",
    "kef": "Kef",
    "الكاف": "Kef",
    "mahdia": "Mehdia",
    "المهدية": "Mehdia",
    "manouba": "Manouba",
    "منوبة": "Manouba",
    "medenine": "Medenine",
    "مدنين": "Medenine",
    "monastir": "Monastir",
    "المنستير": "Monastir",
    "nabeul": "Nabeul",
    "نابل": "Nabeul",
    "sfax": "Sfax",
    "صفاقس": "Sfax",
    "sidi bouzid": "Sidi Bouzid",
    "سيدي بوزيد": "Sidi Bouzid",
    "siliana": "Siliana",
    "سليانة": "Siliana",
    "sousse": "Sousse",
    "سوسة": "Sousse",
    "tataouine": "Tataouine",
    "تطاوين": "Tataouine",
    "tozeur": "Tozeur",
    "توزر": "Tozeur",
    "tunis": "Tunis",
    "تونس": "Tunis",
    "zaghouan": "Zaghouan",
    "زغوان": "Zaghouan",
}


def normalize_text(text: str | None) -> str | None:
    if not text:
        return None
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_make(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = normalize_text(raw)
    if not cleaned:
        return None
    return MAKE_ALIASES.get(cleaned.lower(), cleaned.title())


def normalize_region(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = normalize_text(raw)
    if not cleaned:
        return None
    mapped = REGION_MAP.get(cleaned, REGION_MAP.get(cleaned.lower()))
    if mapped:
        return mapped
    return cleaned.title()


def normalize_fuel(raw: str | None) -> FuelType:
    if not raw:
        return FuelType.UNKNOWN
    cleaned = normalize_text(raw)
    if not cleaned:
        return FuelType.UNKNOWN
    return FUEL_MAP.get(cleaned.lower(), FuelType.UNKNOWN)


def normalize_gearbox(raw: str | None) -> GearboxType:
    if not raw:
        return GearboxType.UNKNOWN
    cleaned = normalize_text(raw)
    if not cleaned:
        return GearboxType.UNKNOWN
    return GEARBOX_MAP.get(cleaned.lower(), GearboxType.UNKNOWN)


def normalize_price(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = normalize_text(raw)
    if not cleaned:
        return None
    cleaned = re.sub(r"[^\d.,]", "", cleaned)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_mileage(raw: str | None) -> int | None:
    if not raw:
        return None
    cleaned = normalize_text(raw)
    if not cleaned:
        return None
    cleaned = re.sub(r"[^\d.,]", "", cleaned)
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) > 2:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def is_negotiable(raw: str | None) -> bool:
    if not raw:
        return False
    pattern = r"(?i)(?:l[ée]g[èe]rement\s+)?(?:n[ée]go(?:ciable)?|à débattre)"

    matches = re.findall(pattern, raw)
    return len(matches) > 0


def normalize_date(raw: str | None, format: str | None = None) -> str | None:
    if not raw:
        return None
    try:
        if format:
            dt = datetime.datetime.strptime(raw.strip(), format).replace(
                tzinfo=datetime.timezone.utc
            )
        else:
            dt = dateutil.parser.parse(raw.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone().isoformat()
    except (ValueError, TypeError):
        return None
