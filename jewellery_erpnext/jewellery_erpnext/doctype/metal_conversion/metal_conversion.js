// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Metal Conversion', {
    // before_save: function(frm) {
    //     frm.set_value("department", "")
    //     frm.set_value("customer_received_voucher", "")
    //     frm.set_value("batch_no", "")
    //     frm.set_value("metal_type", "")
    //     frm.set_value("base_purity", "")
    //     frm.set_value("base_metal_wt", "")
    //     frm.set_value("total_weight", "")
    //     frm.set_value("making_type", "")
    //     frm.set_value("manager", "")
    //     frm.set_value("mix_metal", "")
    //     frm.set_value("to_purity", "")
    //     frm.set_value("mix_weight", "")
    //     frm.set_value("wastage_per", "")
    //     frm.set_value("wastage_wt", "")
    //     frm.set_value("total_received_wt", "")
    //     frm.set_value("item_details", "")
    //     // frm.refresh()
    //     frm.insert()
    // },

    refresh: function(frm) {
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
        frm.set_value("mix_weight", "")
        frm.set_value("wastage_per", "")
        frm.set_value("wastage_wt", "")
        frm.set_value("total_received_wt", "")
        frm.set_value("item_details", "")
        // frm.refresh()
        // frm.save()

        set_html(frm)
        frm.set_query("customer_received_voucher", function() {
            return {
                filters: {
                    "stock_entry_type": "Customer Goods Received"
                }
            };
        })
        frm.set_query("batch_no", function() {
            return {
                filters: {
                    "reference_doctype": "Stock Entry",
                    "reference_name": frm.doc.customer_received_voucher
                }
            };
        })
        // frm.set_query("metal_shape", function() {
        //  return {
        //      filters: {
        //          "name": ["in", ["Metal Type", "Metal Touch","Metal Colour", "Metal Purity"]]
        //      }
        //  };
        // })

        // frappe.call({ 
        //  method: "get_list_of_metal_type",
        //  doc: frm.doc,
        //  callback: function (r) {
        //      frm.set_df_property("metal_type", "options", r.message)
        //  } 
        // })

        frappe.call({ 
            method: "get_list_of_metal_purity",
            doc: frm.doc,
            callback: function (r) {
                // frm.set_df_property("base_purity", "options", r.message)
                frm.set_df_property("to_purity", "options", r.message)
            } 
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
            } 
        })
    },

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