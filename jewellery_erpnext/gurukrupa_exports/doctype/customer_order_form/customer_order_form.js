// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Order Form', {
	titan_code(frm){
		if (cur_frm.doc.titan_code){
			frappe.call({
				method: 'jewellery_erpnext.gurukrupa_exports.doctype.titan_order_form.titan_order_form.set_customer_code_logic',
				args: {
					'titan_code': cur_frm.doc.titan_code,
					'customer_code': cur_frm.doc.customer_code,
				},
				callback: function(r) {
					if (!r.exc) {
						console.log(r.message)
						frm.set_value('metal_type',r.message['metal_type'])
						frm.set_value('metal_colour',r.message['metal_colour'])
						frm.set_value('metal_touch',r.message['metal_touch'])
						frm.set_value('productivity',r.message['productivity'])
						frm.set_value('design_code',r.message['design_code'])
						frm.set_value('product_size',r.message['size_data'])
						frm.set_value('chain',r.message['chain'])
						frm.set_value('stone',r.message['stone_data'])
						frm.set_value('finding',r.message['finding_data'])
						frm.set_value('enamal',r.message['enamal'])
						frm.set_value('rhodium',r.message['rhodium'])
						frm.set_value('diamond_quality',r.message['diamond_quality'])
						frm.set_value('product_size',r.message['size'])
						frm.set_value('qty',r.message['qty'])
						// frm.set_value('gemstone_type',r.message['stone_type'])stone
						// frm.set_value('gemstone_quality',r.message['stone_quality'])

					}
				}
			});
		}
		else{
			frm.set_value('metal_type','')
			frm.set_value('metal_colour','')
			frm.set_value('metal_touch','')
			frm.set_value('metal_purity','')
			frm.set_value('design_code','')
			frm.set_value('product_size','')
			frm.set_value('stone','')
			frm.set_value('finding','')
			// frm.set_value('gemstone_type','')
			// frm.set_value('gemstone_quality','')
		}	
	}
});
