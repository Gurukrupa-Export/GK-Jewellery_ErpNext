// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manufacturing Operation', {
	refresh: function(frm) {
		set_html(frm)
		if (frm.doc.is_last_operation && frm.doc.for_fg && in_list(["Not Started", "WIP"],frm.doc.status)) {
			frm.add_custom_button(__("Finish"), ()=>{
				frm.set_value("status", "Finished")
				frm.save()
				frm.call("create_fg")
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
					frm.set_value("status", "WIP")
					frm.save()
				})
			}
		}
	},
});

function set_html(frm) {
	if (!frm.doc.__islocal) {
		//ToDo: add function for stock entry detail for normal manufacturing operations
	}
	else {
		frm.get_field("stock_entry_details").$wrapper.html("")
	}
	if (frm.doc.is_last_operation) {
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
}