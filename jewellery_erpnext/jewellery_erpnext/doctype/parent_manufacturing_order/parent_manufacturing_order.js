// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Parent Manufacturing Order', {
	setup(frm) {
		var parent_fields = [['diamond_grade', 'Diamond Grade'], ['metal_color', 'Metal Colour'], ['metal_purity', 'Metal Purity']];
		set_filters_on_parent_table_fields(frm, parent_fields);
	},
	sales_order_item: function (frm) {
		frappe.call({
			method: "jewellery_erpnext.jewellery_erpnext.doctype.production_order.production_order.get_item_code",
			args: {
				'sales_order_item': frm.doc.sales_order_item
			},
			type: "GET",
			callback: function (r) {
				console.log(r.message)
				frm.doc.item_code = r.message
				frm.set_value('item_code', r.message)
				refresh_field('item_code')
				frm.trigger('item_code')
			}
		})
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