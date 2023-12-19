// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Department IR', {
	setup: function (frm) {
		frm.set_query("receive_against", function (doc) {
			return {
				filters: {
					current_department: frm.doc.previous_department,
					next_department: frm.doc.current_department
				},
				query: "jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir.department_receive_query"
			}
		})
		frm.set_query("current_department", department_filter(frm))
		frm.set_query("next_department", department_filter(frm))
		frm.set_query("previous_department", department_filter(frm))
		frm.set_query("manufacturing_operation", "department_ir_operation", function (doc, cdt, cdn) {
			var dir_status = frm.doc.type == "Receive" ? "In-Transit" : ["not in", ["In-Transit", "Received"]]
			var filter_dict = {
				"department_ir_status": dir_status
			}
			if (frm.doc.type == "Issue") {
				filter_dict["status"] = ["in", ["Finished", "Revert"]]
				filter_dict["department"] = frm.doc.current_department
			} else {
				if (frm.doc.receive_against) {
					filter_dict["department_issue_id"] = frm.doc.receive_against
				}
			}
			return {
				filters: filter_dict
			}
		})
	},
	// refresh:function(frm){
	// 	frm.add_custom_button(__('End Transit'), function() {
	// 		frappe.model.open_mapped_doc({
	// 			// method: "erpnext.stock.doctype.stock_entry.stock_entry.make_stock_in_entry",
	// 			method:"jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir.stock_entry_end_transit",
	// 			frm: frm,
	// 			args: {
	// 				doc: frm.doc.name
	// 			}
	// 		})
	// 	});
	// },
	type(frm) {
		frm.clear_table("department_ir_operation")
		frm.refresh_field("department_ir_operation")
	},
	receive_against(frm) {
		if (frm.doc.receive_against) {
			frappe.call({
				method: "jewellery_erpnext.utils.db_get_value",
				args: {
					doctype: "Department IR",
					docname: frm.doc.receive_against,
					fields: ["current_department", "next_department"]
				},
				callback(r) {
					var value = r.message
					frm.set_value({ "previous_department": value.current_department, "current_department": value.next_department })
				}
			})
			frappe.call({
				method: "jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir.get_manufacturing_operations_from_department_ir",
				args: {
					docname: frm.doc.receive_against
				},
				callback(r) {
					frm.clear_table("department_ir_operation")
					$.each(r.message || [], function (i, d) {
						frm.add_child("department_ir_operation", d)
					})
					frm.refresh_field("department_ir_operation")
				}
			})
		}
		else {
			frm.clear_table("department_ir_operation")
			frm.refresh_field("department_ir_operation")
		}
	},
	// scan_mop(frm) {
	// 	if (frm.doc.scan_mop) {
	// 		if (!frm.doc.current_department) {
	// 			frappe.throw("Please select current department first")
	// 		}
	// 		var query_filters = {
	// 			"company": frm.doc.company,
	// 			"name": frm.doc.scan_mop
	// 		}
	// 		if (frm.doc.type == "Issue") {
	// 			query_filters["department_ir_status"] = ["not in", ["In-Transit", "Revert"]]
	// 			query_filters["status"] = ["in", ["Not Started", "Finished"]]
	// 			query_filters["employee"] = ["is", "not set"]
	// 			query_filters["subcontractor"] = ["is", "not set"]
	// 		}
	// 		else {
	// 			query_filters["department_ir_status"] = "In-Transit"
	// 			query_filters["department"] = frm.doc.current_department
	// 		}

	// 		frappe.db.get_value('Manufacturing Operation', query_filters, ['name', 'manufacturing_work_order', 'status'])
	// 			.then(r => {
	// 				let values = r.message;
	// 				if (values.manufacturing_work_order) {
	// 					console.log(values.manufacturing_work_order)
	// 					let row = frm.add_child('department_ir_operation', {
	// 						"manufacturing_work_order": values.manufacturing_work_order,
	// 						"manufacturing_operation": values.name,
	// 						// "status":values.status
	// 					});
	// 					frm.refresh_field('department_ir_operation');
	// 				}
	// 				else {
	// 					frappe.throw('Invalid Manufacturing Operation')
	// 					console.log("values.manufacturing_work_order")
	// 				}
	// 				frm.set_value('scan_mop', "")
	// 			})
	// 	}
	// },
	scan_mwo(frm) {
		if (frm.doc.scan_mwo) {
			if (!frm.doc.current_department) {
				frappe.throw("Please select current department first")
			}
			var query_filters = {
				"company": frm.doc.company,
				"manufacturing_work_order": frm.doc.scan_mwo
			}
			if (frm.doc.type == "Issue") {
				query_filters["department_ir_status"] = ["not in", ["In-Transit", "Revert"]]
				query_filters["status"] = ["in", ["Not Started"]]
				query_filters["employee"] = ["is", "not set"]
				query_filters["subcontractor"] = ["is", "not set"]
			}
			else {
				query_filters["department_ir_status"] = "In-Transit"
				query_filters["department"] = frm.doc.current_department
			}

			frappe.db.get_value('Manufacturing Operation', query_filters, ['name', 'manufacturing_work_order', 'status'])
				.then(r => {
					let values = r.message;
					if (values.manufacturing_work_order) {
						console.log(values)
						let row = frm.add_child('department_ir_operation', {
							"manufacturing_work_order": values.manufacturing_work_order,
							"manufacturing_operation": values.name,
							// "status":values.status
						});
						frm.refresh_field('department_ir_operation');
					}
					else {
						frappe.throw('No Manufacturing Operation Found')
					}
					frm.set_value('scan_mwo', "")
				})
		}
	},
	get_operations(frm) {
		if (!frm.doc.current_department) {
			frappe.throw("Please select current department first")
		}
		var query_filters = {
			"company": frm.doc.company
		}
		if (frm.doc.type == "Issue") {
			query_filters["department_ir_status"] = ["not in", ["In-Transit", "Revert"]]
			query_filters["status"] = ["in", ["Not Started"]]
			query_filters["employee"] = ["is", "not set"]
			query_filters["subcontractor"] = ["is", "not set"]
		}
		else {
			query_filters["department_ir_status"] = "In-Transit"
			query_filters["department"] = frm.doc.current_department
		}
		erpnext.utils.map_current_doc({
			method: "jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir.get_manufacturing_operations",
			source_doctype: "Manufacturing Operation",
			target: frm,
			setters: {
				manufacturing_work_order: undefined,
				company: frm.doc.company || undefined,
				department: frm.doc.current_department
			},
			get_query_filters: query_filters,
			size: "extra-large"
		})
	}
});

var department_filter = function (frm) {
	return {
		filters: {
			"company": frm.doc.company
		}
	}
}

