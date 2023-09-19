import frappe

@frappe.whitelist()
def get_context(employee):
	employee_data = []
	for i in frappe.get_list('Employee', ['name','employee_name','department','designation']):
		if i['name'] == employee:
			employee_data.append(i)
			break
	return employee_data
	
