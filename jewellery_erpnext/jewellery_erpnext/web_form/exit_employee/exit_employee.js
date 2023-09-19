frappe.ready(function() {
	// bind events here
	frappe.web_form.on('employee', (field, value) => {
		frappe.call({
			method: 'jewellery_erpnext.jewellery_erpnext.web_form.exit_employee.exit_employee.get_context',
			args: {
				'employee' :value
			},
			callback: (data) => {
				if (data.message) {
					console.log(data.message);
					frappe.web_form.set_value(['employee_name'], [data.message[0]['employee_name']])
					frappe.web_form.set_value(['department'], [data.message[0]['department']])
					frappe.web_form.set_value(['designation'], [data.message[0]['designation']])
				}
			}
		})
	})
})