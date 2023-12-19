// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Metal Conversion', {
    setup: function(frm) {
        let metal_fields = [['to_metal_touch','Metal Touch']]
        set_filters_on_fields(frm, metal_fields, "metal_criteria");
        frm.set_query("to_purity", function(r) {
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {'item_attribute': "Metal Purity", "metal_touch":frm.doc.to_metal_touch}
            }
        })
        
    },

    refresh: function(frm) {
        frm.set_value("company", "")
        frm.set_value("department", "")
        frm.set_value("customer_received_voucher", "")
        frm.set_value("batch_no", "")
        frm.set_value("metal_type", "")
        frm.set_value("base_purity", "")
        frm.set_value("base_metal_wt", "")
        frm.set_value("total_weight", "")
        frm.set_value("making_type", "")
        frm.set_value("manager", "")
        frm.set_value("mix_metal", "")
        frm.set_value("to_purity", "")
        frm.set_value("to_metal_touch", "")
        frm.set_value("mix_weight", "")
        frm.set_value("wastage_per", "")
        frm.set_value("wastage_wt", "")
        frm.set_value("total_received_wt", "")
        frm.set_value("item_details", "")
        frm.set_value("base_metal_touch", "")

        set_html(frm)

        frm.set_query("batch_no", function() {
            return {
                filters: {
                    "reference_doctype": "Stock Entry",
                    "reference_name": frm.doc.customer_received_voucher
                }
            };
        })
    },

    company: function(frm) {
        frm.set_query("department", function() {
            return {
                filters: {
                    "company": frm.doc.company
                }
            };
        })
    },

    customer_received_voucher: function(frm) {
        set_html(frm)
        frappe.call({ 
            method: "get_itm_det",
            doc: frm.doc,
            callback: function (r) {
                frm.set_value("batch_no", r.message.batch_no)
                frm.refresh_fields('batch_no')
                frm.set_value("metal_type", r.message.metal_type)
                frm.refresh_fields('metal_type')
                frm.set_value("base_purity", r.message.metal_purity)
                frm.refresh_fields('base_purity')
                frm.set_value("base_metal_wt", r.message.metal_wt)
                frm.refresh_fields('base_metal_wt')
                frm.set_value("total_weight", r.message.metal_wt)
                frm.refresh_fields('total_weight')
                frm.set_value("base_metal_touch", r.message.metal_touch)
                frm.refresh_fields('base_metal_touch')
            } 
        })
    },

    department: function(frm) {
        frappe.call({
            method: "set_warehouse_filter",
            doc: frm.doc,
            callback: function(r) {
                frm.set_query("customer_received_voucher", function() {
                    return {
                        filters: {
                            "stock_entry_type": "Customer Goods Received",
                            "t_warehouse": ["in", r.message],
                            "docstatus": 1
                        }
                    };
                })
            }
        })
    },

    // to_purity: function(frm) {
    //     frappe.call({ 
    //         method: "calculate_total_rcv_wt",
    //         doc: frm.doc,
    //         callback: function (r) {
    //             frm.set_value("total_received_wt", r.message)
    //             frm.refresh_fields('total_received_wt')
    //         } 
    //     })
    // }

});

function set_html(frm) {
    if (frm.doc.customer_received_voucher) {
        frappe.call({ 
            method: "get_linked_item_details",
            doc: frm.doc,
            callback: function (r) { 
                frm.get_field("item_details").$wrapper.html(r.message) 
            } 
        })
    }
    else {
        frm.get_field("item_details").$wrapper.html("")
    }
}


function set_filters_on_fields(frm, fields) {
    fields.map(function(field){
        frm.set_query(field[0], function() {
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: {'item_attribute': field[1]}
            }
        })
    })
}