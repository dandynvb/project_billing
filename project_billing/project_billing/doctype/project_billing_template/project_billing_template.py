import frappe
from frappe.model.document import Document

from project_billing.calculations import validate_terms


class ProjectBillingTemplate(Document):
    def validate(self):
        try:
            validate_terms([row.as_dict() for row in self.terms])
        except ValueError as exc:
            frappe.throw(str(exc))
