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
	def onload(self):
		docstatus = frappe.db.get_value('Manufacturing Work Order',self.name,'docstatus')
		
		if docstatus == 1:
			db_data = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':self.name},['name','gross_wt','net_wt','diamond_wt','gemstone_wt','other_wt','received_gross_wt','received_net_wt','loss_wt','diamond_wt_in_gram','gemstone_wt_in_gram','diamond_pcs','gemstone_pcs'],as_dict=1,order_by='creation DESC')
			gross_wt = db_data['gross_wt']
			if gross_wt == 0:
				gross_wt = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':self.name},['name','prev_gross_wt'],as_dict=1,order_by='creation DESC')['prev_gross_wt']
			self.gross_wt=gross_wt
			self.net_wt = db_data['net_wt']
			self.diamond_wt = db_data['diamond_wt']
			self.gemstone_wt = db_data['gemstone_wt']
			self.other_wt = db_data['other_wt']
			self.received_gross_wt = db_data['received_gross_wt']
			self.received_net_wt = db_data['received_net_wt']
			self.diamond_wt_in_gram = db_data['diamond_wt_in_gram']
			self.diamond_pcs = db_data['diamond_pcs']
			self.gemstone_pcs = db_data['gemstone_pcs']

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
		status = "Not Started"
	if doc.split_from:
		department = doc.department
		status = "Not Started"
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

# @frappe.whitelist()
# def get_weight(manufacturing_work_order):
# 	docstatus = frappe.db.get_value('Manufacturing Work Order',manufacturing_work_order,'docstatus')
# 	if docstatus == 1:
# 		db_data = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':manufacturing_work_order},['name','gross_wt','net_wt','diamond_wt','gemstone_wt','other_wt','received_gross_wt','received_net_wt','loss_wt','diamond_wt_in_gram','gemstone_wt_in_gram','diamond_pcs','gemstone_pcs'],as_dict=1,order_by='creation DESC')
# 		gross_wt = db_data['gross_wt']
# 		if gross_wt == 0:
# 			gross_wt = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':manufacturing_work_order},['name','prev_gross_wt'],as_dict=1,order_by='creation DESC')['prev_gross_wt']
			
# 		frappe.db.set_value('Manufacturing Work Order',manufacturing_work_order,{
# 			'gross_wt':gross_wt,
# 			'net_wt':db_data['net_wt'],
# 			'diamond_wt':db_data['diamond_wt'],
# 			'gemstone_wt':db_data['gemstone_wt'],
# 			'other_wt':db_data['other_wt'],
# 			'received_gross_wt':db_data['received_gross_wt'],
# 			'received_net_wt':db_data['received_net_wt'],
# 			'diamond_wt_in_gram':db_data['diamond_wt_in_gram'],
# 			'diamond_pcs':db_data['diamond_pcs'],
# 			'gemstone_pcs':db_data['gemstone_pcs']
# 			})
# 		return db_data