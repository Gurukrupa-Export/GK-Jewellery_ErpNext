frappe.ui.form.on('Purchase Invoice', {
    refresh (frm) {
        // set_si_reference_field_filter()
        // get_items(frm)
    }
})

let set_si_reference_field_filter = () =>{
    cur_frm.set_query("si_reference_field", function() {
        return {
            'filters':{
                'sales_type': 'Branch Sales'
            }
        }
    })
}

let get_items = (frm) =>{
    /* Function to add custom button for sales invoice in get items and appending table with selected invoice items */
    frm.add_custom_button(__('Sales Invoice'), function () {
        let query_args = {
            filters: { docstatus: ["!=", 2], sales_type: 'Branch Sales' }
        }
        
        let d = new frappe.ui.form.MultiSelectDialog({
            doctype: "Sales Invoice",
            target: cur_frm,
            setters: {
                posting_date: null,
                status: 'Submitted'
            },
            add_filters_group: 1,
            date_field: "posting_date",
            get_query() {
                return query_args;
            },
            action(selections) {
                if (selections && selections.length) {
                    frappe.call({
                        method: 'jewellery_erpnext.utils.get_sales_invoice_items',
                        freeze: true,
                        args: {
                            sales_invoices: selections
                        },
                        callback: function (r) {
                            if (r && r.message && r.message.length) {
                                r.message.forEach(element => {
                                    frm.add_child('items', {
                                        'item_code': element.item_code,
                                        'qty': element.qty,
                                        'serial_no': element.serial_no
                                    })
                                    frm.refresh_fields('items')
                                });
                            }
                        }
                    })
                    d.dialog.hide();
                }
            }
        });
    }, __('Get Items From'));
}