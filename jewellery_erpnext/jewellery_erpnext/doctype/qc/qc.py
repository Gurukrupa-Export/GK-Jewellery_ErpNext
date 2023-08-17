# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now, time_diff, cint, flt
from frappe.model.document import Document
from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)

class QC(Document):
	def after_insert(self):
		frappe.db.set_value("Manufacturing Operation",self.manufacturing_operation, {"status": "QC Pending"})

	def on_submit(self):
		if self.status not in ["Accepted", "Rejected"] or any([row.idx for row in self.readings if not row.status]):
			frappe.throw(_("QC can only be submitted in Accepted or Rejected state"))
		status = "WIP"
		if self.status == "Accepted":
			pending_qc = frappe.db.get_value("QC", {"manufacturing_operation": self.manufacturing_operation, "status": ["!=", "Accepted"], "docstatus": ["!=",2]}, "name")
			if pending_qc:
				status = "QC Pending"
			else:
				status = "QC Completed"
		frappe.db.set_value("Manufacturing Operation",self.manufacturing_operation, {"status": status})

	def validate(self):
		if not self.readings:
			self.get_specification_details()
		else:
			self.inspect_and_set_status()

		if self.has_value_changed("status") and self.status in ["Accepted", "Rejected"]:
			self.finish_time = now()
			self.time_taken = time_diff(self.finish_time, self.start_time)

	@frappe.whitelist()
	def get_specification_details(self):
		if not self.quality_inspection_template:
			return

		self.set("readings", [])
		parameters = get_template_details(self.quality_inspection_template)
		for d in parameters:
			child = self.append("readings", {})
			child.update(d)
			child.manual_inspection = 1

	def inspect_and_set_status(self):
		for reading in self.readings:
			if not reading.manual_inspection:  # dont auto set status if manual
				if reading.formula_based_criteria:
					self.set_status_based_on_acceptance_formula(reading)
				else:
					# if not formula based check acceptance values set
					self.set_status_based_on_acceptance_values(reading)

		if not self.manual_inspection:
			for reading in self.readings:
				if reading.status == "Rejected":
					self.status = "Rejected"
					frappe.msgprint(
						_("Status set to rejected as there are one or more rejected readings."), alert=True
					)
					break
				elif reading.status == "Accepted":
					self.status = "Accepted"
		
	def set_status_based_on_acceptance_values(self, reading):
		if not cint(reading.numeric):
			result = reading.get("reading_value") == reading.get("value")
		else:
			# numeric readings
			result = self.min_max_criteria_passed(reading)

		reading.status = "Accepted" if result else "Rejected"

	def min_max_criteria_passed(self, reading):
		"""Determine whether all readings fall in the acceptable range."""
		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			frappe.msgprint(reading_value)
			if reading_value is not None and reading_value.strip():
				result = flt(reading.get("min_value")) <= flt(reading_value) <= flt(reading.get("max_value"))
				if not result:
					return False
			
		return True


	def set_status_based_on_acceptance_formula(self, reading):
		if not reading.acceptance_formula:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is required.").format(reading.idx),
				title=_("Missing Formula"),
			)

		condition = reading.acceptance_formula
		data = self.get_formula_evaluation_data(reading)

		try:
			result = frappe.safe_eval(condition, None, data)
			reading.status = "Accepted" if result else "Rejected"
		except NameError as e:
			field = frappe.bold(e.args[0].split()[1])
			frappe.throw(
				_("Row #{0}: {1} is not a valid reading field. Please refer to the field description.").format(
					reading.idx, field
				),
				title=_("Invalid Formula"),
			)
		except Exception:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is incorrect.").format(reading.idx),
				title=_("Invalid Formula"),
			)

	def get_formula_evaluation_data(self, reading):
		data = {}
		if not cint(reading.numeric):
			data = {"reading_value": reading.get("reading_value")}
		else:
			# numeric readings
			for i in range(1, 11):
				field = "reading_" + str(i)
				data[field] = flt(reading.get(field))
			data["mean"] = self.calculate_mean(reading)

		return data

	def calculate_mean(self, reading):
		"""Calculate mean of all non-empty readings."""
		from statistics import mean

		readings_list = []

		for i in range(1, 11):
			reading_value = reading.get("reading_" + str(i))
			if reading_value is not None and reading_value.strip():
				readings_list.append(flt(reading_value))

		actual_mean = mean(readings_list) if readings_list else 0
		return actual_mean

def create_qc_record(row, operation):
	templates = frappe.db.get_all("Operation MultiSelect", {"operation": operation}, pluck = "parent")
	for template in templates:
		if frappe.db.sql(f"""select name from `tabQC` where manufacturing_operation = '{row.manufacturing_operation}' and
					quality_inspection_template = '{template}' and ((docstatus = 1 and status = 'Accepted') or docstatus = 0)"""):
			continue
		doc = frappe.new_doc("QC")
		doc.manufacturing_work_order = row.manufacturing_work_order
		doc.manufacturing_operation = row.manufacturing_operation
		doc.quality_inspection_template = template
		doc.qc_person = frappe.session.user
		doc.posting_date = frappe.utils.getdate()
		doc.save(ignore_permissions=True)