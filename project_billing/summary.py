"""Persist payment fields without redefining ERPNext's order status."""
import frappe
from frappe.utils import now_datetime

from project_billing.calculations import decimal, summarize


def receipts(order_name, invoice_names=()):
    # PE references move from SO to SI when an advance is reconciled. Reading the
    # current references counts either allocation once, unlike SO.advance_paid + SI paid.
    invoices = tuple(invoice_names) or ("",)
    rows = frappe.db.sql("""
        select pe.name as payment_entry, pe.payment_type,
          case when pe.payment_type='Receive' then pe.paid_from_account_currency
               else pe.paid_to_account_currency end as party_account_currency,
          ref.allocated_amount
        from `tabPayment Entry Reference` ref
        join `tabPayment Entry` pe on pe.name=ref.parent
        where pe.docstatus=1 and pe.party_type='Customer'
          and ((ref.reference_doctype='Sales Order' and ref.reference_name=%s)
            or (ref.reference_doctype='Sales Invoice' and ref.reference_name in %s))
    """, (order_name, invoices), as_dict=True)
    currency = frappe.db.get_value("Sales Order", order_name, "currency")
    result = decimal(0)
    checked = set()
    for row in rows:
        if row.payment_entry not in checked:
            payment = frappe.get_doc("Payment Entry", row.payment_entry)
            if payment.get("deductions") or payment.get("taxes"):
                frappe.throw("An allocated Payment Entry has deductions or payment taxes unsupported by Project Billing 0.1; review the allocation before refreshing the cash summary")
            checked.add(row.payment_entry)
        if row.party_account_currency != currency:
            frappe.throw("Project Billing payment references must use the order currency")
        if row.payment_type == "Receive":
            result += decimal(row.allocated_amount)
        elif row.payment_type == "Pay":
            result -= decimal(row.allocated_amount)
    return result


def invoice_rows(name):
    return frappe.get_all("Sales Invoice", filters={"custom_pb_sales_order": name, "docstatus": 1},
                          fields=["name", "grand_total", "rounded_total", "disable_rounded_total", "outstanding_amount"])


def refresh(name):
    from project_billing.billing import lock_order, precision, total
    order = lock_order(name)
    if not order.get("custom_pb_enabled"):
        return {}
    invoices = invoice_rows(name)
    values = summarize(
        total(order), sum(decimal(total(row)) for row in invoices),
        sum(decimal(row.outstanding_amount) for row in invoices),
        max(receipts(name, [row.name for row in invoices]), decimal(0)), precision(order),
    )
    if order.docstatus == 2:
        values["custom_pb_payment_status"] = "Cancelled"
    values["custom_pb_refreshed_at"] = now_datetime()
    frappe.db.set_value("Sales Order", name, values, update_modified=False)
    return values


@frappe.whitelist(methods=["POST"])
def refresh_payment_summary(sales_order):
    frappe.get_doc("Sales Order", sales_order).check_permission("read")
    return refresh(sales_order)


def refresh_all():
    # Scheduler repair also catches ERPNext reconciliation paths that use direct SQL.
    start = 0
    while True:
        rows = frappe.get_all("Sales Order", filters={"custom_pb_enabled": 1, "docstatus": 1},
                              pluck="name", order_by="name", limit_start=start, limit_page_length=200)
        for name in rows:
            refresh(name)
        if len(rows) < 200:
            break
        start += len(rows)


def enqueue_refresh(names):
    for name in sorted(set(filter(None, names))):
        frappe.enqueue("project_billing.summary.refresh", name=name, enqueue_after_commit=True)
