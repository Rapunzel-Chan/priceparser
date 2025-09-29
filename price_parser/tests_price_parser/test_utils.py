from decimal import Decimal

from django.test import TestCase

from price_parser.utils import price_utils


class PriceUtilsTests(TestCase):

    def test_normalize_price_str_valid(self):
        self.assertEqual(price_utils.normalize_price_str("123,45 ₽"), Decimal("123.45"))
        self.assertEqual(price_utils.normalize_price_str(" 99.99 руб "), Decimal("99.99"))
        self.assertEqual(price_utils.normalize_price_str("10"), Decimal("10"))
        self.assertEqual(price_utils.normalize_price_str("1 234,56"), Decimal("1234.56"))
        self.assertEqual(price_utils.normalize_price_str("1\u00a0234"), Decimal("1234"))

    def test_normalize_price_str_invalid(self):
        self.assertIsNone(price_utils.normalize_price_str("abc"))
        self.assertIsNone(price_utils.normalize_price_str(""))
        self.assertIsNone(price_utils.normalize_price_str(None))

    def test_filtered_unique_mean_basic(self):
        values = ["10", "10", "20"]
        result = price_utils.filtered_unique_mean(values)
        self.assertEqual(result, Decimal("15.00"))

    def test_filtered_unique_mean_empty(self):
        self.assertIsNone(price_utils.filtered_unique_mean([]))
        self.assertIsNone(price_utils.filtered_unique_mean([None, None]))

    def test_filtered_unique_mean_outliers(self):
        values = ["10", "10", "20", "1000"]
        result = price_utils.filtered_unique_mean(values)
        self.assertEqual(result, Decimal("15.00"))

    def test_filtered_unique_mean_only_outliers(self):
        values = ["1000", "2000", "3000"]
        result = price_utils.filtered_unique_mean(values)
        self.assertEqual(result, Decimal("2000.00"))

    def test_extract_unit_and_pack_examples(self):
        self.assertEqual(price_utils.extract_unit_and_pack("12 шт."), ("шт", Decimal("12")))
        self.assertEqual(price_utils.extract_unit_and_pack("1.5 кг"), ("кг", Decimal("1.5")))
        self.assertEqual(price_utils.extract_unit_and_pack("0.5 л"), ("л", Decimal("0.5")))
        self.assertEqual(price_utils.extract_unit_and_pack("3 упак."), ("уп.", Decimal("3")))
        self.assertEqual(price_utils.extract_unit_and_pack("текст без цифр"), (None, Decimal("1")))
        self.assertEqual(price_utils.extract_unit_and_pack(""), (None, Decimal("1")))
        self.assertEqual(price_utils.extract_unit_and_pack(None), (None, Decimal("1")))

    def test_clean_product_name_removes_brands(self):
        self.assertEqual(price_utils.clean_product_name("Церезит клей для плитки"), "клей для плитки")
        self.assertEqual(price_utils.clean_product_name("CE Ветонит LR смесь"), "смесь")
        self.assertEqual(price_utils.clean_product_name("Просто текст"), "Просто текст")

    def test_clean_product_name_removes_any_brand(self):
        self.assertEqual(price_utils.clean_product_name("MegaBrand СуперКлей Extra"), "СуперКлей Extra")
        self.assertEqual(price_utils.clean_product_name("XYZ Лакокрасочная смесь"), "Лакокрасочная смесь")
        self.assertEqual(price_utils.clean_product_name("UltraFix 2000"), "2000")
        self.assertEqual(price_utils.clean_product_name(""), "")
        self.assertEqual(price_utils.clean_product_name(None), "")
