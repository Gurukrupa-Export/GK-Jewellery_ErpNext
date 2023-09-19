// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Refining', {
	get_parent_production_order(frm) {
		var query_filters = {
			"department": frm.doc.department
		}
		if (frm.doc.refining_type == "Parent Manufacturing Order") {
			query_filters["status"] = ["in", ["Not Started"]]
			// query_filters["operation"] = ["is", "not set"]
			// else {
			// 	query_filters["subcontractor"] = ["is", "not set"]
			// }
		}
		// else {
		// 	query_filters["status"] = ["in", ["On Hold", "WIP", "QC Completed"]]
		// 	query_filters["operation"] = frm.doc.operation
		// 	if (frm.doc.employee) query_filters["employee"] = frm.doc.employee
		// 	if (frm.doc.subcontractor && frm.doc.subcontracting == "Yes") query_filters["subcontractor"] = frm.doc.subcontractor
		// }
		erpnext.utils.map_current_doc({
			method: "jewellery_erpnext.jewellery_erpnext.doctype.refining.refining.get_manufacturing_operations",
			source_doctype: "Manufacturing Work Order",
			target: frm,
			setters: {
				// manufacturing_work_order: undefined,
				company: frm.doc.company || undefined,
				department: frm.doc.department || undefined,
				manufacturing_order: undefined,
			},
			get_query_filters: query_filters,
			size: "extra-large",
		})
	}
});