from django.test import SimpleTestCase

from core.normalization import normalize_merchant


class MerchantNormalizationTests(SimpleTestCase):
    def test_normalize_merchant_returns_empty_string_for_blank_input(self):
        self.assertEqual(normalize_merchant(""), "")
        self.assertEqual(normalize_merchant("   "), "")

    def test_normalize_merchant_maps_tesco_variants(self):
        self.assertEqual(
            normalize_merchant("TESCO STORE 5122 5122TE LONDON"),
            "Tesco",
        )
        self.assertEqual(
            normalize_merchant("Tesco PFS 1234 Reading"),
            "Tesco",
        )

    def test_normalize_merchant_maps_amazon_variants(self):
        self.assertEqual(
            normalize_merchant("AMZNMKTPLACE PMTS"),
            "Amazon",
        )
        self.assertEqual(
            normalize_merchant("AMAZON EU SARL"),
            "Amazon",
        )

    def test_normalize_merchant_maps_other_known_merchants(self):
        self.assertEqual(normalize_merchant("UBER TRIP"), "Uber")
        self.assertEqual(normalize_merchant("TRAINLINE *BOOKING"), "Trainline")
        self.assertEqual(normalize_merchant("PRET A MANGER 123"), "Pret")

    def test_normalize_merchant_falls_back_to_cleaned_title_case(self):
        self.assertEqual(
            normalize_merchant("local corner shop 123"),
            "Local Corner Shop 123",
        )
        self.assertEqual(
            normalize_merchant("  random   merchant name "),
            "Random Merchant Name",
        )