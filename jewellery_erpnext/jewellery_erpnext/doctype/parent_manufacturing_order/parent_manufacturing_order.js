// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Parent Manufacturing Order', {
	setup(frm) {
		var parent_fields = [['diamond_grade', 'Diamond Grade'], ['metal_colour', 'Metal Colour'], ['metal_purity', 'Metal Purity']];
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
	},
	// onload(frm){
	// 	if (cur_frm.doc.weight_details.length ==0 && cur_frm.doc.docstatus == 0){
	// 		frappe.call({
	// 			method: 'jewellery_erpnext.jewellery_erpnext.doctype.parent_manufacturing_order.parent_manufacturing_order.get_weight',
	// 			args: {
	// 				'master_bom': cur_frm.doc.master_bom,
	// 			},
	// 			callback: function(r) {
	// 				if (!r.exc) {
	// 					for (var i = 0; i < r.message.length; i++) {
	// 						let row = frm.add_child('weight_details', {
	// 							weight_label: r.message[i][0],
	// 							from_tolerance_weight: r.message[i][1],
	// 							to_tolerance_weight: r.message[i][2] 
	// 						});
	// 					}
	// 					frm.refresh_field('weight_details');
	// 				}
	// 			}
	// 		});
	// 	}
	// }
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