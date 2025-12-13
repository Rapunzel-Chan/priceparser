import re

import pandas as pd


class ProductParser:
    def __init__(self, file_path):
        # header=None чтобы читать без заголовков, мы знаем, что первые 4 строки - шапка
        self.df = pd.read_excel(file_path, header=None, skiprows=4)
        self.result = []

    def parse(self):
        category = None

        for idx, row in self.df.iterrows():
            first_cell = str(row[0]).strip() if pd.notna(row[0]) else ""

            # Если первая колонка — категория (например "01. Сухие смеси")
            if re.match(r"^\d{2}\.\s", first_cell):
                # Отрезаем номер и точку, оставляем название категории
                category = re.sub(r"^\d{2}\.\s*", "", first_cell)
                continue

            # Если пятой колонки нет или там пусто — значит не товар, пропускаем
            if pd.isna(row[4]):
                continue

            # Название товара и единица измерения
            name = str(row[4]).strip()
            unit = str(row[5]).strip() if pd.notna(row[5]) else None

            self.result.append(
                {
                    "category": category,
                    "name": name,
                    "unit": unit,
                    "price": None,  # Пока цена не берём
                }
            )

        return pd.DataFrame(self.result)
