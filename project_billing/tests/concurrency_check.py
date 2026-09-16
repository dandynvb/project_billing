"""Manual two-connection check; creates data ONLY on an explicitly isolated test site."""
import json
import subprocess
import sys

import frappe


def run():
    if not frappe.conf.get("project_billing_test_site"):
        frappe.throw("Concurrency check requires an isolated Project Billing test site")
    from project_billing.tests.test_integration import TestProjectBilling

    case = TestProjectBilling()
    case.setUp()
    order = case.order()
    # Separate database connections must see the same submitted order.
    # Do not use this check in an ordinary rollback-based unit test.
    frappe.db.commit()
    program = '''
import frappe,sys,time,json
from project_billing.billing import create_invoice, lock_order
frappe.init(site=sys.argv[1]);frappe.connect();frappe.set_user('Administrator')
frappe.get_doc('Sales Order',sys.argv[2]).check_permission('read')
lock_order(sys.argv[2]);time.sleep(1)
name=create_invoice(sys.argv[2],'DP')
frappe.db.commit();frappe.destroy()
print(json.dumps({'invoice':name}))
'''
    processes = [subprocess.Popen([sys.executable, "-c", program, frappe.local.site, order.name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    names = []
    for process in processes:
        out, err = process.communicate(timeout=60)
        if process.returncode:
            raise AssertionError(err[-3000:])
        names.append(json.loads(out.strip().splitlines()[-1])["invoice"])
    frappe.db.rollback()  # Start a fresh read snapshot after both worker commits.
    active = frappe.get_all("Sales Invoice", filters={"custom_pb_sales_order": order.name,
        "custom_pb_term_code": "DP", "docstatus": ["<", 2]}, pluck="name")
    assert len(active) == 1 and names[0] == names[1] == active[0], (names, active)
    return {"result": "PASS", "order": order.name, "invoices_returned": names, "active_count": len(active)}
