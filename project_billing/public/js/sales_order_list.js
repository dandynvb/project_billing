// Preserve ERPNext's native indicator (To Deliver/To Bill/Completed).
(() => {
    const settings = frappe.listview_settings["Sales Order"] || {};
    settings.add_fields = [...new Set([...(settings.add_fields || []),
        "custom_pb_enabled", "custom_pb_payment_status", "custom_pb_outstanding_total"
    ])];
    frappe.listview_settings["Sales Order"] = settings;
})();
