// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee IR', {
	refresh(frm) {
		if (frm.doc.docstatus == 0 && !frm.doc.__islocal && frm.doc.type == "Receive" && frm.doc.is_qc_reqd) {
			frm.add_custom_button(__("Generate QC"), function () {
				frm.dirty()
				frm.save()
			})
		}
	},
	setup(frm) {
		frm.set_query("operation", function () {
			return {
				filters: [
                    ["Department Operation", "department", "=", cur_frm.doc.department],
                    ["Department Operation", "is_subcontracted", "=", frm.doc.subcontracting == "Yes"],
                ]
			}
		});
		frm.set_query("department", function(){
            return {
                "filters": [
                    ["Department", "company", "=", cur_frm.doc.company],
                ]
            }
        });
		frm.set_query("main_slip", function (doc) {
			return {
				filters: {
					"docstatus": 0,
					"employee": frm.doc.employee,
					"for_subcontracting": frm.doc.subcontracting == "Yes"
				}
			}
		})
		frm.set_query("employee", function (doc) {
			return {
				filters: {
					"department": frm.doc.department,
					"custom_operation": frm.doc.operation
				}
			}
		})
		frm.set_query("manufacturing_operation", "employee_ir_operations", function (doc, cdt, cdn) {
			var filters = {
				department: frm.doc.department,
				operation: ["is", "not set"],
			}
			if (doc.subcontracting == "Yes") {
				filters["employee"] = ["is", "not set"]
			}
			else {
				filters["subcontractor"] = ["is", "not set"]
			}

			return {
				filters: filters
			}
		})
		frm.set_query("subcontractor", function () {
			return {
				filters: [["Operation MultiSelect", "operation", "=", frm.doc.operation]]
			}
		})
		var parent_fields = [['custom_transfer_type', 'Employee IR Reason']];
		set_filters_on_parent_table_fields(frm, parent_fields);
	},
	
	type(frm) {
		frm.clear_table("department_ir_operation")
		frm.refresh_field("department_ir_operation")		
	},
	// scan_mop(frm) {
	// 	if (frm.doc.scan_mop) {
	// 		var query_filters = {
	// 			"department": frm.doc.department,
	// 			"name": frm.doc.scan_mop
	// 		}
	// 		if (frm.doc.type == "Issue") {
	// 			query_filters["status"] = ["in", ["Not Started"]]
	// 			query_filters["operation"] = ["is", "not set"]
	// 			query_filters["department_ir_status"] = ["=", "Received"]

	// 			if (frm.doc.subcontracting == "Yes") {
	// 				query_filters["employee"] = ["is","not set"]
	// 			}
	// 			else {
	// 				query_filters["subcontractor"] = ["is","not set"]
	// 			}
	// 		}
	// 		else {
	// 			query_filters["status"] = ["in", ["On Hold", "WIP", "QC Completed"]]
	// 			query_filters["operation"] = frm.doc.operation
	// 			if (frm.doc.employee) query_filters["employee"] = frm.doc.employee
	// 			if (frm.doc.subcontractor && frm.doc.subcontracting == "Yes") query_filters["subcontractor"] = frm.doc.subcontractor
	// 		}

	// 		frappe.db.get_value('Manufacturing Operation', query_filters, ['name', 'manufacturing_work_order', 'status'])
	// 			.then(r => {
	// 				let values = r.message;
	// 				if (values.manufacturing_work_order) {
	// 					let row = frm.add_child('employee_ir_operations', {
	// 						"manufacturing_work_order": values.manufacturing_work_order,
	// 						"manufacturing_operation": values.name,
	// 						// "status":values.status
	// 					});
	// 					frm.refresh_field('employee_ir_operations');
	// 				}
	// 				else {
	// 					frappe.throw('Invalid Manufacturing Operation')
	// 				}
	// 				frm.set_value('scan_mop', "")
	// 			})
	// 	}
	// },
	scan_mwo(frm) {
		if (frm.doc.scan_mwo) {
			var query_filters = {
				"department": frm.doc.department,
				"manufacturing_work_order": frm.doc.scan_mwo
			}
			if (frm.doc.type == "Issue") {
				query_filters["status"] = ["in", ["Not Started"]]
				query_filters["operation"] = ["is", "not set"]
				// query_filters["department_ir_status"] = ["=", "Received"]

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
		
			frappe.db.get_value('Manufacturing Operation', query_filters, ['name', 'manufacturing_work_order', 'status'])
				.then(r => {
					let values = r.message;
					
					if (values.manufacturing_work_order) {
						let row = frm.add_child('employee_ir_operations', {
							"manufacturing_work_order": values.manufacturing_work_order,
							"manufacturing_operation": values.name,
							// "status":values.status
						});
						frm.refresh_field('employee_ir_operations');
					}
					else {
						frappe.throw('No Manufacturing Operation Found')
					}
					frm.set_value('scan_mwo', "")
				})
		}
	},
	get_operations(frm) {
		var query_filters= {
			"department": frm.doc.department,
		};
		if (frm.doc.main_slip == null)
		{
			if (frm.doc.type == "Issue") {
				query_filters["status"] = ["in", ["Not Started"]];
				query_filters["operation"] = ["is", "not set"];
	
				if (frm.doc.subcontracting == "Yes") {
					query_filters["employee"] = ["is", "not set"];
				} else {
					query_filters["subcontractor"] = ["is", "not set"];
				}
			} else {
				query_filters["status"] = ["in", ["On Hold", "WIP", "QC Completed"]];
				query_filters["operation"] = frm.doc.operation;
	
				if (frm.doc.employee) query_filters["employee"] = frm.doc.employee;
				if (frm.doc.subcontractor && frm.doc.subcontracting == "Yes") query_filters["subcontractor"] = frm.doc.subcontractor;
			}
	
			erpnext.utils.map_current_doc({
				method: "jewellery_erpnext.jewellery_erpnext.doctype.employee_ir.employee_ir.get_manufacturing_operations",
				source_doctype: "Manufacturing Operation",
				slip: frm.doc.main_slip,
				target: frm,
				setters: {
					manufacturing_work_order: undefined,
					company: frm.doc.company || undefined,
					department: frm.doc.department,
					manufacturer: frm.doc.manufacturer || undefined,
				
				},
				get_query_filters: query_filters,
				size: "extra-large"
			});	
		}
		else{

			frappe.db.get_value("Main Slip", frm.doc.main_slip, ["metal_colour", "metal_purity"])
			.then(r => {
				var metal_colour = r.message.metal_colour;
				var metal_purity = r.message.metal_purity;
	
			if (frm.doc.type == "Issue") {
				query_filters["status"] = ["in", ["Not Started"]];
				query_filters["operation"] = ["is", "not set"];
	
				if (frm.doc.subcontracting == "Yes") {
					query_filters["employee"] = ["is", "not set"];
				} else {
					query_filters["subcontractor"] = ["is", "not set"];
				}
			} else {
				query_filters["status"] = ["in", ["On Hold", "WIP", "QC Completed"]];
				query_filters["operation"] = frm.doc.operation;
	
				if (frm.doc.employee) query_filters["employee"] = frm.doc.employee;
				if (frm.doc.subcontractor && frm.doc.subcontracting == "Yes") query_filters["subcontractor"] = frm.doc.subcontractor;
			}
	
			erpnext.utils.map_current_doc({
				method: "jewellery_erpnext.jewellery_erpnext.doctype.employee_ir.employee_ir.get_manufacturing_operations",
				source_doctype: "Manufacturing Operation",
				slip: frm.doc.main_slip,
				target: frm,
				setters: {
					manufacturing_work_order: undefined,
					company: frm.doc.company || undefined,
					department: frm.doc.department,
					manufacturer: frm.doc.manufacturer || undefined,
					metal_purity: metal_purity || undefined,
					metal_colour: metal_colour|| undefined
				},
				get_query_filters: query_filters,
				size: "extra-large"
			});	
		})
		}
		}
});
function set_filters_on_parent_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1] }
			};
		});
	});
}
frappe.ui.form.on('Employee IR Operation', {
    received_gross_wt: function (frm, cdt, cdn) {
        var child = locals[cdt][cdn];
		// console.log(child.manufacturing_operation);
		if (frm.doc.type == "Issue"){
			frappe.throw("Transaction type must be a <b>Receive</b>")
		}
        if (child.received_gross_wt && frm.doc.type == "Receive") {
			var mwo = child.manufacturing_work_order;
			var gwt = child.gross_wt;
			var opt = child.manufacturing_operation
			var r_gwt = child.received_gross_wt;
			frappe.db.get_value("Manufacturing Work Order", mwo, ['multicolour','allowed_colours'])
				.then(r => {
					console.log(r.message);
					if (r.message.multicolour == 1){
						book_loss_details(frm,mwo,opt,gwt,r_gwt);
					}
				})
        }
    }
});

function book_loss_details(frm,mwo,opt,gwt,r_gwt) {
	if(gwt == r_gwt){
		frm.clear_table("employee_loss_details");
		frm.refresh_field("employee_loss_details");
		frm.save()
	}
	frappe.call({
		method: "jewellery_erpnext.jewellery_erpnext.doctype.employee_ir.employee_ir.book_metal_loss",
		args: {
			doc_name: frm.doc.name,
			mwo:mwo,
			mwo:mwo,
			opt:opt,
			gwt:gwt,
			r_gwt:r_gwt
		},
		callback: function(r) {
			if (r.message) {
				frm.clear_table("employee_loss_details");
				var r_data = r.message[0]
				for (var i = 0; i < r_data.length; i++) {
                    var child = frm.add_child("employee_loss_details");
                    child.item_code = r_data[i].item_code;
                    child.net_weight = r_data[i].qty;
					child.stock_uom = r_data[i].stock_uom;
					child.manufacturing_work_order = r_data[i].manufacturing_work_order;
					child.proportionally_loss = r_data[i].proportionally_loss;
					child.received_gross_weight = r_data[i].received_gross_weight;
					child.main_slip_consumption = r_data[i].main_slip_consumption;
                }
				frm.set_value("mop_loss_details_total",r.message[1])
                frm.refresh_field("employee_loss_details","mop_loss_details_total");
			}
		}
	})
}