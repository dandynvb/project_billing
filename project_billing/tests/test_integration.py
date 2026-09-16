"""Run on a disposable Frappe/ERPNext v15 test site with this app installed.

bench --site TEST_SITE run-tests --app project_billing --module project_billing.tests.test_integration
These tests have NOT been executed by the standalone Python test suite.
"""
import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from project_billing.billing import create_invoice
from project_billing.summary import refresh

test_dependencies = []


class TestProjectBilling(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.savepoint("project_billing_test")
        if not frappe.db.exists("Company", "PB Test Company"):
            frappe.get_doc(dict(doctype="Company", company_name="PB Test Company", abbr="PBT",
                default_currency="INR", country="United States", chart_of_accounts="Standard")).insert()
        if not frappe.db.exists("Customer", "PB Test Customer"):
            frappe.get_doc(dict(doctype="Customer", customer_name="PB Test Customer", customer_type="Company",
                customer_group=frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
                territory=frappe.db.get_value("Territory", {"is_group": 0}, "name"))).insert()
        for code in ("_Test PB Goods", "_Test PB Installment"):
            if not frappe.db.exists("Item", code):
                frappe.get_doc(dict(doctype="Item", item_code=code, item_name=code,
                    item_group="Products", stock_uom="Nos", is_stock_item=0,
                    is_sales_item=1, is_purchase_item=0)).insert()
        config = frappe.get_single("Project Billing Settings")
        config.update(dict(enabled=1, billing_item="_Test PB Installment", enforce_delivery_payment=1))
        config.save()
        self.cash = frappe.db.get_value("Account", {
            "company": "PB Test Company", "account_type": "Cash", "is_group": 0}, "name")
        self.assertTrue(self.cash, "ERPNext test company cash account fixture is required")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback(save_point="project_billing_test")
        frappe.clear_cache()

    def order(self, tax=False, inclusive=False, actual=0):
        doc = make_sales_order(company="PB Test Company", customer="PB Test Customer", warehouse="Stores - PBT",
                               item_code="_Test PB Goods", qty=10, rate=1000, do_not_save=True)
        doc.custom_pb_enabled = 1
        doc.disable_rounded_total = 1
        doc.set("custom_pb_terms", [
            dict(term_code="DP", label="Down Payment", invoice_portion=50, credit_days=7, required_before_delivery=1),
            dict(term_code="FINAL", label="Final", invoice_portion=50, credit_days=14),
        ])
        if tax:
            account = frappe.db.get_value("Account", {
                "company": "PB Test Company", "account_type": "Tax", "is_group": 0}, "name")
            if not account:
                parent = frappe.db.get_value("Account", {"company": "PB Test Company", "root_type": "Liability", "is_group": 1}, "name")
                account = frappe.get_doc(dict(doctype="Account", account_name="PB Output Tax", company="PB Test Company",
                    parent_account=parent, account_type="Tax", is_group=0)).insert().name
            doc.append("taxes", dict(charge_type="On Net Total", account_head=account,
                                     description="Test VAT 11%", rate=11, included_in_print_rate=int(inclusive)))
            if actual:
                doc.append("taxes", dict(charge_type="Actual", account_head=account,
                                         description="Test fixed charge", tax_amount=actual))
        doc.insert()
        doc.submit()
        self.assertFalse(doc.payment_schedule)
        return doc

    def invoice(self, order, code):
        return frappe.get_doc("Sales Invoice", create_invoice(order.name, code, nowdate()))

    def pay(self, invoice):
        pe = get_payment_entry("Sales Invoice", invoice.name, bank_account=self.cash)
        pe.reference_no = "PB-TEST"
        pe.reference_date = nowdate()
        pe.insert()
        pe.submit()
        return pe

    def test_dp_delivery_final_invoice_and_payment(self):
        order = self.order()
        dp = self.invoice(order, "DP")
        self.assertEqual(dp.grand_total, 5000)
        self.assertEqual(dp.custom_pb_contract_items[0].qty, 10)
        self.assertEqual(dp.custom_pb_contract_items[0].rate, 1000)
        self.assertEqual(str(dp.due_date), str(add_days(nowdate(), 7)))
        dp.submit()
        order.reload()
        self.assertEqual(order.per_billed, 50)
        dn = make_delivery_note(order.name)
        dn.insert()
        with self.assertRaises(frappe.ValidationError):
            dn.submit()
        self.pay(dp)
        dn = frappe.get_doc("Delivery Note", dn.name)
        dn.submit()
        order.reload()
        self.assertEqual(order.per_delivered, 100)
        self.assertEqual(order.per_billed, 50)
        self.assertEqual(order.custom_pb_payment_status, "Partly Paid")
        self.assertEqual(order.custom_pb_outstanding_total, 0)
        self.assertEqual(order.custom_pb_unbilled_total, 5000)
        final = self.invoice(order, "FINAL")
        final.submit()
        order.reload()
        self.assertEqual(order.status, "Completed")
        self.assertEqual(order.custom_pb_payment_status, "Partly Paid")
        self.assertEqual(order.custom_pb_outstanding_total, 5000)
        self.pay(final)
        order.reload()
        self.assertEqual(order.custom_pb_payment_status, "Paid")
        self.assertEqual(order.custom_pb_received_total, 10000)
        self.assertEqual(order.custom_pb_outstanding_total, 0)

    def test_tax_included_in_installment_amount(self):
        order = self.order(tax=True)
        dp = self.invoice(order, "DP")
        self.assertEqual(dp.grand_total, 5550)
        self.assertEqual(dp.total_taxes_and_charges, 550)
        dp.submit()
        final = self.invoice(order, "FINAL")
        final.submit()
        self.assertEqual(dp.grand_total + final.grand_total, order.grand_total)

    def test_draft_reuse_and_cancel_releases_term(self):
        order = self.order()
        invoice = self.invoice(order, "DP")
        self.assertEqual(self.invoice(order, "DP").name, invoice.name)
        clone = frappe.copy_doc(invoice)
        with self.assertRaises(frappe.ValidationError):
            clone.insert()
        invoice.submit()
        invoice.cancel()
        replacement = self.invoice(order, "DP")
        self.assertNotEqual(replacement.name, invoice.name)
        order.reload()
        self.assertEqual(order.per_billed, 0)
        self.assertEqual(refresh(order.name)["custom_pb_billed_total"], 0)

    def test_direct_native_invoice_cannot_bypass_installments(self):
        order = self.order()
        invoice = make_sales_invoice(order.name)
        with self.assertRaises(frappe.ValidationError):
            invoice.insert()

    def test_standard_sales_order_invoice_still_works(self):
        order = make_sales_order(company="PB Test Company", customer="PB Test Customer", warehouse="Stores - PBT",
                                 item_code="_Test PB Goods", qty=2, rate=1000)
        invoice = make_sales_invoice(order.name)
        invoice.insert()
        invoice.submit()
        self.assertFalse(invoice.custom_pb_sales_order)
        self.assertEqual(invoice.grand_total, order.grand_total)

    def test_guest_cannot_generate_invoice(self):
        order = self.order()
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            create_invoice(order.name, "DP")

    def test_native_amendment_retains_installment(self):
        order = self.order()
        original = self.invoice(order, "DP")
        original.submit()
        original.cancel()
        amended = frappe.copy_doc(original)
        amended.docstatus = 0
        amended.amended_from = original.name
        amended.insert()
        self.assertEqual(amended.custom_pb_sales_order, order.name)
        self.assertEqual(amended.custom_pb_term_code, "DP")
        amended.submit()
        order.reload()
        self.assertEqual(order.per_billed, 50)

    def test_so_advance_reconciles_without_double_counting(self):
        order = self.order()
        pe = get_payment_entry("Sales Order", order.name, bank_account=self.cash)
        pe.paid_amount = 5000
        pe.received_amount = 5000
        pe.references[0].allocated_amount = 5000
        pe.reference_no = "PB-ADVANCE"
        pe.reference_date = nowdate()
        pe.insert()
        pe.submit()
        self.assertEqual(refresh(order.name)["custom_pb_received_total"], 5000)
        dp = self.invoice(order, "DP")
        dp.set_advances()
        dp.save()
        dp.submit()
        dp.reload()
        self.assertEqual(dp.outstanding_amount, 0)
        values = refresh(order.name)
        self.assertEqual(values["custom_pb_received_total"], 5000)
        self.assertEqual(values["custom_pb_outstanding_total"], 0)
        self.assertEqual(values["custom_pb_payment_status"], "Partly Paid")

    def test_inclusive_tax_installment(self):
        order = self.order(tax=True, inclusive=True)
        dp = self.invoice(order, "DP")
        dp.submit()
        self.assertEqual(dp.grand_total, order.grand_total / 2)
        self.assertTrue(dp.taxes[0].included_in_print_rate)

    def test_actual_tax_apportioned(self):
        order = self.order(tax=True, actual=200)
        dp = self.invoice(order, "DP")
        dp.submit()
        self.assertEqual(dp.grand_total, 5650)
        self.assertEqual(dp.taxes[1].tax_amount, 100)
