from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def check_compatibility():
    import erpnext

    if frappe.__version__.split(".")[0] != "15" or erpnext.__version__.split(".")[0] != "15":
        frappe.throw("Project Billing 0.1 supports Frappe/ERPNext v15 only")
    hooks = frappe.get_hooks("override_doctype_class").get("Sales Invoice", [])
    if isinstance(hooks, str):
        hooks = [hooks]
    own = "project_billing.overrides.ProjectBillingSalesInvoice"
    if any(path != own for path in hooks):
        frappe.throw("Another app overrides Sales Invoice. Review compatibility before installing Project Billing.")


def prepare_install():
    check_compatibility()
    # Existing sites can retain an app_modules cache from before bench get-app.
    # Frappe's sync_for reads this map before importing the new app's DocTypes.
    frappe.cache().delete_value("app_modules")
    frappe.setup_module_map(include_all_apps=True)


def ensure_schema():
    prepare_install()
    # Recover safely if an earlier install registered the app but stopped before
    # all DocTypes were imported. Child types must exist before their parents.
    for name in ("project_billing_term", "project_billing_contract_item",
                 "project_billing_template", "project_billing_settings"):
        if not frappe.db.exists("DocType", name.replace("_", " ").title()):
            frappe.reload_doc("project_billing", "doctype", name, force=True)


def setup():
    ensure_schema()
    currency = "currency"
    summary = [
        ("billed_total", "Total Ditagih"),
        ("unbilled_total", "Belum Ditagih"),
        ("received_total", "Pembayaran Diterima"),
        ("outstanding_total", "Outstanding Invoice"),
    ]
    so = [
        dict(fieldname="custom_pb_section", label="Project Billing", fieldtype="Section Break", insert_after="payment_schedule"),
        dict(fieldname="custom_pb_enabled", label="Use Project Installments", fieldtype="Check", default="0", insert_after="custom_pb_section"),
        dict(fieldname="custom_pb_template", label="Project Billing Template", fieldtype="Link", options="Project Billing Template", insert_after="custom_pb_enabled", depends_on="custom_pb_enabled"),
        dict(fieldname="custom_pb_terms", label="Project Installments", fieldtype="Table", options="Project Billing Term", insert_after="custom_pb_template", depends_on="custom_pb_enabled", mandatory_depends_on="custom_pb_enabled"),
        dict(fieldname="custom_pb_summary", label="Order Payment Summary", fieldtype="Section Break", insert_after="custom_pb_terms", depends_on="custom_pb_enabled"),
    ]
    after = "custom_pb_summary"
    for key, label in summary:
        name = "custom_pb_" + key
        so.append(dict(fieldname=name, label=label, fieldtype="Currency", options=currency, read_only=1, allow_on_submit=1, insert_after=after, in_list_view=int(key == "outstanding_total")))
        after = name
    so.extend([
        dict(fieldname="custom_pb_payment_status", label="Status Pembayaran", fieldtype="Select", options="\nUnpaid\nPartly Paid\nPaid\nSettled with Adjustments\nCancelled", read_only=1, allow_on_submit=1, in_list_view=1, in_standard_filter=1, insert_after=after),
        dict(fieldname="custom_pb_refreshed_at", label="Payment Summary Updated", fieldtype="Datetime", read_only=1, allow_on_submit=1, insert_after="custom_pb_payment_status"),
    ])
    # Keep the complete native customer section intact. Each conditional custom
    # section ends before the next native Section Break.
    si = [
        dict(fieldname="custom_pb_section", label="Penagihan Termin", fieldtype="Section Break", insert_after="amended_from", depends_on="custom_pb_sales_order"),
        dict(fieldname="custom_pb_sales_order", label="Sales Order", fieldtype="Link", options="Sales Order", read_only=1, no_copy=1, in_standard_filter=1, insert_after="custom_pb_section"),
        dict(fieldname="custom_pb_term_code", label="Installment Code", fieldtype="Data", read_only=1, hidden=1, no_copy=0, insert_after="custom_pb_sales_order"),
        dict(fieldname="custom_pb_term_label", label="Termin", fieldtype="Data", read_only=1, insert_after="custom_pb_term_code"),
        dict(fieldname="custom_pb_column", fieldtype="Column Break", insert_after="custom_pb_term_label"),
        dict(fieldname="custom_pb_portion", label="Porsi Termin (%)", fieldtype="Percent", read_only=1, insert_after="custom_pb_column"),
        dict(fieldname="custom_pb_contract_total", label="Nilai Kontrak (Termasuk Pajak)", fieldtype="Currency", options=currency, read_only=1, insert_after="custom_pb_portion"),
        dict(fieldname="custom_pb_target_total", label="Installment Total Including Tax", fieldtype="Currency", options=currency, read_only=1, hidden=1, insert_after="custom_pb_contract_total"),
        dict(fieldname="custom_pb_contract_section", label="Referensi Barang Kontrak", fieldtype="Section Break", collapsible=1, depends_on="custom_pb_sales_order", insert_after="custom_pb_target_total"),
        dict(fieldname="custom_pb_contract_items", label="Barang Kontrak", description="Rincian barang dari Sales Order; nilai tagihan termin tercantum pada Items dan Grand Total invoice.", fieldtype="Table", options="Project Billing Contract Item", read_only=1, insert_after="custom_pb_contract_section"),
    ]
    create_custom_fields({"Sales Order": so, "Sales Invoice": si}, update=True)
    frappe.db.add_index("Sales Invoice", ["custom_pb_sales_order", "custom_pb_term_code", "docstatus"], "pb_order_term_status")
    from project_billing.print_format_setup import setup as setup_si_jsi
    setup_si_jsi()
    name = "Project Installment Invoice"
    html = (Path(__file__).parent / "templates" / "installment_invoice.html").read_text()
    values = dict(doc_type="Sales Invoice", module="Project Billing", standard="No", custom_format=1, print_format_type="Jinja", html=html)
    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        doc.update(values)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc(dict(doctype="Print Format", name=name, **values)).insert(ignore_permissions=True)


def prevent_unsafe_uninstall():
    if frappe.db.exists("Sales Invoice", {"custom_pb_sales_order": ["is", "set"], "docstatus": ["!=", 2]}):
        frappe.throw("Active installment invoices exist. Plan a data migration before uninstalling Project Billing.")
