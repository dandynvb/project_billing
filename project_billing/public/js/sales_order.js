frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        const enabled = Boolean(frm.doc.custom_pb_enabled);
        frm.toggle_display(["payment_terms_template", "payment_schedule"], !enabled);
        if (!enabled || frm.is_new()) return;
        frm.add_custom_button(__("Refresh Payments"), async () => {
            await frappe.call({method: "project_billing.summary.refresh_payment_summary",
                args: {sales_order: frm.doc.name}, freeze: true});
            await frm.reload_doc();
        }, __("Project Billing"));
        frm.add_custom_button(__("Installment Invoices"), () => {
            frappe.set_route("List", "Sales Invoice", {custom_pb_sales_order: frm.doc.name});
        }, __("Project Billing"));
        if (frm.doc.docstatus !== 1 || ["Closed", "On Hold", "Cancelled"].includes(frm.doc.status)) return;
        if (!frappe.model.can_create("Sales Invoice")) return;
        frm.add_custom_button(__("Create Installment Invoice"), () => {
            const terms = frm.doc.custom_pb_terms || [];
            const dialog = new frappe.ui.Dialog({
                title: __("Create Installment Invoice"),
                fields: [
                    {fieldname: "term_code", label: __("Installment"), fieldtype: "Select", reqd: 1,
                        options: terms.map(t => ({value: t.term_code,
                            label: `${t.label} (${t.invoice_portion}%)`}))},
                    {fieldname: "posting_date", label: __("Invoice Date"), fieldtype: "Date",
                        reqd: 1, default: frappe.datetime.get_today()}
                ],
                primary_action_label: __("Create Draft"),
                async primary_action(values) {
                    dialog.disable_primary_action();
                    try {
                        const result = await frappe.call({method: "project_billing.billing.create_invoice",
                            args: {sales_order: frm.doc.name, ...values}, freeze: true});
                        dialog.hide();
                        frappe.set_route("Form", "Sales Invoice", result.message);
                    } finally { dialog.enable_primary_action(); }
                }
            });
            dialog.show();
        }, __("Project Billing"));
    },
    custom_pb_enabled(frm) {
        if (frm.doc.docstatus !== 0) return;
        if (frm.doc.custom_pb_enabled) {
            frm.set_value("payment_terms_template", "");
            frm.clear_table("payment_schedule");
            frm.refresh_field("payment_schedule");
        }
        frm.trigger("refresh");
    },
    async custom_pb_template(frm) {
        if (frm.doc.docstatus !== 0 || !frm.doc.custom_pb_template) return;
        const templateName = frm.doc.custom_pb_template;
        const result = await frappe.db.get_doc("Project Billing Template", templateName);
        if (frm.doc.custom_pb_template !== templateName) return;
        if (result.disabled) {
            frappe.msgprint(__("Choose an enabled Project Billing Template"));
            return;
        }
        frm.clear_table("custom_pb_terms");
        for (const term of result.terms) {
            const row = frm.add_child("custom_pb_terms");
            for (const field of ["term_code", "label", "term_type", "invoice_portion", "credit_days", "required_before_delivery"])
                row[field] = term[field];
        }
        frm.refresh_field("custom_pb_terms");
        frm.dirty();
    }
});
