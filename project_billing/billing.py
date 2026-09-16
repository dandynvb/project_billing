"""Create native Sales Invoices; never submit, pay, or bypass permissions for the caller."""
import frappe
from frappe.utils import add_days, getdate, nowdate

from project_billing.calculations import allocate, decimal, money, validate_terms

TAX_FIELDS = (
    "charge_type", "account_head", "description", "cost_center", "included_in_print_rate",
    "rate", "row_id", "included_in_paid_amount",
)
HEADER_FIELDS = (
    "company", "customer", "currency", "conversion_rate", "selling_price_list",
    "price_list_currency", "plc_conversion_rate", "customer_address", "contact_person",
    "shipping_address_name", "company_address", "territory", "project", "cost_center",
    "tax_category", "po_no", "po_date", "tc_name", "terms",
)
CONTRACT_FIELDS = ("item_code", "item_name", "description", "qty", "uom", "rate", "amount")


def lock_order(name):
    # All invoice insert/save/submit paths share this lock, not just the UI button.
    rows = frappe.db.sql("select name from `tabSales Order` where name=%s for update", (name,))
    if not rows:
        frappe.throw("Sales Order not found")
    return frappe.get_doc("Sales Order", name, for_update=True)


def settings():
    doc = frappe.get_single("Project Billing Settings")
    if not doc.enabled:
        frappe.throw("Enable Project Billing in Project Billing Settings first")
    doc.validate()
    return doc


def precision(order):
    value = order.precision("grand_total")
    return 2 if value is None else value


def total(order):
    return order.rounded_total if order.rounded_total and not order.disable_rounded_total else order.grand_total


def check_order(order):
    if order.docstatus != 1 or not order.get("custom_pb_enabled"):
        frappe.throw("Select a submitted Sales Order with Project Installments enabled")
    if order.status in ("Closed", "On Hold", "Cancelled"):
        frappe.throw("This Sales Order is closed, on hold, or cancelled")
    check_supported(order)


def check_supported(order):
    """Fail visibly for cases whose proportional accounting is not supported yet."""
    try:
        validate_terms(order.get("custom_pb_terms"))
    except ValueError as exc:
        frappe.throw(str(exc))
    company_currency = frappe.get_cached_value("Company", order.company, "default_currency")
    if order.currency != company_currency or decimal(order.conversion_rate) != 1:
        frappe.throw("Project Billing 0.1 requires the company currency and conversion rate 1")
    if decimal(order.grand_total) <= 0 or not order.items:
        frappe.throw("Project Billing requires a positive contract total")
    if money(total(order), precision(order)) != money(order.grand_total, precision(order)):
        frappe.throw("Disable Rounded Total on this order before using Project Billing")
    if order.get("discount_amount") or order.get("additional_discount_percentage"):
        frappe.throw("Project Billing 0.1 supports item discounts, but not additional order-level discounts")
    if order.get("is_internal_customer"):
        frappe.throw("Inter-company billing is not supported by Project Billing 0.1")
    for row in order.items:
        if decimal(row.amount) <= 0 or decimal(row.qty) <= 0:
            frappe.throw("Each contract item must have a positive quantity and amount")
        if row.get("item_tax_template") or any(decimal(v) for v in frappe.parse_json(row.get("item_tax_rate") or "{}").values()):
            frappe.throw("Use order-level taxes: item-specific tax overrides are not supported yet")
        if row.get("delivered_by_supplier"):
            frappe.throw("Drop shipping is not supported by Project Billing 0.1")
    for tax in order.get("taxes", []):
        if tax.charge_type not in ("On Net Total", "Actual") or decimal(tax.rate) < 0 or decimal(tax.tax_amount) < 0:
            frappe.throw("Project Billing 0.1 supports positive On Net Total and Actual sales taxes only")


def term_plan(order, code):
    terms = order.custom_pb_terms
    codes = [row.term_code for row in terms]
    if code not in codes:
        frappe.throw("Installment code is not part of this Sales Order")
    index = codes.index(code)
    portions = [row.invoice_portion for row in terms]
    def share(value):
        return float(allocate(value, portions, precision(order))[index])
    return terms[index], share


def live_invoice(order, code, exclude=None):
    # Locking/current read also sees another request's newly committed draft
    # under MariaDB REPEATABLE READ, after waiting on the order lock.
    rows = frappe.db.sql("""
        select name from `tabSales Invoice`
        where custom_pb_sales_order=%s and custom_pb_term_code=%s
          and docstatus<2 and name!=%s limit 1 for update
    """, (order, code, exclude or ""))
    return rows[0][0] if rows else None


def contract_rows(order):
    return [dict(sales_order_item=r.name, currency=order.currency, **{f: r.get(f) for f in CONTRACT_FIELDS}) for r in order.items]


def copy_dimensions(source, target):
    from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
        get_accounting_dimensions,
    )
    for field in get_accounting_dimensions():
        if target.meta.has_field(field) and source.get(field):
            target.set(field, source.get(field))


def build_invoice(order, code, posting_date):
    term, share = term_plan(order, code)
    item = frappe.get_doc("Item", settings().billing_item)
    invoice = frappe.new_doc("Sales Invoice")
    for field in HEADER_FIELDS:
        if order.get(field) is not None:
            invoice.set(field, order.get(field))
    copy_dimensions(order, invoice)
    invoice.update(dict(
        posting_date=getdate(posting_date), due_date=add_days(posting_date, term.credit_days or 0),
        set_posting_time=1, ignore_pricing_rule=1, disable_rounded_total=1,
        payment_terms_template=None, ignore_default_payment_terms_template=1,
        custom_pb_sales_order=order.name, custom_pb_term_code=code,
        custom_pb_term_label=term.label, custom_pb_portion=term.invoice_portion,
        custom_pb_contract_total=total(order), custom_pb_target_total=share(total(order)),
        custom_pb_contract_items=contract_rows(order), update_stock=0,
    ))
    for source in order.items:
        rate = share(source.amount)
        if rate <= 0:
            frappe.throw("An installment rounds to zero for an item. Increase its portion or revise the contract before submitting it.")
        row = invoice.append("items", dict(
            item_code=item.name, item_name=item.item_name,
            description=f"{term.label} ({term.invoice_portion}%) - {source.item_code}",
            qty=1, uom=item.stock_uom, stock_uom=item.stock_uom, conversion_factor=1,
            rate=rate, price_list_rate=rate, sales_order=order.name, so_detail=source.name,
            income_account=source.get("income_account"), cost_center=source.get("cost_center") or order.get("cost_center"),
            project=source.get("project") or order.get("project"),
        ))
        copy_dimensions(source, row)
    for source in order.get("taxes", []):
        row = {field: source.get(field) for field in TAX_FIELDS}
        if source.charge_type == "Actual":
            row["tax_amount"] = share(source.tax_amount)
        invoice.append("taxes", row)
    invoice.set_missing_values()
    # Customer defaults must not replace the contract's taxes or installment due date.
    invoice.payment_terms_template = None
    invoice.set("payment_schedule", [])
    invoice.calculate_taxes_and_totals()
    invoice.append("payment_schedule", dict(
        description=term.label, invoice_portion=100,
        due_date=invoice.due_date, payment_amount=invoice.grand_total,
    ))
    return invoice


@frappe.whitelist(methods=["POST"])
def create_invoice(sales_order, term_code, posting_date=None):
    frappe.get_doc("Sales Order", sales_order).check_permission("read")
    frappe.has_permission("Sales Invoice", "create", throw=True)
    order = lock_order(sales_order)
    check_order(order)
    existing = live_invoice(order.name, term_code)
    if existing:
        frappe.get_doc("Sales Invoice", existing, for_update=True).check_permission("read")
        return existing
    invoice = build_invoice(order, term_code, posting_date or nowdate())
    invoice.insert()  # Native permission, mandatory, and accounting validations.
    return invoice.name


def validate_installment(invoice):
    order = lock_order(invoice.custom_pb_sales_order)
    order.check_permission("read")
    check_order(order)
    if live_invoice(order.name, invoice.custom_pb_term_code, invoice.name):
        frappe.throw("This installment already has a draft or submitted invoice")
    term, share = term_plan(order, invoice.custom_pb_term_code)
    forbidden = ("is_return", "is_debit_note", "is_pos", "update_stock", "discount_amount", "additional_discount_percentage", "apply_tds", "is_internal_customer")
    if any(invoice.get(field) for field in forbidden) or invoice.get("return_against"):
        frappe.throw("Returns, POS, stock updates, withholding, and additional discounts are not supported on installment invoices")
    if invoice.payment_terms_template or invoice.get("auto_repeat"):
        frappe.throw("Use the installment due date and create each invoice from the Sales Order")
    for field in ("customer", "company", "currency", "project"):
        if (invoice.get(field) or "") != (order.get(field) or ""):
            frappe.throw(f"Installment invoice {field} must match its Sales Order")
    if invoice.get("party_account_currency") and invoice.party_account_currency != order.currency:
        frappe.throw("Receivable account currency must match the contract currency")
    if decimal(invoice.conversion_rate) != 1:
        frappe.throw("Installment currency conversion rate must remain 1")
    if getdate(invoice.due_date) != getdate(add_days(invoice.posting_date, term.credit_days or 0)):
        frappe.throw("Due date must equal invoice date plus the installment credit days")
    expected_item = settings().billing_item
    stock_uom = frappe.get_cached_value("Item", expected_item, "stock_uom")
    originals = {row.name: row for row in order.items}
    seen = set()
    for row in invoice.items:
        source = originals.get(row.so_detail)
        if not source or row.so_detail in seen or row.sales_order != order.name:
            frappe.throw("Each original Sales Order row must be referenced exactly once")
        seen.add(row.so_detail)
        if row.item_code != expected_item or decimal(row.qty) != 1 or decimal(row.conversion_factor) != 1 or row.uom != stock_uom or row.stock_uom != stock_uom:
            frappe.throw("Use one unit of the configured non-stock installment billing item")
        if row.get("delivery_note") or row.get("dn_detail") or row.get("item_tax_template") or row.get("enable_deferred_revenue"):
            frappe.throw("Deliver original goods from the Sales Order; no delivery or deferred-revenue references on installment rows")
        if any(decimal(v) for v in frappe.parse_json(row.get("item_tax_rate") or "{}").values()):
            frappe.throw("Item tax overrides are not supported on installment rows")
        if money(row.rate, precision(order)) != money(share(source.amount), precision(order)) or money(row.amount, precision(order)) != money(share(source.amount), precision(order)):
            frappe.throw("Installment row amounts must match the contract portion; recreate the draft from the Sales Order")
    if seen != set(originals):
        frappe.throw("Invoice is missing an original Sales Order reference")
    if len(invoice.taxes) != len(order.taxes):
        frappe.throw("Installment taxes must match the Sales Order")
    for actual, source in zip(invoice.taxes, order.taxes):
        for field in TAX_FIELDS:
            if field in ("description", "cost_center"):
                continue
            if field in ("rate", "row_id", "included_in_print_rate", "included_in_paid_amount"):
                matches = decimal(actual.get(field)) == decimal(source.get(field))
            else:
                matches = (actual.get(field) or "") == (source.get(field) or "")
            if not matches:
                frappe.throw("Installment tax configuration must match the Sales Order")
        if source.charge_type == "Actual" and money(actual.tax_amount, precision(order)) != money(share(source.tax_amount), precision(order)):
            frappe.throw("Actual tax charges must be apportioned across installments")
    if money(total(invoice), precision(order)) != money(share(total(order)), precision(order)):
        frappe.throw("ERPNext tax rounding does not equal this installment's contract share. This combination needs a rounding design review; do not change the contract or tax amounts to bypass this check.")
    # Snapshot is authoritative contract data, not editable sales lines.
    invoice.set("custom_pb_contract_items", contract_rows(order))
    invoice.custom_pb_contract_total = total(order)
    invoice.custom_pb_target_total = share(total(order))
    invoice.custom_pb_portion = term.invoice_portion
    invoice.custom_pb_term_label = term.label
    if len(invoice.payment_schedule) != 1 or decimal(invoice.payment_schedule[0].invoice_portion) != 100 or getdate(invoice.payment_schedule[0].due_date) != getdate(invoice.due_date):
        frappe.throw("Each installment invoice must have one payment schedule for 100% of its amount")
