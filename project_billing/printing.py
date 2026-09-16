"""Read-only context for the builder-based SI JSI print format."""
import frappe
from frappe.utils import now_datetime

from project_billing.calculations import decimal


def installment_kind(terms, code):
    for index, term in enumerate(terms):
        if term.get("term_code") == code:
            explicit = term.get("term_type")
            if explicit in ("DP", "Progress", "Pelunasan"):
                return explicit
            if index == len(terms) - 1:
                return "Pelunasan"
            return "DP" if index == 0 else "Progress"
    raise ValueError("Invoice term is not present in its Sales Order")


def balances(contract, received, invoice_total, invoice_outstanding, current_received):
    # Never subtract earlier installments from this invoice's own receivable.
    return dict(
        contract_remaining=float(max(decimal(contract) - decimal(received), decimal(0))),
        received=float(received),
        received_elsewhere=float(max(decimal(received) - decimal(current_received), decimal(0))),
        current_received=float(current_received),
        invoice_total=float(invoice_total),
        due=float(max(decimal(invoice_outstanding), decimal(0))),
    )


def sales_invoice_context(doc):
    # Do not expose this as a public API: it is called by the authorized print route.
    doc.check_permission("print")
    if doc.get("is_return"):
        frappe.throw("Use a credit-note print format for returns")
    invoice_total = doc.rounded_total if doc.rounded_total and not doc.disable_rounded_total else doc.grand_total
    outstanding = doc.outstanding_amount if doc.docstatus == 1 else max(
        decimal(invoice_total) - decimal(doc.get("total_advance")) - decimal(doc.get("paid_amount")), decimal(0))
    if doc.docstatus == 2:
        outstanding = 0
    result = dict(kind="Standard", order=None, rows=doc.items, source=doc,
                  printed_at=now_datetime(), portion=doc.get("custom_pb_portion") or 100)
    if not doc.get("custom_pb_sales_order"):
        result.update(balances(invoice_total, 0, invoice_total, outstanding, 0))
        return result
    order = frappe.get_doc("Sales Order", doc.custom_pb_sales_order)
    order.check_permission("read")
    if order.company != doc.company or order.customer != doc.customer or order.currency != doc.currency:
        frappe.throw("Invoice and Sales Order identities do not match")
    from project_billing.billing import total
    from project_billing.summary import invoice_rows, receipts
    names = [row.name for row in invoice_rows(order.name)]
    received = max(receipts(order.name, names), decimal(0))
    # The aggregate above checks supported payments and matching account currency.
    allocated = frappe.db.sql("""
        select coalesce(sum(case when pe.payment_type='Receive' then r.allocated_amount
                     when pe.payment_type='Pay' then -r.allocated_amount else 0 end),0)
        from `tabPayment Entry Reference` r join `tabPayment Entry` pe on pe.name=r.parent
        where pe.docstatus=1 and pe.party_type='Customer'
          and r.reference_doctype='Sales Invoice' and r.reference_name=%s
    """, (doc.name,))[0][0] if doc.name in names else 0
    kind = installment_kind(order.custom_pb_terms, doc.custom_pb_term_code)
    result.update(kind=kind, order=order, source=order if kind == "Pelunasan" else doc,
                  rows=order.items if kind == "Pelunasan" else doc.items)
    result.update(balances(total(order), received, invoice_total, outstanding, allocated))
    return result
