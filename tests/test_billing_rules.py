"""Server rule tests with a minimal Frappe adapter. Not a substitute for Bench tests."""
import copy
import importlib
import sys
import types
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


class Doc(dict):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name in self:
            return self[name]
        return None

    __setattr__ = dict.__setitem__

    def set(self, key, value):
        self[key] = value

    def precision(self, field):
        return 2

    def check_permission(self, *args):
        pass


def fail(message, *args, **kwargs):
    raise ValueError(message)


def getdate(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


class BillingRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        cls.frappe = types.ModuleType('frappe')
        cls.frappe.whitelist = lambda **kwargs: lambda fn: fn
        cls.frappe.throw = fail
        cls.frappe.parse_json = json.loads
        cls.frappe.db = MagicMock()
        cls.frappe.get_cached_value = MagicMock(return_value='IDR')
        cls.utils = types.ModuleType('frappe.utils')
        cls.utils.getdate = getdate
        cls.utils.add_days = lambda value, days: getdate(value) + timedelta(days=int(days))
        cls.utils.nowdate = lambda: '2026-09-11'
        cls.utils.now_datetime = lambda: '2026-09-11 12:00:00'
        cls.modules = patch.dict(sys.modules, {'frappe': cls.frappe, 'frappe.utils': cls.utils})
        cls.modules.start()
        cls.billing = importlib.import_module('project_billing.billing')
        cls.events = importlib.import_module('project_billing.events')

    @classmethod
    def tearDownClass(cls):
        for name in ('project_billing.billing', 'project_billing.events'):
            sys.modules.pop(name, None)
        cls.modules.stop()

    def setUp(self):
        self.frappe.get_cached_value.reset_mock(side_effect=True, return_value=True)
        self.frappe.get_cached_value.return_value = 'IDR'
        self.order = Doc(name='SO1', company='C', customer='CUSTOMER', currency='IDR',
                         conversion_rate=1, docstatus=1, status='To Deliver and Bill',
                         custom_pb_enabled=1, grand_total=11100, rounded_total=0, disable_rounded_total=1)
        self.order['items'] = [Doc(name='ROW1', item_code='GOODS', item_name='Goods', qty=10, uom='Nos', rate=1000, amount=10000)]
        self.order.taxes = [Doc(charge_type='On Net Total', account_head='VAT', rate=11, tax_amount=1100)]
        self.order.custom_pb_terms = [Doc(term_code='DP', label='DP', invoice_portion=50, credit_days=7), Doc(term_code='FINAL', label='Final', invoice_portion=50, credit_days=7)]
        # dict.items shadows Document.items, so use a non-dict wrapper for documents.
        self.order = Wrap(self.order)
        self.invoice = Wrap(Doc(name='SI1', custom_pb_sales_order='SO1', custom_pb_term_code='DP',
            customer='CUSTOMER', company='C', currency='IDR', conversion_rate=1,
            posting_date='2026-09-11', due_date='2026-09-18', grand_total=5550,
            rounded_total=0, disable_rounded_total=1, payment_terms_template=None,
            items=[Wrap(Doc(item_code='BILL', qty=1, rate=5000, amount=5000, conversion_factor=1,
                            sales_order='SO1', so_detail='ROW1', uom='Nos', stock_uom='Nos'))],
            taxes=copy.deepcopy(self.order.taxes),
            payment_schedule=[Doc(invoice_portion=100, due_date='2026-09-18')]))
        self.order.items = [Wrap(row) for row in self.order.items]

    def validate(self):
        with patch.object(self.billing, 'lock_order', return_value=self.order), \
             patch.object(self.billing, 'live_invoice', return_value=None), \
             patch.object(self.billing, 'settings', return_value=Doc(billing_item='BILL')), \
             patch.object(self.frappe, 'get_cached_value', side_effect=lambda dt, *args: 'IDR' if dt == 'Company' else 'Nos'):
            self.billing.validate_installment(self.invoice)

    def test_valid_installment_with_tax_and_full_contract_reference(self):
        self.validate()
        row = self.invoice.custom_pb_contract_items[0]
        self.assertEqual(row['qty'], 10)
        self.assertEqual(row['rate'], 1000)
        self.assertEqual(self.invoice.custom_pb_target_total, 5550)

    def test_invoice_quantity_tampering(self):
        self.invoice.items[0].qty = 0.5
        with self.assertRaisesRegex(ValueError, 'one unit'):
            self.validate()

    def test_invoice_price_tampering(self):
        self.invoice.items[0].rate = 1
        with self.assertRaisesRegex(ValueError, 'amounts'):
            self.validate()

    def test_missing_contract_row(self):
        self.invoice.items = []
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.validate()

    def test_wrong_customer(self):
        self.invoice.customer = 'OTHER'
        with self.assertRaisesRegex(ValueError, 'customer'):
            self.validate()

    def test_due_date_is_from_invoice(self):
        self.invoice.due_date = '2026-09-19'
        with self.assertRaisesRegex(ValueError, 'Due date'):
            self.validate()

    def test_tax_override_rejected(self):
        self.invoice.taxes[0].rate = 12
        with self.assertRaisesRegex(ValueError, 'tax configuration'):
            self.validate()

    def test_wrong_grand_total_rejected(self):
        self.invoice.grand_total = 5600
        with self.assertRaisesRegex(ValueError, 'rounding'):
            self.validate()

    def test_return_rejected(self):
        self.invoice.is_return = 1
        with self.assertRaisesRegex(ValueError, 'Returns'):
            self.validate()

    def test_stock_update_rejected(self):
        self.invoice.update_stock = 1
        with self.assertRaisesRegex(ValueError, 'stock'):
            self.validate()

    def test_multiple_payment_terms_rejected(self):
        self.invoice.payment_schedule *= 2
        with self.assertRaisesRegex(ValueError, 'one payment schedule'):
            self.validate()

    def test_closed_order_rejected(self):
        self.order.status = 'Closed'
        with self.assertRaisesRegex(ValueError, 'closed'):
            self.validate()

    def test_multicurrency_order_rejected(self):
        self.order.currency = 'USD'
        with self.assertRaisesRegex(ValueError, 'company currency'):
            self.billing.check_supported(self.order)

    def test_duplicate_current_read_is_locked_and_parameterized(self):
        self.frappe.db.sql.return_value = [('SI-existing',)]
        self.assertEqual(self.billing.live_invoice('SO1', 'DP'), 'SI-existing')
        query, values = self.frappe.db.sql.call_args.args
        self.assertIn('for update', query)
        self.assertEqual(values, ('SO1', 'DP', ''))

    def test_order_schedule_cleared_only_for_opt_in_orders(self):
        self.order.payment_schedule = [Doc(due_date='2026-09-11')]
        self.events.prepare_order(self.order)
        self.assertEqual(self.order.payment_schedule, [])
        self.order.custom_pb_enabled = 0
        self.order.payment_schedule = [Doc(due_date='2026-09-11')]
        self.events.prepare_order(self.order)
        self.assertEqual(len(self.order.payment_schedule), 1)


class Wrap:
    def __init__(self, values):
        self.__dict__.update(values)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def __getattr__(self, name):
        return None

    def set(self, key, value):
        setattr(self, key, value)

    def precision(self, field):
        return 2

    def check_permission(self, *args):
        pass
