// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Parent Manufacturing Order', {
	setup(frm) {
		filter_departments(frm,"diamond_department")
		filter_departments(frm,"gemstone_department")
		filter_departments(frm,"finding_department")
		filter_departments(frm,"other_material_department")
		filter_departments(frm,"metal_department")
		var parent_fields = [['diamond_grade', 'Diamond Grade'], ['metal_colour', 'Metal Colour'], ['metal_purity', 'Metal Purity']];
		set_filters_on_parent_table_fields(frm, parent_fields);
	},
	refresh(frm){
		if (!frm.doc.__islocal) {
			frm.set_df_property('diamond_grade', 'reqd', 1)
		}
		set_html(frm);
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

function filter_departments(frm,field_name){
	frm.set_query(field_name, function(){
		return {
			filters: {
				"company": frm.doc.company
			}
		}
	})
}

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
function set_html(frm) {
	frappe.call({ 
		method: "get_stock_summary",
		doc: frm.doc,
		args: { 
			"docname": frm.doc.name,
		}, 
		callback: function (r) { 
			frm.get_field("stock_summery").$wrapper.html(r.message) 
		} 
	})

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