// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee IR', {
	setup(frm) {
		frm.set_query("main_slip", function(doc) {
			return {
				filters: {
					"docstatus": 0,
					"employee": frm.doc.employee
				}
			}
		})
		frm.set_query("employee", function(doc) {
			return {
				filters: {
					"department": frm.doc.department
				}
			}
		})
		frm.set_query("manufacturing_operation","employee_ir_operations", function(doc, cdt,cdn) {
			return {
				filters: {
					department: frm.doc.department,
					operation: ["is", "not set"],
					employee: ["is","not set"]
				}
			}
		})
	},
	type(frm) {
		frm.clear_table("department_ir_operation")
		frm.refresh_field("department_ir_operation")
	},
	get_operations(frm) {
		var query_filters = {
			"department": frm.doc.department
		}
		if (frm.doc.type == "Issue") {
			query_filters["status"] = ["in", ["Not Started"]]
			query_filters["operation"] = ["is", "not set"]
			query_filters["employee"] = ["is", "not set"]
		}
		else {
			query_filters["status"] = ["in", ["On Hold", "WIP", "QC"]]
			query_filters["operation"] = frm.doc.operation
			if (frm.doc.employee) query_filters["employee"] = frm.doc.employee
		}
		erpnext.utils.map_current_doc({
			method: "jewellery_erpnext.jewellery_erpnext.doctype.employee_ir.employee_ir.get_manufacturing_operations",
			source_doctype: "Manufacturing Operation",
			target: frm,
			setters: {
				company: frm.doc.company || undefined,
				department: frm.doc.department,
				manufacturer: frm.doc.manufacturer || undefined,
				manufacturing_work_order: undefined,
			},
			get_query_filters: query_filters,
			size: "large"
		})
	}
});
