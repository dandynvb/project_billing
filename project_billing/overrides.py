from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.controllers.selling_controller import SellingController


class ProjectBillingSalesInvoice(SalesInvoice):
    def validate_with_previous_doc(self):
        if not self.get("custom_pb_sales_order"):
            return super().validate_with_previous_doc()
        from project_billing.billing import validate_installment

        # Replace only the same-item/same-rate comparison for value-based billing.
        # All other SalesInvoice.validate/on_submit/accounting logic remains native.
        validate_installment(self)
        SellingController.validate_with_previous_doc(self, {
            "Sales Order": {
                "ref_dn_field": "sales_order",
                "compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]],
            },
            "Sales Order Item": {
                "ref_dn_field": "so_detail",
                "compare_fields": [],
                "is_child_table": True,
                "allow_duplicate_prev_row_id": False,
            },
        })
