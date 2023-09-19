# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class demoforwebform(Document):
	pass

# @frappe.whitelist()
# def get_context_(employee):
# 	employee_name = frappe.db.get_value('Employee',employee,'employee_name')
# 	return employee_name