import re
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional, Tuple

def normalize_price_str(s: str) -> Optional[Decimal]:
    if s is None:
        return None
    if isinstance(s, (int, float, Decimal)):
        try:
            return Decimal(str(s))
        except InvalidOperation:
            return None
    s = str(s).replace('\xa0', '').replace(' ', '').replace('₽', '').replace('руб', '')
    s = s.replace(',', '.')
    s = re.sub(r'[^0-9.]', '', s)
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def filtered_unique_mean(prices: Iterable, trim_pct: float = 0.30) -> Optional[Decimal]:
    nums = [normalize_price_str(p) for p in prices]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None
    unique = sorted(list({n for n in nums}))
    if len(unique) == 1:
        return unique[0].quantize(Decimal('0.01'))
    ln = len(unique)
    median = unique[ln // 2] if ln % 2 == 1 else (unique[ln // 2 - 1] + unique[ln // 2]) / Decimal(2)
    lower, upper = median * (Decimal(1) - Decimal(str(trim_pct))), median * (Decimal(1) + Decimal(str(trim_pct)))
    filtered = [p for p in unique if lower <= p <= upper]
    if not filtered:
        return None
    avg = sum(filtered) / Decimal(len(filtered))
    return avg.quantize(Decimal('0.01'))

def extract_unit_and_pack(name: str) -> Tuple[Optional[str], Decimal]:
    match = re.search(r'(\d+[.,]?\d*)\s*(кг|шт|л|м2|м³|г)', name.lower())
    if match:
        pack_size = Decimal(match.group(1).replace(',', '.'))
        unit = match.group(2)
        return unit, pack_size
    return None, Decimal(1)

def clean_product_name(name: str) -> str:
    brands = ["церезит", "ce", "vetonit", "lr"]
    words = name.split()
    cleaned = [w for w in words if w.lower() not in brands]
    return " ".join(cleaned)
