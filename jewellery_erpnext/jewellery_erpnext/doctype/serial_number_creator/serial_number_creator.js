// Copyright (c) 2024, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serial Number Creator', {
	refresh: function(frm) {
		// var condition = true;
		// $.each(frm.fields_dict['fg_details'].grid.grid_rows, function(idx, row) {
        //     // Access the child table field value for the condition check
        //     var fieldValue = row.doc.id;

        //     // Customize the condition as per your requirement
        //     if (condition) {
		// 		row.$row.css('background-color', 'green');
        //         // Set the background color to green
        //     } else {
        //         // Set the background color to red
        //         row.$row.css('background-color', 'red');
        //     }
        // });
	},

	onload:function(frm,cdt,cdn){
	$('input[data-fieldname="type"]')
	$('input[data-fieldname="type"]').val()
	$('input[data-fieldname="ityped"]').css("color","red")
	console.log('input[data-fieldname="type"]');
	}
});

frappe.ui.form.on("SNC FG Details", {
	refresh:function(frm,cdt,cdn){
		var child = locals[cdt][cdn]; 
		// child.qty
	}, 

	qty:function(frm,cdt,cdn){
		// frm.call("calulate_id_wise_sum_up")
		// frappe.call({
		// 	method:"jewellery_erpnext.jewellery_erpnext.doctype.serial_number_creator.serial_number_creator.get_operation_details",
		// 	args:{}
		// })
		
	}
});
