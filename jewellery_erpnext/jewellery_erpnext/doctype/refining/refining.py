# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt


import frappe
import json
from frappe import _
from frappe.utils import flt, cint, today
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class Refining(Document):
	pass

@frappe.whitelist()
def get_manufacturing_operations(source_name, target_doc=None):
	if not target_doc:
		target_doc = frappe.new_doc("Refining")
	elif isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))
	if not target_doc.get("manufacturing_work_order",{"manufacturing_work_order":source_name}):
		order = frappe.db.get_value("Manufacturing Work Order", source_name,
								   ["metal_type","metal_weight","manufacturing_order"],as_dict=1)
		target_doc.append("manufacturing_work_order",{"manufacturing_work_order":source_name,
												"metal_type":order["metal_type"],
												"metal_weight":order["metal_weight"],
												"parent_manufacturing_work_order":order["manufacturing_order"]})
	
	return target_doc
