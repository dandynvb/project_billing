import frappe

from project_billing.calculations import decimal, money


def prepare_order(doc, method=None):
    if doc.get("custom_pb_enabled"):
        doc.payment_terms_template = None
        doc.ignore_default_payment_terms_template = 1
        doc.set("payment_schedule", [])


def validate_order(doc, method=None):
    if not doc.get("custom_pb_enabled"):
        return
    from project_billing.billing import check_supported, settings
    settings()
    check_supported(doc)
    # ERPNext may generate a default single payment row during its validation.
    # The custom term table is the only schedule persisted for these orders.
    prepare_order(doc)


def freeze_order(doc, method=None):
    if not doc.get("custom_pb_enabled"):
        return
    old = doc.get_doc_before_save()
    if not old:
        return
    fields = ("qty", "rate", "amount", "item_code", "uom", "conversion_factor")
    before = [(r.name, tuple(r.get(f) for f in fields)) for r in old.items]
    after = [(r.name, tuple(r.get(f) for f in fields)) for r in doc.items]
    if before != after or decimal(doc.grand_total) != decimal(old.grand_total):
        frappe.throw("A submitted project contract is fixed. Create a new Sales Order for changes in project value.")


def refresh_order(doc, method=None):
    if doc.get("custom_pb_enabled"):
        from project_billing.summary import refresh
        refresh(doc.name)


def guard_invoice(doc, method=None):
    # no_copy on the SO link prevents ERPNext's generic mapper from marking every
    # ordinary SO invoice as an installment. Restore it only for native amendments.
    if doc.get("amended_from"):
        source = frappe.db.get_value("Sales Invoice", doc.amended_from,
            ["custom_pb_sales_order", "custom_pb_term_code"], as_dict=True)
        if source and source.custom_pb_sales_order:
            if doc.get("custom_pb_sales_order") not in (None, "", source.custom_pb_sales_order) or doc.get("custom_pb_term_code") not in (None, "", source.custom_pb_term_code):
                frappe.throw("An amended installment must retain the original contract and term")
            doc.custom_pb_sales_order = source.custom_pb_sales_order
            doc.custom_pb_term_code = source.custom_pb_term_code
    before = doc.get_doc_before_save()
    if before and before.get("custom_pb_sales_order") and doc.get("custom_pb_sales_order") != before.custom_pb_sales_order:
        frappe.throw("An installment invoice cannot be detached from its Sales Order")
    orders = {row.sales_order for row in doc.items if row.sales_order}
    for row in doc.items:
        if row.get("so_detail"):
            source = frappe.db.get_value("Sales Order Item", row.so_detail, "parent")
            if source:
                orders.add(source)
        # A mapped Delivery Note invoice must not bypass the managed SO check.
        if row.get("dn_detail"):
            source = frappe.db.get_value("Delivery Note Item", row.dn_detail, "against_sales_order")
            if source:
                orders.add(source)
    managed = {name for name in orders if frappe.db.get_value("Sales Order", name, "custom_pb_enabled")}
    if managed and (not doc.get("custom_pb_sales_order") or managed != {doc.custom_pb_sales_order}):
        frappe.throw("Create installment invoices using Project Billing on the Sales Order")
    if doc.get("return_against") and frappe.db.get_value("Sales Invoice", doc.return_against, "custom_pb_sales_order"):
        frappe.throw("Returns are outside the Project Billing workflow")
    if doc.get("custom_pb_sales_order"):
        doc.ignore_default_payment_terms_template = 1
        if doc.get("is_return") or doc.get("is_debit_note"):
            frappe.throw("Returns and debit notes are outside the Project Billing workflow")


def refresh_invoice(doc, method=None):
    if doc.get("custom_pb_sales_order"):
        from project_billing.summary import enqueue_refresh, refresh
        if method == "on_trash":
            enqueue_refresh([doc.custom_pb_sales_order])
        else:
            refresh(doc.custom_pb_sales_order)


def orders_for_references(references):
    orders = set()
    for doctype, name in references:
        if doctype == "Sales Order" and frappe.db.get_value(doctype, name, "custom_pb_enabled"):
            orders.add(name)
        elif doctype == "Sales Invoice":
            order = frappe.db.get_value(doctype, name, "custom_pb_sales_order")
            if order:
                orders.add(order)
    return orders


def refresh_payment(doc, method=None):
    from project_billing.summary import enqueue_refresh, refresh
    refs = [(r.reference_doctype, r.reference_name) for r in doc.references]
    before = doc.get_doc_before_save()
    if before:
        refs.extend((r.reference_doctype, r.reference_name) for r in before.references)
    orders = orders_for_references(refs)
    for name in sorted(orders):
        refresh(name)
    enqueue_refresh(orders)


def ledger_changed(doc, method=None):
    from project_billing.summary import enqueue_refresh
    enqueue_refresh(orders_for_references([
        (doc.voucher_type, doc.voucher_no),
        (doc.against_voucher_type, doc.against_voucher_no),
    ]))


def guard_delivery_source(doc, method=None):
    for row in doc.items:
        if row.get("against_sales_invoice") and frappe.db.get_value("Sales Invoice", row.against_sales_invoice, "custom_pb_sales_order"):
            frappe.throw("Create the Delivery Note from the Sales Order to deliver the original goods")
        if doc.get("is_return") and row.get("against_sales_order") and frappe.db.get_value("Sales Order", row.against_sales_order, "custom_pb_enabled"):
            frappe.throw("Returns are outside the Project Billing workflow")


def check_delivery_payment(doc, method=None):
    from project_billing.billing import lock_order, precision, term_plan, total
    from project_billing.summary import invoice_rows, receipts
    if not frappe.db.get_single_value("Project Billing Settings", "enforce_delivery_payment"):
        return
    orders = {row.against_sales_order for row in doc.items if row.against_sales_order}
    for name in sorted(orders):
        order = lock_order(name)
        if not order.get("custom_pb_enabled"):
            continue
        required = decimal(0)
        for term in order.custom_pb_terms:
            if term.required_before_delivery:
                _, share = term_plan(order, term.term_code)
                required += decimal(share(total(order)))
        received = receipts(name, [row.name for row in invoice_rows(name)])
        if money(received, precision(order)) < money(required, precision(order)):
            frappe.throw(f"Sales Order {name}: receive the required down payment before submitting delivery")


def validate_invoice_final(doc, method=None):
    # Recheck after the complete native validate pipeline, including tax withholding.
    if doc.get("custom_pb_sales_order"):
        from project_billing.billing import validate_installment
        validate_installment(doc)


def guard_payment(doc, method=None):
    refs = [(r.reference_doctype, r.reference_name) for r in doc.references]
    if not orders_for_references(refs):
        return
    if doc.get("deductions") or doc.get("taxes"):
        frappe.throw("Project Billing 0.1 requires Payment Entries without deductions or payment taxes. Use a separate accounting adjustment so received cash remains traceable.")
