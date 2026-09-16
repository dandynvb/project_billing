app_name = "project_billing"
app_title = "Project Billing"
app_publisher = "Project Billing Contributors"
app_description = "Invoice project installments and track Sales Order payments"
app_email = ""
app_license = "MIT"
required_apps = ["erpnext"]

before_install = "project_billing.install.prepare_install"
after_install = "project_billing.install.setup"
after_migrate = "project_billing.install.setup"
before_uninstall = "project_billing.install.prevent_unsafe_uninstall"

# Only one narrow validation override; standard invoices delegate to ERPNext unchanged.
override_doctype_class = {
    "Sales Invoice": "project_billing.overrides.ProjectBillingSalesInvoice",
}
doctype_js = {
    "Sales Order": "public/js/sales_order.js",
    "Sales Invoice": "public/js/sales_invoice.js",
}
doctype_list_js = {"Sales Order": "public/js/sales_order_list.js"}

doc_events = {
    "Sales Order": {
        "before_validate": "project_billing.events.prepare_order",
        "validate": "project_billing.events.validate_order",
        "before_update_after_submit": "project_billing.events.freeze_order",
        "on_update_after_submit": "project_billing.events.refresh_order",
        "on_submit": "project_billing.events.refresh_order",
        "on_cancel": "project_billing.events.refresh_order",
    },
    "Sales Invoice": {
        "before_validate": "project_billing.events.guard_invoice",
        "validate": "project_billing.events.validate_invoice_final",
        "on_submit": "project_billing.events.refresh_invoice",
        "on_cancel": "project_billing.events.refresh_invoice",
        "on_trash": "project_billing.events.refresh_invoice",
    },
    "Payment Entry": {
        "validate": "project_billing.events.guard_payment",
        "before_update_after_submit": "project_billing.events.guard_payment",
        "on_submit": "project_billing.events.refresh_payment",
        "on_cancel": "project_billing.events.refresh_payment",
        "on_update_after_submit": "project_billing.events.refresh_payment",
    },
    "Payment Ledger Entry": {
        "on_update": "project_billing.events.ledger_changed",
        "on_trash": "project_billing.events.ledger_changed",
    },
    "Delivery Note": {
        "before_validate": "project_billing.events.guard_delivery_source",
        "before_submit": "project_billing.events.check_delivery_payment",
    },
}
scheduler_events = {"hourly": ["project_billing.summary.refresh_all"]}

before_tests = "project_billing.tests.setup.before_tests"

# Builder HTML blocks may obtain a permission-checked, read-only print context.
jinja = {"methods": ["project_billing.printing.sales_invoice_context"]}
