// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('QC', {
	setup: function(frm) {
		frm.set_query("manufacturing_operation", function(doc) {
			return {
				filters: {
					"manufacturing_work_order": frm.doc.manufacturing_work_order
				}
			}
		})
	}
});
