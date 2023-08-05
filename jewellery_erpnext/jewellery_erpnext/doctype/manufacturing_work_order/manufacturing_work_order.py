# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class ManufacturingWorkOrder(Document):
	def autoname(self):
		color = self.metal_colour.split('+')
		self.color = ''.join([word[0] for word in color if word])

	def on_submit(self):
		create_manufacturing_operation(self)
		self.start_datetime = now()

def create_manufacturing_operation(doc):
	doc = get_mapped_doc("Manufacturing Work Order", doc.name,
			{
			"Manufacturing Work Order" : {
				"doctype":	"Manufacturing Operation",
				"field_map": {
					"name": "manufacturing_work_order"
				}
			}
			})
	doc.type = "Manufacturing Work Order"
	doc.operation = frappe.db.get_single_value("Jewellery Settings", "default_operation")
	doc.status = "Finished"
	doc.department = frappe.db.get_single_value("Jewellery Settings", "default_department")
	doc.save()