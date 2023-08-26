// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee IR', {
	refresh(frm) {
		if (frm.doc.docstatus == 0 && !frm.doc.__islocal && frm.doc.type == "Receive" && frm.doc.is_qc_reqd) {
			frm.add_custom_button(__("Generate QC"), function() {
				frm.dirty()
				frm.save()
			})
		}
	},
	setup(frm) {
		frm.set_query("operation", function() {
			return {
				filters: {
					"is_subcontracted": frm.doc.subcontracting == "Yes"
				}
			}
		})
		frm.set_query("main_slip", function(doc) {
			return {
				filters: {
					"docstatus": 0,
					"employee": frm.doc.employee,
					"for_subcontracting": frm.doc.subcontracting == "Yes"
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
			var filters={
				department: frm.doc.department,
				operation: ["is", "not set"],
			}
			if (doc.subcontracting == "Yes") {
				filters["employee"] = ["is","not set"]
			}
			else {
				filters["subcontractor"] = ["is","not set"]
			}

			return {
				filters: filters
			}
		})
		frm.set_query("subcontractor", function() {
			return {
				filters: [["Operation MultiSelect", "operation", "=", frm.doc.operation]]
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
			if (frm.doc.subcontracting == "Yes") {
				query_filters["employee"] = ["is","not set"]
			}
			else {
				query_filters["subcontractor"] = ["is","not set"]
			}
		}
		else {
			query_filters["status"] = ["in", ["On Hold", "WIP", "QC Completed"]]
			query_filters["operation"] = frm.doc.operation
			if (frm.doc.employee) query_filters["employee"] = frm.doc.employee
			if (frm.doc.subcontractor && frm.doc.subcontracting == "Yes") query_filters["subcontractor"] = frm.doc.subcontractor
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
			size: "extra-large"
		})
	}
});