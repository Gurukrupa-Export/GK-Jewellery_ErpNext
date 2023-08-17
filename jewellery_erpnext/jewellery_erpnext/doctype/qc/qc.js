// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt
cur_frm.cscript.refresh = cur_frm.cscript.inspection_type;

frappe.ui.form.on('QC', {
	refresh: function(frm) {
		// Ignore cancellation of reference doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = ["Manufacturing Work Order", "Manufacturing Operation"];
		if (frm.doc.docstatus == 0 && frm.doc.status == 'Pending') {
			frm.add_custom_button("Start QC", function() {
				frm.set_value({"status":"WIP", "start_time": frappe.datetime.now_datetime()})
				frm.save()
			})
		}
	},
	setup: function(frm) {
		frm.set_query("manufacturing_operation", function(doc) {
			return {
				filters: {
					"manufacturing_work_order": frm.doc.manufacturing_work_order
				}
			}
		})
	},
	quality_inspection_template: function(frm) {
		if (frm.doc.quality_inspection_template) {
			return frm.call({
				method: "get_specification_details",
				doc: frm.doc,
				callback: function() {
					refresh_field('readings');
				}
			});
		}
	},
});
