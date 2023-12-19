frappe.ui.form.on('Sales Order', {
  refresh: function(frm){
    
    frm.add_custom_button(__('Customer Approval'), function() {
      var customer_approval_dialoge = new frappe.ui.form.MultiSelectDialog({
          doctype: "Customer Approval",
          target: frm,
          setters: {
              date: null,
          },
          add_filters_group: 1,
        
          action(selections) {
              if (selections.length !== 1) {
                  frappe.throw(__("Please select exactly one option."));
                  return;
              }
              frappe.call({
                  method: 'jewellery_erpnext.jewellery_erpnext.doc_events.sales_order.get_customer_approval_data',
                  args: {
                      customer_approval_data: selections[0]
                  },

                  callback: (response) => {
                      frm.set_value('company', response.message["company"])
                      frm.set_value('order_type', response.message["order_type"])
                      frm.set_value('customer', response.message["customer"])
                      frm.set_value('set_warehouse', response.message["set_warehouse"])
                      
                      frm.clear_table("items")   

                      for(let items_row of response.message.items){
                          var child_row = frm.add_child('items')
                          child_row.item_code = items_row["item_code"];
                          child_row.item_name = items_row["item_name"];
                          child_row.delivery_date = items_row["delivery_date"]
                          child_row.description = items_row["description"]
                          child_row.uom = items_row["uom"]
                          child_row.conversion_factor = items_row["uom_conversion_factor"]
                          child_row.qty = items_row["quantity"];
                          child_row.amount = items_row["amount"];     
                      }
                      for(let sales_person_row of response.message.sales_person_child){
                          var child_row = frm.add_child('custom_sales_teams')
                          child_row.sales_person = sales_person_row["sales_person"];
                      }

                      customer_approval_dialoge.dialog.hide();
                      
                  },
                 
              })
          }
      });
    }, __("Get Items From"));

    console.log(frm.doc.docstatus)

    if(frm.doc.docstatus==1){
      frm.add_custom_button(__("Create Production Order"), () => {
        frappe.call({
          'method': "jewellery_erpnext.jewellery_erpnext.doctype.production_order.production_order._make_production_order",
          args: {
            sales_order: frm.doc.name
          },
          callback: function(r) {
            if(r.message){
              console.log("Message")
            }}
      });
    })


  }



  },
  validate:function(frm){
    frm.doc.items.forEach(function(d){
      if(d.bom){
        frappe.db.get_value("Item Price",{"item_code":d.item_code,"price_list":frm.doc.selling_price_list,"bom_no":d.bom},'price_list_rate',function(r){
          if(r.price_list_rate){
            frappe.model.set_value(d.doctype, d.name, 'rate',r.price_list_rate)
          }
        })
      }
    })
  },
})