# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.utils import flt, cint
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from jewellery_erpnext.jewellery_erpnext.doctype.main_slip.main_slip import get_main_slip_item, get_item_from_attribute
from jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir import update_stock_entry_dimensions, get_material_wt
from jewellery_erpnext.utils import update_existing
from jewellery_erpnext.jewellery_erpnext.doctype.qc.qc import create_qc_record


class EmployeeIR(Document):
	@frappe.whitelist()
	def get_operations(self):
		records = frappe.get_list("Manufacturing Operation",{"department": self.department,
						       "employee": ["is","not set"], "operation": ["is","not set"]},["name","gross_wt"])
		self.employee_ir_operations = []
		if records:
			for row in records:
				self.append("employee_ir_operations",{
					"manufacturing_operation": row.name
				})

	def on_submit(self):
		if self.type == "Issue":
			self.on_submit_issue()
		else:
			self.on_submit_receive()
	
	def validate(self):
		self.validate_gross_wt()
		self.update_main_slip()
		self.validate_qc("Warn")

	def on_cancel(self):
		if self.type == "Issue":
			self.on_submit_issue(cancel=True)
		else:
			self.on_submit_receive(cancel=True)

	def validate_gross_wt(self):
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
		for row in self.employee_ir_operations:
			if not self.main_slip:
				if flt(row.gross_wt, precision) < flt(row.received_gross_wt, precision):
					frappe.throw(f"Row #{row.idx}: Received gross wt cannot be greater than gross wt")

	#for issue
	def on_submit_issue(self, cancel=False):
		employee = None if cancel else self.employee
		operation = None if cancel else self.operation
		status = "Not Started" if cancel else "WIP"
		values = {"employee": employee, "operation": operation, "status": status}
		
		for row in self.employee_ir_operations:
			if not cancel:
				update_stock_entry_dimensions(self, row, row.manufacturing_operation, True)
				create_stock_entry(self,row)
				res = get_material_wt(self, row.manufacturing_operation)
				values.update(res)
			# values["gross_wt"] = get_value("Stock Entry Detail", {'manufacturing_operation': row.manufacturing_operation, "to_employee":self.employee}, 'sum(if(uom="cts",qty*0.2,qty))', 0)
			frappe.db.set_value("Manufacturing Operation", row.manufacturing_operation, values)

	#for receive
	def on_submit_receive(self, cancel=False):
		self.validate_qc("Stop")
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
		for row in self.employee_ir_operations:
			status = "WIP"
			if not cancel:
				status = "Finished"
				create_operation_for_next_op(row.manufacturing_operation)
				difference_wt = flt(row.received_gross_wt, precision) - flt(row.gross_wt, precision)
				create_stock_entry(self, row, difference_wt)
				res = get_material_wt(self, row.manufacturing_operation)
			res["status"] = status
			# gross_wt = get_value("Stock Entry Detail", {'manufacturing_operation': row.manufacturing_operation, "employee":self.employee}, 'sum(if(uom="cts",qty*0.2,qty))', 0)
			frappe.set_value("Manufacturing Operation", row.manufacturing_operation, res)

	def validate_qc(self, action = 'Warn'):
		if not self.is_qc_reqd or self.type == "Issue":
			return
	
		qc_list = []
		for row in self.employee_ir_operations:
			# is_created = frappe.db.sql("""select 
		 	# 					(select count(name) from `tabQC` where manufacturing_operation = 'MOP-01307' and docstatus != 2)
		 	# 					= (select count(distinct quality_inspection_template) from `tabQC` where manufacturing_operation = 'MOP-01307' and docstatus != 2) 
		 	# 				as is_created""")
			operation = frappe.db.get_value("Manufacturing Operation",row.manufacturing_operation, ["status"], as_dict=1)
			# qc_rejected = False
			# if operation.get("quality_inspection"):
			# 	qc_rejected = frappe.db.get_value("QC", operation.get("quality_inspection"), "status") == "Rejected"

			# if not operation.get("quality_inspection") or qc_rejected:
			# 	if action == "Warn":
			# 		create_qc_record(row, self.operation)
			# 	qc_list.append(row.manufacturing_operation)
			if operation.get("status") in ['QC Pending',"WIP"]:
				if action == "Warn":
					create_qc_record(row, self.operation)
				qc_list.append(row.manufacturing_operation)
		if qc_list:
			msg = f"Please complete QC for the following: {', '.join(qc_list)}"
			if action == "Warn":
				frappe.msgprint(_(msg))
			elif action == 'Stop':
				frappe.throw(_(msg))		

	def update_main_slip(self):
		if not self.main_slip or not self.is_main_slip_required:
			return
		
		main_slip = frappe.get_doc("Main Slip",self.main_slip)
		for row in self.employee_ir_operations:
			if not main_slip.get("main_slip_operation",{"manufacturing_operation":row.manufacturing_operation}):
				main_slip.append("main_slip_operation",{"manufacturing_operation":row.manufacturing_operation})
		main_slip.save()

def create_operation_for_next_op(docname, target_doc=None):
	def set_missing_value(source, target):
		target.previous_operation = source.operation

	target_doc = get_mapped_doc("Manufacturing Operation", docname,
			{
			"Manufacturing Operation" : {
				"doctype":	"Manufacturing Operation",
				"field_no_map": ['status','employee',"start_time",
		     					"finish_time", "time_taken", "department_issue_id",
								"department_receive_id", "department_ir_status", "operation", "previous_operation"]
			}
			}, target_doc, set_missing_value)

	target_doc.time_taken = None
	target_doc.save()


@frappe.whitelist()
def get_manufacturing_operations(source_name, target_doc=None):
	if not target_doc:
		target_doc = frappe.new_doc("Employee IR")
	elif isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))
	if not target_doc.get("employee_ir_operations",{"manufacturing_operation":source_name}):
		operation = frappe.db.get_value("Manufacturing Operation", source_name, ["gross_wt","manufacturing_work_order"],as_dict=1)
		target_doc.append("employee_ir_operations",{"manufacturing_operation":source_name, 
					      "gross_wt": operation["gross_wt"], "manufacturing_work_order": operation["manufacturing_work_order"]})
	return target_doc

def create_stock_entry(doc, row, difference_wt=0):
	department_wh = frappe.get_value("Warehouse", {"department": doc.department})
	employee_wh = frappe.get_value("Warehouse", {"employee": doc.employee})
	if not department_wh:
		frappe.throw(_(f"Please set warhouse for department {doc.department}"))
	if not employee_wh:
		frappe.throw(_(f"Please set warhouse for employee {doc.employee}"))
	stock_entries = frappe.db.sql(f"""select se.name from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name 
			       where se.docstatus=1 and sed.manufacturing_operation = '{row.manufacturing_operation}' and 
				   {"sed.t_warehouse" if doc.type == "Issue" else "sed.s_warehouse"} = '{department_wh}' 
				   and sed.to_department = '{doc.department}'""", as_dict=1, pluck=1)
	
	if doc.type == "Issue" and not stock_entries:
		prev_mfg_operation = get_previous_operation(row.manufacturing_operation)
		stock_entries = frappe.db.sql(f"""select se.name from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name 
			       where se.docstatus=1 and sed.manufacturing_operation = '{prev_mfg_operation}' and 
				   sed.t_warehouse = '{department_wh}' and sed.employee is not NULL
				   and sed.to_department = '{doc.department}'""", as_dict=1, pluck=1)
	item = None
	metal_item = None
	if doc.main_slip:
		item = get_main_slip_item(doc.main_slip)

	if difference_wt != 0:
		mwo = frappe.db.get_value("Manufacturing Work Order", row.manufacturing_work_order, ["metal_type", "metal_touch", "metal_purity", "metal_colour"], as_dict=1)
		metal_item = get_item_from_attribute(mwo.metal_type, mwo.metal_touch, mwo.metal_purity, mwo.metal_colour)
		existing_items = frappe.get_all("Stock Entry Detail",{"parent": ['in',stock_entries]}, pluck='item_code')
		if (metal_item not in existing_items) and difference_wt != 0:
			frappe.throw(_(f"Stock Entry for metal not found. Unable to add/subtract weight difference({difference_wt})"))
	
	for stock_entry in stock_entries:
		existing_doc = frappe.get_doc("Stock Entry", stock_entry)
		se_doc = frappe.copy_doc(existing_doc)
		for child in se_doc.items:
			if doc.type == "Issue":
				child.s_warehouse = department_wh
				child.t_warehouse = employee_wh
				child.to_employee = doc.employee
				child.employee = None
				child.department_operation = doc.operation
				child.main_slip = None
				child.to_main_slip = doc.main_slip if item == child.item_code else None
			else:
				child.s_warehouse = employee_wh
				child.t_warehouse = department_wh
				child.to_employee = None
				child.employee = doc.employee
				child.to_main_slip = None
				child.main_slip = doc.main_slip if item == child.item_code else None
			child.qty = child.qty + (difference_wt if metal_item == child.item_code else 0)
			if child.qty < 0:
				frappe.throw(_("Qty cannot be negative"))
			child.manufacturing_operation = row.manufacturing_operation
			child.department = doc.department
			child.to_department = doc.department
			child.manufacturer =  doc.manufacturer
			child.material_request = None
			child.material_request_item = None
			if (metal_item == child.item_code):
				update_existing("Manufacturing Operation", row.manufacturing_operation, {"gross_wt": f"gross_wt + {difference_wt}", "net_wt": f"net_wt + {difference_wt}"})
		
		se_doc.department = doc.department
		se_doc.to_department = doc.department
		se_doc.auto_created = True
		se_doc.employee_ir = doc.name
		se_doc.manufacturing_operation = row.manufacturing_operation
		se_doc.save()
		se_doc.submit()


def get_previous_operation(manufacturing_operation):
	mfg_operation = frappe.db.get_value("Manufacturing Operation", manufacturing_operation, ["previous_operation", "manufacturing_work_order"], as_dict=1)
	if not mfg_operation.previous_operation:
		return None
	return frappe.db.get_value("Manufacturing Operation", {"operation": mfg_operation.previous_operation, "manufacturing_work_order": mfg_operation.manufacturing_work_order})