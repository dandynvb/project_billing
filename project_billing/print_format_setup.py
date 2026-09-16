"""Install the SI JSI builder format without changing PO JSI or global print settings."""
import json
from pathlib import Path

import frappe


def setup():
    path = Path(__file__).parent / "templates"
    heading = '<div align="right"><h1><b>{{ "Proforma Invoice" if doc.docstatus == 0 else ("Cancelled Invoice" if doc.docstatus == 2 else "Sales Invoice") }}</b></h1></div>'
    blocks = [
        dict(fieldname="print_heading_template", fieldtype="Custom HTML", options=heading),
        dict(fieldtype="Section Break", label=""),
        dict(fieldtype="Column Break"),
    ]
    sections = [
        ("Informasi Invoice", "invoice_info"),
        ("Alamat Bill To dan Ship To", "addresses"),
        ("Referensi SO dan Termin", "order_reference"),
        ("Tabel Item, Total, dan Pembayaran", "items"),
        ("Catatan Pembayaran", "notes"),
        ("Tanda Tangan", "signature"),
    ]
    for label, filename in sections:
        blocks.append(dict(fieldname="_custom_html", fieldtype="HTML", label=label,
                           print_hide=0, options=(path / f"si_jsi_{filename}.html").read_text()))
    values = dict(doc_type="Sales Invoice", module="Project Billing", standard="No",
                  custom_format=0, print_format_type="Jinja", disabled=0,
                  font_size=14, css=(path / "si_jsi.css").read_text(),
                  format_data=json.dumps(blocks), html="")
    name = "SI JSI"
    if frappe.db.exists("Print Format", name):
        doc = frappe.get_doc("Print Format", name)
        if doc.module != "Project Billing" or doc.doc_type != "Sales Invoice":
            frappe.throw("SI JSI already exists outside Project Billing; choose a different name before installing")
        doc.update(values)
        doc.save()
    else:
        frappe.get_doc(dict(doctype="Print Format", name=name, **values)).insert()
