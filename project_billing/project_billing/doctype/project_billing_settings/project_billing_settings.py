import frappe
from frappe.model.document import Document


class ProjectBillingSettings(Document):
    def validate(self):
        if not self.enabled:
            return
        if not self.billing_item:
            frappe.throw("Select a non-stock installment billing item first")
        item = frappe.get_doc("Item", self.billing_item)
        if item.disabled or item.is_stock_item or not item.is_sales_item or item.is_fixed_asset or item.enable_deferred_revenue or item.taxes:
            frappe.throw("Billing item must be an enabled non-stock sales item, without deferred revenue or item tax templates")
