frappe.ui.form.on('Material Request', {
    refresh(frm) {
        frm.trigger("get_items_from_customer_goods")
        if (frm.doc.material_request_type === 'Material Transfer') {

            frm.add_custom_button(__('Material Transfer (In Transit)'),
                () => frm.events.make_in_transit_stock_entry(frm), __('Create'));
        }
    },
    make_in_transit_stock_entry(frm) {
		frappe.prompt(
			[
				{
					label: __('In Transit Warehouse'),
					fieldname: 'in_transit_warehouse',
					fieldtype: 'Link',
					options: 'Warehouse',
					reqd: 1,
					get_query: () => {
						return{
							filters: {
								'company': frm.doc.company,
								'is_group': 0,
								'warehouse_type': 'Transit'
							}
						}
					}
				}
			],
			(values) => {
				frappe.call({
					method: "jewellery_erpnext.jewellery_erpnext.doc_events.material_request.make_in_transit_stock_entry",
					args: {
						source_name: frm.doc.name,
						in_transit_warehouse: values.in_transit_warehouse
					},
					callback: function(r) {
						if (r.message) {
							let doc = frappe.model.sync(r.message);
							frappe.set_route('Form', doc[0].doctype, doc[0].name);
						}
					}
				})
			},
			__('In Transit Transfer'),
			__('Create Stock Entry')
		)
	},
	validate(frm) {
		$.each(frm.doc.items || [], function(i, d) {
		    d.custom_insurance_amount = flt(d.custom_insurance_rate) * flt(d.qty)
            d.batch_no = d.custom_batch_no
            d.serial_no = d.custom_serial_no
		})
		frm.refresh_field("items")
	},
    get_items_from_customer_goods(frm) {
        console.log("test")
        if (frm.doc.docstatus===0) {
            frm.add_custom_button(__('Customer Goods Received'), function() {
                erpnext.utils.map_current_doc({
                    method: "jewellery_erpnext.jewellery_erpnext.doc_events.material_request.make_stock_in_entry",
                    source_doctype: "Stock Entry",
                    target: frm,
                    date_field: "posting_date",
                    setters: {
                        stock_entry_type: "Customer Goods Received",
                        purpose: "Material Receipt",
                        _customer: frm.doc._customer,
                        inventory_type: frm.doc.inventory_type
                    },
                    get_query_filters: {
                        docstatus: 1,
                        purpose: "Material Receipt",
                    },
    		    	size: "extra-large"

                })
            }, __("Get Items From"));
        }
        else {
            frm.remove_custom_button(__('Customer Goods Received'),__("Get Items From"))
        }
    },
})

frappe.ui.form.on('Material Request Item', {
    item_code(frm, cdt, cdn) {
        frm.trigger("custom_insurance_rate")
    },

	custom_insurance_rate(frm, cdt, cdn) {
		var d = locals[cdt][cdn]
		d.custom_insurance_amount = flt(d.custom_insurance_rate) * flt(d.qty)
		console.log(d.custom_insurance_amount)
		frm.refresh_field("items")
	}
})