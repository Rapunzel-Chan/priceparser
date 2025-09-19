# catalog/utils/price_utils.py

import re
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional

def normalize_price_str(s: str) -> Optional[Decimal]:
    if s is None:
        return None
    if isinstance(s, (int, float, Decimal)):
        try:
            return Decimal(str(s))
        except InvalidOperation:
            return None
    s = str(s)
    s = s.replace('\xa0', '').replace(' ', '').replace('₽', '').replace('руб', '')
    s = s.replace(',', '.')
    s = re.sub(r'[^0-9.]', '', s)
    if s == '':
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def filtered_unique_mean(prices: Iterable, trim_pct: float = 0.30) -> Optional[Decimal]:
    """
    - Преобразует вход в Decimal
    - Убирает None
    - Берёт уникальные значения
    - Отсечёт выбросы по % от медианы (trim_pct)
    - Вернёт среднее (Decimal, 2 знака) или None
    """
    nums = [normalize_price_str(p) for p in prices]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None

    # Уникальные цены
    unique = sorted(list({n for n in nums}))
    if len(unique) == 0:
        return None
    if len(unique) == 1:
        return unique[0].quantize(Decimal('0.01'))

    # медиана
    ln = len(unique)
    if ln % 2 == 1:
        median = unique[ln // 2]
    else:
        median = (unique[ln//2 - 1] + unique[ln//2]) / Decimal(2)

    lower = median * (Decimal(1) - Decimal(str(trim_pct)))
    upper = median * (Decimal(1) + Decimal(str(trim_pct)))

    filtered = [p for p in unique if lower <= p <= upper]
    if not filtered:
        return None

    avg = sum(filtered) / Decimal(len(filtered))
    return avg.quantize(Decimal('0.01'))
