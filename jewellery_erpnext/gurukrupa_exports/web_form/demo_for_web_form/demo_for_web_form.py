import frappe

@frappe.whitelist()
def get_context(employee_code):
	employee_data = []
	for i in  frappe.get_list('Employee',['name','employee_name','department','designation','reports_to']):
		if i['name'] == employee_code:
			employee_data.append(i)
			break
	return employee_data
