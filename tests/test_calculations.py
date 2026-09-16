import unittest
from decimal import Decimal

from project_billing.calculations import allocate, decimal, money, summarize, validate_terms


class CalculationTests(unittest.TestCase):
    def test_two_installments(self):
        self.assertEqual(allocate(10000000, [50, 50]), [Decimal('5000000.00')] * 2)

    def test_three_installments(self):
        self.assertEqual(allocate(11100000, [50, 30, 20]), list(map(Decimal, ['5550000', '3330000', '2220000'])))

    def test_remainders_conserve_total(self):
        for total in ['0.01', '100.01', '999999.99', '123.45']:
            for portions in ([50, 50], [33.33, 33.33, 33.34], [10, 20, 30, 40]):
                self.assertEqual(sum(allocate(total, portions)), Decimal(total))

    def test_whole_currency_precision(self):
        self.assertEqual(allocate(101, [50, 50], 0), [Decimal(51), Decimal(50)])

    def test_out_of_order_is_stable(self):
        plan = allocate('100.01', [50, 30, 20])
        self.assertEqual([plan[i] for i in [2, 0, 1]], [Decimal('20.00'), Decimal('50.01'), Decimal('30.00')])

    def test_no_dates_required(self):
        validate_terms([dict(term_code='DP', invoice_portion=50), dict(term_code='FINAL', invoice_portion=50, credit_days=14)])

    def test_invalid_terms(self):
        cases = [[], [dict(term_code='A', invoice_portion=99)],
                 [dict(term_code='A', invoice_portion=50), dict(term_code='A', invoice_portion=50)],
                 [dict(term_code='A', invoice_portion=100, credit_days=-1)],
                 [dict(term_code='A', invoice_portion=100, credit_days=1.5)],
                 [dict(term_code='', invoice_portion=100)],
                 [dict(term_code='A', invoice_portion=101), dict(term_code='B', invoice_portion=-1)]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_terms(rows)

    def test_invalid_allocations(self):
        for portions in ([], [50], [101, -1], [0, 100]):
            with self.assertRaises(ValueError):
                allocate(100, portions)

    def test_nonfinite_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.assertRaises(ValueError):
                decimal(value)

    def test_half_up(self):
        self.assertEqual(money('1.005'), Decimal('1.01'))

    def test_dp_paid_is_not_order_paid(self):
        values = summarize(10000000, 5000000, 0, 5000000)
        self.assertEqual(values['custom_pb_payment_status'], 'Partly Paid')
        self.assertEqual(values['custom_pb_unbilled_total'], 5000000)
        self.assertEqual(values['custom_pb_outstanding_total'], 0)

    def test_full_billing_partial_payment(self):
        values = summarize(10000000, 10000000, 5000000, 5000000)
        self.assertEqual(values['custom_pb_payment_status'], 'Partly Paid')
        self.assertEqual(values['custom_pb_outstanding_total'], 5000000)

    def test_fully_paid(self):
        self.assertEqual(summarize(100, 100, 0, 100)['custom_pb_payment_status'], 'Paid')

    def test_advance_not_yet_invoiced(self):
        values = summarize(100, 0, 0, 50)
        self.assertEqual(values['custom_pb_payment_status'], 'Partly Paid')
        self.assertEqual(values['custom_pb_unbilled_total'], 100)

    def test_write_off_not_cash(self):
        self.assertEqual(summarize(100, 100, 0, 90)['custom_pb_payment_status'], 'Settled with Adjustments')

    def test_cancelled_invoice_removed_from_aggregates(self):
        values = summarize(100, 0, 0, 0)
        self.assertEqual(values['custom_pb_payment_status'], 'Unpaid')
        self.assertEqual(values['custom_pb_unbilled_total'], 100)

    def test_returns_are_not_silently_interpreted(self):
        with self.assertRaises(ValueError):
            summarize(100, -10, 0, 0)
