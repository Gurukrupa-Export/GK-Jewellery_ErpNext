# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from jewellery_erpnext.utils import get_item_from_attribute


class MainSlip(Document):
	def autoname(self):
		department = self.department.split("-")[0]
		initials = department.split(' ')
		self.dep_abbr = ''.join([word[0] for word in initials if word])
		self.type_abbr = self.metal_type[0]
		self.color_abbr = self.metal_colour[0] if self.metal_colour else None

	def validate(self):
		if not self.for_subcontracting:
			self.validate_metal_properties()
			self.warehouse = frappe.db.get_value("Warehouse",{"employee": self.employee})
		else:
			self.warehouse = frappe.db.get_value("Warehouse",{"subcontractor": self.subcontractor})
		if not self.warehouse:
			frappe.throw(_(f"Please set warehouse for {'subcontractor' if self.for_subcontracting else 'employee'}: {self.subcontractor if self.for_subcontracting else self.employee}"))
		field_map = {
			"10KT": "wax_to_gold_10",
			"14KT": "wax_to_gold_14",
			"18KT": "wax_to_gold_18",
			"22KT": "wax_to_gold_22",
			"24KT": "wax_to_gold_24",
		}
		if self.is_tree_reqd:
			ratio = frappe.db.get_value("Manufacturing Setting",{"company": self.company},field_map.get(self.metal_touch))
			self.computed_gold_wt = flt(self.tree_wax_wt) * flt(ratio)
		if not frappe.db.exists("Material Request",{"main_slip": self.name}) and not self.is_new() and self.computed_gold_wt > 0:
			create_material_request(self)

	def validate_metal_properties(self):
		for row in self.main_slip_operation:
			mwo = frappe.db.get_value("Manufacturing Work Order", row.manufacturing_work_order, ["metal_type", "metal_touch", "metal_purity", "metal_colour"], as_dict=1)
			if mwo.metal_type != self.metal_type or mwo.metal_touch != self.metal_touch or mwo.metal_purity != self.metal_purity or (self.check_color and mwo.metal_colour != self.metal_colour):
				frappe.throw(f"Metal properties in Manufacturing Work Order: {row.manufacturing_work_order} do not match the main slip")

	def before_insert(self):
		if self.is_tree_reqd:
			self.tree_number = create_tree_number()

def create_material_request(doc):
	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Material Transfer"
	item = get_item_from_attribute(doc.metal_type, doc.metal_touch, doc.metal_purity, doc.metal_colour)
	if not item:
		return
	mr.schedule_date = frappe.utils.nowdate()
	mr.to_main_slip = doc.name
	mr.department = doc.department
	mr.append("items", {
		"item_code": item,
		"qty": doc.computed_gold_wt,
		"warehouse":  frappe.db.get_value("Warehouse",{"department": doc.department},"name")
	})
	mr.save()

def create_tree_number():
	doc = frappe.get_doc({"doctype": "Tree Number"}).insert()
	return doc.name

@frappe.whitelist()
def create_stock_entries(main_slip, actual_qty, metal_loss, metal_type, metal_touch, metal_purity, metal_colour=None):
	item = get_item_from_attribute(metal_type, metal_touch, metal_purity, metal_colour)
	if not item:
		frappe.throw("No Item found for selected atrributes in main slip")
	if flt(actual_qty) <= 0:
		return
	doc = frappe.db.get_value("Main Slip", main_slip, "*")
	settings = frappe.db.get_value("Manufacturing Setting", {"company": doc.company}, ["gold_loss_item"], as_dict=1)
	settings.department_wip = frappe.db.get_value("Warehouse", {"department": doc.department})
	create_metal_loss(doc, settings, item, flt(metal_loss))
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Transfer"
	stock_entry.inventory_type = "Regular Stock"
	stock_entry.append("items",{
		"item_code": item,
		"qty": flt(actual_qty),
		"s_warehouse": settings.department_wip,
		"t_warehouse": settings.department_wip,
		"main_slip": main_slip,
		"to_department": doc.department,
		"manufacturer": doc.manufacturer
	})
	stock_entry.save()
	stock_entry.submit()

def create_metal_loss(doc,settings,item,metal_loss):
	if metal_loss <= 0:
		return
	metal_loss_item = settings.gold_loss_item
	if not item:
		frappe.msgprint("Please set item for metal loss in Manufacturing Setting for selected company")
		return
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Repack"
	se.inventory_type = "Regular Stock"
	se.append("items",{
		"item_code": item,
		"qty": metal_loss,
		"s_warehouse": settings.department_wip,
		"t_warehouse": None,
		"main_slip": doc.name,
		"to_department": doc.department,
		"manufacturer": doc.manufacturer
	})
	se.append("items",{
		"item_code": metal_loss_item,
		"qty": metal_loss,
		"s_warehouse": None,
		"t_warehouse": settings.department_wip,
		"main_slip": doc.name,
		"to_department": doc.department,
		"manufacturer": doc.manufacturer
	})

	se.save()
	se.submit()

def get_main_slip_item(main_slip):
	ms = frappe.db.get_value("Main Slip", main_slip, ["metal_type", "metal_touch", "metal_purity", "metal_colour"], as_dict=1)
	item = get_item_from_attribute(ms.metal_type, ms.metal_touch, ms.metal_purity, ms.metal_colour)
	return item