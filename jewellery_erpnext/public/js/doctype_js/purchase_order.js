frappe.ui.form.on('Purchase Order', {
    onload:function(frm){
        var fields = [['custom_metal_purity','Metal Purity']];
        set_filters_on_child_table_fields(frm, fields);
    }
})

frappe.ui.form.on('Purchase Order Item', {
    custom_rate_99_9:function(frm, cdt, cdn){
    		var row = locals[cdt][cdn]
    		row.custom_rate_99_5 = (row.custom_rate_99_9*99.5)/100
    		refresh_field("items");
    	},
	custom_rate_99_5:function(frm, cdt, cdn){
		var row = locals[cdt][cdn]
		row.custom_rate_99_9 = (row.custom_rate_99_5*100)/99.5
		refresh_field("items");
	},
	item_code:function(frm,cdt,cdn){
		if (frm.doc.supplier){
			var supplier = frm.doc.supplier
		}
		else{
			var supplier = 'None'
		}
		var row = locals[cdt][cdn]
		frappe.call({
// 			method: 'get_metal_purity',
			method: 'jewellery_erpnext.jewellery_erpnext.doc_events.purchase_order.get_supplier_details',
			args: {
				'item_code': row.item_code,
				'supplier':supplier
			},
			callback: function(r) {
				if (!r.exc) {
					row.custom_wastages = r.message
					refresh_field("items");
				}
			}
		});
	},
	custom_metal_purity:function(frm,cdt,cdn){
		var row = locals[cdt][cdn]
		row.rate = (row.custom_rate_99_9*row.custom_wastages)/100 + (row.custom_rate_99_9*row.custom_metal_purity)/100
		refresh_field("items");
	}
})

function set_filters_on_child_table_fields(frm, fields) {
			fields.map(function (field) {
			frm.set_query(field[0], "items", function () {
				return {
					query: 'jewellery_erpnext.query.item_attribute_query',
					filters: { 'item_attribute': field[1] }
				};
			});
		});
}