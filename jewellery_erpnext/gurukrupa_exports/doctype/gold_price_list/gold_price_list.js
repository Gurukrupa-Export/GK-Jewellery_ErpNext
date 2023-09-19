// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gold Price List', {
	onload(frm) {
		if (cur_frm.doc.docstatus == 0){
			frappe.call({
				method: 'jewellery_erpnext.gurukrupa_exports.doctype.gold_price_list.gold_price_list.get_gold_price',
				callback: function(r) {
					if (!r.exc) {
						cur_frm.clear_table('gold_mrp_price_details');
						console.log(r.message)
						cur_frm.set_value('usd_per_ounce',r.message[1]);
						var arrayLength = r.message[0].length;
						console.log(arrayLength)
						for (var i = 0; i < arrayLength; i++) {
							console.log(r.message[i]);
							let row = frm.add_child('gold_mrp_price_details', {
								metal_touch:r.message[0][i][0],
								metal_purity:r.message[0][i][1],
								dollor:r.message[0][i][2],
							});
						}
						frm.refresh_field('gold_mrp_price_details');
					}
				}
			});
		}
		
	},
});
