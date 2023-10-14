// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Demo Dharm', {
	onload: function(frm) {
		frappe.call({
			method: 'jewellery_erpnext.gurukrupa_exports.doctype.demo_dharm.demo_dharm.get_time',
			args: {
				'from_time': cur_frm.doc.from_time,
				'to_time': cur_frm.doc.to_time,
				'employee': cur_frm.doc.employee,
			},
			callback: function(r) {
				if (!r.exc) {
					console.log(r.message)
					// frm.set_value('time_in_hours',r.message)
				}
			}
		});


	}
});
