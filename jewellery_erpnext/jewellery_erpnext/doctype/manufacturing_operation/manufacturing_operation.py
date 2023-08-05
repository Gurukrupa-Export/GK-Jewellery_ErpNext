# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, time_diff
from frappe.model.document import Document

class ManufacturingOperation(Document):
	def validate(self):
		self.set_start_finish_time()
		# self.set_active_department_in_work_order()

	def set_start_finish_time(self):
		if self.has_value_changed("status"):
			if self.status == "WIP" and not self.start_time:
				self.start_time = now()
				self.finish_time = None
			elif self.status == "Finished":
				if not self.start_time:
					self.start_time = now()
				self.finish_time = now()
		if self.start_time and self.finish_time:
			self.time_taken = time_diff(self.finish_time, self.start_time)
	
	def set_active_department_in_work_order(self):
		if self.status == "WIP":
			frappe.set_value("Manufacturing Work Order", self.manufacturing_work_order, "department", self.department)

@frappe.whitelist()
def get_linked_stock_entries(docname):
	target_wh = frappe.db.get_value("Jewellery Settings","Jewellery Settings", "department_wip")
	filters = {"manufacturing_operation":docname, "docstatus":1, "t_warehouse": target_wh}

	data = frappe.get_all("Stock Entry Detail", filters=filters,fields="*")
	return frappe.render_template("jewellery_erpnext/jewellery_erpnext/doctype/manufacturing_operation/stock_entry_details.html", {"data":data})