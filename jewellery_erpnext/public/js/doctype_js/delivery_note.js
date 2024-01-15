frappe.ui.form.on('Delivery Note', {
    onload_post_render (frm) {
        // filter_customer(frm)
    },
    // sales_type (frm) {
        // filter_customer(frm)
    // },
})

let filter_customer = (frm) => {
    if (frm.doc.sales_type) {
      //filtering customer with sales type
      cur_frm.set_query("customer", function(doc) {
        return {
          query: 'jewellery_erpnext.utils.customer_query',
          'filters': {
            'sales_type': frm.doc.sales_type
          }
        };
      });
    } else {
      // removing filters
      cur_frm.set_query("customer", function(doc) {
        return {}
      });
    }
}