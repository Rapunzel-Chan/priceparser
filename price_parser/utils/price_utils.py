import re
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Iterable, Optional, Tuple


def normalize_price_str(s: str) -> Optional[Decimal]:
    """Извлекает первое числовое значение из строки и возвращает Decimal."""
    if s is None:
        return None
    if isinstance(s, (int, float, Decimal)):
        try:
            return Decimal(str(s))
        except InvalidOperation:
            return None

    text = str(s)
    pattern = r"(\d{1,3}(?:[ \xa0]\d{3})+(?:[.,]\d+)?|\d{4,}(?:[.,]\d+)?|\d{1,3}(?:[.,]\d+)?)"
    m = re.search(pattern, text)
    if not m:
        cleaned = re.sub(r"[^0-9.,]", "", text).replace(",", ".")
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    num = m.group(1).replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(num)
    except InvalidOperation:
        return None


def filtered_unique_mean(prices: Iterable) -> Optional[Decimal]:
    nums = [normalize_price_str(p) for p in prices]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None

    unique_nums = sorted(set(nums))
    n = len(unique_nums)
    if n == 1:
        return unique_nums[0].quantize(Decimal("0.01"))

    def percentile(data: list[Decimal], p: float) -> Decimal:
        n_data = len(data)
        p_dec = Decimal(str(p))
        k = (Decimal(n_data - 1) * p_dec).quantize(Decimal("0.000001"))
        f = int(k)
        c = min(f + 1, n_data - 1)

        weight1 = Decimal(c) - k
        weight2 = k - Decimal(f)

        d0 = data[f] * weight1
        d1 = data[c] * weight2
        return (d0 + d1).quantize(Decimal("0.01"))

    Q1 = percentile(unique_nums, 0.25)
    Q3 = percentile(unique_nums, 0.75)
    IQR = Q3 - Q1

    lower = Q1 - Decimal("1.5") * IQR
    upper = Q3 + Decimal("1.5") * IQR

    if lower < 0:
        lower = Decimal("0")

    filtered = [n for n in unique_nums if lower <= n <= upper]

    if len(filtered) < 2:
        med = median(unique_nums)
        from statistics import stdev

        if len(unique_nums) > 1:
            std_dev = stdev(unique_nums)
            filtered = [x for x in unique_nums if abs(x - med) <= 3 * std_dev]
        else:
            filtered = unique_nums

    if not filtered:
        return None

    return (sum(filtered) / Decimal(len(filtered))).quantize(Decimal("0.01"))


def extract_unit_and_pack(name: str) -> Tuple[Optional[str], Decimal]:
    """Извлекает фасовку из названия. Если не найдено, возвращает 'шт' и 1."""
    if not name:
        return "шт", Decimal(1)

    name_l = name.lower()

    pattern = r"(?:[,]\s*|\s+)(\d+[.,]?\d*)\s*(кг|кг\.|г|г\.|шт|шт\.|л|л\.|м2|м²|м3|м³|м|упак|упак\.|пар|пары)"

    match = re.search(pattern, name_l)

    if match:
        pack_size = Decimal(match.group(1).replace(",", "."))
        unit = match.group(2).replace(".", "")

        if unit in ("упак", "упак."):
            unit = "упак"
        elif unit in ("пар", "пары"):
            unit = "пар"
        elif unit == "кг":
            unit = "кг"
        elif unit in ("шт", "шт."):
            unit = "шт"

        return unit, pack_size

    pattern2 = r"(\d+)\s*(пар|пары)\s*$"
    match2 = re.search(pattern2, name_l)
    if match2:
        pack_size = Decimal(match2.group(1))
        unit = "пар"
        return unit, pack_size

    return "шт", Decimal(1)


def clean_product_name(name: str) -> str:
    """
    Убирает известные бренды и торговые марки.
    """
    if not name:
        return ""

    brands = ["церезит", "ce", "vetonit", "lr", "megabrand", "xyz", "ultrafix", "ветонит"]
    pattern = r"\b(?:" + "|".join(brands) + r")\b\s*"
    cleaned = re.sub(pattern, "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()
