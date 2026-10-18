"""Checks the cleaning rules on a few handcrafted rows.

Run with plain Python from the repository root:  python tests/test_clean.py
Exits with a non-zero code if any check fails.
"""
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import clean  # noqa: E402

EUR = "\u20ac"

ROWS = [
    ["1", "Castle and Byrne", "12.03.2024", "1.299,00 " + EUR, "Paid", " INFO@Client1.COM "],
    ["2", "castle & byrne", "03/12/2024", EUR + "1,299.00", "OPEN", "info@client2.com"],
    ["3", "Northwind  Trading ", "April 1, 2024", "845,5", "open", "contact@client3.com"],
    ["", "", "", "", "", ""],
    ["   ", " ", "", "", "", ""],
    ["4", "Hensley it", "1 April 2024", "EUR 2.100,00", "PAID", "a@b.com"],
    ["4", "Hensley it", "1 April 2024", "EUR 2.100,00", "PAID", "a@b.com"],   # exact duplicate
    ["5", "Pike & Sons", "31.02.2024", "1.299", "open", "x@y.com"],            # unreadable values
]


class DateRules(unittest.TestCase):
    def test_formats_become_iso(self):
        self.assertEqual(clean.norm_date("12.03.2024"), "2024-03-12")       # DD.MM.YYYY
        self.assertEqual(clean.norm_date("03/12/2024"), "2024-03-12")       # MM/DD/YYYY (agreed)
        self.assertEqual(clean.norm_date("1 April 2024"), "2024-04-01")
        self.assertEqual(clean.norm_date("April 1, 2024"), "2024-04-01")
        self.assertEqual(clean.norm_date("2024-04-01"), "2024-04-01")

    def test_impossible_or_unknown_dates_are_not_guessed(self):
        self.assertIsNone(clean.norm_date("31.02.2024"))
        self.assertIsNone(clean.norm_date("next Tuesday"))


class AmountRules(unittest.TestCase):
    def test_formats_become_numbers(self):
        self.assertEqual(clean.norm_amount("1.299,00 " + EUR), "1299.00")
        self.assertEqual(clean.norm_amount(EUR + "1,299.00"), "1299.00")
        self.assertEqual(clean.norm_amount("EUR 1.299,00"), "1299.00")
        self.assertEqual(clean.norm_amount("1299,00"), "1299.00")
        self.assertEqual(clean.norm_amount("845.5"), "845.50")
        self.assertEqual(clean.norm_amount("2100"), "2100.00")

    def test_ambiguous_amounts_are_not_guessed(self):
        self.assertIsNone(clean.norm_amount("1.299"))
        self.assertIsNone(clean.norm_amount("on request"))


class CompanyRules(unittest.TestCase):
    def test_spellings_unified(self):
        self.assertEqual(clean.norm_company("Castle and Byrne"), "Castle & Byrne")
        self.assertEqual(clean.norm_company("castle & byrne"), "Castle & Byrne")
        self.assertEqual(clean.norm_company("HARBOUR LOGISTICS"), "Harbour Logistics")
        self.assertEqual(clean.norm_company("Northwind  Trading "), "Northwind Trading")
        self.assertEqual(clean.norm_company("Hensley it"), "Hensley IT")
        self.assertEqual(clean.norm_company("avoncroft ltd"), "Avoncroft Ltd")


class WholeRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = clean.clean_rows([list(r) for r in ROWS])
        cls.by_id = {r[0]: r for r in cls.res["rows"]}

    def test_row_counts(self):
        self.assertEqual(self.res["counts"]["empty"], 2)
        self.assertEqual(self.res["counts"]["dupes"], 1)
        self.assertEqual(len(self.res["rows"]), 5)

    def test_first_row_fully_cleaned(self):
        self.assertEqual(self.by_id["1"], ["1", "Castle & Byrne", "2024-03-12", "1299.00", "paid", "info@client1.com"])

    def test_status_and_email(self):
        self.assertEqual(self.by_id["2"][4], "open")
        self.assertEqual(self.by_id["4"][4], "paid")
        self.assertEqual(self.by_id["1"][5], "info@client1.com")

    def test_unreadable_values_left_empty_and_counted(self):
        self.assertEqual(self.by_id["5"][2], "")
        self.assertEqual(self.by_id["5"][3], "")
        self.assertEqual(sorted(u[1] for u in self.res["unresolved"]), ["amount", "invoice_date"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
