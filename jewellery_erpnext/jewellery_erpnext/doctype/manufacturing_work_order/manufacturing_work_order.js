// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manufacturing Work Order', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && in_list(["In Process", "Not Started"],frm.doc.status)) {
			frm.add_custom_button("Split Work Order", function() {
                frm.trigger("split_work_order")
			})
		}
        set_html(frm);
	},
	split_work_order: function (frm) {
        const dialog = new frappe.ui.Dialog({
            title: __("Update"),
            fields: [
                {
                    fieldname: "split_count",
                    fieldtype: "Int",
                    label: "Split Into",
                },
            ],
            primary_action: function () {
                frappe.call({
                    method: 'jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_work_order.manufacturing_work_order.create_split_work_order',
                    freeze: true,
                    args: {
                        "docname": frm.doc.name,
                        "company": frm.doc.company,
                        "count": dialog.get_values()["split_count"]
                    },
                    callback: function (r) {
                        frm.reload_doc();
                    }
                });
                dialog.hide();
            },
            primary_action_label: __('Submit')
        });
        dialog.show()
        // dialog.$wrapper.find('.modal-dialog').css("max-width", "90%");
    }
});
function set_html(frm) {
	if (!frm.doc.__islocal && frm.doc.is_last_operation) {
	}
	else {
		frm.get_field("stock_entry_details").$wrapper.html("")
	}
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