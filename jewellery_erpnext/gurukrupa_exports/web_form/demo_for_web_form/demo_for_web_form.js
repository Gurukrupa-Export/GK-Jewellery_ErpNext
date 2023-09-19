frappe.ready(function() {
	frappe.web_form.on('employee_code', (field, value) => {
		frappe.call({
			method: 'jewellery_erpnext.gurukrupa_exports.web_form.demo_for_web_form.demo_for_web_form.get_context',
			args: {
				'employee_code':value
			},
			callback: (data) => {
				if (data.message) {
					console.log(data.message)
					frappe.web_form.set_value(['employee_name'], [data.message[0]['employee_name']])
					frappe.web_form.set_value(['department'], [data.message[0]['department']])
					frappe.web_form.set_value(['designation'], [data.message[0]['designation']])
					frappe.web_form.set_value(['reports_to'], [data.message[0]['reports_to']])
				}
			},
		});
	});
})
