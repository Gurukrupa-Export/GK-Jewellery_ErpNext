# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now, cint
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.naming import make_autoname
from jewellery_erpnext.utils import set_values_in_bulk


class ManufacturingWorkOrder(Document):
	def autoname(self):
		if self.for_fg:
			self.name = make_autoname("MWO-.abbr.-.item_code.-.seq.-.##", doc=self)
		else:
			color = self.metal_colour.split('+')
			self.color = ''.join([word[0] for word in color if word])

	def on_submit(self):
		if self.for_fg:
			self.validate_other_work_orders()
		create_manufacturing_operation(self)
		self.start_datetime = now()
		self.db_set("status","Not Started")

	def validate_other_work_orders(self):
		last_department = frappe.db.get_value("Department Operation", {"is_last_operation":1,"company":self.company}, "department")
		if not last_department:
			frappe.throw(_("Please set last operation first in Department Operation"))
		pending_wo = frappe.get_all("Manufacturing Work Order",
			      {"name": ["!=",self.name],"manufacturing_order":self.manufacturing_order, "docstatus":["!=",2], "department":["!=",last_department]},
				  "name")
		if pending_wo:
			frappe.throw(_(f"All the pending manufacturing work orders should be in {last_department}."))

	def on_cancel(self):
		self.db_set("status","Cancelled")

	@frappe.whitelist()
	def get_linked_stock_entries(self): # MWO Details Tab code
		mwo = frappe.get_all("Manufacturing Work Order",{"name":self.name},pluck="name")
		data = frappe.db.sql(f"""select se.manufacturing_operation, se.name, sed.item_code,sed.item_name, sed.qty, sed.uom 
							from `tabStock Entry Detail` sed left join `tabStock Entry` se 
							on sed.parent = se.name 
							where se.docstatus = 1 and se.manufacturing_work_order in ('{"', '".join(mwo)}') ORDER BY se.modified ASC""", as_dict=1)
		total_qty = len([item['name'] for item in data])
		return frappe.render_template("jewellery_erpnext/jewellery_erpnext/doctype/manufacturing_work_order/stock_entry_details.html", {"data":data,"total_qty":total_qty})

def create_manufacturing_operation(doc):
	mop = get_mapped_doc("Manufacturing Work Order", doc.name,
			{
			"Manufacturing Work Order" : {
				"doctype":	"Manufacturing Operation",
				"field_map": {
					"name": "manufacturing_work_order"
				}
			}
			})
	
	settings = frappe.db.get_value("Manufacturing Setting", {'company': doc.company},["default_operation", "default_department"], as_dict=1)
	department = settings.get("default_department")
	operation = settings.get("default_operation")
	status = "Not Started"
	if doc.for_fg:
		department, operation = frappe.db.get_value("Department Operation", {"is_last_operation":1,"company":doc.company}, ["department","name"]) or ["",""]
	if doc.split_from:
		department = doc.department
		operation = None
	mop.status = status
	mop.type = "Manufacturing Work Order"
	mop.operation = operation
	mop.department = department
	mop.save()
	mop.db_set("employee", None)

@frappe.whitelist()
def create_split_work_order(docname, company, count = 1):
	limit = cint(frappe.db.get_value("Manufacturing Setting", {"company", company}, "wo_split_limit"))
	if cint(count) < 1 or (cint(count) > limit and limit > 0):
		frappe.throw(_("Invalid split count"))
	open_operations = frappe.get_all("Manufacturing Operation", filters={"manufacturing_work_order": docname},
				  or_filters = {"status": ["not in",["Finished", "Not Started", "Revert"]], "department_ir_status": "In-Transit"}, pluck='name')
	if open_operations:
		frappe.throw(f"Following operation should be closed before splitting work order: {', '.join(open_operations)}")
	for i in range(0, cint(count)):
		mop = get_mapped_doc("Manufacturing Work Order", docname,
			{
			"Manufacturing Work Order" : {
				"doctype":	"Manufacturing Work Order",
				"field_map": {
					"name": "split_from"
				}
			}
		})
		mop.save()
	pending_operations = frappe.get_all("Manufacturing Operation", {"manufacturing_work_order": docname, "status": "Not Started"}, pluck='name')
	if pending_operations:	#to prevent this workorder from showing in any IR doc
		set_values_in_bulk("Manufacturing Operation", pending_operations, {"status": "Finished"})
	frappe.db.set_value("Manufacturing Work Order", docname, "status", "Closed")