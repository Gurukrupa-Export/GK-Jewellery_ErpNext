# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, time_diff
from frappe.model.document import Document

class QC(Document):
	def validate(self):
		status = None
		if self.status == "Accept":
			status = "Finished"
		elif self.status == "Reject":
			status = "Revert"
		if self.has_value_changed("status") and self.status in ["Accept","Reject"]:
			self.finish_time = now()
		if status and self.manufacturing_operation:
			frappe.db.set_value("Manufacturing Operation",self.manufacturing_operation,"status",status)
		self.time_taken = time_diff(self.finish_time, self.start_time)