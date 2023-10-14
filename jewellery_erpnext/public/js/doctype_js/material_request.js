frappe.ui.form.on('Material Request', {
    refresh(frm) {
        frm.trigger("get_items_from_customer_goods")
    },
	validate(frm) {
		$.each(frm.doc.items || [], function(i, d) {
		    d.custom_insurance_amount = flt(d.custom_insurance_rate) * flt(d.qty)
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