"""Pure, deterministic rules. No Frappe imports or database side effects."""

from decimal import ROUND_HALF_UP, Decimal


def decimal(value):
    result = Decimal(str(value if value is not None else 0))
    if not result.is_finite():
        raise ValueError("Amounts must be finite")
    return result


def money(value, precision=2):
    return decimal(value).quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)


def validate_terms(rows):
    if not rows:
        raise ValueError("Add at least one installment")
    codes = set()
    total = Decimal(0)
    for row in rows:
        code = str(row.get("term_code") or "").strip()
        if not code or code in codes:
            raise ValueError("Each installment needs a unique code")
        codes.add(code)
        if row.get("term_type") not in (None, "", "Auto", "DP", "Progress", "Pelunasan"):
            raise ValueError("Choose Auto, DP, Progress, or Pelunasan for the installment type")
        portion = decimal(row.get("invoice_portion"))
        if portion <= 0 or portion > 100:
            raise ValueError("Each installment portion must be greater than 0 and at most 100")
        days = decimal(row.get("credit_days"))
        if days < 0 or days != days.to_integral_value():
            raise ValueError("Credit days must be a non-negative integer")
        total += portion
    if total != 100:
        raise ValueError("Installment portions must total exactly 100%")


def allocate(total, portions, precision=2):
    """Cumulative rounding: stable by term order, sums exactly even if billed out of order."""
    if sum(map(decimal, portions)) != 100 or any(decimal(p) <= 0 for p in portions):
        raise ValueError("Positive portions must sum to 100%")
    total = money(total, precision)
    cumulative = Decimal(0)
    previous = Decimal(0)
    amounts = []
    for portion in portions:
        cumulative += decimal(portion)
        current = money(total * cumulative / 100, precision)
        amounts.append(current - previous)
        previous = current
    return amounts


def summarize(contract_total, billed_total, invoice_outstanding, payments_received, precision=2):
    total, billed, outstanding, received = map(
        lambda x: money(x, precision),
        (contract_total, billed_total, invoice_outstanding, payments_received),
    )
    if min(total, billed, received) < 0:
        raise ValueError("Negative contracts, billing or receipts require a separate adjustment flow")
    unbilled = max(total - billed, Decimal(0))
    outstanding = max(outstanding, Decimal(0))
    # A paid first invoice is not a fully paid contract. Write-offs are not cash receipts.
    if total > 0 and received >= total:
        status = "Paid"
    elif unbilled == 0 and outstanding == 0 and billed > 0:
        status = "Settled with Adjustments"
    elif received > 0:
        status = "Partly Paid"
    else:
        status = "Unpaid"
    return {
        "custom_pb_billed_total": float(billed),
        "custom_pb_unbilled_total": float(unbilled),
        "custom_pb_received_total": float(received),
        "custom_pb_outstanding_total": float(outstanding),
        "custom_pb_payment_status": status,
    }
