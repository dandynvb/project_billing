frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (!frm.doc.custom_pb_sales_order) return;
        frm.add_custom_button(__("Project Sales Order"), () =>
            frappe.set_route("Form", "Sales Order", frm.doc.custom_pb_sales_order), __("View"));
        frm.add_custom_button(__("Print Installment Invoice"), () => {
            const query = new URLSearchParams({doctype: "Sales Invoice", name: frm.doc.name,
                format: "SI JSI", no_letterhead: "0"});
            window.open(`/printview?${query.toString()}`, "_blank", "noopener");
        }, __("View"));
    }
});
