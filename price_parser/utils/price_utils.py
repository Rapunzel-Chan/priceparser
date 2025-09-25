import re
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional, Tuple

def normalize_price_str(s: str) -> Optional[Decimal]:
    """
    Надёжно извлекает первое числовое значение из строки цены и возвращает Decimal.
    Поддерживает форматы: "1 234,56", "1234.56", "от 1 234", "1 234 — 1 500", "1\u00A0234"
    Возвращает None, если числа нет / невозможно распарсить.
    """
    if s is None:
        return None
    if isinstance(s, (int, float, Decimal)):
        try:
            return Decimal(str(s))
        except InvalidOperation:
            return None

    text = str(s)

    # Попробуем найти первое подходящее число (включая тысячные разделители)
    pattern = r'(\d{1,3}(?:[ \xa0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)'
    m = re.search(pattern, text)
    if not m:
        # fallback: удалить все не-цифры и точки/запятые
        cleaned = re.sub(r'[^0-9.,]', '', text)
        cleaned = cleaned.replace(',', '.')
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    num = m.group(1).replace('\xa0', '').replace(' ', '').replace(',', '.')
    try:
        return Decimal(num)
    except InvalidOperation:
        return None


def filtered_unique_mean(prices: Iterable, trim_pct: float = 0.30) -> Optional[Decimal]:
    nums = [normalize_price_str(p) for p in prices]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None
    # set of decimals
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
    """
    По названию пытается извлечь фасовку: '10 кг', '5 шт', '0.5 л' и т.д.
    Возвращает (unit, pack_size). Если не найдено — (None, Decimal(1))
    """
    if not name:
        return None, Decimal(1)
    name_l = name.lower()
    # расширенный набор единиц
    match = re.search(r'(\d+[.,]?\d*)\s*(кг|кг\.|г|г\.|шт|шт\.|л|л\.|м2|м²|м3|м³|м|упак|упак\.)', name_l)
    if match:
        pack_size = Decimal(match.group(1).replace(',', '.'))
        unit = match.group(2).replace('.', '')
        # нормализуем
        if unit in ('упак',):
            unit = 'уп.'
        return unit, pack_size
    return None, Decimal(1)


def clean_product_name(name: str) -> str:
    brands = ["церезит", "ce", "vetonit", "lr"]
    words = name.split()
    cleaned = [w for w in words if w.lower() not in brands]
    return " ".join(cleaned)

# import re
# from decimal import Decimal, InvalidOperation
# from typing import Iterable, Optional, Tuple
#
# def normalize_price_str(s: str) -> Optional[Decimal]:
#     if s is None:
#         return None
#     if isinstance(s, (int, float, Decimal)):
#         try:
#             return Decimal(str(s))
#         except InvalidOperation:
#             return None
#     s = str(s).replace('\xa0', '').replace(' ', '').replace('₽', '').replace('руб', '')
#     s = s.replace(',', '.')
#     s = re.sub(r'[^0-9.]', '', s)
#     if not s:
#         return None
#     try:
#         return Decimal(s)
#     except InvalidOperation:
#         return None
#
# def filtered_unique_mean(prices: Iterable, trim_pct: float = 0.30) -> Optional[Decimal]:
#     nums = [normalize_price_str(p) for p in prices]
#     nums = [n for n in nums if n is not None]
#     if not nums:
#         return None
#     unique = sorted(list({n for n in nums}))
#     if len(unique) == 1:
#         return unique[0].quantize(Decimal('0.01'))
#     ln = len(unique)
#     median = unique[ln // 2] if ln % 2 == 1 else (unique[ln // 2 - 1] + unique[ln // 2]) / Decimal(2)
#     lower, upper = median * (Decimal(1) - Decimal(str(trim_pct))), median * (Decimal(1) + Decimal(str(trim_pct)))
#     filtered = [p for p in unique if lower <= p <= upper]
#     if not filtered:
#         return None
#     avg = sum(filtered) / Decimal(len(filtered))
#     return avg.quantize(Decimal('0.01'))
#
# def extract_unit_and_pack(name: str) -> Tuple[Optional[str], Decimal]:
#     match = re.search(r'(\d+[.,]?\d*)\s*(кг|шт|л|м2|м³|г)', name.lower())
#     if match:
#         pack_size = Decimal(match.group(1).replace(',', '.'))
#         unit = match.group(2)
#         return unit, pack_size
#     return None, Decimal(1)
#
# def clean_product_name(name: str) -> str:
#     brands = ["церезит", "ce", "vetonit", "lr"]
#     words = name.split()
#     cleaned = [w for w in words if w.lower() not in brands]
#     return " ".join(cleaned)
