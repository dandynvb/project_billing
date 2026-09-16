"""Checks that progress receipts are not subtracted from later invoices twice."""
import sys
import types
import unittest
from unittest.mock import patch

from project_billing.calculations import validate_terms

# Test the two pure print rules without installing Frappe locally.
with patch.dict(sys.modules, {"frappe": types.ModuleType("frappe"), "frappe.utils": types.SimpleNamespace(now_datetime=lambda: None)}):
    from project_billing.printing import balances, installment_kind


class PrintRulesTest(unittest.TestCase):
    def setUp(self):
        self.terms = [dict(term_code=c, invoice_portion=p) for c, p in [("A", 50), ("B", 30), ("C", 20)]]

    def test_existing_three_terms_use_position_not_label(self):
        self.assertEqual([installment_kind(self.terms, c) for c in ["A", "B", "C"]], ["DP", "Progress", "Pelunasan"])

    def test_explicit_type_and_single_term(self):
        self.terms[0]["term_type"] = "Progress"
        self.assertEqual(installment_kind(self.terms, "A"), "Progress")
        self.assertEqual(installment_kind([dict(term_code="ONLY")], "ONLY"), "Pelunasan")
        with self.assertRaises(ValueError):
            installment_kind(self.terms, "MISSING")

    def test_progress_does_not_deduct_dp_twice(self):
        value = balances(10000000, 5000000, 3000000, 3000000, 0)
        self.assertEqual(value["due"], 3000000)
        self.assertEqual(value["received_elsewhere"], 5000000)

    def test_partial_progress_payment(self):
        value = balances(10000000, 6000000, 3000000, 2000000, 1000000)
        self.assertEqual(value["due"], 2000000)
        self.assertEqual(value["received_elsewhere"], 5000000)

    def test_unpaid_earlier_term_is_not_rebilled_on_final(self):
        value = balances(10000000, 5000000, 2000000, 2000000, 0)
        self.assertEqual(value["contract_remaining"], 5000000)
        self.assertEqual(value["due"], 2000000)

    def test_paid_final_and_adjustments(self):
        self.assertEqual(balances(10000000, 10000000, 2000000, 0, 2000000)["due"], 0)
        self.assertEqual(balances(10000000, 9000000, 2000000, 0, 1000000)["contract_remaining"], 1000000)

    def test_valid_type_required(self):
        self.terms[0]["term_type"] = "Unknown"
        with self.assertRaises(ValueError):
            validate_terms(self.terms)


if __name__ == "__main__":
    unittest.main()
