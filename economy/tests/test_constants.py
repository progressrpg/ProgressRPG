from django.test import SimpleTestCase

from economy.constants import format_quantity, format_rate


class FormatQuantityTest(SimpleTestCase):
    def test_bread_displays_as_loaves(self):
        self.assertEqual(format_quantity("bread", 12000), "12.0 loaves")
        self.assertEqual(format_quantity("bread", 1000), "1.0 loaf")
        self.assertEqual(format_quantity("bread", 500), "0.5 loaves")

    def test_flour_displays_as_whole_sacks_rounded_up(self):
        self.assertEqual(format_quantity("flour", 1000), "1 sack")
        self.assertEqual(format_quantity("flour", 20000), "1 sack")
        self.assertEqual(format_quantity("flour", 21000), "2 sacks")
        self.assertEqual(format_quantity("flour", 38000), "2 sacks")
        self.assertEqual(format_quantity("flour", 41000), "3 sacks")
        self.assertEqual(format_quantity("flour", 0), "0 sacks")

    def test_wheat_and_unlisted_goods_use_plain_kg(self):
        self.assertEqual(format_quantity("wheat", 5000), "5.0kg")
        self.assertEqual(format_quantity("some_future_good", 2500), "2.5kg")

    def test_signed_deltas_always_use_plain_weight_regardless_of_good_type(self):
        self.assertEqual(format_quantity("flour", -500, signed=True), "-0.5kg")
        self.assertEqual(format_quantity("bread", 2000, signed=True), "+2.0kg")

    def test_wheat_over_threshold_displays_as_tonnes(self):
        # Exactly at the threshold still switches - TONNE_DISPLAY_THRESHOLD_KG
        # is inclusive.
        self.assertEqual(format_quantity("wheat", 1_000_000), "1.0t")
        self.assertEqual(format_quantity("wheat", 2_500_000), "2.5t")

    def test_wheat_under_threshold_stays_in_kg(self):
        self.assertEqual(format_quantity("wheat", 999_000), "999.0kg")

    def test_wheat_signed_deltas_never_switch_to_tonnes(self):
        self.assertEqual(format_quantity("wheat", 2_500_000, signed=True), "+2,500.0kg")

    def test_bread_never_switches_to_tonnes_regardless_of_size(self):
        self.assertEqual(format_quantity("bread", 5_000_000), "5,000.0 loaves")


class FormatRateTest(SimpleTestCase):
    """
    format_rate always uses the plain weight/volume figure, even for goods
    with a GOOD_TYPE_FORMATTER meant for stored quantities (bread as
    loaves, flour as whole sacks) - unlike format_quantity, which switches
    to those for unsigned values. See economy_status's population capacity
    section, where demand/capacity/surplus are all per-day rates, not
    stock levels.
    """

    def test_bread_and_flour_use_plain_kg_not_loaves_or_sacks(self):
        self.assertEqual(format_rate("bread", 12000), "12.0kg")
        self.assertEqual(format_rate("flour", 21000), "21.0kg")

    def test_wheat_and_unlisted_goods_use_plain_kg(self):
        self.assertEqual(format_rate("wheat", 5000), "5.0kg")
        self.assertEqual(format_rate("some_future_good", 2500), "2.5kg")

    def test_signed_surplus_shows_sign(self):
        self.assertEqual(format_rate("flour", -12500, signed=True), "-12.5kg")
        self.assertEqual(format_rate("bread", 5000, signed=True), "+5.0kg")

    def test_flour_rate_over_threshold_displays_as_tonnes(self):
        self.assertEqual(format_rate("flour", 1_500_000), "1.5t")

    def test_bread_rate_never_switches_to_tonnes_regardless_of_size(self):
        self.assertEqual(format_rate("bread", 5_000_000), "5,000.0kg")
