// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manufacturing Operation', {
	refresh: function(frm) {
		set_html(frm)
	}
});

function set_html(frm) {
	if (!frm.doc.__islocal) {
		frappe.call({ 
			method: "jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_operation.manufacturing_operation.get_linked_stock_entries",
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
}