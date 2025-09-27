import re
from decimal import Decimal, InvalidOperation
from statistics import median  # Добавлен импорт median
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
    # Исправленный паттерн:
    # 1. Числа с разделителями тысяч (1 234, 1 234.56)
    # 2. Числа длиной >=4 без разделителей (1000, 12345)
    # 3. Короткие числа с дробной частью (123.45)
    pattern = r'(\d{1,3}(?:[ \xa0]\d{3})+(?:[.,]\d+)?|\d{4,}(?:[.,]\d+)?|\d{1,3}(?:[.,]\d+)?)'
    m = re.search(pattern, text)
    if not m:
        cleaned = re.sub(r'[^0-9.,]', '', text).replace(',', '.')
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

    lower = Q1 - Decimal("0.5") * IQR
    upper = Q3 + Decimal("0.5") * IQR

    filtered = [n for n in unique_nums if lower <= n <= upper]

    if len(filtered) < 2:
        if filtered:
            med = median(filtered)
        else:
            med = median(unique_nums)
        filtered.extend([
            x for x in unique_nums if abs(x - med) <= 2 * IQR
        ])

    if not filtered:
        return None

    return (sum(filtered) / Decimal(len(filtered))).quantize(Decimal("0.01"))


def extract_unit_and_pack(name: str) -> Tuple[Optional[str], Decimal]:
    """Извлекает фасовку из названия."""
    if not name:
        return None, Decimal(1)
    name_l = name.lower()
    match = re.search(
        r'(\d+[.,]?\d*)\s*(кг|кг\.|г|г\.|шт|шт\.|л|л\.|м2|м²|м3|м³|м|упак|упак\.)',
        name_l
    )
    if match:
        pack_size = Decimal(match.group(1).replace(',', '.'))
        unit = match.group(2).replace('.', '')
        if unit in ('упак',):
            unit = 'уп.'
        return unit, pack_size
    return None, Decimal(1)


def clean_product_name(name: str) -> str:
    """
    Убирает известные бренды и торговые марки.
    """
    if not name:
        return ""

    brands = [
        "церезит", "ce", "vetonit", "lr",
        "megabrand", "xyz", "ultrafix", "ветонит"
    ]
    pattern = r'\b(?:' + '|'.join(brands) + r')\b\s*'
    cleaned = re.sub(pattern, '', name, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', cleaned).strip()

# def normalize_price_str(s: str) -> Optional[Decimal]:
#     """
#     Надёжно извлекает первое числовое значение из строки цены и возвращает Decimal.
#     Поддерживает форматы: "1 234,56", "1234.56", "от 1 234", "1 234 — 1 500", "1\u00A0234"
#     Возвращает None, если числа нет / невозможно распарсить.
#     """
#     if s is None:
#         return None
#     if isinstance(s, (int, float, Decimal)):
#         try:
#             return Decimal(str(s))
#         except InvalidOperation:
#             return None
#
#     text = str(s)
#
#     # Попробуем найти первое подходящее число (включая тысячные разделители)
#     pattern = r'(\d{1,3}(?:[ \xa0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)'
#     m = re.search(pattern, text)
#     if not m:
#         # fallback: удалить все не-цифры и точки/запятые
#         cleaned = re.sub(r'[^0-9.,]', '', text)
#         cleaned = cleaned.replace(',', '.')
#         if not cleaned:
#             return None
#         try:
#             return Decimal(cleaned)
#         except InvalidOperation:
#             return None
#
#     num = m.group(1).replace('\xa0', '').replace(' ', '').replace(',', '.')
#     try:
#         return Decimal(num)
#     except InvalidOperation:
#         return None
#
#
# from decimal import Decimal
# from typing import Iterable, Optional
#
# def filtered_unique_mean(prices: Iterable, trim_pct: float = 0.30) -> Optional[Decimal]:
#     """
#     Считает среднее значение цен, удаляя выбросы ±trim_pct от среднего всех цен.
#     Работает со строками, числами и Decimal.
#     """
#     # Преобразуем все цены в Decimal, пропуская None
#     nums = []
#     for p in prices:
#         try:
#             if p is None:
#                 continue
#             if isinstance(p, Decimal):
#                 nums.append(p)
#             else:
#                 nums.append(Decimal(str(p).replace(',', '.')))
#         except Exception:
#             continue
#
#     if not nums:
#         return None
#
#     # Среднее всех значений
#     mean_all = sum(nums) / Decimal(len(nums))
#
#     lower = mean_all * (Decimal(1) - Decimal(str(trim_pct)))
#     upper = mean_all * (Decimal(1) + Decimal(str(trim_pct)))
#
#     # Фильтруем выбросы ±trim_pct от среднего
#     filtered = [n for n in nums if lower <= n <= upper]
#
#     if not filtered:
#         return None
#
#     avg = sum(filtered) / Decimal(len(filtered))
#     return avg.quantize(Decimal("0.01"))
#
# def extract_unit_and_pack(name: str) -> Tuple[Optional[str], Decimal]:
#     """
#     По названию пытается извлечь фасовку: '10 кг', '5 шт', '0.5 л' и т.д.
#     Возвращает (unit, pack_size). Если не найдено — (None, Decimal(1))
#     """
#     if not name:
#         return None, Decimal(1)
#     name_l = name.lower()
#     # расширенный набор единиц
#     match = re.search(r'(\d+[.,]?\d*)\s*(кг|кг\.|г|г\.|шт|шт\.|л|л\.|м2|м²|м3|м³|м|упак|упак\.)', name_l)
#     if match:
#         pack_size = Decimal(match.group(1).replace(',', '.'))
#         unit = match.group(2).replace('.', '')
#         # нормализуем
#         if unit in ('упак',):
#             unit = 'уп.'
#         return unit, pack_size
#     return None, Decimal(1)
#
#
# def clean_product_name(name: str) -> str:
#     brands = ["церезит", "ce", "vetonit", "lr"]
#     words = name.split()
#     cleaned = [w for w in words if w.lower() not in brands]
#     return " ".join(cleaned)

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
