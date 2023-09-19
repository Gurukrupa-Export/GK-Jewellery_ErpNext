// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manufacturing Setting', {
	setup: function(frm) {
		frm.set_query("default_department", function(){
			return {
				filters: {
					"company": frm.doc.company
				}
			}
		})
		frm.set_query("in_transit", function(){
			return {
				filters: {
					"company": frm.doc.company
				}
			}
		})
	}
});
