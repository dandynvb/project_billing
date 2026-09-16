"""ERPNext's fixture setup can reset test data; require an explicitly isolated site."""
import frappe


def before_tests():
    if not frappe.conf.get("project_billing_test_site"):
        frappe.throw("Run Project Billing integration tests only on an isolated site with project_billing_test_site enabled")
    from erpnext.setup.utils import before_tests as erpnext_before_tests

    erpnext_before_tests()
