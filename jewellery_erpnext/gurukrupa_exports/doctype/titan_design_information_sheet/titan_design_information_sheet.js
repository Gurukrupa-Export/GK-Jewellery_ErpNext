// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Titan Design Information Sheet', {
	refresh: function(frm) {
		var parent_fields = [
								['enamel', 'Enamal'],
								['rhodium', 'Rhodium'],
								['chain_type', 'Chain Type'],
								['metal_type', 'Metal Type'],
								['metal_touch', 'Metal Touch'],
								['metal_colour', 'Metal Colour'],
								['metal_purity', 'Metal Purity'],
								['item_category','Titan Item Category'],
								['item_subcategory','Item Subcategory'],
								// ['collection','Collection'],
								['setting_type','Sub Setting Type'],
								['finding_type','Finding Sub-Category'],
							];
		set_filters_on_parent_table_fields(frm, parent_fields);

		frm.set_query("design_code", function(){
			return {
				"filters": [
					["Item", "is_design_code", "=", 1],
				]
			}
		});
		
		frm.set_query("metal_type", function(){
			return {
				"filters": [
					["Attribute Value", "name", "in", ["Gold","Silver","Platinum"]],
				]
			}
		});

		frm.set_query('metal_purity', function () {
			return {
				filters: {
					// 'is_metal_purity': 1,
					'metal_touch':cur_frm.doc.metal_touch
				}
			};
		});

		frm.set_query('item_subcategory', function () {
			return {
				filters: {
					'parent_attribute_value':cur_frm.doc.item_category
				}
			};
		});

	},
	design_code:function(frm) {
		const arr = []
		frappe.db.get_value("Titan Design Information Sheet", {"design_code": frm.doc.design_code}, "design_code", (r)=> {
			if (r.design_code){
				arr.push(r.design_code)
				frm.set_value('design_code','')
				frappe.throw(`<b>${arr[0]}</b> already available`)
			}   
		})
		// frm.set_value('serial_no','')
	}
});



function set_filters_on_parent_table_fields(frm, fields) {
	fields.map(function (field) {
		frm.set_query(field[0], function (doc) {
			return {
				query: 'jewellery_erpnext.query.item_attribute_query',
				filters: { 'item_attribute': field[1]}
			};
		});
	});
}


