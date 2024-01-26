// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manufacturing Operation', {
	refresh: function(frm) {
		set_html(frm)
		if (frm.doc.is_last_operation && frm.doc.for_fg && in_list(["Not Started", "WIP"],frm.doc.status)) {
			frm.add_custom_button(__("Finish"), async ()=>{
				await frappe.call({ 
					method: "get_linked_stock_entries_for_serial_number_creator",
					doc: frm.doc,
					args: { 
						"docname": frm.doc.name,
					}, 
					callback: function (r) { 
						frappe.call({
							method:"jewellery_erpnext.jewellery_erpnext.doctype.serial_number_creator.serial_number_creator.get_operation_details",
							// doc:doc.name,
							args:{
								"data":r.message,
								"docname":frm.doc.name,
								"mwo":frm.doc.manufacturing_work_order,
								"pmo":frm.doc.manufacturing_order,
								"company":frm.doc.company,
								"mnf":frm.doc.manufacturer,
								"dpt":frm.doc.department,
								"for_fg":frm.doc.for_fg,
								"design_id_bom":frm.doc.design_id_bom,
							},
						})
					} 
				})
				
				// await frm.call("create_fg")
				// frm.set_value("status", "Finished")
				// frm.save()
			}).addClass("btn-primary")
		}
		if (!frm.doc.__islocal) {
			if (!in_list(["Finished", "On Hold"],frm.doc.status)) {
				frm.add_custom_button(__("On Hold"), ()=>{
					frm.set_value("status", "On Hold")
					frm.save()
				})
			}
			if (in_list(["On Hold"],frm.doc.status)) {
				frm.add_custom_button(__("Resume"), ()=>{
					frm.set_value("status", (frm.doc.employee || frm.doc.subcontractor)? "WIP": "Not Started")
					frm.save()
				})
			}
		}
	},
	setup(frm) {
		frm.set_query("item_code", "loss_details", function(doc, cdt, cdn) {
			return {
			  query: 'jewellery_erpnext.query.get_scrap_items',
			  filters: {'manufacturing_operation': doc.name}
			}
		  })
	},
});

function set_html(frm) {
	if (!frm.doc.__islocal && frm.doc.is_last_operation) {
		//ToDo: add function for stock entry detail for normal manufacturing operations
		frappe.call({ 
			method: "get_linked_stock_entries",
			doc: frm.doc,
			args: { 
				"docname": frm.doc.name,
			}, 
			callback: function (r) { 
				frm.get_field("stock_entry_details").$wrapper.html(r.message) 
			} 
		})
	}
	else {
		frm.get_field("stock_entry_details").$wrapper.html("")
	}
	// if (frm.doc.is_last_operation) {
		
	// }
}