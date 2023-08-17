# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, time_diff
from frappe.model.document import Document
from jewellery_erpnext.utils import set_values_in_bulk

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
			frappe.set_value("Manufacturing Work Order", self.manufacturing_work_order, {"department": self.department, "status": "In Process"})

	@frappe.whitelist()
	def create_fg(self):
		create_manufacturing_entry(self)
		pmo = frappe.db.get_value("Manufacturing Work Order", self.manufacturing_work_order, "manufacturing_order")
		wo = frappe.get_all("Manufacturing Work Order", {"manufacturing_order": pmo}, pluck="name")
		set_values_in_bulk("Manufacturing Work Order", wo, {"status": "Completed"})

	@frappe.whitelist()
	def get_linked_stock_entries(self):
		target_wh = frappe.db.get_value("Warehouse",{"department": self.department})
		pmo = frappe.db.get_value("Manufacturing Work Order", self.manufacturing_work_order, "manufacturing_order")
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Manufacture"
		mwo = frappe.get_all("Manufacturing Work Order",
					{"name": ["!=",self.manufacturing_work_order],"manufacturing_order": pmo, "docstatus":["!=",2], "department":["=",self.department]},
					pluck="name")
		data = frappe.db.sql(f"""select se.manufacturing_work_order, se.manufacturing_operation, sed.parent, sed.item_code,sed.item_name, sed.qty, sed.uom 
		       				from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name where
							se.docstatus = 1 and se.manufacturing_work_order in ('{"', '".join(mwo)}') and sed.t_warehouse = '{target_wh}' 
							group by sed.manufacturing_operation,  sed.item_code, sed.qty, sed.uom """, as_dict=1)

		return frappe.render_template("jewellery_erpnext/jewellery_erpnext/doctype/manufacturing_operation/stock_entry_details.html", {"data":data})

def create_manufacturing_entry(doc):
	target_wh = frappe.db.get_value("Warehouse",{"department": doc.department})
	pmo = frappe.db.get_value("Manufacturing Work Order", doc.manufacturing_work_order, "manufacturing_order")
	pmo_det = frappe.db.get_value("Parent Manufacturing Order", pmo, ["item_code", "qty"], as_dict=1)
	se = frappe.get_doc({
		"doctype": "Stock Entry",
		"purpose": "Manufacture",
		"manufacturing_order": pmo,
		"stock_entry_type": "Manufacture",
		"department": doc.department,
		"to_department": doc.department,
		"manufacturing_work_order": doc.manufacturing_work_order,
		"manufacturing_operation": doc.name,
		"inventory_type": "Regular Stock",
		"auto_created":1
		})
	mwo = frappe.get_all("Manufacturing Work Order",
			      {"name": ["!=",doc.manufacturing_work_order],"manufacturing_order": pmo, "docstatus":["!=",2], "department":["=",doc.department]},
				  pluck="name")
	data = frappe.db.sql(f"""select se.manufacturing_work_order, se.manufacturing_operation, sed.parent, sed.item_code,sed.item_name, sed.qty, sed.uom 
		      				from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name where
							se.docstatus = 1 and se.manufacturing_work_order in ('{"', '".join(mwo)}') and sed.t_warehouse = '{target_wh}' 
							group by sed.manufacturing_operation,  sed.item_code, sed.qty, sed.uom """, as_dict=1)
	for entry in data:
		se.append("items",{
			"item_code": entry.item_code,
			"qty": entry.qty,
			"uom": entry.uom,
			"manufacturing_operation": doc.name,
			"department": doc.department,
			"to_department": doc.department,
			"s_warehouse": target_wh
		})
	se.append("items",{
		"item_code": pmo_det.item_code,
		"qty": pmo_det.qty,
		"t_warehouse": target_wh,
		"department": doc.department,
		"to_department": doc.department,
		"manufacturing_operation": doc.name,
		"is_finished_item":1
	})
	se.save()
	se.submit()
	frappe.msgprint('Finished Good created successfully')